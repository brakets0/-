"""员工人脸考勤桌面端（wxPython）。

登录 → 人脸注册（部门管理员/总管理员代操作）→ 人脸签到/签退。
摄像头只做抓帧与上传，人脸识别与比对全部由后端调用百度云完成。
"""

import sys
import base64

import wx

from api_client import ApiError, AttendanceApi
from camera import CameraCapture, CameraError


APP_TITLE = "员工考勤系统 · 桌面端"
BG = wx.Colour(9, 12, 22)
PANEL = wx.Colour(20, 25, 42)
TEXT = wx.Colour(238, 244, 255)
MUTED = wx.Colour(139, 148, 171)
CYAN = wx.Colour(69, 230, 255)
VIOLET = wx.Colour(138, 124, 255)


def make_font(size: int, *, bold: bool = False) -> wx.Font:
    font = wx.Font(
        size,
        wx.FONTFAMILY_DEFAULT,
        wx.FONTSTYLE_NORMAL,
        wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL,
    )
    font.SetFaceName("Microsoft YaHei UI")
    return font


def button(parent, label, *, primary=False):
    btn = wx.Button(parent, label=label, style=wx.BORDER_NONE)
    btn.SetMinSize((-1, 42))
    btn.SetBackgroundColour(CYAN if primary else wx.Colour(38, 46, 70))
    btn.SetForegroundColour(wx.Colour(8, 12, 20) if primary else TEXT)
    btn.SetFont(make_font(11, bold=True))
    return btn


