# GridPulse Brasil

Lakehouse serverless na AWS para análise de demanda elétrica brasileira usando dados públicos do ONS.

## Objetivo

Construir uma arquitetura Medallion na AWS para ingerir, transformar, catalogar e consultar dados públicos de carga elétrica brasileira.

## Stack

- Python
- AWS S3
- AWS Glue Data Catalog
- AWS Glue Crawler
- Amazon Athena
- Parquet
- Pandas
- Boto3

## Arquitetura

```text
ONS API
  -> S3 Bronze: JSON cru
  -> Python Transform
  -> S3 Silver: Parquet limpo e particionado
  -> Glue Data Catalog
  -> Athena
  -> S3 Gold: tabelas analíticas
```


## Analytics: dias críticos de demanda

A tabela `gridpulse_gold.dias_criticos_demanda_clima` calcula um score de risco diário combinando métricas de demanda elétrica e clima.

O score considera:

- carga média acima do percentil 95
- carga máxima acima do percentil 95
- temperatura média acima do percentil 90
- temperatura máxima acima do percentil 90
- amplitude de carga acima do percentil 90
- combinação de pico de carga com temperatura máxima elevada

O resultado classifica cada dia em `BAIXO`, `MEDIO` ou `ALTO` risco.