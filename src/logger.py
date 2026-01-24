import logging
import os
from datetime import datetime

# Define log file name
LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

# Determine where to save logs
# Vercel provides a read-only filesystem except for /tmp
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    # In Vercel/Lambda, use /tmp
    logs_path = os.path.join("/tmp", "logs")
else:
    # Locally, use the current directory
    logs_path = os.path.join(os.getcwd(), "logs")

os.makedirs(logs_path, exist_ok=True)

LOG_FILE_PATH = os.path.join(logs_path, LOG_FILE)

logging.basicConfig(
    filename=LOG_FILE_PATH,
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Also print to console (Standard Output) so Vercel logs capture it
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[ %(asctime)s ] %(name)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(console_handler)