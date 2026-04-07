import asyncio
import os
import sys

from ballparkpal_auth import ensure_logged_in

os.makedirs("data", exist_ok=True)

if __name__ == "__main__":
    keep_open = "--inspect" in sys.argv or os.getenv("BALLPARKPAL_AUTH_INSPECT") == "1"
    success = asyncio.run(ensure_logged_in(keep_open=keep_open))
    raise SystemExit(0 if success else 1)
