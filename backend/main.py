from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app_state
from routes.pages import router as pages_router
from routes.auth import router as auth_router
from routes.blockchain import router as blockchain_router
from routes.system import router as system_router
from routes.flights import router as flights_router
from routes.tasks import router as tasks_router
from routes.inspection import router as inspection_router
from routes.permissions import router as permissions_router
from routes.video import router as video_router

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时加载数据"""
    app_state.load_users()
    app_state.load_tasks()
    app_state.load_maintenance_records()
    app_state.load_flights()
    app_state.load_airport_data()  # 加载机场数据
    app_state.load_blockchain_events()
    app_state.initialize_blockchain()
    app_state.ensure_users_have_keys()

app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(blockchain_router)
app.include_router(system_router)
app.include_router(flights_router)
app.include_router(tasks_router)
app.include_router(inspection_router)
app.include_router(permissions_router)
app.include_router(video_router)

# 启动应用
if __name__ == "__main__":
    import uvicorn
    import os
    
    # 检查是否存在SSL证书
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("🔐 使用HTTPS模式启动...")
        print("⚠️  首次访问时，浏览器会提示证书不受信任，请点击'高级'→'继续访问'")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            ssl_keyfile=key_file,
            ssl_certfile=cert_file
        )
    else:
        print("⚠️  未找到SSL证书，使用HTTP模式启动")
        print("💡 提示: 远程访问时摄像头/麦克风可能无法使用")
        print("💡 运行 'python generate_cert.py' 生成SSL证书以启用HTTPS")
        uvicorn.run(app, host="0.0.0.0", port=8000)
