import cv2
import json
import numpy as np
from collections import Counter
from ultralytics import YOLO

MODEL = "yolov8n.pt"
VIDEO = "data/videos/sample.mp4"
OUT = "outputs/tracked.mp4"
KEEP = [0, 1, 2, 3, 5, 7, 9]
SCENE_THRESH = 6

model = YOLO(MODEL)
cap = cv2.VideoCapture(VIDEO)

fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
writer = cv2.VideoWriter(OUT, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

history = {}
frame_no = 0
prev_gray = None
cut_frame = None
while True:
    ok, frame = cap.read()
    if not ok:
        break

    gray = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)   
    if prev_gray is not None:
        diff = np.abs(gray.astype(float) - prev_gray.astype(float)).mean()
        if diff > SCENE_THRESH:
            cut_frame = frame_no
            print(f"화면 전환 감지: 프레임 {frame_no} (차이 {diff:.1f}) → 여기서 분석 중단")
            break
    prev_gray = gray

    results = model.track(frame, persist=True, tracker="bytetrack.yaml",
                          conf=0.1, classes=KEEP, agnostic_nms=True,
                          imgsz=1280, verbose=False)
    r = results[0]

    ids = []
    if r.boxes.id is not None:
        for tid, c, cf, box in zip(r.boxes.id.tolist(), r.boxes.cls.tolist(),
                                   r.boxes.conf.tolist(), r.boxes.xywhn.tolist()):
            tid = int(tid)
            name = model.names[int(c)]
            cx, cy, bw, bh = box
            history.setdefault(tid, []).append({
                "frame": frame_no,
                "t": round(frame_no / fps, 3),
                "cls": name,
                "conf": round(cf, 3),
                "bbox": [round(cx - bw / 2, 4), round(cy - bh / 2, 4), round(bw, 4), round(bh, 4)],
                "pos": [round(cx, 4), round(cy + bh / 2, 4)],
            })
            ids.append(tid)
    # print(frame_no, "IDs:", ids)

    writer.write(r.plot())
    frame_no += 1

cap.release()
writer.release()

print("\n=== ID 요약 ===")
for tid, recs in sorted(history.items()):
    first, last = recs[0], recs[-1]
    major = Counter(rec["cls"] for rec in recs).most_common(1)[0][0]
    print(f"ID {tid:>3} | {major:<10} | 프레임 {first['frame']:>3}~{last['frame']:>3} ({len(recs):>3}회) | 시작 {first['pos']} → 끝 {last['pos']}")

out = {
    "schema_version": "0.2",
    "video": VIDEO,
    "fps": fps,
    "detector": MODEL,
    "tracker": "bytetrack",
    "frames_analyzed": frame_no,
    "scene_cut_frame": cut_frame,
    "tracks": {str(tid): recs for tid, recs in sorted(history.items())},
}
with open("outputs/tracks.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("저장: outputs/tracks.json")