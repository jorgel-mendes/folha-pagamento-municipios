# Plano de Discovery — Folha de Pagamento dos Municípios

**Data:** 15/08/2026 · **Revisão 2**
**Estágio:** produto novo (entrega única para concurso)
**Equipe:** Jorge (engenheiro de dados — pipeline, viz) + irmão (economista — metodologia, nota técnica)
**Alvo:** 2º Concurso de Reúso de Dados Abertos da CGU — Edital CGU nº 46/2026
**Prazo de inscrição:** 11/09/2026 (data-alvo interna: 08/09)
**Ano de referência:** 2025

**Pergunta de discovery:** É possível montar, em 27 dias, um painel exploratório que mostre a
composição da renda registrada de cada município brasileiro — salário privado, folha pública,
previdência e benefício social — e que permita identificar quais municípios estão mais expostos
a mudanças de regra em cada uma dessas fontes?

---

## 1. Contexto do concurso

### Cronograma oficial

| Etapa | Data |
|---|---|
| Inscrições | 29/06/2026 a **11/09/2026** |
| Resultado preliminar de admissibilidade | 25/09/2026 |
| Recursos (admissibilidade) | 28/09 a 02/10/2026 |
| Lista final de admitidos | 12/10/2026 |
| Resultado preliminar do julgamento | 13/11/2026 |
| Recursos (julgamento) | 16 a 20/11/2026 |
| **Resultado final** | 09/12/2026 |
| Entrega da premiação | até 30/03/2027 |

### Critérios de julgamento — texto do edital, item 8.2

Nota de 0 a 10 por critério, multiplicada pelo peso. **Máximo 70 pontos.**

| Critério | Peso | Máx | Como a entrega endereça |
|---|---|---|---|
| Relevância e impacto | 2 | 20 | 5.570 municípios, cobertura nacional, dois usos nomeados |
| Benefício para a sociedade ou economia | 2 | 20 | subsídio a desenho de política e a gestão municipal |
| Apresentação e usabilidade | 1 | 10 | contracheque, página única, mobile-first |
| Inovação e originalidade | 1 | 10 | harmonização inédita de 4 linhas + metáfora do holerite |
| Replicabilidade e escalabilidade | 1 | 10 | **repositório público com licença** + dataset harmonizado |

Desempate (item 8.6), nesta ordem: benefício → relevância → inovação → apresentação →
replicabilidade. Não cabe recurso contra os próprios critérios (item 13.7).

> **Correção importante.** A página-resumo da CGU lista critérios diferentes destes —
> apresentação 2, inovação 2, transparência 2, foco nas pessoas 2, uso de 2+ fontes 1,
> ferramentas tecnológicas 1, inclusividade 1. **Esses não são os critérios do edital.**
> O que vale é o item 8.2 acima. Consequências: "inclusividade" e "uso de 2+ fontes" não
> são critérios próprios, e "replicabilidade" — que ninguém tinha na conta — vale 10 pontos
> e depende de código aberto e licença.

**Leitura estratégica:** relevância e benefício somam **40 dos 70 pontos (57%)**. São critérios
de alcance e de utilidade pública, não de estética. A apresentação vale 10. Isso reordena o
esforço: a narrativa de impacto e a abertura do código pesam mais que o refinamento visual.

### Requisitos de admissibilidade (item 4 do edital, eliminatórios)

1. Formulário de inscrição preenchido e submetido no prazo.
2. Iniciativa cadastrada como caso de reúso no dados.gov.br e **enviada para homologação**
   dentro do período de inscrição (item 6.3).
3. A iniciativa deve promover "acesso a direitos, transparência, controle social, melhoria de
   serviços ou políticas públicas, conhecimento ou inovação, economia digital ou benefícios à
   sociedade" (item 4.1.3).
4. Utilização e identificação de dados públicos em formato aberto (item 4.1.4).
5. Referenciar ao menos um conjunto do dados.gov.br **ou de sítio oficial do governo federal**.

**Vedações e desclassificação**

- Servidores em exercício na CGU não podem participar (item 3.4); membros das comissões e
  parentes até terceiro grau também (16.5).
- Não são aceitas iniciativas que promovam "preconceito, discriminação, desinformação" (4.2).
- Desclassificação a qualquer tempo por plágio, fraude ou desconformidade com a inscrição (16.4).
- Um trabalho por inscrição (6.1); mais de uma inscrição é permitida se os reúsos forem
  suficientemente distintos (6.6).

**A6 resolvida.** O edital **não restringe temas** — os "25 temas" que aparecem na página-resumo
da CGU não constam do texto legal. O item 4.1.3 é qualitativo e amplo, e a entrega se encaixa
diretamente em transparência, controle social e melhoria de políticas públicas.

