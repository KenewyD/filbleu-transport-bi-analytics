-- DEMONSTRATION SYNTHETIQUE exclusivement, pas de chiffres KEOLIS.
SELECT ligne, SUM(courses_prevues) AS courses_prevues,
       SUM(courses_effectuees) AS courses_effectuees,
       ROUND(100.0 * SUM(courses_effectuees) / NULLIF(SUM(courses_prevues), 0), 2) AS taux_realisation,
       ROUND(100.0 * (SUM(courses_effectuees)-SUM(courses_en_retard)) / NULLIF(SUM(courses_effectuees), 0), 2) AS ponctualite,
       SUM(voyageurs_estimes) AS voyageurs_estimes
FROM mart_demo_operations GROUP BY ligne ORDER BY voyageurs_estimes DESC;
