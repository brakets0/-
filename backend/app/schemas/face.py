"""人脸注册与人脸打卡的请求/响应结构。"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.baidu_face import MAX_IMAGE_BYTES


def _validate_image(value: str) -> str:
    """校验客户端上传的图片是 base64 data URL，并限制大小。"""
    value = value.strip()
    if "," not in value:
        raise ValueError("图片需为 base64 data URL")
    header, encoded = value.split(",", 1)
    if ";base64" not in header:
        raise ValueError("图片需为 base64 data URL")
    media = header[5:].split(";")[0].lower()
    if media not in {"image/jpeg", "image/jpg", "image/png"}:
        raise ValueError("仅支持 JPG/PNG 图片")
    if len(encoded) > MAX_IMAGE_BYTES * 4 // 3 + 1024:
        raise ValueError("图片过大，请压缩后重试")
    return f"data:{media};base64,{encoded}"


class FaceRegisterRequest(BaseModel):
    employee_id: int | None = Field(
        default=None, description="目标员工；留空表示当前登录账号"
    )
    image: str

    _validate_image = field_validator("image")(_validate_image)


class FaceAttendanceRequest(BaseModel):
    punch_type: Literal["in", "out"]
    image: str

    _validate_image = field_validator("image")(_validate_image)


class FaceStatusOut(BaseModel):
    employee_id: int
    employee_no: str
    name: str
    department_name: str | None = None
    face_registered: bool
    face_registered_at: datetime | None = None


class FacePunchOut(BaseModel):
    employee_id: int
    employee_no: str
    name: str
    score: float
    work_date: date
    punch_type: str
    status: str
    sign_in_at: datetime | None = None
    sign_out_at: datetime | None = None
    working_minutes: int
