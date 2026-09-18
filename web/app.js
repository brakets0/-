// Nebula Attendance 管理台前端：先聚焦交互与视觉，API 对接按迭代逐步接入。

const state = {
    user: null,
    token: "",
    page: "dashboard",
};

const $ = (sel) => document.querySelector(sel);

const API_BASE = "";

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
    return escapeHtml(value);
}

async function apiFetch(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
        ? await response.json().catch(() => ({}))
        : await response.text().catch(() => "");
    if (!response.ok) {
        const message =
            typeof data === "object" && data && typeof data.detail === "string"
                ? data.detail
                : "请求失败，请稍后重试";
        throw new Error(message);
    }
    return data;
}

const PAGE_TITLES = {
    dashboard: "工作台",
    "my-attendance": "我的考勤",
    employees: "员工管理",
    departments: "部门管理",
    attendance: "考勤中心",
    shifts: "班次管理",
    requests: "审批中心",
    reports: "报表中心",
};

const ROLE_LABELS = {
    employee: "普通员工",
    department_manager: "部门管理员",
    general_admin: "总管理员",
};

const NAV_ITEMS = [
    { page: "my-attendance", label: "我的考勤", permission: "attendance.view.self", icon: attendanceIcon() },
    { page: "dashboard", label: "工作台", permission: null, icon: dashboardIcon() },
    { page: "attendance", label: "考勤中心", permission: "attendance.view.department", icon: attendanceIcon() },
    { page: "requests", label: "审批中心", permission: "leave.review.department", icon: requestsIcon() },
    { page: "employees", label: "员工管理", permission: "employee.manage.department", icon: employeesIcon() },
    { page: "departments", label: "部门管理", permission: "department.manage", icon: departmentsIcon() },
    { page: "shifts", label: "班次管理", permission: "shift.manage.department", icon: shiftsIcon() },
    { page: "reports", label: "报表中心", permission: "report.view.department", icon: reportsIcon() },
];

const ROUTE_GUARDS = {
    employees: "employee.manage.department",
    departments: "department.manage",
    "my-attendance": "attendance.view.self",
};

let autoLoadTimer = null;

function dashboardIcon() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>';
}

function attendanceIcon() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></svg>';
}

function requestsIcon() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>';
}

function employeesIcon() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>';
}

function departmentsIcon() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l1.5-4a2 2 0 0 1 2-1H15l5 4v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M8 21v-7a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v7"/><path d="M3 9h18"/></svg>';
}

function shiftsIcon() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>';
}

function reportsIcon() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/><line x1="2" y1="20" x2="22" y2="20"/></svg>';
}

function init() {
    const saved = localStorage.getItem("nebula_session");
    if (saved) {
        try {
            const session = JSON.parse(saved);
            state.user = session.user;
            state.token = session.token;
            showApp();
            return;
        } catch (err) {
            localStorage.removeItem("nebula_session");
        }
    }
    showLogin();
}

function showLogin() {
    $("#login-view").classList.remove("hidden");
    $("#app-view").classList.add("hidden");
}

function showApp() {
    $("#login-view").classList.add("hidden");
    $("#app-view").classList.remove("hidden");
    $("#user-name").textContent = state.user?.name || "管理员";
    $("#user-role").textContent = ROLE_LABELS[state.user?.role] || state.user?.role;
    $("#user-avatar").textContent = (state.user?.name || "A").slice(0, 1).toUpperCase();
    renderNav();
    navigate(
        state.user?.role === "employee" || state.user?.role === "department_manager"
            ? "my-attendance"
            : "dashboard"
    );
    startClock();
}

function renderNav() {
    const nav = $("#side-nav");
    nav.innerHTML = "";
    NAV_ITEMS.forEach((item) => {
        if (state.user?.role === "employee" && item.page === "dashboard") return;
        if (state.user?.role === "general_admin" && item.page === "my-attendance") return;
        if (item.permission && !hasPermission(item.permission)) return;
        const button = document.createElement("button");
        button.className = "nav-item" + (state.page === item.page ? " active" : "");
        button.dataset.page = item.page;
        button.innerHTML = `${item.icon}<span>${item.label}</span>`;
        button.addEventListener("click", () => navigate(item.page));
        nav.appendChild(button);
    });
}

function hasPermission(permission) {
    return state.user?.permissions?.includes(permission) || state.user?.role === "general_admin";
}

function navigate(page) {
    const guard = ROUTE_GUARDS[page];
    if (guard && !hasPermission(guard)) {
        page = "dashboard";
    }
    if (state.user?.role === "employee" && page === "dashboard") {
        page = "my-attendance";
    }
    state.page = page;
    $("#page-title").textContent = PAGE_TITLES[page] || "工作台";
    document.querySelectorAll(".nav-item").forEach((el) => {
        el.classList.toggle("active", el.dataset.page === page);
    });
    renderPage(page);
}

function renderPage(page) {
    const content = $("#page-content");
    if (page === "dashboard") {
        renderDashboard(content);
    } else if (page === "my-attendance") {
        renderMyAttendance(content);
    } else if (page === "employees") {
        renderEmployees(content);
    } else if (page === "departments") {
        renderDepartments(content);
    } else if (page === "attendance") {
        renderAttendance(content);
    } else if (page === "requests") {
        renderRequests(content);
    } else if (page === "shifts") {
        renderShifts(content);
    } else if (page === "reports") {
        renderReports(content);
    }
}

