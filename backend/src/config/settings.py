import os,json
from pathlib import Path
_packaged=Path('/app/project.json')
CONFIG=json.loads((_packaged if _packaged.exists() else Path(__file__).resolve().parents[2]/'project.json').read_text())
DATABASE_URL=os.environ['DATABASE_URL']
REDIS_URL=os.getenv('REDIS_URL','redis://redis:6379/0')
SECRET=os.environ['JWT_SECRET']
