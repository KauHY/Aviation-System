# 航空维护管理系统

这是一个综合性的航空维护管理平台，集成了权限管理、区块链技术、智能合约、航班信息管理和航机检查等功能。该系统旨在确保航空器的安全性、可维护性和合规性。

## 🎯 功能特性

### 核心功能
- ✅ **权限管理系统** - 基于角色的访问控制（RBAC）和数据权限管理
- ✅ **区块链智能合约** - 不可篡改的维护记录和事件链
- ✅ **航班管理** - 航班搜索、航班信息查询
- ✅ **航机管理** - 航机信息、航机检查和维护记录
- ✅ **维护记录管理** - 创建、追踪、签署维护记录
- ✅ **权限审计日志** - 详细的用户操作审计追踪
- ✅ **系统监控** - 实时系统状态监控和可视化
- ✅ **报告生成** - 自动生成维护和检查报告
- ✅ **区块链可视化** - 区块链事件和交易可视化展示

## 📚 技术栈

### 后端
- **框架**: Python 3.9+, FastAPI
- **通信**: WebSockets（实时通信）
- **密码学**: JWT认证、数字签名、哈希算法
- **区块链**: 自定义智能合约引擎、Merkle树、签名管理
- **数据存储**: JSON文件存储（可扩展为数据库）

### 前端
- **标记语言**: HTML5
- **样式**: CSS3、统一主题框架
- **交互**: JavaScript、动态表单、实时更新
- **可视化**: 图表库、区块链可视化

### 部署
- **容器化**: Docker & Docker Compose
- **跨平台**: Windows/Linux/Mac支持

## 🏗️ 系统架构

```
┌─────────────────────────────────────────┐
│         前端（Web界面）                  │
│  - 权限管理 / 航班管理 / 检查管理         │
└──────────────────┬──────────────────────┘
                   │ HTTP/WebSocket
┌──────────────────▼──────────────────────┐
│      FastAPI 后端服务（main.py）        │
│  - 路由处理 / WebSocket信令 / 业务逻辑   │
└──────────────────┬──────────────────────┘
                   │
      ┌────────────┼────────────┬─────────────┐
      │            │            │             │
┌─────▼──┐  ┌─────▼──┐  ┌─────▼──┐  ┌──────▼──┐
│权限管理 │  │区块链  │  │检修    │  │JSON数据  │
│系统     │  │合约    │  │存储    │  │存储      │
└────────┘  └────────┘  └────────┘  └──────────┘
```

## 📁 项目结构

```
AviationSystem/
├── backend/
│   ├── main.py                          # 主应用程序入口
│   ├── permission_manager.py            # 权限管理和审计系统
│   ├── update_blockchain_info.py        # 区块链信息更新
│   ├── contracts/                       # 智能合约模块
│   │   ├── contract_engine.py           # 合约执行引擎
│   │   ├── base_contract.py             # 基础合约抽象类
│   │   ├── aircraft_subchain_contract.py # 航机子链合约
│   │   ├── maintenance_record_master_contract.py # 维护记录主合约
│   │   ├── signature_manager.py         # 数字签名管理
│   │   ├── merkle_tree.py               # Merkle树实现
│   │   ├── event_system.py              # 事件系统
│   │   └── state_root.py                # 状态根管理
│   ├── tests/
│   │   └── test_system.py               # 系统测试
│   └── *.json                           # 数据文件
│       ├── users.json                   # 用户信息
│       ├── flights.json                 # 航班数据
│       ├── airports.json                # 机场数据
│       ├── blockchain.json              # 区块链数据
│       ├── maintenance_records.json      # 维护记录
│       └── contracts.json               # 合约部署记录
├── frontend/
│   ├── index.html                       # 首页
│   ├── login.html                       # 登录页面
│   ├── profile.html                     # 用户资料页
│   ├── permission-management.html       # 权限管理页面
│   ├── flight-search.html               # 航班搜索页面
│   ├── aircraft-info.html               # 航机信息页面
│   ├── blockchain.html                  # 区块链页面
│   ├── blockchain-visualization.html    # 区块链可视化页面
│   ├── inspection-management.html       # 检查管理页面
│   ├── report-generation.html           # 报告生成页面
│   ├── system-monitor.html              # 系统监控页面
│   ├── system-settings.html             # 系统设置页面
│   ├── static/
│   │   ├── script.js                    # 主JavaScript文件
│   │   ├── style.css                    # 全局样式文件
│   │   ├── contract-client.js           # 区块链合约客户端
│   │   ├── permission-manager.js        # 权限管理前端逻辑
│   │   ├── load-header.js               # 统一头部加载模块
│   │   ├── unified-header.html          # 统一头部模板
│   │   ├── unified-header.js            # 头部交互逻辑
│   │   ├── unified-header.css           # 头部样式
│   │   ├── airlines.js                  # 航空公司数据
│   │   ├── airports.js                  # 机场数据
│   │   ├── chart-theme.js               # 图表主题配置
│   │   └── images/                      # 静态图片目录
│   └── *.py                             # 前端辅助脚本
├── PICTURES/                            # 航机图片库（已在.gitignore中忽略）
│   ├── AirBus/
│   ├── BOEING/
│   ├── COMAC/
│   └── ...
├── docker-compose.yml                   # Docker编排配置
├── Dockerfile                           # Docker镜像构建文件
├── requirements.txt                     # Python依赖
├── .gitignore                           # Git忽略配置
├── start.sh                             # Linux启动脚本
├── start.bat                            # Windows启动脚本
└── README.md                            # 项目文档
```

