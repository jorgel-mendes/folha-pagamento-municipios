#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1", "numpy", "dbfread>=2.0", "py7zr>=0.21"]
# ///
"""CAMADA SILVER -- normaliza cada fonte para o mesmo grao: municipio x codigo IBGE.

Cada fonte vira um parquet independente, com esquema estavel e chave `cod_ibge` de
7 digitos. Nenhuma juncao entre fontes acontece aqui -- isso e trabalho da camada gold.

Saidas em dados/silver/{ref}/:
    dim_municipio.parquet   cod_ibge, nome, uf, regiao
    populacao.parquet       cod_ibge, pop_total, pop_adulta
    depara_inss.parquet     cod_inss, uf, nome_inss, cod_ibge   (+ relatorio de residuo)
    inss.parquet            cod_ibge, especie, qtde, valor
    bolsa_familia.parquet   cod_ibge, familias_ref, valor_ref, familias_comp, valor_comp
    cadunico.parquet        cod_ibge, familias, pessoas, tam_medio_familia
    rais.parquet            cod_ibge, setor, esfera, vinculos, massa_salarial

Uso:
    uv run pipeline/02_silver.py [--ref 202512] [--so inss,rais] [--sem-rais]
"""
from __future__ import annotations

import csv
import json
import os
import shlex
import subprocess
import tempfile
import sys
import zipfile
from contextlib import contextmanager
from pathlib import Path

import duckdb
from dbfread import DBF

sys.path.insert(0, str(Path(__file__).parent))
import config as C  # noqa: E402


# ------------------------------------------------------------------ helpers
def registra_udfs(con: duckdb.DuckDBPyConnection) -> None:
    con.create_function("nrm", C.normaliza, ["VARCHAR"], "VARCHAR")
    con.create_function("k11", C.chave11, ["VARCHAR"], "VARCHAR")


def brl(col: str) -> str:
    """SQL que converte '1.518,00' em DOUBLE."""
    return f"TRY_CAST(replace(replace(trim({col}),'.',''),',','.') AS DOUBLE)"


