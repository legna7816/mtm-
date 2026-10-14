import argparse
import cv2

STEP = 0.05

def label(img, text, org, col):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)

def run(video, out_path="outputs/grid.jpg", frame_no=0):
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"프레임을 읽지 못했음: {video}")
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

    cv2.imwrite(out_path, frame)
    print(f"저장: {out_path} ({w}x{h}, 프레임 {frame_no})")
    return out_path

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="sample.mp4 영상의 첫 프레임을 기준으로 그리드 그리기")
    ap.add_argument("--video", default="data/videos/sample.mp4")
    ap.add_argument("--out", default="outputs/grid.jpg")
    ap.add_argument("--frame", type=int, default=0)
    args = ap.parse_args()
    run(args.video, args.out, args.frame)