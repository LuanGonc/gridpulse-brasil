CREATE TABLE gridpulse_gold.clima_diario_area
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://{{S3_BUCKET}}/gold/weather/clima_diario_area/',
    partitioned_by = ARRAY['ano', 'mes']
) AS
WITH base AS (
    SELECT
        area_carga,
        CAST(data_referencia AS date) AS data_referencia,
        codigo_estacao,
        uf,
        temperatura_ar_c,
        temperatura_max_c,
        temperatura_min_c,
        umidade_relativa_pct,
        precipitacao_total_mm,
        radiacao_global_kj_m2,
        vento_velocidade_ms
    FROM gridpulse_silver.inmet_observacoes_horarias
    WHERE area_carga IS NOT NULL
      AND data_referencia IS NOT NULL
      AND temperatura_ar_c IS NOT NULL
)
SELECT
    area_carga,
    data_referencia,

    COUNT(*) AS qtd_observacoes_horarias,
    COUNT(DISTINCT codigo_estacao) AS qtd_estacoes,

    AVG(temperatura_ar_c) AS temperatura_media_c,
    MAX(temperatura_ar_c) AS temperatura_max_observada_c,
    MIN(temperatura_ar_c) AS temperatura_min_observada_c,

    AVG(temperatura_max_c) AS temperatura_max_media_estacoes_c,
    AVG(temperatura_min_c) AS temperatura_min_media_estacoes_c,

    AVG(umidade_relativa_pct) AS umidade_media_pct,

    SUM(COALESCE(precipitacao_total_mm, 0)) AS precipitacao_total_mm,

    AVG(radiacao_global_kj_m2) AS radiacao_media_kj_m2,
    AVG(vento_velocidade_ms) AS vento_velocidade_media_ms,

    CAST(year(data_referencia) AS varchar) AS ano,
    lpad(CAST(month(data_referencia) AS varchar), 2, '0') AS mes
FROM base
GROUP BY
    area_carga,
    data_referencia;
