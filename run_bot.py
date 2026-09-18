import signal
import subprocess
import sys
import time


def start_backend():
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.api:app",
                             "--host", "127.0.0.1", "--port", "8000",
                             "--log-level", "warning"])

def start_client():
    return subprocess.Popen([sys.executable, "client/example_client.py"])

def main():
    backend = start_backend()
    time.sleep(2)  # give server a moment to start
    client = start_client()
    def shutdown(signum, frame):
        client.terminate()
        backend.terminate()
        sys.exit(0)
    signal.signal(signal.SIGINT, shutdown)
    backend.wait()
    client.wait()

if __name__ == "__main__":
    main()
