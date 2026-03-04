# Aviation-System（航空维护管理系统）

面向航空维护场景的综合管理平台，包含权限控制、维护任务与记录管理、区块链存证、系统监控与可视化能力。

---

## 功能概览

- 认证与用户资料：注册、登录、当前用户信息、个人资料更新
- 权限管理（RBAC）：按角色进行接口与操作控制
- 任务管理：检测人员列表、任务分配、任务完成闭环
- 维护记录与区块链：记录创建、审批、放行、链上同步与事件追踪
- 航班管理：航班列表、创建、更新
- 系统能力：备份/恢复、清缓存、清日志、统计与报表导出
- 前端可视化：区块链可视化、系统监控图表
- 前端离线化：Chart.js / D3 / ECharts 已支持本地静态资源加载

---

## 当前技术栈

### 后端
- Python 3.9+
- FastAPI
- JWT（python-jose）
- passlib[bcrypt]
- JSON 文件存储
- 自定义区块链合约引擎（contracts）

### 前端
- HTML + CSS + JavaScript
- 本地图表资源：
  - `/static/js/chart.umd.min.js`
  - `/static/js/d3.v7.min.js`
  - `/static/js/echarts.min.js`

### 部署
- Docker / Docker Compose
- Windows / Linux

---

## 架构（当前实现）

```text
Browser Pages
   │
   ├─ GET 页面路由（backend/routes/pages.py）
   └─ 调用 /api/*

FastAPI（backend/main.py）
   ├─ routes/*        # 控制器层
   ├─ services/*      # 业务 workflow + 存储 service
   ├─ state/*         # app_state 拆分后的状态/初始化/报表/指标模块
   ├─ contracts/*     # 区块链与合约模拟引擎
   └─ *.json          # 运行时数据
```

---

## 目录结构（精简版）

```text
Aviation-System/
├─ backend/
│  ├─ main.py
│  ├─ app_state.py
│  ├─ routes/
│  │  ├─ pages.py
│  │  ├─ auth.py
│  │  ├─ blockchain.py
│  │  ├─ system.py
│  │  ├─ flights.py
│  │  ├─ tasks.py
│  │  ├─ inspection.py
│  │  └─ permissions.py
│  ├─ services/
│  │  ├─ *_workflow.py
│  │  ├─ json_store.py
│  │  └─ users.py / tasks.py / flights.py ...
│  ├─ state/
│  │  ├─ config.py
│  │  ├─ services_registry.py
│  │  ├─ blockchain_ops.py
│  │  ├─ reporting.py
│  │  └─ ...
│  ├─ contracts/
│  └─ *.json
├─ frontend/
│  ├─ *.html
│  └─ static/
│     ├─ js/                         # 本地图表库
│     ├─ chart-theme.js
│     ├─ contract-client.js
│     ├─ permission-manager.js
│     └─ ...
├─ tools/
│  ├─ assets/                        # 前端资源下载脚本
│  ├─ generators/                    # 数据生成脚本
│  ├─ data/                          # 数据处理脚本
│  └─ dev_checks/                    # 开发检查脚本
├─ docker-compose.yml
├─ Dockerfile
└─ requirements.txt
```

---

## 快速开始

### 方式一：本地直接运行（推荐开发）

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动

- Windows

```bash
.\start.bat
```

- Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

3. 访问

- 首页：http://localhost:8000
- 登录页：http://localhost:8000/login

### 方式二：Docker

```bash
docker-compose up --build
```

访问：http://localhost:8000

---

## API 总览（按模块）

> 以下为当前主干接口前缀，完整定义请以 `backend/routes/*.py` 为准。

### 认证
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/verify-signature`
- `POST /api/profile/update`
- `GET  /api/user/current`
- `GET  /api/user/keys/{username}`

### 权限
- `GET /api/permissions/role`
- `GET /api/permissions/check`

### 任务与人员
- `GET  /api/inspectors`
- `GET  /api/tasks`
- `POST /api/tasks/assign`
- `POST /api/tasks/complete`

### 航班
- `GET  /api/flights`
- `POST /api/flights`
- `PUT  /api/flights/{flight_id}`

### 区块链与维护记录
- `POST /api/blockchain/records/create`
- `GET  /api/blockchain/records/list`
- `GET  /api/blockchain/records/view/{record_id}`
- `POST /api/blockchain/records/approve/{record_id}`
- `POST /api/blockchain/release-record`
- `GET  /api/blockchain/stats`
- `GET  /api/blockchain/visualization/*`
- `POST /api/blockchain/verify`
- `GET/POST /api/contract/*`

### 系统与报表
- `POST /api/system/backup`
- `GET  /api/system/backup/download`
- `POST /api/system/restore`
- `POST /api/system/clear-cache`
- `POST /api/system/clear-logs`
- `GET  /api/system/stats`
- `GET  /api/system/users`
- `POST /api/reports/generate`
- `GET  /api/reports/download/{report_type}/{timestamp}`

---

## 数据文件说明

运行时主要使用 `backend/*.json`：

- `users.json`：用户与角色数据
- `tasks.json`：任务数据
- `flights.json`：航班数据
- `maintenance_records.json`：维护记录
- `blockchain.json`：区块数据
- `contracts.json`：合约状态
- `blockchain_events.json`：链上事件

---

## 前端离线资源说明

项目已支持图表库本地化，不依赖外网 CDN：

- Chart.js：`frontend/static/js/chart.umd.min.js`
- D3：`frontend/static/js/d3.v7.min.js`
- ECharts：`frontend/static/js/echarts.min.js`

如需重新下载：

```bash
python tools/assets/download_js_libs.py
```

---

## 开发建议（新增后端 API）

推荐遵循现有分层：

1. `backend/routes/*.py` 只做参数、鉴权、响应映射
2. `backend/services/*_workflow.py` 放业务逻辑
3. `backend/services/*.py` 放持久化访问（JsonStore）
4. `backend/main.py` 注册路由

---

## 常见问题

### 1) 启动后图表不显示
先确认本地 JS 文件存在于 `frontend/static/js/`，再检查浏览器控制台是否有脚本加载错误。

### 2) 登录后接口 401
确认 `access_token` 是否已写入本地存储，并检查请求头/页面登录态。

### 3) 区块链接口报“未初始化”
确认启动时 `startup_event` 已执行，且 `backend/blockchain.json`、`contracts.json` 可读。

---

## 许可证

MIT，详见 `LICENSE`。