**Propriedade intelectual (16.3):** regida pela legislação comum. O edital **não transfere
direitos** à CGU. Publicar o código com licença aberta é escolha nossa — e pontua em
replicabilidade.

**Premiação (item 11):** certificados, selo de vencedor, divulgação no portal e possível convite
a cursos, eventos e missões técnicas em até um ano. Não há prêmio em dinheiro.

> A homologação do caso de reúso tem fila. Fazer o cadastro agora, não em 11/09.

## 2. Usuários-alvo

**P1 — Gestor municipal.** Quer entender como a renda da população da sua cidade se distribui.
Entra pelo nome do município, precisa de uma leitura em segundos, não vai comparar 5.570 casos.
→ atendido pelo **contracheque**.

**P2 — Formulador de política (gestor federal/estadual, parlamentar, assessoria técnica).**
Está desenhando mudança de regra — Bolsa Família, fator previdenciário, teto salarial ou
contratação em prefeitura — e quer saber quais municípios são mais afetados.
→ atendido pelo **panorama nacional com ranking e filtros**.

**P3 — Curioso / jornalista local / pesquisador.** Deriva de P1 e P2, não exige desenho próprio.

Os dois usos justificam a estrutura da página: contracheque em cima (P1), panorama nacional
explorável embaixo (P2).

---

## 3. Conceito da entrega

Página única, estática, mobile-first.

**Bloco 1 — O contracheque do município.** Busca por município. Layout de holerite com quatro
linhas de renda, cada uma em R$ (total e médio) e em pessoas (taxa por 100 adultos).

**Bloco 2 — Panorama nacional.** Beeswarm dos 5.570 municípios + tabela ordenável de exposição.
Filtro por UF e por faixa populacional. O município escolhido no bloco 1 fica destacado.

**Bloco 3 — Método e limites.** O que está dentro, o que está fora, como cada número foi obtido.

### As quatro linhas de renda

| Linha | Fonte | Unidade de pessoas | Serve a |
|---|---|---|---|
| Salário — setor privado | RAIS 2025 | vínculo | exposição a ciclo econômico |
| Salário — administração pública | RAIS 2025 (natureza jurídica, por esfera) | vínculo | teto salarial, contratação |
| Previdência — INSS/BPC | INSS benefícios emitidos | benefício | fator previdenciário, idade mínima |
| Benefício social — Bolsa Família | Portal da Transparência | família (+ pessoas estimadas) | regras do BF |

> A RAIS cobre vínculos **celetistas e estatutários**, então a folha pública sai da mesma fonte
> que o salário privado — sem pipeline adicional. Confirmado no guia oficial da RAIS ano-base 2025.

### Ideias descartadas para esta entrega

Simulador contrafactual "e se parasse?" (premissas econômicas fora do prazo), comparador
lado a lado, Sankey, série histórica.

---

## 4. Assunções críticas

> **A tabela abaixo é o estado de 15/08 antes do spike.** O E1 foi executado no mesmo dia e
> resolveu A1a, A1b, A1c, A2a, A2d, A5 e A10. Estado atual em
> [e1-resultados.md](e1-resultados.md), que prevalece sobre esta tabela.

| # | Assunção | Categoria | Impacto | Incerteza | Status |
|---|---|---|---|---|---|
| A1a | RAIS ano-base 2025 publicada com granularidade municipal | Viab. técnica | Alto | — | **RESOLVIDA** ✅ |
| A1b | INSS tem 2025 completo (jan–dez) por município de residência | Viab. técnica | Alto | Média | P0 — testar em E1 |
| A1c | Bolsa Família tem 2025 completo por município | Viab. técnica | Alto | Baixa | P1 — testar em E1 |
| A2a | A massa em R$ é aditiva entre as quatro linhas | Metodologia | Alto | Baixa | **RESOLVIDA** ✅ |
| A2b | Taxas por 100 adultos comunicam sem induzir a soma | Usabilidade | Alto | Média | P0 — testar em E4 |
| A2c | CadÚnico dá tamanho médio de família por município | Viab. técnica | Médio | Média | P1 — testar em E1 |
| A2d | INSS **não** tem chave de pessoa (dedup impossível) | Viab. técnica | Médio | Média | P1 — testar em E1 |
| A3 | Ranking simétrico resiste a leitura política adversa | Viabilidade | Alto | Média | P0 — testar em E5 |
| A4 | A metáfora do contracheque é compreendida por leigos | Valor | Alto | Média | P1 — testar em E4 |
| A5 | Municípios pequenos têm cobertura (sem supressão por sigilo) | Viab. técnica | Médio | Alta | P1 — testar em E1 |
| A6 | A iniciativa se enquadra no objeto do edital | Admissibilidade | Alto | — | **RESOLVIDA** ✅ item 4.1.3 |
| A7 | A página atinge WCAG AA com D3 | Usabilidade | Médio | Média | P2 — testar em E6 |
| A8 | Jorge aprende D3 o suficiente para o beeswarm no prazo | Viab. técnica | Médio | Média | P2 — testar em E7 |
| A9 | RAIS permite separar esfera municipal por natureza jurídica | Viab. técnica | Médio | Baixa | P1 — testar em E1 |
| A10 | Denominador de população adulta 18+ por município disponível | Viab. técnica | Alto | Baixa | P1 — Censo 2022/projeções IBGE |

