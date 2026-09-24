// Nebula Attendance 管理台前端：先聚焦交互与视觉，API 对接按迭代逐步接入。

const state = {
    user: null,
    token: "",
    page: "dashboard",
    attendanceFilters: {
        date: "",
        departmentId: "all",
    },
    requestFilters: {
        type: "all",
        status: "all",
    },
    reportFilters: {
        month: "",
        departmentId: "all",
    },
    departments: [],
    demoRequests: null,
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

function pad2(value) {
    return String(value).padStart(2, "0");
}

function formatLocalDate(date = new Date()) {
    return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function parseLocalDate(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]) - 1;
    const day = Number(match[3]);
    const date = new Date(year, month, day);
    return date.getFullYear() === year && date.getMonth() === month && date.getDate() === day
        ? date
        : null;
}

function addLocalDays(value, days) {
    const date = typeof value === "string" ? parseLocalDate(value) : new Date(value);
    if (!date) return null;
    const next = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    next.setDate(next.getDate() + days);
    return next;
}

function formatMonthValue(date = new Date()) {
    return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}`;
}

function formatMonthLabel(value) {
    const match = /^(\d{4})-(\d{2})$/.exec(String(value || ""));
    if (!match) return value || "—";
    return `${match[1]}年${Number(match[2])}月`;
}

function formatDateWithWeekday(value) {
    const date = parseLocalDate(value);
    if (!date) return value || "—";
    const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
    return `${value} ${weekdays[date.getDay()]}`;
}

function formatShortDate(value) {
    const date = parseLocalDate(value);
    return date ? `${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}` : value || "—";
}

function formatDateRange(start, end) {
    if (!start || !end || start === end) return formatShortDate(start || end);
    return `${formatShortDate(start)} 至 ${formatShortDate(end)}`;
}

function daysInclusive(start, end) {
    const startDate = parseLocalDate(start);
    const endDate = parseLocalDate(end);
    if (!startDate || !endDate || endDate < startDate) return 0;
    return Math.round((endDate - startDate) / 86400000) + 1;
}

function departmentLabel(user = state.user) {
    if (user?.department_name) return user.department_name;
    if (user?.department_id) return `部门 #${user.department_id}`;
    return "未分配部门";
}

