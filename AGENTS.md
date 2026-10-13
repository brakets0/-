# Project Memory

## 项目

- 企业员工人脸识别考勤系统（毕设），基于百度云人脸识别 + FastAPI + MySQL 8 + Web 管理台。
- 项目根：`D:\employee_attendance`
- 本地 MySQL 8，不用 Docker；数据库与账号由 `backend/scripts/setup_db.py` 创建，表结构由 Alembic 迁移初始化。
- 演示账号：`admin/admin123`（总管理员）、`manager/manager123`（部门管理员，技术部）、`employee/employee123`（普通员工）。
- 后端虚拟环境：`D:\employee_attendance\backend\.venv`；PyCharm 打开后端项目时解释器应指向它。
- Git 仓库：`D:\employee_attendance\.git`，当前分支 `master`；`.env`、`.venv/`、`.idea/`、缓存、`web/_screenshots/`、`frontend/node_modules/`、`frontend/dist/`、`frontend/scripts/_screenshots/` 均不入库。

## 当前架构

- `backend/app`：FastAPI 后端
  - `routers/`：`auth.py`、`permissions.py`、`departments.py`、`employees.py`、`shifts.py`、`attendance.py`、`requests.py`、`reports.py`、`face.py`
  - `services/attendance.py`：班次匹配、打卡状态刷新、月度汇总
  - `services/reports.py`：按部门聚合月度考勤报表（出勤/缺勤/请假/外派）
  - `services/baidu_face.py`：百度云人脸 REST 客户端（access_token、检测、注册、检索）
  - `services/face_service.py`：人脸注册权限、绑定状态与人脸检索业务编排
  - `models/`：User、Department、Shift、Attendance、LeaveRequest、BusinessTrip
  - `services/working_time.py`：工时计算、工作日解析、打卡状态
  - `permissions.py`：三角色权限矩阵
  - `seed.py`：幂等演示数据
- `frontend/`：Vue 3 + Vite + Pinia + Element Plus 的前后端分离前端（`npm run dev` → `127.0.0.1:5173`）
  - `src/api/`：axios 客户端（默认 baseURL `/api`）与各资源接口
  - `src/stores/`：`auth`（登录态/权限）、`departments`（部门缓存）
  - `src/router/`：路由与权限守卫，三角色菜单规则与旧版一致
  - `src/views/`：`LoginView`、`DashboardView`（账号 + 今日出勤 + 本月概览真实统计）、`MyAttendanceView`、`AttendanceView`、`ApprovalView`、`EmployeesView`（含个人考勤抽屉）、`DepartmentsView`、`ShiftsView`、`ReportsView`
- 旧版原生 `web/` 控制台已在 P4 下线；生产/演示态由 FastAPI 托管 `frontend/dist`（Vite 构建产物，不入库），根路径与 `/{path}` 走 SPA 兜底，`/api`、`/health`、`/docs` 保持原路由
- 登录页品牌文案已改为「员工考勤系统 / employee attendance」；演示账号区暂时保留，待成品阶段确认是否移除。
- `desktop/`：wxPython 员工桌面端（登录、人脸注册、人脸签到/签退），摄像头只抓帧，识别全部走后端调用百度云
- `docs/` 尚未创建

## 已完成

