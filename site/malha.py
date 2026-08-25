#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.31", "topojson>=1.9", "shapely>=2.0"]
# ///
"""Gera site/malha.topojson -- a malha municipal do IBGE, simplificada para o mapa.

Por que TopoJSON e nao GeoJSON: municipios vizinhos compartilham fronteira, e o TopoJSON
guarda cada fronteira uma vez so. Sao 655 KB em gzip contra 269 KB para o mesmo desenho.

A tolerancia de simplificacao e 0,04 grau, cerca de 4 km. Num mapa nacional de mil pixels
o Brasil ocupa uns 40 graus de largura, entao isso da meio pixel -- invisivel na tela e
tres vezes mais leve. Nao serve para calculo de area nem para zoom municipal.

O arquivo e carregado sob demanda pelo painel, so quando o usuario abre a vista de mapa.

SOBRE A ORIENTACAO DOS ANEIS
O d3-geo faz geometria esferica e le a orientacao do anel para saber onde fica o interior.
Anel externo na direcao errada vira o COMPLEMENTO do poligono: o municipio cobre o planeta
e pinta a tela inteira de uma cor so. A simplificacao inverte alguns poligonos pequenos --
tres, na malha atual -- e corrigir aqui nao adianta, porque a montagem da topologia
reescreve a orientacao de novo para poder compartilhar arcos entre vizinhos.

Por isso a correcao mora no cliente, em enxame.js: depois de converter para GeoJSON, ele
mede d3.geoArea de cada municipio e inverte os poucos que sairem invertidos. E a mesma
biblioteca que desenha julgando o proprio resultado, que e o unico juiz que importa.

Uso:
    uv run site/malha.py
"""
from __future__ import annotations

import gzip
from pathlib import Path

import requests
import topojson as tp

AQUI = Path(__file__).resolve().parent
URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
       "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio")
NAVEGADOR = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36")

TOLERANCIA = 0.04
QUANTIZACAO = 20_000


def main() -> None:
    print("baixando a malha municipal do IBGE ...")
    r = requests.get(URL, headers={"User-Agent": NAVEGADOR}, timeout=300)
    r.raise_for_status()
    bruto = r.json()
    print(f"  {len(bruto['features'])} municipios, {len(r.content) / 1e6:.1f} MB de GeoJSON")

    # so o codigo do IBGE interessa; o resto das propriedades e peso morto
    for f in bruto["features"]:
        f["properties"] = {"id": f["properties"]["codarea"]}

    topo = tp.Topology(bruto, prequantize=QUANTIZACAO,
                       toposimplify=TOLERANCIA, simplify_algorithm="dp")
    saida = topo.to_json()
    (AQUI / "malha.topojson").write_text(saida, "utf-8")

    comprimido = len(gzip.compress(saida.encode())) / 1024
    print(f"malha.topojson: {len(saida) / 1e6:.2f} MB | {comprimido:.0f} KB em gzip")
    print("  a orientacao dos aneis e conferida no cliente, em enxame.js")


if __name__ == "__main__":
    main()