## 🚀 快速开始

### 前置要求
- Python 3.9+
- Docker & Docker Compose （可选，用于容器化部署）
- 现代浏览器（Chrome 90+、Firefox 88+、Edge 90+ 或更高版本）

### 方法一: 直接运行（推荐开发环境）

1. **克隆项目并进入项目目录**
   ```bash
   git clone <repository-url>
   cd AviationSystem
   ```

2. **创建虚拟环境（可选但推荐）**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **启动服务**
   
   **Windows:**
   ```bash
   .\start.bat
   ```
   
   **Linux/Mac:**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

5. **访问系统**
   打开浏览器访问: `http://localhost:8000`

### 方法二: Docker容器部署（推荐生产环境）

1. **构建并启动容器**
   ```bash
   docker-compose up --build
   ```

2. **访问系统**
   打开浏览器访问: `http://localhost:8000`

3. **停止容器**
   ```bash
   docker-compose down
   ```

4. **查看日志**
   ```bash
   docker-compose logs -f
   ```

## 📖 功能模块说明

### 1. 权限管理系统
- **基于角色的访问控制（RBAC）**: 支持多种用户角色（管理员、技术人员、检查员等）
- **数据权限管理**: 支持细粒度的数据访问权限控制
- **操作审计（Audit）**: 记录所有用户操作，便于追踪和审计
- **实时权限检查**: 每次操作都进行权限验证

### 2. 区块链智能合约系统
- **航机子链合约**: 管理单个航机的维护历史
- **维护记录主合约**: 管理所有维护记录的总账
- **数字签名**: 确保记录的不可篡改性和真实性
- **Merkle树**: 高效的数据完整性验证机制
- **事件系统**: 区块链事件的实时通知

### 3. 航班和航机管理
- **航班查询**: 支持多条件搜索航班信息
- **航机信息**: 查看航机基本信息、维护历史
- **检查管理**: 追踪航机检查和维护状态

### 4. 报告和监控
- **报告生成**: 自动生成维护和检查报告
- **系统监控**: 实时监控系统运行状态
- **任务管理**: 管理维护和检查任务

## 🔐 权限矩阵

| 功能模块 | 技术人员 | 管理人员 | 总负责人 |
|---------|--------|--------|--------|
| 维修记录-查看 | 自己的记录 | 所有记录 | 所有记录 |
| 维修记录-创建 | ✓ | ✓ | ✓ |
| 维修记录-编辑 | 自己的记录 | 所有记录 | 所有记录 |
| 维修记录-删除 | ✗ | ✓ | ✓ |
| 维修记录-审批 | ✗ | ✓ | ✓ |
| 维修记录-上传 | ✓ | ✓ | ✓ |
| 任务管理-查看 | 分配给自己的 | 所有任务 | 所有任务 |
| 任务管理-分配 | ✗ | ✓ | ✓ |
| 航班信息-查看 | ✓ | ✓ | ✓ |
| 航空器信息-查看 | ✓ | ✓ | ✓ |
| 用户管理 | ✗ | ✗ | ✓ |
| 角色管理 | ✗ | ✗ | ✓ |
| 权限分配 | ✗ | ✗ | ✓ |
| 系统设置 | ✗ | ✗ | ✓ |
| 系统监控 | ✗ | ✓ | ✓ |
| 数据备份 | ✗ | ✗ | ✓ |
| 日志查看 | ✗ | ✗ | ✓ |
| 区块链管理 | ✗ | ✗ | ✓ |
| 报表生成 | ✗ | ✓ | ✓ |
| 报表导出 | ✗ | ✓ | ✓ |

