CREATE TABLE gridpulse_gold.demanda_clima_diaria
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://gridpulse-brasil-luan-dev/gold/analytics/demanda_clima_diaria/',
    partitioned_by = ARRAY['ano', 'mes']
) AS
SELECT
    d.area_carga,
    d.data_referencia,

    d.qtd_medicoes AS qtd_medicoes_demanda,
    d.carga_media_mwmed,
    d.carga_minima_mwmed,
    d.carga_maxima_mwmed,
    d.amplitude_carga_mwmed,

    c.qtd_observacoes_horarias AS qtd_observacoes_clima,
    c.qtd_estacoes,
    c.temperatura_media_c,
    c.temperatura_max_observada_c,
    c.temperatura_min_observada_c,
    c.umidade_media_pct,
    c.precipitacao_total_mm,
    c.radiacao_media_kj_m2,
    c.vento_velocidade_media_ms,

    d.carga_media_mwmed / NULLIF(c.temperatura_media_c, 0) AS carga_por_grau_mwmed,

    CAST(year(d.data_referencia) AS varchar) AS ano,
    lpad(CAST(month(d.data_referencia) AS varchar), 2, '0') AS mes
FROM gridpulse_gold.demanda_diaria_area d
INNER JOIN gridpulse_gold.clima_diario_area c
    ON d.area_carga = c.area_carga
   AND d.data_referencia = c.data_referencia;