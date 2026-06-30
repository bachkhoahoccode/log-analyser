import subprocess
import sys
import signal
import time
from pathlib import Path

ROOT = Path(__file__).parent
SRC  = ROOT / "src"

pipeline_proc  = None
dashboard_proc = None

def shutdown(*_args):
    print("\n[run_all] Shutting down both processes...")
    for name, proc in (("pipeline", pipeline_proc), ("dashboard", dashboard_proc)):
        if proc is not None and proc.poll() is None:
            print(f"[run_all]   stopping {name} (pid {proc.pid})")
            proc.terminate()

    # give them a moment to exit cleanly, then force-kill anything left over
    deadline = time.time() + 5
    for proc in (pipeline_proc, dashboard_proc):
        if proc is None:
            continue
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            proc.kill()

    print("[run_all] Both processes stopped.")
    sys.exit(0)


def main():
    global pipeline_proc, dashboard_proc

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("[run_all] Starting live_bg_pipeline.py ...")
    pipeline_proc = subprocess.Popen(
        [sys.executable, str(SRC / "live_bg_pipeline.py")],
        cwd=str(SRC),
    )

    print("[run_all] Starting Streamlit dashboard ...")
    dashboard_proc = subprocess.Popen(
        ["streamlit", "run", str(SRC / "app.py")],
        cwd=str(SRC),
    )

    print("[run_all] Both running. Press Ctrl+C to stop both.")

    try:
        # If either process dies on its own, tear down the other too,
        # instead of leaving a half-running system.
        while True:
            if pipeline_proc.poll() is not None:
                print("[run_all] Pipeline exited unexpectedly — stopping dashboard too.")
                break
            if dashboard_proc.poll() is not None:
                print("[run_all] Dashboard exited — stopping pipeline too.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    shutdown()

if __name__ == "__main__":
    main()