class PreviewPanel(wx.Panel):
    """摄像头预览：静态图显示，未取到画面时显示提示文字。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundColour(wx.Colour(20, 26, 43))
        self.SetMinSize((420, 320))
        self._bitmap: wx.Bitmap | None = None
        self._hint = "摄像头预览"
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, lambda _e: self.Refresh())

    def set_hint(self, text: str):
        self._bitmap = None
        self._hint = text
        self.Refresh()

    def set_data_url(self, data_url: str):
        try:
            raw = base64.b64decode(data_url.split(",", 1)[1])
            stream = wx.MemoryInputStream(raw)
            image = wx.Image(stream, wx.BITMAP_TYPE_JPEG)
        except Exception:
            return
        self._bitmap = image.ConvertToBitmap()
        self.Refresh()

    def _on_paint(self, _event):
        dc = wx.PaintDC(self)
        width, height = self.GetClientSize()
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()
        if self._bitmap and self._bitmap.IsOk():
            bitmap = self._bitmap
            scale = min(width / bitmap.GetWidth(), height / bitmap.GetHeight())
            new_w = max(1, int(bitmap.GetWidth() * scale))
            new_h = max(1, int(bitmap.GetHeight() * scale))
            image = bitmap.ConvertToImage().Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
            dc.DrawBitmap(image.ConvertToBitmap(), (width - new_w) // 2, (height - new_h) // 2)
            return
        dc.SetTextForeground(MUTED)
        dc.SetFont(make_font(11))
        text_w, text_h = dc.GetTextExtent(self._hint)
        dc.DrawText(self._hint, (width - text_w) // 2, (height - text_h) // 2)


class LoginPanel(wx.Panel):
    def __init__(self, parent, api: AttendanceApi, on_success):
        super().__init__(parent)
        self.api = api
        self.on_success = on_success
        self.SetBackgroundColour(BG)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.AddStretchSpacer(1)

        card = wx.Panel(self, style=wx.BORDER_NONE)
        card.SetBackgroundColour(PANEL)
        card.SetMinSize((420, -1))
        box = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(card, label="员工考勤系统")
        title.SetForegroundColour(TEXT)
        title.SetFont(make_font(20, bold=True))
        subtitle = wx.StaticText(card, label="人脸识别打卡 · 桌面端")
        subtitle.SetForegroundColour(MUTED)
        subtitle.SetFont(make_font(10))
        box.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 28)
        box.Add(subtitle, 0, wx.LEFT | wx.RIGHT | wx.TOP, 28)

        self.username = wx.TextCtrl(card, value="employee", size=(-1, 38))
        self.password = wx.TextCtrl(card, value="employee123", style=wx.TE_PASSWORD, size=(-1, 38))
        for label, ctrl in (("用户名", self.username), ("密码", self.password)):
            text = wx.StaticText(card, label=label)
            text.SetForegroundColour(MUTED)
            text.SetFont(make_font(10))
            box.Add(text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 28)
            box.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 28)

        self.login_btn = button(card, "登录", primary=True)
        self.login_btn.Bind(wx.EVT_BUTTON, self._on_login)
        box.Add(self.login_btn, 0, wx.EXPAND | wx.ALL, 28)

        self.error = wx.StaticText(card, label="")
        self.error.SetForegroundColour(wx.Colour(255, 85, 112))
        self.error.SetFont(make_font(10))
        box.Add(self.error, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 28)

        card.SetSizer(box)
        outer.Add(card, 0, wx.ALIGN_CENTER)
        outer.AddStretchSpacer(2)
        self.SetSizer(outer)

    def _on_login(self, _event):
        self.error.SetLabel("")
        self.login_btn.Disable()
        try:
            user = self.api.login(self.username.GetValue(), self.password.GetValue())
        except ApiError as exc:
            self.error.SetLabel(str(exc))
            self.Layout()
            return
        finally:
            self.login_btn.Enable()
        self.on_success(user)


class MainPanel(wx.Panel):
    def __init__(self, parent, api: AttendanceApi, user: dict, on_logout):
        super().__init__(parent)
        self.api = api
        self.user = user
        self.on_logout = on_logout
        self.camera = CameraCapture()
        self.SetBackgroundColour(BG)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(self._build_header(), 0, wx.EXPAND | wx.ALL, 18)
        root.Add(self._build_body(), 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 18)
        self.SetSizer(root)

        self.refresh_status()

    def _build_header(self):
        header = wx.Panel(self)
        header.SetBackgroundColour(PANEL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        name = wx.StaticText(header, label=f"{self.user.get('name') or self.user['username']}")
        name.SetForegroundColour(TEXT)
        name.SetFont(make_font(16, bold=True))
        meta = wx.StaticText(
            header,
            label=f"{self.user.get('employee_no')} · {self.user.get('department_name') or '未分配部门'}",
        )
        meta.SetForegroundColour(MUTED)
        meta.SetFont(make_font(10))
        text_box = wx.BoxSizer(wx.VERTICAL)
        text_box.Add(name, 0, wx.BOTTOM, 4)
        text_box.Add(meta, 0)
        sizer.Add(text_box, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 16)

        self.status_label = wx.StaticText(header, label="人脸状态：查询中…")
        self.status_label.SetForegroundColour(CYAN)
        self.status_label.SetFont(make_font(10, bold=True))
        sizer.Add(self.status_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 16)

        logout = button(header, "退出登录")
        logout.Bind(wx.EVT_BUTTON, lambda _e: self.on_logout())
        sizer.Add(logout, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 12)

        header.SetSizer(sizer)
        return header

    def _build_body(self):
        body = wx.Panel(self)
        body.SetBackgroundColour(BG)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        self.info_text = wx.StaticText(body, label="")
        self.info_text.SetForegroundColour(MUTED)
        self.info_text.SetFont(make_font(10))
        left.Add(self.info_text, 0, wx.BOTTOM, 12)

        self.register_btn = button(body, "采集并注册人脸")
        self.register_btn.Bind(wx.EVT_BUTTON, lambda _e: self.capture_and_register())
        left.Add(self.register_btn, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.capture_btn = button(body, "刷新摄像头画面")
        self.capture_btn.Bind(wx.EVT_BUTTON, lambda _e: self.refresh_preview())
        left.Add(self.capture_btn, 0, wx.EXPAND | wx.BOTTOM, 18)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.punch_in_btn = button(body, "人脸签到", primary=True)
        self.punch_in_btn.Bind(wx.EVT_BUTTON, lambda _e: self.face_punch("in"))
        self.punch_out_btn = button(body, "人脸签退")
        self.punch_out_btn.Bind(wx.EVT_BUTTON, lambda _e: self.face_punch("out"))
        row.Add(self.punch_in_btn, 1, wx.RIGHT, 8)
        row.Add(self.punch_out_btn, 1)
        left.Add(row, 0, wx.EXPAND)

        self.message = wx.StaticText(body, label="")
        self.message.SetForegroundColour(MUTED)
        self.message.SetFont(make_font(10))
        left.Add(self.message, 0, wx.TOP, 14)

        sizer.Add(left, 1, wx.ALL | wx.EXPAND, 18)

        self.preview = PreviewPanel(body)
        sizer.Add(self.preview, 1, wx.ALL | wx.EXPAND, 18)

        body.SetSizer(sizer)
        return body

    def _set_preview(self, caption: str, image_data_url: str | None = None):
        if image_data_url:
            self.preview.set_data_url(image_data_url)
        else:
            self.preview.set_hint(caption)

    def _grab_image(self) -> str | None:
        try:
            return self.camera.read_data_url()
        except CameraError as exc:
            self.message.SetForegroundColour(wx.Colour(255, 200, 87))
            self.message.SetLabel(str(exc))
            self.Layout()
            return None

    def refresh_preview(self):
        image = self._grab_image()
        if image:
            self._set_preview("", image)

    def refresh_status(self):
        try:
            status = self.api.face_status()
        except ApiError as exc:
            self.status_label.SetLabel(f"人脸状态：{exc}")
            return
        if status.get("face_registered"):
            self.status_label.SetLabel("人脸状态：已注册")
            self.register_btn.SetLabel("重新采集人脸")
            self.punch_in_btn.Enable()
            self.punch_out_btn.Enable()
        else:
            self.status_label.SetLabel("人脸状态：未注册")
            self.register_btn.SetLabel("采集并注册人脸")
            self.punch_in_btn.Disable()
            self.punch_out_btn.Disable()
        self.info_text.SetLabel(
            f"工号 {status.get('employee_no')} · 部门 {status.get('department_name') or '未分配'}"
        )
        self.Layout()

    def capture_and_register(self):
        image = self._grab_image()
        if not image:
            return
        self._set_preview("", image)
        try:
            status = self.api.register_face(image)
        except ApiError as exc:
            self.message.SetForegroundColour(wx.Colour(255, 85, 112))
            self.message.SetLabel(f"注册失败：{exc}")
        else:
            self.message.SetForegroundColour(wx.Colour(56, 242, 180))
            self.message.SetLabel("人脸注册成功，可以开始打卡")
            self.refresh_status()
        self.Layout()

    def face_punch(self, punch_type: str):
        image = self._grab_image()
        if not image:
            return
        self._set_preview("", image)
        try:
            record = self.api.face_attendance(punch_type, image)
        except ApiError as exc:
            self.message.SetForegroundColour(wx.Colour(255, 85, 112))
            self.message.SetLabel(f"打卡失败：{exc}")
        else:
            label = "签到" if punch_type == "in" else "签退"
            at = record.get("sign_in_at") if punch_type == "in" else record.get("sign_out_at")
            self.message.SetForegroundColour(wx.Colour(56, 242, 180))
            self.message.SetLabel(
                f"{label}成功 · {record.get('work_date')} {str(at or '')[11:16]}"
            )
        self.Layout()

    def destroy(self):
        self.camera.close()
        super().destroy()


class MainFrame(wx.Frame):
    def __init__(self, api: AttendanceApi, on_ready=None):
        super().__init__(None, title=APP_TITLE, size=(1080, 680))
        self.api = api
        self.on_ready = on_ready
        self.SetBackgroundColour(BG)
        self.SetMinSize((880, 560))
        self._container = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._container)
        self._show_login()
        self.Centre()

    def _swap(self, panel: wx.Panel):
        self._container.Clear(delete_windows=True)
        self._container.Add(panel, 1, wx.EXPAND)
        self.Layout()

    def _show_login(self):
        self._swap(LoginPanel(self, self.api, self._show_main))

    def _show_main(self, user: dict):
        self._swap(MainPanel(self, self.api, user, self._logout))

    def _logout(self):
        self.api.logout()
        self._show_login()


def main():
    app = wx.App(False)
    frame = MainFrame(AttendanceApi())
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    sys.exit(main())
