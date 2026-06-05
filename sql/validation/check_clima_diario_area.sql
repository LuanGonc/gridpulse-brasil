SELECT
    area_carga,
    COUNT(*) AS qtd_dias,
    MIN(data_referencia) AS inicio,
    MAX(data_referencia) AS fim,
    AVG(temperatura_media_c) AS temperatura_media_c,
    MAX(temperatura_max_observada_c) AS maior_temperatura_observada_c,
    AVG(umidade_media_pct) AS umidade_media_pct,
    SUM(precipitacao_total_mm) AS precipitacao_total_mm,
    AVG(qtd_estacoes) AS media_estacoes_por_dia
FROM gridpulse_gold.clima_diario_area
GROUP BY
    area_carga
ORDER BY
    area_carga;