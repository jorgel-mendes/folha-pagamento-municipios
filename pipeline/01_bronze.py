#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.31"]
# ///
"""CAMADA BRONZE -- baixa os arquivos originais, sem transformar nada.

Nada aqui interpreta o dado. O objetivo e ter uma copia fiel e datada da fonte,
para que o pipeline seja reprodutivel mesmo que o orgao republique o arquivo depois.

Uso:
    uv run pipeline/01_bronze.py                  # competencia padrao (config.REF_PADRAO)
    uv run pipeline/01_bronze.py --ref 202606     # outra competencia
    uv run pipeline/01_bronze.py --force          # rebaixa o que ja existe
    uv run pipeline/01_bronze.py --sem-rais       # pula a RAIS (~3,9 GB)

E idempotente: arquivo ja baixado com o tamanho esperado e pulado.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import config as C  # noqa: E402


def baixa_http(url: str, destino: Path, force: bool = False) -> Path:
    if destino.exists() and not force:
        try:
            r = requests.head(url, allow_redirects=True, timeout=60)
            esperado = int(r.headers.get("content-length", 0))
        except Exception:
            esperado = 0
        if esperado == 0 or destino.stat().st_size == esperado:
            C.log(f"  ja existe, pulando: {destino.name} ({C.humano(destino.stat().st_size)})")
            return destino
        C.log(f"  tamanho divergente, rebaixando: {destino.name}")

    C.log(f"  baixando {destino.name} ...")
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.replace(destino)
    C.log(f"  ok: {destino.name} ({C.humano(destino.stat().st_size)})")
    return destino


def baixa_ftp(url: str, destino: Path, force: bool = False) -> Path:
    """FTP via curl -- requests nao fala ftp://."""
    if destino.exists() and not force:
        C.log(f"  ja existe, pulando: {destino.name} ({C.humano(destino.stat().st_size)})")
        return destino
    C.log(f"  baixando (ftp) {destino.name} ...")
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    subprocess.run(["curl", "-sS", "-L", "--max-time", "3600", "-o", str(tmp), url], check=True)
    tmp.replace(destino)
    C.log(f"  ok: {destino.name} ({C.humano(destino.stat().st_size)})")
    return destino


MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def url_recurso_inss(pacote: str, ref: str, por_nome: bool = False) -> str:
    """Resolve a URL do mes pedido no CKAN do INSS.

    Duas formas de casar, porque os dois pacotes nomeiam diferente:
      - microdado: a competencia esta na URL (`...EMI.202512.CSV.ZIP`)
      - agregado nacional: a URL traz a **data de extracao**, nao a competencia
        (`p_benefemitidos..._20260106_121803.xlsx`). So o campo `name` diz o mes
        ("... - dezembro 2025"), entao e por ele que casamos.
    Casar o agregado pela URL pega o mes errado em silencio -- foi o que aconteceu
    e o que a validacao do 03_gold pegou.
    """
    r = requests.get(C.CKAN_INSS, params={"id": pacote}, timeout=120)
    r.raise_for_status()
    recursos = r.json()["result"]["resources"]

    if por_nome:
        alvo_txt = f"{MESES[int(ref[4:6]) - 1]} {ref[:4]}"
        alvos = [x for x in recursos if alvo_txt in (x.get("name") or "").lower()]
        disponiveis = sorted({(x.get("name") or "").split(" - ")[-1] for x in recursos})
    else:
        alvos = [x for x in recursos if ref in (x.get("url") or "")]
        disponiveis = sorted({u[-16:-4] for u in (x.get("url") or "" for x in recursos) if u})

    if not alvos:
        raise SystemExit(f"competencia {ref} nao encontrada em {pacote}.\n"
                         f"Disponiveis: {disponiveis[-6:]}")
    if len(alvos) > 1:
        raise SystemExit(f"competencia {ref} casou com {len(alvos)} recursos em {pacote} -- "
                         f"ambiguo, confira o catalogo antes de seguir")
    return alvos[0]["url"]


