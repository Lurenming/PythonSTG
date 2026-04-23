"""
UDP 后台监听线程

在独立 daemon 线程中绑定 UDP 端口，接收来自 NoneBot 的 JSON 包，
解析后压入线程安全的 Queue，供主线程每帧 poll()。
"""
import json
import socket
import threading
from queue import Empty, Queue

EMOJI_SET: frozenset[str] = frozenset(["😂", "😡", "💩", "😅"])


class UDPReceiver:
    """UDP 监听器（daemon 线程，主线程只需 poll() 取事件）。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9999) -> None:
        self.host = host
        self.port = port
        self._queue: Queue[dict] = Queue()
        self._thread: threading.Thread | None = None
        self._running = False
        self._sock: socket.socket | None = None

    # ── 生命周期 ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="emoji-udp"
        )
        self._thread.start()
        print(f"[emoji_danmaku] UDP 监听已启动 {self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    # ── 主线程接口 ────────────────────────────────────────────────────────────

    def poll(self) -> list[dict]:
        """取出本帧所有待处理事件，主线程调用，无锁安全。"""
        events: list[dict] = []
        try:
            while True:
                events.append(self._queue.get_nowait())
        except Empty:
            pass
        return events

    # ── 内部 ─────────────────────────────────────────────────────────────────

    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.host, self.port))
        except OSError as e:
            print(f"[emoji_danmaku] UDP bind 失败: {e}  (端口 {self.port} 已被占用?)")
            return
        sock.settimeout(0.2)
        self._sock = sock

        while self._running:
            try:
                data, _ = sock.recvfrom(8192)
                try:
                    payload = json.loads(data.decode("utf-8"))
                    self._dispatch(payload)
                except Exception as e:  # noqa: BLE001
                    print(f"[emoji_danmaku] 解析失败: {e}")
            except socket.timeout:
                pass
            except OSError:
                break  # socket closed

        sock.close()

    def _dispatch(self, payload: dict) -> None:
        cmd = payload.get("cmd", "")
        nickname = str(payload.get("nickname", ""))
        user_id = int(payload.get("user_id", 0))

        if cmd == "emoji":
            emoji = str(payload.get("emoji", "")).strip()
            if emoji in EMOJI_SET:
                self._queue.put({"emoji": emoji, "nickname": nickname, "user_id": user_id})

        elif cmd == "stg":
            # 支持 /stg 😂 这种写法（Bot 那边透传 args）
            args = str(payload.get("args", "")).strip()
            if args in EMOJI_SET:
                self._queue.put({"emoji": args, "nickname": nickname, "user_id": user_id})
