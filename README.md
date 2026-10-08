# 🚌 Transit BI Analytics — Tours / Fil Bleu

[![Python tests](https://img.shields.io/badge/tests-pytest-informational)](tests/test_pipeline.py) [![BI](https://img.shields.io/badge/BI-Streamlit-blue)](app.py)

**Portfolio indépendant — Démonstration métier pour un poste de Développeuse BI. Pas un produit officiel de KEOLIS ou Fil Bleu.**

## Fonctionnalités (7 modules)

1. **Direction / KPI** : courses planifiées, courses simulées effectuées, ponctualité simulée, voyageurs simulés, tendance quotidienne.
2. **Exploitation** : comparaison des lignes, heures de pointe, heatmap, filtres dates/lignes.
3. **Data Quality** : clés manquantes, trip_id dupliqués, intégrité référentielle, contrôles de cohérence.
4. **Analyse & scénarios** : moyenne mobile 7 jours et simulation de variation de demande (pas une prédiction validée).
5. **SQL / BI** : datamart SQLite, requêtes SQL documentées, explorateur et exports CSV.
6. **GTFS** : import manuel des véritables horaires publics Fil Bleu et constitution automatique des tables `raw_*` et `mart_schedule`.
7. **Documentation** : provenance, hypothèses, limites et axes d'industrialisation.

## Architecture

```text
GTFS ZIP public --> parser pandas --> contrôles DQ --> SQLite raw_* --> mart_schedule --> dashboard
                                                           ^
Simulation explicite ---------------------------------- mart_demo_operations ------>
```

Le projet est **entièrement exécutable sans télécharger de fichier** grâce à un petit générateur déterministe de données fictives. Une importation facultative des horaires réels GTFS enrichit la partie offre théorique.

## ⚠️ Transparence essentielle

- **Réel (si importé)** : horaires théoriques, lignes, arrêts, trajets d'un réseau GTFS. Le fichier public Fil Bleu est consultable sur [transport.data.gouv.fr](https://transport.data.gouv.fr/datasets/fil-bleu-syndicat-des-mobilites-gtfs-gtfs-rt).
- **Simulé** : voyageurs, retards, courses effectuées, annulations et ponctualité dans la démo. Ce ne sont **PAS** des statistiques KEOLIS.
- Les trajets définis par un GTFS ne sont pas des courses quotidiennes : il faut évaluer `calendar.txt` et `calendar_dates.txt` à une date précise pour produire des sorties journalières exactes.
- Ni données internes, ni API privées, ni affiliation KEOLIS, ni preuve de performances de l'entreprise.
- Source GTFS Fil Bleu : Tours Métropole / Syndicat des Mobilités de Touraine, *Licence Ouverte v2.0*.

## Démarrage Windows (sans Docker)

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

> Premier chargement : création automatique d'une base `data/transport_bi.db` non versionnée.

## Tests

```bash
python -m pytest -q
```

## Docker

```bash
docker build -t transit-bi .
docker run --rm -p 8501:8501 transit-bi
```

## Déploiement gratuit Streamlit Community Cloud

1. Créer un dépôt public `filbleu-transport-bi-analytics` sur GitHub.
2. Télécharger et décompresser le ZIP livré ; envoyer **tout son contenu** dans le dépôt (le fichier `app.py` doit rester à la racine).
3. Dans [share.streamlit.io](https://share.streamlit.io), créer une app avec ce dépôt, branche `main`, entrée `app.py`.
4. Vérifier l'URL en navigation privée, puis copier les liens GitHub + Streamlit pour le recruteur.

> Les fichiers importés et la base SQLite de Streamlit Cloud ne sont pas garantis persistants entre les redémarrages. Pour une production robuste : PostgreSQL managé + stockage pérenne et collecte planifiée des flux.

## Ce que démontre le projet

**ETL / ELT**, ingestion de fichiers standardisés, **modélisation de tables analytiques**, SQL d'agrégation, **qualité / fiabilisation**, tableaux de bord et exploration métier, exports, documentation, tests CI et dockerisation.

### Améliorations envisagées

- Calendrier GTFS exact par date et fréquences `frequencies.txt`.
- Historisation de `trip-updates` GTFS-RT et calcul de ponctualité réelle documenté.
- Matrice arrêts / accessibilité et cartes géographiques.
- Power BI `.pbix` construit dans Power BI Desktop à partir de tables SQLite exportées en CSV ou PostgreSQL (non fourni).
- Authentification, alertes opérationnelles, orchestration planifiée et catalogue de données.

## Autrice

Kenewy DIALLO — projet portfolio indépendant réalisé à titre démonstratif.
