# 隧道收敛测缝台

测量员登记里程桩号与收敛毫米值。接口进程内后台线程认领待判行（不另起 worker 容器），按绝对值是否不超过 3.0 mm 给出合格或超限。页面是 Svelte。

页眉「邻断面对照」进对照专页，用来比相邻两个桩号谁挤得更狠：

1. **上部**选两个桩号与时段（起始时刻可选、截止时刻必填）；
2. 点「重算」后，**中部**才列出两侧在时段内最近一次**已办结**读数及差值（A − B）。任一侧时段内没有办结读数时该侧与差值一律留空，不填假数；时段之外的点不计；
3. **下部**写对照口径并「报送」。报送由服务端按同一口径重新计算，前端传入的中间数一律不信；两侧未齐办结、或缺截止时刻都不能报送；
4. 权限：测量员（surveyor）可重算、可报送；巡检岗（inspector）可查看与重算，但不能报送。

## 技术栈

- 后端：Flask、Gunicorn、SQLAlchemy、进程内认领线程
- 前端：Svelte、Vite、nginx 反代 `/api`
- 数据库：PostgreSQL 16

## 端口

| 服务 | 地址 |
|------|------|
| 页面 | http://localhost:3201 |
| 接口 | http://localhost:8201 |
| PostgreSQL | localhost:54401（库名 `tunnelconv`） |

## 账号

| 用户 | 密码 | 权限 |
|------|------|------|
| surveyor | surv123456 | 可提交、可报送对照 |
| inspector | insp123456 | 只读：可查看、可重算，不能报送 |

## 启动

```bash
cd projects/21-tunnel-convergence-desk
docker compose up --build
```

健康检查：`GET http://localhost:8201/api/health`

## 对照接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/chainages` | 登录 | 已登记桩号下拉 |
| POST | `/api/comparisons/recompute` | 登录 | 参数 `chainage_a`、`chainage_b`、`cutoff_at`（必填）、`start_at`（可选）；返回两侧最近办结值与 `diff_mm`，未齐时 `ready=false` 且无数 |
| POST | `/api/comparisons` | 测量员 | 报送，另需 `caliber`；服务端重算落库，未办结或缺截止时刻返回 400 |
| GET | `/api/comparisons` | 登录 | 已报送对照列表 |

## 种子

| 桩号 | 收敛 | 结论 |
|------|------|------|
| K12+180 | 1.2 mm | 合格 |
| K18+040 | 5.6 mm | 超限 |
