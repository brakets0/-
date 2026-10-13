"""前端冒烟：登录链路、权限菜单/守卫、员工管理 CRUD、响应式布局。

前置条件：
- 后端在 http://127.0.0.1:8000 运行（MySQL 已初始化演示数据）
- 前端 Vite 在 http://127.0.0.1:5173 运行
- 使用系统 Python（已安装 playwright）+ 本机 Edge
"""

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
SCREENSHOT_DIR = ROOT / "_screenshots"
BASE_URL = "http://127.0.0.1:5173"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

SMOKE_EMPLOYEE = {
    "employee_no": "T9001",
    "username": "smoke_user",
    "name": "冒烟员工",
    "password": "secret123",
}
SMOKE_DEPARTMENT = "冒烟部门"
SMOKE_SHIFT_DATE = "2026-11-01"
SMOKE_LEAVE_REASON = "smoke-leave"


def attach_diagnostics(page, label, errors):
    page.on("pageerror", lambda error: errors.append(f"{label} pageerror: {error}"))
    page.on(
        "console",
        lambda message: errors.append(f"{label} console: {message.text}")
        if message.type == "error"
        else None,
    )
    page.on(
        "response",
        lambda response: errors.append(f"{label} http {response.status}: {response.url}")
        if response.status >= 400
        else None,
    )


def login(page, username, password):
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.evaluate("window.localStorage.clear()")
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    page.wait_for_selector(".app-shell")


def new_context(browser, viewport):
    """每个检查块使用独立上下文，避免会话串场。"""
    return browser.new_context(viewport=viewport)


def nav_labels(page):
    return [text.strip() for text in page.locator(".side-nav .nav-item").all_inner_texts()]


def expect_message(page, text):
    page.locator(".el-message", has_text=text).first.wait_for(timeout=10000)


def form_item(dialog, label):
    return dialog.locator(".el-form-item").filter(has_text=label).first


def fill_field(dialog, label, value):
    form_item(dialog, label).locator("input").first.fill(value)


def pick_option(page, dialog, label, option_text):
    form_item(dialog, label).locator(".el-select").first.click()
    page.locator(".el-select-dropdown:visible .el-select-dropdown__item").filter(
        has_text=option_text
    ).first.click()


def employee_row(page, employee_no):
    return page.locator(".employee-table .el-table__row").filter(has_text=employee_no)


def department_row(page, name):
    return page.locator(".department-table .el-table__row").filter(has_text=name)


def shift_row(page, text):
    return page.locator(".shift-table .el-table__row").filter(has_text=text)


def fill_date_field(dialog, label, value):
    input_el = form_item(dialog, label).locator("input").first
    input_el.click()
    input_el.fill(value)
    input_el.press("Enter")


def dispose_rows(page, locator, limit=4):
    """清理上一轮失败留下的测试数据，保证脚本可重复运行。"""
    for _ in range(limit):
        if locator.count() == 0:
            return
        locator.first.get_by_role("button", name="删除").click()
        message_box = page.locator(".el-message-box")
        message_box.wait_for(state="visible")
        message_box.get_by_role("button", name="删除").click()
        expect_message(page, "已删除")
        page.wait_for_timeout(700)


def fill_date_range(dialog, start, end):
    start_item = form_item(dialog, "开始日期")
    end_item = form_item(dialog, "结束日期")
    start_input = start_item.locator("input").first
    end_input = end_item.locator("input").first
    for date_input, value in ((start_input, start), (end_input, end)):
        date_input.click()
        date_input.fill(value)
        date_input.press("Enter")
        assert date_input.input_value() == value, date_input.input_value()


