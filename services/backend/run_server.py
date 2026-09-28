"""Supervisor dev server runner for Candidate Capability Intelligence backend."""
import subprocess
import sys
import time


def main():
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "cci.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    while True:
        try:
            proc = subprocess.run(cmd)
            # If terminated cleanly by SIGINT/Ctrl-C, break
            if proc.returncode in (0, -2, 3221225786):
                break
            time.sleep(0.5)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(0.5)


if __name__ == "__main__":
    main()
