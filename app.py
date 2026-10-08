"""Public transport BI portfolio app — independent, non-affiliated demonstration."""
import io
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from src.pipeline import DB, read_gtfs_zip, persist_gtfs, load_demo

st.set_page_config(page_title='Transit BI | Tours',page_icon='🚌',layout='wide')
st.title('🚌 Transit BI | Pilotage & qualité des données')
st.caption('Projet portfolio indépendant · Réseau Fil Bleu (Tours) · Sans affiliation avec KEOLIS · Indicateurs opérationnels simulés')
st.warning('⚠️ Les fréquentations, retards et courses effectuées affichés dans la démo sont **100 % synthétiques**. Ils ne représentent aucune mesure réelle de Fil Bleu ou de KEOLIS.',icon='📌')

with st.sidebar:
    st.header('Navigation')
    tab=st.radio('Module',['Vue direction','Exploitation & lignes','Qualité des données','Prévision & scénarios','Explorateur SQL','Importer GTFS réel','Documentation'],label_visibility='collapsed')
    st.divider()
    st.caption('Source des horaires réels : licence ouverte, Tours Métropole / Syndicat des Mobilités de Touraine')
    st.link_button('Données publiques Fil Bleu','https://transport.data.gouv.fr/datasets/fil-bleu-syndicat-des-mobilites-gtfs-gtfs-rt')

@st.cache_data

def demo():
    return load_demo()

df=demo()
df['date']=pd.to_datetime(df['date'])
with st.sidebar:
    period=st.date_input('Période de la démo',(df.date.min().date(),df.date.max().date()),min_value=df.date.min().date(),max_value=df.date.max().date())
    lines=st.multiselect('Lignes',sorted(df.ligne.unique().tolist()),default=sorted(df.ligne.unique().tolist()))
start,end=period if isinstance(period,tuple) and len(period)==2 else (df.date.min().date(),df.date.max().date())
f=df[(df.date.dt.date>=start)&(df.date.dt.date<=end)&df.ligne.isin(lines)].copy()

def indicator_summary(z):
    scheduled=int(z.courses_prevues.sum()); done=int(z.courses_effectuees.sum()); late=int(z.courses_en_retard.sum())
    return {'planned':scheduled,'done':done,'late':late,'riders':int(z.voyageurs_estimes.sum()),'service':done/scheduled if scheduled else 0,'punct':(done-late)/done if done else 0}

if tab=='Vue direction':
    st.subheader('Tableau de bord exécutif · Données simulées')
    a=indicator_summary(f)
    cols=st.columns(4)
    for c,label,value in zip(cols,['Courses planifiées','Courses réalisées (simulation)','Ponctualité simulée','Voyageurs simulés'],[f"{a['planned']:,}",f"{a['done']:,}",f"{a['punct']:.1%}",f"{a['riders']:,}"]): c.metric(label,value)
    daily=f.groupby('date',as_index=False)[['voyageurs_estimes','courses_prevues','courses_effectuees']].sum()
    st.plotly_chart(px.line(daily,x='date',y='voyageurs_estimes',title='Voyageurs simulés par jour'),use_container_width=True)
    left,right=st.columns(2)
    with left: st.plotly_chart(px.bar(f.groupby('ligne',as_index=False).voyageurs_estimes.sum(),x='ligne',y='voyageurs_estimes',title='Fréquentation simulée par ligne'),use_container_width=True)
    with right:
        byhour=f.groupby('heure',as_index=False).voyageurs_estimes.sum()
        st.plotly_chart(px.area(byhour,x='heure',y='voyageurs_estimes',title='Heures de pointe simulées'),use_container_width=True)
    st.download_button('Télécharger agrégats CSV',daily.to_csv(index=False).encode(),file_name='simulation_quotidienne.csv',mime='text/csv')

elif tab=='Exploitation & lignes':
    st.subheader('Analyse opérationnelle et lignes · Simulation')
    if f.empty: st.info('Sélectionnez au moins une ligne.')
    else:
        agg=f.groupby('ligne',as_index=False)[['courses_prevues','courses_effectuees','courses_en_retard','voyageurs_estimes']].sum()
        agg['ponctualite_pct']=100*(agg.courses_effectuees-agg.courses_en_retard)/agg.courses_effectuees.clip(lower=1)
        agg['realisation_pct']=100*agg.courses_effectuees/agg.courses_prevues.clip(lower=1)
        st.dataframe(agg,hide_index=True,use_container_width=True)
        st.plotly_chart(px.bar(agg,x='ligne',y=['realisation_pct','ponctualite_pct'],barmode='group',title='Comparaison : service réalisé vs ponctualité (simulés)'),use_container_width=True)
        st.plotly_chart(px.density_heatmap(f,x='heure',y='ligne',z='voyageurs_estimes',histfunc='sum',title='Charge simulée par heure et par ligne'),use_container_width=True)

