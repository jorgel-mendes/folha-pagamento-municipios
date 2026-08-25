# PRD — Folha de Pagamento dos Municípios

**Versão:** 1.0 · 15/08/2026
**Alvo:** 2º Concurso de Reúso de Dados Abertos da CGU · inscrição até 11/09/2026
**Mês de referência:** dezembro/2025 (pendente de confirmação em E3/Q4)

---

## 1. Objetivo

Uma página web única que responde, para qualquer um dos 5.570 municípios brasileiros:
**de onde vem a renda registrada da população daqui?**

E, no agregado nacional: **quais municípios são mais expostos a uma mudança de regra em cada
fonte de renda?**

## 2. Usuários e casos de uso

| # | Usuário | Pergunta que traz | Bloco que atende |
|---|---|---|---|
| P1 | Gestor municipal | "Como a renda da minha cidade se distribui?" | Contracheque |
| P2 | Formulador de política | "Quais municípios são mais afetados se eu mexer nesta regra?" | Panorama nacional |
| P3 | Jornalista local / curioso | "Minha cidade é normal ou é um caso extremo?" | Contracheque + posição no beeswarm |

## 3. Escopo

**Dentro:** 5.570 municípios · 4 linhas de renda · valores em R$ (massa e média) e em pessoas
(taxa por 100 adultos) · busca por município · ranking de exposição com filtro por UF e porte ·
seção de método e limites · dataset harmonizado publicado.

**Fora da v1:** série histórica, comparador lado a lado, simulador contrafactual, recorte
intramunicipal, quebra por sexo/idade/setor, exportação de gráfico como imagem.

---

## 4. Estrutura da página

Página única, rolagem vertical, quatro blocos.

```
┌─────────────────────────────────────────────┐
│ BLOCO 0 — Abertura                          │
│ Título + subtítulo + busca de município     │
│ (com município padrão pré-carregado)        │
├─────────────────────────────────────────────┤
│ BLOCO 1 — O CONTRACHEQUE                    │
│ Cabeçalho: município, UF, população,        │
│            mês de referência                │
│ 4 linhas de renda × (R$ total, R$ médio,    │
│                      pessoas/100 adultos)   │
│ Rodapé: total da renda registrada           │
│ Alternador: [R$] [pessoas]                  │
├─────────────────────────────────────────────┤
│ BLOCO 2 — PANORAMA NACIONAL                 │
│ Beeswarm dos 5.570, município destacado     │
│ Seletor de linha (privado/público/INSS/BF)  │
│ Filtros: UF, faixa populacional             │
│ Tabela ordenável de exposição               │
├─────────────────────────────────────────────┤
│ BLOCO 3 — MÉTODO E LIMITES                  │
│ Fontes, unidades, o que ficou de fora,      │
│ link para nota técnica e para o dataset     │
└─────────────────────────────────────────────┘
```

---

## 5. Bloco 1 — O contracheque

### Layout

Metáfora de holerite: cabeçalho com identificação, corpo com linhas discriminadas, rodapé com
total. Tipografia tabular, alinhamento de valores à direita, régua horizontal entre linhas.

### Campos por linha

| Coluna | Conteúdo | Formato |
|---|---|---|
| Descrição | Nome da linha de renda | texto |
| Fonte | Origem do dado (RAIS / INSS / Portal da Transparência) | texto pequeno |
| Pessoas | Contagem na unidade da fonte + rótulo da unidade | `12.480 vínculos` |
| Por 100 adultos | Taxa sobre população 18+ | `22,4` |
| Valor médio | Ver regra abaixo | `R$ 2.180` |
| Massa mensal | Total que entra no município no mês | `R$ 27,2 mi` |
| Participação | % da massa total registrada | barra + `%` |

### Como o valor médio é calculado

As duas coisas não seguem a mesma regra, e a diferença precisa aparecer na nota de rodapé:

- **Linhas de salário (RAIS).** Média sobre a base filtrada de **0,7 a 30 salários mínimos** da
  remuneração de dezembro — parâmetro da própria RAIS. Em 2025, R$ 1.062,60 a R$ 45.540,00.
  A base de cálculo é menor que a contagem de vínculos exibida, e isso é intencional.
- **Previdência e Bolsa Família.** Massa ÷ contagem, sem corte, porque não há parâmetro
  equivalente publicado para essas fontes.

**A massa nunca é filtrada** — em nenhuma das quatro linhas. Massa é total; o corte existe só
para a estimativa central não ser distorcida por outliers.

### Regras de exibição

- **A coluna "Pessoas" nunca é totalizada.** O rodapé soma apenas R$.
- Cada linha declara sua unidade explicitamente — *vínculos*, *benefícios*, *famílias* — porque
  não são a mesma coisa. Ver [briefing-nota-tecnica.md](briefing-nota-tecnica.md), Q1 e Q3.
