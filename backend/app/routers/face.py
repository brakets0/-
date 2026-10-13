"""人脸路由：注册/换绑（管理员代操作）与人脸打卡（员工本人）。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import User
from app.permissions import is_attendance_subject
from app.schemas.face import (
    FaceAttendanceRequest,
    FacePunchOut,
    FaceRegisterRequest,
    FaceStatusOut,
)
from app.services import attendance as attendance_service
from app.services import face_service
from app.services.attendance import PunchConflict
from app.services.baidu_face import (
    BaiduFaceClient,
    FaceConfigError,
    FaceNetworkError,
    FaceServiceError,
    NoFaceDetected,
    get_face_client,
)


router = APIRouter(prefix="/face", tags=["人脸识别"])


def _status_out(user: User) -> FaceStatusOut:
    return FaceStatusOut(
        employee_id=user.id,
        employee_no=user.employee_no,
        name=user.name,
        department_name=user.department_name,
        face_registered=user.face_registered,
        face_registered_at=user.face_registered_at,
    )


def _raise_service_error(exc: Exception) -> None:
    """把百度/网络异常映射成稳定的 HTTP 状态码。"""
    if isinstance(exc, FaceConfigError):
        raise HTTPException(status_code=503, detail="人脸服务未配置，请联系管理员")
    if isinstance(exc, FaceNetworkError):
        raise HTTPException(status_code=503, detail="人脸服务暂不可用，请稍后重试")
    if isinstance(exc, NoFaceDetected):
        raise HTTPException(status_code=422, detail="图片中未检测到人脸，请重新拍摄")
    if isinstance(exc, FaceServiceError):
        if exc.error_code == 18:
            raise HTTPException(status_code=429, detail="人脸服务调用过于频繁，请稍后重试")
        raise HTTPException(status_code=502, detail=f"人脸服务调用失败：{exc.message}")
    raise exc


@router.post("/register", response_model=FaceStatusOut, summary="注册或换绑人脸")
def register_face(
    payload: FaceRegisterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    client: BaiduFaceClient = Depends(get_face_client),
):
    target = user if payload.employee_id is None else db.get(User, payload.employee_id)
    if target is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    if not is_attendance_subject(target.role):
        raise HTTPException(status_code=400, detail="该账号不参与考勤")
    try:
        face_service.ensure_face_registration_allowed(user, target)
    except face_service.FacePermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    try:
        target = face_service.register_face(db, client, target, payload.image)
    except Exception as exc:  # noqa: BLE001 - 统一交给状态码映射
        _raise_service_error(exc)
    return _status_out(target)


@router.get("/me", response_model=FaceStatusOut, summary="当前账号人脸绑定状态")
def face_status(
    user: User = Depends(get_current_user),
):
    return _status_out(user)


@router.post("/attendance", response_model=FacePunchOut, summary="人脸考勤打卡")
def face_attendance(
    payload: FaceAttendanceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attendance.sign")),
    client: BaiduFaceClient = Depends(get_face_client),
):
    if not is_attendance_subject(user.role):
        raise HTTPException(status_code=403, detail="总管理员不参与考勤")
    try:
        employee, score = face_service.match_employee(
            db, client, user.employee_no, payload.image
        )
    except face_service.FaceNotRegistered as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except face_service.FaceMatchRejected as exc:
        message = (
            f"人脸比对未通过（相似度 {exc.score:.1f}）"
            if exc.score is not None
            else str(exc)
        )
        raise HTTPException(status_code=401, detail=message)
    except Exception as exc:  # noqa: BLE001 - 统一交给状态码映射
        _raise_service_error(exc)
    if employee.id != user.id:
        raise HTTPException(status_code=401, detail="人脸与当前账号不匹配")

    try:
        record = attendance_service.punch(db, user, payload.punch_type)
    except PunchConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return FacePunchOut(
        employee_id=user.id,
        employee_no=user.employee_no,
        name=user.name,
        score=score,
        work_date=record.work_date,
        punch_type=payload.punch_type,
        status=record.status,
        sign_in_at=record.sign_in_at,
        sign_out_at=record.sign_out_at,
        working_minutes=record.working_minutes,
    )
