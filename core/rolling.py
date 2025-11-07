import time, collections

class RollingBuffer:
    def __init__(self, pre_sec: int, post_sec: int):
        self.pre = pre_sec; self.post = post_sec
        self.buf = collections.deque()  # (ts, text)

    def add(self, text: str):
        now = time.time()
        self.buf.append((now, text))
        cutoff = now - (self.pre + self.post + 60)
        while self.buf and self.buf[0][0] < cutoff:
            self.buf.popleft()

    def window_text(self, center_ts: float):
        start = center_ts - self.pre; end = center_ts + self.post
        return " ".join(t for ts, t in self.buf if start <= ts <= end)