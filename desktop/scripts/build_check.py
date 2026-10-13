"""桌面端自检：启动 wx 界面，登录并截图登录页与主界面。

前置条件：后端已启动、演示库已初始化。运行后生成：
    desktop/scripts/_screenshots/login.png
    desktop/scripts/_screenshots/main.png
"""

import sys
from pathlib import Path

import wx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api_client import AttendanceApi  # noqa: E402
from main import LoginPanel, MainFrame, MainPanel  # noqa: E402


SHOT_DIR = ROOT / "scripts" / "_screenshots"
ERRORS: list[str] = []


def current_panel(frame: MainFrame):
    for child in frame.GetChildren():
        if isinstance(child, (LoginPanel, MainPanel)):
            return child
    return None


def shoot(frame: MainFrame, name: str) -> None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    width, height = frame.GetClientSize()
    bitmap = wx.Bitmap(width, height)
    memory = wx.MemoryDC(bitmap)
    try:
        origin = frame.ClientToScreen(wx.Point(0, 0))
        memory.Blit(0, 0, width, height, wx.ScreenDC(), origin.x, origin.y)
    finally:
        memory.SelectObject(wx.NullBitmap)
    if not bitmap.SaveFile(str(SHOT_DIR / name), wx.BITMAP_TYPE_PNG):
        ERRORS.append(f"截图保存失败：{name}")


def run() -> int:
    app = wx.App(False)
    frame = MainFrame(AttendanceApi())
    frame.Show()
    app.SetTopWindow(frame)

    def finish():
        app.ExitMainLoop()

    def check_main():
        panel = current_panel(frame)
        if not isinstance(panel, MainPanel):
            ERRORS.append(f"登录后未进入主界面，当前面板：{type(panel).__name__}")
            finish()
            return
        shoot(frame, "main.png")
        print("main status:", panel.status_label.GetLabel())
        panel.camera.close()
        finish()

    def do_login():
        panel = current_panel(frame)
        if not isinstance(panel, LoginPanel):
            ERRORS.append("未找到登录面板")
            finish()
            return
        panel.username.SetValue("employee")
        panel.password.SetValue("employee123")
        panel._on_login(None)
        wx.CallLater(1500, check_main)

    def capture_login():
        panel = current_panel(frame)
        if isinstance(panel, LoginPanel):
            shoot(frame, "login.png")
        else:
            ERRORS.append("启动后未显示登录面板")
        wx.CallLater(300, do_login)

    def on_ready(_frame):
        # 等首帧绘制完成再截图，避免自绘控件还是空白
        wx.CallLater(700, capture_login)

    frame.on_ready = on_ready
    wx.CallAfter(on_ready, frame)
    app.MainLoop()

    if ERRORS:
        print("FAIL:\n" + "\n".join(ERRORS))
        return 1
    print(f"OK: 桌面端渲染正常，截图位于 {SHOT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