function downloadCsv(filename, headers, rows) {
    const csvCell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const csv = [headers, ...rows]
        .map((row) => row.map(csvCell).join(","))
        .join("\r\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

function mountPanel(control, wrap) {
    document.body.appendChild(wrap);
    control._panelWrap = wrap;
}

function positionPanel(wrap, trigger) {
    const rect = trigger.getBoundingClientRect();
    const margin = 8;
    const gap = 6;
    const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
    const viewportHeight = document.documentElement.clientHeight || window.innerHeight;
    const maxPanelHeight = Math.max(120, viewportHeight - margin * 2);
    if (wrap.offsetHeight > maxPanelHeight) {
        wrap.style.maxHeight = `${maxPanelHeight}px`;
        wrap.style.overflowY = "auto";
    }
    const panelHeight = wrap.offsetHeight;
    const panelWidth = wrap.offsetWidth;
    let top = rect.bottom + gap;
    if (top + panelHeight > viewportHeight - margin) {
        const above = rect.top - gap - panelHeight;
        top = above >= margin
            ? above
            : Math.max(margin, viewportHeight - margin - panelHeight);
    }
    let left = rect.left;
    const maxLeft = viewportWidth - margin - panelWidth;
    if (left > maxLeft) left = Math.max(margin, maxLeft);
    if (left < margin) left = margin;
    wrap.style.top = `${Math.round(top)}px`;
    wrap.style.left = `${Math.round(left)}px`;
}

function scrollActiveIntoView(container) {
    const active = container.querySelector(".active");
    if (!active) return;
    const box = container.getBoundingClientRect();
    const item = active.getBoundingClientRect();
    if (item.top < box.top) {
        container.scrollTop -= box.top - item.top + 4;
    } else if (item.bottom > box.bottom) {
        container.scrollTop += item.bottom - box.bottom + 4;
    }
}

function openSelectPanel(select) {
    if (select.dataset.panelOpen === "1") {
        return;
    }
    if (select._panelWrap) {
        closeSelectPanel(select);
    }
    select.dataset.panelOpen = "1";
    const wrap = document.createElement("div");
    wrap.className = "select-pop-wrap";
    const availableWidth = Math.max(120, (document.documentElement.clientWidth || window.innerWidth) - 16);
    wrap.style.minWidth = `${Math.min(Math.max(select.offsetWidth, 180), availableWidth)}px`;
    wrap.innerHTML = `
        <div class="select-pop glass" role="listbox" tabindex="-1"></div>
    `;
    const list = wrap.querySelector(".select-pop");
    list.addEventListener("mousedown", (event) => event.preventDefault());
    Array.from(select.options).forEach((option, index) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "select-pop-item" + (option.selected ? " active" : "");
        item.textContent = option.textContent || option.value;
        item.addEventListener("click", () => {
            select.selectedIndex = index;
            select.dispatchEvent(new Event("change", { bubbles: true }));
            closeSelectPanel(select);
        });
        list.appendChild(item);
    });
    mountPanel(select, wrap);
    positionPanel(wrap, select);
    scrollActiveIntoView(list);
    const dismiss = (event) => {
        if (!wrap.contains(event.target) && event.target !== select) {
            closeSelectPanel(select);
        }
    };
    const onKey = (event) => {
        if (event.key === "Escape") {
            closeSelectPanel(select);
        }
    };
    const abort = new AbortController();
    select._panelAbort = abort;
    document.addEventListener("click", dismiss, { capture: true, signal: abort.signal });
    document.addEventListener("keydown", onKey, { capture: true, signal: abort.signal });
    document.addEventListener("scroll", dismiss, { capture: true, signal: abort.signal });
    window.addEventListener("resize", () => closeSelectPanel(select), { signal: abort.signal });
    list.focus();
}

function closeSelectPanel(select) {
    const wrap = select._panelWrap;
    if (!wrap && select.dataset.panelOpen !== "1") return;
    wrap?.remove();
    select._panelWrap = null;
    select._panelAbort?.abort();
    select._panelAbort = null;
    select.dataset.panelOpen = "0";
}

function closeOpenPanels(scope) {
    (scope || document).querySelectorAll("[data-panel-open='1']").forEach((control) => {
        closeSelectPanel(control);
    });
}

function removeModal(wrap) {
    closeOpenPanels(wrap);
    wrap.remove();
}

function openDatePanel(input) {
    if (input.dataset.panelOpen === "1") {
        return;
    }
    if (input._panelWrap) {
        closeSelectPanel(input);
    }
    input.dataset.panelOpen = "1";
    const wrap = document.createElement("div");
    wrap.className = "select-pop-wrap date-pop-wrap";
    wrap.innerHTML = `
        <div class="select-pop date-pop glass" tabindex="-1">
            <div class="date-pop-header"></div>
            <div class="date-pop-grid"></div>
        </div>
    `;
    const pop = wrap.querySelector(".date-pop");
    const header = wrap.querySelector(".date-pop-header");
    const grid = wrap.querySelector(".date-pop-grid");
    const initialDate = parseLocalDate(input.value) || new Date();
    let viewYear = initialDate.getFullYear();
    let viewMonth = initialDate.getMonth();
    const pick = (iso) => {
        input.value = iso;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        closeSelectPanel(input);
    };
    const onClick = (event) => {
        if (event.target.closest("[data-action='today']")) {
            const today = new Date();
            viewYear = today.getFullYear();
            viewMonth = today.getMonth();
            pick(formatLocalDate(today));
        } else if (event.target.closest("[data-action='prev']")) {
            viewMonth -= 1;
            if (viewMonth < 0) {
                viewMonth = 11;
                viewYear -= 1;
            }
            render();
        } else if (event.target.closest("[data-action='next']")) {
            viewMonth += 1;
            if (viewMonth > 11) {
                viewMonth = 0;
                viewYear += 1;
            }
            render();
        } else {
            const day = event.target.closest("[data-day]");
            if (day) {
                const iso = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(Number(day.dataset.day)).padStart(2, "0")}`;
                pick(iso);
            }
        }
    };
    const render = () => {
        header.innerHTML = `
            <button type="button" class="date-pop-nav" data-action="prev" aria-label="上个月">‹</button>
            <span>${viewYear}年 ${viewMonth + 1}月</span>
            <button type="button" class="date-pop-nav" data-action="next" aria-label="下个月">›</button>
            <button type="button" class="date-pop-today" data-action="today">今天</button>
        `;
        grid.innerHTML = "";
        grid.innerHTML = ["日", "一", "二", "三", "四", "五", "六"]
            .map((day) => `<span class="date-pop-week">${day}</span>`)
            .join("");
        const first = new Date(viewYear, viewMonth, 1);
        const startOffset = first.getDay();
        const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
        for (let i = 0; i < startOffset; i += 1) {
            grid.insertAdjacentHTML("beforeend", '<span class="date-pop-empty"></span>');
        }
        const selectedIso = input.value || "";
        const todayIso = formatLocalDate();
        for (let day = 1; day <= daysInMonth; day += 1) {
            const iso = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
            const classes = ["date-pop-day"];
            if (iso === selectedIso) classes.push("active");
            if (iso === todayIso) classes.push("today");
            grid.insertAdjacentHTML("beforeend", `<button type="button" class="${classes.join(" ")}" data-day="${day}">${day}</button>`);
        }
    };
    render();
    pop.addEventListener("mousedown", (event) => event.preventDefault());
    pop.addEventListener("click", onClick);
    mountPanel(input, wrap);
    positionPanel(wrap, input);
    requestAnimationFrame(() => scrollActiveIntoView(pop));
    const dismiss = (event) => {
        if (!wrap.contains(event.target) && event.target !== input) {
            closeSelectPanel(input);
        }
    };
    const onKey = (event) => {
        if (event.key === "Escape") {
            closeSelectPanel(input);
        }
    };
    const abort = new AbortController();
    input._panelAbort = abort;
    document.addEventListener("click", dismiss, { capture: true, signal: abort.signal });
    document.addEventListener("keydown", onKey, { capture: true, signal: abort.signal });
    document.addEventListener("scroll", dismiss, { capture: true, signal: abort.signal });
    window.addEventListener("resize", () => closeSelectPanel(input), { signal: abort.signal });
}

function openTimePanel(input) {
    if (input.dataset.panelOpen === "1") {
        return;
    }
    if (input._panelWrap) {
        closeSelectPanel(input);
    }
    input.dataset.panelOpen = "1";
    const snapMinute = (value) => Math.min(55, Math.max(0, Math.round(value / 5) * 5));
    const now = new Date();
    let hour = now.getHours();
    let minute = snapMinute(now.getMinutes());
    if (input.value) {
        const [rawHour, rawMinute] = input.value.split(":").map(Number);
        if (
            Number.isInteger(rawHour) &&
            rawHour >= 0 &&
            rawHour <= 23 &&
            Number.isInteger(rawMinute) &&
            rawMinute >= 0 &&
            rawMinute <= 59
        ) {
            hour = rawHour;
            minute = snapMinute(rawMinute);
        }
    }
    const wrap = document.createElement("div");
    wrap.className = "select-pop-wrap time-pop-wrap";
    wrap.innerHTML = `
        <div class="select-pop time-pop glass" tabindex="-1">
            <div class="time-pop-header">
                <button type="button" class="date-pop-today" data-action="now">现在</button>
            </div>
            <div class="time-pop-cols">
                <div class="time-pop-col">
                    <span class="time-pop-label">小时</span>
                    <div class="time-pop-grid" data-part="hours"></div>
                </div>
                <div class="time-pop-col">
                    <span class="time-pop-label">分钟</span>
                    <div class="time-pop-grid" data-part="minutes"></div>
                </div>
            </div>
        </div>
    `;
    const pop = wrap.querySelector(".time-pop");
    const hoursGrid = wrap.querySelector("[data-part='hours']");
    const minutesGrid = wrap.querySelector("[data-part='minutes']");
    const pick = () => {
        const value = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
        input.value = value;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        closeSelectPanel(input);
    };
    const render = () => {
        const selectedHour = String(hour).padStart(2, "0");
        const selectedMinute = String(minute).padStart(2, "0");
        hoursGrid.innerHTML = Array.from({ length: 24 }, (_, i) => {
            const label = String(i).padStart(2, "0");
            const active = label === selectedHour ? " active" : "";
            return `<button type="button" class="time-pop-cell${active}" data-hour="${i}">${label}</button>`;
        }).join("");
        minutesGrid.innerHTML = Array.from({ length: 12 }, (_, i) => {
            const label = String(i * 5).padStart(2, "0");
            const active = label === selectedMinute ? " active" : "";
            return `<button type="button" class="time-pop-cell${active}" data-minute="${i * 5}">${label}</button>`;
        }).join("");
        requestAnimationFrame(() => {
            scrollActiveIntoView(hoursGrid);
            scrollActiveIntoView(minutesGrid);
        });
    };
    const onClick = (event) => {
        const nowBtn = event.target.closest("[data-action='now']");
        if (nowBtn) {
            const today = new Date();
            hour = today.getHours();
            minute = snapMinute(today.getMinutes());
            render();
            return;
        }
        const hourCell = event.target.closest("[data-hour]");
        if (hourCell) {
            hour = Number(hourCell.dataset.hour);
            render();
            return;
        }
        const minuteCell = event.target.closest("[data-minute]");
        if (minuteCell) {
            minute = Number(minuteCell.dataset.minute);
            pick();
        }
    };
    render();
    pop.addEventListener("mousedown", (event) => event.preventDefault());
    pop.addEventListener("click", onClick);
    mountPanel(input, wrap);
    positionPanel(wrap, input);
    const dismiss = (event) => {
        if (!wrap.contains(event.target) && event.target !== input) {
            closeSelectPanel(input);
        }
    };
    const onKey = (event) => {
        if (event.key === "Escape") {
            closeSelectPanel(input);
        }
    };
    const abort = new AbortController();
    input._panelAbort = abort;
    document.addEventListener("click", dismiss, { capture: true, signal: abort.signal });
    document.addEventListener("keydown", onKey, { capture: true, signal: abort.signal });
    document.addEventListener("scroll", dismiss, { capture: true, signal: abort.signal });
    window.addEventListener("resize", () => closeSelectPanel(input), { signal: abort.signal });
}

function setupSelects(scope) {
    (scope || document).querySelectorAll("select").forEach((select) => {
        if (select.dataset.enhanced === "1") return;
        select.dataset.enhanced = "1";
        select.classList.add("enhanced-select");
        select.addEventListener("click", (event) => {
            event.preventDefault();
            openSelectPanel(select);
        });
        select.addEventListener("mousedown", (event) => event.preventDefault());
        select.addEventListener("focus", () => {
            if (!select.value) openSelectPanel(select);
        });
    });
    (scope || document).querySelectorAll("input[type='date']").forEach((input) => {
        if (input.dataset.enhanced === "1") return;
        input.dataset.enhanced = "1";
        input.type = "text";
        input.readOnly = true;
        input.tabIndex = 0;
        input.dataset.kind = "date";
        input.classList.add("enhanced-picker");
        input.placeholder = "选择日期";
        input.addEventListener("click", () => openDatePanel(input));
        input.addEventListener("focus", () => {
            if (!input.value) openDatePanel(input);
        });
    });
    (scope || document).querySelectorAll("input[type='time']").forEach((input) => {
        if (input.dataset.enhanced === "1") return;
        input.dataset.enhanced = "1";
        input.type = "text";
        input.readOnly = true;
        input.tabIndex = 0;
        input.dataset.kind = "time";
        input.classList.add("enhanced-picker");
        input.placeholder = "选择时间";
        input.addEventListener("click", () => openTimePanel(input));
        input.addEventListener("focus", () => {
            if (!input.value) openTimePanel(input);
        });
    });
}

function enhanceFormControls(scope) {
    setupSelects(scope);
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
    closeOpenPanels(document);
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
    content.classList.remove("page-enter");
    // Force reflow so the page-in animation can restart on every navigation.
    void content.offsetWidth;
    content.classList.add("page-enter");
}

function renderMyAttendance(content) {
    const user = state.user || {};
    const department = departmentLabel(user);
    const todayText = formatLocalDate();
    const recentWorkdays = [];
    let cursor = parseLocalDate(todayText);
    while (recentWorkdays.length < 4 && cursor) {
        if (cursor.getDay() !== 0 && cursor.getDay() !== 6) {
            recentWorkdays.push(formatLocalDate(cursor));
        }
        cursor = addLocalDays(cursor, -1);
    }
    const demoRecords = [
        { start: "08:56", end: "18:02", status: "正常", statusClass: "tag-success", hours: "7.9h" },
        { start: "09:04", end: "18:10", status: "迟到", statusClass: "tag-warning", hours: "8.0h" },
        { start: "08:50", end: "18:05", status: "正常", statusClass: "tag-success", hours: "8.1h" },
        { start: "08:58", end: "17:40", status: "早退", statusClass: "tag-warning", hours: "7.6h" },
    ];
    const recordRows = recentWorkdays.map((date, index) => {
        const record = demoRecords[index] || demoRecords[demoRecords.length - 1];
        return `<tr><td>${formatShortDate(date)}</td><td>${record.start}</td><td>${record.end}</td><td><span class="tag ${record.statusClass}">${record.status}</span></td><td>${record.hours}</td></tr>`;
    }).join("");
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
                        ${recordRows || '<tr><td colspan="5" class="table-empty">暂无考勤记录</td></tr>'}
                    </tbody>
                </table>
                <p class="demo-note">个人打卡数据将在 I5 考勤接口完成后实时联调；当前展示界面结构与日期样例。</p>
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

function getDemoRequests() {
    if (state.demoRequests) return state.demoRequests;
    const today = formatLocalDate();
    const dateAfter = (days) => {
        const date = addLocalDays(today, days);
        return date ? formatLocalDate(date) : today;
    };
    state.demoRequests = [
        {
            id: 1,
            applicant: "林悦",
            department_id: 2,
            department: "人事部",
            type: "leave",
            typeLabel: "事假",
            start: dateAfter(-7),
            end: dateAfter(-7),
            duration: 0.5,
            status: "pending",
            reason: "个人事务",
        },
        {
            id: 2,
            applicant: "周航",
            department_id: 1,
            department: "技术部",
            type: "trip",
            typeLabel: "外派",
            start: dateAfter(2),
            end: dateAfter(3),
            duration: 2,
            status: "pending",
            reason: "客户现场支持",
        },
        {
            id: 3,
            applicant: "陈晓",
            department_id: 1,
            department: "技术部",
            type: "leave",
            typeLabel: "年假",
            start: dateAfter(-1),
            end: dateAfter(-1),
            duration: 1,
            status: "approved",
            reason: "调休",
        },
    ];
    return state.demoRequests;
}

function renderDashboard(content) {
    const isAdmin = state.user?.role === "general_admin";
    const scopeLabel = isAdmin ? "全公司" : departmentLabel();
    const todayCount = isAdmin ? 86 : 42;
    const punchedCount = isAdmin ? 74 : 37;
    const requests = getDemoRequests().filter(
        (request) => isAdmin || request.department_id === state.user?.department_id
    );
    const pendingRequests = requests.filter((request) => request.status === "pending");
    const pendingCount = pendingRequests.length;
    const pendingLeaveCount = pendingRequests.filter((request) => request.type === "leave").length;
    const pendingTripCount = pendingRequests.filter((request) => request.type === "trip").length;
    const pendingText = pendingCount
        ? `请假 ${pendingLeaveCount} · 外派 ${pendingTripCount}`
        : "暂无待处理申请";
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
    const approvalRows = pendingRequests.length
        ? pendingRequests.slice(0, 3).map((request) => `
                    <div class="timeline-item">
                        <strong>${escapeHtml(request.applicant)} · ${escapeHtml(request.typeLabel)}</strong>
                        <span>${escapeHtml(formatDateRange(request.start, request.end))} · ${request.duration} 天 · 待审批</span>
                    </div>`).join("")
        : `
                    <div class="timeline-item">
                        <strong>暂无待处理审批</strong>
                        <span>新的请假或外派申请会显示在这里</span>
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
    invalidateDepartments();
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
            removeModal(wrap);
        }
    });
    enhanceFormControls(wrap);
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
            removeModal(wrap);
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
    invalidateDepartments();
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
            removeModal(wrap);
        }
    });
    enhanceFormControls(wrap);
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
            removeModal(wrap);
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
            removeModal(wrap);
        }
    });
    enhanceFormControls(wrap);
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
            removeModal(wrap);
            renderDepartments($("#page-content"));
        } catch (err) {
            toast(err.message);
        }
    });
    document.body.appendChild(wrap);
}

