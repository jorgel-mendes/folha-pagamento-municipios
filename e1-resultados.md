# E1 — Resultados do spike de dados

**Data:** 15/08/2026 · **Status: PASSOU, com 4 achados que mudam o plano**

Executado de verdade sobre o microdado real do INSS de dezembro/2025 (41,6 milhões de registros).
Artefatos em `pipeline/inss_agrega_municipio.py` e `dados/interim/`.

---

## Veredito por assunção

| # | Assunção | Status |
|---|---|---|
| A1a | RAIS 2025 publicada com granularidade municipal | ✅ **CONFIRMADA** |
| A1b | INSS com 2025 completo por município de residência | ✅ **CONFIRMADA** |
| A1c | Bolsa Família com 2025 completo por município | ✅ **CONFIRMADA** (disponibilidade; schema pendente) |
| A2a | Massa em R$ aditiva | ✅ validada contra agregado oficial |
| A2d | INSS **não** tem chave de pessoa | ✅ **CONFIRMADA — dedup é impossível** |
| A5 | Cobertura de municípios pequenos | ✅ 5.569 de 5.570 no INSS |
| A10 | Denominador populacional por idade | ✅ DATASUS/TABNET + SIDRA 9514 |
| A9 | RAIS separa esfera pública | ⏳ pendente — microdado baixado, não inspecionado |
| A2c | CadÚnico dá tamanho médio de família | ⏳ pendente |

---

## Fontes confirmadas — endereços exatos

**RAIS 2025 — microdados**
`ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/2025/`
Arquivos `.7z`: `RAIS_ESTAB_PUB`, `RAIS_VINC_PUB_{SP, SUL, NORDESTE, NORTE, CENTRO_OESTE, MG_ES_RJ, NI}`.
Layouts em `ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/Layouts/`.

**INSS — Benefícios Emitidos (microdado mensal)**
API CKAN: `https://dadosabertos.inss.gov.br/api/3/action/package_show?id=beneficios-emitidos-plano-de-dados-abertos-jun-2023-a-jun-2025`
Padrão de URL: `.../Benefícios+emitidos/D.SDA.PDA.003.EMI.{AAAAMM}.CSV.ZIP`
Dez/2025: 578 MB zipado → **11,7 GB em CSV**, 41.641.943 linhas.

**INSS — agregado nacional por espécie (benchmark de validação)**
Dataset `dados-agregados-da-folha-de-pagamento-...-jun-2023-a-jun-2027`, XLSX de 6 KB por mês.

**Bolsa Família — Portal da Transparência**
`https://portaldatransparencia.gov.br/download-de-dados/novo-bolsa-familia/{AAAAMM}`
Dez/2025: 330 MB zipado. Responde 302 → 200.

**Denominadores** — DATASUS/TABNET (estimativas por município, sexo e faixa etária) e SIDRA
tabela 9514 (Censo 2022 por idade). PIB municipal do IBGE para sanidade.

---

## Achado 1 — Dezembro resolve o problema do volume

O microdado do INSS tem **11,7 GB por mês**. Doze meses seriam ~140 GB só do INSS, mais o Bolsa
Família. Como as três fontes têm estoque em dezembro — RAIS em 31/12, INSS na folha de dezembro,
BF no pagamento de dezembro — **dezembro/2025 como mês de referência único** alinha os períodos
naturalmente e reduz o pipeline em ~90%.

Fica pendente a confirmação de Q4 no briefing: dezembro tem 13º na RAIS e abono anual no INSS, e
precisamos decidir se isso torna o mês atípico.

## Achado 2 — Não existe chave de pessoa. A decisão de A2 está certa

Schema real do INSS, 14 colunas:

```
Despacho · Sexo · Clientela · Tipo Benefício · UF · Meio pagamento · Banco ·
Mun Pagto · Mun Resid · Vl Líquido · Ramo Atividade · Dt início validade ·
Espécie (código) · Espécie (nome)
```

Nenhum CPF, NIT, NIS ou hash. **Deduplicar benefícios por pessoa é impossível com o dado aberto** —
o que confirma a decisão de não somar pessoas entre fontes e apresentar taxas paralelas por 100
adultos.

## Achado 3 — Município de pagamento enviesaria 1 em cada 5 benefícios

**8.610.281 registros (20,7%) têm município de residência diferente do de pagamento.** O primeiro
registro do arquivo já mostra o caso: pago em Canapi (AL), residência em Capivari (SP).