### Resolução de A2 — dinheiro não duplica, pessoas duplicam

**Visão em R$ (primária).** Aditiva sem premissa nenhuma. Um aposentado que também trabalha
contribui às duas massas, e isso está correto — o dinheiro circulou duas vezes no município.
O contracheque em reais não precisa de deduplicação.

**Visão em pessoas (secundária).** Não somável. A decisão é **não deduplicar**, por dois motivos:

1. A sobreposição resolvível é a menor. Juntar benefícios acumulados do mesmo segurado corrige
   talvez 5–10% da contagem do INSS. A sobreposição grande é *entre* fontes — quem recebe INSS
   e tem vínculo na RAIS, famílias do BF com renda formal (permitida pela regra de permanência).
   Essa não sai de dado agregado municipal, com chave de pessoa ou sem.
2. Os dados abertos do INSS provavelmente não trazem chave de pessoa (espécie, sexo, clientela,
   município, valor — sem CPF/NIT, coerente com LGPD). Confirmar em E1, mas não desenhar contando
   com isso.

**Formato adotado — taxas sobre denominador comum, nunca empilhamento:**

> A cada 100 adultos: **22** vínculos formais · **19** benefícios do INSS · **31** pessoas em
> famílias do Bolsa Família

A soma pode passar de 100, e isso não é erro — é a própria informação sobre sobreposição,
exibida em vez de escondida atrás de um dedup falso. A página diz isso explicitamente.

**Bolsa Família:** reportar as duas unidades — "X famílias, abrangendo ≈Y pessoas" — usando o
tamanho médio de família do CadÚnico *daquele município*.

**Unidades para a nota técnica:** RAIS = vínculo · INSS = benefício · BF = família.
Nenhuma das três é "pessoa", e o produto nunca finge que é.

---

## 5. Experimentos de validação

| # | Testa | Método | Critério de sucesso | Esforço | Quando |
|---|---|---|---|---|---|
| E1 | A1b/c, A2c/d, A5, A9, A10 | Spike de 5 municípios | 4 linhas montadas para 2025, valores plausíveis | 2–3 dias | Sem. 1 |
| E2 | A2a | Sanidade macro | Soma nacional bate com agregados oficiais em ±10% | 1 dia | Sem. 1 |
| E3 | A2b, A2d | Nota de unidades (irmão) | Regra de agregação escrita antes do front-end | 3 dias | Sem. 1–2 |
| E4 | A2b, A4 | Teste de 5 segundos | 4 de 5 leigos leem o contracheque corretamente | 2 horas | Sem. 2 |
| E5 | A3 | Red team de simetria | 3 leitores de posições distintas não apontam viés | 1 dia | Sem. 3 |
| E6 | A7 | Auditoria de acessibilidade | Lighthouse ≥ 95, navegação completa por teclado | 1 dia | Sem. 3 |
| E7 | A8 | Spike D3 do beeswarm | 5.570 pontos com tooltip e destaque em 1 dia | 1 dia | Sem. 1 |
| E8 | A6, admissib. | Ensaio de submissão | Caso de reúso cadastrado e em homologação | 0,5 dia | Sem. 3 |

### Detalhamento

**E1 — Spike de 5 municípios (o teste que destrava tudo)**
Cinco municípios de perfis deliberadamente distintos: uma capital, uma cidade média do Sul/Sudeste,
uma pequena do Nordeste, uma da Amazônia, e uma com menos de 2.000 habitantes.
Checklist:
- INSS tem jan–dez/2025 por município de **residência** (não só de pagamento)?
- Bolsa Família tem 2025 completo por município?
- RAIS 2025 separa natureza jurídica a ponto de isolar administração pública municipal?
- CadÚnico dá pessoas/famílias por município (para o tamanho médio)?
- INSS tem alguma chave de pessoa?
- Há supressão por sigilo no município <2.000 hab?
- Existe população 18+ por município (Censo 2022 ou projeção)?
*Sanidade:* comparar a folha total contra o PIB municipal do IBGE. Folha > PIB = erro de unidade.
**Nada de front-end antes do E1 fechar.**