## 📡 API概述

### 认证接口
- `POST /login` - 用户登录
- `POST /logout` - 用户登出
- `GET /verify-token` - 验证token有效性

### 权限接口
- `GET /permissions` - 获取当前用户权限
- `POST /assign-permission` - 分配权限（需要管理员权限）
- `GET /audit-logs` - 查看审计日志

### 航班接口
- `GET /flights` - 获取航班列表
- `GET /flights/{flight_id}` - 获取航班详情
- `POST /flights` - 创建航班（需要管理员权限）

### 航机接口
- `GET /aircraft` - 获取航机列表
- `GET /aircraft/{aircraft_id}` - 获取航机详情
- `POST /maintenance-records` - 创建维护记录

### 区块链接口
- `GET /blockchain/blocks` - 获取区块链区块列表
- `GET /blockchain/transactions` - 获取交易列表
- `POST /blockchain/deploy-contract` - 部署智能合约
- `POST /blockchain/invoke-contract` - 调用智能合约

### WebSocket接口
- `ws://localhost:8000/ws` - WebSocket实时连接

## 🔧 配置说明

### 环境变量
可在 `start.bat` 或 `start.sh` 中设置：
- `HOST`: 服务器监听地址（默认: 0.0.0.0）
- `PORT`: 服务器监听端口（默认: 8000）
- `DEBUG`: 调试模式（默认: False）

### 密钥配置
- `SECRET_KEY`: JWT密钥（用于token加密）
- `ALGORITHM`: 加密算法（默认: HS256）

## 🧪 测试

### 运行测试
```bash
python backend/tests/test_system.py
```

### 测试覆盖内容
- 区块链合约执行
- 权限验证
- 数据签名和验证
- API端点功能

## 📝 常见问题

### Q: 如何修改数据库存储方式？
A: 当前系统使用JSON文件存储，若需切换至数据库，修改对应的数据读写接口即可。

### Q: 如何添加新的用户角色？
A: 修改 `permission_manager.py` 中的 `Role` 枚举类，添加新角色及其权限配置。

### Q: 区块链数据存储在哪里？
A: 区块链数据存储在 `blockchain.json` 和 `blockchain_events.json` 文件中。

### Q: 如何恢复生成的密钥？
A: 用户密钥存储在 `backend/` 目录下的相应文件中，可通过 `generate_keys.py` 重新生成。

## 🚨 故障排除

### 常见错误

**错误: "No module named 'fastapi'"**
- 解决: 重新安装依赖 `pip install -r requirements.txt`

**错误: "Address already in use"**
- 解决: 更改PORT值或关闭占用该端口的其他进程

**错误: "权限不足"**
- 解决: 检查用户角色和权限分配，使用管理员账户操作

### 日志查看
- **后端日志**: 服务启动时控制台输出
- **前端日志**: 浏览器开发者工具（F12）的控制台

## 🔒 安全建议

1. **生产环境**:
   - 使用强密钥和复杂密码
   - 启用HTTPS协议
   - 定期备份关键数据
   - 限制管理员账号数量

2. **网络安全**:
   - 配置防火墙规则
   - 使用VPN隔离关键网络
   - 定期更新系统补丁

3. **数据安全**:
   - 加密敏感数据
   - 定期备份区块链数据
   - 实施访问日志监控

## 📚 扩展开发

### 添加新的API端点
在 `backend/main.py` 中添加新的路由（route）。

### 添加新的前端页面
1. 在 `frontend/` 创建HTML文件
2. 在 `frontend/static/` 添加相应的JS和CSS
3. 在 `unified-header.html` 中添加导航链接

### 部署自定义智能合约
1. 在 `backend/contracts/` 创建新合约类
2. 继承 `BaseContract` 类
3. 在 `contract_engine.py` 中注册合约

## 🤝 贡献指南

欢迎提交Issue和Pull Request！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。

## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**最后更新**: 2026年3月2日  
**版本**: 1.0.0  
**维护者**: Aviation System Team