# Controle de Custos

## Visão geral

O **GridPulse Brasil** foi desenhado para rodar com baixo custo em uma conta pessoal da AWS.

A estratégia foi usar serviços serverless e sob demanda, evitando infraestrutura provisionada continuamente.

---

## Estratégia geral

Principais decisões de custo:

- usar S3 como armazenamento central;
- usar Athena para consultas SQL sob demanda;
- usar Glue Crawler apenas manualmente;
- armazenar Silver e Gold em Parquet;
- particionar os dados por área, UF, ano e mês;
- evitar clusters persistentes;
- evitar Redshift, EMR, Kinesis ou RDS no MVP;
- usar Streamlit local para dashboard.

---

## Serviços utilizados

### Amazon S3

O S3 armazena as camadas:

```text
bronze/
silver/
gold/
athena-results/
logs/
```

Boas práticas:

- bloquear acesso público;
- separar camadas por prefixo;
- evitar versionar dados no GitHub;
- limpar resultados temporários quando necessário;
- usar lifecycle rules futuramente para logs e resultados antigos.

---

### Amazon Athena

O Athena é usado para consultar dados no S3.

Boas práticas aplicadas:

- uso de Parquet;
- uso de particionamento;
- filtros por partições;
- evitar consultas desnecessárias;
- cache no dashboard Streamlit;
- armazenamento dos resultados em prefixo controlado.

Exemplo de filtro eficiente:

```sql
WHERE area_carga = 'SECO'
  AND ano = '2025'
  AND mes = '01'
```

---

### AWS Glue

O Glue é usado para:

- Data Catalog;
- Crawlers de descoberta de schema;
- atualização de partições.

Boas práticas aplicadas:

- crawlers sob demanda;
- sem jobs Glue no MVP;
- evitar execuções repetidas sem necessidade.

---

## Por que Parquet ajuda no custo?

Parquet é um formato colunar.

Em consultas analíticas, isso permite ler apenas as colunas necessárias, reduzindo o volume escaneado pelo Athena.

Além disso, o particionamento ajuda a reduzir a quantidade de arquivos lidos quando a consulta filtra por:

- área de carga;
- UF;
- ano;
- mês.

---

## Cuidados recomendados

Para manter o projeto barato:

- criar AWS Budget com alerta mensal;
- não deixar crawlers agendados sem necessidade;
- evitar serviços provisionados;
- limpar resultados antigos do Athena;
- revisar o Billing periodicamente;
- manter dados de teste controlados;
- evitar `SELECT *` em tabelas grandes.

---

## Recursos evitados no MVP

O projeto não usa:

- Amazon Redshift;
- Amazon EMR;
- Amazon Kinesis;
- Amazon MSK;
- Amazon RDS;
- Glue Jobs permanentes;
- infraestrutura sempre ligada.

Esses serviços podem ser úteis em cenários reais maiores, mas não são necessários para o escopo atual do portfólio.

---

## Conclusão

A arquitetura escolhida permite demonstrar conceitos reais de Engenharia de Dados na AWS sem depender de infraestrutura cara ou permanentemente ativa.

O projeto prioriza:

- baixo custo;
- simplicidade operacional;
- uso de serviços gerenciados;
- escalabilidade futura.