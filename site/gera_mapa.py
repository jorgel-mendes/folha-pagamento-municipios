#!/usr/bin/env python3
"""Mapa de fonte dominante, direto do malha.topojson -- sem depender de navegador nem D3.

Reproduz em Python a mesma logica de enxame.js (vista=mapa): projecao Mercator
ajustada (fitSize) ao recorte escolhido, cada municipio pintado pela fonte que
mais pesa na sua renda registrada. Usado por build.py para embutir o mapa
(Brasil inteiro e um zoom no estado da cidade-exemplo) direto no HTML da porta
de entrada -- sem JavaScript, como o resto da pagina.
"""
from __future__ import annotations

import math
from pathlib import Path

CHAVES = ["salario_privado", "salario_publico", "previdencia", "bolsa_familia"]
COR_VAR = {
    "salario_privado": "var(--c-privado)",
    "salario_publico": "var(--c-publico)",
    "previdencia": "var(--c-prev)",
    "bolsa_familia": "var(--c-bf)",
}
def _dequantiza_arcos(topo):
    escala = topo["transform"]["scale"]
    desloca = topo["transform"]["translate"]
    arcos = []
    for arco in topo["arcs"]:
        pontos = []
        x = y = 0
        for dx, dy in arco:
            x += dx
            y += dy
            pontos.append((x * escala[0] + desloca[0], y * escala[1] + desloca[1]))
        arcos.append(pontos)
    return arcos


def _monta_anel(indices, arcos):
    anel = []
    for i in indices:
        pontos = arcos[i] if i >= 0 else list(reversed(arcos[~i]))
        anel.extend(pontos[1:] if anel else pontos)
    return anel


def _aneis_da_geometria(geom, arcos):
    if geom["type"] == "Polygon":
        return [[_monta_anel(anel, arcos) for anel in geom["arcs"]]]
    if geom["type"] == "MultiPolygon":
        return [[_monta_anel(anel, arcos) for anel in poligono] for poligono in geom["arcs"]]
    raise ValueError(geom["type"])


def _mercator(lon, lat):
    x = math.radians(lon)
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, -y  # nega y: latitude maior (norte) fica mais acima na tela


def dominante(linhas):
    massas = {k: (linhas.get(k) or {}).get("massa", 0) for k in CHAVES}
    return max(massas, key=massas.get)


def _carrega_projetadas(topo, dados, indice, filtro_uf=None):
    arcos = _dequantiza_arcos(topo)
    geometrias = topo["objects"]["data"]["geometries"]
    projetadas = []
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for geom in geometrias:
        cod = geom["properties"]["id"]
        if cod not in dados or not dados[cod].get("massa_total"):
            continue
        if filtro_uf and indice.get(cod, {}).get("uf") != filtro_uf:
            continue
        poligonos = [
            [[_mercator(lon, lat) for lon, lat in anel] for anel in poligono]
            for poligono in _aneis_da_geometria(geom, arcos)
        ]
        for poligono in poligonos:
            for anel in poligono:
                for x, y in anel:
                    minx, maxx = min(minx, x), max(maxx, x)
                    miny, maxy = min(miny, y), max(maxy, y)
        projetadas.append((cod, poligonos))
    return projetadas, (minx, miny, maxx, maxy)


def _gera_svg(projetadas, bbox, dados, largura, altura, marcador_id):
    minx, miny, maxx, maxy = bbox
    alvo_w, alvo_h = largura - 8, altura - 8
    bbox_w, bbox_h = maxx - minx, maxy - miny
    escala = min(alvo_w / bbox_w, alvo_h / bbox_h)
    off_x = (alvo_w - bbox_w * escala) / 2 - minx * escala
    off_y = (alvo_h - bbox_h * escala) / 2 - miny * escala

    def para_px(x, y):
        return (x * escala + off_x + 4, y * escala + off_y + 4)

    contagem = {k: 0 for k in CHAVES}
    paths = []
    marcador_px = None
    for cod, poligonos in projetadas:
        dom = dominante(dados[cod]["linhas"])
        contagem[dom] += 1
        d = []
        maior_anel = max((anel for poligono in poligonos for anel in poligono), key=len)
        for poligono in poligonos:
            for anel in poligono:
                px = [para_px(x, y) for x, y in anel]
                d.append("M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in px) + "Z")
        paths.append(f'<path class="area" fill="{COR_VAR[dom]}" d="{"".join(d)}"/>')
        if marcador_id and cod == marcador_id:
            pxs = [para_px(x, y) for x, y in maior_anel]
            marcador_px = (sum(p[0] for p in pxs) / len(pxs), sum(p[1] for p in pxs) / len(pxs))

    marcador_svg = ""
    if marcador_px:
        mx, my = marcador_px
        marcador_svg = (
            '<g class="marcador-cidade">'
            f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="11" fill="none" stroke="var(--destaque)" stroke-width="1.5" opacity="0.55"/>'
            f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="4" fill="var(--destaque)" stroke="var(--papel)" stroke-width="1.2"/>'
            "</g>"
        )

    svg = (
        f'<svg viewBox="0 0 {largura} {altura}" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-label="Mapa colorido pela fonte de renda que mais pesa em cada município">'
        + "".join(paths) + marcador_svg + "</svg>"
    )
    return svg, contagem


def estatisticas_dominante(contagem):
    """[(chave, contagem, percentual)], ordenado do maior para o menor."""
    total = sum(contagem.values())
    itens = sorted(contagem.items(), key=lambda kv: -kv[1])
    return [(k, v, 100 * v / total if total else 0) for k, v in itens]


def gerar(topo: dict, dados: dict, indice: dict, exemplo_id: str, exemplo_uf: str):
    """Devolve (svg_brasil, stats_brasil, svg_uf, stats_uf)."""
    proj, bbox = _carrega_projetadas(topo, dados, indice)
    svg_brasil, contagem_brasil = _gera_svg(proj, bbox, dados, 900, 500, exemplo_id)

    proj_uf, bbox_uf = _carrega_projetadas(topo, dados, indice, filtro_uf=exemplo_uf)
    svg_uf, contagem_uf = _gera_svg(proj_uf, bbox_uf, dados, 700, 560, exemplo_id)

    return (
        svg_brasil, estatisticas_dominante(contagem_brasil),
        svg_uf, estatisticas_dominante(contagem_uf),
    )
