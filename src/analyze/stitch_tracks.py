import json
import math
from collections import Counter

IN = "outputs/tracks.json"
OUT = "outputs/tracks_stitched.json"
MAX_GAP = 20      # 이어붙일 수 있는 최대 공백 (프레임)
MAX_DIST = 0.2   # 앞 조각 끝 ~ 뒤 조각 시작 최대 거리 (정규화 좌표)

with open(IN, encoding="utf-8") as f:
    data = json.load(f)
tracks = data["tracks"]


def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


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
        if d > MAX_DIST:
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
data["stitch"] = {"max_gap": MAX_GAP, "max_dist": MAX_DIST, "members": members}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(f"저장: {OUT}")