#!/usr/bin/env python3
"""Enxame (beeswarm) e plano ("radar" de composição), direto de dados.json.

Reproduz em Python a mesma logica de enxame.js -- o algoritmo de empacotamento
do enxame e o posicionamento por quadrante do plano -- sem depender de
navegador nem D3. Usado por build.py para embutir esses dois graficos, ja
com a cidade-exemplo destacada, direto no HTML da porta de entrada.
"""
from __future__ import annotations

import math

MARGEM = {"topo": 10, "dir": 12, "baixo": 30, "esq": 12}
REF, R_MIN, R_MAX, FOLGA = 1400, 1.1, 6.0, 0.15
LARGURA = 900

ANCORAS = [
    {"chave": "previdencia", "ang": 45, "curto": "Previdência"},
    {"chave": "salario_privado", "ang": 135, "curto": "Salário privado"},
    {"chave": "salario_publico", "ang": 225, "curto": "Folha pública"},
    {"chave": "bolsa_familia", "ang": 315, "curto": "Bolsa Família"},
]
COR_FONTE = {
    "salario_privado": "var(--c-privado)", "salario_publico": "var(--c-publico)",
    "previdencia": "var(--c-prev)", "bolsa_familia": "var(--c-bf)",
}


def _fmt(v):
    return f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parte(dados, cod, chave):
    l = dados.get(cod, {}).get("linhas", {})
    return (l.get(chave) or {}).get("part", 0)


# ---------------------------------------------------------------- enxame (beeswarm)
def _empacotar(itens, folga):
    eps = 1e-3
    r_max = max((d["r"] for d in itens), default=1)
    itens.sort(key=lambda d: d["x"])
    ativos = []
    inicio = 0

    def bate(x, y, r):
        for a in ativos[inicio:]:
            dr = r + a["r"] + folga
            if dr * dr - eps > (a["x"] - x) ** 2 + (a["y"] - y) ** 2:
                return True
        return False

    for b in itens:
        while inicio < len(ativos) and ativos[inicio]["x"] < b["x"] - 2 * r_max - folga:
            inicio += 1
        if bate(b["x"], 0, b["r"]):
            melhor = math.inf
            for a in ativos[inicio:]:
                dr = b["r"] + a["r"] + folga
                dx = a["x"] - b["x"]
                base = dr * dr - dx * dx
                if base <= 0:
                    continue
                dy = math.sqrt(base)
                for y in (a["y"] + dy, a["y"] - dy):
                    if abs(y) < abs(melhor) and not bate(b["x"], y, b["r"]):
                        melhor = y
            b["y"] = melhor if math.isfinite(melhor) else 0
        else:
            b["y"] = 0
        ativos.append(b)
    return itens


def gera_enxame(dados: dict, indice: dict, alvo: str, fonte: str = "previdencia"):
    alvo_uf = indice[alvo]["uf"]
    todos = [cod for cod in indice if cod in dados and fonte in dados[cod].get("linhas", {})]
    max_pop = max(indice[cod]["pop"] for cod in todos) or 1

    escala = (LARGURA - MARGEM["esq"] - MARGEM["dir"]) / REF
    r_min, r_max = R_MIN * escala, R_MAX * escala

    def x_de(cod):
        return MARGEM["esq"] + _parte(dados, cod, fonte) * (LARGURA - MARGEM["esq"] - MARGEM["dir"])

    def r_de(cod):
        t = math.sqrt(indice[cod]["pop"] / max_pop) if max_pop else 0
        return max(r_min, r_min + t * (r_max - r_min))

    itens = [{"cod": cod, "x": x_de(cod), "r": r_de(cod)} for cod in todos]
    _empacotar(itens, FOLGA * escala)

    extremo = max((abs(d["y"]) + d["r"] for d in itens), default=10)
    altura = extremo * 2 + MARGEM["topo"] + MARGEM["baixo"] + 6
    meio = MARGEM["topo"] + extremo

    partes, alvo_item = [], None
    for d in itens:
        cod = d["cod"]
        cy = meio + d["y"]
        eh_alvo = cod == alvo
        if eh_alvo:
            fill, cls = "var(--alvo-cor)", "no alvo"
        else:
            mesma_uf = indice[cod]["uf"] == alvo_uf
            fill, cls = "var(--neutro)", "no" + ("" if mesma_uf else " apagado")
        partes.append(f'<circle class="{cls}" fill="{fill}" cx="{d["x"]:.2f}" cy="{cy:.2f}" r="{d["r"]:.2f}"/>')
        if eh_alvo:
            alvo_item = (d["x"], cy, d["r"])

    eixo = []
    y_eixo = altura - MARGEM["baixo"] + 8
    eixo.append(f'<line x1="{MARGEM["esq"]}" y1="{y_eixo}" x2="{LARGURA-MARGEM["dir"]}" y2="{y_eixo}" class="eixo-cruz" stroke-width="1"/>')
    for pct in (0, 20, 40, 60, 80, 100):
        tx = MARGEM["esq"] + (pct / 100) * (LARGURA - MARGEM["esq"] - MARGEM["dir"])
        eixo.append(f'<g transform="translate({tx:.1f},{y_eixo})"><line y2="6" stroke="currentColor"/>'
                     f'<text y="9" dy="0.71em" text-anchor="middle" fill="currentColor" font-size="10">{pct}%</text></g>')

    rotulo = ""
    if alvo_item:
        ax, ay, ar = alvo_item
        a_direita = ax < LARGURA / 2
        tx = ax + (ar + 6 if a_direita else -ar - 6)
        nome = f'{indice[alvo]["nome"]} ({indice[alvo]["uf"]})'
        rotulo = (f'<text class="rotulo-alvo" x="{tx:.1f}" y="{ay+4:.1f}" '
                  f'text-anchor="{"start" if a_direita else "end"}">{nome}</text>')

    return (
        f'<svg viewBox="0 0 {LARGURA} {altura:.0f}" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-label="Distribuição dos municípios brasileiros pela participação de previdência na renda registrada">'
        + "".join(partes) + "".join(eixo) + rotulo + "</svg>"
    )


