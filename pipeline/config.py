"""Configuracao compartilhada do pipeline Folha de Pagamento dos Municipios.

Nao e um passo do pipeline -- so parametros, caminhos e helpers usados pelas tres camadas.
Para rodar outro periodo, mude REF_PADRAO aqui ou passe --ref na linha de comando.
"""
from __future__ import annotations

import os
import re
import sys
import time
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------- periodo
REF_PADRAO = "202512"          # competencia AAAAMM usada por INSS, Bolsa Familia e CadUnico
ANO_RAIS_PADRAO = "2025"       # RAIS e anual: estoque em 31/12

def ref_do_argv(argv: list[str] | None = None) -> str:
    argv = argv if argv is not None else sys.argv[1:]
    if "--ref" in argv:
        return argv[argv.index("--ref") + 1]
    return os.environ.get("FPM_REF", REF_PADRAO)

def ano_rais(ref: str) -> str:
    return os.environ.get("FPM_ANO_RAIS", ref[:4])

def tem_flag(nome: str, argv: list[str] | None = None) -> bool:
    return nome in (argv if argv is not None else sys.argv[1:])

# ---------------------------------------------------------------- caminhos
RAIZ = Path(__file__).resolve().parent.parent
BRONZE = RAIZ / "dados" / "bronze"
SILVER = RAIZ / "dados" / "silver"
GOLD = RAIZ / "dados" / "gold"
SITE = RAIZ / "site"

def dir_camada(base: Path, ref: str) -> Path:
    d = base / ref
    d.mkdir(parents=True, exist_ok=True)
    return d

# ---------------------------------------------------------------- fontes
CKAN_INSS = "https://dadosabertos.inss.gov.br/api/3/action/package_show"
PKG_INSS_EMITIDOS = "beneficios-emitidos-plano-de-dados-abertos-jun-2023-a-jun-2025"
PKG_INSS_AGREGADO = "dados-agregados-da-folha-de-pagamento-beneficios-emitidos-plano-de-dados-abertos-jun-2023-a-jun-2027"

URL_BOLSA_FAMILIA = "https://portaldatransparencia.gov.br/download-de-dados/novo-bolsa-familia/{ref}"
URL_IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
URL_POPSVS = "ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPSVS/POPSBR{aa}.zip"
URL_SAGI = "https://aplicacoes.mds.gov.br/sagi/servicos/misocial"

FTP_RAIS = "ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/{ano}/"
RAIS_ARQUIVOS = [
    "RAIS_VINC_PUB_NORTE.7z", "RAIS_VINC_PUB_NORDESTE.7z", "RAIS_VINC_PUB_CENTRO_OESTE.7z",
    "RAIS_VINC_PUB_MG_ES_RJ.7z", "RAIS_VINC_PUB_SP.7z", "RAIS_VINC_PUB_SUL.7z",
    "RAIS_VINC_PUB_NI.7z",
]

CAMPOS_CADUNICO = [
    "codigo_ibge",
    "cadun_qtd_familias_cadastradas_i",
    "cadun_qtd_pessoas_cadastradas_i",
    "cadun_qtd_familias_cadastradas_baixa_renda_i",
    # pessoas em familias do Bolsa Familia -- numero publicado, nao estimativa.
    # Familias do BF sao maiores que a media do CadUnico (o programa foca familias com
    # criancas), entao derivar pessoas do tamanho medio geral subestima em ~18%.
    "cadunico_tot_pes_pbf_i",
    "pbf_media_pessoas_benef_f",
]

# ---------------------------------------------------------------- dominio
IDADE_ADULTA = 18   # denominador das taxas "por 100 adultos"

# Salario minimo nacional por ano, para os cortes da media da RAIS.
# 2025 confirmado empiricamente: R$ 1.518,00 e o valor mais frequente na folha do INSS
# de dezembro/2025, que e o piso previdenciario e portanto igual ao minimo.
SALARIO_MINIMO = {
    "2022": 1212.00, "2023": 1320.00, "2024": 1412.00, "2025": 1518.00,
}

# Faixa de remuneracao considerada no calculo da MEDIA salarial, em salarios minimos.
# Parametro da propria RAIS. Vale so para a media -- a massa salarial soma todo mundo,
# sem corte, porque massa e total e nao estimativa central.
FAIXA_MEDIA_SM = (0.7, 30.0)

def faixa_media_reais(ano: str) -> tuple[float, float]:
    sm = SALARIO_MINIMO.get(ano)
    if sm is None:
        raise SystemExit(f"salario minimo de {ano} nao cadastrado em config.SALARIO_MINIMO")
    return FAIXA_MEDIA_SM[0] * sm, FAIXA_MEDIA_SM[1] * sm

# Natureza juridica -- tabela oficial Concla/IBGE 2021, grupo 1 (Administracao Publica).
# Usado para separar a linha "salario -- administracao publica" da linha privada, e a
# esfera dentro dela. Conferido contra concla.ibge.gov.br em 15/08/2026.
NATUREZA_ESFERA = {
    "1015": "federal",   "1023": "estadual",  "1031": "municipal",  # orgao do executivo
    "1040": "federal",   "1058": "estadual",  "1066": "municipal",  # orgao do legislativo
    "1074": "federal",   "1082": "estadual",                        # orgao do judiciario
    "1104": "federal",   "1112": "estadual",  "1120": "municipal",  # autarquia
    "1139": "federal",   "1147": "estadual",  "1155": "municipal",  # fundacao dir. publico
    "1163": "federal",   "1171": "estadual",  "1180": "municipal",  # orgao publico autonomo
    "1198": "federal",                                              # comissao polinacional
    "1210": "outros",    "1228": "outros",                          # consorcio publico
    "1236": "estadual",  "1244": "municipal", "1341": "federal",    # Estado/DF, Municipio, Uniao
    "1252": "federal",   "1260": "estadual",  "1279": "municipal",  # fundacao dir. privado
    "1287": "federal",   "1295": "estadual",  "1309": "municipal",  # fundo publico indireto
    "1317": "federal",   "1325": "estadual",  "1333": "municipal",  # fundo publico direto
}