async function ensureDepartments() {
    if (state.departments.length) return state.departments;
    state.departments = await apiFetch("/departments");
    return state.departments;
}

function invalidateDepartments() {
    state.departments = [];
}

function visibleDepartments() {
    const departments = state.departments;
    if (state.user?.role === "general_admin") return departments;
    return departments.filter((department) => department.id === state.user?.department_id);
}

function renderAttendanceRows(content) {
    const tbody = content.querySelector("#attendance-table-body");
    const summary = content.querySelector("#attendance-summary");
    if (!tbody) return;
    const date = state.attendanceFilters.date;
    const departments = visibleDepartments().filter((department) => {
        return state.attendanceFilters.departmentId === "all"
            || department.id === Number(state.attendanceFilters.departmentId);
    });
    const seedBase = Number(String(date).replaceAll("-", "")) || 0;
    const rows = departments.map((department, index) => {
        const expected = department.employee_count || 0;
        const seed = (seedBase + department.id * 37 + index * 11) % 17;
        const absent = expected ? Math.min(expected, seed % 3 === 0 ? 2 : 1) : 0;
        const punched = Math.max(0, expected - absent);
        const late = Math.min(punched, seed % 4);
        const early = Math.min(Math.max(0, punched - late), (seed + 1) % 3);
        return `
            <tr>
                <td>${escapeHtml(department.name)}</td>
                <td>${expected}</td>
                <td>${punched}</td>
                <td>${late}</td>
                <td>${early}</td>
                <td>${absent}</td>
            </tr>
        `;
    });
    tbody.innerHTML = rows.length
        ? rows.join("")
        : '<tr><td colspan="6" class="table-empty">当前筛选条件下暂无考勤数据</td></tr>';
    const totals = departments.reduce(
        (acc, department) => {
            const expected = department.employee_count || 0;
            acc.expected += expected;
            return acc;
        },
        { expected: 0 }
    );
    const punchedTotal = Array.from(tbody.querySelectorAll("tr"))
        .filter((row) => row.children.length === 6)
        .reduce((total, row) => total + Number(row.children[2]?.textContent || 0), 0);
    if (summary) {
        summary.textContent = `共 ${departments.length} 个部门 · 应到 ${totals.expected} 人 · 已打卡 ${punchedTotal} 人`;
    }
}