**E2 — Sanidade macro**
Somar a folha nacional das quatro linhas e comparar com agregados independentes: massa salarial
das Contas Nacionais (IBGE), despesa do RGPS (Boletim Estatístico da Previdência), execução
orçamentária do Bolsa Família (Portal da Transparência).
*Decisão:* desvio acima de 10% em qualquer linha = investigar antes de prosseguir.

**E3 — Nota de unidades**
Documento curto do irmão: o que é uma "pessoa" em cada fonte, o que é um "valor", período de
referência, regra de agregação, e a taxa de acumulação de benefícios do INSS a nível nacional
(citada como caveat, já que não é mensurável por município).

**E4 — Teste de 5 segundos**
Cinco pessoas não-analistas — incluindo ao menos uma que nunca teve carteira assinada, já que o
holerite pode não ser objeto familiar justamente para quem mais depende de transferência.
Perguntar: "o que é isso? de quem é?" e "essas três barras somam 100?".

**E5 — Red team de simetria**
Três leitores de posições políticas diferentes. *Critério:* nenhum consegue dizer de que lado
o painel está, e todos encontram com igual facilidade o ranking de folha pública e o de BF.

**E7 — Spike D3**
Beeswarm com 5.570 nós, `forceSimulation` + `forceCollide`, tooltip e destaque do município
selecionado. Posições **pré-computadas no build**, não no navegador.
*Plano B se travar:* dot plot ou strip plot com jitter — mesma leitura, um décimo do esforço.

---

## 6. Neutralidade por simetria

O tema é sensível e a decisão é tratá-lo com método, não com omissão. O painel **tem** ranking —
mas sob regras que tornam o viés estruturalmente difícil.

### A regra central: simetria obrigatória

Se é possível rankear "% da renda vinda do Bolsa Família", tem que ser igualmente possível rankear
"% vinda da folha da prefeitura" e "% vinda do salário privado" — mesmo peso visual, mesmo
destaque, mesmo número de cliques. No caso deste projeto a simetria é substantiva, não cosmética:
o caso de uso P2 é sobre teto salarial de prefeitura tanto quanto sobre regra de Bolsa Família.

Um painel que responde igualmente bem "quais municípios são mais afetados se mexer no BF" e
"quais são mais afetados se mexer na folha pública" não tem lado — tem método.

### Regras de enquadramento

- **"Exposição"**, não "dependência" nem "vulnerabilidade". É linguagem de risco, factual e
  simétrica: um município exposto à folha da prefeitura também está exposto.
- **Ranking estratificado por faixa populacional.** Ranking absoluto entre 5.570 municípios
  devolve só cidades minúsculas (variância de amostra pequena) ou só capitais.
- **Sem índice composto único.** Shares explícitos múltiplos. Índice único vira manchete
  descontextualizada e é o objeto mais fácil de instrumentalizar.
- **Ranking sempre com a distribuição atrás.** O beeswarm contextualiza o top-10 em vez de isolá-lo.
- **Nenhum texto atribui causa.** O produto descreve composição e exposição; a nota técnica
  discute interpretação.
- Valores per capita e por adulto ao lado dos absolutos.

### Honestidade metodológica — o que fica de fora, visível na página

- Trabalho informal (parcela grande da ocupação, invisível na RAIS)
- Renda do capital, aluguel, agricultura familiar de subsistência
- Regimes próprios de previdência (RPPS) estaduais e municipais
- Transferências estaduais e municipais de renda
- Diferença entre benefício *pago* (INSS, BF) e renda *declarada* (CadÚnico)
- Sobreposição entre fontes na contagem de pessoas (ver A2)

A frase-chave da página: isto é a renda **registrada e rastreável** em dados públicos —
não a renda total da população.

---

## 7. Cronograma

**Semana 1 — 15 a 22/08 · Provar que os dados existem**
- E1: spike de 5 municípios (Jorge)
- E2: sanidade macro (Jorge)
- E7: spike D3 do beeswarm (Jorge)
- E3 começa: nota de unidades (irmão)
- **Gate:** as quatro linhas existem para 2025. Se não, replanejar o recorte.

