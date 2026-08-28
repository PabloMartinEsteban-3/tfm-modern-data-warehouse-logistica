-- =====================================================================
-- CONSULTAS ANALITICAS DE REFERENCIA (Anexo D de la memoria)
--
-- Ejecuta cada una tres veces sobre fact_servicio y sobre
-- fact_servicio_control, y anota la mediana del tiempo de ejecucion.
-- Esa tabla comparativa es el resultado del objetivo OE3.
--
-- Para ver el tiempo real: consulta SVL_QUERY_REPORT o STL_QUERY.
-- =====================================================================

-- Q1. Panoramica mensual de flota
SELECT t.anio, t.mes,
       COUNT(*)                    AS n_servicios,
       AVG(f.duracion_min)         AS duracion_media,
       AVG(f.velocidad_kmh)        AS velocidad_media,
       AVG(f.desviacion_eta_pct)   AS desviacion_media_eta
FROM fact_servicio f
JOIN dim_tiempo t ON f.sk_tiempo = t.sk_tiempo
GROUP BY t.anio, t.mes
ORDER BY t.anio, t.mes;

-- Q2. Corredores menos fiables (el hallazgo analitico principal)
SELECT zo.nombre_zona AS origen,
       zd.nombre_zona AS destino,
       f.franja_horaria,
       COUNT(*)                      AS n_servicios,
       AVG(f.eta_referencia_min)     AS eta_mediana,
       AVG(f.fiabilidad_corredor)    AS fiabilidad
FROM fact_servicio f
JOIN dim_zona zo ON f.sk_zona_origen  = zo.sk_zona
JOIN dim_zona zd ON f.sk_zona_destino = zd.sk_zona
GROUP BY 1, 2, 3
HAVING COUNT(*) > 500
ORDER BY fiabilidad DESC
LIMIT 25;

-- Q3. Degradacion temporal por franja horaria y dia de la semana
SELECT t.nombre_dia, f.franja_horaria,
       AVG(f.duracion_min)       AS duracion_media,
       AVG(f.desviacion_eta_pct) AS desviacion_media,
       AVG(f.velocidad_kmh)      AS velocidad_media
FROM fact_servicio f
JOIN dim_tiempo t ON f.sk_tiempo = t.sk_tiempo
GROUP BY 1, 2
ORDER BY t.nombre_dia, f.franja_horaria;

-- Q4. Eficiencia de ruta: zonas con mayor factor de rodeo
SELECT zo.distrito, zo.nombre_zona,
       COUNT(*)               AS n_servicios,
       AVG(f.factor_rodeo)    AS rodeo_medio,
       AVG(f.distancia_km)    AS distancia_media
FROM fact_servicio f
JOIN dim_zona zo ON f.sk_zona_origen = zo.sk_zona
WHERE f.factor_rodeo IS NOT NULL
GROUP BY 1, 2
HAVING COUNT(*) > 1000
ORDER BY rodeo_medio DESC
LIMIT 20;

-- Q5. Consulta con filtro selectivo por rango de fechas
--     (la que mas se beneficia de la SORTKEY: comparala con la de control)
SELECT zo.distrito,
       COUNT(*)             AS n_servicios,
       AVG(f.duracion_min)  AS duracion_media
FROM fact_servicio f
JOIN dim_tiempo t ON f.sk_tiempo = t.sk_tiempo
JOIN dim_zona zo  ON f.sk_zona_origen = zo.sk_zona
WHERE t.fecha BETWEEN '2023-02-01' AND '2023-02-14'
GROUP BY 1
ORDER BY n_servicios DESC;