def create_leave_request(page, reason, start="2026-12-01", end="2026-12-02"):
    request_ids = []

    def remember(response):
        if response.request.method == "POST" and response.url.endswith("/api/leave-requests"):
            try:
                request_ids.append(response.json()["id"])
            except Exception:
                pass

    page.on("response", remember)
    page.locator(".panel-header").get_by_role("button", name="新建申请").click()
    dialog = page.locator(".el-dialog").filter(has_text="新建申请")
    dialog.wait_for(state="visible")
    fill_date_range(dialog, start, end)
    form_item(dialog, "事由").locator("textarea").first.fill(reason)
    dialog.get_by_role("button", name="提交申请").click()
    expect_message(page, "请假申请已提交")
    dialog.wait_for(state="hidden")
    page.remove_listener("response", remember)
    return request_ids[-1] if request_ids else None


def request_row(table, reason):
    return table.locator(".el-table__row").filter(has_text=reason)


def api_delete(page, path):
    page.evaluate(
        """
        async (path) => {
            const session = JSON.parse(
                window.localStorage.getItem("employee_attendance_session") || "{}"
            );
            const response = await fetch(`/api${path}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${session.token}` },
            });
            if (!response.ok) {
                throw new Error(`delete failed: ${response.status}`);
            }
        }
        """,
        path,
    )


def api_create_leave_as(
    page,
    username,
    password,
    reason,
    start,
    end,
):
    """以指定账号登录并创建一条请假申请，返回申请 id。"""
    return page.evaluate(
        """
        async ({ username, password, payload }) => {
            const loginResponse = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            if (!loginResponse.ok) {
                throw new Error(`login failed: ${loginResponse.status}`);
            }
            const token = (await loginResponse.json()).access_token;
            const response = await fetch("/api/leave-requests", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                throw new Error(`create failed: ${response.status}`);
            }
            return (await response.json()).id;
        }
        """,
        {
            "username": username,
            "password": password,
            "payload": {
                "leave_type": "事假",
                "start_date": start,
                "end_date": end,
                "duration_days": 1,
                "reason": reason,
            },
        },
    )


def api_delete_reason(page, reason):
    """按事由清理冒烟残留（有审批权限的账号可删除范围内的申请）。"""
    page.evaluate(
        """
        async (reason) => {
            const session = JSON.parse(
                window.localStorage.getItem("employee_attendance_session") || "{}"
            );
            const headers = { Authorization: `Bearer ${session.token}` };
            const response = await fetch("/api/leave-requests", { headers });
            if (!response.ok) {
                throw new Error(`list failed: ${response.status}`);
            }
            for (const item of await response.json()) {
                if (item.reason === reason) {
                    // 无权限清理的残留忽略即可，不影响本轮断言。
                    await fetch(`/api/leave-requests/${item.id}`, {
                        method: "DELETE",
                        headers,
                    }).catch(() => null);
                }
            }
        }
        """,
        reason,
    )


def open_employee_dialog(page, button_name):
    page.get_by_role("button", name=button_name).click()
    dialog = page.locator(".el-dialog")
    dialog.wait_for(state="visible")
    return dialog


