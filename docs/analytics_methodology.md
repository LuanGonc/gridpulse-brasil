# Metodologia Analítica

## Objetivo

A metodologia analítica do **GridPulse Brasil** busca identificar dias críticos de demanda elétrica combinando indicadores de carga e clima.

A hipótese inicial é:

> Temperaturas mais elevadas podem estar associadas a maior demanda elétrica, especialmente por aumento do uso de refrigeração.

---

## Tabela base da análise

A análise parte da tabela:

```text
gridpulse_gold.demanda_clima_diaria
```

Essa tabela combina:

- demanda elétrica diária;
- clima diário;
- área de carga;
- data de referência.

---

## Granularidade

A granularidade da análise é:

```text
uma linha = uma área de carga em um dia
```

Essa granularidade permite comparar regiões e períodos de forma consistente.

---

## Correlação

O dashboard calcula correlação entre:

```text
carga_media_mwmed
temperatura_media_c
```

A correlação é usada como indicador exploratório da relação entre carga elétrica e temperatura.

---

## Interpretação da correlação

A correlação indica associação linear entre duas variáveis.

Importante:

> Correlação não implica causalidade.

Uma correlação positiva entre carga e temperatura sugere que as variáveis se movem juntas, mas não prova que a temperatura causou diretamente o aumento da carga.

---

## Score de risco

A tabela:

```text
gridpulse_gold.dias_criticos_demanda_clima
```

calcula um score de risco diário entre 0 e 100.

O score combina indicadores de demanda e clima com base em percentis históricos de cada área de carga.

---

## Por que usar percentis por área?

As áreas de carga têm escalas diferentes.

Por exemplo, o SECO tende a ter carga absoluta maior que outras áreas.

Por isso, o score é calculado em relação ao histórico da própria área.

Um dia de risco alto na área `N` significa:

```text
esse dia foi extremo em relação ao comportamento histórico da área N
```

Não significa necessariamente que a carga absoluta foi maior do que na área `SECO`.

---

## Regras do score

| Condição | Pontos |
|---|---:|
| Carga média >= P95 da área | 25 |
| Carga máxima >= P95 da área | 20 |
| Temperatura média >= P90 da área | 20 |
| Temperatura máxima >= P90 da área | 15 |
| Amplitude de carga >= P90 da área | 10 |
| Pico de carga alto + temperatura máxima alta | 10 |

---

## Classificação do risco

| Score | Nível |
|---:|---|
| 0 a 39 | BAIXO |
| 40 a 69 | MEDIO |
| 70 a 100 | ALTO |

---

## Explicabilidade

O score é explicável porque cada componente é representado por flags.

Exemplo de interpretação:

```text
Dia X:
- carga média acima do P95;
- pico de carga acima do P95;
- temperatura máxima acima do P90;
- combinação de pico de carga com temperatura elevada.
```

Isso permite entender por que um dia foi classificado como crítico.

---

## Principais métricas

### Métricas de demanda

- carga média diária;
- carga máxima diária;
- carga mínima diária;
- amplitude diária da carga.

### Métricas climáticas

- temperatura média diária;
- temperatura máxima observada;
- temperatura mínima observada;
- umidade média;
- precipitação total;
- radiação média;
- velocidade média do vento.

### Métricas de risco

- score de risco;
- nível de risco;
- flags de carga alta;
- flags de temperatura alta.

---

## Limitações

A metodologia possui limitações importantes:

- o score é baseado em regras, não em aprendizado supervisionado;
- o mapeamento clima -> área de carga é aproximado por UF;
- a análise não considera feriados;
- a análise não considera atividade econômica;
- a análise não considera eventos extremos específicos;
- a análise não considera restrições operacionais do sistema elétrico;
- correlação não implica causalidade.

---

## Melhorias futuras

Possíveis evoluções:

- adicionar múltiplos anos históricos;
- incluir calendário de feriados;
- criar variáveis de defasagem térmica;
- treinar modelo preditivo de carga;
- avaliar anomalias com Isolation Forest;
- criar comparação sazonal por estação do ano;
- integrar dados de geração solar distribuída;
- adicionar monitoramento de qualidade de dados.