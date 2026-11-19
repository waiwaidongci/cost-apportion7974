"""折算引擎自测：python3 -I tests/test_fx.py（在backend目录下运行，需DATABASE_URL/JWT_SECRET环境变量）。"""
import sys,time,random
from pathlib import Path
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.services.fx import fx_calculate,FxError,build_graph,detect_conflicts,find_path,round_half_up

POLICY={'version':'工时口径-v1','weights':{'光学研究':37,'材料研究':41,'工艺研究':22}}
def expense(date,voucher,ccy,amount,dept='光学研究',cat='境外差旅'):
 return {'date':date,'voucher':voucher,'department':dept,'category':cat,'currency':ccy,'amount_minor':amount}
def quote(date,base,to,rate): return {'date':date,'base':base,'quote':to,'rate':rate}
def snapshot(expenses,quotes,policy=None): return {'kind':'fx','policy':policy or POLICY,'expenses':expenses,'quotes':quotes,'period':'全部'}

def test_direct_and_cross():
 q=[quote('2026-11-19','USD','CNY','7.10'),quote('2026-11-19','EUR','USD','1.08')]
 e=[expense('2026-11-19','V-1','USD',10000),expense('2026-11-19','V-2','EUR',10000)]
 r=fx_calculate(snapshot(e,q))
 conv={c['凭证编号']:c for c in r['conversion']}
 assert conv['V-1']['折算路径']=='USD→CNY(7.10)' and conv['V-1']['入账分']==71000
 assert conv['V-2']['折算路径']=='EUR→USD(1.08)，USD→CNY(7.10)' and conv['V-2']['路径积率']==str(Fraction('7.668'))
 assert conv['V-2']['精确分']==str(Fraction('7.668')*10000) and conv['V-2']['入账分']==76680
 assert r['summary']['守恒差额分']==0 and r['summary']['折算人民币分']==r['summary']['分摊金额分']
 print('ok 直兑与中间币转兑')

def test_local_currency():
 r=fx_calculate(snapshot([expense('2026-11-19','V-9','CNY',12345)],[]))
 assert r['conversion'][0]['折算路径']=='本币' and r['conversion'][0]['入账分']==12345
 print('ok 本币直接入账')

def test_conflict_cycle_reproducible():
 q=[quote('2026-11-19','USD','CNY','7'),quote('2026-11-19','EUR','USD','2'),quote('2026-11-19','EUR','CNY','13')]
 try:
  fx_calculate(snapshot([expense('2026-11-19','V-1','EUR',100)],q));assert False,'应整份退回'
 except FxError as exc:
  assert '冲突环' in str(exc) and '整份退回' in str(exc)
  def product(steps):
   total=Fraction(1)
   for s in steps:
    rate=s['rate'].rsplit('(',1)[1].rstrip(')')
    total*=Fraction(rate)
   return total
  assert exc.details,'应列出可复算冲突环'
  for c in exc.details:
   assert str(product(c['path_a']))==c['product_a'] and str(product(c['path_b']))==c['product_b']
   assert c['product_a']!=c['product_b'] and c['date']=='2026-11-19'
 print('ok 冲突环可复算且整份退回')

def test_missing_path():
 q=[quote('2026-11-19','USD','CNY','7.10')]
 try:
  fx_calculate(snapshot([expense('2026-11-19','V-1','CHF',100),expense('2026-11-19','V-2','USD',100)],q));assert False,'应整份退回'
 except FxError as exc:
  assert '缺少折算路径' in str(exc) and 'CHF' in str(exc) and 'V-1' in str(exc)
 print('ok 缺路径整份退回并列出凭证')

def test_rounding_and_voucher_tie():
 # 两笔精确分各余0.5，同余数按凭证编号升序补给V-1
 q=[quote('2026-11-19','USD','CNY','0.005')]
 e=[expense('2026-11-19','V-2','USD',100),expense('2026-11-19','V-1','USD',100)]
 r=fx_calculate(snapshot(e,q))
 conv={c['凭证编号']:c for c in r['conversion']}
 assert conv['V-1']['入账分']==1 and conv['V-2']['入账分']==0
 g=r['rounding'][0]
 assert g['取整合计分']==1 and g['精确合计分']=='1' and g['补分凭证']==['V-1']
 assert r['summary']['折算人民币分']==1 and r['summary']['守恒差额分']==0
 print('ok 四舍五入到分+同余数按凭证编号')

def test_largest_remainder():
 # 余数 0.9/0.1/0.1 -> 补余数最大者；组内合计四舍五入
 q=[quote('2026-11-19','USD','CNY','0.001')]
 e=[expense('2026-11-19','V-1','USD',900),expense('2026-11-19','V-2','USD',100),expense('2026-11-19','V-3','USD',100)]
 r=fx_calculate(snapshot(e,q))
 conv={c['凭证编号']:c for c in r['conversion']}
 assert (conv['V-1']['入账分'],conv['V-2']['入账分'],conv['V-3']['入账分'])==(1,0,0)
 assert r['rounding'][0]['取整合计分']==1
 print('ok 最大余数补分')

