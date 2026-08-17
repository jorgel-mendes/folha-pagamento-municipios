# Briefing — Nota Técnica e Metodologia

**Para:** o economista da dupla
**De:** Jorge (engenharia de dados)
**Projeto:** Folha de Pagamento dos Municípios — 2º Concurso de Reúso de Dados Abertos da CGU
**Prazo do concurso:** 11/09/2026 · **Seu bloqueio crítico: E3 até 30/08**

---

## 1. O que estamos construindo

Uma página web única que mostra, para cada um dos 5.570 municípios brasileiros, de onde vem a
renda registrada da população, em quatro linhas:

| Linha | Fonte | Unidade de contagem |
|---|---|---|
| Salário — setor privado | RAIS 2025 (microdados PDET) | vínculo |
| Salário — administração pública | RAIS 2025, por natureza jurídica/esfera | vínculo |
| Previdência — INSS/BPC | INSS, benefícios emitidos dez/2025 | benefício |
| Benefício social — Bolsa Família | Portal da Transparência, dez/2025 | família |

Cada linha aparece em **R$** (massa total e valor médio) e em **pessoas** (taxa por 100 adultos).

Dois usos-alvo: (1) gestor municipal entendendo a própria cidade; (2) formulador de política
querendo saber quais municípios são mais expostos a uma mudança de regra — no Bolsa Família,
no fator previdenciário, ou no teto salarial e na contratação em prefeituras.

**Mês de referência: dezembro/2025.** As três fontes têm estoque em dezembro, o que alinha os
períodos naturalmente. (Ver pergunta Q4 abaixo — tem uma pegadinha aí.)

---

## 2. Seu papel

Duas entregas, uma bloqueante e uma final.

**E3 — Nota de unidades (bloqueante, até 30/08).** Documento curto, 2 a 4 páginas, que define
formalmente as unidades e a regra de agregação. Bloqueia porque determina a forma do
contracheque: se as quatro linhas podem ou não aparecer numa pilha única. Não dá para desenhar
a interface antes disso.

**Nota técnica completa (até 06/09).** O documento que acompanha a inscrição e que sustenta a
credibilidade da entrega. É também o que nos protege da leitura política enviesada.

---

## 3. As perguntas que a nota de unidades precisa responder

**Q1 — O que é uma "pessoa" em cada fonte, e por que não são a mesma coisa?**
RAIS conta vínculos (uma pessoa com dois empregos = dois vínculos). INSS conta benefícios
emitidos (um segurado com aposentadoria + pensão = dois benefícios). Bolsa Família conta
famílias. Precisamos da definição formal de cada uma e da taxa de acumulação conhecida
para RAIS e INSS a nível nacional — não conseguimos medir por município, então vai como
ressalva quantificada.

**Q2 — A massa em R$ é somável entre as quatro linhas? Justifique.**
Nossa posição de trabalho é que sim: um aposentado que também trabalha contribui às duas massas
e isso está correto, porque o dinheiro circulou duas vezes no município. Preciso que você
confirme ou refute isso com argumento econômico, não com intuição. Se houver alguma dupla
contagem real em R$ (algum benefício que apareça em duas fontes), é agora que descobrimos.

**Q3 — A contagem de pessoas pode ser somada? Se não, qual a apresentação correta?**
Nossa proposta: **não somar**. Apresentar como taxa sobre a população adulta do município —
"a cada 100 adultos: 22 vínculos formais, 19 benefícios do INSS, 31 pessoas em famílias do BF" —
aceitando que a soma passe de 100, porque o excesso *é* a sobreposição, exibida honestamente.
Preciso que você valide o denominador (população 18+? 16+? em idade ativa?) e escreva a frase
de uma linha que explica ao leitor por que passa de 100.

**Q4 — Dezembro é um mês representativo? — DECIDIDO**
Usamos a **remuneração de dezembro**, que é o padrão dos relatórios da RAIS, e o **corte de 0,7 a
30 salários mínimos no cálculo da média**, também parâmetro da RAIS. A massa salarial soma todo
mundo, sem corte — massa é total, não estimativa central; o corte vale só para a média.
Salário mínimo de 2025: R$ 1.518,00, então a faixa é R$ 1.062,60 a R$ 45.540,00.

> **Pendência para você:** não consegui localizar a documentação pública do PDET que fixa esses
> dois limites — achei a definição da remuneração média de dezembro, não os cortes. Precisamos da
> referência exata (nota técnica do MTE, manual da RAIS ou metodologia do PDET) para citar na
> nota técnica. Sem citação, é um número que o júri pode questionar.

Fica registrada uma consequência do corte inferior: trabalhadores em jornada parcial que ganham
legitimamente menos de 0,7 SM saem da média, o que a puxa para cima. É a escolha da RAIS e
mantemos, mas precisa estar declarada.

**Q5 — Como anualizar?**
Se o painel mostrar valores mensais, é direto. Se mostrar anuais, multiplicar por 12 ignora o 13º
e o abono; por 13 assume que todo mundo recebe. Minha inclinação é mostrar **mensal** e evitar o
problema inteiro, mas quero seu parecer.

