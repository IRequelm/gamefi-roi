"""Entrypoint for `python -m app.doctor`."""

from app.doctor.checks import main

raise SystemExit(main())
