import os
import sys
import json
import cv2
import numpy as np

MIN_SEG = 3  # 이보다 짧은 영역 구간은 경계 근처 흔들림으로 보고 앞 구간에 흡수


def poly(pts):
    return np.array(pts, np.float32)

def inside(pt, p):
    return cv2.pointPolygonTest(p, (float(pt[0]), float(pt[1])), False) >= 0

def zone_of(pt, zones, roi):
    if not inside(pt, roi):
        return "out_of_roi"
    for zid, p in zones:
        if inside(pt, p):
            return zid
    return "unknown"

def segments(frames, zones, roi):
    raw = []
    for r in frames:
        z = zone_of(r["pos"], zones, roi)
        if raw and raw[-1]["zone"] == z:
            raw[-1]["end"] = r["frame"]
        else:
            raw.append({"zone": z, "start": r["frame"], "end": r["frame"]})

    cleaned = []
    for s in raw:
        length = s["end"] - s["start"] + 1
        if cleaned and (length < MIN_SEG or cleaned[-1]["zone"] == s["zone"]):
            cleaned[-1]["end"] = s["end"]
        else:
            cleaned.append(dict(s))
    return cleaned

def run(scene_path, out_dir="outputs"):
    tracks_path = os.path.join(out_dir, "tracks_final.json")
    coll_path = os.path.join(out_dir, "collision.json")
    out_path = os.path.join(out_dir, "zones.json")

    with open(tracks_path, encoding="utf-8") as f:
        data = json.load(f)
    with open(scene_path, encoding="utf-8") as f:
        scene = json.load(f)
    with open(coll_path, encoding="utf-8") as f:
        coll = json.load(f)
    fps = data["fps"]
    
    tracks = data["tracks"]
    zones = [(z["id"], poly(z["polygon"])) for z in scene["zones"]]
    roi = poly(scene["roi"])

    timelines, events = {}, []
    for tid, tr in tracks.items():
        if not tr["moving"]:
            continue
        segs = segments(tr["frames"], zones, roi)
        timelines[tid] = {"cls": tr["cls"], "segments": segs}
        for prev, cur in zip(segs, segs[1:]):
            events.append(
                {
                    "type": "enter_zone",
                    "track": tid,
                    "from": prev["zone"],
                    "zone": cur["zone"],
                    "frame": cur["start"],
                    "t": round(cur["start"] / fps, 3),
                }
            )

    collisions = []
    for e in coll["events"]:
        f0 = e["frame"]
        parties = {}
        for t in (e["a"], e["b"]):
            rec = next((r for r in tracks[t]["frames"] if r["frame"] == f0), None)
            parties[t] = zone_of(rec["pos"], zones, roi) if rec else "unknown"
        collisions.append(
            {
                "frame": f0,
                "a": e["a"],
                "b": e["b"],
                "zone": zone_of(e["pos"], zones, roi),
                "party_zones": parties,
            }
        )

    print("=== 영역 타임라인 ===")
    for tid, tl in timelines.items():
        path = " → ".join(
            f"{s['zone']}({s['start']}~{s['end']})" for s in tl["segments"]
        )
        print(f"ID {tid:>3} {tl['cls']:<12} | {path}")
    print("\n=== 영역 이동 이벤트 ===")
    for ev in events:
        print(
            f"프레임 {ev['frame']:>3} | ID {ev['track']} : {ev['from']} → {ev['zone']}"
        )
    print("\n=== 충돌 지점 ===")
    for c in collisions:
        print(
            f"프레임 {c['frame']} | {c['a']} ↔ {c['b']} | 충돌 위치 {c['zone']} | 당사자 위치 {c['party_zones']}"
        )

    out = {
        "schema_version": "0.2",
        "video": data["video"],
        "scene": scene_path,
        "road_type": scene.get("road_type", "unknown"),
        "params": {"min_seg": MIN_SEG},
        "timelines": timelines,
        "events": events,
        "collisions": collisions,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {out_path}")
    return out_path


if __name__ == "__main__":
    scene_path = sys.argv[1] if len(sys.argv) > 1 else "scenes/sample.json"
    run(scene_path)
