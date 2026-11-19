import time
from fractions import Fraction
from collections import defaultdict,deque
from src.services.validation import validate_fx_quote,validate_fx_expense,validate_policy,parse_rate
from src.services.calculation import calculate
from src.constants.enums import FX_BUDGET_SECONDS
TARGET='CNY'
class FxError(ValueError):
 """折算核算被整份退回：报价冲突、缺少路径或超时。"""
 def __init__(self,message,details=None):
  super().__init__(message);self.details=details or []
def build_graph(quotes):
 """当日报价建无向图：base→quote用报价rate，反向用精确倒数（分数形式展示，可复算）。"""
 adj=defaultdict(list)
 for q in quotes:
  rate=parse_rate(q['rate'])
  adj[q['base']].append((q['quote'],rate,f"{q['base']}→{q['quote']}({q['rate']})"))
  adj[q['quote']].append((q['base'],Fraction(1)/rate,f"{q['quote']}→{q['base']}({Fraction(1)/rate})"))
 return adj
def _tree_path(parent,node):
 steps=[]
 while parent[node] is not None:
  prev,rate,label=parent[node];steps.append((prev,node,rate,label));node=prev
 steps.reverse();return steps
def _product(steps):
 total=Fraction(1)
 for _,_,rate,_ in steps: total*=rate
 return total
def _steps_json(steps): return [{'from':a,'to':b,'rate':label} for a,b,_,label in steps]
def detect_conflicts(date,adj):
 """BFS势位核对：同一分量内任意两条可达路径的精确分数积必须相等，否则记录可复算冲突环。"""
 potential={};parent={};conflicts=[]
 for root in adj:
  if root in potential: continue
  potential[root]=Fraction(1);parent[root]=None;queue=deque([root])
  while queue:
   u=queue.popleft()
   for v,rate,label in adj[u]:
    expect=potential[u]*rate
    if v not in potential:
     potential[v]=expect;parent[v]=(u,rate,label);queue.append(v)
    elif potential[v]!=expect:
     path_a=_tree_path(parent,u)+[(u,v,rate,label)];path_b=_tree_path(parent,v)
     conflicts.append({'date':date,'from':path_a[0][0],'to':v,'path_a':_steps_json(path_a),'path_b':_steps_json(path_b),'product_a':str(_product(path_a)),'product_b':str(_product(path_b))})
 return conflicts
def find_path(adj,src,dst=TARGET):
 """BFS最少边路径：直兑优先，无直兑经中间币转兑；返回(精确积率,步骤)或None。"""
 if src==dst: return Fraction(1),[]
 if src not in adj: return None
 prev={src:None};queue=deque([src])
 while queue:
  u=queue.popleft()
  for v,rate,label in adj[u]:
   if v in prev: continue
   prev[v]=(u,rate,label)
   if v==dst:
    steps=[];node=dst;total=Fraction(1)
    while prev[node] is not None:
     p,r,lbl=prev[node];steps.append((p,node,r,lbl));total*=r;node=p
    steps.reverse();return total,_steps_json(steps)
   queue.append(v)
 return None
def round_half_up(value):
 """精确分数四舍五入到整数分。"""
 return (value.numerator*2+value.denominator)//(2*value.denominator)
def _fmt_steps(steps): return '，'.join(s['rate'] for s in steps) if steps else '本币'
def _conflict_message(conflicts):
 lines=[f"[{i+1}]{c['date']} {c['from']}→{c['to']} 甲:{_fmt_steps(c['path_a'])}={c['product_a']} 乙:{_fmt_steps(c['path_b'])}={c['product_b']}" for i,c in enumerate(conflicts[:10])]
 if len(conflicts)>10: lines.append(f"……另有{len(conflicts)-10}个")
 return f"当日报价存在{len(conflicts)}个可复算冲突环，整份退回："+'；'.join(lines)
def _missing_message(missing):
 groups=sorted(missing.items())
 lines=[f"{date} {ccy}→{TARGET}不可达（凭证{'、'.join(vs[:5])}{'等'+str(len(vs))+'笔' if len(vs)>5 else ''}）" for (date,ccy),vs in groups[:10]]
 if len(groups)>10: lines.append(f"……另有{len(groups)-10}组")
 return "缺少折算路径，整份退回："+'；'.join(lines)
