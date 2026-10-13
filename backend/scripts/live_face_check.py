"""真实人脸联调：检测/注册/检索都走真实百度云接口。

用法（在 backend 目录）：
    .venv/Scripts/python -m scripts.live_face_check D:\\path\\face.jpg detect
    .venv/Scripts/python -m scripts.live_face_check D:\\path\\face.jpg register E00001
    .venv/Scripts/python -m scripts.live_face_check D:\\path\\face.jpg search E00001

`register` 需要员工已存在（用工号），会把人脸写入百度人脸库；
`search` 用同一张照片检索，验证能否匹配回该工号。
"""

import base64
import sys
from pathlib import Path

from app.services.baidu_face import BaiduFaceClient, FaceServiceError


def _data_url(path: str) -> str:
    raw = Path(path).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    image_path, action = sys.argv[1], sys.argv[2]
    employee_no = sys.argv[3] if len(sys.argv) > 3 else None
    image = _data_url(image_path)
    client = BaiduFaceClient()

    try:
        if action == "detect":
            result = client.detect(image)
            print(f"OK: 检测到人脸 face_token={result['face_token'][:12]}...")
        elif action == "register":
            if not employee_no:
                print("register 需要提供工号")
                return 2
            token = client.add_face(employee_no, image)
            print(f"OK: 已注册 {employee_no}，face_token={token[:12]}...")
        elif action == "search":
            if not employee_no:
                print("search 需要提供工号")
                return 2
            result = client.search(image, user_id=employee_no)
            print(
                f"OK: 检索到 user_id={result['user_id']} "
                f"score={result['score']:.1f}"
            )
        else:
            print(f"未知动作：{action}")
            return 2
    except FaceServiceError as exc:
        print(f"FAIL: error_code={exc.error_code} message={exc.message}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
