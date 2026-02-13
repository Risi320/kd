#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from http.server import ThreadingHTTPServer


def run_fallback_server(addrport: str = "127.0.0.1:8000") -> int:
    from app import HotelHandler, init_db

    if ":" in addrport:
        host, port_text = addrport.rsplit(":", 1)
    else:
        host, port_text = "127.0.0.1", addrport

    host = host or "127.0.0.1"
    try:
        port = int(port_text)
    except ValueError:
        print(f"Port i pavlefshëm: {port_text}")
        return 1

    init_db()
    server = ThreadingHTTPServer((host, port), HotelHandler)
    print(f"Starting development server at http://{host}:{port}/")
    print("Quit the server with CONTROL-C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hotel_project.settings")

    argv = sys.argv[1:]
    if not argv:
        print("Usage: python manage.py runserver [addr:port]")
        return 1

    command = argv[0]

    if command == "runserver":
        addrport = argv[1] if len(argv) > 1 else "127.0.0.1:8000"
        try:
            from django.core.management import execute_from_command_line  # type: ignore
        except Exception:
            print("Django nuk është i instaluar në këtë ambient. Po startoj fallback serverin e projektit...")
            return run_fallback_server(addrport)

        execute_from_command_line([sys.argv[0], "runserver", addrport])
        return 0

    print(f"Command i panjohur: {command}")
    print("Supported: runserver")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
