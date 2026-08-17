# Dicionário de dados — painel municipal

Uma linha por município. Valores monetários em reais nominais do mês de referência.

| Coluna | Descrição | Unidade |
|---|---|---|
| `cod_ibge` | Código IBGE de 7 dígitos | — |
| `nome`, `uf`, `regiao` | Identificação | — |
| `pop_total` | População residente estimada | pessoas |
| `pop_adulta` | População com 18 anos ou mais | pessoas |
| `salario_privado_n` | Salário — setor privado — contagem (RAIS) | **vinculos** |
| `salario_privado_massa` | Salário — setor privado — massa mensal | R$ |
| `salario_privado_medio` | Salário — setor privado — valor médio (base: 0.7 a 30.0 SM) | R$ / vinculo |
| `salario_privado_part` | Salário — setor privado — participação na massa total | proporção |
| `salario_privado_por100` | Salário — setor privado — por 100 adultos | taxa |
| `salario_publico_n` | Salário — administração pública — contagem (RAIS) | **vinculos** |
| `salario_publico_massa` | Salário — administração pública — massa mensal | R$ |
| `salario_publico_medio` | Salário — administração pública — valor médio (base: 0.7 a 30.0 SM) | R$ / vinculo |
| `salario_publico_part` | Salário — administração pública — participação na massa total | proporção |
| `salario_publico_por100` | Salário — administração pública — por 100 adultos | taxa |
| `previdencia_n` | Previdência — INSS/BPC — contagem (INSS) | **beneficios** |
| `previdencia_massa` | Previdência — INSS/BPC — massa mensal | R$ |
| `previdencia_medio` | Previdência — INSS/BPC — valor médio | R$ / beneficio |
| `previdencia_part` | Previdência — INSS/BPC — participação na massa total | proporção |
| `previdencia_por100` | Previdência — INSS/BPC — por 100 adultos | taxa |
| `bolsa_familia_n` | Benefício social — Bolsa Família — contagem (Portal da Transparência) | **familias** |
| `bolsa_familia_massa` | Benefício social — Bolsa Família — massa mensal | R$ |
| `bolsa_familia_medio` | Benefício social — Bolsa Família — valor médio | R$ / familia |
| `bolsa_familia_part` | Benefício social — Bolsa Família — participação na massa total | proporção |
| `bolsa_familia_por100` | Benefício social — Bolsa Família — por 100 adultos | taxa |
| `massa_total` | Soma das quatro massas | R$ |
| `massa_per_capita` | Massa total ÷ população | R$ |
| `porte` | Faixa populacional | — |

## Atenção às unidades

As colunas `_n` **não são comparáveis entre si e não devem ser somadas**. A RAIS conta vínculos, o INSS conta benefícios emitidos e o Bolsa Família conta famílias. Uma mesma pessoa pode aparecer em mais de uma fonte. As colunas `_por100` existem justamente para permitir leitura relativa sem induzir soma — elas podem ultrapassar 100 no conjunto, e isso não é erro.

As colunas `_massa` **são** somáveis: representam fluxos de dinheiro distintos.