async function loadAttendancePage(content) {
    const tbody = content.querySelector("#attendance-table-body");
    const select = content.querySelector("#attendance-dept-filter");
    try {
        await ensureDepartments();
        if (state.page !== "attendance") return;
        const departments = visibleDepartments();
        if (state.user?.role !== "general_admin" && departments.length === 1) {
            state.attendanceFilters.departmentId = String(departments[0].id);
        }
        if (select) {
            const options = departments.map(
                (department) => `<option value="${department.id}">${escapeHtml(department.name)}</option>`
            ).join("");
            select.innerHTML = state.user?.role === "general_admin"
                ? `<option value="all">全部部门</option>${options}`
                : options || '<option value="">暂无部门</option>';
            select.value = state.attendanceFilters.departmentId;
        }
        renderAttendanceRows(content);
    } catch (err) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" class="table-empty">${escapeHtml(err.message)}</td></tr>`;
        }
    }
}

function renderAttendance(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "按日期与部门汇总打卡状态" : "仅本部门考勤";
    if (!state.attendanceFilters.date) {
        state.attendanceFilters.date = formatLocalDate();
    }
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>考勤中心</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <span class="status-pill" id="attendance-date-pill">${formatDateWithWeekday(state.attendanceFilters.date)}</span>
            </div>
            <div class="filter-toolbar">
                <label class="form-field filter-field">
                    <span>考勤日期</span>
                    <input id="attendance-date-filter" type="date" value="${escapeAttr(state.attendanceFilters.date)}">
                </label>
                <label class="form-field filter-field">
                    <span>部门范围</span>
                    <select id="attendance-dept-filter">
                        <option value="all">全部部门</option>
                    </select>
                </label>
                <button class="btn btn-ghost" id="reset-attendance-filters" type="button">重置筛选</button>
                <button class="btn btn-ghost" id="refresh-attendance" type="button">刷新</button>
            </div>
            <div class="filter-summary" id="attendance-summary">正在加载部门数据...</div>
            <table class="data-table">
                <thead><tr><th>部门</th><th>应到</th><th>已打卡</th><th>迟到</th><th>早退</th><th>缺勤</th></tr></thead>
                <tbody id="attendance-table-body">
                    <tr><td colspan="6" class="table-loading">正在加载考勤数据...</td></tr>
                </tbody>
            </table>
            <p class="demo-note">考勤汇总将在 I5 考勤接口完成后接入真实数据；当前筛选与汇总基于演示数据生成。</p>
        </section>
    `;
    enhanceFormControls(content);
    const dateInput = content.querySelector("#attendance-date-filter");
    const departmentSelect = content.querySelector("#attendance-dept-filter");
    dateInput.addEventListener("change", () => {
        state.attendanceFilters.date = dateInput.value || formatLocalDate();
        const pill = content.querySelector("#attendance-date-pill");
        if (pill) pill.textContent = formatDateWithWeekday(state.attendanceFilters.date);
        renderAttendanceRows(content);
    });
    departmentSelect.addEventListener("change", () => {
        state.attendanceFilters.departmentId = departmentSelect.value || "all";
        renderAttendanceRows(content);
    });
    content.querySelector("#reset-attendance-filters").addEventListener("click", () => {
        state.attendanceFilters.date = formatLocalDate();
        state.attendanceFilters.departmentId = isAdmin ? "all" : String(state.user?.department_id || "");
        renderAttendance(content);
    });
    content.querySelector("#refresh-attendance").addEventListener("click", () => {
        renderAttendance(content);
        toast("考勤数据已刷新");
    });
    loadAttendancePage(content);
}

function scopedRequests() {
    const requests = getDemoRequests();
    if (state.user?.role === "general_admin") return requests;
    return requests.filter((request) => request.department_id === state.user?.department_id);
}

function requestStatusMeta(status) {
    const map = {
        pending: { label: "待审批", className: "tag-violet" },
        approved: { label: "已通过", className: "tag-success" },
        rejected: { label: "已驳回", className: "tag-danger" },
    };
    return map[status] || { label: status || "未知", className: "tag-cyan" };
}

function renderRequestRows(content) {
    const tbody = content.querySelector("#request-table-body");
    const summary = content.querySelector("#request-summary");
    if (!tbody) return;
    const requests = scopedRequests();
    const visible = requests.filter((request) => {
        const typeMatched = state.requestFilters.type === "all"
            || request.type === state.requestFilters.type;
        const statusMatched = state.requestFilters.status === "all"
            || request.status === state.requestFilters.status;
        return typeMatched && statusMatched;
    });
    const rows = visible.map((request) => {
        const status = requestStatusMeta(request.status);
        const permission = request.type === "leave"
            ? "leave.review.department"
            : "trip.review.department";
        const actions = request.status === "pending" && hasPermission(permission)
            ? `
                <div class="row-actions">
                    <button class="btn btn-ghost btn-sm" data-request-id="${request.id}" data-action="approve">通过</button>
                    <button class="btn btn-ghost btn-sm btn-danger" data-request-id="${request.id}" data-action="reject">驳回</button>
                </div>
            `
            : '<span class="table-muted">—</span>';
        return `
            <tr>
                <td>${escapeHtml(request.applicant)}</td>
                <td>${escapeHtml(request.department || "未分配")}</td>
                <td><span class="tag ${request.type === "trip" ? "tag-cyan" : "tag-warning"}">${escapeHtml(request.typeLabel)}</span></td>
                <td>${escapeHtml(formatDateRange(request.start, request.end))}</td>
                <td>${Number(request.duration).toFixed(1)} 天</td>
                <td><span class="tag ${status.className}">${status.label}</span></td>
                <td>${actions}</td>
            </tr>
        `;
    });
    tbody.innerHTML = rows.length
        ? rows.join("")
        : '<tr><td colspan="7" class="table-empty">当前筛选条件下暂无申请单</td></tr>';
    if (summary) {
        summary.textContent = `显示 ${visible.length} 条，共 ${requests.length} 条申请`;
    }
    tbody.querySelectorAll("[data-request-id]").forEach((button) => {
        button.addEventListener("click", () => {
            const request = getDemoRequests().find(
                (item) => item.id === Number(button.dataset.requestId)
            );
            if (!request) return;
            request.status = button.dataset.action === "approve" ? "approved" : "rejected";
            renderRequestRows(content);
            toast(button.dataset.action === "approve" ? "申请已通过" : "申请已驳回");
        });
    });
}

function renderRequests(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "请假与外派申请单" : "仅本部门请假与外派申请单";
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>审批中心</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <div class="panel-actions">
                    <button class="btn btn-ghost" id="new-leave-request" type="button">请假</button>
                    <button class="btn btn-ghost" id="new-trip-request" type="button">外派</button>
                </div>
            </div>
            <div class="filter-toolbar">
                <label class="form-field filter-field">
                    <span>申请类型</span>
                    <select id="request-type-filter">
                        <option value="all">全部类型</option>
                        <option value="leave">请假</option>
                        <option value="trip">外派</option>
                    </select>
                </label>
                <label class="form-field filter-field">
                    <span>审批状态</span>
                    <select id="request-status-filter">
                        <option value="all">全部状态</option>
                        <option value="pending">待审批</option>
                        <option value="approved">已通过</option>
                        <option value="rejected">已驳回</option>
                    </select>
                </label>
                <button class="btn btn-ghost" id="reset-request-filters" type="button">重置筛选</button>
            </div>
            <div class="filter-summary" id="request-summary"></div>
            <table class="data-table">
                <thead><tr><th>申请人</th><th>部门</th><th>类型</th><th>日期</th><th>时长</th><th>状态</th><th>操作</th></tr></thead>
                <tbody id="request-table-body">
                    <tr><td colspan="7" class="table-loading">正在加载申请单...</td></tr>
                </tbody>
            </table>
            <p class="demo-note">申请单当前保存在前端演示状态中，I5 接口完成后将切换为后端审批流。</p>
        </section>
    `;
    const typeFilter = content.querySelector("#request-type-filter");
    const statusFilter = content.querySelector("#request-status-filter");
    typeFilter.value = state.requestFilters.type;
    statusFilter.value = state.requestFilters.status;
    enhanceFormControls(content);
    typeFilter.addEventListener("change", () => {
        state.requestFilters.type = typeFilter.value || "all";
        renderRequestRows(content);
    });
    statusFilter.addEventListener("change", () => {
        state.requestFilters.status = statusFilter.value || "all";
        renderRequestRows(content);
    });
    content.querySelector("#reset-request-filters").addEventListener("click", () => {
        state.requestFilters.type = "all";
        state.requestFilters.status = "all";
        renderRequests(content);
    });
    content.querySelector("#new-leave-request").addEventListener("click", () => openRequestForm("leave"));
    content.querySelector("#new-trip-request").addEventListener("click", () => openRequestForm("trip"));
    renderRequestRows(content);
}

