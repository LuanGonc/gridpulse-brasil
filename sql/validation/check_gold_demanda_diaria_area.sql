SELECT
    area_carga,
    ano,
    mes,
    COUNT(*) AS qtd_dias,
    AVG(carga_media_mwmed) AS media_mensal_mwmed,
    MAX(carga_maxima_mwmed) AS maior_pico_mensal_mwmed,
    AVG(amplitude_carga_mwmed) AS amplitude_media_diaria_mwmed
FROM gridpulse_gold.demanda_diaria_area
GROUP BY
    area_carga,
    ano,
    mes
ORDER BY
    ano,
    mes,
    area_carga;