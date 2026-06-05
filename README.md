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