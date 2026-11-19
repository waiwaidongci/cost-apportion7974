import math,re
from fractions import Fraction
from datetime import date as bizdate
from src.config.settings import CONFIG
CCY=re.compile(r'^[A-Z]{3}$')
DATE=re.compile(r'^\d{4}-\d{2}-\d{2}$')
def number(value,name,minimum=0,integer=False):
 if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<minimum or (integer and int(value)!=value): raise ValueError(name+'数值不合法')
 return value
def biz_date(value,name):
 if not isinstance(value,str) or not DATE.match(value): raise ValueError(name+'需为YYYY-MM-DD日期')
 try: bizdate.fromisoformat(value)
 except ValueError: raise ValueError(name+'需为YYYY-MM-DD日期')
 return value
def parse_rate(value):
 if isinstance(value,bool): raise ValueError('报价数值不合法')
 try:
  if isinstance(value,(int,float)): rate=Fraction(str(value))
  elif isinstance(value,str):
   text=value.strip()
   if not 1<=len(text)<=40: raise ValueError('报价长度不合法')
   if '/' in text:
    num,den=text.split('/',1);rate=Fraction(int(num.strip()),int(den.strip()))
   else: rate=Fraction(text)
  else: raise ValueError('报价类型不合法')
 except (ValueError,ZeroDivisionError): raise ValueError('报价数值不合法')
 if rate<=0: raise ValueError('报价必须为正数')
 return rate
def validate_source(d):
 if not isinstance(d,dict) or set(d)!=set(CONFIG['fields']): raise ValueError('底稿字段必须与业务字段一致')
 for key in ('period','department'):
  if not isinstance(d[key],str) or not 1<=len(d[key])<=100: raise ValueError(key+'不能为空或过长')
 number(d['amount_cents'],'金额分',integer=True)
 if not isinstance(d['category'],str) or not d['category'].strip(): raise ValueError('费用类别不能为空')
def validate_policy(d):
 if not isinstance(d,dict) or not isinstance(d.get('version'),str) or not 2<=len(d['version'])<=120: raise ValueError('口径版本名不合法')
 weights=d.get('weights')
 if not isinstance(weights,dict) or not weights or len(weights)>20: raise ValueError('工时权重需为非空对象且不超过20部门')
 for k,v in weights.items():
  if not isinstance(k,str) or not k or k=='公共': raise ValueError('分摊部门名不合法')
  number(v,'工时权重')
 if sum(weights.values())<=0: raise ValueError('工时权重合计必须大于0')
def validate_fx_quote(d):
 if not isinstance(d,dict) or set(d)!={'date','base','quote','rate'}: raise ValueError('报价字段必须与业务字段一致')
 biz_date(d['date'],'报价日期')
 for key in ('base','quote'):
  if not isinstance(d[key],str) or not CCY.match(d[key]): raise ValueError('币种需为3位大写代码')
 if d['base']==d['quote']: raise ValueError('基准币与报价币不可相同')
 parse_rate(d['rate'])
def validate_fx_expense(d):
 if not isinstance(d,dict) or set(d)!={'date','voucher','department','category','currency','amount_minor'}: raise ValueError('境外底稿字段必须与业务字段一致')
 biz_date(d['date'],'费用日期')
 if not isinstance(d['voucher'],str) or not 1<=len(d['voucher'])<=40: raise ValueError('凭证编号不能为空或过长')
 if not isinstance(d['department'],str) or not 1<=len(d['department'])<=100: raise ValueError('department不能为空或过长')
 if not isinstance(d['category'],str) or not d['category'].strip(): raise ValueError('费用类别不能为空')
 if not isinstance(d['currency'],str) or not CCY.match(d['currency']): raise ValueError('币种需为3位大写代码')
 number(d['amount_minor'],'原币金额',integer=True)
