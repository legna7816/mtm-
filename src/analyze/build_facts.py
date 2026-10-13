import json
import math

TRACKS = "outputs/tracks_final.json"
COLL = "outputs/collision.json"
ZONES = "outputs/zones.json"
OUT = "outputs/facts.json"
WIN = 15          # 진행 방향을 잴 프레임 수 (약 1초)
TURN_DEG = 30     # 진행 방향이 이 각도 이상 바뀌면 회전으로 판단
MIN_DISP = 0.02   # 1초 동안 이동 거리가 이보다 작으면 방향을 판단하지 않음

with open(TRACKS, encoding="utf-8") as f:
    data = json.load(f)
with open(COLL, encoding="utf-8") as f:
    coll = json.load(f)
with open(ZONES, encoding="utf-8") as f:
    zones = json.load(f)

fps = data["fps"]
tracks = data["tracks"]
by_tf = {tid: {r["frame"]: r for r in tr["frames"]} for tid, tr in tracks.items()}

if not coll["events"]:
    raise SystemExit("충돌 이벤트가 없어서 facts를 만들 수 없어요")


def pos_at(tid, f):                                  # 궤적 범위 밖이면 가장 가까운 끝으로 맞춤
    recs = by_tf[tid]
    f = max(min(recs), min(max(recs), f))
    return recs[f]["pos"]


def heading(tid, f1, f2):                            # f1 → f2 동안의 이동 벡터
    p, q = pos_at(tid, f1), pos_at(tid, f2)
    return (q[0] - p[0], q[1] - p[1])


def turn_angle(h1, h2):                              # h1 → h2 회전 각도 (+: 시계 방향 = 우회전)
    cross = h1[0] * h2[1] - h1[1] * h2[0]
    dot = h1[0] * h2[0] + h1[1] * h2[1]
    return math.degrees(math.atan2(cross, dot))


def movement(deg):
    if abs(deg) >= 150:
        return "u_turn"
    if deg >= TURN_DEG:
        return "right_turn"
    if deg <= -TURN_DEG:
        return "left_turn"
    return "straight"


def screen_dir(h):                                   # 화면 기준 대략적인 방향
    if abs(h[1]) >= abs(h[0]):
        return "away_from_camera" if h[1] < 0 else "toward_camera"
    return "rightward" if h[0] > 0 else "leftward"


c = coll["events"][0]                                # 첫 번째 충돌
f0 = c["frame"]
zc = next(z for z in zones["collisions"] if z["frame"] == f0)

parties = {}
for tid in (c["a"], c["b"]):
    tr = tracks[tid]
    first = tr["frames"][0]["frame"]
    segs = zones["timelines"][tid]["segments"]
    origin = next((s["zone"] for s in segs if s["zone"] != "out_of_roi"), "unknown")
    enter = next((e for e in zones["events"] if e["track"] == tid and e["zone"] == "road"), None)

    h_start = heading(tid, first, first + WIN)
    h_end = heading(tid, f0 - WIN, f0)
    deg = turn_angle(h_start, h_end)

    d_start, d_end = math.hypot(*h_start), math.hypot(*h_end)
    if d_start < MIN_DISP or d_end < MIN_DISP:
        mv, turn = "unknown", None
    else:
        mv, turn = movement(deg), round(deg, 1)

    parties[tid] = {
        "cls": tr["cls"],
        "first_frame": first,
        "origin_zone": origin,
        "enter_road": {"frame": enter["frame"], "t": enter["t"]} if enter else None,
        "zone_at_collision": zc["party_zones"][tid],
        "movement": mv,
        "turn_deg": turn,
        "disp_start": round(d_start, 4),
        "disp_before_collision": round(d_end, 4),
        "heading_start": [round(v, 4) for v in h_start],
        "heading_before_collision": [round(v, 4) for v in h_end],
        "direction_before_collision": screen_dir(h_end) if d_end >= MIN_DISP else "unknown",
        "approach_speed": c["approach_speed"][tid],
        "stop_frame": c["stop_frame"][tid],
    }

events = []
for tid, p in parties.items():
    events.append({"frame": p["first_frame"], "t": round(p["first_frame"] / fps, 3),
                   "type": "appear", "track": tid, "zone": p["origin_zone"]})
for e in zones["events"]:
    if e["track"] in parties:
        events.append({"frame": e["frame"], "t": e["t"], "type": "enter_zone",
                       "track": e["track"], "from": e["from"], "zone": e["zone"]})
events.append({"frame": f0, "t": c["t"], "type": "collision",
               "a": c["a"], "b": c["b"], "zone": zc["zone"]})
for tid, sf in c["stop_frame"].items():
    if sf is not None:
        events.append({"frame": sf, "t": round(sf / fps, 3), "type": "stop", "track": tid})
events.sort(key=lambda e: e["frame"])

facts = {
    "schema_version": "0.2",
    "source": data["source"],
    "video": data["video"],
    "scene": zones["scene"],
    "road_type": zones["road_type"],
    "fps": fps,
    "collision": {"frame": f0, "t": c["t"], "a": c["a"], "b": c["b"],
                  "zone": zc["zone"], "pos": c["pos"], "contact": c["contact"],
                  "interp": c["interp"]},
    "parties": parties,
    "events": events,
    "params": {"win": WIN, "turn_deg": TURN_DEG, "min_disp": MIN_DISP,
               "tracks": data["params"], "collision": coll["params"], "zones": zones["params"]},
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(facts, f, ensure_ascii=False, indent=1)

print(f"도로 종류: {facts['road_type']}")
print(f"충돌: 프레임 {f0} ({c['t']}초), 위치 {zc['zone']}\n")
for tid, p in parties.items():
    print(f"ID {tid} ({p['cls']})")
    print(f"  출발 영역: {p['origin_zone']}  | 도로 진입: {p['enter_road']}")
    print(f"  진행: {p['movement']} (회전 {p['turn_deg']}도) | 충돌 직전 방향: {p['direction_before_collision']}")
    print(f"  처음 이동 {p['heading_start']} → 충돌 직전 이동 {p['heading_before_collision']}")
    print(f"  접근 속도 {p['approach_speed']} | 정지 프레임 {p['stop_frame']}\n")
print("=== 사건 순서 ===")
for e in events:
    print(f"  {e['t']:>6}초 (프레임 {e['frame']:>3}) | {e['type']} | "
          + ", ".join(f"{k}={v}" for k, v in e.items() if k not in ('frame', 't', 'type')))
print(f"\n저장: {OUT}")