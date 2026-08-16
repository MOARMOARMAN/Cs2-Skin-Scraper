import subprocess
import webbrowser
import time
import atexit
import logging
import sys
from pathlib import Path
from subprocess import Popen
from backend.utilities import (
    create_inventory_skins_table_db,
    create_transactions_table_db,
    INVENTORY_DB
)


logger = logging.getLogger("Inventory Dashboard")

ROOT = Path(__file__).resolve().parent

def close_processes(backend_process, frontend_process):
    logger.info("Closing Inventory Dashboard Services.")
    backend_process.terminate()
    frontend_process.terminate()

def launch_processes():
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.inventory:app", "--port", "8000"],
        cwd = ROOT
    )
    dashboard_process = subprocess.Popen(
        ["npm.cmd", "run", "dev"],
        cwd = ROOT / "frontend"
    )

    atexit.register(close_processes, api_process, dashboard_process)

    time.sleep(3)
    webbrowser.open_new_tab("http://localhost:5173")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping dashboard...")

if __name__ == "__main__":
    create_inventory_skins_table_db(INVENTORY_DB)
    create_transactions_table_db(INVENTORY_DB)
    launch_processes()