Usar `Mun Pagto` inflaria municípios com agência bancária e esvaziaria os pequenos — exatamente os
que mais interessam ao projeto. **Usar sempre `Mun Resid`.**

## Achado 4 — Os códigos de município são do INSS, não do IBGE, e os nomes vêm truncados

O campo tem formato `CCCCC-UF-Nome` com o **nome truncado em 11 caracteres**:

```
05045-Ce-Fortaleza      09040-Ma-Fortaleza d      19238-Rs-Fortaleza d
11263-Mg-Fortaleza d    28095-To-Fortaleza d
```

Casar por nome puro é impossível. Testei a hipótese de que os códigos seguem ordem alfabética
dentro da UF — **refutada, mas de forma útil**: são alfabéticos até um marco histórico e depois
recebem municípios novos anexados no fim da sequência. No Acre, 24001–24025 vão de Assis Brasil a
Xapuri em ordem; 24026–24031 são Santa Rosa, Acrelândia, Bujari, Capixaba, Porto Walter e
Rodrigues Alves — todos criados nos anos 1990.

**Solução prática:** de-para por `(UF, primeiros 11 caracteres do nome normalizado)`. As colisões de
nome truncado são quase todas entre UFs diferentes, então a UF resolve. Sobra um resíduo pequeno
para tratar à mão. Prefixo de UF já identificado: `24`=AC, `27`=RR.

**Esta é a primeira tarefa do pipeline da semana 2.**

## Achado 5 — 1,1% dos benefícios não têm município

| Código | Benefícios | Massa |
|---|---|---|
| `00000-Zerada` | 456.810 (1,1%) | R$ 731 mi (1,0%) |
| `{ñ Class}` | 10 | ~0 |
| `16224-Rco do Piaui` | 866 | R$ 1,2 mi (código malformado) |

Precisa de tratamento explícito e de uma linha na nota técnica. Não distribuir proporcionalmente
entre municípios — declarar como não alocado.

## Achado 6 — E2 já passou para o INSS

Validação cruzada do microdado agregado contra o arquivo oficial de agregados nacionais,
espécie 01 (Pensão por Morte do Trabalhador Rural), dez/2025:

| | Quantidade | Valor |
|---|---|---|
| Microdado agregado por mim | 249.885 | R$ 340.856.972,11 |
| Agregado oficial do INSS | 249.885 | R$ 340.856.972,11 |

**Bate na casa dos centavos.** O pipeline de leitura está correto.

**Totais nacionais dez/2025:** 41.641.943 benefícios · R$ 74,19 bilhões líquidos ·
5.569 municípios com dado.

---

## Nova questão para a nota técnica (Q7)

O campo do INSS é **`Vl Líquido`** — já descontados consignado, imposto de renda e demais
descontos. A remuneração da RAIS é **bruta**. Somar as duas massas mistura líquido com bruto.

Três saídas: (a) usar líquido no INSS e bruto na RAIS, declarando a inconsistência; (b) procurar
valor bruto do benefício em outra fonte; (c) estimar o desconto médio e ajustar. A magnitude não
é desprezível — o crédito consignado do INSS é da ordem de dezenas de bilhões por ano.

**Adicionar como Q7 no briefing. É decisão do economista.**

---

## Detalhes de leitura do arquivo INSS

Para quem for reproduzir:

- Encoding **latin-1**, não UTF-8
- Separador `;`, campos com **padding de espaços** à direita (usar `trim`)
- Sem aspas — passar `quote=''` ao DuckDB
- Cabeçalho tem **`Espécie` duplicado** (código e nome) — ler posicionalmente
- Valores em formato brasileiro (`1.518,00`) — `replace('.','')` depois `replace(',','.')`
- Streaming funciona: `unzip -p arquivo.zip | duckdb` lendo `/dev/stdin` processa os 11,7 GB
  sem escrever em disco. 41,6 M de linhas, zero valores não parseados.

---

---

# Segunda rodada — pendências resolvidas

## De-para INSS→IBGE: 99,19% automático, validado

| Etapa | Resultado |
|---|---|
| Casamento por (UF, 11 primeiros caracteres) + ordem alfabética | 5.524 de 5.569 (**99,19%**) |
| Resíduo resolvido por tabela de alias | 45 municípios |
| **Cobertura final** | **100%** |