function renderMyAttendance(content) {
    const user = state.user || {};
    const department = "技术部";
    const today = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const todayText = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
    content.innerHTML = `
        <div class="hero-grid">
            <article class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>今日状态</div>
                <h3>已打卡</h3>
                <span class="metric-delta">08:56 上班 · 18:02 下班</span>
            </article>
            <article class="metric-card glass accent-violet">
                <div class="metric-label"><span class="status-dot"></span>今日工时</div>
                <h3>7.9h</h3>
                <span class="metric-delta">扣除午休 60 分钟</span>
            </article>
            <article class="metric-card glass accent-pink">
                <div class="metric-label"><span class="status-dot"></span>本月出勤</div>
                <h3>12天</h3>
                <span class="metric-delta">缺勤 0 天 · 迟到 1 次</span>
            </article>
        </div>

        <div class="deep-panel">
            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h3>最近考勤</h3>
                        <p class="panel-sub">仅展示当前账号的打卡记录</p>
                    </div>
                    <span class="status-pill">${todayText}</span>
                </div>
                <table class="data-table">
                    <thead>
                        <tr><th>日期</th><th>上班</th><th>下班</th><th>状态</th><th>工时</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>09-17</td><td>08:56</td><td>18:02</td><td><span class="tag tag-success">正常</span></td><td>7.9h</td></tr>
                        <tr><td>09-16</td><td>09:04</td><td>18:10</td><td><span class="tag tag-warning">迟到</span></td><td>8.0h</td></tr>
                        <tr><td>09-15</td><td>08:50</td><td>18:05</td><td><span class="tag tag-success">正常</span></td><td>8.1h</td></tr>
                        <tr><td>09-14</td><td>08:58</td><td>17:40</td><td><span class="tag tag-warning">早退</span></td><td>7.6h</td></tr>
                    </tbody>
                </table>
            </section>

            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h3>个人档案</h3>
                        <p class="panel-sub">账号与所属部门</p>
                    </div>
                </div>
                <div class="recent-row">
                    <div class="mini-avatar">${(user.name || "员").slice(0, 1)}</div>
                    <div class="recent-info"><strong>${user.name || "员工"}</strong><span>${user.employee_no || "E00001"} · ${department}</span></div>
                    <span class="tag tag-cyan">在职</span>
                </div>
                <div class="timeline">
                    <div class="timeline-item">
                        <strong>本月请假</strong>
                        <span>0.5 天 · 已审批通过</span>
                    </div>
                    <div class="timeline-item">
                        <strong>本月外派</strong>
                        <span>0 天</span>
                    </div>
                </div>
            </section>
        </div>
    `;
}

function renderDashboard(content) {
    const isAdmin = state.user?.role === "general_admin";
    const scopeLabel = isAdmin ? "全公司" : "技术部";
    const todayCount = isAdmin ? 86 : 42;
    const punchedCount = isAdmin ? 74 : 37;
    const pendingCount = isAdmin ? 5 : 2;
    const pendingText = isAdmin ? "请假 3 · 外派 2" : "外派 2 · 待部门审核";
    const activityRows = isAdmin
        ? `
                <div class="recent-row">
                    <div class="mini-avatar">陈</div>
                    <div class="recent-info"><strong>陈晓</strong><span>技术部 · 09:01 打卡 · 正常</span></div>
                    <span class="tag tag-success">完成</span>
                </div>
                <div class="recent-row">
                    <div class="mini-avatar">林</div>
                    <div class="recent-info"><strong>林悦</strong><span>人事部 · 提交请假申请</span></div>
                    <span class="tag tag-warning">待审批</span>
                </div>
                <div class="recent-row">
                    <div class="mini-avatar">周</div>
                    <div class="recent-info"><strong>周航</strong><span>技术部 · 08:52 打卡 · 早到</span></div>
                    <span class="tag tag-cyan">已同步</span>
                </div>`
        : `
                <div class="recent-row">
                    <div class="mini-avatar">陈</div>
                    <div class="recent-info"><strong>陈晓</strong><span>技术部 · 09:01 打卡 · 正常</span></div>
                    <span class="tag tag-success">完成</span>
                </div>
                <div class="recent-row">
                    <div class="mini-avatar">周</div>
                    <div class="recent-info"><strong>周航</strong><span>技术部 · 08:52 打卡 · 早到</span></div>
                    <span class="tag tag-cyan">已同步</span>
                </div>`;
    const approvalRows = isAdmin
        ? `
                    <div class="timeline-item">
                        <strong>林悦 · 事假</strong>
                        <span>9月17日 · 半天 · 待部门经理审核</span>
                    </div>
                    <div class="timeline-item">
                        <strong>周航 · 外派</strong>
                        <span>9月20日 · 2天 · 需总经理审核</span>
                    </div>`
        : `
                    <div class="timeline-item">
                        <strong>周航 · 外派</strong>
                        <span>9月20日 · 2天 · 待部门经理审核</span>
                    </div>`;
    content.innerHTML = `
        <div class="hero-grid">
            <article class="metric-card glass accent-cyan">
                <div class="metric-label"><span class="status-dot"></span>今日应到</div>
                <h3>${todayCount}</h3>
                <span class="metric-delta">实时统计 · ${scopeLabel}</span>
            </article>
            <article class="metric-card glass accent-violet">
                <div class="metric-label"><span class="status-dot"></span>已打卡</div>
                <h3>${punchedCount}</h3>
                <span class="metric-delta">${isAdmin ? "打卡率 86.0%" : "打卡率 88.1%"}</span>
            </article>
            <article class="metric-card glass accent-pink">
                <div class="metric-label"><span class="status-dot"></span>待审批</div>
                <h3>${pendingCount}</h3>
                <span class="metric-delta">${pendingText}</span>
            </article>
        </div>

        <div class="deep-panel">
            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h3>实时动态</h3>
                        <p class="panel-sub">最近考勤与审批事件</p>
                    </div>
                    <span class="status-pill">LIVE</span>
                </div>
                ${activityRows}
            </section>

            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h3>本周审批</h3>
                        <p class="panel-sub">${pendingCount} 条待处理</p>
                    </div>
                </div>
                <div class="timeline">
                    ${approvalRows}
                </div>
            </section>
        </div>
    `;
}

