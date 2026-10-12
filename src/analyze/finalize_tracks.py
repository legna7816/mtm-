import json
import math
from collections import Counter

IN = "outputs/tracks_stitched.json"
OUT = "outputs/tracks_final.json"
MIN_FRAMES = 15    # 이보다 짧은 궤적은 잡음으로 보고 제외
TW_MIN = 3         # motorcycle/bicycle이 이 횟수 이상이면 two_wheeler
MOVE_MIN = 0.03    # 시작점에서 최대 이동 거리가 이보다 작으면 정지 물체

NAME_MAP = {
    "car": "vehicle", "truck": "vehicle", "bus": "vehicle",
    "motorcycle": "two_wheeler",
    "bicycle": "bicycle",
    "person": "pedestrian",
    "traffic light": "traffic_light",
}

with open(IN, encoding="utf-8") as f:
    data = json.load(f)


def decide_cls(votes):
    moto = votes.get("motorcycle", 0)
    bike = votes.get("bicycle", 0)
    if moto >= TW_MIN or bike >= TW_MIN:
        return "two_wheeler" if moto >= bike else "bicycle"
    major = votes.most_common(1)[0][0]
    return NAME_MAP.get(major, "unknown")


def max_move(recs):
    x0, y0 = recs[0]["pos"]
    return max(math.hypot(r["pos"][0] - x0, r["pos"][1] - y0) for r in recs)

def interpolate(frames, fps):
    out = [frames[0]]
    for prev, cur in zip(frames, frames[1:]):
        gap = cur["frame"] - prev["frame"]
        for k in range(1, gap):
            a = k / gap
            f = prev["frame"] + k
            out.append({
                "frame": f,
                "t": round(f / fps, 3),
                "bbox": [round(p + (c - p) * a, 4) for p, c in zip(prev["bbox"], cur["bbox"])],
                "pos": [round(p + (c - p) * a, 4) for p, c in zip(prev["pos"], cur["pos"])],
                "conf": None,
                "yolo_cls": None,
                "interp": True,
            })
        out.append(cur)
    return out


final, dropped = {}, {}
for tid, recs in data["tracks"].items():
    if len(recs) < MIN_FRAMES:
        dropped[tid] = f"short ({len(recs)} frames)"
        continue

    votes = Counter(r["cls"] for r in recs)
    move = max_move(recs)
    final[tid] = {
        "cls": decide_cls(votes),
        "cls_votes": dict(votes),
        "moving": move >= MOVE_MIN,
        "max_move": round(move, 3),
        "members": data["stitch"]["members"][tid],
        "frames": interpolate([
            {"frame": r["frame"], "t": r["t"], "bbox": r["bbox"],
             "pos": r["pos"], "conf": r["conf"], "yolo_cls": r["cls"], "interp": False}
            for r in recs
        ], data["fps"]),
    }

print("=== 최종 궤적 ===")
for tid, tr in final.items():
    fr = tr["frames"]
    print(f"ID {tid:>3} | {tr['cls']:<12} | {'이동' if tr['moving'] else '정지'} "
          f"(최대 {tr['max_move']:.3f}) | 프레임 {fr[0]['frame']:>3}~{fr[-1]['frame']:>3} | {tr['cls_votes']}")
print("\n=== 제외 ===")
for tid, why in dropped.items():
    print(f"ID {tid:>3} | {why}")

out = {
    "schema_version": "0.2",
    "source": "yolo",
    "video": data["video"],
    "fps": data["fps"],
    "detector": data["detector"],
    "tracker": data["tracker"],
    "scene_cut_frame": data.get("scene_cut_frame"),
    "params": {"min_frames": MIN_FRAMES, "tw_min": TW_MIN, "move_min": MOVE_MIN,
               "stitch": {"max_gap": data["stitch"]["max_gap"], "max_dist": data["stitch"]["max_dist"]}},
    "tracks": final,
    "dropped": dropped,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"\n저장: {OUT}")