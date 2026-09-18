"""ORM 模型汇总：所有模块都要被导入，确保 Base.metadata 注册完整。"""

from app.models.attendance import Attendance
from app.models.business_trip import BusinessTrip
from app.models.department import Department
from app.models.leave_request import LeaveRequest
from app.models.shift import Shift
from app.models.user import User

__all__ = [
    "Attendance",
    "BusinessTrip",
    "Department",
    "LeaveRequest",
    "Shift",
    "User",
]

