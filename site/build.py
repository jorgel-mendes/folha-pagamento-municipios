#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Monta site/index.html a partir de site/template.html.

O contracheque do municipio padrao vai **pre-renderizado no HTML**, entao a pagina
mostra conteudo real sem JavaScript. O app.js depois so troca os valores dentro da
estrutura ja existente -- nao existe markup duplicado entre Python e JavaScript.

Uso:
    uv run site/build.py [--municipio 3550308]
"""
from __future__ import annotations

import html
import hashlib
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PADRAO = "3550308"  # Sao Paulo: o maior, reconhecivel e sem carga narrativa

# (chave, rotulo, fonte). A ordem e a do contracheque e nunca muda.
LINHAS = [
    ("salario_privado", "Salário — setor privado",          "RAIS 2025"),
    ("salario_publico", "Salário — administração pública",  "RAIS 2025"),
    ("previdencia",     "Previdência — INSS e BPC",         "INSS"),
    ("bolsa_familia",   "Benefício social — Bolsa Família", "Portal da Transparência"),
]
UNIDADES = {"vinculos": "vínculos", "beneficios": "benefícios", "familias": "famílias"}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

TROCA = str.maketrans({",": ".", ".": ","})


# ------------------------------------------------------------------ formatacao
def num(v: float, casas: int = 0) -> str:
    """1234567.8 -> '1.234.567,8' (pt-BR)."""
    return f"{v:,.{casas}f}".translate(TROCA)


def compacto(v: float) -> str:
    """R$ 25,6 bi -- mesma regra do formatarMassa() em app.js."""
    for lim, suf in ((1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if abs(v) >= lim:
            return "R$ " + num(v / lim, 1) + suf
    return "R$ " + num(v)


def taxa(v: float) -> str:
    return num(v, 1)


def pct(v: float) -> str:
    return num(v * 100, 1) + "%"


# ------------------------------------------------------------------ renderizacao
def celula(col: str, grupo: str, conteudo: str) -> str:
    return f'<td data-col="{col}" data-grupo="{grupo}">{conteudo}</td>'


def linha_html(chave: str, rotulo: str, fonte: str, d: dict | None) -> str:
    """Sempre a mesma estrutura, presente ou ausente.

    A linha ausente usa os mesmos elementos com travessao no lugar do numero. Isso deixa
    o app.js apenas trocar textos, sem reconstruir markup -- que seria markup duplicado
    entre Python e JavaScript, com risco de divergir.
    """
    ausente = d is None
    unidade = "" if ausente else UNIDADES.get(d["unidade"], d["unidade"])
    v_n     = "—" if ausente else num(d["n"])
    v_por   = "—" if ausente else taxa(d["por100"])
    v_med   = "—" if ausente else "R$ " + num(d["medio"])
    v_massa = "—" if ausente else compacto(d["massa"])
    v_part  = "—" if ausente else pct(d["part"])
    largura = 0.0 if ausente else d["part"] * 100

    cab = (f'<th scope="row"><span class="linha-nome">{html.escape(rotulo)}</span>'
           f'<span class="linha-fonte">{html.escape(fonte)}</span></th>')
    pessoas = (f'<span class="valor" data-v="n">{v_n}</span>'
               f'<span class="unidade" data-v="unidade">{unidade}</span>')
    por100 = f'<span class="valor" data-v="por100">{v_por}</span>'
    medio = f'<span class="valor" data-v="medio">{v_med}</span>'
    massa = f'<span class="valor" data-v="massa">{v_massa}</span>'
    barra = (f'<span class="barra"><i data-v="barra" style="width:{largura:.2f}%"></i></span>'
             f'<span class="barra-pct" data-v="part">{v_part}</span>')

    attrs = f' data-ausente="sim" title="Sem dado publicado para este municipio nesta fonte"' if ausente else ""
    return (f'<tr data-linha="{chave}"{attrs}>{cab}'
            + celula("Pessoas", "pessoas", pessoas) + celula("Por 100 adultos", "pessoas", por100)
            + celula("Valor médio", "reais", medio) + celula("Massa no mês", "reais", massa)
            + celula("Participação", "reais", barra) + "</tr>")


def contracheque(mun: dict, dados: dict) -> str:
    ano, mes = dados["ref"].split("-")
    competencia = f"{MESES[int(mes) - 1]} de {ano}"
    nome = html.escape(mun["nome"])
    linhas = dados["linhas"]

    corpo = "".join(linha_html(k, rot, fon, linhas.get(k)) for k, rot, fon in LINHAS)
    bf_pessoas = linhas.get("bolsa_familia", {}).get("pessoas")
    nota_bf = (f' No município, <span data-v="bf-pessoas">{num(bf_pessoas)}</span> pessoas vivem '
               f'em famílias que recebem o Bolsa Família.' if bf_pessoas else "")

    return f"""
      <div class="holerite-topo">
        <div class="holerite-titulo">
          <p class="holerite-rotulo">Renda registrada do município</p>
          <p class="holerite-municipio"><span data-v="municipio">{nome}</span>
            <span class="holerite-uf" data-v="uf">({mun["uf"]})</span></p>
          <p class="holerite-meta"><span data-v="pop">{num(mun["pop"])}</span> habitantes ·
            <span data-v="pop18">{num(mun["pop18"])}</span> com 18 anos ou mais</p>
        </div>
        <p class="holerite-competencia">Competência<strong data-v="competencia">{competencia}</strong></p>
      </div>

      <div class="modos">
        <span class="rotulo" id="rot-modo">Destacar</span>
        <button type="button" data-modo="reais" aria-pressed="true" aria-describedby="rot-modo">Reais</button>
        <button type="button" data-modo="pessoas" aria-pressed="false" aria-describedby="rot-modo">Pessoas</button>
      </div>

      <table class="linhas">
        <caption>Cada fonte conta em uma unidade diferente, indicada na coluna Pessoas.
          Vínculos, benefícios e famílias não são a mesma coisa e não devem ser somados.</caption>
        <thead>
          <tr>
            <th scope="col">Fonte de renda</th>
            <th scope="col" class="num">Pessoas</th>
            <th scope="col" class="num">Por 100 adultos</th>
            <th scope="col" class="num">Valor médio</th>
            <th scope="col" class="num">Massa no mês</th>
            <th scope="col" class="num">Participação</th>
          </tr>
        </thead>
        <tbody>{corpo}</tbody>
      </table>

      <div class="total">
        <div class="total-linha">
          <span class="total-rotulo">Total da renda registrada</span>
          <span class="total-valor" data-v="total">{compacto(dados["massa_total"])}</span>
        </div>
        <p class="total-obs">Por mês, em reais correntes.
          Equivale a <span data-v="percapita">R$ {num(dados["massa_per_capita"])}</span> por habitante.{nota_bf}</p>
      </div>"""


def main() -> None:
    alvo = PADRAO
    if "--municipio" in sys.argv:
        alvo = sys.argv[sys.argv.index("--municipio") + 1]

    indice = {m["id"]: m for m in json.loads((AQUI / "municipios.json").read_text("utf-8"))}
    dados = json.loads((AQUI / "dados.json").read_text("utf-8"))
    if alvo not in indice or alvo not in dados:
        raise SystemExit(f"município {alvo} não está nos dados -- rode pipeline/03_gold.py antes")

    pagina = (AQUI / "template.html").read_text("utf-8").replace(
        "<!--CONTRACHEQUE-->", contracheque(indice[alvo], dados[alvo]))
    # Carimbo de versão nos assets. Sem isto, navegador e CDN do GitHub Pages seguem
    # servindo o CSS e o JS antigos depois de uma republicação -- o que já custou uma
    # sessão inteira de depuração de um bug que só existia no cache.
    versao = hashlib.sha1(
        b"".join((AQUI / n).read_bytes() for n in ("estilo.css", "app.js", "enxame.js"))
    ).hexdigest()[:8]
    for arquivo in ("estilo.css", "app.js", "enxame.js"):
        pagina = pagina.replace(f'"{arquivo}"', f'"{arquivo}?v={versao}"')
    pagina = pagina.replace("<body>", f'<body data-padrao="{alvo}" data-versao="{versao}">')
    (AQUI / "index.html").write_text(pagina, "utf-8")
    print(f"versao dos assets: {versao}")
    print(f"index.html gerado com {indice[alvo]['nome']} ({indice[alvo]['uf']}) "
          f"pre-renderizado - {len(pagina):,} bytes")


if __name__ == "__main__":
    main()
