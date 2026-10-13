"""FastAPI 应用入口。

I1 阶段目标：
- 可启动的基础 Web 服务；
- 健康检查接口用于验证后端、配置与后续数据库容器是否就绪。
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import IntegrityError

from app import models  # noqa: F401
from app.database import Base
from app.config import settings
from app.routers import (
    attendance,
    auth,
    departments,
    employees,
    permissions,
    reports,
    requests,
    shifts,
)


app = FastAPI(
    title="企业员工人脸考勤系统 API",
    description="员工桌面端与 Web 管理台共用的后端服务。",
    version="0.1.0",
)

# 前后端分离后仅放行本地 Vite 开发源；使用 Bearer 令牌，无需携带 Cookie。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
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


# 业务接口统一挂在 /api 下，与前端静态资源、/health、/docs 分离。
API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(permissions.router, prefix=API_PREFIX)
app.include_router(departments.router, prefix=API_PREFIX)
app.include_router(employees.router, prefix=API_PREFIX)
app.include_router(shifts.router, prefix=API_PREFIX)
app.include_router(attendance.router, prefix=API_PREFIX)
app.include_router(requests.leave_router, prefix=API_PREFIX)
app.include_router(requests.trip_router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)


# P4：前端构建产物由 FastAPI 托管，开发态仍由 Vite 提供。
FRONTEND_DIST = (
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
)


def _dist_file(relative_path: str) -> Path:
    """把请求路径安全解析到 dist 内，阻止 `..` 目录穿越。"""
    candidate = (FRONTEND_DIST / relative_path).resolve()
    dist_root = FRONTEND_DIST.resolve()
    if candidate != dist_root and dist_root not in candidate.parents:
        raise HTTPException(status_code=404, detail="资源不存在")
    return candidate


def _spa_index() -> FileResponse:
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.is_file():
        raise HTTPException(
            status_code=404,
            detail="前端尚未构建，请先在 frontend 目录执行 npm run build",
        )
    return FileResponse(index_file)


@app.get("/health")
def health():
    """健康检查：确认应用、模型加载与百度密钥配置状态。"""
    return {
        "status": "ok",
        "models_loaded": len(Base.metadata.tables),
        "baidu_face_ak_set": bool(settings.baidu_face_ak),
    }


@app.get("/assets/{asset_path:path}", include_in_schema=False)
def serve_asset(asset_path: str):
    """返回 Vite 构建出的静态资源。"""
    asset = _dist_file(f"assets/{asset_path}")
    if not asset.is_file():
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(asset)


@app.get("/", include_in_schema=False)
def spa_index():
    """根路径返回 Vue 应用入口。"""
    return _spa_index()


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """SPA 兜底：静态文件优先，其余路径交给 vue-router。"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")
    requested = _dist_file(full_path)
    if full_path and requested.is_file():
        return FileResponse(requested)
    return _spa_index()