**Q7 — Líquido ou bruto? (achado do E1, e é sério)**
O campo do INSS é `Vl Líquido` — já descontados crédito consignado, imposto de renda e demais
descontos. A remuneração da RAIS é **bruta**. Somar as duas massas mistura líquido com bruto.
Três saídas: (a) manter e declarar a inconsistência; (b) achar valor bruto do benefício em outra
fonte; (c) estimar o desconto médio e ajustar. A magnitude não é desprezível — o consignado do
INSS é da ordem de dezenas de bilhões por ano. **Sua decisão.**

**Q8 — Qual competência do Bolsa Família conta? (achado do E1)**
O arquivo de dezembro do Portal da Transparência tem duas colunas de mês: *competência*
(quando o dinheiro saiu) e *referência* (a que mês a parcela se refere). O arquivo de
dezembro/2025 contém parcelas referentes a março, abril e outros meses de 2025 — retroativos.
São duas leituras legítimas e diferentes: "famílias com benefício em dezembro" versus "dinheiro
do BF que entrou no município em dezembro". O pipeline calcula as duas (`_ref` e `_comp`) e hoje
usa `_ref`. **Confirme ou troque.**

**Q9 — A RAIS e o INSS localizam a renda em lugares diferentes (achado do E1)**
A RAIS registra o vínculo no **município do estabelecimento**; o INSS registra o benefício no
**município de residência**. Em região metropolitana isso desloca massa salarial da cidade-dormitório
para a cidade-polo, enquanto a massa previdenciária fica na cidade-dormitório. O efeito é
sistemático e favorece a leitura de que periferias metropolitanas "dependem de transferências".
Precisa de uma ressalva explícita na página, não só na nota técnica.

**Q10 — O que conta como "pessoa com renda formal"? (achado do E1, e é o mais espinhoso)**
Testando a região Norte da RAIS 2025, entre os vínculos marcados como ativos em 31/12:

- **1,07% são vínculos abandonados** — o trabalhador saiu sem rescisão formal. Todos têm
  remuneração zero. Já excluí do pipeline: não mexem na massa, mas inflavam a contagem, que é o
  denominador do salário médio e da taxa por 100 adultos. Excluí-los move o salário médio do
  Norte de R$ 3.427,94 para R$ 3.465,00.
- **Uma parcela relevante dos restantes tem remuneração zero ou nula.** Provavelmente afastados
  o ano inteiro (auxílio-doença, licença), admitidos em 31/12, ou erro de declaração.

O corte de 0,7 SM (Q4) resolve isso para a **média**, porque esses vínculos caem abaixo do piso e
saem da base de cálculo automaticamente. Mas eles continuam contando como **vínculo** na coluna de
pessoas e na taxa por 100 adultos. **A decisão que sobra é sua:** uma pessoa com carteira assinada
e nenhuma remuneração no mês conta como "pessoa com renda formal" no contracheque?

O pipeline grava as duas contagens (`vinculos` e `base_media_vinculos`) para você comparar.

**Q6 — O que declaramos que está fora, e com que magnitude?**
Trabalho informal, renda do capital, aluguel, agricultura de subsistência, RPPS estaduais e
municipais, transferências estaduais/municipais, e a diferença entre benefício *pago* e renda
*declarada* no CadÚnico. Para cada item, se existir uma estimativa nacional de magnitude
(ex.: taxa de informalidade da PNAD Contínua), citar. A honestidade quantificada vale mais que
a ressalva genérica.

---

## 4. A questão política — e por que ela é sua também

O tema é sensível. A mesma composição de renda pode ser lida como "o Nordeste vive de bolsa" ou
como "as transferências federais sustentam a economia local". Nossa defesa é estrutural, não
retórica, e tem duas partes:

**Simetria.** Todo ranking de exposição ao Bolsa Família tem equivalente de igual destaque para
folha da prefeitura e salário privado. Um painel que responde igualmente bem "quais municípios
são mais afetados se mexer no BF" e "quais são mais afetados se mexer na folha pública" não tem
lado — tem método.

**Vocabulário.** Usamos "exposição", nunca "dependência" nem "vulnerabilidade". Se você usar
"dependência" na nota técnica, que seja com definição formal e citação de literatura.

Você conduz o red team disso na semana 3: três leitores de posições políticas diferentes leem a
página e a nota, e o critério de sucesso é que nenhum consiga dizer de que lado o painel está.

---

## 5. Prompts para começar a pesquisa

Cole diretamente numa ferramenta de busca ou de IA com acesso à web. Foram escritos para trazer
trabalho anterior de intenção parecida — o que já existe, como enquadraram, e onde erraram.

**Prompt 1 — precedente brasileiro direto**
> Procure estudos brasileiros que analisem a composição da renda da população em nível municipal
> combinando massa salarial formal (RAIS), benefícios previdenciários do INSS e transferências de
> renda (Bolsa Família / CadÚnico). Inclua os estudos da ANFIP sobre "Previdência Social e a
> Economia dos Municípios", textos para discussão do IPEA sobre impacto econômico de
> transferências de renda em municípios, e trabalhos que comparem benefícios do INSS com o FPM
> como fonte de recursos municipais. Para cada um: pergunta de pesquisa, fonte de dados, unidade
> de análise, e principal achado.

