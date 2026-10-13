import os
import json
import math
from collections import Counter

MAX_GAP = 20      # 이어붙일 수 있는 최대 공백 (프레임)
MAX_DIST = 0.2    # 앞 조각 끝 ~ 뒤 조각 시작 최대 거리 (정규화 좌표)

STATIC_SPEED = 0.002  # 프레임당 이동량이 이보다 작으면 정지 조각
STATIC_DIST = 0.05    # 정지 조각 뒤에 이어붙일 수 있는 최대 거리

def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])

def is_static(recs):
    x0, y0 = recs[0]["pos"]
    move = max(math.hypot(r["pos"][0] - x0, r["pos"][1] - y0) for r in recs)
    span = recs[-1]["frame"] - recs[0]["frame"]
    return span > 0 and move / span < STATIC_SPEED

def run(out_dir="outputs"):
    in_path = os.path.join(out_dir, "tracks.json")
    out_path = os.path.join(out_dir, "tracks_stitched.json")

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)
    tracks = data["tracks"]
    order = sorted(tracks, key=lambda tid: tracks[tid][0]["frame"])

    merged = {}    # 대표 ID -> 이어붙인 기록 목록
    members = {}   # 대표 ID -> 합쳐진 원래 ID 목록

    for tid in order:
        recs = tracks[tid]
        start = recs[0]

        best, best_d, best_gap = None, None, None
        for root, mrecs in merged.items():
            end = mrecs[-1]
            gap = start["frame"] - end["frame"]
            if gap <= 0 or gap > MAX_GAP:
                continue
            d = dist(end["pos"], start["pos"])
            static = is_static(mrecs)
            limit = STATIC_DIST if static else MAX_DIST
            if d > limit:
                if static and d <= MAX_DIST:
                    print(f"거부: {root} <- {tid} (정지 조각 뒤 거리 {d:.3f} > {STATIC_DIST})")
                continue
            if best is None or d < best_d:
                best, best_d, best_gap = root, d, gap

        if best is None:
            merged[tid] = list(recs)
            members[tid] = [tid]
        else:
            merged[best].extend(recs)
            members[best].append(tid)
            print(f"연결: {best} ← {tid}  (공백 {best_gap}프레임, 거리 {best_d:.3f})")

    print("\n=== 이어붙인 결과 ===")
    for root, recs in merged.items():
        cnt = Counter(rec["cls"] for rec in recs)
        print(f"ID {root:>3} | 프레임 {recs[0]['frame']:>3}~{recs[-1]['frame']:>3} "
            f"| 조각 {members[root]} | {dict(cnt)}")

    data["tracks"] = merged
    data["stitch"] = {"max_gap": MAX_GAP, "max_dist": MAX_DIST, 
                    "static_speed": STATIC_SPEED, "static_dist": STATIC_DIST, 
                    "members": members}
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"저장: {out_path}")
    return out_path

if __name__ == "__main__":
    run()