import cv2
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
frame = cv2.imread("outputs/first_frame.jpg")

results = model(frame, conf=0.4)
r = results[0]
h_img, w_img = frame.shape[:2]

KEEP = ["car", "truck", "bus", "motorcycle", "bicycle", "person", "traffic light"]

for box in r.boxes:
    
    cls_id = int(box.cls[0])
    name = model.names[cls_id]
    conf = float(box.conf[0])
    if name not in KEEP or conf < 0.4:
        continue
    x1, y1, x2, y2 = box.xyxy[0].tolist()

    x = x1 / w_img
    y = y1 / h_img
    w = (x2 - x1) / w_img
    h = (y2 - y1) / h_img

    print(f"{name:12s} {conf:.2f} ({x1:.0f}, {y1:.0f}) ~ ({x2:.0f}, {y2:.0f})")
    print(f"  -> [x, y, w, h] = [{x:.2f}, {y:.2f}, {w:.2f}, {h:.2f}]")

cv2.imwrite("outputs/first_frame_det.jpg", r.plot())