function renderEmployees(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "账号、所属部门与角色状态" : "仅本部门员工档案";
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>员工档案</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <button class="btn btn-ghost" id="add-employee-btn">+ 新建员工</button>
            </div>
            <table class="data-table">
                <thead>
                    <tr><th>工号</th><th>姓名</th><th>部门</th><th>角色</th><th>状态</th><th>操作</th></tr>
                </thead>
                <tbody>
                    <tr><td colspan="6" class="table-loading">正在加载员工列表...</td></tr>
                </tbody>
            </table>
            <div class="panel-footer">
                <button class="btn btn-ghost btn-sm" id="refresh-employees-btn">刷新</button>
            </div>
        </section>
    `;
    $("#add-employee-btn").addEventListener("click", () => openEmployeeForm());
    $("#refresh-employees-btn").addEventListener("click", () => renderEmployees(content));
    loadEmployees(content);
}

async function loadEmployees(content) {
    const tbody = content.querySelector("tbody");
    try {
        const employees = await apiFetch("/employees");
        const rows = employees.map((employee) => {
            const roleTag =
                employee.role === "general_admin"
                    ? "tag-violet"
                    : employee.role === "department_manager"
                    ? "tag-violet"
                    : "tag-cyan";
            const statusTag = employee.status === "active" ? "tag-success" : "tag-danger";
            const statusText = employee.status === "active" ? "在职" : "停用";
            const roleText =
                employee.role === "general_admin"
                    ? "总管理员"
                    : employee.role === "department_manager"
                    ? "部门管理员"
                    : "普通员工";
            return `
                <tr>
                    <td>${escapeHtml(employee.employee_no)}</td>
                    <td>${escapeHtml(employee.name)}</td>
                    <td>${escapeHtml(employee.department_name || "—")}</td>
                    <td><span class="tag ${roleTag}">${roleText}</span></td>
                    <td><span class="tag ${statusTag}">${statusText}</span></td>
                    <td>
                        <div class="row-actions">
                            ${state.user?.role === "general_admin" || employee.role === "employee" ? `<button class="btn btn-ghost btn-sm" data-employee-id="${employee.id}" data-action="edit">编辑</button>` : ""}
                            <button class="btn btn-ghost btn-sm" data-employee-id="${employee.id}" data-action="attendance">个人考勤</button>
                            ${state.user?.role === "general_admin" ? `<button class="btn btn-ghost btn-sm btn-danger" data-employee-id="${employee.id}" data-action="delete">删除</button>` : ""}
                        </div>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = rows.length ? rows.join("") : '<tr><td colspan="6" class="table-empty">暂无员工</td></tr>';
        tbody.querySelectorAll("[data-action='edit']").forEach((btn) => {
            btn.addEventListener("click", () => {
                const employee = employees.find((item) => item.id === Number(btn.dataset.employeeId));
                openEmployeeForm(employee);
            });
        });
        tbody.querySelectorAll("[data-action='attendance']").forEach((btn) => {
            btn.addEventListener("click", () => {
                const employee = employees.find((item) => item.id === Number(btn.dataset.employeeId));
                openEmployeeAttendance({
                    employeeNo: employee?.employee_no || "—",
                    employeeName: employee?.name || "员工",
                    department: employee?.department_name || "未分配",
                });
            });
        });
        tbody.querySelectorAll("[data-action='delete']").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const employee = employees.find((item) => item.id === Number(btn.dataset.employeeId));
                if (!employee) return;
                if (!window.confirm(`确定删除员工「${employee.name}」吗？`)) return;
                try {
                    await apiFetch(`/employees/${employee.id}`, { method: "DELETE" });
                    toast("员工已删除");
                    renderEmployees(content);
                } catch (err) {
                    toast(err.message);
                }
            });
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="table-empty">${escapeHtml(err.message)}</td></tr>`;
    }
}

async function openEmployeeForm(employee = null) {
    let departments = [];
    try {
        departments = await apiFetch("/departments");
    } catch (err) {
        toast(err.message);
        return;
    }
    const isAdmin = state.user?.role === "general_admin";
    const departmentOptions = isAdmin
        ? `<option value="">不分配</option>` +
          departments.map((dept) => `<option value="${dept.id}" ${employee?.department_id === dept.id ? "selected" : ""}>${escapeHtml(dept.name)}</option>`).join("")
        : departments
              .filter((dept) => dept.id === state.user?.department_id)
              .map((dept) => `<option value="${dept.id}" selected>${escapeHtml(dept.name)}</option>`)
              .join("");
    const roleOptions = isAdmin
        ? `<option value="employee">普通员工</option>` +
          `<option value="department_manager">部门管理员</option>` +
          `<option value="general_admin">总管理员</option>`
        : `<option value="employee">普通员工</option>`;
    const statusOptions = `
        <option value="active">在职</option>
        <option value="inactive">停用</option>
    `;
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `
        <div class="modal-panel glass" role="dialog" aria-modal="true" aria-label="${employee ? "编辑员工" : "新建员工"}">
            <div class="modal-header">
                <div>
                    <p class="drawer-kicker">EMPLOYEE PROFILE</p>
                    <h3>${employee ? "编辑员工" : "新建员工"}</h3>
                </div>
                <button class="icon-btn modal-close" title="关闭" aria-label="关闭">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <form class="form-grid" data-employee-id="${employee?.id || ""}">
                <label class="form-field">
                    <span>工号</span>
                    <input name="employee_no" value="${escapeAttr(employee?.employee_no || "")}" required>
                </label>
                <label class="form-field">
                    <span>用户名</span>
                    <input name="username" value="${escapeAttr(employee?.username || "")}" required>
                </label>
                <label class="form-field">
                    <span>姓名</span>
                    <input name="name" value="${escapeAttr(employee?.name || "")}" required>
                </label>
                <label class="form-field">
                    <span>所属部门</span>
                    <select name="department_id">${departmentOptions}</select>
                </label>
                <label class="form-field">
                    <span>角色</span>
                    <select name="role">${roleOptions}</select>
                </label>
                <label class="form-field">
                    <span>状态</span>
                    <select name="status">${statusOptions.replace(/value="active"/, `value="active" ${employee?.status === "active" ? "selected" : ""}`).replace(/value="inactive"/, `value="inactive" ${employee?.status === "inactive" ? "selected" : ""}`)}</select>
                </label>
                ${!employee ? '<label class="form-field form-field-wide"><span>初始密码</span><input name="password" type="password" minlength="6" required placeholder="至少 6 位"></label>' : ""}
                <div class="form-actions form-field-wide">
                    <button type="button" class="btn btn-ghost" data-action="cancel">取消</button>
                    <button type="submit" class="btn btn-primary">${employee ? "保存修改" : "创建员工"}</button>
                </div>
            </form>
        </div>
    `;
    const selectRole = wrap.querySelector("select[name='role']");
    if (employee?.role) selectRole.value = employee.role;
    wrap.addEventListener("click", (event) => {
        if (event.target === wrap || event.target.closest("[data-action='cancel'], .modal-close")) {
            wrap.remove();
        }
    });
    wrap.querySelector("form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = Object.fromEntries(new FormData(form).entries());
        if (payload.role === "general_admin") {
            payload.department_id = null;
        }
        if (!form.dataset.employeeId) {
            payload.department_id = payload.department_id ? Number(payload.department_id) : null;
        } else {
            delete payload.password;
            payload.department_id = payload.department_id ? Number(payload.department_id) : null;
        }
        try {
            if (form.dataset.employeeId) {
                await apiFetch(`/employees/${form.dataset.employeeId}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                toast("员工信息已更新");
            } else {
                await apiFetch("/employees", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                toast("员工已创建");
            }
            wrap.remove();
            renderEmployees($("#page-content"));
        } catch (err) {
            toast(err.message);
        }
    });
    document.body.appendChild(wrap);
}