function openRequestForm(type) {
    const isLeave = type === "leave";
    const today = formatLocalDate();
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `
        <div class="modal-panel glass" role="dialog" aria-modal="true" aria-label="${isLeave ? "新建请假申请" : "新建外派申请"}">
            <div class="modal-header">
                <div>
                    <p class="drawer-kicker">${isLeave ? "LEAVE REQUEST" : "BUSINESS TRIP"}</p>
                    <h3>${isLeave ? "新建请假申请" : "新建外派申请"}</h3>
                </div>
                <button class="icon-btn modal-close" title="关闭" aria-label="关闭">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <form class="form-grid" data-request-type="${type}">
                ${isLeave ? `
                    <label class="form-field">
                        <span>请假类型</span>
                        <select name="leave_type">
                            <option value="事假">事假</option>
                            <option value="年假">年假</option>
                            <option value="病假">病假</option>
                        </select>
                    </label>
                    <label class="form-field">
                        <span>请假时段</span>
                        <select name="leave_part">
                            <option value="full">全天</option>
                            <option value="half">半天</option>
                        </select>
                    </label>
                ` : `
                    <label class="form-field form-field-wide">
                        <span>外派地点</span>
                        <input name="destination" required maxlength="100" placeholder="请输入外派地点">
                    </label>
                `}
                <label class="form-field">
                    <span>开始日期</span>
                    <input name="start" type="date" value="${today}" required>
                </label>
                <label class="form-field">
                    <span>结束日期</span>
                    <input name="end" type="date" value="${today}" required>
                </label>
                <label class="form-field form-field-wide">
                    <span>申请说明</span>
                    <textarea name="reason" rows="3" maxlength="300" required placeholder="请填写申请原因或工作安排"></textarea>
                </label>
                <div class="form-actions form-field-wide">
                    <button type="button" class="btn btn-ghost" data-action="cancel">取消</button>
                    <button type="submit" class="btn btn-primary">提交申请</button>
                </div>
            </form>
        </div>
    `;
    wrap.addEventListener("click", (event) => {
        if (event.target === wrap || event.target.closest("[data-action='cancel'], .modal-close")) {
            removeModal(wrap);
        }
    });
    enhanceFormControls(wrap);
    wrap.querySelector("form").addEventListener("submit", (event) => {
        event.preventDefault();
        const formData = new FormData(event.currentTarget);
        const start = formData.get("start");
        const end = formData.get("end");
        const days = daysInclusive(start, end);
        if (!days) {
            toast("结束日期不能早于开始日期");
            return;
        }
        const isHalfDay = isLeave && formData.get("leave_part") === "half";
        if (isHalfDay && days !== 1) {
            toast("半天请假只能选择同一天");
            return;
        }
        const typeLabel = isLeave ? String(formData.get("leave_type") || "事假") : "外派";
        const requests = getDemoRequests();
        const nextId = requests.reduce((max, request) => Math.max(max, request.id), 0) + 1;
        requests.unshift({
            id: nextId,
            applicant: state.user?.name || "当前账号",
            department_id: state.user?.department_id ?? null,
            department: departmentLabel(),
            type,
            typeLabel,
            start,
            end,
            duration: isHalfDay ? 0.5 : days,
            status: "pending",
            reason: String(formData.get("reason") || ""),
            destination: String(formData.get("destination") || ""),
        });
        removeModal(wrap);
        renderRequests($("#page-content"));
        toast(isLeave ? "请假申请已提交" : "外派申请已提交");
    });
    document.body.appendChild(wrap);
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
    invalidateDepartments();
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
            removeModal(wrap);
        }
    });
    enhanceFormControls(wrap);
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
            removeModal(wrap);
            renderShifts($("#page-content"));
        } catch (err) {
            toast(err.message);
        }
    });
    document.body.appendChild(wrap);
}

