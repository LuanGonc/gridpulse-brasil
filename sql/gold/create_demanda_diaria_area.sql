CREATE TABLE gridpulse_gold.demanda_diaria_area
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://gridpulse-brasil-luan-dev/gold/energy_demand/demanda_diaria_area/',
    partitioned_by = ARRAY['ano', 'mes']
) AS
WITH base AS (
    SELECT
        area_carga,
        CAST(data_referencia AS date) AS data_referencia,
        referencia_utc,
        carga_global_mwmed,
        carga_mmgd_mwmed,
        carga_supervisionada_mwmed,
        carga_nao_supervisionada_mwmed
    FROM gridpulse_silver.ons_carga_verificada
)
SELECT
    area_carga,
    data_referencia,

    COUNT(*) AS qtd_medicoes,

    MIN(referencia_utc) AS primeira_medicao_utc,
    MAX(referencia_utc) AS ultima_medicao_utc,

    AVG(carga_global_mwmed) AS carga_media_mwmed,
    MIN(carga_global_mwmed) AS carga_minima_mwmed,
    MAX(carga_global_mwmed) AS carga_maxima_mwmed,

    MAX(carga_global_mwmed) - MIN(carga_global_mwmed) AS amplitude_carga_mwmed,

    AVG(carga_mmgd_mwmed) AS carga_mmgd_media_mwmed,
    AVG(carga_supervisionada_mwmed) AS carga_supervisionada_media_mwmed,
    AVG(carga_nao_supervisionada_mwmed) AS carga_nao_supervisionada_media_mwmed,

    CAST(year(data_referencia) AS varchar) AS ano,
    lpad(CAST(month(data_referencia) AS varchar), 2, '0') AS mes
FROM base
GROUP BY
    area_carga,
    data_referencia;