- Abaixo das taxas, frase fixa: *"As taxas podem somar mais de 100 porque uma mesma pessoa pode
  aparecer em mais de uma fonte — por exemplo, quem recebe aposentadoria e também trabalha com
  carteira assinada."*
- Bolsa Família exibe duas unidades: `3.204 famílias (≈ 9.900 pessoas)`, com a estimativa marcada
  como derivada do tamanho médio de família do CadÚnico do município.
- Dado suprimido ou ausente aparece como `—` com tooltip explicando o motivo. **Nunca zero.**

### Alternador R$ / pessoas

Botão de dois estados que troca a coluna em destaque. Em telas estreitas, as duas visões viram
abas. O estado atual precisa ser óbvio sem depender de cor.

---

## 6. Bloco 2 — Panorama nacional

### Beeswarm

- Um nó por município (5.570). Eixo X = % da massa registrada vinda da linha selecionada.
- Raio proporcional à população (escala de raiz quadrada, mínimo 1,5px).
- Cor por região, com paleta segura para daltonismo.
- Município selecionado no Bloco 1 fica destacado com anel e rótulo persistente.
- **Empacotamento calculado no cliente**, com o algoritmo *dodge* determinístico: ordena por x
  e encaixa cada ponto no menor |y| livre. Não é simulação de força — roda em milissegundos
  mesmo com os 5.571 municípios. Foi preciso trazer o cálculo para o cliente porque o escopo é
  dinâmico: posições pré-computadas para o país inteiro deixariam buracos ao exibir um estado.
- **Raio pela população**, com piso que acompanha a contagem de pontos em cena. Piso fixo faz
  o enxame virar uma linha fina quando há muitos municípios e some com a distribuição.
- Tooltip no hover e no foco por teclado: nome, UF, população, % da linha selecionada.

### Seletor de linha — a regra de simetria

As quatro linhas aparecem como opções de **igual peso visual, igual destaque e igual número de
cliques**. É requisito de produto, não preferência estética: é o que sustenta a neutralidade do
painel. Ver [discovery-plan.md](discovery-plan.md), seção 6.

### Escopo, ampliação e foco

Três controles, todos desenhados para não competir com o gráfico:

- **Escopo** (`estado` por padrão, `região`, `todos`). O padrão é o estado do município
  escolhido: é o recorte mais leve e o grupo de comparação mais intuitivo para um gestor.
- **Cor conforme o escopo.** Em `todos`, cor por região — o padrão que importa é regional.
  Em `região`, cor por UF — a diferença relevante passa a ser entre estados. Em `estado`,
  nenhuma cor agrega informação, então só o município escolhido aparece destacado.
- **Legenda clicável.** Clicar numa cor destaca só aquele grupo e restringe a tabela;
  clicar de novo desfaz. Vale para região e para UF.
- **Ampliar.** Clique no gráfico abre-o num `<dialog>` modal; clique fora ou `Esc` volta.
  A figura é movida para dentro do diálogo e redesenhada — não há duplicação de SVG.
- **Botão de opções.** Uma seta discreta no canto superior direito, a 45% de opacidade,
  que só ganha contorno no hover ou no foco. Abriga escopo e porte.

### Tabela de exposição

- Colunas: município, UF, população, % da linha selecionada, massa total, R$ per capita.
- Ordenável por qualquer coluna, crescente e decrescente.
- **Filtro obrigatório por faixa populacional** (até 5k / 5–20k / 20–100k / 100k+), com o filtro
  aplicado por padrão à faixa do município selecionado. Ranking absoluto entre os 5.570 devolve
  só cidades minúsculas ou só capitais e não informa nada.
- Máximo 50 linhas visíveis com paginação.
- Vocabulário: **"exposição"**. Nunca "dependência", nunca "vulnerabilidade".

---

## 7. Contrato de dados

Dois arquivos gerados no build, consumidos estaticamente.

**`municipios.json`** — índice leve para busca (~5.570 registros, alvo < 400 KB):

```json
{"id":"2304400","nome":"Fortaleza","uf":"CE","pop":2428708,"pop18":1859000,
 "x":412.5,"y":88.1,"regiao":"NE","porte":"100k+"}
```

**`dados.json`** — payload principal (alvo < 3 MB; se estourar, particionar por UF):

```json
{"2304400": {
  "ref": "2025-12",
  "linhas": {
    "salario_privado":  {"n":412880,"unidade":"vinculos","massa":1284000000,"medio":3110},
    "salario_publico":  {"n": 58210,"unidade":"vinculos","massa": 262000000,"medio":4500,
                         "esferas":{"municipal":31200,"estadual":21010,"federal":6000}},
    "previdencia":      {"n":289450,"unidade":"beneficios","massa": 612000000,"medio":2115},
    "bolsa_familia":    {"n": 98120,"unidade":"familias","massa":  62000000,"medio": 632,
                         "pessoas_estimadas":301000,"tam_medio_familia":3.07}
  },
  "massa_total": 2220000000,
  "supressoes": []
}}
```

