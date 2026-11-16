from __future__ import annotations

import argparse
import logging

from . import db as dbmod
from .api import create_app
from .jobs import JobQueue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HypeCut Local backend server")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (loopback only)")
    parser.add_argument("--port", type=int, default=8756)
    parser.add_argument("--db", default=None, help="path to SQLite database")
    args = parser.parse_args(argv)

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("HypeCut binds to loopback only; refusing non-local host")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    conn = dbmod.connect(args.db)
    dbmod.init_db(conn)
    queue = JobQueue(conn)
    app = create_app(conn=conn, queue=queue)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
