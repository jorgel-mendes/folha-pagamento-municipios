# Pipeline — Folha de Pagamento dos Municípios

Medallion em três camadas e três scripts. Cada script roda sozinho, é idempotente e
recebe a competência por parâmetro, então atualizar para outro mês é uma linha.

```
dados/
├── bronze/                       cópia fiel da fonte, nada interpretado
│   ├── 202512/                   arquivos da competência
│   ├── estatico/                 IBGE municípios, população DATASUS
│   └── rais_2025/                microdados anuais da RAIS
├── silver/202512/                uma tabela por fonte, chave cod_ibge de 7 dígitos
└── gold/202512/                  painel municipal + validação + dicionário
site/                             municipios.json e dados.json consumidos pela página
```

## Rodando

```bash
uv run pipeline/01_bronze.py
```

```bash
uv run pipeline/02_silver.py
```

```bash
uv run pipeline/03_gold.py
```

Os scripts declaram as próprias dependências (PEP 723), então o `uv run` resolve o
ambiente sozinho — não existe `requirements.txt` para manter.

### Atualizando para outra competência

```bash
uv run pipeline/01_bronze.py --ref 202606 && uv run pipeline/02_silver.py --ref 202606 && uv run pipeline/03_gold.py --ref 202606
```

Cada competência vive no próprio diretório, então as anteriores continuam intactas e
dá para comparar meses sem reprocessar nada.

### Parâmetros

| Flag | Camada | Efeito |
|---|---|---|
| `--ref AAAAMM` | todas | competência a processar (padrão em `config.py`) |
| `--force` | bronze | rebaixa arquivos já existentes |
| `--sem-rais` | bronze, silver | pula a RAIS (~3,9 GB de download) |
| `--so fonte1,fonte2` | silver | processa só as fontes listadas (`inss`, `bf`, `cadunico`, `rais`) |

Também dá para fixar por variável de ambiente: `FPM_REF`, `FPM_ANO_RAIS`.

## O que cada camada faz

### 01_bronze.py — baixar

Nada aqui interpreta o dado. O objetivo é ter uma cópia datada da fonte, para que o
pipeline continue reprodutível mesmo que o órgão republique o arquivo.

A URL do INSS é resolvida via API CKAN em vez de montada na mão, porque o padrão de
nome mudou entre meses (`.CSV.ZIP` virou `.zip` em 2026).

Downloads são idempotentes: arquivo existente com o tamanho esperado é pulado.

### 02_silver.py — normalizar

Cada fonte vira um parquet independente com chave `cod_ibge` de 7 dígitos. Nenhuma
junção entre fontes acontece aqui.

O trabalho pesado é a reconciliação de códigos de município, porque **cada fonte usa um
código diferente**:

| Fonte | Código | Solução |
|---|---|---|
| INSS | código próprio, nome truncado em 11 caracteres | de-para por (UF, prefixo) + ordem alfabética + tabela de alias |
| Bolsa Família | SIAFI | exato por (UF, nome) + similaridade dentro da UF |
| CadÚnico | IBGE de 6 dígitos | prefixo do código de 7 |
| RAIS | IBGE de 6 dígitos | prefixo do código de 7 |
| População DATASUS | IBGE de 7 dígitos | direto |

O de-para do INSS resolve ~99,2% automaticamente; o resíduo são grafias antigas
(Moji das Cruzes, Parati, Açu) e está em `config.ALIAS_INSS_IBGE`. Se um mês novo trouxer
código sem par, o script imprime a linha pronta para colar no dicionário. Precisa de tabela
manual porque o nome vem truncado em 11 caracteres — não há texto suficiente para casar sozinho.

O do Bolsa Família **não precisa de tabela manual**: os nomes vêm completos, então uma segunda
passada por similaridade (Jaro-Winkler ≥ 0,85), restrita à mesma UF e só entre os municípios
ainda livres dos dois lados, resolve as grafias antigas sozinha e sobrevive a meses futuros.
O log mostra cada casamento aproximado com o score, para auditoria.

### 03_gold.py — juntar e publicar

Monta o painel municipal, gera o dicionário de dados, roda a validação contra os
agregados oficiais e exporta os JSON do site.

**A regra que atravessa esta camada: massa em R$ soma, contagem de pessoas não soma.**
Cada linha carrega sua unidade (vínculo, benefício, família) e o painel não produz total
de pessoas — o campo simplesmente não existe no JSON, para que ninguém o some depois.

## Armadilha de performance: UDF Python antes de reduzir

O DuckDB não sabe que uma função registrada com `create_function` é cara. Se ela aparecer numa
expressão avaliada antes do `DISTINCT` ou dentro de um `GROUP BY`, ela roda **uma vez por linha**
— e as tabelas de origem aqui têm dezenas de milhões de linhas.

Isso derrubou o pipeline três vezes durante o desenvolvimento: 31 min no INSS, 9 min na RAIS,
3 min no Bolsa Família. Todos viraram segundos com a mesma correção.

```sql
-- lento: k11() roda 41.641.943 vezes
SELECT DISTINCT substr(mun,1,5), k11(substr(mun,10)) FROM inss_bruto

-- rápido: k11() roda 5.569 vezes
SELECT cod_inss, k11(nome) FROM (SELECT DISTINCT substr(mun,1,5) cod_inss, ... FROM inss_bruto)
```

A regra: **reduza primeiro, aplique a UDF depois.** Quando não dá para reduzir — o caso do
`setor`/`esfera` no `GROUP BY` da RAIS — materialize uma dimensão pequena com os valores
distintos e troque a UDF por um `JOIN` nativo.

## Decisões que ainda dependem do economista

Estão marcadas no código e detalhadas em [briefing-nota-tecnica.md](../briefing-nota-tecnica.md):

- **Q4/Q5** — dezembro tem 13º na RAIS e abono no INSS. O silver grava as duas medidas
  (`massa_salarial` da remuneração média e `massa_dezembro`) e o gold usa a média por
  padrão, que evita o 13º e cobre os ~20% de vínculos ativos sem remuneração de dezembro.
- **Q7** — o INSS publica valor **líquido** e a RAIS publica **bruto**. O painel soma os
  dois hoje; a nota técnica precisa declarar ou corrigir.
- **Q8** — o arquivo do Bolsa Família mistura competências: o pagamento de dezembro inclui
  parcelas referentes a meses anteriores. O silver grava as duas leituras (`_ref` e
  `_comp`) e o gold usa `_ref`.
- **Q9** — a RAIS localiza a renda no **município do estabelecimento** e o INSS no
  **município de residência**. Em região metropolitana isso desloca massa salarial da
  cidade-dormitório para a cidade-polo.

## Custo e tempo

| Fonte | Download | Descompactado |
|---|---|---|
| INSS (1 mês) | 578 MB | 11,7 GB (lido em streaming, não vai para disco) |
| Bolsa Família (1 mês) | 330 MB | 2,1 GB (streaming) |
| RAIS (ano) | 3,9 GB | ~35 GB (extraído em disco) |
| População + IBGE | 7 MB | — |
| CadÚnico | < 1 MB | — |

Reserve ~45 GB livres para rodar com a RAIS completa. Sem ela (`--sem-rais`), ~1 GB.