elif tab=='Qualité des données':
    st.subheader('Contrôles qualité et traçabilité')
    with sqlite3.connect(DB) as cn:
        try: qc=pd.read_sql_query('SELECT * FROM mart_quality',cn)
        except Exception: qc=pd.DataFrame()
    if len(qc):
        st.success('Contrôles du GTFS importé')
        st.dataframe(qc,hide_index=True,use_container_width=True)
        st.metric('Anomalies GTFS détectées',int(qc.anomalies.sum()))
    else: st.info('Importez un ZIP GTFS officiel dans « Importer GTFS réel » pour lancer les contrôles sur données ouvertes.')
    checks=pd.DataFrame([{'contrôle':'Valeurs manquantes (démo)','anomalies':int(f.isna().sum().sum())},{'contrôle':'Courses négatives (démo)','anomalies':int((f.courses_effectuees<0).sum())},{'contrôle':'Courses réalisées > planifiées (démo)','anomalies':int((f.courses_effectuees>f.courses_prevues).sum())},{'contrôle':'Retards > courses réalisées (démo)','anomalies':int((f.courses_en_retard>f.courses_effectuees).sum())}])
    st.dataframe(checks,hide_index=True,use_container_width=True)

elif tab=='Prévision & scénarios':
    st.subheader('Prévision exploratoire, sur fréquentation simulée')
    daily=f.groupby('date',as_index=False).voyageurs_estimes.sum().sort_values('date')
    if len(daily)<8: st.info('Choisissez au moins 8 jours.')
    else:
        daily['moyenne_mobile_7j']=daily.voyageurs_estimes.rolling(7,min_periods=1).mean()
        st.plotly_chart(px.line(daily,x='date',y=['voyageurs_estimes','moyenne_mobile_7j'],title='Tendance et lissage à 7 jours (ceci n’est pas une prévision validée)'),use_container_width=True)
        scenario=st.slider('Scénario de croissance de demande (%)',-30,40,10)
        base=daily.voyageurs_estimes.tail(7).mean()
        st.metric('Estimation scénario à partir des 7 derniers jours',f'{base*(1+scenario/100):,.0f} voyageurs / jour')
        st.caption('Simulation illustrative : pas de modèle prédictif validé, pas de données voyageurs réelles.')

elif tab=='Explorateur SQL':
    st.subheader('Explorateur SQL sécurisé · requêtes prédéfinies')
    queries={'Top lignes par volume simulé':'SELECT ligne, SUM(voyageurs_estimes) AS voyageurs, SUM(courses_effectuees) AS courses FROM mart_demo_operations GROUP BY ligne ORDER BY voyageurs DESC', 'Qualité des opérations simulées':'SELECT ligne, SUM(courses_prevues) AS prevues, SUM(courses_effectuees) AS faites, SUM(courses_en_retard) AS retards FROM mart_demo_operations GROUP BY ligne','Horaires réels importés':'SELECT route_short_name AS ligne, COUNT(*) AS trips, MIN(departure_hour) AS premiere_heure FROM mart_schedule GROUP BY route_short_name ORDER BY trips DESC'}
    name=st.selectbox('Analyse',list(queries))
    st.code(queries[name],language='sql')
    try:
        with sqlite3.connect(DB) as cn: table=pd.read_sql_query(queries[name],cn)
        st.dataframe(table,hide_index=True,use_container_width=True)
        st.download_button('Exporter CSV',table.to_csv(index=False).encode(),file_name='query_result.csv',mime='text/csv')
    except Exception: st.info('Importez un GTFS réel pour cette analyse, ou sélectionnez une requête sur la démo.')

elif tab=='Importer GTFS réel':
    st.subheader('Import des horaires officiels GTFS')
    st.write('Téléchargez le fichier GTFS ZIP sur le portail open data puis déposez-le ici. Seuls les horaires théoriques, trajets, lignes et arrêts sont réels ; les KPI voyageurs et retards restent simulés.')
    file=st.file_uploader('ZIP GTFS Fil Bleu ou autre réseau',type='zip')
    if file and st.button('Valider et construire le datamart'):
        try:
            with st.spinner('Chargement et contrôles en cours...'):
                gtfs=read_gtfs_zip(file.getvalue());schedule,qc=persist_gtfs(gtfs)
            st.success(f'{len(schedule):,} trajets théoriques importés ; {int(qc.anomalies.sum())} anomalies détectées')
            st.dataframe(schedule[['route_short_name','trip_id','departure_hour','stop_count','planned_minutes']].head(100),hide_index=True)
        except Exception as ex: st.error(f'Import impossible : {ex}')

elif tab=='Documentation':
    st.subheader('Architecture & restitution métier')
    st.markdown("""**ETL** : ZIP GTFS → pandas → validation des clés → SQLite (raw_* + mart_schedule) → analyses SQL.

**BI** : dashboard exécutif, filtres dynamiques, export CSV, comparaison par lignes, exploration SQL préconfigurée, scénarios.

**Qualité** : clés manquantes, références orphelines, unicité, contrôles opérationnels.

**Sources & limites** : horaires publics GTFS sous Licence Ouverte v2.0 ; fréquentation, retards et courses réellement effectuées sont **simulés**, donc aucune conclusion opérationnelle n'est possible sur KEOLIS à partir de ces KPI.

**Industrialisation** : CLI, pytest, GitHub Actions, container Docker, modèles SQL, README reproductible.

**Prochaine étape réaliste** : collecteur GTFS-RT horodaté, historisation des retards et calcul des métriques validées, sous réserve des conditions d'accès et de disponibilité des flux.""")