function openEmployeeAttendance({ employeeNo, employeeName, department }) {
    const wrap = document.createElement("div");
    wrap.className = "attendance-drawer-backdrop";
    wrap.innerHTML = `
        <aside class="attendance-drawer glass" role="dialog" aria-modal="true" aria-label="个人考勤">
            <div class="drawer-header">
                <div>
                    <p class="drawer-kicker">EMPLOYEE ATTENDANCE</p>
                    <h3>${employeeName} · 个人考勤</h3>
                    <p class="panel-sub">工号 ${employeeNo} · ${department}</p>
                </div>
                <button class="icon-btn drawer-close" title="关闭" aria-label="关闭">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div class="drawer-metrics">
                <div class="metric-card glass accent-cyan">
                    <div class="metric-label"><span class="status-dot"></span>本月出勤</div>
                    <h3>94.6%</h3>
                    <span class="metric-delta">缺勤 1 天</span>
                </div>
                <div class="metric-card glass accent-violet">
                    <div class="metric-label"><span class="status-dot"></span>平均工时</div>
                    <h3>7.9h</h3>
                    <span class="metric-delta">本月 21 个工作日</span>
                </div>
                <div class="metric-card glass accent-pink">
                    <div class="metric-label"><span class="status-dot"></span>迟到/早退</div>
                    <h3>2 次</h3>
                    <span class="metric-delta">迟到 1 · 早退 1</span>
                </div>
            </div>
            <table class="data-table">
                <thead><tr><th>日期</th><th>上班</th><th>下班</th><th>状态</th><th>工时</th></tr></thead>
                <tbody>
                    <tr><td>09-17</td><td>08:56</td><td>18:02</td><td><span class="tag tag-success">正常</span></td><td>7.9h</td></tr>
                    <tr><td>09-16</td><td>09:04</td><td>18:10</td><td><span class="tag tag-warning">迟到</span></td><td>8.0h</td></tr>
                    <tr><td>09-15</td><td>08:50</td><td>18:05</td><td><span class="tag tag-success">正常</span></td><td>8.1h</td></tr>
                    <tr><td>09-14</td><td>08:58</td><td>17:40</td><td><span class="tag tag-warning">早退</span></td><td>7.6h</td></tr>
                    <tr><td>09-13</td><td>---</td><td>---</td><td><span class="tag tag-danger">缺勤</span></td><td>0h</td></tr>
                </tbody>
            </table>
            <div class="drawer-footer">
                <p class="demo-note">个人考勤明细将在考勤 API 就绪后实时联调；当前展示界面结构与数据样例。</p>
                <button class="btn btn-primary" data-action="close">关闭</button>
            </div>
        </aside>
    `;
    wrap.addEventListener("click", (event) => {
        if (event.target === wrap || event.target.closest("[data-action='close'], .drawer-close")) {
            wrap.remove();
        }
    });
    document.body.appendChild(wrap);
}

