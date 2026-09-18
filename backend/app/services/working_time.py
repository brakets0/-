"""工时与班次相关的基础计算工具（I2 先实现纯函数，I9 接入打卡）。"""

from datetime import datetime, time


ATTENDANCE_STATUS_PRIORITY = ["absent", "late", "early_leave", "partial", "present"]


def parse_workdays(workdays: str) -> set[int]:
    """把 '1,2,3,4,5' 解析为 {1,2,3,4,5}。"""
    return {int(item) for item in workdays.split(",") if item.strip()}


def is_workday(workdays: str, weekday_iso: int) -> bool:
    """判断某个 ISO 星期几(1=周一)是否在班次工作日内。"""
    return weekday_iso in parse_workdays(workdays)


def overlap_minutes(start: datetime, end: datetime, break_start: time, break_end: time) -> int:
    """返回 [start, end] 与 [break_start, break_end] 的重叠分钟数。"""
    break_begin = datetime.combine(start.date(), break_start)
    break_finish = datetime.combine(start.date(), break_end)
    overlap_start = max(start, break_begin)
    overlap_end = min(end, break_finish)
    if overlap_end <= overlap_start:
        return 0
    return int((overlap_end - overlap_start).total_seconds() // 60)


def compute_working_minutes(
    sign_in: datetime,
    sign_out: datetime,
    break_start: time | None = None,
    break_end: time | None = None,
) -> int:
    """按"总分钟数 - 午休重叠分钟数"计算实际工时。"""
    if sign_out <= sign_in:
        return 0
    total_minutes = int((sign_out - sign_in).total_seconds() // 60)
    if break_start and break_end:
        total_minutes -= overlap_minutes(sign_in, sign_out, break_start, break_end)
    return max(0, total_minutes)


def latest_attendance_status(sign_in: bool, sign_out: bool, is_late: bool, is_early: bool) -> str:
    """根据打卡情况返回展示用主状态；缺勤等状态由对账流程单独生成。"""
    if is_late:
        if sign_out:
            return "late"
        return "partial"
    if is_early:
        if sign_in:
            return "early_leave"
        return "partial"
    if sign_in and sign_out:
        return "present"
    return "partial"
