"""I2：工时计算与工作日解析的纯函数测试。"""

from datetime import datetime, time

from app.services.working_time import (
    compute_working_minutes,
    is_workday,
    latest_attendance_status,
    parse_workdays,
    overlap_minutes,
)


def test_parse_workdays():
    assert parse_workdays("1,2,3,4,5") == {1, 2, 3, 4, 5}
    assert is_workday("1,2,3,4,5", 1) is True
    assert is_workday("1,2,3,4,5", 6) is False


def test_typical_full_day_works_480_minutes():
    sign_in = datetime(2026, 9, 1, 9, 0)
    sign_out = datetime(2026, 9, 1, 18, 0)
    assert compute_working_minutes(sign_in, sign_out, time(12, 0), time(13, 0)) == 480


def test_cross_break_from_1130_to_1330_works_60_minutes():
    sign_in = datetime(2026, 9, 1, 11, 30)
    sign_out = datetime(2026, 9, 1, 13, 30)
    assert compute_working_minutes(sign_in, sign_out, time(12, 0), time(13, 0)) == 60


def test_no_break_overlap_works_180_minutes():
    sign_in = datetime(2026, 9, 1, 14, 0)
    sign_out = datetime(2026, 9, 1, 17, 0)
    assert compute_working_minutes(sign_in, sign_out, time(12, 0), time(13, 0)) == 180


def test_overlap_minutes_direct():
    start = datetime(2026, 9, 1, 11, 30)
    end = datetime(2026, 9, 1, 13, 30)
    assert overlap_minutes(start, end, time(12, 0), time(13, 0)) == 60


def test_status_priority():
    assert latest_attendance_status(True, True, False, False) == "present"
    assert latest_attendance_status(True, True, True, False) == "late"
    assert latest_attendance_status(True, False, False, False) == "partial"
    assert latest_attendance_status(True, True, False, True) == "early_leave"

