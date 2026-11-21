from ultralytics import YOLO
import cv2
import math


VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


def TrackCar(
    video_path,
    chunk_seconds=5,
    interval=0.1,
    model_path="yolo26n.pt",
    tracker="bytetrack.yaml"
):
    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)

    frame_interval = max(1, round(fps * interval))
    chunk_frames = max(1, round(fps * chunk_seconds))

    tracking_data = []
    frame_index = 0

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                break

            if frame_index % frame_interval == 0:

                result = model.track(
                    frame,
                    persist=True,
                    tracker=tracker,
                    classes=list(VEHICLE_CLASSES.keys()),
                    conf=0.2,
                    imgsz=1280,
                    verbose=False
                )[0]

                frame_data = []

                if result.boxes.id is not None:

                    boxes = result.boxes.xyxy.cpu().numpy()
                    ids = result.boxes.id.cpu().numpy()
                    classes = result.boxes.cls.cpu().numpy()
                    confs = result.boxes.conf.cpu().numpy()

                    for box, track_id, cls, conf in zip(
                        boxes, ids, classes, confs
                    ):
                        x1, y1, x2, y2 = box

                        frame_data.append({
                            "frame": frame_index,
                            "time": frame_index / fps,
                            "track_id": int(track_id),
                            "class_id": int(cls),
                            "class_name": VEHICLE_CLASSES[int(cls)],
                            "confidence": float(conf),
                            "bbox": [
                                float(x1), float(y1),
                                float(x2), float(y2)
                            ],
                            "center": [
                                float((x1 + x2) / 2),
                                float((y1 + y2) / 2)
                            ]
                        })

                tracking_data.append(frame_data)

            frame_index += 1

            # 5초 분량이 쌓이면 반환
            if frame_index % chunk_frames == 0:
                yield tracking_data
                tracking_data = []

        # 마지막에 5초 미만의 데이터가 남으면 반환
        if tracking_data:
            yield tracking_data
            
    finally:
        cap.release()


def findtraj(tracking_data):
    """
    Output:
        trajectories : 차량 ID별 시간순 중심 좌표
        ex)
        trajectories = {
        1: [
            {"frame": 0, "time": 0.0, "center": [100, 200]},
            {"frame": 3, "time": 0.1, "center": [110, 200]},
            {"frame": 6, "time": 0.2, "center": [120, 200]}
        ],

        2: [
            {"frame": 0, "time": 0.0, "center": [500, 300]},
            {"frame": 3, "time": 0.1, "center": [490, 300]},
            {"frame": 6, "time": 0.2, "center": [480, 300]}
        ]
    }
    """

    trajectories = {}

    for frame_data in tracking_data:
        for vehicle in frame_data:

            track_id = vehicle["track_id"]

            if track_id not in trajectories:
                trajectories[track_id] = []

            trajectories[track_id].append({
                "frame": vehicle["frame"],
                "time": vehicle["time"],
                "center": vehicle["center"]
            })

    return trajectories


def findspeed(trajectories):
    """
    Output:
        speed_data : 차량 ID별 시간순 픽셀 속도 (pixels/s)
        ex)
        speed_data = {
        1: [
            (0.1, 100.0),
            (0.2, 100.0),
            (0.3, 80.0)
        ],

        2: [
            (0.1, 50.0),
            (0.2, 45.0),
            (0.3, 30.0)
        ]
    }
    """

    speed_data = {}

    for track_id, points in trajectories.items():

        speeds = []

        for i in range(1, len(points)):

            p1 = points[i - 1]
            p2 = points[i]

            dt = p2["time"] - p1["time"]

            if dt <= 0:
                continue

            x1, y1 = p1["center"]
            x2, y2 = p2["center"]

            distance = math.hypot(x2 - x1, y2 - y1)

            speed = distance / dt

            speeds.append((p2["time"], speed))

        speed_data[track_id] = speeds

    return speed_data
