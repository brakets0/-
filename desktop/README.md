# 员工考勤系统 · 桌面端（wxPython）

员工人脸考勤客户端：登录 → 人脸注册（部门管理员/总管理员代操作）→ 人脸签到/签退。

人脸识别与比对全部由后端调用**百度云人脸识别 REST API** 完成，桌面端只负责
摄像头抓帧、压缩编码和 HTTP 调用，不实现也不依赖本地人脸识别算法。

## 依赖

使用系统 Python（已含 OpenCV）安装依赖：

```powershell
cd D:\employee_attendance
python -m pip install -r desktop\requirements.txt
```

- `wxPython`：桌面界面
- `opencv-python`：摄像头抓帧与 JPEG 编码（不做识别）
- `requests`：调用后端
- `Pillow`：抓帧转 wx 位图

## 启动

先启动后端（默认 `http://127.0.0.1:8000`），再运行：

```powershell
cd D:\employee_attendance\desktop
python main.py
```

演示账号：`employee / employee123`。若需要给员工注册人脸，请用
`manager / manager123`（本部门）或 `admin / admin123`（任意员工）登录后操作，
员工本人只有查询与打卡权限。

## 自检（无需摄像头）

```powershell
cd D:\employee_attendance
python desktop\scripts\build_check.py
```

会启动界面、用演示账号登录并截图到 `desktop/scripts/_screenshots/`，
用于确认界面与登录链路可渲染；`desktop/scripts/_screenshots/` 不入库。

## 人脸打卡流程

1. 部门管理员/总管理员为员工采集并注册人脸，后端调用百度
   `faceset/user/add` 把人脸写入人脸库（`user_id` = 工号）。
2. 员工登录桌面端，点「人脸签到」/「人脸签退」，桌面端抓帧后调用
   `/api/face/attendance`。
3. 后端调用百度 `face/v3/search` 在人脸库中检索该工号，相似度达到阈值
   （默认 80）后才写入考勤记录。

## 常见问题

- 提示「人脸服务调用过于频繁」：百度控制台的人脸接口 QPS 配额已耗尽或未开通，
  需要在百度智能云「人脸识别」应用中确认接口已开通并领取免费额度。
- 提示「未检测到可用摄像头」：确认摄像头未被其他程序占用，或更换 `CameraCapture(index=...)`。
