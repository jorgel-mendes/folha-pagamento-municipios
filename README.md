# Folha de Pagamento dos Municípios

De onde vem a renda registrada da população de cada cidade brasileira.

Página única que mostra, para cada um dos 5.570 municípios, a composição da renda registrada em
quatro linhas — salário do setor privado, folha da administração pública, benefícios
previdenciários do INSS e Bolsa Família — em reais e em pessoas.

Inscrição no **2º Concurso de Reúso de Dados Abertos da CGU** (Edital CGU nº 46/2026).

---

## Documentos

| Arquivo | O quê |
|---|---|
| [referencias/edital-cgu-46-2026.txt](referencias/edital-cgu-46-2026.txt) | Texto integral do edital, extraído do PDF do DOU |
| [discovery-plan.md](discovery-plan.md) | Plano de discovery: ideias, assunções, experimentos, cronograma |
| [e1-resultados.md](e1-resultados.md) | Resultados do spike de dados — o que existe, o que não existe, o que quebra |
| [prd.md](prd.md) | Especificação da página: blocos, campos, contrato JSON, acessibilidade |
| [briefing-nota-tecnica.md](briefing-nota-tecnica.md) | Briefing do economista: 9 perguntas metodológicas + prompts de pesquisa |
| [pipeline/README.md](pipeline/README.md) | Como rodar e atualizar o pipeline de dados |

## Fontes

| Linha | Fonte | Unidade | Granularidade |
|---|---|---|---|
| Salário — setor privado | RAIS 2025 (microdados PDET) | vínculo | município do estabelecimento |
| Salário — administração pública | RAIS 2025, por natureza jurídica | vínculo | município do estabelecimento |
| Previdência — INSS/BPC | INSS, benefícios emitidos | benefício | município de residência |
| Benefício social — Bolsa Família | Portal da Transparência | família | município (SIAFI) |
| Tamanho médio de família | CadÚnico via SAGI/MDS | — | município |
| Denominador populacional | DATASUS POPSVS (idade ano a ano) | pessoa | município |

Mês de referência: **dezembro/2025**.

## A regra que atravessa o projeto

**Massa em R$ soma. Contagem de pessoas não soma.**

A RAIS conta vínculos, o INSS conta benefícios emitidos e o Bolsa Família conta famílias — três
unidades diferentes, e uma mesma pessoa pode aparecer em mais de uma. O painel nunca produz um
total de pessoas: o campo simplesmente não existe no JSON.

Em compensação, as massas em reais **são** somáveis, porque representam fluxos de dinheiro
distintos. Um aposentado que também trabalha contribui às duas massas, e isso está correto — o
dinheiro circulou duas vezes no município.

## Neutralidade por simetria

O tema é politicamente sensível, e a defesa é estrutural: **todo ranking de exposição ao Bolsa
Família tem equivalente de igual destaque para a folha da prefeitura e para o salário privado.**
Um painel que responde igualmente bem "quais municípios são mais afetados se mexer no BF" e
"quais são mais afetados se mexer na folha pública" não tem lado — tem método.

O vocabulário é "exposição", nunca "dependência" nem "vulnerabilidade".

## Estado — painel nacional completo (dezembro/2025)

| Fonte | Cobertura | Total |
|---|---|---|
| RAIS 2025 | 5.571 municípios | 59.967.880 vínculos ativos · R$ 228,2 bi |
| INSS | 5.569 municípios | 41.184.257 benefícios · R$ 74,2 bi |
| Bolsa Família | 5.571 municípios | 18.475.656 famílias · R$ 12,5 bi |
| CadÚnico | 5.571 municípios | 49,2 M pessoas em famílias do BF |
| População | 5.571 municípios | 213.421.037 habitantes |

**Massa registrada: R$ 310,4 bilhões por mês.** Desvio contra o agregado oficial do INSS:
**+0,0100%**. De-para de município resolvido em 100% nas duas fontes que usam código próprio.

### Composição nacional

| Fonte | R$ bi/mês | Participação |
|---|---|---|
| Salário privado | 157,9 | 50,9% |
| Previdência (INSS/BPC) | 73,5 | 23,7% |
| Folha pública | 66,5 | 21,4% |
| Bolsa Família | 12,5 | 4,0% |

### O achado que sustenta a entrega

Em **88,8% dos municípios com menos de 5.000 habitantes**, INSS e Bolsa Família juntos
movimentam mais dinheiro que toda a massa salarial privada. Em municípios de 5 a 20 mil, 78,7%.

E a simetria não é artifício: a folha da prefeitura é a **maior fonte isolada** de renda em
21,3% dos municípios do Norte.

## Rodando

```bash
uv run pipeline/01_bronze.py && uv run pipeline/02_silver.py && uv run pipeline/03_gold.py
```

Detalhes, parâmetros e custo de disco em [pipeline/README.md](pipeline/README.md).

## Equipe

Jorge — engenharia de dados, pipeline e visualização.
Irmão — economia, metodologia e nota técnica.
