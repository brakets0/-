"""员工人脸考勤桌面端（wxPython）。

登录 → 人脸注册（部门管理员/总管理员代操作）→ 人脸签到/签退。
摄像头只做抓帧与上传，人脸识别与比对全部由后端调用百度云完成。
配色与 Web 管理台保持一致（浅色企业风）：
    背景 #F5F6F8 / 卡片 #FFFFFF / 边框 #E4E6EE / 主色 #5F7A99。
"""

import base64
import sys

import wx

from api_client import ApiError, AttendanceApi
from camera import CameraCapture, CameraError


APP_TITLE = "员工考勤系统 · 桌面端"

# ---------------- 设计 token（与 Web 端一致） ----------------
BG = wx.Colour(0xF5, 0xF6, 0xF8)
SURFACE = wx.Colour(0xFF, 0xFF, 0xFF)
SURFACE_ALT = wx.Colour(0xFA, 0xFB, 0xFC)
BORDER = wx.Colour(0xE4, 0xE6, 0xEE)

TEXT = wx.Colour(0x33, 0x36, 0x45)
MUTED = wx.Colour(0x7C, 0x85, 0x98)

PRIMARY = wx.Colour(0x5F, 0x7A, 0x99)
PRIMARY_HOVER = wx.Colour(0x51, 0x69, 0x8A)
PRIMARY_TEXT = wx.Colour(0xFF, 0xFF, 0xFF)
GHOST_HOVER = wx.Colour(0xF3, 0xF6, 0xFA)

SUCCESS = wx.Colour(0x3E, 0xA9, 0x8C)
WARNING = wx.Colour(0xD9, 0x90, 0x3F)
DANGER = wx.Colour(0xC2, 0x54, 0x3F)

DISABLED_BG = wx.Colour(0xEE, 0xF0, 0xF4)
DISABLED_TEXT = wx.Colour(0xA8, 0xB0, 0xC0)

BRAND = wx.Colour(0x4C, 0x7C, 0xE0)
BRAND_ALT = wx.Colour(0x7F, 0xA8, 0xA0)

CARD_RADIUS = 10


def make_font(size: int, *, bold: bool = False) -> wx.Font:
    font = wx.Font(
        size,
        wx.FONTFAMILY_DEFAULT,
        wx.FONTSTYLE_NORMAL,
        wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL,
    )
    if not font.SetFaceName("Microsoft YaHei UI"):
        font.SetFaceName("Microsoft YaHei")
    return font


def text_label(parent, label: str, *, size=10, bold=False, colour=TEXT) -> wx.StaticText:
    widget = wx.StaticText(parent, label=label)
    widget.SetForegroundColour(colour)
    widget.SetFont(make_font(size, bold=bold))
    return widget