function renderDepartments(content) {
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>部门概览</h3>
                    <p class="panel-sub">部门规模、负责人与默认班次数</p>
                </div>
                <button class="btn btn-ghost" id="add-dept-btn">+ 新建部门</button>
            </div>
            <table class="data-table">
                <thead><tr><th>部门</th><th>人数</th><th>负责人</th><th>班次数</th><th>操作</th></tr></thead>
                <tbody>
                    <tr><td colspan="5" class="table-loading">正在加载部门列表...</td></tr>
                </tbody>
            </table>
            <div class="panel-footer">
                <button class="btn btn-ghost btn-sm" id="refresh-depts-btn">刷新</button>
            </div>
        </section>
    `;
    $("#add-dept-btn").addEventListener("click", () => openDepartmentForm());
    $("#refresh-depts-btn").addEventListener("click", () => renderDepartments(content));
    loadDepartments(content);
}

async function loadDepartments(content) {
    const tbody = content.querySelector("tbody");
    try {
        const departments = await apiFetch("/departments");
        const rows = departments.map((dept) => {
            const shiftCount = dept.shift_count || 0;
            return `
                <tr>
                    <td>${escapeHtml(dept.name)}</td>
                    <td>${dept.employee_count ?? 0}</td>
                    <td>${escapeHtml(dept.manager_name || "未指定")}</td>
                    <td>${shiftCount}</td>
                    <td>
                        <div class="row-actions">
                            <button class="btn btn-ghost btn-sm" data-dept-id="${dept.id}" data-action="edit">编辑</button>
                            <button class="btn btn-ghost btn-sm" data-dept-id="${dept.id}" data-action="assign">指派管理员</button>
                            <button class="btn btn-ghost btn-sm btn-danger" data-dept-id="${dept.id}" data-action="delete">删除</button>
                        </div>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = rows.length ? rows.join("") : '<tr><td colspan="5" class="table-empty">暂无部门</td></tr>';
        tbody.querySelectorAll("[data-action='edit']").forEach((btn) => {
            btn.addEventListener("click", () => {
                const dept = departments.find((item) => item.id === Number(btn.dataset.deptId));
                openDepartmentForm(dept);
            });
        });
        tbody.querySelectorAll("[data-action='assign']").forEach((btn) => {
            btn.addEventListener("click", () => {
                const dept = departments.find((item) => item.id === Number(btn.dataset.deptId));
                openAssignManagerForm(dept);
            });
        });
        tbody.querySelectorAll("[data-action='delete']").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const dept = departments.find((item) => item.id === Number(btn.dataset.deptId));
                if (!dept) return;
                if (!window.confirm(`确定删除部门「${dept.name}」吗？`)) return;
                try {
                    await apiFetch(`/departments/${dept.id}`, { method: "DELETE" });
                    toast("部门已删除");
                    renderDepartments(content);
                } catch (err) {
                    toast(err.message);
                }
            });
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="table-empty">${escapeHtml(err.message)}</td></tr>`;
    }
}

async function openDepartmentForm(department = null) {
    let managers = [];
    try {
        managers = await apiFetch("/employees");
    } catch (err) {
        managers = [];
    }
    const managerOptions = `<option value="">未指定</option>` +
        managers
            .filter((item) => item.role === "department_manager")
            .map((item) => `<option value="${item.id}" ${department?.manager_user_id === item.id ? "selected" : ""}>${escapeHtml(item.name)}（${escapeHtml(item.department_name || "未分配")}）</option>`)
            .join("");
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `
        <div class="modal-panel glass" role="dialog" aria-modal="true" aria-label="${department ? "编辑部门" : "新建部门"}">
            <div class="modal-header">
                <div>
                    <p class="drawer-kicker">DEPARTMENT PROFILE</p>
                    <h3>${department ? "编辑部门" : "新建部门"}</h3>
                </div>
                <button class="icon-btn modal-close" title="关闭" aria-label="关闭">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <form class="form-grid" data-dept-id="${department?.id || ""}">
                <label class="form-field form-field-wide">
                    <span>部门名称</span>
                    <input name="name" value="${escapeAttr(department?.name || "")}" required maxlength="50">
                </label>
                <label class="form-field form-field-wide">
                    <span>部门管理员</span>
                    <select name="manager_user_id">${managerOptions}</select>
                </label>
                <div class="form-actions form-field-wide">
                    <button type="button" class="btn btn-ghost" data-action="cancel">取消</button>
                    <button type="submit" class="btn btn-primary">${department ? "保存修改" : "创建部门"}</button>
                </div>
            </form>
        </div>
    `;
    wrap.addEventListener("click", (event) => {
        if (event.target === wrap || event.target.closest("[data-action='cancel'], .modal-close")) {
            wrap.remove();
        }
    });
    wrap.querySelector("form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = Object.fromEntries(new FormData(form).entries());
        payload.manager_user_id = payload.manager_user_id ? Number(payload.manager_user_id) : null;
        try {
            if (form.dataset.deptId) {
                await apiFetch(`/departments/${form.dataset.deptId}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                toast("部门已更新");
            } else {
                await apiFetch("/departments", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                toast("部门已创建");
            }
            wrap.remove();
            renderDepartments($("#page-content"));
        } catch (err) {
            toast(err.message);
        }
    });
    document.body.appendChild(wrap);
}