function reportMonthOptions() {
    const now = new Date();
    return Array.from({ length: 12 }, (_, index) => {
        const date = new Date(now.getFullYear(), now.getMonth() - index, 1);
        const value = formatMonthValue(date);
        return `<option value="${value}">${formatMonthLabel(value)}</option>`;
    }).join("");
}

function currentReportRows() {
    const month = state.reportFilters.month || formatMonthValue();
    const seedBase = Number(month.replace("-", "")) || 0;
    const departments = visibleDepartments().filter((department) => {
        return state.reportFilters.departmentId === "all"
            || department.id === Number(state.reportFilters.departmentId);
    });
    return departments.map((department, index) => {
        const seed = (seedBase + department.id * 11 + index * 7) % 23;
        return {
            department: department.name,
            attendanceRate: Math.min(99.2, 89.4 + (seed % 9) + ((seed * 3) % 10) / 10),
            averageHours: 7.3 + (seed % 7) / 10,
            leaveDays: Number((((seed * 5) % 32) / 2).toFixed(1)),
            tripDays: Number((((seed * 3) % 13) / 2).toFixed(1)),
        };
    });
}

function renderReportRows(content) {
    const tbody = content.querySelector("#report-table-body");
    const summary = content.querySelector("#report-summary");
    if (!tbody) return;
    const rows = currentReportRows();
    tbody.innerHTML = rows.length
        ? rows.map((row) => `
            <tr>
                <td>${escapeHtml(row.department)}</td>
                <td>${row.attendanceRate.toFixed(1)}%</td>
                <td>${row.averageHours.toFixed(1)}h</td>
                <td>${row.leaveDays.toFixed(1)}</td>
                <td>${row.tripDays.toFixed(1)}</td>
            </tr>
        `).join("")
        : '<tr><td colspan="5" class="table-empty">当前筛选条件下暂无报表数据</td></tr>';
    if (summary) {
        summary.textContent = `${formatMonthLabel(state.reportFilters.month)} · 共 ${rows.length} 个部门`;
    }
}

