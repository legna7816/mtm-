# CCTV 교통사고 과실비율 분석 — A 파트 (영상 분석)

CCTV 사고 영상과 장면 정의(scene.json)를 입력받아 사고 사실을 정리한 `facts.json`을 만든다.
facts.json은 B 파트 규칙 엔진(rules.json → result.json)의 입력이다.

## 파이프라인

```
영상 + scenes/*.json
 → track_video       YOLO 탐지 + ByteTrack 추적 + 화면 전환(줌인 등) 감지 → tracks.json
 → stitch_tracks     끊긴 ID 이어붙이기 (공백 프레임·거리 기준)       → tracks_stitched.json
 → finalize_tracks   클래스 확정, 정지/이동 판정, 빈 프레임 보간      → tracks_final.json
 → detect_collision  접촉 + 직후 속도 급감으로 충돌 확정               → collision.json
 → zone_events       객체별 영역 타임라인, 충돌 위치 영역               → zones.json
 → build_facts       당사자·출발 영역·진행 방향·사건 순서 정리          → facts.json
```

무거운 YOLO는 첫 단계에서 한 번만 돌리고, 이후 단계는 JSON만 읽는다.

## 폴더 구조

```
run_a.py            A 파이프라인 전체 실행
src/analyze/        파이프라인 단계 (각 파일은 단독 실행도 가능)
tools/              확인·시각화용 (결과 영상, 격자, 영역 오버레이 등)
scenes/             영상별 장면 정의 (ROI, 영역 다각형, 도로 종류)
data/videos/        입력 영상 (git 제외, AI Hub 원본)
outputs/            결과 JSON·영상 (git 제외)
```

## 설치 (WSL Ubuntu, CPU)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

- OpenCV는 `opencv-python-headless`만 설치한다. `opencv-python`과 같이 깔면 충돌한다.
- `yolov8n.pt`는 첫 실행 때 자동으로 내려받는다.

## 실행

```bash
# 전체 실행
python run_a.py data/videos/sample.mp4 scenes/sample.json

# YOLO 단계 생략 (기존 tracks.json 재사용, 뒤 단계 기준값 실험용)
python run_a.py data/videos/sample.mp4 scenes/sample.json --skip-track

# 추적 확인용 영상도 저장
python run_a.py data/videos/sample.mp4 scenes/sample.json --save-video

# 결과 폴더 지정
python run_a.py data/videos/sample.mp4 scenes/sample.json --out outputs/sample

# 사용법
python run_a.py -h
```

단계 하나만 다시 돌릴 때 (루트에서 실행):

```bash
python src/analyze/detect_collision.py
python src/analyze/zone_events.py scenes/sample.json
```

확인 도구 (루트에서 실행):

```bash
python tools/render_tracks.py   # tracks_final.json → 추적 결과 영상
python tools/make_grid.py       # 좌표 격자 이미지 (scene.json 작성용)
python tools/draw_scene.py      # scene.json 영역을 첫 프레임에 겹쳐 그리기
```

## 새 영상 추가하기

1. 영상을 `data/videos/`에 넣는다. 압축본이 아니라 **원본 해상도**를 쓴다 (압축본은 탐지 결과가 달라진다).
2. `tools/make_grid.py`로 격자 이미지를 만들고, 좌표를 읽어 `scenes/<이름>.json`을 작성한다.
3. `tools/draw_scene.py`로 영역이 맞게 그려졌는지 확인한다.
4. `run_a.py`로 실행한다.

## 좌표·데이터 규칙

- 좌표는 영상 크기 기준 0~1로 정규화한다.
- `bbox` = `[x, y, w, h]` (왼쪽 위 기준), `pos` = 박스 아래 중앙 (바퀴 위치).
- 시간은 `frame`과 `t`(초)를 함께 기록한다.
- 판단할 수 없는 값은 `"unknown"`, 보간한 값은 `interp: true`로 표시한다.
- 클래스: `vehicle`, `two_wheeler`, `bicycle`, `pedestrian`, `traffic_light`

## facts.json 주요 필드

| 필드 | 내용 |
|---|---|
| `road_type` | 도로 종류 (예: `no_center_line`) |
| `collision` | 충돌 프레임·시간·위치 영역 |
| `parties.{id}.cls` | 당사자 종류 |
| `parties.{id}.origin_zone` | 처음 나타난 영역 |
| `parties.{id}.enter_road` | 도로 진입 시점 |
| `parties.{id}.movement` | `straight` / `left_turn` / `right_turn` / `u_turn` / `unknown` |
| `parties.{id}.approach_speed` | 충돌 직전 속도 (정규화 좌표/프레임) |
| `parties.{id}.stop_frame` | 충돌 후 정지 프레임 |
| `events` | 등장 → 영역 이동 → 충돌 → 정지 시간순 목록 |

## 알려진 한계

- 사전학습 YOLO(COCO)가 위에서 본 오토바이를 car/truck으로 자주 분류한다. 여러 프레임의 판정을 모아 보정하지만, 학습 모델로 바꿀 예정이다.
- 천천히 움직이거나 가려진 차량은 진행 방향을 판단하지 못하고 `unknown`으로 남긴다.
- 기준값(이어붙이기 거리, 접촉 비율 등)은 샘플 영상 1개로 정했다. 다른 영상에서 검증이 필요하다.
- 영상 끝에 줌인 등 화면 전환이 있으면 그 지점에서 분석을 멈춘다.
