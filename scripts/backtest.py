"""Reproducible synthetic mechanics and explicit real-data proxy description."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta, timezone
import json
import random
from statistics import mean
from aquasentinel.usgs import load_bundle
from aquasentinel.weather import validate_capture, watch


def run():
    rng=random.Random(260921)
    base=datetime(2026,9,21,tzinfo=timezone.utc)
    scenarios=[]
    for i in range(200):
        event=rng.random()<.4
        predicted=max(0,rng.gauss(1.5 if event else .3,.7))
        c=validate_capture(dict(stream_id='synthetic',source_type='synthetic',kind='forecast',
            fetched_at=base.isoformat(),issued_at=None,
            raw={'utc_offset_seconds':0,'hourly_units':{'rain':'mm'},'hourly':{
                'time':[(base+timedelta(hours=h)).isoformat() for h in range(1,25)],
                'rain':[predicted if 7<=h<=12 else 0 for h in range(1,25)]}}))
        scenarios.append((event,c))
    rows=[]
    for threshold in [3,5,10,15]:
        tp=fp=fn=tn=0;leads=[]
        for event,c in scenarios:
            w=watch(c,base.isoformat(),threshold)
            if w and event:tp+=1;leads.append(18) # known artificial event at +18h, evaluated at 0h
            elif w:fp+=1
            elif event:fn+=1
            else:tn+=1
        rows.append(dict(threshold_mm=threshold,precision=tp/(tp+fp) if tp+fp else None,
            recall=tp/(tp+fn),false_alert_rate=fp/(fp+tn),lead_to_synthetic_peak_hours=mean(leads) if leads else None,
            tp=tp,fp=fp,fn=fn,tn=tn))
    records=load_bundle()['records']
    peaks=[r for i,r in enumerate(records[1:-1],1) if r['value'] is not None and r['value']>records[i-1]['value'] and r['value']>records[i+1]['value']]
    result={'synthetic':{'seed':260921,'scenarios':200,'results':rows,'limitation':'Artificial correlated generator; tests mechanics, not environmental or forecast skill'},
        'real_proxy':{'label':'USGS daily discharge local maxima: PROXY for rain-driven runoff events',
            'peaks':[{'date':r['measurement_date'],'flow_cfs':r['value']} for r in peaks],
            'forecast_skill':None,'lead_time_hours':None,
            'reason':'No as-issued contemporaneous forecast capture for February 2024. Daily mean has no known sub-day peak instant. Archive/reanalysis is not as-issued forecast skill.',
            'does_not_validate':'Unusual citizen-report rule, water quality, rainfall causality, or disease'}}
    root=Path(__file__).resolve().parents[1]
    (root/'docs/backtest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':run()
