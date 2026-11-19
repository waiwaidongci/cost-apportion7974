import uuid
from fastapi import HTTPException
from sqlalchemy import select
from src.config.database import engine
from src.models.fx import FxQuote,FxExpense
from src.services.validation import validate_fx_quote,validate_fx_expense
from src.services.audit import log
def save_fx_quote(db,user,data,id=None):
 validate_fx_quote(data)
 obj=db.get(FxQuote,id) if id else FxQuote(natural_key='fxq-'+uuid.uuid4().hex)
 if not obj: raise HTTPException(404,'报价不存在')
 obj.data=data;db.add(obj)
 log(db,user.email,'fxquote.update' if id else 'fxquote.create',obj.natural_key);db.commit();return obj
def save_fx_expense(db,user,data,id=None):
 validate_fx_expense(data)
 obj=db.get(FxExpense,id) if id else FxExpense(natural_key='fxe-'+uuid.uuid4().hex)
 if not obj: raise HTTPException(404,'境外底稿不存在')
 obj.data=data;db.add(obj)
 log(db,user.email,'fxexpense.update' if id else 'fxexpense.create',obj.natural_key);db.commit();return obj
def delete_fx_quote(db,user,id):
 obj=db.get(FxQuote,id)
 if not obj: raise HTTPException(404,'报价不存在')
 db.delete(obj);log(db,user.email,'fxquote.delete',id);db.commit();return {'deleted':id}
def delete_fx_expense(db,user,id):
 obj=db.get(FxExpense,id)
 if not obj: raise HTTPException(404,'境外底稿不存在')
 db.delete(obj);log(db,user.email,'fxexpense.delete',id);db.commit();return {'deleted':id}
def snapshot_inputs(period):
 """独立REPEATABLE READ连接：并发更正报价与底稿时，排队只取同一时点的完整输入。"""
 with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
  expenses=[row[0] for row in conn.execute(select(FxExpense.data).order_by(FxExpense.id)).all()]
  expenses=[dict(e) for e in expenses if period=='全部' or e['date'][:7]==period]
  dates={e['date'] for e in expenses}
  quotes=[dict(row[0]) for row in conn.execute(select(FxQuote.data).order_by(FxQuote.id)).all() if row[0].get('date') in dates]
  return expenses,quotes