def baixa_cadunico(ref: str, destino: Path, force: bool = False) -> Path:
    """CadUnico agregado por municipio, via API Solr do SAGI/MDS."""
    if destino.exists() and not force:
        C.log(f"  ja existe, pulando: {destino.name}")
        return destino
    C.log("  consultando SAGI/MDS ...")
    r = requests.get(C.URL_SAGI, params={
        "q": "*:*", "fq": [f"anomes_s:{ref}", "tipo_s:mes_mu"],
        "fl": ",".join(C.CAMPOS_CADUNICO), "wt": "csv", "rows": 6000,
    }, timeout=180)
    r.raise_for_status()
    linhas = r.text.strip().splitlines()
    if len(linhas) <= 1:
        raise SystemExit(f"SAGI devolveu vazio para {ref}. O CadUnico costuma ter defasagem -- "
                         f"confira a competencia disponivel antes de seguir.")
    destino.write_text(r.text, encoding="utf-8")
    C.log(f"  ok: {destino.name} ({len(linhas) - 1} municipios)")
    return destino


def main() -> None:
    ref = C.ref_do_argv()
    ano = C.ano_rais(ref)
    force = C.tem_flag("--force")
    sem_rais = C.tem_flag("--sem-rais")
    dst = C.dir_camada(C.BRONZE, ref)
    est = C.BRONZE / "estatico"
    est.mkdir(parents=True, exist_ok=True)

    C.log(f"BRONZE | competencia={ref} | ano RAIS={ano} | destino={dst}")

    C.log("1/6 INSS -- beneficios emitidos (microdado)")
    baixa_http(url_recurso_inss(C.PKG_INSS_EMITIDOS, ref), dst / f"inss_emitidos_{ref}.zip", force)

    C.log("2/6 INSS -- agregado nacional por especie (benchmark de validacao)")
    try:
        baixa_http(url_recurso_inss(C.PKG_INSS_AGREGADO, ref, por_nome=True), dst / f"inss_agregado_{ref}.xlsx", force)
    except SystemExit as e:
        C.log(f"  AVISO: agregado indisponivel ({e}). A validacao do 03_gold ficara sem benchmark.")

    C.log("3/6 Bolsa Familia -- Portal da Transparencia")
    baixa_http(C.URL_BOLSA_FAMILIA.format(ref=ref), dst / f"bolsa_familia_{ref}.zip", force)

    C.log("4/6 CadUnico -- agregado municipal (SAGI/MDS)")
    baixa_cadunico(ref, dst / f"cadunico_{ref}.csv", force)

    C.log("5/6 IBGE municipios + populacao DATASUS por idade")
    r = requests.get(C.URL_IBGE_MUNICIPIOS, timeout=180)
    r.raise_for_status()
    (est / "ibge_municipios.json").write_text(
        json.dumps(r.json(), ensure_ascii=False), encoding="utf-8")
    C.log(f"  ok: ibge_municipios.json ({len(r.json())} municipios)")
    baixa_ftp(C.URL_POPSVS.format(aa=ano[2:]), est / f"POPSBR{ano[2:]}.zip", force)

    if sem_rais:
        C.log("6/6 RAIS -- pulada (--sem-rais)")
    else:
        C.log(f"6/6 RAIS {ano} -- microdados de vinculos (~3,9 GB, sete arquivos)")
        drais = C.BRONZE / f"rais_{ano}"
        drais.mkdir(parents=True, exist_ok=True)
        for nome in C.RAIS_ARQUIVOS:
            baixa_ftp(C.FTP_RAIS.format(ano=ano) + nome, drais / nome, force)

    total = sum(f.stat().st_size for f in C.BRONZE.rglob("*") if f.is_file())
    C.log(f"BRONZE concluida. Total em disco: {C.humano(total)}")
    C.log("Proximo passo: uv run pipeline/02_silver.py --ref " + ref)


if __name__ == "__main__":
    main()