Validação independente: **correlação de 0,9907** entre a população do município atribuído e a
quantidade de benefícios (0,9442 em log). Se o de-para estivesse trocando municípios, a
correlação despencaria.

Os 45 resíduos são todos grafias antigas ou renomeações: Moji das Cruzes → Mogi das Cruzes,
Parati → Paraty, Açu → Assú, Brodósqui → Brodowski, Santarém (PB) → Joca Claudino,
Augusto Severo → Campo Grande, Fortaleza do Tabocão → Tabocão. Estão em
`config.ALIAS_INSS_IBGE`, e o silver imprime a linha pronta para colar se aparecer um novo.

## A9 confirmada — a RAIS separa a folha da prefeitura

Mas o formato da RAIS 2025 **mudou** em relação a anos anteriores:

| | RAIS 2025 |
|---|---|
| Extensão | `.COMT` dentro do `.7z` |
| Delimitador | **vírgula**, com aspas duplas |
| Decimal | **ponto** (`3009.56`) |
| Encoding | latin-1 |
| Município | `"Município - Código"`, IBGE de 6 dígitos |

Teste no Norte (5,6 M vínculos, 3,9 M ativos, 450 municípios):

| Setor | Vínculos ativos | Massa dez (R$ mi) |
|---|---|---|
| Público | 1.519.337 | 6.610,9 |
| Privado | 2.391.684 | 6.400,5 |

A natureza jurídica mais frequente no setor público do Norte é **`1244` — Município**
(665.771 vínculos), exatamente a folha das prefeituras. Tabela oficial Concla/IBGE 2021
conferida e carregada em `config.NATUREZA_ESFERA`.

**Achado colateral:** 20% dos vínculos ativos em 31/12 têm `Vl Rem Dezembro Nom` **em branco**.
Por isso o pipeline usa `Vl Rem Média Nom` como medida principal — que tem zero nulos e ainda
evita o problema do 13º de dezembro (Q4/Q5 do briefing). As duas medidas são gravadas.

## Bolsa Família — dois achados

Schema: `MÊS COMPETÊNCIA`, `MÊS REFERÊNCIA`, `UF`, `CÓDIGO MUNICÍPIO SIAFI`, `NOME MUNICÍPIO`,
`CPF FAVORECIDO` (mascarado), `NIS FAVORECIDO`, `NOME FAVORECIDO`, `VALOR PARCELA`.
2,06 GB descompactado.

**1. O NIS não vem mascarado.** Diferente do INSS, dá para contar famílias distintas —
`count(DISTINCT nis)` é a contagem correta de famílias, não o número de parcelas.

**2. O arquivo mistura competências.** O de dezembro/2025 contém parcelas com referência a
março, abril e outros meses — retroativos. "Famílias com benefício em dezembro" e "dinheiro do
BF que entrou no município em dezembro" são números diferentes. O pipeline calcula os dois.
Virou **Q8** no briefing.

**3. O código é SIAFI, não IBGE.** Mas os nomes vêm completos e sem truncar, então o de-para por
(UF, nome normalizado) é direto — muito mais simples que o do INSS.

## CadÚnico — A2c resolvida

API Solr do SAGI/MDS, sem chave de acesso:

```
https://aplicacoes.mds.gov.br/sagi/servicos/misocial?fq=anomes_s=202512&fq=tipo_s:mes_mu
```

O filtro correto é `tipo_s:mes_mu` (não `mun`). Devolve **5.571 municípios** com famílias e
pessoas cadastradas → tamanho médio de família por município, que é o que permite estimar
pessoas a partir de famílias no Bolsa Família.

## Denominador — A10 resolvida

DATASUS POPSVS, `ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPSVS/POPSBR25.zip`, 4,5 MB.
Contém `POP25.dbf` com `cod_mun`, `ano`, `sexo`, `idade`, `pop` — **idade ano a ano** até 80+,
e o código já vem em **7 dígitos IBGE**, sem necessidade de de-para.

Total: 5.571 municípios, 213.421.037 habitantes em 2025.

## Nova questão para a nota técnica (Q9)

A RAIS registra o vínculo no **município do estabelecimento**; o INSS registra o benefício no
**município de residência**. Em região metropolitana isso desloca massa salarial da
cidade-dormitório para a cidade-polo, enquanto a massa previdenciária fica na cidade-dormitório.

O efeito é sistemático e enviesa na direção de fazer periferias metropolitanas parecerem mais
"dependentes de transferências" do que são. Precisa de ressalva na própria página.