**Regras do contrato**

- `n` sempre acompanhado de `unidade` — o front-end nunca assume que `n` é pessoa.
- **Não existe campo `pessoas_total`.** A ausência é intencional: impede que alguém some no futuro.
- Linha ausente = chave ausente, com o motivo em `supressoes`. Nunca `0`.
- Todos os valores monetários em reais nominais do mês de referência, sem deflacionamento.

---

## 8. Acessibilidade — vale 1 ponto no edital

Requisito de aceite, não item de polimento.

- **Alternativa tabular do beeswarm.** Uma `<table>` real com os mesmos dados, alcançável por
  teclado, escondida visualmente mas não do leitor de tela.
- Todo elemento interativo alcançável por `Tab`, com foco visível.
- Nós do beeswarm navegáveis por teclado, ou pelo menos o município selecionado focável.
- Contraste mínimo 4.5:1; nunca usar cor como único portador de informação.
- SVG com `role="img"` e `<title>`/`<desc>`; atualizações anunciadas via `aria-live="polite"`.
- Funciona sem JavaScript até o ponto de exibir um município padrão e o texto de método.
- `prefers-reduced-motion` respeitado em qualquer transição.
- Meta de aceite: **Lighthouse ≥ 95** em acessibilidade.

## 9. Arquitetura e performance

- Site estático. Sem backend, sem banco, sem chamada de rede em runtime.
- Pipeline: fontes brutas → DuckDB → Parquet → JSON pré-agregado → build.
- D3 apenas para o beeswarm e as barras de participação. O contracheque é HTML/CSS — o que tira
  a peça mais importante do caminho crítico do aprendizado de D3.
- Orçamento de JS: **< 100 KB em gzip**, que é o que trafega. Hoje: D3 v7 completo
  (273 KB brutos / 91 KB gzip) + 17 KB de código próprio. O D3 completo foi mantido de
  propósito enquanto o projeto é veículo de aprendizado; trocar por um bundle só com
  `d3-selection`, `d3-scale`, `d3-axis` e `d3-transition` cortaria cerca de dois terços.
- Sem CDN: o D3 é vendorizado em `site/vendor/`, para o repositório ser reprodutível
  sozinho — o que também é o critério de replicabilidade do edital.
- Mobile-first. O contracheque tem que funcionar em 360px de largura.
- Deploy em GitHub Pages, repositório público desde o dia 1.

## 10. Microcopy

| Elemento | Texto |
|---|---|
| Título | Folha de Pagamento dos Municípios |
| Subtítulo | De onde vem a renda registrada da população de cada cidade brasileira |
| Frase-âncora | Isto é a renda **registrada e rastreável** em dados públicos — não a renda total da população. |
| Rótulo do ranking | Exposição a cada fonte de renda |
| Nota das taxas | As taxas podem somar mais de 100 porque uma mesma pessoa pode aparecer em mais de uma fonte. |

Nenhum texto atribui causa. O produto descreve composição e exposição; a interpretação fica na
nota técnica.

## 11. Critérios de aceite

1. Qualquer um dos 5.570 municípios é encontrável por busca e renderiza contracheque completo.
2. O contracheque nunca totaliza pessoas; o rodapé soma apenas R$.
3. Cada linha exibe sua unidade explicitamente.
4. As quatro linhas do seletor de exposição têm peso visual idêntico.
5. O ranking vem filtrado por faixa populacional por padrão.
6. Dado ausente aparece como `—` com motivo, nunca como zero.
7. Lighthouse ≥ 95 em acessibilidade; navegação completa por teclado.
8. A página carrega e exibe um município padrão sem JavaScript.
9. Bloco 3 lista todas as exclusões da seção 6 do plano de discovery.
10. Dataset harmonizado e dicionário de dados publicados e linkados na página.
11. Nenhuma ocorrência de "dependência" ou "vulnerabilidade" na interface.

## 12. Riscos de produto

| Risco | Mitigação |
|---|---|
| Usuário soma as taxas por 100 adultos | Nota fixa + teste de 5 segundos (E4) |
| Usuário acha que o contracheque é dele | Cabeçalho com nome do município em destaque máximo |
| Ranking usado como manchete descontextualizada | Estratificação obrigatória + distribuição sempre visível |
| Beeswarm ilegível em mobile | Plano B: strip plot com jitter, decidido até o fim da semana 3 |
| Página não fica pronta | Corte planejado: submeter só o Bloco 1. Uma peça acabada pontua mais que duas pela metade |
