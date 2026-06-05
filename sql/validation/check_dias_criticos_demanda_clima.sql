SELECT
    nivel_risco,
    COUNT(*) AS qtd_dias
FROM gridpulse_gold.dias_criticos_demanda_clima
GROUP BY nivel_risco
ORDER BY qtd_dias DESC;

SELECT
    data_referencia,
    area_carga,
    risk_score,
    nivel_risco,
    carga_media_mwmed,
    carga_maxima_mwmed,
    temperatura_media_c,
    temperatura_max_observada_c
FROM gridpulse_gold.dias_criticos_demanda_clima
ORDER BY risk_score DESC, carga_maxima_mwmed DESC
LIMIT 20;