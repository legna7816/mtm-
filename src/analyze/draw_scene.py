import cv2
import json
import numpy as np

VIDEO = "data/videos/sample.mp4"
SCENE = "scenes/sample.json"
OUT = "outputs/scene_check.jpg"
COLORS = {"road": (0, 200, 0), "parking_left": (255, 128, 0),
          "roadside_right": (255, 0, 255), "side_entry_left": (0, 255, 255)}

with open(SCENE, encoding="utf-8") as f:
    scene = json.load(f)

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, scene["frame_ref"])
ok, frame = cap.read()
cap.release()
if not ok:
    raise SystemExit("프레임을 읽지 못했어요")
h, w = frame.shape[:2]


def to_px(pts):                                    # 정규화 좌표 목록 → 픽셀 좌표 배열
    return np.array([[int(x * w), int(y * h)] for x, y in pts], np.int32)


overlay = frame.copy()
for z in scene["zones"]:
    cv2.fillPoly(overlay, [to_px(z["polygon"])], COLORS.get(z["id"], (200, 200, 200)))
frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)   # 칠한 이미지 35% + 원본 65%

cv2.polylines(frame, [to_px(scene["roi"])], True, (255, 255, 255), 2)      # 분석 영역: 흰 테두리
for ln in scene["lines"]:
    cv2.polylines(frame, [to_px(ln["points"])], False, (0, 0, 255), 4)      # 선: 빨강

for z in scene["zones"]:                            # 영역 이름을 꼭짓점 평균 위치에 표시
    cx = int(np.mean([p[0] for p in z["polygon"]]) * w)
    cy = int(np.mean([p[1] for p in z["polygon"]]) * h)
    cv2.putText(frame, z["id"], (cx - 60, cy), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
    cv2.putText(frame, z["id"], (cx - 60, cy), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

cv2.imwrite(OUT, frame)
print(f"저장: {OUT}")