- I1：项目骨架、健康检查、配置
- I2：SQLAlchemy 模型、Alembic 初始迁移、种子脚本、工时计算
- I3：账号密码登录、JWT、三角色权限矩阵、401/403 测试
- I4：Web 管理台深色霓虹玻璃拟态界面，三角色菜单、工作台、员工/部门/考勤/审批/班次/报表页面
- I4 评审高/中优先级修复：空白名称 422 校验、部门列表 N+1 消除、员工/班次列表预加载、员工无部门/跨部门/降级时清空旧部门 manager、班次 PATCH 合并全字段时间校验、全局 `IntegrityError` 返回 409
- 部门管理员权限限定：只能查看/管理/分配本部门员工与考勤信息，前端已按本部门视角过滤
- 员工登录默认进入「我的考勤」，不显示总管理工作台
- 部门管理员登录后与员工一样显示「我的考勤」，本人参与部门考勤统计
- 部门管理员/总管理员员工管理页有「个人考勤」抽屉弹窗，接入 `GET /api/attendance/employee/{id}?month=`，展示月度汇总与明细并支持切换月份
- 总管理员不计入考勤统计：`app/permissions.py` 的 `is_attendance_subject(role)` 只允许 `employee`、`department_manager`
- 前端侧边栏顺序：`我的考勤` 在顶部，`工作台` 在其后
- 首次 Git 提交 `9a62c21 Initial commit: attendance I1-I4 with web console`（53 文件）
- 前端表单控件与弹层修复（提交 `79f0d48 Fix form picker behavior and popup positioning`）：自定义下拉框、日期/时间选择器弹层改为挂载到 `body`，增加视口边界定位与活动项滚动；修复模态框关闭和页面切换后的弹层残留；修正本地日期解析、时间按 5 分钟取整以及表单操作区换行。
- “下拉框和日期/时间选择框默认方框透明、无边框”的最后一次尝试已由用户检查后撤销，未包含在提交 `79f0d48` 中。
- I4 收尾：考勤中心支持日期与部门筛选和演示汇总；审批中心支持类型/状态筛选、请假/外派申请及演示审批；报表中心支持月份/范围筛选与 CSV 导出。
- I4 接口补充：`/auth/me` 返回 `department_name`，供前端按当前用户所属部门展示和过滤演示数据。
- I4 响应式修复：移动端考勤表格保持单行并支持横向滚动，顶栏时间完整显示；员工、部门、班次页面重新加载时会清空部门缓存，避免 CRUD 后显示旧统计值。
- P0：搭建 `frontend/` Vue 3 脚手架，迁移登录页与应用外壳，登录 → `/auth/me` → 权限菜单全链路打通；旧 `web/` 未改动。
- P1：业务接口统一加 `/api` 前缀（`backend/app/main.py` 的 `API_PREFIX`），CORS 收敛为显式放行 `127.0.0.1:5173` 且关闭 credentials；`web/app.js` 的 `API_BASE` 同步改为 `/api`；测试路径断言同步更新。
- P2a：迁移员工管理、部门管理、班次管理三页到 Vue + Element Plus，保留原权限规则、部门缓存失效、移动端表格横向滚动；冒烟脚本 `frontend/scripts/smoke.py` 覆盖三角色登录/守卫与三页 CRUD。
- I5a：新增 `/api/attendance/punch`（签到/签退，重复打卡 409）、`/api/attendance/me`、`/api/attendance?date=&department_id=`（按日期出勤对账）、`/api/attendance/employee/{id}`；「我的考勤」页已接入真实数据与打卡按钮。出勤率 = 打卡完整天数 / 应出勤天数（迟到、早退仍计出勤）。
- I5a 续：「考勤中心」已接入 `/api/attendance`，支持日期/部门筛选与出勤汇总。
- I5b（后端已完成）：`POST/GET /api/leave-requests`、`PATCH /api/leave-requests/{id}/review`、`POST/GET /api/business-trips`、`PATCH /api/business-trips/{id}/review`；列表范围=本人/本部门/全部，审批需 `*.review.department`，越权 403、重复审批 409。测试文件 `backend/tests/test_requests.py`（5 用例）。
- I5b 补齐：新增 `DELETE /api/leave-requests/{id}`、`DELETE /api/business-trips/{id}`（员工撤回本人待审批申请，审批人可删除范围内申请）；「审批中心」向拥有 `leave.apply` 的角色开放，普通员工可提交并查看本人申请、撤回待审批记录，审批人保留通过/驳回。测试新增 `test_delete_leave_scope_and_pending_rule`，`test_requests.py` 共 6 用例。
- I5c：新增 `GET /api/reports/monthly`（`month=YYYY-MM`、可选 `department_id`），按部门聚合应出勤、出勤、迟到、早退、缺勤、平均工时、平均出勤率、请假/外派天数；部门管理员锁定本部门，总管理员可全公司或按部门下钻，员工无部门级报表权限。Vue「报表中心」接入真实数据、部门筛选、汇总卡片与带 BOM 的 CSV 导出。测试 `backend/tests/test_reports.py`（3 用例）。
- P4：删除旧 `web/` 控制台（`web/app.js`、`index.html`、`styles.css`），FastAPI 改用 `FRONTEND_DIST = frontend/dist` 托管：`/assets/{path}` 返回构建资源，`/` 与 `/{path}` SPA 兜底，未匹配的 `/api/*` 明确返回 JSON 404；`dist` 未构建时返回 404 并提示 `npm run build`。`backend/tests/test_health.py` 改为断言构建入口、构建资源、`/reports` 深链接与 `/api` 404。
- 遗留文件安全清理：删除已无引用的 `frontend/src/views/PlaceholderView.vue` 与冒烟调试用的 `frontend/scripts/_debug_requests.py`；`DashboardView` 工作台统计、员工个人考勤抽屉仍按主方案后续迭代，不在清理范围内。
- P5（收尾）：工作台 `DashboardView` 接入真实统计（账号信息 + 今日出勤 + 本月概览 + 待审批，数据源 `/api/departments`、`/api/employees`、`/api/attendance`、`/api/reports/monthly`、请假/外派列表），移除“P2 迁移阶段”占位文案；员工管理页「个人考勤」抽屉接入 `/api/attendance/employee/{id}`，含月度汇总、明细与月份切换。冒烟脚本新增工作台真实统计与抽屉检查。
- I6（人脸 + 桌面端）：新增百度云人脸 REST 客户端与 `POST /api/face/register`、`GET /api/face/me`、`POST /api/face/attendance`；`users` 表新增 `face_token`、`face_registered_at`（迁移 `0002_user_face_token`）。注册/换绑只给部门管理员（本部门）与总管理员，员工只能查询状态和刷脸打卡；人脸命中后复用 `attendance.punch` 写考勤。桌面端 `desktop/` 使用 wxPython，`desktop/scripts/build_check.py` 可在无摄像头环境渲染自检。测试 `backend/tests/test_face.py`（10 用例，百度客户端用 fake）。
- I6 真实联调已完成：百度服务开通后，真实人脸检测、注册、检索全部成功；`scripts/e2e_face_demo.py` 走真实 API 完成「管理员代注册 → 员工刷脸签到」，注册 200、打卡 200（相似度 99.9986）。演示库中 E00001 已绑定测试人像（公共测试照片，可通过重新注册换绑），仅用于验证链路。

