"""Main entry point to run the SRMS application locally."""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("SRMS_PORT", 5000))
    debug = os.environ.get("SRMS_DEBUG", "true").lower() == "true"
    app.run(host="127.0.0.1", port=port, debug=debug)
