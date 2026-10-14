import argparse
import time
from src.analyze import (track_video, stitch_tracks,
                         finalize_tracks, detect_collision, zone_events, build_facts)

def main():
    ap = argparse.ArgumentParser(description="파이프라인: 영상 + scene.json -> facts.json")
    ap.add_argument("video", help="분석할 영상 경로")
    ap.add_argument("scene", help="scene.json 경로")
    ap.add_argument("--out", default="outputs", help="결과 폴더 (기본 outputs)")
    ap.add_argument("--save-video", action="store_true", help="추적 확인용 영상도 저장")
    ap.add_argument("--skip-track", action="store_true", help="기존 tracks.json 재사용 (YOLO 생략)")
    args = ap.parse_args()

    stages = []
    if not args.skip_track:
        stages.append(("tracks", lambda: track_video.run(args.video, args.out, args.save_video)))
    stages += [
        ("stitch", lambda: stitch_tracks.run(args.out)),
        ("finalize", lambda: finalize_tracks.run(args.out)),
        ("collision", lambda: detect_collision.run(args.out)),
        ("zones", lambda: zone_events.run(args.scene, args.out)),
        ("facts", lambda: build_facts.run(args.out)),
    ]

    for name, fn in stages:
        print(f"\n-> [{name}]")
        t0 = time.perf_counter()
        fn()
        print(f"  ({time.perf_counter() - t0:.1f}초)")

    print(f"\n완료: {args.out}/facts.json")

if __name__ == "__main__":
    main()