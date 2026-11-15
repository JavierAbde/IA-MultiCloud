
import logging
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "backend.log"

logging.basicConfig(
    level=logging.INFO,
    force=True,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("monitoreo_vial")
