
-- melhores zonas por qualidade de reservatório

SELECT
    zone,
    COUNT(*) AS samples,
    AVG(phi) AS avg_phi,
    AVG(sw) AS avg_sw,
    AVG(so) AS avg_so,
    AVG(perm_md) AS avg_perm_md,
    AVG(vsh) AS avg_vsh,
    AVG(young_modulus_pa) / 1e9 AS avg_young_gpa
FROM read_parquet('data/parquet/petrophysics/**/*.parquet')
GROUP BY zone
ORDER BY avg_phi DESC, avg_perm_md DESC;
