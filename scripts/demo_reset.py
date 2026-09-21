"""Create a fresh demo DB without deleting or overwriting any existing DB."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime,timezone
from aquasentinel.store import Store
from aquasentinel.demo import seed
from aquasentinel.usgs import FIXTURE
import json

path=Path('runtime')/('demo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.sqlite3')
path.parent.mkdir(exist_ok=True)
s=Store(str(path));seed(s);s.import_environment(FIXTURE)
for f in Path('data/weather').glob('*.json'):s.import_weather(json.loads(f.read_text()))
s.close()
print('Created',path)
print('python -m aquasentinel.server --db '+str(path))
