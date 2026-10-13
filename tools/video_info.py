import cv2

cap = cv2.VideoCapture("data/videos/sample.mp4")

print("열림:", cap.isOpened())

fps = cap.get(cv2.CAP_PROP_FPS)
count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
hegiht = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print("FPS:", fps)
print("프레임 수:", count)
print("해상도:", width, "x", hegiht)
print("길이(초):", count / fps)

ok, frame = cap.read()
if ok:
    cv2.imwrite("outputs/first_frame.jpg", frame)
cap.release()