class CardPanel(wx.Panel):
    """带圆角与细边框的白色卡片容器。"""

    def __init__(self, parent, *, radius: int = CARD_RADIUS):
        super().__init__(parent)
        self._radius = radius
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _on_paint(self, _event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        width, height = self.GetClientSize()
        dc.SetPen(wx.Pen(BORDER, 1))
        dc.SetBrush(wx.Brush(SURFACE))
        dc.DrawRoundedRectangle(0, 0, width - 1, height - 1, self._radius)


class BrandMark(wx.Panel):
    """品牌标记：圆角渐变方块 + 白色圆环。"""

    def __init__(self, parent, size: int = 40):
        super().__init__(parent, size=(size, size))
        self._size = size
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _on_paint(self, _event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        size = self._size
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.GradientFillLinear(
            wx.Rect(0, 0, size, size), BRAND, BRAND_ALT, wx.EAST
        )
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255, 220), 2))
        inset = int(size * 0.28)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawCircle(size // 2, size // 2, (size - inset * 2) // 2)


class HoverButton(wx.Panel):
    """自绘按钮：支持主色/次要样式、禁用态与悬停动画。"""

    def __init__(self, parent, label: str, *, primary=False, width=140, height=40, on_click=None):
        super().__init__(parent, size=(width, height))
        self._label = label
        self._primary = primary
        self._enabled = True
        self._hover = False
        self._pressed = False
        self._on_click = on_click
        self.SetMinSize((width, height))
        self.SetFont(make_font(10, bold=True))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ENTER_WINDOW, self._on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_SIZE, lambda _e: self.Refresh())
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))

    # -- 外部接口 --
    def SetLabel(self, label: str):
        self._label = label
        self.Refresh()

    def GetLabel(self) -> str:
        return self._label

    def Enable(self, enable: bool = True):
        self._enabled = enable
        self._hover = False
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND if enable else wx.CURSOR_ARROW))
        self.Refresh()

    def Disable(self):
        self.Enable(False)

    def IsEnabled(self) -> bool:
        return self._enabled

    # -- 事件 --
    def _on_enter(self, _event):
        if self._enabled:
            self._hover = True
            self.Refresh()

    def _on_leave(self, _event):
        self._hover = False
        self._pressed = False
        self.Refresh()

    def _on_down(self, _event):
        if self._enabled:
            self._pressed = True
            self.Refresh()

    def _on_up(self, _event):
        if not self._enabled:
            return
        was_pressed = self._pressed
        self._pressed = False
        self.Refresh()
        if was_pressed and self._on_click:
            self._on_click()

    def _on_paint(self, _event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        width, height = self.GetClientSize()
        radius = 8

        if not self._enabled:
            background, foreground, border = DISABLED_BG, DISABLED_TEXT, BORDER
        elif self._primary:
            background = PRIMARY_HOVER if (self._hover or self._pressed) else PRIMARY
            foreground, border = PRIMARY_TEXT, background
        else:
            background = GHOST_HOVER if (self._hover or self._pressed) else SURFACE
            foreground = PRIMARY if self._hover else TEXT
            border = PRIMARY if self._hover else BORDER

        # 悬停时画一层极淡的阴影，模拟“上浮”
        if self._hover and self._enabled:
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.Brush(wx.Colour(0xE7, 0xEC, 0xF3)))
            dc.DrawRoundedRectangle(2, 3, width - 4, height - 4, radius)

        dc.SetPen(wx.Pen(border, 1))
        dc.SetBrush(wx.Brush(background))
        offset = 1 if (self._hover and self._enabled) else 0
        dc.DrawRoundedRectangle(1, 1 + offset, width - 2, height - 2, radius)

        dc.SetTextForeground(foreground)
        dc.SetFont(self.GetFont())
        text_width, text_height = dc.GetTextExtent(self._label)
        dc.DrawText(
            self._label,
            (width - text_width) // 2,
            (height - text_height) // 2 + offset,
        )


