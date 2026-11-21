import math
import statistics
from collections import defaultdict, deque


class EventDetector_SuddenStop:

    def __init__(self, ref_far=2.5, ref_near=0.6, now_win=0.5,
                 min_ref_speed=30.0,   # pixels/s 이보다 느리면 서행으로 간주함. 무시
                 drop_ratio=0.3,       # 현재속도 <= 직전속도 * 0.3 이면 급정차
                 cooldown=5.0,         # 같은 차량 중복 이벤트 억제(초)
                 min_samples=3,
                 max_gap=1.0):         # 트래킹 끊김 허용 한계(초)
        self.ref_far, self.ref_near, self.now_win = ref_far, ref_near, now_win
        self.min_ref_speed, self.drop_ratio = min_ref_speed, drop_ratio
        self.cooldown, self.min_samples, self.max_gap = cooldown, min_samples, max_gap
        self.speeds = defaultdict(lambda: deque())   # id -> deque[(t, v)]
        self.last_pt = {}                            # id -> (t, x, y)
        self.last_event = {}                         # id -> t

    def _push(self, tid, p):
        t, (x, y) = p["time"], p["center"]
        prev = self.last_pt.get(tid)
        self.last_pt[tid] = (t, x, y)
        if prev is None:
            return None
        dt = t - prev[0]
        if dt <= 0 or dt > self.max_gap:      # ID 끊김 구간은 속도 계산 제외
            self.speeds[tid].clear()
            return None
        v = math.hypot(x - prev[1], y - prev[2]) / dt
        dq = self.speeds[tid]
        dq.append((t, v))
        while dq and dq[0][0] < t - self.ref_far - 0.5:
            dq.popleft()
        return t, v

    def _check(self, tid, t, center):
        dq = self.speeds[tid]
        ref = [v for s, v in dq if t - self.ref_far <= s <= t - self.ref_near]
        now = [v for s, v in dq if s > t - self.now_win]
        if len(ref) < self.min_samples or len(now) < self.min_samples:
            return None
        v_ref, v_now = statistics.median(ref), statistics.median(now)
        if v_ref < self.min_ref_speed or v_now > self.drop_ratio * v_ref:
            return None
        if t - self.last_event.get(tid, -1e9) < self.cooldown:
            return None
        self.last_event[tid] = t
        return {"type": "sudden_stop", "track_id": tid, "time": t,
                "v_before": v_ref, "v_after": v_now,
                "drop_ratio": v_now / v_ref, "center": center}

    def update(self, trajectories):
        # findtraj() 결과를 넣으면 이 청크에서 발생한 이벤트 리스트 반환
        events = []
        for tid, pts in trajectories.items():
            for p in sorted(pts, key=lambda q: q["time"]):
                if self._push(tid, p) is None:
                    continue
                ev = self._check(tid, p["time"], p["center"])
                if ev:
                    events.append(ev)
        return events


def events_to_intervals(events, pre=3.0, post=5.0, merge_gap=1.0):
    # 이벤트 -> 고화질 저장 구간 [(start, end)] 
    iv = sorted((max(0.0, e["time"] - pre), e["time"] + post) for e in events)
    merged = []
    for s, e in iv:
        if merged and s <= merged[-1][1] + merge_gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged
