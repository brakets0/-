"""FastAPI 应用入口。

I1 阶段目标：
- 可启动的基础 Web 服务；
- 健康检查接口用于验证后端、配置与后续数据库容器是否就绪。
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app import models  # noqa: F401
from app.database import Base
from app.config import settings
from app.routers import auth, departments, employees, permissions, shifts


app = FastAPI(
    title="企业员工人脸考勤系统 API",
    description="员工桌面端与 Web 管理台共用的后端服务。",
    version="0.1.0",
)

# 开发阶段允许本地桌面端与 Web 管理台访问；后续按域名收紧。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """并发请求撞唯一约束时返回 409，避免暴露 500 内部错误。"""
    return JSONResponse(
        status_code=409,
        content={"detail": "数据已存在或违反唯一约束，请刷新后重试"},
    )


app.include_router(auth.router)
app.include_router(permissions.router)
app.include_router(departments.router)
app.include_router(employees.router)
app.include_router(shifts.router)


@app.get("/")
def root():
    """根路径：优先返回 Web 管理台页面，否则返回 API 基本信息。"""
    web_index = WEB_DIR / "index.html"
    if web_index.is_file():
        return HTMLResponse(web_index.read_text(encoding="utf-8"))
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """健康检查：确认应用、模型加载与百度密钥配置状态。"""
    return {
        "status": "ok",
        "models_loaded": len(Base.metadata.tables),
        "baidu_face_ak_set": bool(settings.baidu_face_ak),
    }


# I4：Web 管理台静态资源（放在所有 API 路由之后定义）
WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web-console")
