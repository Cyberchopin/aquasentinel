"""Append-only Open-Meteo captures. Fetch time is never a model issue time."""
import argparse
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .config import station
from .engine import digest, now, utc


def validate_capture(capture):
    c = dict(capture)
    c['fetched_at'] = utc(c['fetched_at'])
    if c['kind'] not in {'forecast', 'reanalysis'} or c['source_type'] not in {'real', 'synthetic'}:
        raise ValueError('Invalid weather source/kind')
    if c.get('issued_at') is not None:
        c['issued_at'] = utc(c['issued_at'])
        if c['issued_at'] > c['fetched_at']:
            raise ValueError('Issue time cannot follow receipt')
    hourly = c['raw']['hourly']
    if c['raw'].get('utc_offset_seconds') != 0 or c['raw']['hourly_units']['rain'] != 'mm':
        raise ValueError('Expected UTC hourly rain in mm')
    if len(hourly['time']) != len(hourly['rain']) or not hourly['time']:
        raise ValueError('Unequal/empty hourly arrays')
    times = [utc(t + 'Z' if len(t) == 16 else t) for t in hourly['time']]
    if times != sorted(set(times)):
        raise ValueError('Weather times must be unique and increasing')
    for value in hourly['rain']:
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1000):
            raise ValueError('Invalid rain value')
    c['capture_id'] = digest({k: v for k, v in c.items() if k != 'capture_id'})
    return c


def fetch_capture(folder, kind='forecast', start=None, end=None):
    cfg = station()
    query = dict(latitude=cfg['latitude'], longitude=cfg['longitude'], hourly='rain', timezone='UTC')
    if kind == 'forecast':
        base = 'https://api.open-meteo.com/v1/forecast'
        query['forecast_days'] = 3
    elif kind == 'reanalysis' and start and end:
        base = 'https://archive-api.open-meteo.com/v1/archive'
        query.update(start_date=start, end_date=end)
    else:
        raise ValueError('Archive requires start and end')
    url = base + '?' + urlencode(query)
    with urlopen(Request(url, headers={'User-Agent': 'AquaSentinel/0.2'}), timeout=30) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Weather response too large')
        fetched = now()
    c = validate_capture(dict(stream_id=cfg['stream_id'], source_type='real', kind=kind,
        fetched_at=fetched, issued_at=None, url=url, raw=json.loads(raw),
        attribution='Open-Meteo (CC BY 4.0)',
        time_note='API does not supply an issue timestamp here. fetched_at records our receipt; archive is not as-issued forecast skill.'))
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (c['capture_id'] + '.json')
    with path.open('x', encoding='utf-8') as out:
        json.dump(c, out, indent=2, allow_nan=False)
    return path


def watch(capture, as_of, threshold=5, window=6):
    """Only complete future six-hour windows from a recently received forecast."""
    at = datetime.fromisoformat(utc(as_of))
    if not capture or capture['kind'] != 'forecast' or capture['fetched_at'] > utc(as_of):
        return None
    if at - datetime.fromisoformat(capture['fetched_at']) > timedelta(hours=12):
        return None
    h = capture['raw']['hourly']
    pairs = [(datetime.fromisoformat(utc(t + 'Z' if len(t) == 16 else t)), v) for t, v in zip(h['time'], h['rain'])]
    # Each rain value covers the preceding hour. Exclude intervals overlapping now.
    future = [(t, v) for t, v in pairs if at <= t - timedelta(hours=1) and t <= at + timedelta(hours=48)]
    for i in range(len(future) - window + 1):
        block = future[i:i + window]
        if any(v is None for _, v in block) or any(block[j][0]-block[j-1][0] != timedelta(hours=1) for j in range(1, window)):
            continue
        total = sum(v for _, v in block)
        if total >= threshold:
            start = block[0][0] - timedelta(hours=1)
            return dict(state='watch', capture_id=capture['capture_id'], source_type=capture['source_type'],
                window_start=start.isoformat(), window_end=block[-1][0].isoformat(), rain_mm=round(total, 3),
                threshold_mm=threshold, lead_hours=round((start-at).total_seconds()/3600, 2),
                limitation='Illustrative rainfall Watch; not a water-quality or disease prediction')
    return None


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', default='data/weather')
    p.add_argument('--kind', choices=['forecast', 'reanalysis'], default='forecast')
    p.add_argument('--start'); p.add_argument('--end')
    a = p.parse_args()
    print(fetch_capture(a.capture, a.kind, a.start, a.end))
