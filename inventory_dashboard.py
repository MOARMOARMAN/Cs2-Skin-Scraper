import subprocess
import webbrowser
import time
import atexit
import logging
import sys

logger = logging.getLogger("Inventory Dashboard")

def close_processes(backend_process, frontend_process):
    logger.info("Closing Inventory Dashboard Services.")
    backend_process.terminate()
    frontend_process.terminate()

def launch_processes():
    api_process = subprocess.Popen(
        [sys.executable, "-m", "unvicorn", "inventory:app", "--port", "8000"]
    )
    dashboard_process = subprocess.Popen(

    )

    atexit.register(close_processes, api_process, dashboard_process)
