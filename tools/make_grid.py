import cv2
VIDEO = "data/videos/sample.mp4"
OUT = "outputs/grid.jpg"
FRAME_NO = 0
STEP = 0.05

def label(img, text, org, col):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME_NO)
ok, frame = cap.read()
cap.release()
if not ok:
    raise SystemExit("프레임을 읽지 못했음")

h, w = frame.shape[:2]
n = round(1 / STEP)

for i in range(1, n):
    v = i * STEP
    major = (i % 2 == 0)
    col = (0, 255, 255) if major else (200, 200, 200)
    th = 2 if major else 1
    x, y = int(v * w), int(v * h)
    cv2.line(frame, (x, 0), (x, h), col, th)
    cv2.line(frame, (0, y), (w, y), col, th)
    if major:
        label(frame, f"{v:.1f}", (x + 4, 30), col)
        label(frame, f"{v:.1f}", (6, y - 6), col)

cv2.imwrite(OUT, frame)
print(f"저장: {OUT} ({w}x{h}, 프레임 {FRAME_NO})")