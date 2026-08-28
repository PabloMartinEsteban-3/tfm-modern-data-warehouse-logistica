-- =====================================================================
-- CAPA GOLD - Modelo dimensional en estrella sobre Amazon Redshift
-- Objetivo OE3. Este fichero va integro al Anexo C de la memoria.
--
-- Las decisiones de DISTSTYLE y SORTKEY son el nucleo del capitulo 4.2.6:
--   - Dimensiones pequenas -> DISTSTYLE ALL (replicadas, join local)
--   - Tabla de hechos      -> DISTKEY sobre zona de origen (alta cardinalidad)
--   - SORTKEY compuesta    -> (tiempo, zona) porque todo filtra por fecha
-- =====================================================================

DROP TABLE IF EXISTS fact_servicio_control;
DROP TABLE IF EXISTS fact_servicio;
DROP TABLE IF EXISTS dim_zona;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_operador;

-- ---------------------------------------------------------------------
CREATE TABLE dim_zona (
    sk_zona                INTEGER       NOT NULL,
    id_zona                INTEGER       NOT NULL,
    nombre_zona            VARCHAR(120),
    distrito               VARCHAR(60),
    zona_servicio          VARCHAR(60),
    lat                    DECIMAL(9,6),
    lon                    DECIMAL(9,6),
    long_via_km            DECIMAL(10,2),
    n_intersecciones       INTEGER,
    densidad_interseccion  DECIMAL(12,4),
    PRIMARY KEY (sk_zona)
)
DISTSTYLE ALL
SORTKEY (sk_zona);

-- ---------------------------------------------------------------------
CREATE TABLE dim_tiempo (
    sk_tiempo        INTEGER      NOT NULL,
    fecha            DATE         NOT NULL,
    anio             SMALLINT,
    trimestre        SMALLINT,
    mes              SMALLINT,
    dia              SMALLINT,
    dia_semana       SMALLINT,
    nombre_dia       VARCHAR(20),
    semana_anio      SMALLINT,
    es_laborable     BOOLEAN,
    PRIMARY KEY (sk_tiempo)
)
DISTSTYLE ALL
SORTKEY (fecha);

-- ---------------------------------------------------------------------
CREATE TABLE dim_operador (
    sk_operador      INTEGER      NOT NULL,
    id_operador      INTEGER      NOT NULL,
    nombre_operador  VARCHAR(100),
    PRIMARY KEY (sk_operador)
)
DISTSTYLE ALL
SORTKEY (sk_operador);

-- ---------------------------------------------------------------------
CREATE TABLE fact_servicio (
    sk_servicio             BIGINT        NOT NULL,
    sk_tiempo               INTEGER       NOT NULL,
    sk_zona_origen          INTEGER       NOT NULL,
    sk_zona_destino         INTEGER       NOT NULL,
    sk_operador             INTEGER,
    hora                    SMALLINT,
    franja_horaria          VARCHAR(20),
    -- Medidas
    duracion_min            DECIMAL(10,2),
    distancia_km            DECIMAL(10,3),
    distancia_geodesica_km  DECIMAL(10,3),
    velocidad_kmh           DECIMAL(10,2),
    eta_referencia_min      DECIMAL(10,2),
    desviacion_eta_pct      DECIMAL(10,2),
    factor_rodeo            DECIMAL(10,4),
    fiabilidad_corredor     DECIMAL(10,4),
    importe_total           DECIMAL(10,2),
    n_pasajeros             SMALLINT,
    PRIMARY KEY (sk_servicio)
)
DISTSTYLE KEY
DISTKEY (sk_zona_origen)
COMPOUND SORTKEY (sk_tiempo, sk_zona_origen);

-- =====================================================================
-- VARIANTE DE CONTROL para el experimento de la seccion 4.7.3.
-- Misma tabla SIN diseno fisico. Carga los mismos datos en ambas y
-- compara la latencia de las consultas de referencia: esa comparacion
-- es uno de los resultados mas defendibles del TFM.
-- =====================================================================
CREATE TABLE fact_servicio_control (
    sk_servicio             BIGINT        NOT NULL,
    sk_tiempo               INTEGER       NOT NULL,
    sk_zona_origen          INTEGER       NOT NULL,
    sk_zona_destino         INTEGER       NOT NULL,
    sk_operador             INTEGER,
    hora                    SMALLINT,
    franja_horaria          VARCHAR(20),
    duracion_min            DECIMAL(10,2),
    distancia_km            DECIMAL(10,3),
    distancia_geodesica_km  DECIMAL(10,3),
    velocidad_kmh           DECIMAL(10,2),
    eta_referencia_min      DECIMAL(10,2),
    desviacion_eta_pct      DECIMAL(10,2),
    factor_rodeo            DECIMAL(10,4),
    fiabilidad_corredor     DECIMAL(10,4),
    importe_total           DECIMAL(10,2),
    n_pasajeros             SMALLINT
)
DISTSTYLE EVEN;