SELECT
    area_carga,
    MIN(data_referencia) AS inicio,
    MAX(data_referencia) AS fim,
    COUNT(*) AS qtd_dias,
    corr(carga_media_mwmed, temperatura_media_c) AS correlacao_carga_temperatura_media,
    corr(carga_maxima_mwmed, temperatura_max_observada_c) AS correlacao_pico_temperatura_maxima
FROM gridpulse_gold.demanda_clima_diaria
GROUP BY area_carga;