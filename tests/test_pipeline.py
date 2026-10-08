from src.pipeline import time_to_seconds,demo_data,validate_gtfs,build_schedule
import pandas as pd

def test_time_gtfs_over_24h():
    assert time_to_seconds('25:10:03')==90603
    assert time_to_seconds('bad') is None

def test_demo_deterministic():
    a=demo_data(days=2); b=demo_data(days=2)
    assert a.equals(b)
    assert (a.courses_effectuees<=a.courses_prevues).all()
    assert (a.courses_en_retard<=a.courses_effectuees).all()

def test_quality_and_mart():
    gtfs={'routes':pd.DataFrame({'route_id':['r1'],'route_short_name':['A']}),
    'stops':pd.DataFrame({'stop_id':['s1','s2']}),
    'trips':pd.DataFrame({'trip_id':['t1'],'route_id':['r1']}),
    'stop_times':pd.DataFrame({'trip_id':['t1','t1'],'stop_id':['s1','s2'],'stop_sequence':['1','2'],'arrival_time':['08:00:00','08:20:00'],'departure_time':['08:00:00','08:20:00']})}
    assert validate_gtfs(gtfs).anomalies.sum()==0
    s=build_schedule(gtfs)
    assert s.iloc[0].planned_minutes==20
    assert s.iloc[0].stop_count==2
