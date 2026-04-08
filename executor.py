"""
Low-Latency Async Executor — reduces trade execution lag.
Uses threading to separate signal detection from order placement.
Execution happens on a dedicated thread with a queue so the main
scan loop never blocks waiting for MT5 order confirmation.

Key improvement over the old approach:
  Old: scan → wait for MT5 order response → continue scan (blocking)
  New: scan → push to queue → executor thread fires order immediately
"""
import threading
import queue
import time
from datetime import datetime, timezone
import mt5_connector as mt5c
import telegram_alerts as tg
import performance_log as perf
import config

_order_queue: queue.Queue = queue.Queue(maxsize=20)
_result_log:  list = []
_lock = threading.Lock()
_running = False
_executor_thread = None


class OrderRequest:
    __slots__ = ["symbol", "direction", "lot", "sl", "tp",
                 "win_prob", "confluence", "queued_at"]

    def __init__(self, symbol, direction, lot, sl, tp, win_prob, confluence):
        self.symbol     = symbol
        self.direction  = direction
        self.lot        = lot
        self.sl         = sl
        self.tp         = tp
        self.win_prob   = win_prob
        self.confluence = confluence
        self.queued_at  = datetime.now(timezone.utc)


def submit_order(symbol: str, direction: str, lot: float,
                 sl: float, tp: float,
                 win_prob: float, confluence: float):
    """
    Non-blocking — push order to execution queue immediately.
    Returns True if queued, False if queue is full.
    """
    req = OrderRequest(symbol, direction, lot, sl, tp, win_prob, confluence)
    try:
        _order_queue.put_nowait(req)
        return True
    except queue.Full:
        print(f"[EXEC] Queue full — order for {symbol} dropped.")
        return False


def _execute_order(req: OrderRequest):
    """Execute a single order. Runs on the executor thread."""
    # Measure latency from queue time
    latency_ms = (datetime.now(timezone.utc) - req.queued_at).total_seconds() * 1000

    result = mt5c.place_order(
        req.symbol, req.direction, req.lot, req.sl, req.tp,
        comment=f"ai-{req.win_prob:.2f}"
    )

    if result["success"]:
        ticket     = result["ticket"]
        exec_price = result.get("price", 0)

        # Log trade
        perf.log_trade(ticket, req.symbol, req.direction, req.lot,
                       exec_price, req.sl, req.tp, req.win_prob)

        # Telegram alert
        tg.alert_trade_opened(
            req.symbol, req.direction, req.lot,
            exec_price, req.sl, req.tp,
            req.win_prob, req.confluence
        )

        print(f"[EXEC] ✓ {req.direction.upper()} {req.symbol} "
              f"@ {exec_price:.5f} | Ticket #{ticket} | Latency: {latency_ms:.0f}ms")

        with _lock:
            _result_log.append({
                "ticket":     ticket,
                "symbol":     req.symbol,
                "direction":  req.direction,
                "price":      exec_price,
                "latency_ms": round(latency_ms),
                "success":    True,
            })
    else:
        print(f"[EXEC] ✗ Order failed for {req.symbol}: {result.get('comment', 'unknown')}")
        with _lock:
            _result_log.append({
                "symbol":    req.symbol,
                "direction": req.direction,
                "error":     result.get("comment", "unknown"),
                "success":   False,
            })


def _executor_loop():
    """Dedicated thread that drains the order queue."""
    global _running
    print("[EXEC] Executor thread started.")
    while _running:
        try:
            req = _order_queue.get(timeout=1.0)
            _execute_order(req)
            _order_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[EXEC] Executor error: {e}")
            time.sleep(1)
    print("[EXEC] Executor thread stopped.")


def start():
    """Start the executor thread. Call once at bot startup."""
    global _running, _executor_thread
    if _running:
        return
    _running = True
    _executor_thread = threading.Thread(target=_executor_loop, daemon=True, name="Executor")
    _executor_thread.start()


def stop():
    """Gracefully stop the executor thread."""
    global _running
    _running = False
    if _executor_thread:
        _executor_thread.join(timeout=5)


def avg_latency_ms() -> float:
    """Return average execution latency in milliseconds."""
    with _lock:
        times = [r["latency_ms"] for r in _result_log if r.get("success") and "latency_ms" in r]
    return round(sum(times) / len(times), 1) if times else 0.0


def queue_size() -> int:
    return _order_queue.qsize()
