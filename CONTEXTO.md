# Contexto para retomar o projeto

Documento de handoff. Quem começar uma conversa nova sobre este projeto deve ler isto
primeiro. **Foco: melhorar o que já existe para a competição.** Nada aqui precisa ser
construído do zero.

**Data deste resumo:** 25/08/2026 · **Prazo de inscrição: 11/09/2026 — restam 17 dias.**

---

## 1. O que é

**Folha de Pagamento dos Municípios** — página que mostra, para cada um dos 5.570 municípios
brasileiros, de onde vem a renda registrada da população, em quatro linhas: salário do setor
privado, folha da administração pública, previdência (INSS/BPC) e Bolsa Família. Em reais e em
pessoas. Mês de referência: **dezembro/2025**.

- **No ar:** https://jorgel-mendes.github.io/folha-pagamento-municipios/
- **Repositório:** https://github.com/jorgel-mendes/folha-pagamento-municipios (público, MIT)

**Equipe:** Jorge (engenharia de dados, pipeline, visualização) e o irmão, economista
(metodologia e nota técnica).

---

## 2. O concurso

**2º Concurso de Reúso de Dados Abertos da CGU** — [Edital CGU nº 46, de 19/06/2026](https://www.gov.br/cgu/pt-br/acesso-a-informacao/dados-abertos/concurso-dados-abertos).
Texto integral extraído do DOU em [referencias/edital-cgu-46-2026.txt](referencias/edital-cgu-46-2026.txt).

### Critérios de julgamento — máximo 70 pontos

| Critério | Peso | Máximo |
|---|---|---|
| Relevância e impacto | 2 | 20 |
| Benefício para a sociedade ou economia | 2 | 20 |
| Apresentação e usabilidade | 1 | 10 |
| Inovação e originalidade | 1 | 10 |
| Replicabilidade e escalabilidade | 1 | 10 |

Cada jurado dá de 0 a 10 por critério; a nota é a média simples multiplicada pelo peso.

**Desempate, nesta ordem:** benefício social → relevância → inovação → apresentação →
replicabilidade. Ou seja, **benefício e relevância decidem duas vezes** — valem 40 dos 70
pontos e são os dois primeiros critérios de desempate.

### Datas

| Etapa | Data |
|---|---|
| **Inscrições** | até **11/09/2026** |
| Admissibilidade preliminar | 25/09/2026 |
| Resultado preliminar do julgamento | 13/11/2026 |
| Resultado final | 09/12/2026 |

### Admissibilidade (eliminatório)

Cadastrar a iniciativa como **caso de reúso no dados.gov.br**, referenciando ao menos um
conjunto catalogado lá, e submeter para homologação **dentro do prazo**. A homologação tem
fila. **Este item ainda não foi feito e é o maior risco do projeto.**

---

## 3. Análise da 1ª edição (2025)

Classificação completa em [referencias/classificacao-1o-concurso-2025.pdf](referencias/classificacao-1o-concurso-2025.pdf).
57 inscritos, notas de 30,67 a 98,67. **A escala de 2025 era diferente da de 2026** — não dá
para comparar notas entre edições, só o padrão.

### Os cinco primeiros

| # | Iniciativa | Nota | O que era |
|---|---|---|---|
| 1º | Índice pelo Futuro das Cidades | 98,67 | IEL Goiás + Federação Goiana de Municípios. Índice composto que **premia prefeituras**, desde 2023 |
| 2º | Agenda Transparente | 95,67 | Fiquem Sabendo. Rastreia encontros de autoridades do Executivo. **Um único conjunto de dados** |
| 3º | Atlas da Mineração do Ceará | 95,67 | Observatório da Indústria (Sistema FIEC), em ArcGIS |
| 4º | Medicamentos Transparentes | 95,33 | Transparência Internacional. Compara preço pago com referência |
| 5º | Observatório da Presença Negra no Serviço Público | 94,33 | Mede desigualdade racial na administração pública |

### O achado mais importante: um experimento natural

**Nove das 57 inscrições eram da mesma pessoa** (`@sfiec.org.br`, Observatório da Indústria do
Sistema FIEC). Mesma equipe, mesmo respaldo, mesma cultura de dados:

| Colocação | Iniciativa | Plataforma | Nota |
|---|---|---|---|
| **3º** | Atlas da Mineração do Ceará | **ArcGIS, sob medida** | **95,67** |
| 11º a 25º | Perfil Setorial, Perfil dos Municípios Cearenses, Águas, Perfis Profissionais, Saúde, Comércio Exterior, Infraestrutura, Panorama Industrial | Power BI | 88,67 a 78,00 |

**A única peça feita sob medida ficou 8 a 17 pontos acima de toda a série de dashboards.**

### Projetos adjacentes ao nosso

| # | Iniciativa | Nota |
|---|---|---|
| 6º | VIS DATA (visualizador de programas sociais do MDS) | 93,00 |
| 7º | Mapa Social MDS | 93,00 |
| 12º | Perfil dos Municípios Cearenses | 87,67 |
| **13º** | **Bolsa Família e Cadastro Único no seu Município** (MDS) | **86,67** |
| **22º** | **Radar dos Salários** (RAIS: salário médio por município) | **81,33** |

**Dois projetos usaram praticamente os nossos dados e ficaram em 13º e 22º.** Painel municipal
descritivo tem teto de ~88 nessa banca.

### O padrão que separa o topo do meio

Não é volume de dados — a Agenda Transparente ficou em 2º com um conjunto só. O que os
primeiros têm é **uma pergunta com consequência e um beneficiário nomeado**. Nenhum deles é
partidário; todos são factuais no método e afiados na finalidade.

O campo também é dominado por instituições (Sistema Indústria, MDS, ANM, Fiquem Sabendo,
Transparência Internacional). Dos 104 casos no catálogo do dados.gov.br, **22 são Power BI e
apenas 3 são site próprio em GitHub Pages** — o que torna a nossa abordagem tecnicamente
distintiva.

---

## 4. Onde o projeto está

### Pipeline — pronto e validado

Medallion de três camadas em `pipeline/`, com `uv run` (PEP 723, sem requirements.txt):

```bash
uv run pipeline/01_bronze.py && uv run pipeline/02_silver.py && uv run pipeline/03_gold.py
```

| Fonte | Cobertura | Total (dez/2025) |
|---|---|---|
| RAIS 2025 | 5.571 municípios | 59.967.880 vínculos ativos · R$ 228,2 bi |
| INSS | 5.569 municípios | 41.184.257 benefícios · R$ 74,2 bi |
| Bolsa Família | 5.571 municípios | 18.475.656 famílias · R$ 12,5 bi |
| CadÚnico | 5.571 municípios | 49,2 M pessoas em famílias do BF |
| População (DATASUS) | 5.571 municípios | 213.421.037 habitantes |

**Massa registrada: R$ 310,4 bilhões por mês.** Conferência contra o agregado oficial do INSS:
**desvio de +0,0100%**. De-para de município resolvido em 100% nas duas fontes que usam código
próprio (INSS e SIAFI).

### Site — no ar

- `index.html` — porta de entrada: motivação, evidência por porte, busca. 115 KB em gzip.
- `painel.html` — contracheque do município + panorama nacional com três vistas
  (**distribuição** em beeswarm, **composição** em quadrantes, **mapa** coroplético). 792 KB.
- Deploy automático por GitHub Actions a cada push que toque `site/`.

### Os achados que sustentam a entrega

- Em **88,9%** dos municípios com menos de 5 mil habitantes, INSS e Bolsa Família somados
  movimentam mais dinheiro que toda a massa salarial privada. Em municípios de 5 a 20 mil, 78,7%.
- A folha da prefeitura é a **maior fonte isolada** de renda em **21,3%** dos municípios do Norte.

Esses números são **calculados no build** a partir do painel, não escritos à mão — uma correção
no pipeline chega sozinha ao texto da página.

---

## 5. Decisões fechadas — não reabrir sem motivo

**Dinheiro soma, pessoas não somam.** RAIS conta vínculos, INSS conta benefícios emitidos, BF
conta famílias. Três unidades diferentes, e a mesma pessoa pode estar em mais de uma. O painel
soma reais e **nunca** produz um total de pessoas — o campo não existe no JSON, de propósito.

**Neutralidade por simetria.** Todo recorte de exposição ao Bolsa Família tem equivalente de
igual destaque para folha da prefeitura e salário privado. Vocabulário é **"exposição"**, nunca
"dependência" nem "vulnerabilidade". Sem índice composto único. Ranking sempre estratificado
por porte.

**Mês de referência dezembro/2025**, remuneração de dezembro da RAIS (padrão dos relatórios do
PDET), com corte de **0,7 a 30 salários mínimos apenas para a média** — a massa soma todo mundo.

**Vínculos abandonados excluídos** (1,07% dos ativos, todos com remuneração zero).

---

## 6. O que falta, em ordem de urgência

1. **Cadastro do caso de reúso no dados.gov.br.** Eliminatório, tem fila, só o Jorge pode fazer.
   Já existe URL pública para informar. **Este é o item que pode anular todo o resto.**

2. **Três respostas do economista** — detalhadas em
   [briefing-nota-tecnica.md](briefing-nota-tecnica.md). Mudam números que estão na primeira
   dobra da página:
   - **Q7** — INSS publica valor **líquido**, RAIS publica **bruto**. Somar mistura os dois.
   - **Q8** — Bolsa Família por competência ou por referência? (~R$ 127 mi/mês de diferença)
   - **Q10** — vínculo ativo sem remuneração conta como "pessoa com renda formal"? (8,5 M)

3. **Nota técnica** completa.

4. **Auditoria de acessibilidade** — meta Lighthouse ≥ 95, navegação por teclado, alternativa
   tabular. Vale 10 pontos em "apresentação e usabilidade" e é barato de garantir.

5. **Pendência de citação:** os cortes de 0,7 e 30 SM foram implementados como parâmetro da
   RAIS, mas a documentação pública do PDET que os fixa não foi localizada. Sem citação, é um
   número que o júri pode questionar.

---

## 7. A recomendação estratégica

Pela análise da edição anterior, o formato "painel descritivo" tem teto de ~88 e o que passa de
94 é **artefato sob medida com uma pergunta que tem consequência**. O projeto já é o primeiro;
o que ainda falta é deixar o segundo explícito.

A porta de entrada (`index.html`) foi criada exatamente para isso — ela lidera com o achado e
nomeia o uso, em vez de prometer uma ferramenta. **Se sobrar tempo, o maior retorno por esforço
continua sendo em relevância e benefício social, não em mais gráficos.**

---

## 8. Mapa do repositório

| Arquivo | O quê |
|---|---|
| [discovery-plan.md](discovery-plan.md) | Plano de discovery: assunções, experimentos, cronograma |
| [e1-resultados.md](e1-resultados.md) | Spike de dados: o que existe, o que quebra, formatos reais |
| [prd.md](prd.md) | Especificação da página: blocos, contrato JSON, acessibilidade |
| [briefing-nota-tecnica.md](briefing-nota-tecnica.md) | As 10 perguntas metodológicas + prompts de pesquisa |
| [pipeline/README.md](pipeline/README.md) | Como rodar e atualizar o pipeline |
| `referencias/` | Edital em texto e classificação da 1ª edição em PDF |
| `site/` | Templates, build, D3, malha do IBGE |
| `dados/gold/202512/` | Painel municipal, dicionário e relatório de validação |