def run_admin_checks(browser, errors):
    context = new_context(browser, {"width": 1440, "height": 900})
    page = context.new_page()
    attach_diagnostics(page, "admin", errors)

    page.goto(f"{BASE_URL}/", wait_until="networkidle")
    assert "/login" in page.url, page.url

    login(page, "admin", "admin123")
    page.wait_for_url("**/dashboard")

    admin_nav = nav_labels(page)
    for label in ["工作台", "考勤中心", "审批中心", "员工管理", "部门管理", "班次管理", "报表中心"]:
        assert label in admin_nav, f"总管理员缺少菜单：{label} / {admin_nav}"
    assert "我的考勤" not in admin_nav, f"总管理员不应看到我的考勤：{admin_nav}"
    assert "总管理员" in page.locator(".sidebar-user").inner_text()

    page.screenshot(path=str(SCREENSHOT_DIR / "p0-dashboard-desktop.png"), full_page=True)

    # 总管理员直接访问 /my-attendance 应被守卫弹回工作台
    page.goto(f"{BASE_URL}/my-attendance", wait_until="networkidle")
    assert page.url.endswith("/dashboard"), page.url

    # 会话持久化：刷新后仍停留在应用内
    page.reload(wait_until="networkidle")
    assert page.locator(".app-shell").is_visible()
    assert page.url.endswith("/dashboard")

    # 工作台：真实统计（今日出勤 + 本月概览 + 待审批）
    page.wait_for_selector(".metric-card", timeout=10000)
    page.wait_for_function(
        "() => !document.querySelector('.page-content .el-loading-mask')",
        timeout=10000,
    )
    dashboard_text = page.locator(".page-content").inner_text()
    assert "应出勤" in dashboard_text, dashboard_text
    assert "今日出勤" in dashboard_text, dashboard_text
    assert "本月概览" in dashboard_text, dashboard_text
    assert "平均出勤率" in dashboard_text, dashboard_text
    assert "待审批" in dashboard_text, dashboard_text
    assert "P2 迁移阶段" not in dashboard_text, dashboard_text
    page.screenshot(path=str(SCREENSHOT_DIR / "p5-dashboard-admin.png"), full_page=True)

    # 员工管理：列表 + 新建 + 编辑 + 删除
    page.get_by_role("link", name="员工管理").click()
    page.wait_for_url("**/employees")
    page.wait_for_selector(".employee-table .el-table__row")
    assert page.locator(".employee-table .el-table__row").count() >= 3
    assert "账号、所属部门与角色状态" in page.locator(".panel").first.inner_text()
    dispose_rows(page, employee_row(page, SMOKE_EMPLOYEE["employee_no"]))

    dialog = open_employee_dialog(page, "+ 新建员工")
    fill_field(dialog, "工号", SMOKE_EMPLOYEE["employee_no"])
    fill_field(dialog, "用户名", SMOKE_EMPLOYEE["username"])
    fill_field(dialog, "姓名", SMOKE_EMPLOYEE["name"])
    pick_option(page, dialog, "所属部门", "技术部")
    fill_field(dialog, "初始密码", SMOKE_EMPLOYEE["password"])
    page.get_by_role("button", name="创建员工").click()
    expect_message(page, "员工已创建")

    row = employee_row(page, SMOKE_EMPLOYEE["employee_no"])
    row.wait_for(timeout=10000)
    assert SMOKE_EMPLOYEE["name"] in row.inner_text()
    assert "技术部" in row.inner_text()

    row.get_by_role("button", name="编辑").click()
    dialog = page.locator(".el-dialog")
    dialog.wait_for(state="visible")
    fill_field(dialog, "姓名", "冒烟员工改")
    page.get_by_role("button", name="保存修改").click()
    expect_message(page, "员工信息已更新")

    row = employee_row(page, SMOKE_EMPLOYEE["employee_no"])
    row.wait_for(timeout=10000)
    assert "冒烟员工改" in row.inner_text()

    page.screenshot(path=str(SCREENSHOT_DIR / "p2-employees-desktop.png"), full_page=True)

    row.get_by_role("button", name="删除").click()
    message_box = page.locator(".el-message-box")
    message_box.wait_for(state="visible")
    message_box.get_by_role("button", name="删除").click()
    expect_message(page, "员工已删除")

    page.wait_for_timeout(600)
    assert employee_row(page, SMOKE_EMPLOYEE["employee_no"]).count() == 0

    # 个人考勤抽屉：真实 /api/attendance/employee/{id} 数据
    worker_row = employee_row(page, "E00001")
    worker_row.wait_for(timeout=10000)
    worker_row.get_by_role("button", name="个人考勤").click()
    drawer = page.locator(".el-drawer")
    drawer.wait_for(state="visible")
    page.wait_for_selector(".attendance-drawer-table .el-table__row")
    assert "E00001" in drawer.inner_text()
    assert "出勤率" in drawer.inner_text()
    assert drawer.locator(".attendance-drawer-table .el-table__row").count() >= 1
    page.screenshot(
        path=str(SCREENSHOT_DIR / "p5-employee-attendance-drawer.png"), full_page=True
    )
    drawer.locator(".el-drawer__close-btn").click()
    drawer.wait_for(state="hidden")

    # 部门管理：列表 + 新建 + 编辑 + 指派弹窗 + 删除
    page.get_by_role("link", name="部门管理").click()
    page.wait_for_url("**/departments")
    page.wait_for_selector(".department-table .el-table__row")

    headers = [
        text.strip()
        for text in page.locator(".department-table .el-table__header th").all_inner_texts()
    ]
    assert headers[:5] == ["部门", "人数", "负责人", "班次数", "操作"], headers
    dispose_rows(
        page,
        page.locator(".department-table .el-table__row").filter(has_text=SMOKE_DEPARTMENT),
    )

    tech_row = department_row(page, "技术部")
    tech_row.wait_for()
    assert "技术部" in tech_row.inner_text()

    page.get_by_role("button", name="+ 新建部门").click()
    dialog = page.locator(".el-dialog")
    dialog.wait_for(state="visible")
    fill_field(dialog, "部门名称", SMOKE_DEPARTMENT)
    page.get_by_role("button", name="创建部门").click()
    expect_message(page, "部门已创建")

    row = department_row(page, "冒烟部门")
    row.wait_for(timeout=10000)
    assert "未指定" in row.inner_text()

    row.get_by_role("button", name="编辑").click()
    dialog = page.locator(".el-dialog")
    dialog.wait_for(state="visible")
    fill_field(dialog, "部门名称", "冒烟部门改")
    page.get_by_role("button", name="保存修改").click()
    expect_message(page, "部门已更新")

    row = department_row(page, "冒烟部门改")
    row.wait_for(timeout=10000)

    page.screenshot(path=str(SCREENSHOT_DIR / "p2-departments-desktop.png"), full_page=True)

    # 指派弹窗：列出部门管理员账号（不提交，避免改动演示数据）
    tech_row = department_row(page, "技术部")
    tech_row.get_by_role("button", name="指派管理员").click()
    assign_dialog = page.locator(".el-dialog").filter(has_text="指派管理员")
    assign_dialog.wait_for(state="visible")
    pick_option(page, assign_dialog, "管理员账号", "manager")
    assert "manager" in assign_dialog.inner_text()
    assign_dialog.get_by_role("button", name="取消").click()
    assign_dialog.wait_for(state="hidden")

    row = department_row(page, "冒烟部门改")
    row.get_by_role("button", name="删除").click()
    message_box = page.locator(".el-message-box")
    message_box.wait_for(state="visible")
    message_box.get_by_role("button", name="删除").click()
    expect_message(page, "部门已删除")

    page.wait_for_timeout(600)
    assert department_row(page, "冒烟部门改").count() == 0

    page.set_viewport_size({"width": 390, "height": 844})
    page.reload(wait_until="networkidle")
    page.wait_for_selector(".department-table .el-table__row")
    page.screenshot(path=str(SCREENSHOT_DIR / "p2-departments-mobile.png"), full_page=True)

    page.set_viewport_size({"width": 1440, "height": 900})

    # 班次管理：列表 + 新建 + 修改工作日 + 删除
    page.get_by_role("link", name="班次管理").click()
    page.wait_for_url("**/shifts")
    page.wait_for_selector(".shift-table .el-table__row")

    headers = [
        text.strip()
        for text in page.locator(".shift-table .el-table__header th").all_inner_texts()
    ]
    assert headers[:7] == ["部门", "生效日期", "上班", "下班", "午休", "工作日", "操作"], headers
    dispose_rows(page, shift_row(page, SMOKE_SHIFT_DATE))

    page.get_by_role("button", name="+ 新建班次").click()
    dialog = page.locator(".el-dialog")
    dialog.wait_for(state="visible")
    pick_option(page, dialog, "所属部门", "人事部")
    fill_date_field(dialog, "生效日期", SMOKE_SHIFT_DATE)
    page.get_by_role("button", name="创建班次").click()
    expect_message(page, "班次已创建")

    row = shift_row(page, SMOKE_SHIFT_DATE)
    row.wait_for(timeout=10000)
    assert "人事部" in row.inner_text()
    assert "09:00" in row.inner_text() and "18:00" in row.inner_text()
    assert "周五" in row.inner_text()

    row.get_by_role("button", name="编辑").click()
    dialog = page.locator(".el-dialog")
    dialog.wait_for(state="visible")
    friday = form_item(dialog, "工作日").locator(".el-checkbox").filter(has_text="周五")
    assert friday.locator("input").is_checked()
    friday.click()
    assert not friday.locator("input").is_checked()
    page.get_by_role("button", name="保存修改").click()
    expect_message(page, "班次已更新")

    row = shift_row(page, SMOKE_SHIFT_DATE)
    row.wait_for(timeout=10000)
    assert "周五" not in row.inner_text(), row.inner_text()
    assert "周四" in row.inner_text()

    page.screenshot(path=str(SCREENSHOT_DIR / "p2-shifts-desktop.png"), full_page=True)

    row.get_by_role("button", name="删除").click()
    message_box = page.locator(".el-message-box")
    message_box.wait_for(state="visible")
    message_box.get_by_role("button", name="删除").click()
    expect_message(page, "班次已删除")

    page.wait_for_timeout(600)
    assert shift_row(page, SMOKE_SHIFT_DATE).count() == 0

    # 考勤中心：按日期对账（真实 /api/attendance）
    page.get_by_role("link", name="考勤中心").click()
    page.wait_for_url("**/attendance")
    page.wait_for_selector(".attendance-center-table .el-table__row")
    assert "应出勤" in page.locator(".filter-summary").inner_text()
    attendance_row = page.locator(".attendance-center-table .el-table__row").filter(
        has_text="E00001"
    )
    attendance_row.wait_for()
    assert "技术部" in attendance_row.inner_text()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "p5-attendance-center-desktop.png"), full_page=True
    )

    context.close()


