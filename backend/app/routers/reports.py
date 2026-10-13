"""报表路由（I5c）：月度考勤报表。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models import Department, User
from app.schemas.reports import DepartmentReportOut, MonthlyReportOut
from app.services import attendance as attendance_service
from app.services import reports as report_service


router = APIRouter(prefix="/reports", tags=["报表"])


@router.get(
    "/monthly",
    response_model=MonthlyReportOut,
    summary="月度部门考勤报表",
)
def monthly_report(
    month: str | None = Query(None, description="YYYY-MM，默认当前月"),
    department_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("report.view.department")),
):
    try:
        start, end = attendance_service.parse_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    scope_department = department_id
    if user.role != "general_admin":
        scope_department = user.department_id
        if scope_department is None:
            raise HTTPException(status_code=403, detail="当前账号未分配部门")

    if scope_department is not None and db.get(Department, scope_department) is None:
        raise HTTPException(status_code=404, detail="部门不存在")

    rows = report_service.department_reports(
        db, start, end, department_id=scope_department
    )
    if scope_department is None:
        scope_label = "全公司"
    else:
        department = db.get(Department, scope_department)
        scope_label = department.name if department else "未知部门"

    return MonthlyReportOut(
        month=f"{start.year:04d}-{start.month:02d}",
        start_date=start,
        end_date=end,
        scope_label=scope_label,
        rows=[DepartmentReportOut(**row) for row in rows],
    )
