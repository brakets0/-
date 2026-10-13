"""人脸业务编排：注册/换绑、人脸检索、打卡前置校验。

职责划分：
- `services/baidu_face.py` 只负责调用百度云；
- 本模块负责权限、数据库状态与调用顺序；
- 考勤记录仍复用 `services/attendance.py` 的打卡逻辑，避免两套口径。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.services.baidu_face import BaiduFaceClient, FaceServiceError


class FacePermissionError(Exception):
    """当前账号无权为该员工注册人脸。"""


class FaceNotRegistered(Exception):
    """该员工尚未注册人脸。"""


class FaceMatchRejected(Exception):
    """检索结果与申报身份不一致或分数不足。"""

    def __init__(self, score: float | None = None):
        super().__init__("人脸比对未通过")
        self.score = score


def ensure_face_registration_allowed(operator: User, target: User) -> None:
    """只有总管理员与目标员工同部门的部门管理员可以代注册/换绑。"""
    if operator.role == "general_admin":
        return
    if (
        operator.role == "department_manager"
        and operator.department_id is not None
        and operator.department_id == target.department_id
    ):
        return
    raise FacePermissionError("无权为该员工注册人脸，请联系部门管理员")


def register_face(
    db: Session, client: BaiduFaceClient, target: User, image: str
) -> User:
    """调用百度注册/换绑人脸，并把 face_token 落到员工记录上。"""
    face_token = client.add_face(target.employee_no, image)
    target.face_token = face_token
    target.face_registered_at = datetime.now()
    db.commit()
    db.refresh(target)
    return target


def match_employee(
    db: Session, client: BaiduFaceClient, employee_no: str, image: str
) -> tuple[User, float]:
    """人脸检索并返回（匹配员工，相似度）；供人脸打卡复用。"""
    employee = db.query(User).filter(User.employee_no == employee_no).one_or_none()
    if employee is None or not employee.face_token:
        raise FaceNotRegistered("该员工尚未注册人脸")

    result = client.search(image, user_id=employee_no)
    if result.get("user_id") != employee_no:
        raise FaceMatchRejected(result.get("score"))
    score = float(result.get("score") or 0)
    if score < settings.baidu_face_score_threshold:
        raise FaceMatchRejected(score)
    return employee, score
