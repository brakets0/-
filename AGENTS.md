# Project Memory

## 项目

- 企业员工人脸识别考勤系统（毕设），基于百度云人脸识别 + FastAPI + MySQL 8 + Web 管理台。
- 项目根：`D:\employee_attendance`
- 本地 MySQL 8，不用 Docker；数据库与账号由 `backend/scripts/setup_db.py` 创建，表结构由 Alembic 迁移初始化。
- 演示账号：`admin/admin123`（总管理员）、`manager/manager123`（部门管理员，技术部）、`employee/employee123`（普通员工）。
- 后端虚拟环境：`D:\employee_attendance\backend\.venv`；PyCharm 打开后端项目时解释器应指向它。
- Git 仓库：`D:\employee_attendance\.git`，当前分支 `master`；`.env`、`.venv/`、`.idea/`、缓存、`web/_screenshots/` 均不入库。

## 当前架构

- `backend/app`：FastAPI 后端
  - `routers/`：`auth.py`、`permissions.py`、`departments.py`、`employees.py`、`shifts.py`
  - `models/`：User、Department、Shift、Attendance、LeaveRequest、BusinessTrip
  - `services/working_time.py`：工时计算、工作日解析、打卡状态
  - `permissions.py`：三角色权限矩阵
  - `seed.py`：幂等演示数据
- `web/`：深色霓虹 + 玻璃拟态 Web 管理台（`index.html`、`styles.css`、`app.js`）
- 登录页品牌文案已改为「员工考勤系统 / employee attendance」；演示账号区暂时保留，待成品阶段确认是否移除。
- `desktop/`、`docs/` 尚未创建

## 已完成

- I1：项目骨架、健康检查、配置
- I2：SQLAlchemy 模型、Alembic 初始迁移、种子脚本、工时计算
- I3：账号密码登录、JWT、三角色权限矩阵、401/403 测试
- I4：Web 管理台深色霓虹玻璃拟态界面，三角色菜单、工作台、员工/部门/考勤/审批/班次/报表页面
- I4 评审高/中优先级修复：空白名称 422 校验、部门列表 N+1 消除、员工/班次列表预加载、员工无部门/跨部门/降级时清空旧部门 manager、班次 PATCH 合并全字段时间校验、全局 `IntegrityError` 返回 409
- 部门管理员权限限定：只能查看/管理/分配本部门员工与考勤信息，前端已按本部门视角过滤
- 员工登录默认进入「我的考勤」，不显示总管理工作台
- 部门管理员登录后与员工一样显示「我的考勤」，本人参与部门考勤统计
- 部门管理员/总管理员员工管理页有「个人考勤」抽屉弹窗（当前为演示数据）
- 总管理员不计入考勤统计：`app/permissions.py` 的 `is_attendance_subject(role)` 只允许 `employee`、`department_manager`
- 前端侧边栏顺序：`我的考勤` 在顶部，`工作台` 在其后
- 首次 Git 提交 `9a62c21 Initial commit: attendance I1-I4 with web console`（53 文件）
- 前端表单控件与弹层修复（提交 `79f0d48 Fix form picker behavior and popup positioning`）：自定义下拉框、日期/时间选择器弹层改为挂载到 `body`，增加视口边界定位与活动项滚动；修复模态框关闭和页面切换后的弹层残留；修正本地日期解析、时间按 5 分钟取整以及表单操作区换行。
- “下拉框和日期/时间选择框默认方框透明、无边框”的最后一次尝试已由用户检查后撤销，未包含在提交 `79f0d48` 中。
- I4 收尾：考勤中心支持日期与部门筛选和演示汇总；审批中心支持类型/状态筛选、请假/外派申请及演示审批；报表中心支持月份/范围筛选与 CSV 导出。
- I4 接口补充：`/auth/me` 返回 `department_name`，供前端按当前用户所属部门展示和过滤演示数据。
- I4 响应式修复：移动端考勤表格保持单行并支持横向滚动，顶栏时间完整显示；员工、部门、班次页面重新加载时会清空部门缓存，避免 CRUD 后显示旧统计值。
- 当前暂无独立桌面端或移动端客户端，统一使用 FastAPI 托管的响应式 Web 管理台；桌面浏览器访问 `127.0.0.1:8000`，手机可通过电脑局域网 IP 访问。

## 权限模型

- `employee`：个人档案、打卡、个人考勤、请假/外派申请、个人报表
- `department_manager`：员工权限 + 本部门员工管理/分配、本部门考勤/审批/班次/报表
- `general_admin`：全部权限 + 系统级配置
- 前端 `hasPermission` 自动放行 `general_admin`；部门权限通过
  `employee.manage.department`、`employee.assign.department`、
  `attendance.view.department`、`leave.review.department` 等控制

## 关键业务规则

- 考勤 `status` 枚举：`present / late / early_leave / absent / partial`
- 班次 `workdays` 用逗号分隔字符串，如 `1,2,3,4,5`
- 实际工时 = 打卡区间分钟数 - 与午休重叠分钟数，只打一端时计 0
- 请假/外派在独立表管理，考勤表只保留打卡状态
- 总管理员没有「我的考勤」菜单，也不进入考勤统计/缺勤对账
- 后续实现打卡/统计 API 时，过滤考勤对象统一使用 `is_attendance_subject`

## 常用命令

```powershell
cd D:\employee_attendance\backend
.\.venv\Scripts\python.exe -m pytest -q           # 测试（当前 53 passed）
.\.venv\Scripts\python.exe -m scripts.setup_db    # 创建数据库与账号
.\.venv\Scripts\python.exe -m scripts.init_db     # 执行迁移并写入演示数据
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
node --check D:\employee_attendance\web\app.js    # 前端语法检查
```

## 当前状态

- Web 端页面多为演示样式数据，业务 API 尚未全部联调（组织/员工/班次 CRUD 已有接口）
- 后端测试 `53 passed, 3 warnings`
- I4 收尾提交信息为 `Complete I4 console workflows and responsive fixes`，包含考勤/审批/报表演示流程、移动端修复与部门缓存失效处理
- 下一步进入 I5：实现打卡、请假、外派、报表等业务路由，并让前端逐步对接真实数据
