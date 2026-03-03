from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import records, users, auth
from app.services.storage import storage_service

# 创建FastAPI应用
app = FastAPI(
    title="航空检修记录系统API",
    description="基于Python的民航飞机检修记录存证系统API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(records.router, prefix="/api", tags=["records"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(auth.router, prefix="/api", tags=["auth"])

# 根路径
@app.get("/")
def read_root():
    return {
        "message": "航空检修记录系统API",
        "version": "1.0.0",
        "status": "running"
    }

# 健康检查
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)