**Prompt 2 — precedente internacional de produto**
> Descreva como o Bureau of Economic Analysis dos EUA publica "Personal Income by County" com
> decomposição em salários, transferências governamentais e renda de propriedade (séries CAINC30
> e CAINC35). Como definem e apresentam "personal current transfer receipts"? Existem
> visualizações interativas conhecidas construídas sobre esses dados — por exemplo o mapa
> interativo do New York Times "The Geography of Government Benefits" (2012)? Que críticas
> metodológicas e de enquadramento essas visualizações receberam?

**Prompt 3 — o problema das unidades**
> Na literatura de estatísticas do trabalho e da previdência no Brasil, qual é a razão conhecida
> entre número de vínculos da RAIS e número de pessoas ocupadas formalmente? E entre número de
> benefícios emitidos pelo INSS e número de beneficiários distintos (taxa de acumulação de
> benefícios, como aposentadoria somada a pensão por morte)? Cite fontes oficiais — Boletim
> Estatístico da Previdência Social, AEPS, notas técnicas do MTE, PNAD Contínua.

**Prompt 4 — multiplicador local**
> Qual a evidência empírica sobre o efeito multiplicador local de transferências de renda e de
> benefícios previdenciários na economia de municípios brasileiros pequenos? Procure estimativas
> de multiplicador do Bolsa Família e da previdência rural, e estudos sobre o papel dessas
> transferências no comércio local de municípios do semiárido. Inclua trabalhos de Neri, Vaz,
> Souza, Delgado e Cardoso Jr.

**Prompt 5 — o lado da folha pública**
> Que estudos analisam o peso da folha de pagamento das prefeituras na economia e na renda local
> de municípios brasileiros pequenos? Procure trabalhos sobre a Lei de Responsabilidade Fiscal e
> limites de gasto com pessoal, sobre municípios onde a prefeitura é o maior empregador, e dados
> do Siconfi / FINBRA sobre despesa com pessoal por município.

**Prompt 6 — quem já fez visualização parecida no Brasil**
> Existem painéis, visualizações interativas ou reportagens de dados brasileiras que mostrem, por
> município, a composição da renda da população entre trabalho formal, previdência e transferências
> sociais? Procure em Base dos Dados, Nexo Políticas Públicas, Estadão Dados, Folha, InfoAmazonia,
> Transparência Brasil, IPEA Data, e nos casos de reúso já publicados no dados.gov.br. Se existirem,
> descreva a abordagem e o que ficou de fora.

**Prompt 7 — como não errar o enquadramento**
> Que críticas metodológicas e éticas existem sobre índices e mapas de "dependência de
> transferências governamentais"? Como pesquisadores em política social recomendam apresentar
> dados de recebimento de benefícios sem produzir estigma territorial ou populacional? Procure
> literatura sobre "welfare stigma", enquadramento midiático de programas de transferência de
> renda, e boas práticas de comunicação de dados sobre pobreza.

> O Prompt 6 tem função dupla: se alguém já fez exatamente isso, precisamos saber agora, na semana
> 1 — muda o argumento de inovação da inscrição (peso 2 no edital). Se ninguém fez, isso vira
> uma frase forte na apresentação.

---

## 6. Estrutura sugerida da nota técnica final

1. Objetivo e perguntas que o painel responde
2. Fontes de dados — origem, periodicidade, data de extração, licença
3. Definições e unidades (sai direto da nota de unidades)
4. Método de agregação municipal e denominadores populacionais
5. Validação — comparação com agregados oficiais independentes (eu forneço os números do E2)
6. Limitações e o que não está coberto
7. Notas de interpretação — o que o painel permite e o que **não** permite concluir
8. Referências

A seção 7 é a mais importante e a que quase ninguém escreve. É onde você antecipa o uso indevido.

---

## 7. O que eu te entrego e quando

| Quando | O quê |
|---|---|
| Semana 1 | Resultado do E1: schema real das fontes, campos disponíveis, cobertura dos 5 municípios-teste |
| Semana 1 | Resultado do E2: totais nacionais das quatro linhas vs. agregados oficiais |
| Semana 2 | Painel municipal harmonizado (Parquet/CSV) + dicionário de dados preliminar |
| Semana 3 | Página navegável para você revisar textos e enquadramento |

## 8. O que preciso de você e quando

| Quando | O quê |
|---|---|
| Até 22/08 | Resposta preliminar a Q4 e Q5 (mês de referência e anualização) — destrava o pipeline |
| Até 30/08 | **Nota de unidades completa (E3)** — destrava o front-end |
| Até 03/09 | Textos da página: título, subtítulo, legendas, o parágrafo de limitações |
| Até 06/09 | Nota técnica final + red team (E5) conduzido |
