import argparse
import cv2
import csv
from collections import defaultdict, deque
from pathlib import Path

# 팀원이 만든 함수 불러오기
from adaptive_cctv.tracking import TrackCar, findtraj, findspeed


def visualize(video_path, tracking_data, output_path, focus_id=None):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError("영상을 열 수 없습니다.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps <= 0:
        cap.release()
        raise ValueError("FPS 정보를 확인할 수 없습니다.")

    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height)
    )

    if not writer.isOpened():
        cap.release()
        raise RuntimeError("영상 저장에 실패했습니다.")

    # 프레임 번호별 검출 데이터 정리
    frame_map = defaultdict(list)

    for frame_data in tracking_data:
        for car in frame_data:
            frame_map[car["frame"]].append(car)

    # 차량별 최근 이동 경로
    paths = defaultdict(deque)
    last_boxes = {}
    last_seen = {}

    frame_index = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # 현재 프레임에서 확인한 차량 정보
        for car in frame_map.get(frame_index, []):
            tid = car["track_id"]
            cx, cy = map(int, car["center"])

            # 추적이 오래 끊겼다면 선을 연결하지 않음
            if paths[tid]:
                last_frame = paths[tid][-1][0]

                if frame_index - last_frame > fps * 0.5:
                    paths[tid].clear()

            paths[tid].append((frame_index, (cx, cy)))
            last_boxes[tid] = car["bbox"]
            last_seen[tid] = frame_index

        # 차량별 경로와 박스 표시
        for tid in list(paths.keys()):
            # 1초 이상 확인되지 않으면 기록 정리
            if frame_index - last_seen[tid] > fps:
                del paths[tid]
                del last_boxes[tid]
                del last_seen[tid]
                continue

            if focus_id is not None and tid != focus_id:
                continue

            # 최근 3초 경로만 표시
            while (
                paths[tid]
                and frame_index - paths[tid][0][0] > fps * 3
            ):
                paths[tid].popleft()

            # 차량마다 다른 색상
            color = (
                70 + (tid * 37) % 180,
                70 + (tid * 73) % 180,
                70 + (tid * 109) % 180
            )

            points = [p for _, p in paths[tid]]

            # 이동 경로
            for i in range(1, len(points)):
                cv2.line(
                    frame,
                    points[i - 1],
                    points[i],
                    color,
                    3
                )

            # 마지막 검출 위치가 최근 0.3초 이내면 표시
            if frame_index - last_seen[tid] <= fps * 0.3:
                x1, y1, x2, y2 = map(int, last_boxes[tid])

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2
                )

                cv2.putText(
                    frame,
                    f"ID {tid}",
                    (x1, max(25, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2
                )

        writer.write(frame)
        frame_index += 1

    cap.release()
    writer.release()
    print(f"시각화 영상 저장 완료: {output_path}")


def save_csv(tracking_data, csv_path):
    with open(
        csv_path, "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "frame",
            "time",
            "track_id",
            "center_x",
            "center_y",
            "confidence"
        ])

        for frame_data in tracking_data:
            for car in frame_data:
                writer.writerow([
                    car["frame"],
                    car["time"],
                    car["track_id"],
                    car["center"][0],
                    car["center"][1],
                    car["confidence"]
                ])

    print(f"좌표 CSV 저장 완료: {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video", help="path to the input video")
    parser.add_argument(
        "--output",
        help="path of the visualized video "
        "(default: <video stem>_tracking_visualized.mp4)"
    )
    parser.add_argument(
        "--csv",
        help="path of the tracking CSV "
        "(default: <video stem>_tracking_data.csv)"
    )
    parser.add_argument(
        "--focus-id",
        type=int,
        help="draw only this track ID (default: all)"
    )
    args = parser.parse_args()
    stem = Path(args.video).stem
    output_path = args.output or f"{stem}_tracking_visualized.mp4"
    csv_path = args.csv or f"{stem}_tracking_data.csv"

    all_data = []
    previous_chunk = []

    # 팀원이 만든 5초 단위 추적 함수 활용
    for chunk_data in TrackCar(
        args.video,
        chunk_seconds=5
    ):
        combined_data = previous_chunk + chunk_data
        trajectories = findtraj(combined_data)
        speed_data = findspeed(trajectories)

        print(
            f"청크 분석 완료 / 차량 ID 수: "
            f"{len(trajectories)}"
        )

        all_data.extend(chunk_data)
        previous_chunk = chunk_data

    # 전체 경로 데이터
    trajectories = findtraj(all_data)
    speed_data = findspeed(trajectories)
    print(f"전체 추적 ID 수: {len(trajectories)}")

    # 결과 저장
    save_csv(all_data, csv_path)
    visualize(args.video, all_data, output_path, args.focus_id)
    print("모든 작업 완료!")