def run_manager_checks(browser, errors):
    context = new_context(browser, {"width": 390, "height": 844})
    page = context.new_page()
    attach_diagnostics(page, "manager", errors)

    login(page, "manager", "manager123")
    page.wait_for_url("**/my-attendance")

    manager_nav = nav_labels(page)
    assert "员工管理" in manager_nav, manager_nav
    assert "部门管理" not in manager_nav, f"部门管理员不应看到部门管理：{manager_nav}"

    page.goto(f"{BASE_URL}/employees", wait_until="networkidle")
    page.wait_for_selector(".employee-table .el-table__row")

    departments = {
        cell.strip()
        for cell in page.locator(
            ".employee-table .el-table__row td:nth-child(3)"
        ).all_inner_texts()
    }
    assert departments <= {"技术部", "—"}, f"部门管理员看到了跨部门员工：{departments}"
    assert "仅本部门员工档案" in page.locator(".panel").first.inner_text()

    dialog = open_employee_dialog(page, "+ 新建员工")
    form_item(dialog, "角色").locator(".el-select").first.click()
    options = page.locator(".el-select-dropdown:visible .el-select-dropdown__item")
    options.first.wait_for()
    assert options.count() == 1, [text.strip() for text in options.all_inner_texts()]
    assert options.first.inner_text().strip() == "普通员工"
    page.keyboard.press("Escape")

    assert "普通员工" in form_item(dialog, "角色").inner_text()

    # 部门管理员只能绑定本部门：下拉显示本部门，且点击不再展开选项
    department_item = form_item(dialog, "所属部门")
    assert "技术部" in department_item.inner_text()
    department_item.locator(".el-select").first.click()
    page.wait_for_timeout(300)
    assert page.locator(".el-select-dropdown:visible .el-select-dropdown__item").count() == 0

    page.get_by_role("button", name="取消").click()
    dialog.wait_for(state="hidden")

    # 部门管理员在考勤中心只能看到本部门
    page.goto(f"{BASE_URL}/attendance", wait_until="networkidle")
    page.wait_for_selector(".attendance-center-table .el-table__row")
    center_departments = {
        cell.strip()
        for cell in page.locator(
            ".attendance-center-table .el-table__row td:nth-child(1)"
        ).all_inner_texts()
    }
    assert center_departments <= {"技术部"}, center_departments

    page.screenshot(path=str(SCREENSHOT_DIR / "p2-employees-mobile.png"), full_page=True)
    context.close()


