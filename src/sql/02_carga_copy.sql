-- Carga paralela desde S3. Sustituye <cuenta> y el bucket por los tuyos.
-- Mide el tiempo de cada COPY: va a la seccion 4.7.3.

COPY dim_zona
FROM 's3://tfm-logistica-pablo/silver/dim_zona/'
IAM_ROLE 'arn:aws:iam::<cuenta>:role/RedshiftCopyRole'
FORMAT AS PARQUET;

COPY dim_tiempo
FROM 's3://tfm-logistica-pablo/silver/dim_tiempo/'
IAM_ROLE 'arn:aws:iam::<cuenta>:role/RedshiftCopyRole'
FORMAT AS PARQUET;

COPY dim_operador
FROM 's3://tfm-logistica-pablo/silver/dim_operador/'
IAM_ROLE 'arn:aws:iam::<cuenta>:role/RedshiftCopyRole'
FORMAT AS PARQUET;

COPY fact_servicio
FROM 's3://tfm-logistica-pablo/silver/fact_servicio/'
IAM_ROLE 'arn:aws:iam::<cuenta>:role/RedshiftCopyRole'
FORMAT AS PARQUET;

-- Estadisticas y recuperacion de espacio tras la carga masiva
ANALYZE fact_servicio;
VACUUM fact_servicio;

-- Comprobacion de integridad: debe coincidir con el informe de calidad Silver
SELECT COUNT(*) AS filas_hechos FROM fact_servicio;
SELECT COUNT(*) AS filas_zona FROM dim_zona;
