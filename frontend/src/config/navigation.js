export const ROLE_LABELS = {
    employee: "普通员工",
    department_manager: "部门管理员",
    general_admin: "总管理员",
};

export const NAV_ITEMS = [
    {
        name: "my-attendance",
        label: "我的考勤",
        permission: "attendance.view.self",
        icon: "attendance",
        hiddenForRoles: ["general_admin"],
    },
    {
        name: "dashboard",
        label: "工作台",
        permission: null,
        icon: "dashboard",
        hiddenForRoles: ["employee"],
    },
    {
        name: "attendance",
        label: "考勤中心",
        permission: "attendance.view.department",
        icon: "attendance",
    },
    {
        name: "requests",
        label: "审批中心",
        permission: "leave.apply",
        icon: "requests",
    },
    {
        name: "employees",
        label: "员工管理",
        permission: "employee.manage.department",
        icon: "employees",
    },
    {
        name: "departments",
        label: "部门管理",
        permission: "department.manage",
        icon: "departments",
    },
    {
        name: "shifts",
        label: "班次管理",
        permission: "shift.manage.department",
        icon: "shifts",
    },
    {
        name: "reports",
        label: "报表中心",
        permission: "report.view.department",
        icon: "reports",
    },
];

export const PAGE_TITLES = {
    dashboard: "工作台",
    "my-attendance": "我的考勤",
    employees: "员工管理",
    departments: "部门管理",
    attendance: "考勤中心",
    shifts: "班次管理",
    requests: "审批中心",
    reports: "报表中心",
};

export function defaultRouteName(role) {
    return role === "employee" || role === "department_manager"
        ? "my-attendance"
        : "dashboard";
}