def run_employee_checks(browser, errors):
    context = new_context(browser, {"width": 390, "height": 844})
    page = context.new_page()
    attach_diagnostics(page, "employee", errors)

    login(page, "employee", "employee123")
    page.wait_for_url("**/my-attendance")

    employee_nav = nav_labels(page)
    assert "我的考勤" in employee_nav, employee_nav
    assert "工作台" not in employee_nav, f"普通员工不应看到工作台：{employee_nav}"
    assert "员工管理" not in employee_nav, f"普通员工不应看到员工管理：{employee_nav}"
    assert "普通员工" in page.locator(".sidebar-user").inner_text()

    # 我的考勤：签到/签退（可重复执行，已打卡时跳过按钮点击）
    page.wait_for_selector(".attendance-table")
    sign_in = page.get_by_role("button", name="签到")
    if sign_in.is_enabled():
        sign_in.click()
        expect_message(page, "签到成功")
    sign_out = page.get_by_role("button", name="签退")
    if sign_out.is_enabled():
        sign_out.click()
        expect_message(page, "签退成功")

    page.wait_for_timeout(500)
    today_status = page.locator(".metric-card").first.inner_text()
    assert "已签到" in today_status or "已签退" in today_status, today_status

    rows = page.locator(".attendance-table .el-table__row")
    assert rows.count() >= 1, "本月考勤明细为空"
    assert rows.first.inner_text().strip() != ""

    page.screenshot(path=str(SCREENSHOT_DIR / "p0-my-attendance-mobile.png"), full_page=True)
    context.close()


