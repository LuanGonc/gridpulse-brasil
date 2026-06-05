# Pipeline ETL/ELT

## Visão geral

O pipeline do **GridPulse Brasil** combina ingestão em Python, transformação local para Silver e materialização analítica com SQL no Athena.

Ele pode ser entendido como um fluxo híbrido de **ETL** e **ELT**:

```text
Extract:
    coleta de dados do ONS e INMET

Load:
    gravação dos dados crus na camada Bronze do S3

Transform:
    transformação para Silver em Python
    transformação para Gold em Athena SQL
```

---

## Fontes de dados

### ONS

Fonte usada para obter dados de carga elétrica verificada por área de carga.

Áreas utilizadas:

- `SECO`
- `S`
- `NE`
- `N`

Exemplo de execução:

```bash
python src/ingestion/ingest_ons_carga.py --area SECO --start 2025-01-01 --end 2025-12-31
```

---

### INMET

Fonte usada para obter dados históricos das estações meteorológicas automáticas.

O pipeline baixa o pacote anual, extrai os CSVs e transforma observações horárias em dados estruturados.

---

## Camada Bronze

### ONS Bronze

Formato:

```text
bronze/ons/carga_verificada/area=SECO/dat_inicio=2025-01-01/dat_fim=2025-01-31/ingestion_timestamp=.../data.json
```

Características:

- JSON bruto;
- dados preservados conforme retornados pela API;
- particionamento lógico por área, período e timestamp de ingestão.

---

### INMET Bronze

Formato:

```text
bronze/inmet/dados_historicos/ano=2025/ingestion_timestamp=.../inmet_dados_historicos_2025.zip
```

Características:

- ZIP bruto da fonte;
- CSVs extraídos localmente;
- preservação do pacote original.

---

## Camada Silver

### ONS Silver

Script:

```text
src/transformation/transform_ons_carga_to_silver.py
```

Transformações aplicadas:

- leitura dos JSONs Bronze;
- validação de colunas obrigatórias;
- criação de colunas opcionais ausentes;
- renomeação de colunas;
- conversão de datas e timestamps;
- conversão de métricas para número;
- remoção de duplicatas;
- particionamento por `area_carga`, `ano`, `mes`;
- gravação em Parquet;
- upload para S3.

Chave lógica:

```text
area_carga + referencia_utc
```

---

### INMET Silver

Script:

```text
src/transformation/transform_inmet_to_silver.py
```

Transformações aplicadas:

- leitura dos CSVs extraídos;
- extração de metadados da estação;
- normalização de textos;
- conversão de vírgula decimal para ponto;
- mapeamento UF para área de carga;
- criação de timestamp UTC;
- remoção de linhas sem chaves críticas;
- deduplicação;
- particionamento por `area_carga`, `uf`, `ano`, `mes`;
- gravação em Parquet;
- upload para S3.

Chave lógica:

```text
codigo_estacao + data_hora_utc
```

---

## Camada Gold

A camada Gold é criada com SQL no Athena.

Ordem de criação:

```text
1. demanda_diaria_area
2. clima_diario_area
3. demanda_clima_diaria
4. dias_criticos_demanda_clima
```

---

### 1. demanda_diaria_area

Agrega a carga elétrica por área e dia.

Fonte:

```text
gridpulse_silver.ons_carga_verificada
```

Granularidade:

```text
area_carga + data_referencia
```

---

### 2. clima_diario_area

Agrega observações meteorológicas por área e dia.

Fonte:

```text
gridpulse_silver.inmet_observacoes_horarias
```

Granularidade:

```text
area_carga + data_referencia
```

---

### 3. demanda_clima_diaria

Integra demanda e clima.

Fontes:

```text
gridpulse_gold.demanda_diaria_area
gridpulse_gold.clima_diario_area
```

Join:

```sql
d.area_carga = c.area_carga
AND d.data_referencia = c.data_referencia
```

---

### 4. dias_criticos_demanda_clima

Calcula:

- percentis;
- flags de carga alta;
- flags de temperatura alta;
- score de risco;
- nível de risco.

Fonte:

```text
gridpulse_gold.demanda_clima_diaria
```

---

## Validação

O projeto possui queries de validação em:

```text
sql/validation/
```

Essas queries verificam:

- contagem de dias;
- período disponível;
- quantidade de registros;
- quantidade de estações;
- correlação carga x temperatura;
- distribuição dos níveis de risco.

---

## Observações de engenharia

### Idempotência parcial

As transformações recriam as camadas Silver e Gold a partir das fontes disponíveis. Para evitar dados duplicados, os prefixos no S3 são limpos antes de recriar tabelas derivadas.

### Deduplicação

A deduplicação evita registros duplicados em reprocessamentos.

### Particionamento

O particionamento melhora consultas no Athena e reduz leitura desnecessária.

Exemplos:

```text
area_carga=SECO/ano=2025/mes=01/
area_carga=SECO/uf=RJ/ano=2025/mes=01/
```