# ---------------------------------------------------------------- plano ("radar")
def _posicao_plano(dados, cod, cx, cy, raio):
    partes_v = {a["chave"]: _parte(dados, cod, a["chave"]) for a in ANCORAS}
    i = max(range(4), key=lambda k: partes_v[ANCORAS[k]["chave"]])
    dom = ANCORAS[i]
    antes, depois = ANCORAS[(i - 1) % 4], ANCORAS[(i + 1) % 4]
    a, b = partes_v[antes["chave"]], partes_v[depois["chave"]]
    t = b / (a + b) if (a + b) > 0 else 0.5
    ang = math.radians((dom["ang"] - 45) + 90 * t)
    forca = min(1, max(0, (partes_v[dom["chave"]] - 0.25) / 0.75))
    r = raio * forca
    return cx + r * math.cos(ang), cy - r * math.sin(ang), dom["chave"]


def gera_plano(dados: dict, indice: dict, alvo: str):
    alvo_uf = indice[alvo]["uf"]
    lado = 470
    cx = cy = lado / 2
    raio = lado / 2 - 38

    todos = [cod for cod in indice if cod in dados and dados[cod].get("linhas")]
    max_pop = max(indice[cod]["pop"] for cod in todos) or 1

    def r_de(cod):
        t = math.sqrt(indice[cod]["pop"] / max_pop) if max_pop else 0
        return max(1.6, 1.6 + t * (9 - 1.6))

    contagem = {a["chave"]: 0 for a in ANCORAS}
    partes, alvo_item = [], None
    for cod in todos:
        x, y, dom = _posicao_plano(dados, cod, cx, cy, raio)
        mesma_uf = indice[cod]["uf"] == alvo_uf
        if mesma_uf:
            contagem[dom] += 1
        eh_alvo = cod == alvo
        r = r_de(cod)
        if eh_alvo:
            fill, cls = "var(--alvo-cor)", "no alvo"
        else:
            fill, cls = "var(--neutro)", "no" + ("" if mesma_uf else " apagado")
        partes.append(f'<circle class="{cls}" fill="{fill}" cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}"/>')
        if eh_alvo:
            alvo_item = (x, y, r)

    moldura = [
        f'<circle class="aro" cx="{cx}" cy="{cy}" r="{raio}"/>',
        f'<line class="eixo-cruz" x1="{cx-raio}" x2="{cx+raio}" y1="{cy}" y2="{cy}"/>',
        f'<line class="eixo-cruz" x1="{cx}" x2="{cx}" y1="{cy-raio}" y2="{cy+raio}"/>',
    ]
    for a in ANCORAS:
        dir_ = -1 if 90 < a["ang"] < 270 else 1
        cima = -1 if a["ang"] < 180 else 1
        x, y = cx + dir_ * raio, cy + cima * raio
        anchor = "start" if dir_ < 0 else "end"
        y1 = y - 8 if cima < 0 else y + 16
        y2 = y + 8 if cima < 0 else y + 30
        moldura.append(
            f'<g text-anchor="{anchor}">'
            f'<text class="rotulo-ancora" x="{x:.1f}" y="{y1:.1f}" fill="{COR_FONTE[a["chave"]]}">{a["curto"]}</text>'
            f'<text class="contagem-quad" x="{x:.1f}" y="{y2:.1f}">{_fmt(contagem[a["chave"]])} municípios</text>'
            "</g>"
        )

    rotulo = ""
    if alvo_item:
        x, y, r = alvo_item
        nome = f'{indice[alvo]["nome"]} ({indice[alvo]["uf"]})'
        a_esquerda = x > lado * 0.68
        tx = x - r - 6 if a_esquerda else x + r + 6
        anchor = "end" if a_esquerda else "start"
        rotulo = f'<text class="rotulo-alvo" x="{tx:.1f}" y="{y+4:.1f}" text-anchor="{anchor}">{nome}</text>'

    svg = (
        f'<svg viewBox="0 0 {lado} {lado}" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-label="Cada município posicionado pela fonte de renda que mais pesa nele">'
        '<g class="moldura">' + "".join(moldura) + "</g>"
        + "".join(partes) + rotulo + "</svg>"
    )
    return svg, contagem
