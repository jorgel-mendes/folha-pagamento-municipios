#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1", "numpy"]
# ///
"""Pre-calcula as posicoes do beeswarm do panorama nacional.

Por que no build e nao no navegador: sao 5.571 nos. Rodar `d3.forceSimulation` com
colisao no cliente custa segundos de CPU, trava a rolagem em celular e da um resultado
diferente a cada carga. Aqui o layout e resolvido uma vez, de forma deterministica, e o
navegador so desenha circulos em coordenadas prontas.

Isso tambem simplifica o D3 do lado do cliente: sobra escala, eixo e interacao --
que e a parte que vale aprender -- sem simulacao fisica no meio.

Gera site/posicoes.json com, para cada uma das quatro linhas de renda, a posicao de
cada municipio no enxame daquela linha.

Uso:
    uv run site/posicoes.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

AQUI = Path(__file__).resolve().parent
GOLD = AQUI.parent / "dados" / "gold"

LINHAS = ["salario_privado", "salario_publico", "previdencia", "bolsa_familia"]

# Espaco do desenho em unidades abstratas. O SVG escala isso para a largura real.
LARGURA = 1400.0
RAIO_MIN, RAIO_MAX = 1.1, 6.0

# As posicoes sao gravadas com uma casa decimal para o arquivo nao inchar. O empacotamento
# reserva essa folga, senao o proprio arredondamento reintroduz sobreposicao.
FOLGA = 0.15


def raio(pop: int, pop_max: int) -> float:
    """Area proporcional a populacao: raio pela raiz quadrada."""
    if pop <= 0:
        return RAIO_MIN
    return RAIO_MIN + (RAIO_MAX - RAIO_MIN) * (pop / pop_max) ** 0.5


def empilha(nos: list[dict]) -> None:
    """Beeswarm deterministico e exato.

    Para cada no, os vizinhos ja posicionados que se sobrepoem em x definem faixas de y
    proibidas. O no vai para o menor |y| fora dessas faixas -- o que da o empilhamento
    caracteristico do beeswarm, sem simulacao fisica e sem aleatoriedade: a mesma entrada
    sempre produz o mesmo desenho.

    A janela de vizinhos e limitada por geometria (so quem esta a menos de r_i + r_max em
    x pode colidir), entao o custo e proporcional a densidade local, nao a n^2.
    """
    nos.sort(key=lambda n: n["x"])
    # A janela so pode avancar, entao o corte precisa usar o alcance do MAIOR par
    # possivel (2 x RAIO_MAX). Cortar pelo raio do no atual descarta vizinhos que um
    # no maior mais adiante ainda precisaria consultar -- e ai sobra sobreposicao.
    alcance = 2 * RAIO_MAX + FOLGA
    inicio = 0
    for i, no in enumerate(nos):
        while nos[inicio]["x"] < no["x"] - alcance:
            inicio += 1

        proibidos = []
        for j in range(inicio, i):
            v = nos[j]
            soma = no["r"] + v["r"] + FOLGA
            dx = no["x"] - v["x"]
            if abs(dx) >= soma:
                continue
            dy = (soma * soma - dx * dx) ** 0.5
            proibidos.append((v["y"] - dy, v["y"] + dy))

        if not proibidos:
            no["y"] = 0.0
            continue

        # candidatos: o zero e as bordas de cada faixa proibida
        candidatos = [0.0]
        for lo, hi in proibidos:
            candidatos.append(lo)
            candidatos.append(hi)
        # a borda de um intervalo e posicao valida: encosta sem sobrepor. A tolerancia
        # precisa ser para dentro, senao rejeita exatamente as posicoes que procuramos.
        melhor = None
        for y in candidatos:
            if any(lo + 1e-9 < y < hi - 1e-9 for lo, hi in proibidos):
                continue
            if melhor is None or abs(y) < abs(melhor):
                melhor = y
        no["y"] = melhor if melhor is not None else 0.0


def main() -> None:
    painel = sorted(GOLD.glob("*/painel_municipal.parquet"))
    if not painel:
        raise SystemExit("painel nao encontrado -- rode pipeline/03_gold.py antes")
    fonte = painel[-1]

    con = duckdb.connect()
    cols = ", ".join(f"{c}_part" for c in LINHAS)
    registros = con.sql(f"""SELECT cod_ibge, pop_total, {cols}
                            FROM '{fonte}' WHERE massa_total > 0
                            ORDER BY cod_ibge""").fetchall()
    pop_max = max(r[1] or 1 for r in registros)

    # ordem canonica: todas as linhas usam os mesmos indices, entao ids e raios sao
    # gravados uma vez so. O raio depende apenas da populacao -- repeti-lo por linha
    # seria quatro copias do mesmo vetor.
    ids = [r[0] for r in registros]
    raios = [round(raio(r[1] or 0, pop_max), 1) for r in registros]
    pos = {i: k for k, i in enumerate(ids)}

    saida = {"largura": LARGURA, "ids": ids, "raios": raios, "linhas": {}}
    for i, chave in enumerate(LINHAS):
        nos = [{"id": r[0], "x": r[2 + i] * LARGURA, "r": raios[pos[r[0]]]}
               for r in registros if r[2 + i] is not None]
        empilha(nos)
        alcance = max(abs(n["y"]) + n["r"] for n in nos)

        # xy achatado na ordem canonica; municipio sem a linha fica como null
        xy: list[float | None] = [None] * (len(ids) * 2)
        for n in nos:
            k = pos[n["id"]] * 2
            xy[k], xy[k + 1] = round(n["x"], 1), round(n["y"], 1)
        saida["linhas"][chave] = {"altura": round(alcance * 2, 1), "xy": xy}
        print(f"{chave:<18} {len(nos):>5} municípios · altura {alcance * 2:6.1f}")

    destino = AQUI / "posicoes.json"
    destino.write_text(json.dumps(saida, separators=(",", ":")), "utf-8")
    bruto = destino.stat().st_size
    print(f"\nposicoes.json: {bruto / 1024:.0f} KB "
          f"(ids e raios uma vez; xy achatado por linha)")


if __name__ == "__main__":
    main()
