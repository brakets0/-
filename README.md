# 企业员工人脸识别考勤系统

基于百度云人脸识别 + FastAPI + MySQL + wxPython 的 C/S 双端考勤系统。

## 数据库方式

项目直接连接**本机 MySQL 8**，不使用容器：

```text
E:\MySQL\mysql-8.0.24-winx64\bin\mysql.exe
127.0.0.1:3306
```

## 目录规划

```text
employee_attendance/
├── backend/          # FastAPI 后端
├── desktop/          # wxPython 员工桌面端（后续迭代）
├── web/              # Web 管理台（深色霓虹玻璃拟态，I4 已搭建）
├── docs/             # 设计文档与迭代记录
└── .env.example
```

## 已完成迭代

- 后端 FastAPI 骨架：根路径、健康检查 `/health`、配置模块。
- 环境变量示例 `.env.example`。
- I2：SQLAlchemy 模型、Alembic 初始迁移、种子脚本、工时计算工具。
- I3：账号密码登录、JWT 签发/校验、当前用户接口、三角色权限矩阵与 401/403 测试。
- I4：Web 管理台：登录页、三角色菜单、工作台/员工/部门/考勤/审批/班次/报表页面，
  员工默认进入个人考勤页、管理员可见工作台，深色霓虹玻璃拟态视觉、按钮动态交互、
  静态资源挂载。
- 后端测试：健康检查、模型约束、迁移 SQL、种子、工时函数。

## 演示账号

| 角色 | 用户名 | 密码 | 说明 |
| --- | --- | --- | --- |
| 总管理员 | `admin` | `admin123` | 跨部门管理、系统级配置 |
| 部门管理员 | `manager` | `manager123` | 本部门考勤/审批/班次 |
| 普通员工 | `employee` | `employee123` | 打卡、请假、外派、个人报表 |

登录接口：`POST /auth/login`，返回 JWT；访问受保护接口时在请求头携带
`Authorization: Bearer <access_token>`。

## 启动步骤

### 1. 准备 MySQL 数据库与账号

确认本机 MySQL 8 服务已启动，root 能登录。复制 `.env.example` 为 `.env` 并填写
`MYSQL_ROOT_USER` / `MYSQL_ROOT_PASSWORD`，然后执行：

```powershell
cd D:\employee_attendance\backend
.\.venv\Scripts\python.exe -m scripts.setup_db
```

这会创建数据库 `employee_attendance` 和账号 `employee`。

### 2. 初始化表结构与演示数据

```powershell
cd D:\employee_attendance\backend
.\.venv\Scripts\python.exe -m scripts.init_db
```

### 3. 启动后端

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

访问 `http://127.0.0.1:8000/health` 验证服务。

访问 `http://127.0.0.1:8000/` 打开 Web 管理台，使用上方演示账号登录。