def test_department_allocation_conserved():
 q=[quote('2026-11-19','USD','CNY','7.10')]
 e=[expense('2026-11-19','V-1','USD',10001,dept='公共'),expense('2026-11-19','V-2','USD',20000,dept='光学研究')]
 r=fx_calculate(snapshot(e,q))
 s=r['summary']
 assert s['折算人民币分']==s['分摊金额分'] and s['守恒差额分']==0 and s['公共成本分']==71007
 assert sum(row['分摊金额分'] for row in r['rows'])==s['折算人民币分']
 print('ok 原部门分摊前后总额对得上')

def test_timeout_rejected():
 q=[quote('2026-11-19','USD','CNY','7.10')]
 try:
  fx_calculate(snapshot([expense('2026-11-19','V-1','USD',100)],q),budget=0);assert False,'应超时退回'
 except FxError as exc: assert '时限' in str(exc) and '拒绝复核' in str(exc)
 print('ok 超时整份退回拒绝复核')

def test_round_half_up():
 assert round_half_up(Fraction(1,2))==1 and round_half_up(Fraction(3,2))==2
 assert round_half_up(Fraction(2,3))==1 and round_half_up(Fraction(1,3))==0
 assert round_half_up(Fraction(5,1))==5
 print('ok 四舍五入口径')

def test_consistent_direct_and_cross():
 # 直兑7.668与转兑1.08×7.10精确相等，不报冲突；直兑优先于转兑
 q=[quote('2026-11-06','USD','CNY','7.10'),quote('2026-11-06','EUR','USD','1.08'),quote('2026-11-06','EUR','CNY','7.668')]
 adj=build_graph(q)
 assert detect_conflicts('2026-11-06',adj)==[]
 r=fx_calculate(snapshot([expense('2026-11-06','V-1','EUR',10000)],q))
 assert r['conversion'][0]['折算路径']=='EUR→CNY(7.668)' and r['conversion'][0]['入账分']==76680
 print('ok 直兑转兑一致时不报冲突且直兑优先')

def test_deterministic():
 q=[quote('2026-11-19','USD','CNY','7.10'),quote('2026-11-19','EUR','USD','1.08')]
 e=[expense('2026-11-19',f'V-{i}','EUR' if i%2 else 'USD',1000+i,dept='公共' if i%3 else '光学研究') for i in range(50)]
 s=snapshot(e,q)
 a=fx_calculate(snapshot(e,q));b=fx_calculate(snapshot(e,q))
 a['summary'].pop('核算耗时毫秒');b['summary'].pop('核算耗时毫秒')
 assert a==b,'同一快照结果必须一致'
 print('ok 同一快照结果确定一致')

def test_performance():
 rng=random.Random(7)
 ccys=[f"X{chr(65+i//26)}{chr(65+i%26)}" for i in range(99)]+['CNY']
 dates=[f'2026-{m:02d}-{d:02d}' for m in (10,11) for d in range(1,11)]
 quotes=[]
 for date in dates:
  pot={c:Fraction(rng.randint(1,10**6),rng.randint(1,10**6)) for c in ccys}
  order=rng.sample(ccys,len(ccys));pairs=[(order[i],order[rng.randrange(i)]) for i in range(1,len(order))]
  pairs+= [rng.sample(ccys,2)]
  for a,b in pairs: quotes.append(quote(date,a,b,str(pot[b]/pot[a])))
 expenses=[expense(rng.choice(dates),f'V-{i:05d}',rng.choice(ccys),rng.randint(1,10**7),dept=rng.choice(['公共','光学研究','材料研究','工艺研究']),cat=rng.choice(['境外差旅','国际会议','数据订阅'])) for i in range(10000)]
 assert len(quotes)==2000 and len(expenses)==10000 and len(ccys)==100
 t0=time.monotonic();r=fx_calculate(snapshot(expenses,quotes));elapsed=time.monotonic()-t0
 s=r['summary']
 assert s['折算费用笔数']==10000 and s['守恒差额分']==0 and s['折算人民币分']==s['分摊金额分']
 assert elapsed<30,f'超时时限：{elapsed:.1f}s'
 print(f'ok 性能：100币种/2000报价/10000费用 用时 {elapsed:.2f}s（限30秒）')

if __name__=='__main__':
 test_round_half_up();test_direct_and_cross();test_local_currency();test_consistent_direct_and_cross();test_conflict_cycle_reproducible();test_missing_path();test_rounding_and_voucher_tie();test_largest_remainder();test_department_allocation_conserved();test_timeout_rejected();test_deterministic();test_performance()
 print('全部折算引擎自测通过')
