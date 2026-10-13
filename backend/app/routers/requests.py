"""审批路由（I5b）：请假与外派申请、列表查询、审批。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import BusinessTrip, LeaveRequest, User
from app.permissions import get_permissions
from app.schemas.leave_trip import (
    LeaveCreate,
    RequestOut,
    ReviewRequest,
    TripCreate,
)


leave_router = APIRouter(prefix="/leave-requests", tags=["审批-请假"])
trip_router = APIRouter(prefix="/business-trips", tags=["审批-外派"])


def _serialize(item, request_type: str) -> RequestOut:
    employee = item.employee
    department = employee.department if employee else None
    approver = item.approver
    return RequestOut(
        id=item.id,
        type=request_type,
        type_label=getattr(item, "leave_type", "外派"),
        employee_id=item.employee_id,
        employee_no=employee.employee_no if employee else None,
        employee_name=employee.name if employee else None,
        department_id=employee.department_id if employee else None,
        department_name=department.name if department else None,
        start_date=item.start_date,
        end_date=item.end_date,
        duration_days=float(item.duration_days),
        reason=item.reason,
        status=item.status,
        approver_name=approver.name if approver else None,
        review_note=item.review_note,
        created_at=item.created_at,
        reviewed_at=item.reviewed_at,
    )


def _scoped_statement(model, user: User):
    """员工看自己，部门管理员看本部门（含自己），总管理员看全部。"""
    permissions = get_permissions(user.role)
    if user.role == "general_admin":
        return select(model)
    if "leave.review.department" in permissions:
        colleagues = select(User.id).where(User.department_id == user.department_id)
        return select(model).where(
            or_(model.employee_id == user.id, model.employee_id.in_(colleagues))
        )
    return select(model).where(model.employee_id == user.id)


def _list(db: Session, model, user: User, status: str | None) -> list[RequestOut]:
    stmt = _scoped_statement(model, user).options(
        selectinload(model.employee).selectinload(User.department),
        selectinload(model.approver),
    )
    if status:
        stmt = stmt.where(model.status == status)
    items = db.execute(stmt.order_by(model.created_at.desc(), model.id.desc())).scalars()
    request_type = "leave" if model is LeaveRequest else "trip"
    return [_serialize(item, request_type) for item in items]


def _review(db: Session, model, item_id: int, payload: ReviewRequest, user: User):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="申请不存在")

    permissions = get_permissions(user.role)
    if user.role != "general_admin":
        if "leave.review.department" not in permissions:
            raise HTTPException(status_code=403, detail="权限不足")
        if item.employee.department_id != user.department_id:
            raise HTTPException(status_code=403, detail="只能审批本部门申请")

    if item.status != "pending":
        raise HTTPException(status_code=409, detail="该申请已处理")

    item.status = payload.status
    item.review_note = payload.review_note
    item.approver_id = user.id
    item.reviewed_at = datetime.now()
    db.commit()
    db.refresh(item)
    return _serialize(item, "leave" if model is LeaveRequest else "trip")


def _delete(db: Session, model, item_id: int, user: User) -> None:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="申请不存在")

    permissions = get_permissions(user.role)
    if user.role != "general_admin":
        if item.employee_id == user.id:
            if item.status != "pending":
                raise HTTPException(status_code=409, detail="只能撤回待审批申请")
        elif "leave.review.department" in permissions:
            if item.employee.department_id != user.department_id:
                raise HTTPException(status_code=403, detail="只能处理本部门申请")
        else:
            raise HTTPException(status_code=403, detail="权限不足")

    db.delete(item)
    db.commit()


@leave_router.post("", response_model=RequestOut, summary="提交请假申请")
def create_leave(
    payload: LeaveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("leave.apply")),
):
    item = LeaveRequest(
        employee_id=user.id,
        leave_type=payload.leave_type.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=payload.duration_days,
        reason=payload.reason,
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(item, "leave")


@leave_router.get("", response_model=list[RequestOut], summary="请假申请列表")
def list_leave(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _list(db, LeaveRequest, user, status)


@leave_router.delete("/{request_id}", status_code=204, summary="撤回请假申请")
def delete_leave(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _delete(db, LeaveRequest, request_id, user)


@leave_router.patch(
    "/{request_id}/review", response_model=RequestOut, summary="审批请假申请"
)
def review_leave(
    request_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_permission("leave.review.department")
    ),
):
    return _review(db, LeaveRequest, request_id, payload, user)


@trip_router.post("", response_model=RequestOut, summary="提交外派申请")
def create_trip(
    payload: TripCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("trip.apply")),
):
    item = BusinessTrip(
        employee_id=user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=payload.duration_days,
        reason=payload.reason,
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(item, "trip")


@trip_router.get("", response_model=list[RequestOut], summary="外派申请列表")
def list_trip(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _list(db, BusinessTrip, user, status)


@trip_router.delete("/{request_id}", status_code=204, summary="撤回外派申请")
def delete_trip(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _delete(db, BusinessTrip, request_id, user)


@trip_router.patch(
    "/{request_id}/review", response_model=RequestOut, summary="审批外派申请"
)
def review_trip(
    request_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_permission("trip.review.department")
    ),
):
    return _review(db, BusinessTrip, request_id, payload, user)
