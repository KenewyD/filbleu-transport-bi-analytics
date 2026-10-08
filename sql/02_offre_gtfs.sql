-- Offre théorique REELLE à partir du ZIP GTFS importé.
SELECT route_short_name AS ligne, COUNT(DISTINCT trip_id) AS trajets_definis,
       MIN(departure_hour) AS premiere_heure, MAX(departure_hour) AS derniere_heure,
       ROUND(AVG(planned_minutes),1) AS duree_moyenne_minutes
FROM mart_schedule GROUP BY route_short_name ORDER BY trajets_definis DESC;
-- Un GTFS avec calendrier ne signifie pas que tous les trajets circulent chaque jour.
