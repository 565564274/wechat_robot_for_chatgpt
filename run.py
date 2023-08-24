import sys
import uvicorn
from fast_api.fast_api import app

host = "127.0.0.1" if "win" in sys.platform else "0.0.0.0"
uvicorn.run(app=app, host=host, port=9981)


