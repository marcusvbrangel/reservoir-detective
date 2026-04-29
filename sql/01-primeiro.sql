
-- Exemplo 2: tabela pequena criada manualmente
CREATE OR REPLACE TABLE poco AS
SELECT *
FROM (
    VALUES
        (1, 'poco-01', 's'),
        (2, 'poco-02', 'n'),
        (3, 'poco-03', 's'),
        (4, 'poco-04', 's')
) AS t(id, nome, ativo);

SELECT *
FROM poco
WHERE ativo = 's';

COPY poco
TO 'data/parquet/meu_poco-por-ativo'
(
    FORMAT PARQUET,
    PARTITION_BY (ativo),
    OVERWRITE_OR_IGNORE TRUE
);

SELECT *
FROM read_parquet('data/parquet/meu_poco-por-ativo/ativo=s/*.parquet');

SELECT *
FROM read_parquet('data/parquet/meu_poco-por-ativo/**/*.parquet');










