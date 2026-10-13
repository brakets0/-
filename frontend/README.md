# 员工考勤系统前端（Vue 3）

## 开发

```powershell
cd D:\employee_attendance\frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

开发模式下请求由 Vite 代理到 `http://127.0.0.1:8000` 的 FastAPI 后端，需先启动后端。

## 构建

```powershell
npm run build        # 产物输出到 dist/
npm run preview      # 本地预览构建产物
```

## 目录

- `src/api/`：HTTP 客户端与会话存储
- `src/stores/`：Pinia 状态
- `src/router/`：路由与权限守卫
- `src/layouts/`：应用外壳
- `src/views/`：页面
- `src/styles/`：设计系统样式与 Element Plus 主题覆盖
