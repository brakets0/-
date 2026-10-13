import { createRouter, createWebHistory } from "vue-router";

import { defaultRouteName } from "@/config/navigation";
import AppLayout from "@/layouts/AppLayout.vue";
import { useAuthStore } from "@/stores/auth";
import ApprovalView from "@/views/ApprovalView.vue";
import AttendanceView from "@/views/AttendanceView.vue";
import DashboardView from "@/views/DashboardView.vue";
import DepartmentsView from "@/views/DepartmentsView.vue";
import EmployeesView from "@/views/EmployeesView.vue";
import LoginView from "@/views/LoginView.vue";
import MyAttendanceView from "@/views/MyAttendanceView.vue";
import ReportsView from "@/views/ReportsView.vue";
import ShiftsView from "@/views/ShiftsView.vue";

const routes = [
    {
        path: "/login",
        name: "login",
        component: LoginView,
        meta: { public: true, title: "账号登录" },
    },
    {
        path: "/",
        component: AppLayout,
        redirect: () => ({ name: defaultRouteName(useAuthStore().role) }),
        children: [
            {
                path: "my-attendance",
                name: "my-attendance",
                component: MyAttendanceView,
                meta: { title: "我的考勤", permission: "attendance.view.self" },
            },
            {
                path: "dashboard",
                name: "dashboard",
                component: DashboardView,
                meta: { title: "工作台" },
            },
            {
                path: "attendance",
                name: "attendance",
                component: AttendanceView,
                meta: { title: "考勤中心", permission: "attendance.view.department" },
            },
            {
                path: "requests",
                name: "requests",
                component: ApprovalView,
                meta: { title: "审批中心", permission: "leave.apply" },
            },
            {
                path: "employees",
                name: "employees",
                component: EmployeesView,
                meta: { title: "员工管理", permission: "employee.manage.department" },
            },
            {
                path: "departments",
                name: "departments",
                component: DepartmentsView,
                meta: { title: "部门管理", permission: "department.manage" },
            },
            {
                path: "shifts",
                name: "shifts",
                component: ShiftsView,
                meta: { title: "班次管理", permission: "shift.manage.department" },
            },
            {
                path: "reports",
                name: "reports",
                component: ReportsView,
                meta: { title: "报表中心", permission: "report.view.department" },
            },
        ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to) => {
    const auth = useAuthStore();

    if (to.meta.public) {
        if (auth.isAuthenticated && to.name === "login") {
            return { name: defaultRouteName(auth.role) };
        }
        return true;
    }

    if (!auth.isAuthenticated) {
        return {
            name: "login",
            query: to.fullPath === "/" ? {} : { redirect: to.fullPath },
        };
    }

    if (!auth.profileLoaded) {
        const loaded = await auth.loadProfile();
        if (!loaded) return { name: "login" };
    }

    if (auth.role === "employee" && to.name === "dashboard") {
        return { name: "my-attendance" };
    }
    if (auth.role === "general_admin" && to.name === "my-attendance") {
        return { name: "dashboard" };
    }
    if (to.meta.permission && !auth.hasPermission(to.meta.permission)) {
        return { name: defaultRouteName(auth.role) };
    }

    return true;
});

router.afterEach((to) => {
    document.title = to.meta.title
        ? `${to.meta.title} | 员工考勤系统`
        : "员工考勤系统 | Employee Attendance";
});

export default router;
