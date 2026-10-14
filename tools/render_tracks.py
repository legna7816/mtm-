import argparse
import os
import cv2
import json

TRAIL = 30
GRAY = (160, 160, 160)
PALETTE = [(0, 0, 255), (255, 128, 0), (0, 200, 255), (255, 0, 255), (0, 255, 0), (255, 255, 0)]

def color_of(tracks, tid):
    moving_ids = sorted((t for t in tracks if tracks[t]["moving"]), key=int)
    if tid in moving_ids:
        return PALETTE[moving_ids.index(tid) % len(PALETTE)]
    return GRAY

def run(out_dir="outputs", video=None, out_path=None):
    with open(os.path.join(out_dir, "tracks_final.json"), encoding="utf-8") as f:
        data = json.load(f)

    video = video or data["video"]
    out_path = out_path or os.path.join(out_dir, "final.mp4")
    cut = data.get("scene_cut_frame")
    tracks = data["tracks"]

    by_frame = {}
    for tid, tr in tracks.items():
        for r in tr["frames"]:
            by_frame.setdefault(r["frame"], []).append((tid, r))

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise SystemExit(f"영상을 열지 못했음: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

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
            col = color_of(tracks, tid) if moving else GRAY
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
                cv2.line(frame, a, b, color_of(tracks, tid), 3)

        cv2.putText(frame, f"frame {frame_no}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        writer.write(frame)
        frame_no += 1

    cap.release()
    writer.release()
    print(f"저장: {out_path}")
    return out_path

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="tracks_final.json 추적 결과를 영상에 그리기")
    ap.add_argument("--out-dir", default="outputs", help="tracks_final.json이 있는 폴더")
    ap.add_argument("--video", default=None, help="생략하면 JSON에 기록된 영상 사용")
    ap.add_argument("--out", default=None, help="생략하면 <out-dir>/final.mp4")
    args = ap.parse_args()
    run(args.out_dir, args.video, args.out)