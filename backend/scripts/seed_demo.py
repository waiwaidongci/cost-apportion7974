import json,random
from src.config.database import Base,engine,Session
from src.config.settings import CONFIG
from src.models.identity import User
from src.models.source import Source,Policy,Period
from src.models.fx import FxQuote,FxExpense
from src.models import run
from src.utils.security import password_hash
from src.services.validation import validate_source,validate_fx_quote,validate_fx_expense

def demo_rows():
 rng=random.Random(42);rows=[]
 for i in range(240):
  rows.append({'period':'2026-'+('10' if i<120 else '11'),'department':rng.choice(['公共','公共','光学研究','材料研究','工艺研究']),'category':rng.choice(['仪器维护','试验耗材','研究工时']),'amount_cents':rng.randint(1000,500000)})
 return rows

def demo_fx_quotes():
 rows=[]
 for d,usd in (('2026-10-09','7.09'),('2026-10-23','7.11'),('2026-11-06','7.10'),('2026-11-19','7.12')):
  rows+=[{'date':d,'base':'USD','quote':'CNY','rate':usd},{'date':d,'base':'EUR','quote':'USD','rate':'1.08'},{'date':d,'base':'JPY','quote':'CNY','rate':'0.047'},{'date':d,'base':'HKD','quote':'CNY','rate':'0.91'},{'date':d,'base':'GBP','quote':'USD','rate':'1.27'}]
 rows.append({'date':'2026-11-06','base':'EUR','quote':'CNY','rate':'7.668'})
 return rows

def demo_fx_expenses():
 rng=random.Random(42);dates=['2026-10-09','2026-10-23','2026-11-06','2026-11-19'];rows=[]
 for i in range(48):
  rows.append({'date':dates[i%4],'voucher':f'FX-2026-{i+1:04d}','department':rng.choice(['公共','公共','光学研究','材料研究','工艺研究']),'category':rng.choice(['境外差旅','国际会议','数据订阅']),'currency':rng.choice(['USD','USD','EUR','JPY','HKD','GBP','CNY']),'amount_minor':rng.randint(1000,2000000)})
 return rows

def seed():
 Base.metadata.create_all(engine)
 with Session() as db:
  for role in ('admin','analyst','viewer'):
   if not db.query(User).filter_by(email=role+'@demo.local').first():db.add(User(email=role+'@demo.local',role=role,password=password_hash('Demo2026!')))
  rows=demo_rows()
  for name in sorted(set(r['period'] for r in rows)):
   if not db.query(Period).filter_by(name=name).first():db.add(Period(name=name,description='合成演示业务期间，seed=42'))
  for i,data in enumerate(rows):
   validate_source(data);key='demo-'+str(i+1)
   if not db.query(Source).filter_by(natural_key=key).first():db.add(Source(natural_key=key,data=data))
  if not db.query(Policy).filter_by(version=CONFIG['policy']['version']).first():db.add(Policy(version=CONFIG['policy']['version'],data=CONFIG['policy']))
  for data in demo_fx_quotes():
   validate_fx_quote(data);key=f"fxq-{data['date']}-{data['base']}-{data['quote']}"
   if not db.query(FxQuote).filter_by(natural_key=key).first():db.add(FxQuote(natural_key=key,data=data))
  for i,data in enumerate(demo_fx_expenses()):
   validate_fx_expense(data);key='fxe-'+str(i+1)
   if not db.query(FxExpense).filter_by(natural_key=key).first():db.add(FxExpense(natural_key=key,data=data))
  db.commit();print(json.dumps({'users':db.query(User).count(),'sources':db.query(Source).count(),'policies':db.query(Policy).count(),'periods':db.query(Period).count(),'fx_quotes':db.query(FxQuote).count(),'fx_expenses':db.query(FxExpense).count()},ensure_ascii=False))
if __name__=='__main__':seed()