async function loadReportsPage(content) {
    const scopeSelect = content.querySelector("#report-scope-filter");
    const tbody = content.querySelector("#report-table-body");
    try {
        await ensureDepartments();
        if (state.page !== "reports") return;
        const departments = visibleDepartments();
        if (state.user?.role !== "general_admin" && departments.length === 1) {
            state.reportFilters.departmentId = String(departments[0].id);
        }
        if (scopeSelect) {
            const options = departments.map(
                (department) => `<option value="${department.id}">${escapeHtml(department.name)}</option>`
            ).join("");
            scopeSelect.innerHTML = state.user?.role === "general_admin"
                ? `<option value="all">全公司</option>${options}`
                : options || '<option value="">暂无部门</option>';
            scopeSelect.value = state.reportFilters.departmentId;
        }
        renderReportRows(content);
    } catch (err) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="table-empty">${escapeHtml(err.message)}</td></tr>`;
        }
    }
}

function renderReports(content) {
    const isAdmin = state.user?.role === "general_admin";
    const panelSub = isAdmin ? "工时、出勤率与请假分布" : "仅本部门月度报表";
    if (!state.reportFilters.month) {
        state.reportFilters.month = formatMonthValue();
    }
    content.innerHTML = `
        <section class="panel">
            <div class="panel-header">
                <div>
                    <h3>月度报表</h3>
                    <p class="panel-sub">${panelSub}</p>
                </div>
                <div class="panel-actions">
                    <button class="btn btn-ghost" id="export-report" type="button">导出 CSV</button>
                    <button class="btn btn-ghost" id="refresh-report" type="button">刷新</button>
                </div>
            </div>
            <div class="filter-toolbar">
                <label class="form-field filter-field">
                    <span>统计月份</span>
                    <select id="report-month-filter">${reportMonthOptions()}</select>
                </label>
                ${isAdmin ? `
                    <label class="form-field filter-field">
                        <span>统计范围</span>
                        <select id="report-scope-filter">
                            <option value="all">全公司</option>
                        </select>
                    </label>
                ` : `
                    <div class="filter-field">
                        <span>统计范围</span>
                        <div class="filter-static">${escapeHtml(departmentLabel())}</div>
                    </div>
                `}
                <button class="btn btn-ghost" id="reset-report-filters" type="button">重置筛选</button>
            </div>
            <div class="filter-summary" id="report-summary">正在加载报表数据...</div>
            <table class="data-table">
                <thead><tr><th>部门</th><th>出勤率</th><th>平均工时</th><th>请假天数</th><th>外派天数</th></tr></thead>
                <tbody id="report-table-body">
                    <tr><td colspan="5" class="table-loading">正在加载报表数据...</td></tr>
                </tbody>
            </table>
            <p class="demo-note">报表聚合将在 I5 接口完成后切换为后端统计；当前导出使用页面中的演示数据。</p>
        </section>
    `;
    const monthSelect = content.querySelector("#report-month-filter");
    monthSelect.value = state.reportFilters.month;
    enhanceFormControls(content);
    monthSelect.addEventListener("change", () => {
        state.reportFilters.month = monthSelect.value || formatMonthValue();
        renderReportRows(content);
    });
    const scopeSelect = content.querySelector("#report-scope-filter");
    scopeSelect?.addEventListener("change", () => {
        state.reportFilters.departmentId = scopeSelect.value || "all";
        renderReportRows(content);
    });
    content.querySelector("#reset-report-filters").addEventListener("click", () => {
        state.reportFilters.month = formatMonthValue();
        state.reportFilters.departmentId = isAdmin ? "all" : String(state.user?.department_id || "");
        renderReports(content);
    });
    content.querySelector("#refresh-report").addEventListener("click", () => {
        renderReports(content);
        toast("报表数据已刷新");
    });
    content.querySelector("#export-report").addEventListener("click", () => {
        const rows = currentReportRows();
        if (!rows.length) {
            toast("当前筛选条件下没有可导出的数据");
            return;
        }
        downloadCsv(
            `考勤报表_${state.reportFilters.month}.csv`,
            ["部门", "出勤率", "平均工时", "请假天数", "外派天数"],
            rows.map((row) => [
                row.department,
                `${row.attendanceRate.toFixed(1)}%`,
                `${row.averageHours.toFixed(1)}h`,
                row.leaveDays.toFixed(1),
                row.tripDays.toFixed(1),
            ])
        );
        toast("报表已导出为 CSV");
    });
    loadReportsPage(content);
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
        department_name: profile.department_name,
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
