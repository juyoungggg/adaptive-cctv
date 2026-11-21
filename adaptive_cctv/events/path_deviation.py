from ultralytics import YOLO
import cv2

# 차량 클래스 정의
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# ==========================================
#  좌표가 갓길/도로 외곽인지 판별
# ==========================================
def is_in_shoulder(x, y, image_width=1280, image_height=720):
    """
    예시: 화면의 좌측 끝(예: x < 200)이나 우측 끝 영역을 갓길로 가정
    실제 CCTV 영상의 픽셀 좌표계에 맞춰 범위를 수정 필요ㅏㅏ
    """
    if x < 200 or x > (image_width - 200):
        return True
    return False

# ==========================================
# 차선 변경
# ==========================================
def get_lane_id(x, y, image_width=1280):
    """
    예시: 화면 가로 폭을 기준으로 3개 차로로 단순 분할
    """
    if x < 400:
        return 1  # 1차로
    elif x < 800:
        return 2  # 2차로 (중간 차로)
    else:
        return 3  # 3차로


# ==========================================
# 차선 이탈 이벤트 판별 함수
# ==========================================
def check_lane_departure_events(trajectory):
    """
    한 차량의 시간별 위치(trajectory)를 받아
    1) 갓길 1초 이상 체류
    2) 4초 내 차선 변경 2회 이상 + 중간 차로 체류 1.5초 이하
    조건 중 하나라도 만족하면 True (이벤트 발생) 반환
    """
    shoulder_duration = 0.0  # 갓길 누적 체류 시간
    lane_history = []        # 차선 변경 기록 [(time, lane_id), ...]

    for i, point in enumerate(trajectory):
        current_time = point["time"]
        x, y = point["center"]

        # --- [조건 1] 갓길 또는 도로 외곽에 1초 이상 위치 ---
        if is_in_shoulder(x, y):
            shoulder_duration += 0.1  # 0.1초 간격 데이터 가정
            if shoulder_duration >= 1.0:
                return True  # 갓길 이탈 이벤트 확정!
        else:
            shoulder_duration = 0.0  # 갓길 벗어나면 리셋

        # --- [조건 2] 차선 변경 감지 및 기록 ---
        current_lane = get_lane_id(x, y)

        if not lane_history or lane_history[-1][1] != current_lane:
            lane_history.append((current_time, current_lane))

    # --- [조건 2 심화] 지그재그 주행 검사 (4초 내 차선 변경 2회 이상 + 중간 차로 1.5초 이하) ---
    # 기록된 차선 변경 내역을 순회하며 4초 윈도우 탐색
    for i in range(len(lane_history) - 2):
        start_time = lane_history[i][0]
        end_time = lane_history[i + 2][0]  # 2번 바뀌었을 때의 시간

        # 4초 이내에 차선 변경이 2회 일어났는지 확인
        if (end_time - start_time) <= 4.0:
            mid_lane_entry = lane_history[i + 1][0]
            mid_lane_exit = lane_history[i + 2][0]
            mid_lane_duration = mid_lane_exit - mid_lane_entry

            # 중간 차로 체류 시간이 1.5초 이하인지 확인
            if mid_lane_duration <= 1.5:
                return True  # 지그재그 주행 이벤트 확정!

    return False


# ==========================================
# [전체 파이프라인 함수] 영상 입력 ➔ 추적 ➔ 판별 ➔ O/X 출력
# ==========================================
def EvaluateVideoAnomaly(video_path, interval=0.1, model_path="yolo26n.pt", tracker="bytetrack.yaml"):
    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, round(fps * interval))

    tracking_data = []
    frame_index = 0

    print("1단계: YOLO 및 ByteTrack으로 차량 추적 데이터 추출 중...")
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
                conf=0.4,
                imgsz=1280,
                verbose=False
            )[0]

            frame_data = []
            if result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                ids = result.boxes.id.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()

                for box, track_id, cls, conf in zip(boxes, ids, classes, confs):
                    x1, y1, x2, y2 = box
                    frame_data.append({
                        "frame": frame_index,
                        "time": frame_index / fps,
                        "track_id": int(track_id),
                        "class_id": int(cls),
                        "class_name": VEHICLE_CLASSES[int(cls)],
                        "confidence": float(conf),
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "center": [float((x1 + x2) / 2), float((y1 + y2) / 2)]
                    })
            tracking_data.append(frame_data)

        frame_index += 1

    cap.release()

    print("2단계: 차량 ID별 궤적 데이터 재구성 중...")
    vehicle_trajectories = {}
    for frame_data in tracking_data:
        for obj in frame_data:
            track_id = obj["track_id"]
            if track_id not in vehicle_trajectories:
                vehicle_trajectories[track_id] = []
            vehicle_trajectories[track_id].append({
                "time": obj["time"],
                "center": obj["center"]
            })

    print("3단계: 차선 이탈 및 지그재그 이벤트 판별 중...")
    # 차량별로 조건 검사 수행
    for track_id, trajectory in vehicle_trajectories.items():
        if check_lane_departure_events(trajectory):
            print(f"-> [탐지] 차량 ID {track_id}에서 이상 상황 조건 충족!")
            return "O"  # 이상 상황 감지됨

    # 모든 차량이 조건에 안 걸리면 정상
    return "X"