class PreviewPanel(wx.Panel):
    """摄像头预览：静态图显示，未取到画面时显示提示文字。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.SetMinSize((420, 320))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self._bitmap: wx.Bitmap | None = None
        self._hint = "摄像头预览"
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, lambda _e: self.Refresh())

    def set_hint(self, hint: str):
        self._bitmap = None
        self._hint = hint
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
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(SURFACE_ALT))
        dc.Clear()
        width, height = self.GetClientSize()
        dc.SetPen(wx.Pen(BORDER, 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRoundedRectangle(0, 0, width - 1, height - 1, CARD_RADIUS)

        if self._bitmap and self._bitmap.IsOk():
            bitmap = self._bitmap
            scale = min(
                (width - 24) / bitmap.GetWidth(), (height - 24) / bitmap.GetHeight()
            )
            new_width = max(1, int(bitmap.GetWidth() * scale))
            new_height = max(1, int(bitmap.GetHeight() * scale))
            image = bitmap.ConvertToImage().Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
            dc.DrawBitmap(
                image.ConvertToBitmap(),
                (width - new_width) // 2,
                (height - new_height) // 2,
            )
            return

        dc.SetTextForeground(MUTED)
        dc.SetFont(make_font(11))
        text_width, text_height = dc.GetTextExtent(self._hint)
        dc.DrawText(self._hint, (width - text_width) // 2, (height - text_height) // 2)


class LoginPanel(wx.Panel):
    def __init__(self, parent, api: AttendanceApi, on_success):
        super().__init__(parent)
        self.api = api
        self.on_success = on_success
        self.SetBackgroundColour(BG)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.AddStretchSpacer(1)

        card = CardPanel(self, radius=14)
        card.SetMinSize((400, -1))
        box = wx.BoxSizer(wx.VERTICAL)

        brand_row = wx.BoxSizer(wx.HORIZONTAL)
        brand_row.Add(BrandMark(card, 38), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        brand_text = wx.BoxSizer(wx.VERTICAL)
        brand_text.Add(text_label(card, "员工考勤系统", size=15, bold=True), 0)
        brand_text.Add(text_label(card, "人脸识别打卡 · 桌面端", size=9, colour=MUTED), 0, wx.TOP, 3)
        brand_row.Add(brand_text, 1, wx.ALIGN_CENTER_VERTICAL)
        box.Add(brand_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 28)

        box.Add(text_label(card, "用户名", size=9, colour=MUTED), 0, wx.LEFT | wx.RIGHT | wx.TOP, 28)
        self.username = wx.TextCtrl(card, value="employee", size=(-1, 34))
        box.Add(self.username, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 28)

        box.Add(text_label(card, "密码", size=9, colour=MUTED), 0, wx.LEFT | wx.RIGHT | wx.TOP, 28)
        self.password = wx.TextCtrl(
            card, value="employee123", style=wx.TE_PASSWORD, size=(-1, 34)
        )
        box.Add(self.password, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 28)

        self.login_btn = HoverButton(
            card, "登录", primary=True, width=344, height=40, on_click=self._on_login
        )
        box.Add(self.login_btn, 0, wx.EXPAND | wx.ALL, 28)

        self.error = text_label(card, "", size=9, colour=DANGER)
        box.Add(self.error, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 28)

        card.SetSizer(box)
        card.SetSize(card.GetBestSize())
        outer.Add(card, 0, wx.ALIGN_CENTER)
        outer.AddStretchSpacer(2)
        self.SetSizer(outer)

    def _on_login(self, _event=None):
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
        header = CardPanel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        name_view = wx.BoxSizer(wx.VERTICAL)
        name_view.Add(
            text_label(header, self.user.get("name") or self.user["username"], size=13, bold=True),
            0,
            wx.BOTTOM,
            3,
        )
        name_view.Add(
            text_label(
                header,
                f"{self.user.get('employee_no')} · {self.user.get('department_name') or '未分配部门'}",
                size=9,
                colour=MUTED,
            ),
            0,
        )
        sizer.Add(name_view, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 16)

        self.status_label = text_label(header, "人脸状态：查询中…", size=9, bold=True, colour=PRIMARY)
        sizer.Add(self.status_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 14)

        logout = HoverButton(header, "退出登录", width=92, height=34, on_click=self.on_logout)
        sizer.Add(logout, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)

        header.SetSizer(sizer)
        header.SetMinSize((-1, 72))
        return header

    def _build_body(self):
        body = CardPanel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        self.info_text = text_label(body, "", size=9, colour=MUTED)
        left.Add(self.info_text, 0, wx.BOTTOM, 12)

        self.register_btn = HoverButton(
            body, "采集并注册人脸", width=300, height=38, on_click=self.capture_and_register
        )
        left.Add(self.register_btn, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.capture_btn = HoverButton(
            body, "刷新摄像头画面", width=300, height=38, on_click=self.refresh_preview
        )
        left.Add(self.capture_btn, 0, wx.EXPAND | wx.BOTTOM, 18)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.punch_in_btn = HoverButton(
            body, "人脸签到", primary=True, width=146, height=42, on_click=lambda: self.face_punch("in")
        )
        self.punch_out_btn = HoverButton(
            body, "人脸签退", width=146, height=42, on_click=lambda: self.face_punch("out")
        )
        row.Add(self.punch_in_btn, 1, wx.RIGHT, 8)
        row.Add(self.punch_out_btn, 1)
        left.Add(row, 0, wx.EXPAND)

        self.message = text_label(body, "", size=9, colour=MUTED)
        left.Add(self.message, 0, wx.TOP, 14)

        sizer.Add(left, 0, wx.ALL | wx.EXPAND, 18)

        self.preview = PreviewPanel(body)
        sizer.Add(self.preview, 1, wx.ALL | wx.EXPAND, 18)

        body.SetSizer(sizer)
        return body

    def _set_preview(self, hint: str, image_data_url: str | None = None):
        if image_data_url:
            self.preview.set_data_url(image_data_url)
        else:
            self.preview.set_hint(hint)

    def _grab_image(self) -> str | None:
        try:
            return self.camera.read_data_url()
        except CameraError as exc:
            self.message.SetForegroundColour(WARNING)
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
            self.status_label.SetForegroundColour(SUCCESS)
            self.status_label.SetLabel("人脸状态：已注册")
            self.register_btn.SetLabel("重新采集人脸")
            self.punch_in_btn.Enable(True)
            self.punch_out_btn.Enable(True)
        else:
            self.status_label.SetForegroundColour(WARNING)
            self.status_label.SetLabel("人脸状态：未注册")
            self.register_btn.SetLabel("采集并注册人脸")
            self.punch_in_btn.Enable(False)
            self.punch_out_btn.Enable(False)
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
            self.api.register_face(image)
        except ApiError as exc:
            self.message.SetForegroundColour(DANGER)
            self.message.SetLabel(f"注册失败：{exc}")
        else:
            self.message.SetForegroundColour(SUCCESS)
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
            self.message.SetForegroundColour(DANGER)
            self.message.SetLabel(f"打卡失败：{exc}")
        else:
            label = "签到" if punch_type == "in" else "签退"
            at = record.get("sign_in_at") if punch_type == "in" else record.get("sign_out_at")
            self.message.SetForegroundColour(SUCCESS)
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