def csv_do_zip(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not nomes:
            raise SystemExit(f"nenhum csv dentro de {zip_path.name}: {z.namelist()}")
        return nomes[0]


@contextmanager
def zip_em_fifo(zip_path: Path):
    """Expõe o CSV de dentro do zip como um caminho legível, sem gravá-lo em disco.

    O CSV do INSS tem 11,7 GB descompactado e o do Bolsa Família 2,1 GB. Descompactar
    para um FIFO deixa o DuckDB ler em streaming e mantém o disco livre. Exige que a
    leitura seja de passada única -- por isso todas as colunas são declaradas
    explicitamente, sem sniffing.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="fpm_"))
    fifo = tmpdir / "stream.csv"
    os.mkfifo(fifo)
    # o shell abre o FIFO para escrita e fica bloqueado ate o DuckDB abrir para leitura
    proc = subprocess.Popen(f"unzip -p {shlex.quote(str(zip_path))} > {shlex.quote(str(fifo))}",
                            shell=True)
    try:
        yield fifo
    finally:
        proc.wait()
        fifo.unlink(missing_ok=True)
        tmpdir.rmdir()


# ------------------------------------------------------------------ dimensoes
def dim_municipio(con, out: Path) -> None:
    raw = json.loads((C.BRONZE / "estatico" / "ibge_municipios.json").read_text(encoding="utf-8"))
    linhas = []
    for m in raw:
        uf_node = (m["microrregiao"]["mesorregiao"]["UF"] if m.get("microrregiao")
                   else m["regiao-imediata"]["regiao-intermediaria"]["UF"])
        linhas.append((str(m["id"]), m["nome"], uf_node["sigla"], uf_node["regiao"]["sigla"]))
    con.execute("CREATE OR REPLACE TABLE dim (cod_ibge VARCHAR, nome VARCHAR, uf VARCHAR, regiao VARCHAR)")
    con.executemany("INSERT INTO dim VALUES (?,?,?,?)", linhas)
    con.execute(f"COPY dim TO '{out}' (FORMAT parquet)")
    C.log(f"  dim_municipio: {len(linhas)} municipios")


def populacao(con, ano: str, out: Path) -> None:
    zp = C.BRONZE / "estatico" / f"POPSBR{ano[2:]}.zip"
    destino = zp.parent / f"POP{ano[2:]}.dbf"
    if not destino.exists():
        with zipfile.ZipFile(zp) as z:
            dbf = [n for n in z.namelist() if n.lower().endswith(".dbf")][0]
            destino.write_bytes(z.read(dbf))
    # ~900 mil linhas: passar por CSV e COPY e ordens de grandeza mais rapido que executemany
    tmp_csv = destino.with_suffix(".csv")
    if not tmp_csv.exists():
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["cod_mun", "idade", "pop"])
            for r in DBF(str(destino), encoding="latin-1"):
                w.writerow([r["cod_mun"], r["idade"], r["pop"]])
    con.execute(f"""CREATE OR REPLACE TABLE pop_raw AS
      SELECT cod_mun, idade::INT AS idade, pop::INT AS pop
      FROM read_csv('{tmp_csv}', header=true, all_varchar=true)""")
    # o POPSVS ja usa o codigo IBGE completo de 7 digitos -- casa direto com a dimensao
    con.execute(f"""COPY (
        SELECT d.cod_ibge,
               sum(p.pop)::BIGINT AS pop_total,
               sum(p.pop) FILTER (WHERE p.idade >= {C.IDADE_ADULTA})::BIGINT AS pop_adulta
        FROM pop_raw p JOIN dim d ON d.cod_ibge = p.cod_mun
        GROUP BY 1) TO '{out}' (FORMAT parquet)""")
    n, tot = con.sql(f"SELECT count(*), sum(pop_total) FROM '{out}'").fetchone()
    if not n:
        raise SystemExit("nenhum municipio casou com a populacao -- confira o formato de cod_mun")
    C.log(f"  populacao: {n} municipios, {tot:,} habitantes")


# ------------------------------------------------------------------ INSS
def depara_inss(con, zip_inss: Path, out: Path) -> None:
    """Casa o codigo proprio do INSS com o codigo IBGE.

    O campo vem como `CCCCC-UF-Nome` com o nome truncado em 11 caracteres, entao:
      1. chave (UF, 11 primeiros caracteres normalizados)
      2. grupos 1:1 casam direto
      3. grupos n:n casam por ordem -- os codigos do INSS sao alfabeticos dentro da UF
      4. o residuo (grafias antigas) sai da tabela de alias em config.ALIAS_INSS_IBGE
    """
    # O DISTINCT vem antes da UDF de proposito: k11() e uma funcao Python, e aplica-la nas
    # 41 milhoes de linhas antes de reduzir para os ~5.570 municipios distintos custa
    # dezenas de minutos. Depois do DISTINCT, custa nada.
    con.execute(f"""CREATE OR REPLACE TABLE inss_mun AS
      SELECT cod_inss, uf, nome_inss, k11(nome_inss) AS k11 FROM (
        SELECT DISTINCT substr(mun,1,5) AS cod_inss, upper(substr(mun,7,2)) AS uf,
               trim(substr(mun,10)) AS nome_inss
        FROM (SELECT trim(mun_resid) AS mun FROM inss_bruto)
        WHERE mun SIMILAR TO '[0-9]{{5}}-[A-Z][a-z]-.*')""")

    con.execute("""CREATE OR REPLACE TABLE dp AS
      WITH i AS (SELECT *, row_number() OVER (PARTITION BY uf,k11 ORDER BY cod_inss) rn,
                            count(*)   OVER (PARTITION BY uf,k11) n FROM inss_mun),
           b AS (SELECT cod_ibge, nome, uf, k11(nome) k11, nrm(nome) nn FROM dim),
           b2 AS (SELECT *, row_number() OVER (PARTITION BY uf,k11 ORDER BY nn) rn,
                            count(*)   OVER (PARTITION BY uf,k11) n FROM b)
      SELECT i.cod_inss, i.uf, i.nome_inss, b2.cod_ibge
      FROM i LEFT JOIN b2 ON i.uf=b2.uf AND i.k11=b2.k11 AND i.rn=b2.rn AND i.n=b2.n""")

    alias = [(uf, nome, cod) for (uf, nome), cod in C.ALIAS_INSS_IBGE.items()]
    con.execute("CREATE OR REPLACE TABLE alias (uf VARCHAR, nome_inss VARCHAR, cod_ibge VARCHAR)")
    con.executemany("INSERT INTO alias VALUES (?,?,?)", alias)
    con.execute(f"""COPY (
        SELECT d.cod_inss, d.uf, d.nome_inss, coalesce(d.cod_ibge, a.cod_ibge) AS cod_ibge
        FROM dp d LEFT JOIN alias a ON a.uf=d.uf AND a.nome_inss=d.nome_inss)
      TO '{out}' (FORMAT parquet)""")
    tot, ok = con.sql(f"SELECT count(*), count(cod_ibge) FROM '{out}'").fetchone()
    C.log(f"  depara_inss: {ok}/{tot} resolvidos ({100*ok/tot:.2f}%)")
    if ok < tot:
        falta = con.sql(f"SELECT cod_inss, uf, nome_inss FROM '{out}' WHERE cod_ibge IS NULL").fetchall()
        C.log(f"  ATENCAO: {len(falta)} sem par -- adicione em config.ALIAS_INSS_IBGE:")
        for c, uf, nome in falta[:20]:
            C.log(f"    (\"{uf}\", \"{nome}\"): \"???\",")


def inss(con, ref: str, dst: Path) -> None:
    zip_inss = C.BRONZE / ref / f"inss_emitidos_{ref}.zip"
    csv_nome = csv_do_zip(zip_inss)
    C.log(f"  lendo {csv_nome} em streaming (o CSV descompactado passa de 11 GB)")
    # unzip -p evita materializar o csv em disco
    cols = {"despacho": "VARCHAR", "sexo": "VARCHAR", "clientela": "VARCHAR", "tipo_benef": "VARCHAR",
            "uf": "VARCHAR", "meio_pagto": "VARCHAR", "banco": "VARCHAR", "mun_pagto": "VARCHAR",
            "mun_resid": "VARCHAR", "vl_liquido": "VARCHAR", "ramo_ativ": "VARCHAR",
            "dt_ini_valid": "VARCHAR", "especie_cod": "VARCHAR", "especie_nome": "VARCHAR"}
    with zip_em_fifo(zip_inss) as fifo:
        con.execute(f"""CREATE OR REPLACE TABLE inss_bruto AS
          SELECT trim(mun_resid) mun_resid, trim(especie_cod) especie,
                 trim(especie_nome) especie_nome, {brl('vl_liquido')} vl
          FROM read_csv('{fifo}', delim=';', header=false, skip=1, encoding='latin-1',
                        quote='', all_varchar=true, columns={cols})""")

    n, soma, nulos = con.sql(
        "SELECT count(*), sum(vl), count(*) FILTER (WHERE vl IS NULL) FROM inss_bruto").fetchone()
    C.log(f"  inss bruto: {n:,} beneficios | R$ {soma:,.2f} | nao parseados: {nulos}")
    if nulos:
        raise SystemExit("valores monetarios nao parseados -- confira o formato do arquivo")

    depara_inss(con, zip_inss, dst / "depara_inss.parquet")

    con.execute(f"""COPY (
        SELECT dp.cod_ibge, b.especie, any_value(b.especie_nome) AS especie_nome,
               count(*)::BIGINT AS qtde, sum(b.vl) AS valor
        FROM inss_bruto b
        JOIN '{dst / "depara_inss.parquet"}' dp ON dp.cod_inss = substr(b.mun_resid,1,5)
        WHERE dp.cod_ibge IS NOT NULL
        GROUP BY 1,2) TO '{dst / "inss.parquet"}' (FORMAT parquet)""")

    nao_aloc = con.sql(f"""SELECT count(*)::BIGINT, coalesce(sum(vl),0) FROM inss_bruto b
        LEFT JOIN '{dst / "depara_inss.parquet"}' dp ON dp.cod_inss = substr(b.mun_resid,1,5)
        WHERE dp.cod_ibge IS NULL""").fetchone()
    C.log(f"  inss: gravado. Nao alocado a municipio: {nao_aloc[0]:,} beneficios / R$ {nao_aloc[1]:,.2f}")
    (dst / "inss_nao_alocado.json").write_text(
        json.dumps({"beneficios": nao_aloc[0], "valor": nao_aloc[1],
                    "total_beneficios": n, "total_valor": soma}, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ Bolsa Familia
def bolsa_familia(con, ref: str, dst: Path) -> None:
    """Portal da Transparencia, um registro por parcela paga.

    Duas leituras diferentes do mesmo arquivo, e a escolha entre elas e decisao
    metodologica (ver briefing, Q8):
      _ref  = parcelas cuja MES REFERENCIA e a propria competencia (estoque do mes)
      _comp = tudo que foi pago naquela competencia, incluindo retroativos
    O municipio vem em codigo SIAFI, casado com o IBGE por (UF, nome normalizado).
    """
    zip_bf = C.BRONZE / ref / f"bolsa_familia_{ref}.zip"
    C.log("  lendo Bolsa Familia em streaming (~2 GB descompactado)")
    cols = {"mes_competencia": "VARCHAR", "mes_referencia": "VARCHAR", "uf": "VARCHAR",
            "cod_siafi": "VARCHAR", "nome_municipio": "VARCHAR", "cpf": "VARCHAR",
            "nis": "VARCHAR", "nome": "VARCHAR", "valor": "VARCHAR"}
    with zip_em_fifo(zip_bf) as fifo:
        con.execute(f"""CREATE OR REPLACE TABLE bf AS
          SELECT trim(mes_referencia) mes_ref, upper(trim(uf)) uf, trim(cod_siafi) siafi,
                 trim(nome_municipio) municipio, trim(nis) nis, {brl('valor')} vl
          FROM read_csv('{fifo}', delim=';', header=false, skip=1, encoding='latin-1',
                        all_varchar=true, columns={cols})""")

    # De-para SIAFI -> IBGE. Diferente do INSS, aqui os nomes vem completos, entao da para
    # resolver sozinho em duas passadas em vez de manter tabela de alias na mao:
    #   1. casamento exato por (UF, nome normalizado), tirando sufixo entre parenteses
    #      -- o Portal escreve "SERRA CAIADA (EX-PRESIDENTE JUSCELINO)"
    #   2. o que sobrou casa por similaridade dentro da MESMA UF, so entre os municipios
    #      ainda livres dos dois lados. Sao grafias antigas (PARATI, POXOREO, ARES).
    # DISTINCT antes da UDF: nrm() e Python, e roda-la nos ~20 milhoes de registros de
    # pagamento antes de reduzir aos ~5.570 municipios custa minutos. Depois, milissegundos.
    con.execute("""CREATE OR REPLACE TABLE bf_mun AS
      SELECT siafi, uf, municipio, nrm(regexp_replace(municipio, '\\(.*\\)', '')) AS nn
      FROM (SELECT DISTINCT siafi, uf, municipio FROM bf)""")
    con.execute("""CREATE OR REPLACE TABLE exato AS
      SELECT b.siafi, b.uf, b.municipio, d.cod_ibge
      FROM bf_mun b LEFT JOIN dim d ON d.uf = b.uf AND nrm(d.nome) = b.nn""")
    con.execute("CREATE OR REPLACE TABLE alias_siafi (uf VARCHAR, municipio VARCHAR, cod_ibge VARCHAR)")
    con.executemany("INSERT INTO alias_siafi VALUES (?,?,?)",
                    [(uf, m, cod) for (uf, m), cod in C.ALIAS_SIAFI_IBGE.items()])

    con.execute("""CREATE OR REPLACE TABLE dp_siafi AS
      WITH livre_bf AS (SELECT * FROM exato WHERE cod_ibge IS NULL),
           livre_ibge AS (SELECT * FROM dim WHERE cod_ibge NOT IN
                          (SELECT cod_ibge FROM exato WHERE cod_ibge IS NOT NULL)),
           cand AS (
             SELECT s.siafi, s.uf, s.municipio, i.cod_ibge, i.nome AS nome_ibge,
                    jaro_winkler_similarity(nrm(s.municipio), nrm(i.nome)) AS sim,
                    row_number() OVER (PARTITION BY s.siafi
                                       ORDER BY jaro_winkler_similarity(nrm(s.municipio), nrm(i.nome)) DESC) AS rk
             FROM livre_bf s JOIN livre_ibge i ON i.uf = s.uf)
      SELECT siafi, uf, municipio, cod_ibge, 'exato' AS origem, 1.0 AS sim
        FROM exato WHERE cod_ibge IS NOT NULL
      UNION ALL
      SELECT siafi, uf, municipio, cod_ibge, 'aproximado', sim
        FROM cand WHERE rk = 1 AND sim >= 0.85
      UNION ALL
      SELECT e.siafi, e.uf, e.municipio, a.cod_ibge, 'alias', 1.0
        FROM exato e JOIN alias_siafi a ON a.uf = e.uf AND a.municipio = e.municipio
       WHERE e.cod_ibge IS NULL
         AND e.siafi NOT IN (SELECT siafi FROM cand WHERE rk = 1 AND sim >= 0.85)""")

    tot = con.sql("SELECT count(*) FROM bf_mun").fetchone()[0]
    ok, aprox = con.sql("""SELECT count(*), count(*) FILTER (WHERE origem='aproximado')
                           FROM dp_siafi""").fetchone()
    C.log(f"  depara SIAFI->IBGE: {ok}/{tot} ({100*ok/tot:.2f}%) | {aprox} por similaridade")
    for m, n, s in con.sql("""SELECT municipio, cod_ibge, round(sim,3) FROM dp_siafi
                              WHERE origem='aproximado' ORDER BY sim LIMIT 5""").fetchall():
        C.log(f"    aproximado: {m} -> {n} (similaridade {s})")
    if ok < tot:
        for (m,) in con.sql("""SELECT municipio FROM bf_mun WHERE siafi NOT IN
                               (SELECT siafi FROM dp_siafi) LIMIT 10""").fetchall():
            C.log(f"    SEM PAR: {m}")

    con.execute(f"""COPY (
        SELECT p.cod_ibge,
               count(DISTINCT b.nis) FILTER (WHERE b.mes_ref = '{ref}')::BIGINT AS familias_ref,
               coalesce(sum(b.vl)    FILTER (WHERE b.mes_ref = '{ref}'), 0)      AS valor_ref,
               count(DISTINCT b.nis)::BIGINT                                     AS familias_comp,
               sum(b.vl)                                                         AS valor_comp
        FROM bf b JOIN dp_siafi p ON p.siafi = b.siafi AND p.uf = b.uf
        WHERE p.cod_ibge IS NOT NULL
        GROUP BY 1) TO '{dst / "bolsa_familia.parquet"}' (FORMAT parquet)""")
    r = con.sql(f"""SELECT count(*), sum(familias_ref), sum(valor_ref), sum(familias_comp), sum(valor_comp)
                    FROM '{dst / "bolsa_familia.parquet"}'""").fetchone()
    C.log(f"  bolsa_familia: {r[0]} municipios | ref: {r[1]:,} familias / R$ {r[2]:,.2f} "
          f"| competencia: {r[3]:,} familias / R$ {r[4]:,.2f}")


# ------------------------------------------------------------------ CadUnico
def cadunico(con, ref: str, dst: Path) -> None:
    src = C.BRONZE / ref / f"cadunico_{ref}.csv"
    con.execute(f"""COPY (
        SELECT d.cod_ibge,
               c.cadun_qtd_familias_cadastradas_i::BIGINT AS familias,
               c.cadun_qtd_pessoas_cadastradas_i::BIGINT  AS pessoas,
               CASE WHEN c.cadun_qtd_familias_cadastradas_i::DOUBLE > 0
                    THEN c.cadun_qtd_pessoas_cadastradas_i::DOUBLE
                       / c.cadun_qtd_familias_cadastradas_i::DOUBLE END AS tam_medio_familia,
               TRY_CAST(c.cadunico_tot_pes_pbf_i AS BIGINT)      AS pessoas_pbf,
               TRY_CAST(c.pbf_media_pessoas_benef_f AS DOUBLE)   AS media_pessoas_pbf
        FROM read_csv('{src}', header=true, all_varchar=true) c
        JOIN dim d ON substr(d.cod_ibge,1,6) = c.codigo_ibge)
      TO '{dst / "cadunico.parquet"}' (FORMAT parquet)""")
    n, tm, pes, mpbf = con.sql(f"""SELECT count(*), round(avg(tam_medio_familia),3),
        sum(pessoas_pbf), round(avg(media_pessoas_pbf),3)
        FROM '{dst / 'cadunico.parquet'}'""").fetchone()
    C.log(f"  cadunico: {n} municipios | familia media no CadUnico: {tm} | "
          f"familia media no PBF: {mpbf}")
    C.log(f"  cadunico: {pes:,} pessoas em familias do Bolsa Familia (numero publicado)")


# ------------------------------------------------------------------ RAIS
# Nomes conferidos no arquivo real da RAIS 2025 (RAIS_VINC_PUB_*.COMT). O formato mudou
# em relacao a anos anteriores: delimitador virgula, aspas duplas e ponto decimal.
ALIAS_RAIS = {
    "municipio":  ["município - código", "municipio - codigo", "município", "municipio"],
    "nat_jur":    ["natureza jurídica - código", "natureza juridica - codigo", "natureza jurídica"],
    "remun_dez":  ["vl rem dezembro nom", "vl remun dezembro nom", "vl rem dezembro (nom)"],
    "remun_med":  ["vl rem média nom", "vl rem media nom", "vl remun média nom"],
    "ativo":      ["ind vínculo ativo 31/12 - código", "ind vinculo ativo 31/12 - codigo",
                   "vínculo ativo 31/12", "vinculo ativo 31/12"],
    "abandonado": ["ind vínculo abandonado - código", "ind vinculo abandonado - codigo"],
}


def detecta_colunas(header: list[str]) -> dict[str, str]:
    achado, baixo = {}, {h.strip().lower(): h for h in header}
    for chave, opcoes in ALIAS_RAIS.items():
        for o in opcoes:
            if o in baixo:
                achado[chave] = baixo[o]
                break
    faltando = set(ALIAS_RAIS) - set(achado)
    if faltando:
        raise SystemExit(
            f"colunas da RAIS nao encontradas: {sorted(faltando)}\n"
            f"colunas presentes no arquivo:\n  " + "\n  ".join(sorted(header)) +
            "\n\nAjuste ALIAS_RAIS em pipeline/02_silver.py com os nomes acima.")
    return achado


def rais(con, ano: str, dst: Path) -> None:
    import py7zr
    drais = C.BRONZE / f"rais_{ano}"
    tmp = drais / "extraido"
    tmp.mkdir(exist_ok=True)
    partes = []
    for arq in sorted(drais.glob("*.7z")):
        alvo = tmp / (arq.stem + ".COMT")
        if not alvo.exists():
            C.log(f"  extraindo {arq.name} ...")
            with py7zr.SevenZipFile(arq) as z:
                nomes = z.getnames()
                z.extractall(path=tmp)
            for n in nomes:
                p = tmp / n
                if p.exists() and p != alvo:
                    p.rename(alvo)
        partes.append(alvo)
    if not partes:
        raise SystemExit(f"nenhum arquivo da RAIS em {drais} -- rode 01_bronze.py primeiro")

    leitura = "delim=',', quote='\"', header=true, encoding='latin-1', all_varchar=true"
    header = con.sql(f"SELECT * FROM read_csv('{partes[0]}', {leitura}, sample_size=1) LIMIT 0").columns
    col = detecta_colunas(list(header))
    C.log(f"  colunas RAIS detectadas: {col}")

    arquivos = "[" + ",".join(f"'{p}'" for p in partes) + "]"
    # Vinculo abandonado: a RAIS marca como ativo em 31/12 um vinculo que o trabalhador
    # deixou sem rescisao formal. Todos vem com remuneracao zero, entao nao mexem na massa,
    # mas inflam a contagem de vinculos -- que e justamente o denominador do salario medio
    # e da taxa por 100 adultos. Ficam de fora.
    con.execute(f"""CREATE OR REPLACE TABLE rais_bruto AS
      SELECT lpad(trim("{col['municipio']}"),6,'0')                   AS cod_mun6,
             lpad(trim("{col['nat_jur']}"),4,'0')                     AS nat_jur,
             trim("{col['abandonado']}")                              AS abandonado,
             TRY_CAST(trim("{col['remun_dez']}") AS DOUBLE)           AS remun_dez,
             TRY_CAST(trim("{col['remun_med']}") AS DOUBLE)           AS remun_med
      FROM read_csv({arquivos}, {leitura}, union_by_name=true)
      WHERE trim("{col['ativo']}") IN ('1','SIM','Sim')""")

    aband, total = con.sql("""SELECT count(*) FILTER (WHERE abandonado='1'), count(*)
                              FROM rais_bruto""").fetchone()
    C.log(f"  rais: {aband:,} vinculos abandonados excluidos ({100*aband/total:.2f}% dos ativos)")
    con.execute("DELETE FROM rais_bruto WHERE abandonado='1'")

    zerados = con.sql("""SELECT count(*) FROM rais_bruto
                         WHERE remun_dez IS NULL OR remun_dez = 0""").fetchone()[0]
    restantes = total - aband
    C.log(f"  rais: {zerados:,} vinculos ativos com remuneracao de dezembro zero ou nula "
          f"({100*zerados/restantes:.2f}%) -- contam como vinculo, ficam fora da media (Q10)")

    # Classificar setor/esfera com UDF Python direto no GROUP BY custaria uma chamada por
    # vinculo (milhoes). A natureza juridica tem ~100 valores distintos, entao materializamos
    # uma dimensao pequena e o resto vira JOIN nativo.
    naturezas = [nj for (nj,) in con.sql("SELECT DISTINCT nat_jur FROM rais_bruto").fetchall()]
    con.execute("CREATE OR REPLACE TABLE dim_nat (nat_jur VARCHAR, setor VARCHAR, esfera VARCHAR)")
    con.executemany("INSERT INTO dim_nat VALUES (?,?,?)",
                    [(nj, *(lambda t: (t[0], t[1] or ""))(C.classifica_setor(nj))) for nj in naturezas])
    C.log(f"  rais: {len(naturezas)} naturezas juridicas distintas classificadas")

    # Medida principal: remuneracao de DEZEMBRO, que e o padrao da RAIS.
    # `massa_salarial` soma todo mundo, sem corte -- massa e total, nao estimativa central.
    # `base_media_*` aplica o corte da RAIS de 0,7 a 30 salarios minimos, e serve **apenas**
    # para o calculo da media. `massa_media_anual` guarda a remuneracao media do ano como
    # medida alternativa, para comparacao.
    piso, teto = C.faixa_media_reais(ano)
    C.log(f"  corte da media: R$ {piso:,.2f} a R$ {teto:,.2f} "
          f"({C.FAIXA_MEDIA_SM[0]} a {C.FAIXA_MEDIA_SM[1]} SM de {ano}, SM = R$ {C.SALARIO_MINIMO[ano]:,.2f})")
    na_faixa = f"r.remun_dez BETWEEN {piso} AND {teto}"
    con.execute(f"""COPY (
        SELECT d.cod_ibge, n.setor, n.esfera,
               count(*)::BIGINT                                        AS vinculos,
               sum(coalesce(r.remun_dez,0))                            AS massa_salarial,
               count(*) FILTER (WHERE {na_faixa})::BIGINT              AS base_media_vinculos,
               sum(r.remun_dez) FILTER (WHERE {na_faixa})              AS base_media_massa,
               sum(coalesce(r.remun_med,0))                            AS massa_media_anual,
               count(*) FILTER (WHERE r.remun_dez IS NULL)::BIGINT     AS vinculos_sem_dezembro
        FROM rais_bruto r
        JOIN dim d       ON substr(d.cod_ibge,1,6) = r.cod_mun6
        JOIN dim_nat n   ON n.nat_jur = r.nat_jur
        GROUP BY 1,2,3) TO '{dst / "rais.parquet"}' (FORMAT parquet)""")
    r = con.sql(f"""SELECT count(DISTINCT cod_ibge), sum(vinculos), sum(massa_salarial),
                           sum(base_media_vinculos), sum(base_media_massa), sum(vinculos_sem_dezembro)
                    FROM '{dst / "rais.parquet"}'""").fetchone()
    C.log(f"  rais: {r[0]} municipios | {r[1]:,} vinculos ativos | massa de dezembro R$ {r[2]:,.2f}")
    C.log(f"  rais: base da media {r[3]:,} vinculos ({100*r[3]/r[1]:.1f}% dos ativos) "
          f"| salario medio R$ {r[4]/r[3]:,.2f}")
    C.log(f"  rais: {r[5]:,} vinculos ativos sem remuneracao de dezembro ({100*r[5]/r[1]:.1f}%)")
    nao_class = con.sql(f"SELECT sum(vinculos) FROM '{dst / 'rais.parquet'}' WHERE setor='ignorado'").fetchone()[0]
    if nao_class:
        C.log(f"  rais: {nao_class:,} vinculos com natureza juridica ignorada (9999)")


# ------------------------------------------------------------------ main
def main() -> None:
    ref = C.ref_do_argv()
    ano = C.ano_rais(ref)
    dst = C.dir_camada(C.SILVER, ref)
    so = None
    if C.tem_flag("--so"):
        so = set(sys.argv[sys.argv.index("--so") + 1].split(","))
    roda = lambda nome: (so is None or nome in so)

    C.log(f"SILVER | competencia={ref} | destino={dst}")
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='6GB'; PRAGMA temp_directory='/tmp/duckdb_fpm'")
    registra_udfs(con)

    C.log("1/6 dimensao de municipios")
    dim_municipio(con, dst / "dim_municipio.parquet")
    C.log("2/6 populacao por idade")
    populacao(con, ano, dst / "populacao.parquet")
    if roda("inss"):
        C.log("3/6 INSS")
        inss(con, ref, dst)
    if roda("bf"):
        C.log("4/6 Bolsa Familia")
        bolsa_familia(con, ref, dst)
    if roda("cadunico"):
        C.log("5/6 CadUnico")
        cadunico(con, ref, dst)
    if roda("rais") and not C.tem_flag("--sem-rais"):
        C.log("6/6 RAIS")
        rais(con, ano, dst)

    C.log("SILVER concluida.")
    C.log("Proximo passo: uv run pipeline/03_gold.py --ref " + ref)


if __name__ == "__main__":
    main()
