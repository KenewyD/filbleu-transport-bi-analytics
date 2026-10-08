"""GTFS ingestion, SQLite dimensional mart and deterministic demo generator."""
from pathlib import Path
import io
import sqlite3
import zipfile
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DB = BASE / 'data' / 'transport_bi.db'
TABLES = ['routes','stops','trips','stop_times','calendar','calendar_dates']


def time_to_seconds(value):
    """GTFS times may exceed 24 hours."""
    try:
        h,m,s = [int(part) for part in str(value).split(':')]
        if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
            return None
        return h*3600+m*60+s
    except (ValueError, TypeError):
        return None


def read_gtfs_zip(content):
    """Read available GTFS files with safe size limits; no remote calls."""
    if len(content)>30_000_000:
        raise ValueError('Fichier ZIP trop volumineux (30 Mo max).')
    result={}
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names={Path(n).name.lower():n for n in z.namelist() if not n.endswith('/')}
        for required in ['routes.txt','stops.txt','trips.txt','stop_times.txt']:
            if required not in names:
                raise ValueError(f'GTFS incomplet : {required} absent')
        for key in TABLES:
            n=key+'.txt'
            if n in names:
                info=z.getinfo(names[n])
                if info.file_size>65_000_000:
                    raise ValueError(f'{n}: fichier décompressé trop volumineux')
                result[key]=pd.read_csv(io.BytesIO(z.read(names[n])),dtype=str,low_memory=False)
    return result


def validate_gtfs(gtfs):
    checks=[]
    for table,col in [('routes','route_id'),('stops','stop_id'),('trips','trip_id'),('stop_times','trip_id')]:
        d=gtfs[table]
        checks.append({'controle':f'{table}.{col} non vide','anomalies':int(d[col].isna().sum()),'lignes':len(d)})
    routes=set(gtfs['routes'].route_id.dropna())
    trips=set(gtfs['trips'].trip_id.dropna())
    stops=set(gtfs['stops'].stop_id.dropna())
    checks += [
        {'controle':'trips avec route_id inconnu','anomalies':int((~gtfs['trips'].route_id.isin(routes)).sum()),'lignes':len(gtfs['trips'])},
        {'controle':'stop_times avec trip_id inconnu','anomalies':int((~gtfs['stop_times'].trip_id.isin(trips)).sum()),'lignes':len(gtfs['stop_times'])},
        {'controle':'stop_times avec stop_id inconnu','anomalies':int((~gtfs['stop_times'].stop_id.isin(stops)).sum()),'lignes':len(gtfs['stop_times'])},
        {'controle':'trip_id dupliqués','anomalies':int(gtfs['trips'].trip_id.duplicated().sum()),'lignes':len(gtfs['trips'])},
    ]
    return pd.DataFrame(checks)


def build_schedule(gtfs):
    trips=gtfs['trips'].copy()
    routes=gtfs['routes'].copy()
    st=gtfs['stop_times'].copy()
    st['departure_seconds']=st['departure_time'].map(time_to_seconds)
    st['arrival_seconds']=st['arrival_time'].map(time_to_seconds)
    st['stop_sequence_num']=pd.to_numeric(st['stop_sequence'],errors='coerce')
    st=st.sort_values(['trip_id','stop_sequence_num'])
    first=st.groupby('trip_id',as_index=False).first()[['trip_id','departure_seconds']]
    last=st.groupby('trip_id',as_index=False).last()[['trip_id','arrival_seconds']]
    counts=st.groupby('trip_id').size().rename('stop_count').reset_index()
    cols=['route_id','route_short_name']+(['route_long_name'] if 'route_long_name' in routes else [])
    schedule=trips.merge(routes[cols],on='route_id',how='left').merge(first,on='trip_id',how='left').merge(last,on='trip_id',how='left').merge(counts,on='trip_id',how='left')
    schedule['planned_minutes']=(schedule['arrival_seconds']-schedule['departure_seconds'])/60
    schedule['departure_hour']=(schedule['departure_seconds']//3600%24).astype('Int64')
    return schedule


def persist_gtfs(gtfs,db=DB):
    Path(db).parent.mkdir(parents=True,exist_ok=True)
    schedule=build_schedule(gtfs)
    quality=validate_gtfs(gtfs)
    with sqlite3.connect(db) as cn:
        for t,d in gtfs.items():
            d.to_sql('raw_'+t,cn,index=False,if_exists='replace',chunksize=5000)
        schedule.to_sql('mart_schedule',cn,index=False,if_exists='replace',chunksize=5000)
        quality.to_sql('mart_quality',cn,index=False,if_exists='replace')
        cn.execute('CREATE INDEX IF NOT EXISTS idx_schedule_route ON mart_schedule(route_id)')
    return schedule,quality


def demo_data(seed=42,days=60):
    """Clearly SYNTHETIC operational KPI dataset, not real KEOLIS measurements."""
    rng=np.random.default_rng(seed)
    dates=pd.date_range('2026-08-01',periods=days)
    lines=['A','B','C1','C2','2','3','4','5','10','11','12','14']
    rows=[]
    for day in dates:
        for line in lines:
            for hour in range(5,24):
                is_peak=hour in (7,8,9,16,17,18)
                weekend=day.dayofweek>=5
                planned= 8 if is_peak else 4
                if weekend: planned=max(2, planned-2)
                operated=max(0,int(planned-rng.binomial(1,.04)))
                late=int(rng.binomial(operated,0.08+(0.1 if is_peak else 0)+(0.03 if weekend else 0)))
                passengers=int(rng.poisson(operated * (35 if is_peak else 18)*(0.65 if weekend else 1)))
                rows.append((day.strftime('%Y-%m-%d'),line,hour,planned,operated,late,passengers,round(float(rng.uniform(1,9)),1)))
    return pd.DataFrame(rows,columns=['date','ligne','heure','courses_prevues','courses_effectuees','courses_en_retard','voyageurs_estimes','retard_moyen_min'])


def persist_demo(db=DB):
    Path(db).parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db) as cn:
        demo_data().to_sql('mart_demo_operations',cn,index=False,if_exists='replace')
    return db


def load_demo(db=DB):
    if not Path(db).exists():
        persist_demo(db)
    with sqlite3.connect(db) as cn:
        try:
            return pd.read_sql_query('SELECT * FROM mart_demo_operations',cn)
        except Exception:
            persist_demo(db)
            return pd.read_sql_query('SELECT * FROM mart_demo_operations',cn)

if __name__=='__main__':
    persist_demo()
    print('Démonstration locale créée dans data/transport_bi.db')
