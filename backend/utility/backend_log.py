# backend/backend_log.py
# Utility module to configure and provide a logger for the backend
import logging
# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# Expose logger to be used from other modules
__all__ = ["logger"]