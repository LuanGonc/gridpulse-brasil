# GridPulse Brasil

Lakehouse serverless na AWS para análise da relação entre demanda elétrica, clima e risco de pico de carga no Brasil.

## Problema

A demanda elétrica pode variar conforme fatores climáticos, especialmente temperatura. O objetivo deste projeto é construir uma plataforma de dados capaz de integrar dados públicos de energia e clima, gerar camadas analíticas e identificar dias críticos de demanda.

## Objetivo

Construir um pipeline de engenharia de dados usando AWS, arquitetura Medallion e dados públicos para analisar a relação entre carga elétrica e variáveis climáticas.

## Stack

- Python
- Pandas
- Boto3
- AWS S3
- AWS Glue Data Catalog
- AWS Glue Crawler
- Amazon Athena
- Parquet
- Streamlit
- Plotly

## Arquitetura

```text
ONS API + INMET Historical Data
        ↓
S3 Bronze
        ↓
Python Transformations
        ↓
S3 Silver - Parquet
        ↓
Glue Data Catalog
        ↓
Athena
        ↓
S3 Gold
        ↓
Streamlit Dashboard
```


## Camadas Medallion
 **Bronze**

Dados crus preservados no formato original:

*ONS:* JSON da API de carga verificada
*INMET:* ZIP/CSV histórico das estações automáticas

**Silver**

Dados limpos, tipados, deduplicados e particionados em Parquet.

**Gold**

Tabelas analíticas:

- demanda_diaria_area
- clima_diario_area
- demanda_clima_diaria
- dias_criticos_demanda_clima
- Principais resultados
- 365 dias analisados em 2025
- Correlação positiva entre carga elétrica média e temperatura média
- Score de risco diário combinando demanda elétrica e clima
- Identificação de dias críticos com risco alto de pico de demanda
- Dashboard

O dashboard permite visualizar:

- Série temporal de carga e temperatura
- Distribuição dos níveis de risco
- Resumo mensal do risco
- Ranking dos dias mais críticos
- Correlação entre demanda elétrica e temperatura

## Como executar localmente
pip install -r requirements.txt
streamlit run dashboard/app.py

Configure o arquivo .env com:

```text
AWS_PROFILE=gridpulse-dev
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name
ATHENA_DATABASE=gridpulse_gold
ATHENA_OUTPUT_LOCATION=s3://your-bucket-name/athena-results/
```

A ordem para rodar no Athena é:

1. create_demanda_diaria_area.sql
2. create_clima_diario_area.sql
3. create_demanda_clima_diaria.sql
4. create_dias_criticos_demanda_clima.sql