## 待办交接（下一轮从这里开始）

- I5b 已完成并端到端验证：`frontend/scripts/smoke.py` 新增审批链路检查（普通员工提交申请 + 列表可见，部门管理员可见本部门申请并审批通过，断言状态与审批人、已处理行无审批按钮），三个账号检查块均改用独立上下文并在 `login()` 前清空 localStorage，冒烟脚本可重复运行。审批日期控件改为两个独立 `el-date-picker`，避免 `daterange` 直接填值产生 `Invalid user input` / 事由丢失问题。
- I5c 已完成：报表接口与「报表中心」页面见上，`frontend/scripts/smoke.py` 覆盖总管理员导出 CSV、部门管理员只看本部门。
- P4 已完成：旧 `web/` 下线，FastAPI 托管 `frontend/dist`；开发态仍用 Vite 5173（`/api` 代理 8000），生产/演示态访问 `127.0.0.1:8000`。
- 收尾习惯：每轮结束跑完整 `pytest -q`（当前累计 85 用例）、`npm run build`、`python frontend/scripts/smoke.py`，再同步本文件。

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
.\.venv\Scripts\python.exe -m pytest -q           # 测试（当前 85 passed）
.\.venv\Scripts\python.exe -m scripts.setup_db    # 创建数据库与账号
.\.venv\Scripts\python.exe -m scripts.init_db     # 执行迁移并写入演示数据
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
node --check D:\employee_attendance\web\app.js    # 前端语法检查

cd D:\employee_attendance\frontend
npm install
npm run dev                                       # Vue 开发服务器 127.0.0.1:5173
npm run build                                     # 生产构建到 frontend/dist
python D:\employee_attendance\frontend\scripts\smoke.py   # 浏览器冒烟（需后端+前端已启动）

cd D:\employee_attendance\desktop
python main.py                                    # wxPython 桌面端
python D:\employee_attendance\desktop\scripts\build_check.py  # 桌面端渲染自检
.\.venv\Scripts\python.exe -m scripts.probe_baidu_face        # 百度人脸接口连通性（在 backend 下）
```

## 当前状态

- Vue 前端已接管登录、工作台（真实统计）、我的考勤、考勤中心、审批中心、员工管理（含个人考勤抽屉）、部门管理、班次管理、报表中心
- 考勤接口（I5a）、请假/外派接口（I5b）、报表接口（I5c）均已就绪并端到端验证
- 人脸接口（I6）已就绪：注册/换绑限部门管理员与总管理员，员工可查询绑定状态并刷脸打卡；百度 REST 客户端支持 token 缓存与错误码映射
- 桌面端 `desktop/` 已可运行：登录、人脸注册、人脸签到/签退、无摄像头自检；人脸识别全部由后端调用百度云
- 后端测试 `85 passed, 3 warnings`
- 演示库中已有 1 条 2026-10-13 的 employee 打卡记录（冒烟脚本真实打卡产生）
- 最近一次提交为 `42e540e Migrate console to Vue 3 with I5 business APIs`；I6 人脸与桌面端改动尚未提交
- 待办：`docs/` 部署文档尚未创建；若需换绑或清除 E00001 的测试人像，用管理员在桌面端重新采集，或调用 `face/register` / 百度 faceset 接口删除
