# Ubuntu 云服务器部署手册（Aviation-System）

> 适用场景：将本项目部署到 Ubuntu 服务器，使用 `systemd` 托管进程，`Nginx` 反向代理（支持 WebSocket），可选 HTTPS。

---

## 0. 部署前信息（先准备）

请先确认以下变量：

- 服务器公网 IP：`YOUR_SERVER_IP`
- 域名（可选）：`your.domain.com`
- 项目部署目录：`/opt/Aviation-System`
- 运行用户：`aviation`（建议专用账号）
- 应用监听端口：`8000`（项目默认）

项目当前启动方式：
- 入口：`backend/main.py`
- 监听：`0.0.0.0:8000`

---

## 1. 服务器初始化

## 1.1 更新系统并安装基础工具

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install git curl unzip nginx ufw python3 python3-venv python3-pip
```


## 1.2 创建运行用户（推荐）

```bash
sudo useradd -m -s /bin/bash aviation
sudo usermod -aG sudo aviation
```

> 如果你已有运维账号，也可以跳过本步骤。

---

## 2. 拉取代码并安装依赖

## 2.1 切换到运行用户

```bash
sudo su - aviation
```

## 2.2 拉取项目

```bash
cd /opt
sudo mkdir -p /opt/Aviation-System
sudo chown -R aviation:aviation /opt/Aviation-System
cd /opt/Aviation-System

# 二选一
# 1) git 克隆
# git clone <你的仓库地址> .

# 2) 上传代码包后解压到当前目录
```

## 2.3 创建虚拟环境并安装依赖

```bash
cd /opt/Aviation-System
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2.4 首次手动试跑（非常重要）

```bash
cd /opt/Aviation-System/backend
/opt/Aviation-System/.venv/bin/python main.py
```

另开一个终端测试：

```bash
curl -I http://127.0.0.1:8000/
```

若能返回 `200/307` 等响应，说明应用可启动。

---

## 3. 注册 systemd 服务（开机自启）

## 3.1 创建服务文件

```bash
sudo tee /etc/systemd/system/aviation-system.service > /dev/null << 'EOF'
[Unit]
Description=Aviation System FastAPI Service
After=network.target

[Service]
Type=simple
User=aviation
Group=aviation
WorkingDirectory=/opt/Aviation-System/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/Aviation-System/.venv/bin/python /opt/Aviation-System/backend/main.py
Restart=always
RestartSec=5

# 提高文件句柄上限（可选）
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF
```

## 3.2 启用并启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable aviation-system
sudo systemctl start aviation-system
```

## 3.3 查看服务状态与日志

```bash
sudo systemctl status aviation-system --no-pager
sudo journalctl -u aviation-system -f
```

---

## 4. 配置 Nginx 反向代理（含 WebSocket）

> 本项目存在 WebSocket 路由（`/ws/...`），Nginx 必须带 `Upgrade` 头。

## 4.1 新建站点配置

```bash
sudo tee /etc/nginx/sites-available/aviation-system > /dev/null << 'EOF'
server {
    listen 80;
    server_name your.domain.com;  # 没有域名可改成服务器IP

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 关键配置
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }
}
EOF
```

## 4.2 启用配置并重载

```bash
sudo ln -sf /etc/nginx/sites-available/aviation-system /etc/nginx/sites-enabled/aviation-system
sudo nginx -t
sudo systemctl reload nginx
```

---

## 5. 防火墙配置

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

> 不需要对公网开放 `8000`，只开放 `80/443` 即可。

---

## 6. 可选：配置 HTTPS（Certbot）

> 前提：域名已解析到服务器公网 IP。

## 6.1 安装 Certbot

```bash
sudo apt -y install certbot python3-certbot-nginx
```

## 6.2 一键签发并写入 Nginx

```bash
sudo certbot --nginx -d your.domain.com
```

## 6.3 验证自动续期

```bash
sudo certbot renew --dry-run
```

---

## 7. 日常运维命令

## 服务管理

```bash
sudo systemctl restart aviation-system
sudo systemctl stop aviation-system
sudo systemctl start aviation-system
sudo systemctl status aviation-system --no-pager
```

## 日志查看

```bash
# 应用日志
sudo journalctl -u aviation-system -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/error.log
```

## 配置修改后生效

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl daemon-reload && sudo systemctl restart aviation-system
```

---

## 8. 升级发布流程（建议）

```bash
sudo su - aviation
cd /opt/Aviation-System

# 1) 拉代码
# git pull

# 2) 安装/更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 3) 重启服务
sudo systemctl restart aviation-system

# 4) 快速健康检查
curl -I http://127.0.0.1:8000/
```

---

## 9. 常见故障排查

## 9.1 `start` 后立刻退出

- 看日志：`sudo journalctl -u aviation-system -n 200 --no-pager`
- 常见原因：
  - `WorkingDirectory` 不对（本项目必须是 `/opt/Aviation-System/backend`）
  - 虚拟环境路径不对
  - 依赖没装全

## 9.2 Nginx 502 Bad Gateway

- 应用没起来：`systemctl status aviation-system`
- 应用端口不对：确认项目仍监听 `8000`
- Nginx upstream 配置错误：确认 `proxy_pass http://127.0.0.1:8000;`

## 9.3 WebSocket 连不上

- 检查 Nginx 是否配置了：
  - `proxy_set_header Upgrade $http_upgrade;`
  - `proxy_set_header Connection "upgrade";`
- 检查浏览器控制台与 Nginx error log

## 9.4 静态资源 404

- 检查项目目录结构是否完整上传（`frontend/static`, `backend/tcg/static`, `PICTURES`）
- 检查服务工作目录是否为 `backend`

---

## 10. 备选方案：Docker 部署（简化）

如果你更偏向容器化：

```bash
cd /opt/Aviation-System
sudo docker compose up -d --build
```

然后 Nginx 同样反代到容器映射端口（默认 `8000`）。

---

## 11. 生产环境建议（下一步）

- 把 `SECRET_KEY`、数据库/路径等移到环境变量（`.env`）
- 加入 `logrotate` 避免日志无限膨胀
- 引入进程探活（健康检查脚本）
- 做最小权限文件访问（`chown/chmod`）
- 定期备份 `backend/*.json` 和 `backend/tcg/data/*.json`

---

如果你愿意，我下一步可以按你的真实域名/IP，直接给你生成“可粘贴即用”的两份文件内容：
1) `/etc/systemd/system/aviation-system.service`
2) `/etc/nginx/sites-available/aviation-system`