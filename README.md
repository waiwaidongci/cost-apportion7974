# 砺禾项目成本归集簿

内部研究项目工时与费用→精确分摊和透视→站内月结交付；金额用整数分，定时worker站内交付。境外费用按当日报价以精确分数折算人民币后再走原部门分摊。

## 业务场景与工作流
模拟客户：砺禾研究协作组，12位业务与分析人员。每月研究明细先从`cost-apportion-202611.csv`录入底稿，经口径冻结、Python核算、负责人复核后向业务阅读者交付站内CSV。原有流程依靠人工表格抄算，痛点为口径版本难追溯、重复计算易错、复核与交付脱节。

模块：业务总览、业务底稿、境外底稿、汇率报价、口径版本、异步核算与复核、折算核算、定时交付、站内收件箱、审计。底稿可新增/修改/删除；口径仅新增版本；报告提交时冻结来源与版本并保存SHA256。定时交付引用已复核报告快照，worker到期写入数据库，业务阅读者下载。

## 算法口径
按工时权重分摊公共成本、整数分最大余数守恒与差异透视。1分三权重守恒与稳定tie；零权重拒绝；透视总数等于源数。

境外费用折算：底稿记日期与原币金额（最小单位），按当天报价换算，无直兑可经中间币转兑（BFS最少边，直兑优先）。同日报价用精确分数（Fraction）核对可达路径：出现直兑与转兑对不上的矛盾即列出可复算的冲突环（两条路径及各自积率）并整份退回；缺少可达路径同样整份退回并列出涉及凭证。按期间×费用类别汇总精确分后四舍五入到分，差额按小数余数降序、同余数按凭证编号升序补回原费用，再走原部门分摊，前后总额对得上。排队折算时以独立REPEATABLE READ事务取同一时点的报价与底稿完整快照，并发更正不会混入半份输入。百种币、两千条报价、万笔费用限30秒（`FX_BUDGET_SECONDS`），超时任务失败并拒绝复核。折算页面可逐笔查折算依据（路径、积率、精确分、入账分），旧人民币报告（kind=cost）照常查看。

整数分守恒 · 公共成本逐笔可追溯。输入：业务底稿与口径JSON；输出：summary、透视rows、method、warnings。算法实现在`backend/src/services/calculation.py`，折算引擎在`backend/src/services/fx.py`，输入校验在`validation.py`。固定seed=42，240条合成数据；未对接真实业务系统。修改源数据和新建因子/口径不会改变已提交报告。

## 一天的验收剧本
1. 09:00 admin查看240条seed底稿与具名业务期间。
2. 09:10 analyst添加`cost-apportion-202611.csv`的一条具名业务记录。
3. 09:20 admin在口径版本页登记新版本；旧版本保留。
4. 09:30 analyst命名“十一月核算”并选择期间/版本排队。
5. 09:31 Redis worker真实执行Python计算，展示汇总/透视与口径边界。
6. 09:40 admin核对数值后填写至少4字复核说明。
7. 09:45 admin建立60秒周期计划，worker到期生成站内持久化交付。
8. 09:46 viewer在站内收件箱下载交付CSV；审计页查看操作者与时间。
9. 10:00 analyst在汇率报价页更正当日报价，在境外底稿页登记原币费用。
10. 10:10 analyst在折算核算页排队“十一月折算”；worker按当天报价折算、取整守恒后走原部门分摊。
11. 10:20 若报价直兑与转兑对不上，任务失败并列出可复算冲突环；更正报价后重新排队。
12. 10:30 admin在折算核算页逐笔核对折算依据后复核；旧人民币报告在核算与复核页照常查看。

## 快速启动
```sh
cp .env.example .env
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```
前端 http://localhost:18250 ，后端 http://localhost:19250/docs ，数据库宿主端口17750。中文父目录可用。恰好5服务frontend/backend/worker/db/redis；均有真实healthcheck。停止并清空演示数据：`docker compose down -v --remove-orphans`。

|角色|邮箱|密码|权限|
|---|---|---|---|
|admin|admin@demo.local|Demo2026!|全部底稿、口径版本、核算、复核、调度|
|analyst|analyst@demo.local|Demo2026!|底稿增改删、核算、导出；无复核/调度/口径写权限|
|viewer|viewer@demo.local|Demo2026!|只读；仅可下载已复核报告与站内交付|

## 工程结构与开发
Python3.11/FastAPI/SQLAlchemy/Redis，PostgreSQL16；前端原生HTML/CSS/JS ES modules，Nginx代理`/api/`剥前缀至后端。`frontend/src`按api/stores/pages/components/hooks/utils/router/constants/types拆分；`backend/src`按models/schemas/services/controllers/routes/middlewares/config/utils/constants拆分；`backend/scripts/seed_demo.py`自然键幂等且不覆盖用户修改。SQLAlchemy启动创建初始结构，`allocationruns.kind`列演进见backend/migrations/002_fx.md。

后端开发：在backend安装requirements，设置DATABASE_URL/REDIS_URL/JWT_SECRET，`uvicorn src.main:app --reload`；前端可用Nginx或带同等代理的静态开发服务器。前后端全部业务计算在Python。折算引擎自测：`DATABASE_URL=... JWT_SECRET=... python3 -I tests/test_fx.py`（含100币种/2000报价/10000费用30秒时限用例）。

环境变量：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、JWT_SECRET（部署替换）、DATABASE_URL、REDIS_URL、SEED_DEMO。`.env`不入Git。数据库/Redis/共享产物为命名卷。共享角色枚举admin/analyst/viewer与状态queued/running/completed/failed分别定义于backend/src/constants/enums.py和frontend/src/constants/enums.js。两个中间件：统一可恢复校验错误、每IP每分钟360请求限流。

## 已知边界
定时分发为站内收件箱；一名worker轮询执行，无外部邮件。调度发送已复核固定报告快照，不自动重算新数据。时间显示Asia/Shanghai。报告导出适合小型数据；底稿全量加载240行演示数据。Google Fonts不可用时回退serif。后端API以专属字段对象收发，页面通过业务输入控件编辑，不要求用户写JSON。新增来源期间自动可选；专属字段和算法严格校验。JWT演示有效期2小时。折算依据逐笔表超过500笔时页面仅展示前500笔（完整数据在报告快照与结果JSON中）；定时交付仅引用旧人民币报告（kind=cost）；币种限3位大写代码，报价可写小数或`分子/分母`分数。

MIT License。

## 实际实体映射
来源记录（Source，专属业务字段校验）、口径版本（Policy）、核算报告（Run，kind区分cost/fx）、交付计划（Schedule）、交付（Delivery）、汇率报价（FxQuote）、境外费用底稿（FxExpense）均经数据库→模型→请求schema→service→route/controller→frontend API→store→page。Period为已有来源期间字典，在任务期间选择器使用；不单独作为复杂度计数。底稿JSON为小型多字段单记录存储，不虚构未落库的子实体。