**Semana 2 — 23 a 30/08 · Pipeline completo e forma do produto**
- ETL dos 5.570 municípios → Parquet → JSON pré-agregado
- Mockup do contracheque (HTML/CSS — não é D3)
- E4: teste de 5 segundos
- E3 fecha: regra de agregação assinada
- **Gate:** dataset harmonizado congelado. Front-end não começa sobre dados que ainda mudam.

**Semana 3 — 31/08 a 06/09 · Montar e blindar**
- Beeswarm em D3 + tabela ordenável de exposição, integrados ao contracheque
- Textos da página + nota técnica (irmão)
- E5: red team de simetria
- E6: auditoria de acessibilidade
- **E8: cadastro do caso de reúso no dados.gov.br** ← não deixar para a semana 4
- **Gate:** página navegável ponta a ponta.

**Semana 4 — 07 a 11/09 · Polimento e submissão**
- Correções do red team e da auditoria
- Publicação do dataset harmonizado + dicionário de dados
- README do repositório (é peça de avaliação, não detalhe)
- **Submissão em 08/09.** Os 3 dias restantes são folga, não escopo.

---

## 8. Divisão de trabalho

| Jorge (eng. de dados) | Irmão (economista) |
|---|---|
| Aquisição e ETL das 4 linhas | Nota de unidades e regra de agregação (E3) |
| Painel municipal harmonizado + dicionário | Nota técnica metodológica |
| Contracheque (HTML/CSS), beeswarm e ranking (D3) | Textos da página e enquadramento |
| Acessibilidade e performance | Limitações e o que fica de fora |
| Repositório, README, publicação do dataset | Condução do red team (E5) |
| Cadastro no dados.gov.br | Revisão dos números contra fontes oficiais |

**Dependência crítica:** E3 precisa fechar até o fim da semana 2 — define a forma do contracheque.
É o único ponto onde o irmão bloqueia o Jorge. Marcar data.

---

## 9. Framework de decisão

- **E1 passa** → pipeline completo dos 5.570 na semana 2.
- **E1 falha em A1b** (INSS sem 2025 completo) → usar os 12 meses móveis mais recentes disponíveis
  e alinhar as demais fontes ao mesmo período, com nota explícita.
- **E1 falha em A5** (municípios pequenos suprimidos) → exibir o município com marcação visível de
  dado suprimido. A ausência de dado é ela própria informação de transparência.
- **E1 falha em A2c** (CadÚnico sem tamanho de família municipal) → usar média estadual, marcada
  como estimativa; ou reportar só famílias, sem estimar pessoas.
- **E1 falha em A9** (RAIS não separa esfera municipal) → manter uma linha única de administração
  pública, sem quebra por esfera. Perde precisão para P2, não invalida o produto.
- **E2 falha** (desvio >10%) → parar e investigar. Publicar número errado num concurso de dados
  abertos é o pior desfecho possível, pior que não submeter.
- **E4 revela que as pessoas somam as taxas** → trocar a apresentação de barras paralelas por
  três blocos separados com denominador repetido em cada um.
- **E5 aponta viés** → reescrever o texto ou adicionar a visão simétrica faltante. Nunca remover o dado.
- **E7 falha** → plano B (dot plot); D3 segue nos elementos menores.
- **Semana 3 termina sem página navegável** → cortar o panorama nacional e submeter só o
  contracheque. Uma peça acabada pontua mais em "apresentação" que duas pela metade.

---

## 10. Próximos passos imediatos

1. Rodar E1 nesta semana — é o gate de tudo. Checklist na seção 5.
2. Alinhar com o irmão o prazo de E3 (fim da semana 2) e o papel dele no red team.
3. Criar o repositório público desde o dia 1 — histórico de commits é evidência de processo aberto.
4. Ler o Edital CGU nº 46/2026 na íntegra e confirmar A6 (encaixe nos 25 temas elegíveis).

---

## Anexo — fontes confirmadas

- **RAIS ano-base 2025** — divulgada. Tabelas de estoque e remuneração 2023/2024/2025 por
  município; microdados anuais em `.txt`; sistema *dardo* para extração `.xls`/`.csv`.
  Cobre vínculos celetistas **e estatutários**. `pdet.mte.gov.br`
- **INSS — Benefícios Emitidos** — Portal de Dados Abertos do INSS, publicação mensal,
  PDA 2023–2027, catalogado no dados.gov.br (satisfaz o requisito de admissibilidade).
  Campos incluem espécie, sexo, clientela, município de pagamento e de residência, valor líquido.
- **Bolsa Família / CadÚnico** — Portal da Transparência (pagamentos mensais por município) e
  dados abertos do MDS. Cobertura de 2025 a confirmar em E1.
- **Denominadores** — IBGE, Censo 2022 e projeções municipais; PIB municipal para sanidade.
