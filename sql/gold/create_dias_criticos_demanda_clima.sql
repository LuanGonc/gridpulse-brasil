CREATE TABLE gridpulse_gold.dias_criticos_demanda_clima
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://gridpulse-brasil-luan-dev/gold/analytics/dias_criticos_demanda_clima/',
    partitioned_by = ARRAY['ano', 'mes']
) AS
WITH thresholds AS (
    SELECT
        area_carga,

        approx_percentile(carga_media_mwmed, 0.95) AS p95_carga_media_mwmed,
        approx_percentile(carga_maxima_mwmed, 0.95) AS p95_carga_maxima_mwmed,
        approx_percentile(amplitude_carga_mwmed, 0.90) AS p90_amplitude_carga_mwmed,

        approx_percentile(temperatura_media_c, 0.90) AS p90_temperatura_media_c,
        approx_percentile(temperatura_max_observada_c, 0.90) AS p90_temperatura_max_c

    FROM gridpulse_gold.demanda_clima_diaria
    GROUP BY area_carga
),

scored AS (
    SELECT
        d.area_carga,
        d.data_referencia,

        d.qtd_medicoes_demanda,
        d.qtd_observacoes_clima,
        d.qtd_estacoes,

        d.carga_media_mwmed,
        d.carga_minima_mwmed,
        d.carga_maxima_mwmed,
        d.amplitude_carga_mwmed,

        d.temperatura_media_c,
        d.temperatura_max_observada_c,
        d.temperatura_min_observada_c,
        d.umidade_media_pct,
        d.precipitacao_total_mm,
        d.radiacao_media_kj_m2,
        d.vento_velocidade_media_ms,

        t.p95_carga_media_mwmed,
        t.p95_carga_maxima_mwmed,
        t.p90_amplitude_carga_mwmed,
        t.p90_temperatura_media_c,
        t.p90_temperatura_max_c,

        CASE
            WHEN d.carga_media_mwmed >= t.p95_carga_media_mwmed THEN 1
            ELSE 0
        END AS flag_carga_media_alta,

        CASE
            WHEN d.carga_maxima_mwmed >= t.p95_carga_maxima_mwmed THEN 1
            ELSE 0
        END AS flag_pico_carga_alto,

        CASE
            WHEN d.amplitude_carga_mwmed >= t.p90_amplitude_carga_mwmed THEN 1
            ELSE 0
        END AS flag_amplitude_alta,

        CASE
            WHEN d.temperatura_media_c >= t.p90_temperatura_media_c THEN 1
            ELSE 0
        END AS flag_temperatura_media_alta,

        CASE
            WHEN d.temperatura_max_observada_c >= t.p90_temperatura_max_c THEN 1
            ELSE 0
        END AS flag_temperatura_maxima_alta

    FROM gridpulse_gold.demanda_clima_diaria d
    INNER JOIN thresholds t
        ON d.area_carga = t.area_carga
),

final AS (
    SELECT
        area_carga,
        data_referencia,

        qtd_medicoes_demanda,
        qtd_observacoes_clima,
        qtd_estacoes,

        carga_media_mwmed,
        carga_minima_mwmed,
        carga_maxima_mwmed,
        amplitude_carga_mwmed,

        temperatura_media_c,
        temperatura_max_observada_c,
        temperatura_min_observada_c,
        umidade_media_pct,
        precipitacao_total_mm,
        radiacao_media_kj_m2,
        vento_velocidade_media_ms,

        p95_carga_media_mwmed,
        p95_carga_maxima_mwmed,
        p90_amplitude_carga_mwmed,
        p90_temperatura_media_c,
        p90_temperatura_max_c,

        flag_carga_media_alta,
        flag_pico_carga_alto,
        flag_amplitude_alta,
        flag_temperatura_media_alta,
        flag_temperatura_maxima_alta,

        (
            flag_carga_media_alta * 25
            + flag_pico_carga_alto * 20
            + flag_temperatura_media_alta * 20
            + flag_temperatura_maxima_alta * 15
            + flag_amplitude_alta * 10
            + CASE
                WHEN flag_pico_carga_alto = 1
                 AND flag_temperatura_maxima_alta = 1 THEN 10
                ELSE 0
              END
        ) AS risk_score,

        CASE
            WHEN (
                flag_carga_media_alta * 25
                + flag_pico_carga_alto * 20
                + flag_temperatura_media_alta * 20
                + flag_temperatura_maxima_alta * 15
                + flag_amplitude_alta * 10
                + CASE
                    WHEN flag_pico_carga_alto = 1
                     AND flag_temperatura_maxima_alta = 1 THEN 10
                    ELSE 0
                  END
            ) >= 70 THEN 'ALTO'
            WHEN (
                flag_carga_media_alta * 25
                + flag_pico_carga_alto * 20
                + flag_temperatura_media_alta * 20
                + flag_temperatura_maxima_alta * 15
                + flag_amplitude_alta * 10
                + CASE
                    WHEN flag_pico_carga_alto = 1
                     AND flag_temperatura_maxima_alta = 1 THEN 10
                    ELSE 0
                  END
            ) >= 40 THEN 'MEDIO'
            ELSE 'BAIXO'
        END AS nivel_risco,

        CAST(year(data_referencia) AS varchar) AS ano,
        lpad(CAST(month(data_referencia) AS varchar), 2, '0') AS mes

    FROM scored
)

SELECT *
FROM final;