def classifica_setor(nat_jur: str) -> tuple[str, str | None]:
    """Retorna (setor, esfera). setor in {'publico','privado','ignorado'}.

    `1244` (Municipio) e `1333` (Fundo Publico da Administracao Direta Municipal) sao os
    codigos que carregam a folha das prefeituras -- o grosso da linha publica municipal.
    """
    nj = (nat_jur or "").strip().zfill(4)
    if nj in ("9999", "0000"):
        return "ignorado", None
    if nj.startswith("1"):
        return "publico", NATUREZA_ESFERA.get(nj, "outros")
    return "privado", None

# Municipios que o INSS ainda grafa com o nome antigo. Levantado no E1 comparando
# os codigos INSS sem par com os codigos IBGE ainda livres na mesma UF.
# Formato: (UF, nome como aparece no INSS) -> codigo IBGE de 7 digitos.
ALIAS_INSS_IBGE = {
    ("BA", "Muquém de S"): "2922250", ("BA", "Santa Teres"): "2928505",
    ("CE", "Itapagé"): "2306306",
    ("MG", "Barão de Mo"): "3105509", ("MG", "Brasópolis"): "3108909",
    ("MG", "Gouvêa"): "3127602",      ("MG", "Piuí"): "3151503",
    ("MG", "Queluzita"): "3153806",   ("MG", "Semixe"): "3165560",
    ("MS", "Bataiporã"): "5002001",
    ("MT", "Poxoréo"): "5107008",
    ("PA", "Mojoui dos"): "1504752",  ("PA", "Santa Isabe"): "1506500",
    ("PB", "Pedro Régio"): "2512721", ("PB", "Santarém"): "2513653",
    ("PB", "Seridó"): "2515401",
    ("PE", "Belém de Sã"): "2601607", ("PE", "Iguaraci"): "2606903",
    ("PE", "Itamaracá"): "2607604",   ("PE", "Lagoa do It"): "2608503",
    ("PR", "Vila Alta"): "4128625",
    ("RJ", "Armação de"): "3300233",  ("RJ", "Parati"): "3303807",
    ("RN", "Arês"): "2401206",        ("RN", "Augusto Sev"): "2401305",
    ("RN", "Açu"): "2400208",         ("RN", "Presidente"): "2410306",
    ("RO", "Jamari"): "1101104",
    ("RR", "São Luiz"): "1400605",
    ("RS", "Chiapeta"): "4305405",    ("RS", "Não-Meque"): "4312658",
    ("RS", "Santana do"): "4317103",
    ("SC", "Piçarras"): "4212809",
    ("SE", "Amparo de S"): "2800100", ("SE", "Gracho Card"): "2802601",
    ("SP", "Brodósqui"): "3507803",   ("SP", "Embu"): "3515004",
    ("SP", "Florínia"): "3516101",    ("SP", "Ipauçu"): "3520905",
    ("SP", "Moji das Cr"): "3530607", ("SP", "Moji-Guaçu"): "3530706",
    ("SP", "Moji-Mirim"): "3530805",  ("SP", "São Luís do"): "3550001",
    ("TO", "Couto de Ma"): "1706001", ("TO", "Fortaleza d"): "1708254",
}

# Municipios que o Portal da Transparencia grafa de forma que a similaridade nao alcanca:
# renomeacoes que mudam o nome inteiro ou acrescentam/removem varias palavras.
# Os outros ~26 casos de grafia antiga o 02_silver resolve sozinho por Jaro-Winkler.
# Formato: (UF, nome como aparece no Bolsa Familia) -> codigo IBGE de 7 digitos.
ALIAS_SIAFI_IBGE = {
    ("PB", "SERIDO"): "2515401",                                  # -> Sao Vicente do Serido
    ("RN", "ACU"): "2400208",                                     # -> Assu
    ("PE", "DISTRITO ESTADUAL DE FERNANDO DE NORONHA"): "2605459",
    ("TO", "FORTALEZA DO TABOCAO"): "1708254",                    # -> Tabocao
}

# Codigos do INSS que nao correspondem a municipio. Ficam fora do painel e entram
# na linha "nao alocado" da nota tecnica.
CODIGOS_INSS_NAO_MUNICIPIO = {"00000", "{ñ Class}"}

# ---------------------------------------------------------------- helpers
def normaliza(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", s).upper()).strip()

def chave11(s: str | None) -> str:
    """Chave de casamento com o nome truncado em 11 caracteres do microdado do INSS."""
    return normaliza(s)[:11].rstrip()

_t0 = time.time()

def log(msg: str) -> None:
    print(f"[{time.time() - _t0:7.1f}s] {msg}", flush=True)

def humano(n: int | float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or u == "GB":
            return f"{n:,.1f} {u}"
        n /= 1024
    return f"{n} B"
