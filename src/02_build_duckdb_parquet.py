# src/02_build_duckdb_parquet.py

# ----------------------------------------------------------------------------

import duckdb
from pathlib import Path

# ----------------------------------------------------------------------------

Path("data/parquet").mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/reservoir.duckdb")

# ----------------------------------------------------------------------------

con.execute("""
CREATE OR REPLACE TABLE raw_logs AS
SELECT *
FROM read_csv_auto('data/raw/synthetic_logs_28_wells.csv');
""")

# ----------------------------------------------------------------------------

con.execute("""
CREATE OR REPLACE TABLE petrophysics AS
WITH 
base AS (
    SELECT
        well_id,
        md_m,
        zone,

        gr_api,
        rhob_gcc,
        nphi_vv,
        dt_usft,
        dts_usft,
        rt_ohmm,

        -- Conversão sonic:
        -- DT em us/ft → V em m/s
        -- V = 304800 / DT
        304800.0 / dt_usft AS vp_ms,
        304800.0 / dts_usft AS vs_ms,

        -- Densidade g/cc → kg/m3
        rhob_gcc * 1000.0 AS rho_kgm3,

        -- Porosidade inicial
        nphi_vv AS phi_nphi,

        -- Vsh simples via Gamma Ray
        (gr_api - 30.0) / NULLIF((130.0 - 30.0), 0) AS vsh_raw
    FROM raw_logs
),
clean AS (
    SELECT
        *,
        LEAST(GREATEST(vsh_raw, 0.0), 1.0) AS vsh,
        LEAST(GREATEST(phi_nphi, 0.01), 0.35) AS phi
    FROM base
),
elastic AS (
    SELECT
        *,

        -- Módulos dinâmicos
        rho_kgm3 * vs_ms * vs_ms AS shear_modulus_pa,

        rho_kgm3 * (
            vp_ms * vp_ms - (4.0 / 3.0) * vs_ms * vs_ms
        ) AS bulk_modulus_pa,

        -- Razão Vp/Vs
        vp_ms / NULLIF(vs_ms, 0) AS vpvs_ratio
    FROM clean
),
elastic2 AS (
    SELECT
        *,

        9.0 * bulk_modulus_pa * shear_modulus_pa
        / NULLIF(3.0 * bulk_modulus_pa + shear_modulus_pa, 0)
        AS young_modulus_pa,

        (3.0 * bulk_modulus_pa - 2.0 * shear_modulus_pa)
        / NULLIF(2.0 * (3.0 * bulk_modulus_pa + shear_modulus_pa), 0)
        AS poisson_ratio,

        1.0 / NULLIF(bulk_modulus_pa, 0) AS rock_compressibility_1pa,

        rho_kgm3 * vp_ms AS acoustic_impedance,

        rho_kgm3 * vs_ms AS shear_impedance
    FROM elastic
),
fluid AS (
    SELECT
        *,

        -- Archie simplificado:
        -- Sw = ((a / phi^m) * Rw / Rt)^(1/n)
        -- parâmetros típicos didáticos:
        -- a=1, m=2, n=2, Rw=0.08 ohm.m
        SQRT(((1.0 / POWER(phi, 2.0)) * 0.08) / NULLIF(rt_ohmm, 0))
        AS sw_raw,

        -- Permeabilidade proxy tipo Timur/Coates simplificada
        -- k em mD, apenas didática
        1000.0 * POWER(phi, 4.0) / NULLIF(POWER(1.0 - phi, 2.0), 0)
        AS perm_md_raw
    FROM elastic2
),
final AS (
    SELECT
        *,

        LEAST(GREATEST(sw_raw, 0.0), 1.0) AS sw,
        1.0 - LEAST(GREATEST(sw_raw, 0.0), 1.0) AS so,

        GREATEST(perm_md_raw, 0.001) AS perm_md,

        -- mD → m2
        GREATEST(perm_md_raw, 0.001) * 9.869233e-16 AS perm_m2,

        -- Coeficiente de Biot simplificado
        -- alpha = 1 - Kdry/Kgrain
        -- Kgrain assumido: 37 GPa
        1.0 - bulk_modulus_pa / 37.0e9 AS biot_alpha_raw,

        -- Difusividade hidráulica simplificada
        -- D = k / (phi * mu * Ct)
        -- mu = 1 cP = 0.001 Pa.s
        -- Ct proxy = Cr + Cf; Cf assumido 4.4e-10 1/Pa
        perm_md_raw * 9.869233e-16 /
        NULLIF(phi * 0.001 * ((1.0 / NULLIF(bulk_modulus_pa, 0)) + 4.4e-10), 0)
        AS hydraulic_diffusivity_m2s
    FROM fluid
)
SELECT
    well_id,
    md_m,
    zone,

    gr_api,
    rhob_gcc,
    nphi_vv,
    dt_usft,
    dts_usft,
    rt_ohmm,

    vp_ms,
    vs_ms,
    rho_kgm3,
    phi,
    vsh,
    sw,
    so,
    perm_md,
    perm_m2,

    shear_modulus_pa,
    bulk_modulus_pa,
    young_modulus_pa,
    poisson_ratio,
    rock_compressibility_1pa,

    acoustic_impedance,
    shear_impedance,
    vpvs_ratio,

    LEAST(GREATEST(biot_alpha_raw, 0.2), 1.0) AS biot_alpha,
    hydraulic_diffusivity_m2s

FROM final;
""")

# ----------------------------------------------------------------------------

con.execute("""
COPY petrophysics
TO 'data/parquet/petrophysics'
(
    FORMAT PARQUET,
    PARTITION_BY (well_id, zone),
    OVERWRITE_OR_IGNORE TRUE
);
""")

# ----------------------------------------------------------------------------

print(con.execute("""
SELECT zone, COUNT(*) qtd,
       AVG(phi) avg_phi,
       AVG(sw) avg_sw,
       AVG(perm_md) avg_perm_md,
       AVG(vp_ms) avg_vp,
       AVG(vs_ms) avg_vs,
       AVG(young_modulus_pa)/1e9 avg_E_GPa
FROM petrophysics
GROUP BY zone
ORDER BY zone;
""").df())

# ----------------------------------------------------------------------------