def fx_calculate(snapshot,budget=FX_BUDGET_SECONDS,clock=time.monotonic):
 """境外费用按当日报价精确分数折算人民币，取整守恒后走原部门分摊。任何矛盾/缺路径/超时即整份退回。"""
 t0=clock()
 def check(stage):
  if clock()-t0>budget: raise FxError(f'核算超过{budget}秒时限（{stage}），整份退回并拒绝复核')
 policy=snapshot['policy'];expenses=snapshot['expenses'];quotes=snapshot['quotes']
 validate_policy(policy)
 for q in quotes: validate_fx_quote(q)
 for e in expenses: validate_fx_expense(e)
 by_date=defaultdict(list)
 for q in quotes: by_date[q['date']].append(q)
 conflicts=[];graphs={}
 for d in sorted({e['date'] for e in expenses}):
  adj=build_graph(by_date.get(d,[]));graphs[d]=adj;conflicts.extend(detect_conflicts(d,adj));check('报价核对')
 if conflicts: raise FxError(_conflict_message(conflicts),conflicts)
 cache={};missing=defaultdict(list);converted=[]
 for i,e in enumerate(expenses):
  if i%128==0: check('逐笔折算')
  key=(e['date'],e['currency'])
  if key not in cache: cache[key]=find_path(graphs[e['date']],e['currency'])
  found=cache[key]
  if found is None: missing[key].append(e['voucher']);continue
  rate,steps=found
  converted.append({'expense':e,'rate':rate,'steps':steps,'exact':rate*int(e['amount_minor'])})
 if missing: raise FxError(_missing_message(missing),[{'date':d,'currency':c,'vouchers':v} for (d,c),v in sorted(missing.items())])
 check('路径核对')
 groups=defaultdict(list)
 for c in converted: groups[(c['expense']['date'][:7],c['expense']['category'])].append(c)
 rounding=[]
 for (period,category),items in sorted(groups.items()):
  total_exact=sum((c['exact'] for c in items),Fraction(0));group_total=round_half_up(total_exact)
  for c in items: c['fen']=c['exact'].numerator//c['exact'].denominator
  order=sorted(items,key=lambda c:(-(c['exact']-c['fen']),c['expense']['voucher']))
  leftover=group_total-sum(c['fen'] for c in items)
  assert 0<=leftover<=len(items),'取整补分越界'
  for c in order[:leftover]: c['fen']+=1
  rounding.append({'期间':period,'费用类别':category,'精确合计分':str(total_exact),'取整合计分':group_total,'补分笔数':leftover,'补分凭证':[c['expense']['voucher'] for c in order[:leftover]][:50]})
  check('取整守恒')
 sources=[{'period':c['expense']['date'][:7],'department':c['expense']['department'],'category':c['expense']['category'],'amount_cents':c['fen']} for c in converted]
 allocated=calculate(sources,policy)
 check('部门分摊')
 conversion=[{'凭证编号':c['expense']['voucher'],'日期':c['expense']['date'],'部门':c['expense']['department'],'费用类别':c['expense']['category'],'币种':c['expense']['currency'],'原币最小单位':int(c['expense']['amount_minor']),'折算路径':_fmt_steps(c['steps']),'路径积率':str(c['rate']),'精确分':str(c['exact']),'入账分':c['fen']} for c in converted]
 total_fen=sum(c['fen'] for c in converted)
 check('结果汇总')
 summary={'折算费用笔数':len(converted),'涉及币种':len({e['currency'] for e in expenses}),'折算人民币分':total_fen,'分摊金额分':allocated['summary']['分摊金额分'],'公共成本分':allocated['summary']['公共成本分'],'守恒差额分':allocated['summary']['分摊金额分']-total_fen,'报价冲突环':0,'核算耗时毫秒':int((clock()-t0)*1000)}
 return {'summary':summary,'rows':allocated['rows'],'trace':allocated['trace'],'conversion':conversion,'rounding':rounding,'method':'境外费用按当日报价以精确分数折算人民币：直兑优先，无直兑经中间币转兑；同日报价出现可复算冲突环或缺少可达路径即整份退回。按期间×费用类别汇总精确分后四舍五入到分，差额按小数余数降序、凭证编号升序补回原费用；再按工时权重口径走原部门分摊，前后总额守恒。','warnings':[]}