async function openAssignManagerForm(department) {
    if (!department) return;
    let managers = [];
    try {
        managers = await apiFetch("/employees");
    } catch (err) {
        toast(err.message);
        return;
    }
    const options = managers
        .filter((item) => item.role === "department_manager")
        .map((item) => `<option value="${item.id}" ${department.manager_user_id === item.id ? "selected" : ""}>${escapeHtml(item.name)}（${escapeHtml(item.department_name || "未分配")}）</option>`)
        .join("");
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `
        <div class="modal-panel glass" role="dialog" aria-modal="true" aria-label="指派部门管理员">
            <div class="modal-header">
                <div>
                    <p class="drawer-kicker">ASSIGN MANAGER</p>
                    <h3>指派管理员 · ${escapeHtml(department.name)}</h3>
                </div>
                <button class="icon-btn modal-close" title="关闭" aria-label="关闭">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <form class="form-grid" data-dept-id="${department.id}">
                <label class="form-field form-field-wide">
                    <span>管理员账号</span>
                    <select name="manager_user_id">
                        <option value="">取消指派</option>
                        ${options}
                    </select>
                </label>
                <div class="form-actions form-field-wide">
                    <button type="button" class="btn btn-ghost" data-action="cancel">取消</button>
                    <button type="submit" class="btn btn-primary">保存指派</button>
                </div>
            </form>
        </div>
    `;
    wrap.addEventListener("click", (event) => {
        if (event.target === wrap || event.target.closest("[data-action='cancel'], .modal-close")) {
            wrap.remove();
        }
    });
    wrap.querySelector("form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const managerUserId = new FormData(form).get("manager_user_id");
        const payload = { manager_user_id: managerUserId ? Number(managerUserId) : null };
        try {
            await apiFetch(`/departments/${form.dataset.deptId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            toast("管理员已指派");
            wrap.remove();
            renderDepartments($("#page-content"));
        } catch (err) {
            toast(err.message);
        }
    });
    document.body.appendChild(wrap);
}

function renderAttendance(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "按部门汇总当日打卡状态" : "仅本部门今日考勤";
    const rows = isAdmin
        ? [
            '<tr><td>技术部</td><td>42</td><td>37</td><td>2</td><td>1</td><td>2</td></tr>',
            '<tr><td>人事部</td><td>18</td><td>15</td><td>1</td><td>0</td><td>2</td></tr>',
        ]
        : [
            '<tr><td>技术部</td><td>42</td><td>37</td><td>2</td><td>1</td><td>2</td></tr>',
        ];
    const demoNote = isAdmin
        ? '<p class="demo-note">数据将在 I5 考勤接口完成后实时联调；当前页面展示的是界面结构与交互。</p>'
        : '<p class="demo-note">仅统计本部门员工；I5 考勤接口完成后实时联调。</p>';
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>今日考勤</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <span class="status-pill">2026-09-17 周四</span>
            </div>
            <table class="data-table">
                <thead><tr><th>部门</th><th>应到</th><th>已打卡</th><th>迟到</th><th>早退</th><th>缺勤</th></tr></thead>
                <tbody>
                    ${rows.join("")}
                </tbody>
            </table>
            ${demoNote}
        </section>
    `;
}

function renderRequests(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "请假与外派申请单" : "仅本部门请假与外派申请单";
    const rows = isAdmin
        ? [
            '<tr><td>林悦</td><td><span class="tag tag-warning">事假</span></td><td>09-17</td><td>0.5 天</td><td><span class="tag tag-violet">待审批</span></td></tr>',
            '<tr><td>周航</td><td><span class="tag tag-cyan">外派</span></td><td>09-20 至 09-21</td><td>2.0 天</td><td><span class="tag tag-violet">待审批</span></td></tr>',
            '<tr><td>陈晓</td><td><span class="tag tag-success">年假</span></td><td>09-24</td><td>1.0 天</td><td><span class="tag tag-success">已通过</span></td></tr>',
        ]
        : [
            '<tr><td>周航</td><td><span class="tag tag-cyan">外派</span></td><td>09-20 至 09-21</td><td>2.0 天</td><td><span class="tag tag-violet">待审批</span></td></tr>',
            '<tr><td>陈晓</td><td><span class="tag tag-success">年假</span></td><td>09-24</td><td>1.0 天</td><td><span class="tag tag-success">已通过</span></td></tr>',
        ];
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>审批中心</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <div class="panel-actions">
                    <button class="btn btn-ghost">请假</button>
                    <button class="btn btn-ghost">外派</button>
                </div>
            </div>
            <table class="data-table">
                <thead><tr><th>申请人</th><th>类型</th><th>日期</th><th>时长</th><th>状态</th></tr></thead>
                <tbody>
                    ${rows.join("")}
                </tbody>
            </table>
        </section>
    `;
}

function renderShifts(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "部门默认班次与午休设置" : "仅本部门班次设置";
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>班次管理</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <button class="btn btn-ghost" id="add-shift-btn">+ 新建班次</button>
            </div>
            <table class="data-table">
                <thead><tr><th>部门</th><th>生效日期</th><th>上班</th><th>下班</th><th>午休</th><th>工作日</th><th>操作</th></tr></thead>
                <tbody>
                    <tr><td colspan="7" class="table-loading">正在加载班次列表...</td></tr>
                </tbody>
            </table>
            <div class="panel-footer">
                <button class="btn btn-ghost btn-sm" id="refresh-shifts-btn">刷新</button>
            </div>
        </section>
    `;
    $("#add-shift-btn").addEventListener("click", () => openShiftForm());
    $("#refresh-shifts-btn").addEventListener("click", () => renderShifts(content));
    loadShifts(content);
}

async function loadShifts(content) {
    const tbody = content.querySelector("tbody");
    try {
        const shifts = await apiFetch("/shifts");
        const rows = shifts.map((shift) => {
            const workdays = formatWorkdays(shift.workdays);
            const breakText = shift.break_start && shift.break_end
                ? `${shift.break_start.slice(0, 5)} - ${shift.break_end.slice(0, 5)}`
                : "无午休";
            return `
                <tr>
                    <td>${escapeHtml(shift.department_name || "—")}</td>
                    <td>${escapeHtml(shift.effective_from)}</td>
                    <td>${escapeHtml(shift.work_start.slice(0, 5))}</td>
                    <td>${escapeHtml(shift.work_end.slice(0, 5))}</td>
                    <td>${breakText}</td>
                    <td>${workdays}</td>
                    <td>
                        <div class="row-actions">
                            <button class="btn btn-ghost btn-sm" data-shift-id="${shift.id}" data-action="edit">编辑</button>
                            <button class="btn btn-ghost btn-sm btn-danger" data-shift-id="${shift.id}" data-action="delete">删除</button>
                        </div>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = rows.length ? rows.join("") : '<tr><td colspan="7" class="table-empty">暂无班次</td></tr>';
        tbody.querySelectorAll("[data-action='edit']").forEach((btn) => {
            btn.addEventListener("click", () => {
                const shift = shifts.find((item) => item.id === Number(btn.dataset.shiftId));
                openShiftForm(shift);
            });
        });
        tbody.querySelectorAll("[data-action='delete']").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const shift = shifts.find((item) => item.id === Number(btn.dataset.shiftId));
                if (!shift) return;
                if (!window.confirm("确定删除该班次吗？")) return;
                try {
                    await apiFetch(`/shifts/${shift.id}`, { method: "DELETE" });
                    toast("班次已删除");
                    renderShifts(content);
                } catch (err) {
                    toast(err.message);
                }
            });
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="table-empty">${escapeHtml(err.message)}</td></tr>`;
    }
}

function formatWorkdays(value) {
    if (!value) return "—";
    const labels = { 1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "日" };
    return value
        .split(",")
        .map((day) => `周${labels[day] || day}`)
        .join(" · ");
}

async function openShiftForm(shift = null) {
    let departments = [];
    try {
        departments = await apiFetch("/departments");
    } catch (err) {
        toast(err.message);
        return;
    }
    const isAdmin = state.user?.role === "general_admin";
    const departmentOptions = isAdmin
        ? departments.map((dept) => `<option value="${dept.id}" ${shift?.department_id === dept.id ? "selected" : ""}>${escapeHtml(dept.name)}</option>`).join("")
        : departments
              .filter((dept) => dept.id === state.user?.department_id)
              .map((dept) => `<option value="${dept.id}" selected>${escapeHtml(dept.name)}</option>`)
              .join("");
    const workdays = shift?.workdays ? new Set(shift.workdays.split(",").map(Number)) : new Set([1, 2, 3, 4, 5]);
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `
        <div class="modal-panel glass" role="dialog" aria-modal="true" aria-label="${shift ? "编辑班次" : "新建班次"}">
            <div class="modal-header">
                <div>
                    <p class="drawer-kicker">SHIFT PROFILE</p>
                    <h3>${shift ? "编辑班次" : "新建班次"}</h3>
                </div>
                <button class="icon-btn modal-close" title="关闭" aria-label="关闭">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <form class="form-grid" data-shift-id="${shift?.id || ""}">
                <label class="form-field">
                    <span>所属部门</span>
                    <select name="department_id">${departmentOptions}</select>
                </label>
                <label class="form-field">
                    <span>生效日期</span>
                    <input name="effective_from" type="date" value="${escapeAttr(shift?.effective_from || "")}" required>
                </label>
                <label class="form-field">
                    <span>上班时间</span>
                    <input name="work_start" type="time" value="${escapeAttr(shift?.work_start?.slice(0, 5) || "09:00")}" required>
                </label>
                <label class="form-field">
                    <span>下班时间</span>
                    <input name="work_end" type="time" value="${escapeAttr(shift?.work_end?.slice(0, 5) || "18:00")}" required>
                </label>
                <label class="form-field">
                    <span>午休开始</span>
                    <input name="break_start" type="time" value="${escapeAttr(shift?.break_start?.slice(0, 5) || "")}">
                </label>
                <label class="form-field">
                    <span>午休结束</span>
                    <input name="break_end" type="time" value="${escapeAttr(shift?.break_end?.slice(0, 5) || "")}">
                </label>
                <fieldset class="form-field form-field-wide workday-field">
                    <legend>工作日</legend>
                    <div class="workday-options">
                        ${[1, 2, 3, 4, 5, 6, 7].map((day) => `<label class="workday-check"><input type="checkbox" name="workdays" value="${day}" ${workdays.has(day) ? "checked" : ""}> 周${"一二三四五六日"[day - 1]}</label>`).join("")}
                    </div>
                </fieldset>
                <div class="form-actions form-field-wide">
                    <button type="button" class="btn btn-ghost" data-action="cancel">取消</button>
                    <button type="submit" class="btn btn-primary">${shift ? "保存修改" : "创建班次"}</button>
                </div>
            </form>
        </div>
    `;
    wrap.addEventListener("click", (event) => {
        if (event.target === wrap || event.target.closest("[data-action='cancel'], .modal-close")) {
            wrap.remove();
        }
    });
    wrap.querySelector("form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const formData = new FormData(form);
        const days = formData.getAll("workdays").map(Number).sort((a, b) => a - b);
        if (!days.length) {
            toast("请至少选择一天工作日");
            return;
        }
        const payload = {
            department_id: Number(formData.get("department_id")),
            effective_from: formData.get("effective_from"),
            work_start: formData.get("work_start"),
            work_end: formData.get("work_end"),
            break_start: formData.get("break_start") || null,
            break_end: formData.get("break_end") || null,
            workdays: days.join(","),
        };
        try {
            if (form.dataset.shiftId) {
                await apiFetch(`/shifts/${form.dataset.shiftId}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                toast("班次已更新");
            } else {
                await apiFetch("/shifts", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                toast("班次已创建");
            }
            wrap.remove();
            renderShifts($("#page-content"));
        } catch (err) {
            toast(err.message);
        }
    });
    document.body.appendChild(wrap);
}

function renderReports(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "工时、出勤率与请假分布" : "仅本部门月度报表";
    const rows = isAdmin
        ? `
            <tr><td>技术部</td><td>94.6%</td><td>7.9h</td><td>18.5</td><td>6.0</td></tr>
            <tr><td>人事部</td><td>92.1%</td><td>7.7h</td><td>9.0</td><td>2.0</td></tr>
        `
        : `
            <tr><td>技术部</td><td>94.6%</td><td>7.9h</td><td>18.5</td><td>6.0</td></tr>
        `;
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>月度报表</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <button class="btn btn-ghost">导出报表</button>
            </div>
            <table class="data-table">
                <thead><tr><th>部门</th><th>出勤率</th><th>平均工时</th><th>请假天数</th><th>外派天数</th></tr></thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        </section>
    `;
}

async function login(username, password) {
    $("#login-error").textContent = "";
    const button = $("#login-button");
    button.disabled = true;
    button.querySelector("span").textContent = "正在登录...";
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || "登录失败");

        state.user = data.user;
        state.token = data.access_token;
        const profile = await loadCurrentUser();
        state.user = { ...state.user, ...profile };
        localStorage.setItem("nebula_session", JSON.stringify({ user: state.user, token: state.token }));
        showApp();
        toast(`欢迎回来，${state.user.name || state.user.username}`);
    } catch (err) {
        $("#login-error").textContent = err.message || "登录失败，请检查账号密码";
    } finally {
        button.disabled = false;
        button.querySelector("span").textContent = "登录管理台";
    }
}

async function loadCurrentUser() {
    const response = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!response.ok) throw new Error("获取用户信息失败");
    const profile = await response.json();
    return {
        id: profile.id,
        employee_no: profile.employee_no,
        username: profile.username,
        name: profile.name,
        role: profile.role,
        department_id: profile.department_id,
        permissions: profile.permissions || [],
    };
}

function logout() {
    localStorage.removeItem("nebula_session");
    state.user = null;
    state.token = "";
    showLogin();
}

function startClock() {
    const update = () => {
        const now = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        $("#live-time").textContent = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    };
    update();
    clearInterval(autoLoadTimer);
    autoLoadTimer = setInterval(update, 1000);
}

function toast(message) {
    const wrap = $("#toast-wrap");
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = message;
    wrap.appendChild(el);
    setTimeout(() => el.remove(), 3200);
}

document.addEventListener("DOMContentLoaded", () => {
    init();

    $("#login-form").addEventListener("submit", (event) => {
        event.preventDefault();
        login($("#login-username").value.trim(), $("#login-password").value);
    });

    document.querySelectorAll(".account-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            $("#login-username").value = chip.dataset.username;
            $("#login-password").value = chip.dataset.password;
            $("#login-button").focus();
        });
    });

    $("#logout-button").addEventListener("click", logout);
    $("#refresh-button").addEventListener("click", () => {
        navigate(state.page);
        toast("数据已刷新");
    });
});
