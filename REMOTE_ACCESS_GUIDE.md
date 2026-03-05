# 远程视频功能配置指南

## 问题说明

通过 IP 地址远程访问时，浏览器出于安全考虑会阻止摄像头和麦克风的访问。这是因为：

1. **浏览器安全策略**：现代浏览器（Chrome、Firefox、Edge 等）要求通过 HTTPS 才能访问摄像头和麦克风
2. **WebSocket 协议**：HTTPS 页面需要使用 WSS（WebSocket Secure）协议
3. **混合内容阻止**：HTTPS 页面无法加载 HTTP 资源

## 解决方案

### 方案一：启用 HTTPS（推荐）

#### 步骤 1：安装依赖

```bash
pip install cryptography
```

#### 步骤 2：生成 SSL 证书

```bash
python generate_cert.py
```

这将在 `backend/` 目录下生成：
- `cert.pem`（证书文件）
- `key.pem`（私钥文件）

#### 步骤 3：启动服务器

使用新的启动脚本：

**Windows:**
```bash
start_https.bat
```

**Linux/macOS:**
```bash
chmod +x start_https.sh
./start_https.sh
```

或直接运行：
```bash
cd backend
python main.py
```

#### 步骤 4：访问系统

- **本地访问**: https://localhost:8000
- **远程访问**: https://您的IP地址:8000

⚠️ **首次访问时的安全警告**

由于使用的是自签名证书，浏览器会显示"您的连接不是私密连接"警告：

1. 点击"高级"或"详细信息"
2. 点击"继续访问"或"接受风险并继续"
3. 系统即可正常使用

#### 步骤 5：允许摄像头和麦克风权限

1. 进入远程视频页面
2. 浏览器会弹出权限请求
3. 点击"允许"授予摄像头和麦克风权限

### 方案二：浏览器临时允许（仅用于测试）

#### Chrome 浏览器

1. 在地址栏输入：`chrome://flags/#unsafely-treat-insecure-origin-as-secure`
2. 在"Insecure origins treated as secure"中添加：`http://您的IP地址:8000`
3. 选择"Enabled"
4. 重启浏览器

#### Firefox 浏览器

1. 在地址栏输入：`about:config`
2. 搜索：`media.devices.insecure.enabled`
3. 设置为 `true`
4. 搜索：`media.getusermedia.insecure.enabled`
5. 设置为 `true`

⚠️ **注意**：此方法仅用于开发测试，不推荐在生产环境使用。

### 方案三：使用反向代理（生产环境推荐）

使用 Nginx 或 Caddy 等反向代理服务器配置正式的 SSL 证书（Let's Encrypt）。

#### Nginx 配置示例

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 常见问题

### Q1: 生成证书后仍然无法访问摄像头？

**A:** 确保：
1. 使用 `https://` 而不是 `http://` 访问
2. 已在浏览器中接受证书警告
3. 已授予浏览器摄像头和麦克风权限
4. 检查浏览器控制台是否有错误信息

### Q2: WebSocket 连接失败？

**A:** 检查：
1. 防火墙是否允许 8000 端口
2. 浏览器控制台中的 WebSocket 连接地址是否正确（应为 `wss://` 而非 `ws://`）
3. 服务器是否正常运行

### Q3: 移动设备无法访问？

**A:** 
1. 确保移动设备和服务器在同一网络
2. 使用 HTTPS 访问
3. 在移动浏览器中允许摄像头和麦克风权限
4. 某些移动浏览器可能需要用户手势（如点击按钮）才能请求权限

### Q4: 实时聊天无法同步？

**A:** 
1. 检查 WebSocket 连接状态（浏览器控制台）
2. 确认使用正确的协议（HTTP 用 `ws://`，HTTPS 用 `wss://`）
3. 检查网络连接是否稳定
4. 查看服务器日志是否有错误

## 技术说明

### 自动协议适配

系统已自动适配 HTTP/HTTPS 协议：

```javascript
// 自动选择 WebSocket 协议
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
socket = new WebSocket(`${protocol}//${window.location.host}/ws/${roomId}/${userId}`);
```

### 服务器自动检测

服务器启动时会自动检测 SSL 证书：
- 如果存在证书文件，自动使用 HTTPS
- 如果不存在，使用 HTTP 并提示生成证书

## 安全建议

1. **生产环境**：使用正式的 SSL 证书（Let's Encrypt 免费）
2. **内网环境**：可以使用自签名证书
3. **开发测试**：可以使用 HTTP + 浏览器标志位
4. **定期更新**：证书有效期为 1 年，需定期重新生成

## 获取本机 IP 地址

**Windows:**
```bash
ipconfig
```
查找"IPv4 地址"

**Linux/macOS:**
```bash
ifconfig
# 或
ip addr show
```

## 支持的浏览器

- ✅ Chrome 47+
- ✅ Firefox 36+
- ✅ Edge 79+
- ✅ Safari 11+
- ✅ Opera 34+

## 相关文档

- [MDN - getUserMedia](https://developer.mozilla.org/zh-CN/docs/Web/API/MediaDevices/getUserMedia)
- [WebRTC 安全性](https://webrtc.org/getting-started/security)
- [Let's Encrypt](https://letsencrypt.org/)
