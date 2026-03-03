# 基于Python的民航飞机检修记录存证系统

这是一个基于Python的民航飞机检修记录存证系统，使用FastAPI实现的Web应用，用于替代原有的基于区块链的实现。系统采用Python后端和HTML模板前端，实现了检修记录的录入、查询、管理等功能。

## ✨ 功能特性

- **Web界面**：基于FastAPI和Jinja2模板的现代化Web界面
- **数据存储**：使用JSON文件存储数据，实现数据的持久化
- **多维度查询**：
  - 按记录ID查询
  - 按飞机注册号查询
  - 按工卡号查询
  - 按机械师工号查询
- **完整的检修记录管理**：
  - 基本信息录入
  - 故障信息记录
  - 零件和工具使用记录
  - 测试测量数据记录
  - 更换件信息记录
- **签名流程**：
  - 工作者签名
  - 互检人员签名
  - 必检人员签名
  - 放行人员签名
- **用户认证和权限管理**：
  - 基于JWT的用户认证
  - 授权用户管理
  - 管理员权限控制

## 🛠️ 技术栈

- **后端**：Python 3.8+, FastAPI, Uvicorn
- **前端**：HTML5, CSS3, Jinja2模板
- **数据存储**：JSON文件
- **认证**：JWT (JSON Web Token)

## 📂 项目结构

```
aviation-maintenance-system/
├── backend/            # Python后端
│   ├── app/            # 应用代码
│   │   ├── api/        # API路由
│   │   ├── models/     # 数据模型
│   │   ├── services/   # 业务逻辑
│   │   └── utils/      # 工具函数
│   ├── main.py         # 后端入口
│   ├── init_db.py      # 数据库初始化
│   ├── seed_data.py    # 测试数据
│   └── requirements.txt # 依赖包
├── templates/          # HTML模板
│   ├── index.html      # 首页
│   ├── login.html      # 登录页面
│   ├── add_record.html # 添加记录页面
│   ├── search.html     # 查询记录页面
│   ├── record_detail.html # 记录详情页面
│   ├── signature.html  # 签名页面
│   ├── users.html      # 用户管理页面
│   └── error.html      # 错误页面
├── static/             # 静态文件
├── data/               # 数据存储
├── main.py             # Web应用主文件
└── README.md           # 项目说明
```

## 🚀 快速开始

### 环境准备

1. **安装Python**：确保安装了Python 3.8或更高版本
2. **安装依赖**：
   ```bash
   # 进入项目目录
   cd aviation-maintenance-system-main/tcg
   
   # 安装依赖包
   pip install fastapi uvicorn jinja2 python-multipart pydantic pydantic-settings python-jose[cryptography] python-dotenv passlib[bcrypt]
   ```

### 启动系统

1. **初始化数据库**：
   ```bash
   python backend/init_db.py
   ```

2. **启动Web服务器**：
   ```bash
   python main.py
   ```

3. **访问系统**：
   - **Web界面**：[http://localhost:8000](http://localhost:8000)
   - **API文档**：[http://localhost:8000/docs](http://localhost:8000/docs)

### 默认登录信息

- **管理员账户**：
  - 地址：`0x0000000000000000000000000000000000000001`
  - 密码：`123456`
- **测试用户**：
  - 地址：`0x0000000000000000000000000000000000000002`
  - 密码：`123456`

## 📋 使用说明

### 1. 登录系统

- 打开浏览器访问 [http://localhost:8000](http://localhost:8000)
- 点击右上角的「登录」按钮
- 输入默认账户信息登录系统

### 2. 录入检修记录

1. 登录后，点击导航栏的「添加记录」
2. 填写基本信息、故障信息等详细内容
3. 点击「提交记录」按钮保存

### 3. 查询检修记录

1. 点击导航栏的「查询记录」
2. 选择查询方式（按记录ID、飞机注册号、工卡号或机械师工号）
3. 输入查询条件并点击「查询」按钮
4. 在结果列表中点击「查看详情」查看完整记录

### 4. 签名管理

1. 在记录详情页面点击「签名管理」按钮
2. 根据需要进行互检、必检或放行签名
3. 签名后，签名状态会更新

### 5. 用户管理

1. 只有管理员可以访问用户管理功能
2. 点击导航栏的「用户管理」
3. 在「授权新用户」部分输入用户信息并点击「授权用户」按钮
4. 在「授权用户列表」部分可以查看和管理已授权用户

## 🔧 开发指南

### 后端开发

1. 进入项目目录
2. 安装依赖：`pip install fastapi uvicorn jinja2 python-multipart pydantic pydantic-settings python-jose[cryptography] python-dotenv passlib[bcrypt]`
3. 启动开发服务器：`python main.py`

### 前端开发

前端使用Jinja2模板，修改`templates`目录下的HTML文件即可。

### API接口

系统提供了以下主要API接口：

- **记录管理**：
  - `GET /record/{record_id}` - 获取记录详情
  - `GET /aircraft/{reg_no}` - 按飞机注册号查询
  - `GET /jobcard/{job_card_no}` - 按工卡号查询
  - `GET /mechanic/{mechanic_id}` - 按机械师工号查询
  - `GET /records` - 获取所有记录（分页）
  - `POST /record` - 添加记录
  - `POST /record/{record_id}/peer-check` - 互检签名
  - `POST /record/{record_id}/rii` - 必检签名
  - `POST /record/{record_id}/release` - 放行签名

- **用户管理**：
  - `GET /user/me` - 获取当前用户信息
  - `POST /auth/login` - 用户登录
  - `GET /admin/authorized-nodes` - 获取授权用户
  - `POST /admin/authorize` - 授权用户
  - `POST /admin/revoke` - 取消用户授权

## 📁 数据存储

系统使用JSON文件存储数据，位于 `data` 目录：

- `records.json` - 存储所有检修记录
- `users.json` - 存储所有用户信息
- `indices.json` - 存储索引数据，用于加速查询

## 🔒 安全注意事项

- **JWT密钥**：默认的JWT密钥仅用于开发环境，生产环境应使用强密钥
- **数据备份**：定期备份 `data` 目录中的数据文件
- **访问控制**：生产环境应配置适当的访问控制

## 📄 License

MIT

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题或建议，请联系项目维护者。