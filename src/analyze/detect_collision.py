import os
import json
import math
from itertools import combinations
from statistics import median

CONTACT_MIN = 0.3
DEPTH_TOL = 0.05
HOLD = 3
SPEED_WIN = 5
REF_WIN = 10
MOVING_SPEED = 0.02
STOP_RATIO = 0.4
STOP_WITHIN = 20

def run(out_dir="outputs"):

    in_path = os.path.join(out_dir, "tracks_final.json")
    out_path = os.path.join(out_dir, "collision.json")

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)
    fps = data["fps"]
    tracks = data["tracks"]

    by_tf = {tid: {r["frame"]: r for r in tr["frames"]} for tid, tr in tracks.items()}

    def area(b):
        return b[2] * b[3]

    def inter(a, b):
        x1, y1 = max(a[0], b[0]), max(a[1], b[1])
        x2, y2 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
        return max(0, x2 - x1,) * max(0, y2 - y1)

    def contact(a, b):
        m = min(area(a), area(b))
        return inter(a, b) / m if m > 0 else 0.0

    def speed(tid, f):
        recs = by_tf[tid]
        if f not in recs or f - SPEED_WIN not in recs:
            return None
        p, q = recs[f]["pos"], recs[f - SPEED_WIN]["pos"]
        return round(math.hypot(p[0] - q[0], p[1] - q[1]) / (SPEED_WIN / fps), 3)

    def approach_speed(tid, f0):
        vals = [s for f in range(f0 - REF_WIN, f0 + 1) if (s := speed(tid, f)) is not None]
        return median(vals) if vals else None

    def find_stop(tid, f0, ref):
        run = 0
        for f in range(f0, f0 + STOP_WITHIN + 1):
            s = speed(tid, f)
            if s is not None and s <= ref * STOP_RATIO:
                run += 1
                if run == HOLD:
                    return f - HOLD + 1
            else:
                run = 0
        return None

    events = []
    for a, b in combinations(sorted(tracks, key=int), 2):
        if not (tracks[a]["moving"] or tracks[b]["moving"]): 
            continue

        common = sorted(set(by_tf[a]) & set(by_tf[b]))
        was_apart = False
        run, run_start = 0, None
        for f in common:
            ra, rb = by_tf[a][f], by_tf[b][f]
            touching = contact(ra["bbox"], rb["bbox"]) >= CONTACT_MIN and abs(ra["pos"][1] - rb["pos"][1]) <= DEPTH_TOL

            if not touching:
                was_apart = True
                run = 0
                continue
            if not was_apart:
                continue

            if run == 0:
                run_start = f
            run += 1
            if run < HOLD:
                continue

            f0 = run_start
            ref = {t: approach_speed(t, f0) for t in (a, b)}
            stop = {t: (find_stop(t, f0, ref[t]) if ref[t] is not None and ref[t] >= MOVING_SPEED else None)
                    for t in (a, b)}
            if not any(stop.values()):
                print(f"후보 기가: {a} <-> {b} 프레임 {f0} (정지 없음)")
                run = 0
                continue
            
            r0a, r0b = by_tf[a][f0], by_tf[b][f0]
            events.append({
                "type": "collision",
                "frame": f0,
                "t": round(f0 / fps, 3),
                "a": a, "b": b,
                "cls": {a: tracks[a]["cls"], b: tracks[b]["cls"]},
                "pos": [round((r0a["pos"][0] + r0b["pos"][0]) / 2, 4),
                        round((r0a["pos"][1] + r0b["pos"][1]) / 2, 4)],
                "contact": round(contact(r0a["bbox"], r0b["bbox"]), 3),
                "approach_speed": {t: (round(v, 3) if v is not None else None) for t, v in ref.items()},
                "stop_frame": stop,
                "confirmed": True,
                "interp": bool(r0a.get("interp") or r0b.get("interp")),
            })
            break

    print("=== 충돌 ===")
    if not events:
        print("검출된 충돌 없음")
    for e in events:
        a, b = e["a"], e["b"]
        print(f"접촉 시작 프레임 {e['frame']} ({e['t']}초) | {a}({e['cls'][a]}) <-> {b}({e['cls'][b]}) "
            f"| 접촉 {e['contact']} | 위치 {e['pos']}")
        print(f"   접근 속도 {e['approach_speed']} | 정지 프레임 {e['stop_frame']}")

    out = {
        "schema_version": "0.2",
        "source": data["source"],
        "video": data["video"],
        "params": {"contact_min": CONTACT_MIN, "depth_tol": DEPTH_TOL, "hold": HOLD, 
                "speed_win": SPEED_WIN, "ref_win": REF_WIN, "moving_speed": MOVING_SPEED,
                "stop_ratio": STOP_RATIO, "stop_within": STOP_WITHIN},
        "events": events,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {out_path}")

if __name__ == "__main__":
    run()