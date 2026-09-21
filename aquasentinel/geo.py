"""Bounded spherical point-to-segment matching, with explicit distance cutoff."""
import json
import math
from pathlib import Path
from .config import station

R=6371008.8


def distance(a,b):
    lat1,lat2=map(math.radians,[a[1],b[1]])
    dlat=lat2-lat1;dlon=math.radians(b[0]-a[0])
    return 2*R*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))


def bearing(a,b):
    p,q=math.radians(a[1]),math.radians(b[1]);d=math.radians(b[0]-a[0])
    return math.atan2(math.sin(d)*math.cos(q),math.cos(p)*math.sin(q)-math.sin(p)*math.cos(q)*math.cos(d))


def segment_distance(p,a,b):
    length=distance(a,b)
    if length<.001:return distance(p,a)
    d=distance(a,p)/R;angle=bearing(a,p)-bearing(a,b)
    along=math.atan2(math.sin(d)*math.cos(angle),math.cos(d))*R
    if not 0<=along<=length:return min(distance(p,a),distance(p,b))
    return abs(math.asin(max(-1,min(1,math.sin(d)*math.sin(angle))))*R)


def features():
    cfg=station();root=Path(__file__).resolve().parents[1]
    path=cfg.get('flowlines')
    real=json.loads((root/path).read_text())['features'] if path else []
    result=[]
    for f in real:
        result.append(dict(f,properties=dict(f.get('properties',{}),stream_id=cfg['stream_id'],source_type='real')))
    for name,offset in [('demo-creek-a',0),('demo-creek-b',.025)]:
        result.append({'type':'Feature','properties':{'stream_id':name,'source_type':'synthetic'},
            'geometry':{'type':'LineString','coordinates':[[-117.83+offset,33.675],[-117.82+offset,33.68],[-117.81+offset,33.69]]}})
    return {'type':'FeatureCollection','features':result}


def match(lon,lat,max_meters=200):
    if not math.isfinite(lon) or not math.isfinite(lat) or abs(lon)>180 or abs(lat)>90:raise ValueError('Invalid location')
    candidates=[]
    for f in features()['features']:
        g=f['geometry'];lines=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
        d=min(segment_distance((lon,lat),a,b) for line in lines for a,b in zip(line,line[1:]))
        candidates.append((d,f['properties']['stream_id'],f['properties']['source_type']))
    d,stream,source=min(candidates)
    return {'stream_id':stream if d<=max_meters else None,'distance_m':round(d,1),'geometry_source_type':source,'max_distance_m':max_meters}