def run_request_employee_checks(browser, errors):
    """普通员工：提交请假申请 → 列表可见 → 撤回待审批申请。"""
    context = new_context(browser, {"width": 1440, "height": 900})
    page = context.new_page()
    attach_diagnostics(page, "employee-requests", errors)

    login(page, "employee", "employee123")
    page.wait_for_url("**/my-attendance")

    employee_nav = nav_labels(page)
    assert "审批中心" in employee_nav, f"普通员工缺少审批中心菜单：{employee_nav}"

    page.goto(f"{BASE_URL}/requests", wait_until="networkidle")
    page.wait_for_url("**/requests")
    table = page.locator(".request-table")
    table.wait_for(state="visible")

    request_id = create_leave_request(page, SMOKE_LEAVE_REASON)
    page.wait_for_timeout(500)

    row = request_row(table, SMOKE_LEAVE_REASON)
    row.wait_for(timeout=10000)
    assert "employee" in row.inner_text()
    assert "事假" in row.inner_text()
    assert "待审批" in row.inner_text()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "p5-requests-employee-desktop.png"), full_page=True
    )

    if request_id is None:
        raise AssertionError("未能捕获新建申请 id")
    api_delete(page, f"/leave-requests/{request_id}")
    page.locator(".filter-toolbar").get_by_role("button", name="刷新").click()
    page.wait_for_timeout(600)
    assert request_row(table, SMOKE_LEAVE_REASON).count() == 0

    context.close()


