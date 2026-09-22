import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                "app.log",
                maxBytes=10 * 1024 * 1024,  # 10 MB per file
                backupCount=5,               # Up to 5 backup files (50 MB disk cap)
                encoding="utf-8"
            )
        ]
    )
