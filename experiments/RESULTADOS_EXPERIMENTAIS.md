# Resultados experimentais do N-Puzzle Genetic Solver

## Fonte dos dados

Este relatório foi preparado com base nos arquivos CSV persistidos em `experiments/results`:

- `baseline_runs.csv`
- `normalization_ab_experiment.csv`

A análise considera apenas os dados armazenados nesses arquivos e não introduz novas hipóteses sobre desempenho fora do conjunto avaliado.

## 1. Baseline consolidado

O arquivo `baseline_runs.csv` contém 21 execuções no total. Os resultados observados foram:

- 9 execuções com solução concluída;
- 12 execuções sem solução dentro do limite configurado;
- taxa de sucesso global: 9 / 21 = 42,86%.

### Distribuição por cenário

| Cenário | Execuções | Soluções | Taxa de sucesso |
|---|---:|---:|---:|
| 3x3_goal | 3 | 3 | 100,00% |
| 3x3_one_move | 3 | 3 | 100,00% |
| 3x3_medium | 3 | 3 | 100,00% |
| 3x3_hard_seed_21 | 3 | 0 | 0,00% |
| 4x4_seed_100 | 3 | 0 | 0,00% |
| 4x4_seed_101 | 3 | 0 | 0,00% |
| 4x4_seed_102 | 3 | 0 | 0,00% |

### Observação

Os cenários 3x3 mais simples e intermediários foram resolvidos em todas as execuções. Já o cenário 3x3 mais difícil e todos os 4x4 avaliados ficaram sem solução dentro do orçamento de busca utilizado no baseline.

## 2. Comparação A/B: normalização vs. sem normalização

O arquivo `normalization_ab_experiment.csv` apresenta 42 linhas, contendo 21 execuções para cada variante:

- `normalized`
- `no_normalization`

### Resultado agregado

| Variante | Execuções | Soluções | Taxa de sucesso |
|---|---:|---:|---:|
| normalized | 21 | 9 | 42,86% |
| no_normalization | 21 | 9 | 42,86% |

### Conclusão observada no conjunto de dados

A partir dos valores armazenados no CSV, não houve diferença na taxa global de sucesso entre as duas variantes. Em outras palavras, os dados persistidos não indicam melhoria mensurável em `normalized` em relação a `no_normalization` para as instâncias registradas.

## 3. Interpretação estritamente apoiada nos dados

Os resultados verificados sugerem:

- o algoritmo apresenta desempenho elevado em estados 3x3 fáceis ou próximos do objetivo;
- o cenário 3x3 mais difícil e todos os 4x4 avaliados permanecem sem solução para a configuração experimental registrada;
- a normalização de cromossomos não alterou a taxa de sucesso observada nas execuções persistidas.

Não é possível afirmar, com base apenas nesses arquivos, que a normalização melhora a convergência em geral, pois o conjunto experimental não mostrou diferença relevante entre as variantes.

## 4. Validação técnica

A validação executada no ambiente local confirmou as contagens registradas:

- 21 linhas em `baseline_runs.csv`;
- 9 soluções no baseline;
- 42,86% de taxa de sucesso global;
- 21 linhas por variante em `normalization_ab_experiment.csv`;
- 9 soluções por variante;
- 42,86% de taxa de sucesso para cada variante.

## 5. Encerramento

Este documento reúne apenas o resultado dos dados experimentais persistidos e validados no projeto. Ele não estabelece nova otimização ou nova melhoria de algoritmo e deve ser interpretado como um registro factual do desempenho observado para as configurações testadas.