def run_request_manager_checks(browser, errors):
    """部门管理员：本部门申请可见 → 通过 → 已处理行无审批按钮。"""
    context = new_context(browser, {"width": 390, "height": 844})
    page = context.new_page()
    attach_diagnostics(page, "manager-requests", errors)

    login(page, "manager", "manager123")
    page.wait_for_url("**/my-attendance")

    api_delete_reason(page, SMOKE_LEAVE_REASON)
    request_id = api_create_leave_as(
        page,
        "employee",
        "employee123",
        SMOKE_LEAVE_REASON,
        start="2026-12-02",
        end="2026-12-03",
    )

    page.goto(f"{BASE_URL}/requests", wait_until="networkidle")
    table = page.locator(".request-table")
    table.wait_for(state="visible")

    pending_row = request_row(table, SMOKE_LEAVE_REASON)
    pending_row.wait_for(timeout=10000)
    assert "employee" in pending_row.inner_text()
    assert "待审批" in pending_row.inner_text()

    pending_row.get_by_role("button", name="通过").click()
    message_box = page.locator(".el-message-box")
    message_box.wait_for(state="visible")
    message_box.get_by_role("button", name="通过").click()
    expect_message(page, "审批已提交")
    page.wait_for_timeout(600)

    reviewed_row = request_row(table, SMOKE_LEAVE_REASON)
    reviewed_row.wait_for(timeout=10000)
    assert "已通过" in reviewed_row.inner_text()
    assert "manager" in reviewed_row.inner_text()
    assert reviewed_row.get_by_role("button", name="通过").count() == 0
    assert reviewed_row.get_by_role("button", name="驳回").count() == 0
    page.screenshot(
        path=str(SCREENSHOT_DIR / "p5-requests-manager-mobile.png"), full_page=True
    )

    api_delete(page, f"/leave-requests/{request_id}")
    context.close()


def run_report_admin_checks(browser, errors):
    """总管理员：报表中心加载真实月度数据并导出 CSV。"""
    context = new_context(browser, {"width": 1440, "height": 900})
    page = context.new_page()
    attach_diagnostics(page, "admin-reports", errors)

    login(page, "admin", "admin123")
    page.goto(f"{BASE_URL}/reports", wait_until="networkidle")
    page.wait_for_selector(".report-table .el-table__row")
    assert page.locator(".report-table .el-table__row").count() >= 1
    assert "部门" in page.locator(".report-metrics").inner_text()
    assert "全公司" in page.locator(".panel").first.inner_text()
    page.screenshot(
        path=str(SCREENSHOT_DIR / "p5-reports-admin-desktop.png"), full_page=True
    )

    with page.expect_download() as download_info:
        page.get_by_role("button", name="导出 CSV").click()
    download = download_info.value
    assert download.suggested_filename.startswith("考勤报表_"), download.suggested_filename
    csv_path = download.path()
    assert csv_path is not None
    content = Path(csv_path).read_text(encoding="utf-8-sig")
    assert "部门" in content and "出勤率" in content
    assert "技术部" in content

    context.close()


def run_report_manager_checks(browser, errors):
    """部门管理员：报表只覆盖本部门，不出现跨部门数据。"""
    context = new_context(browser, {"width": 390, "height": 844})
    page = context.new_page()
    attach_diagnostics(page, "manager-reports", errors)

    login(page, "manager", "manager123")
    page.goto(f"{BASE_URL}/reports", wait_until="networkidle")
    page.wait_for_selector(".report-table .el-table__row")
    panel_text = page.locator(".panel").first.inner_text()
    assert "全公司" not in panel_text, panel_text
    # 部门管理员没有全公司/部门切换下拉
    assert page.locator(".filter-toolbar .el-select").count() == 0
    table_text = page.locator(".report-table").inner_text()
    assert "人事部" not in table_text, table_text
    page.screenshot(
        path=str(SCREENSHOT_DIR / "p5-reports-manager-mobile.png"), full_page=True
    )

    context.close()


def run():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    errors = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(EDGE), headless=True)
        run_admin_checks(browser, errors)
        run_manager_checks(browser, errors)
        run_employee_checks(browser, errors)
        run_request_employee_checks(browser, errors)
        run_request_manager_checks(browser, errors)
        run_report_admin_checks(browser, errors)
        run_report_manager_checks(browser, errors)
        browser.close()

    if errors:
        raise AssertionError("\n".join(errors))
    print("smoke passed")


if __name__ == "__main__":
    run()
