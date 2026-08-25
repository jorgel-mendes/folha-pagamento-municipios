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


PORTES = [("ate_5k", "até 5 mil habitantes"), ("5k_20k", "5 a 20 mil"),
          ("20k_100k", "20 a 100 mil"), ("100k_mais", "100 mil ou mais")]


def estatisticas(indice: dict, dados: dict) -> dict:
    """Números da página de entrada, calculados a partir do próprio painel.

    Ficam fora do texto de propósito. Escrever à mão significa que uma correção no
    pipeline não chega à manchete -- foi o que aconteceu quando o de-para do Bolsa
    Família subiu para 100% e o número da abertura ficou defasado sem ninguém notar.
    """
    porte = {p: [0, 0] for p, _ in PORTES}
    norte = [0, 0]
    for cod, d in dados.items():
        m = indice.get(cod)
        if not m or not d.get("massa_total"):
            continue
        massa = lambda k: (d["linhas"].get(k) or {}).get("massa", 0)
        if m["porte"] in porte:
            porte[m["porte"]][1] += 1
            if massa("previdencia") + massa("bolsa_familia") > massa("salario_privado"):
                porte[m["porte"]][0] += 1
        if m["regiao"] == "N":
            norte[1] += 1
            publico = d["linhas"].get("salario_publico") or {}
            if "massa_municipal" not in publico and publico:
                raise SystemExit(
                    "dados.json sem 'massa_municipal' -- rode pipeline/03_gold.py de novo. "
                    "A página de entrada não publica esse número estimado ou desatualizado.")
            if publico.get("massa_municipal", 0) > max(
                    massa("salario_privado"), massa("previdencia"), massa("bolsa_familia")):
                norte[0] += 1
    return {"porte": porte, "norte": norte}


def proporcao(parte: int, todo: int) -> str:
    """Participação de `parte` em `todo`, já formatada em pt-BR."""
    return f"{100 * parte / todo:.1f}".translate(TROCA) + "%" if todo else "—"


def achado(est: dict) -> str:
    maior, total = est["porte"]["ate_5k"]
    n_maior, n_total = est["norte"]
    return (f"Em <strong>{proporcao(maior, total)}</strong> dos municípios com menos de 5 mil "
            f"habitantes, aposentadorias e Bolsa Família somados movimentam mais dinheiro que "
            f"toda a massa salarial do setor privado. E a folha da prefeitura é a maior fonte "
            f"isolada de renda em <strong>{proporcao(n_maior, n_total)}</strong> dos municípios do Norte.")


def tabela_porte(est: dict) -> str:
    corpo = "\n".join(
        f'        <tr><th scope="row">{rot}</th>'
        f'<td class="num">{num(est["porte"][ch][1])}</td>'
        f'<td class="num">{num(est["porte"][ch][0])}</td>'
        f'<td class="num destaque">{proporcao(*est["porte"][ch])}</td></tr>'
        for ch, rot in PORTES)
    return ('    <table class="tabela-porte">\n'
            '      <thead><tr><th scope="col">Porte do município</th>'
            '<th scope="col" class="num">Municípios</th>'
            '<th scope="col" class="num">Com transferências maiores</th>'
            '<th scope="col" class="num">Proporção</th></tr></thead>\n'
            f'      <tbody>\n{corpo}\n      </tbody>\n    </table>')


def main() -> None:
    alvo = PADRAO
    if "--municipio" in sys.argv:
        alvo = sys.argv[sys.argv.index("--municipio") + 1]

    indice = {m["id"]: m for m in json.loads((AQUI / "municipios.json").read_text("utf-8"))}
    dados = json.loads((AQUI / "dados.json").read_text("utf-8"))
    if alvo not in indice or alvo not in dados:
        raise SystemExit(f"município {alvo} não está nos dados -- rode pipeline/03_gold.py antes")

    # Carimbo de versão nos assets. Sem isto, navegador e CDN do GitHub Pages seguem
    # servindo o CSS e o JS antigos depois de uma republicação -- o que já custou uma
    # sessão inteira de depuração de um bug que só existia no cache.
    versao = hashlib.sha1(
        b"".join((AQUI / n).read_bytes() for n in ("estilo.css", "app.js", "enxame.js"))
    ).hexdigest()[:8]

    def monta(modelo: str, saida: str, corpo: dict[str, str], atributos: str = "") -> int:
        pagina = (AQUI / modelo).read_text("utf-8")
        for marca, valor in corpo.items():
            pagina = pagina.replace(marca, valor)
        for arquivo in ("estilo.css", "app.js", "enxame.js"):
            pagina = pagina.replace(f'"{arquivo}"', f'"{arquivo}?v={versao}"')
        pagina = pagina.replace("<body>", f'<body data-versao="{versao}"{atributos}>')
        (AQUI / saida).write_text(pagina, "utf-8")
        return len(pagina)

    est = estatisticas(indice, dados)
    ref = dados[alvo]["ref"]
    referencia = f"{MESES[int(ref[5:7]) - 1]} de {ref[:4]}"

    n_porta = monta("inicio-template.html", "index.html", {
        "<!--ACHADO-->": achado(est),
        "<!--TABELA-PORTE-->": tabela_porte(est),
        "<!--REFERENCIA-->": referencia,
    })
    n_painel = monta("painel-template.html", "painel.html", {
        "<!--CONTRACHEQUE-->": contracheque(indice[alvo], dados[alvo]),
    }, atributos=f' data-padrao="{alvo}"')

    maior, total = est["porte"]["ate_5k"]
    print(f"versao dos assets: {versao}")
    print(f"index.html   porta de entrada - {n_porta:,} bytes "
          f"(ate 5 mil hab.: {maior}/{total} = {proporcao(maior, total)})")
    print(f"painel.html  {indice[alvo]['nome']} ({indice[alvo]['uf']}) "
          f"pre-renderizado - {n_painel:,} bytes")


if __name__ == "__main__":
    main()
