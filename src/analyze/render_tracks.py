import cv2
import json

VIDEO = "data/videos/sample.mp4"
IN = "outputs/tracks_final.json"
OUT = "outputs/final.mp4"
TRAIL = 30
GRAY = (160, 160, 160)

with open(IN, encoding="utf-8") as f:
    data = json.load(f)
cut = data.get("scene_cut_frame")
tracks = data["tracks"]

by_frame = {}
for tid, tr in tracks.items():
    for r in tr["frames"]:
        by_frame.setdefault(r["frame"], []).append((tid, r))


PALETTE = [(0, 0, 255), (255, 128, 0), (0, 200, 255), (255, 0, 255), (0, 255, 0), (255, 255, 0)]
moving_ids = sorted((t for t in tracks if tracks[t]["moving"]), key=int)


def color_of(tid):
    if tid in moving_ids:
        return PALETTE[moving_ids.index(tid) % len(PALETTE)]
    return GRAY


cap = cv2.VideoCapture(VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
writer = cv2.VideoWriter(OUT, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

trails = {}
frame_no = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if cut is not None and frame_no >= cut:
        break

    for tid, r in by_frame.get(frame_no, []):
        tr = tracks[tid]
        moving = tr["moving"]
        col = color_of(tid) if moving else GRAY
        thick = (1 if r.get("interp") else 3) if moving else 1

        x, y, bw, bh = r["bbox"]
        x1, y1 = int(x * w), int(y * h)
        x2, y2 = int((x + bw) * w), int((y + bh) * h)
        cv2.rectangle(frame, (x1, y1), (x2, y2), col, thick)

        label = f"ID {tid} {tr['cls']}" if moving else f"{tid}"
        cv2.putText(frame, label, (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8 if moving else 0.5, col, 2 if moving else 1)

        if moving:
            px, py = int(r["pos"][0] * w), int(r["pos"][1] * h)
            trails.setdefault(tid, []).append((frame_no, px, py))

    for tid, pts in trails.items():
        recent = [(px, py) for f, px, py in pts if frame_no - f <= TRAIL]
        for a, b in zip(recent, recent[1:]):
            cv2.line(frame, a, b, color_of(tid), 3)

    cv2.putText(frame, f"frame {frame_no}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    writer.write(frame)
    frame_no += 1

cap.release()
writer.release()
print(f"저장: {OUT}")