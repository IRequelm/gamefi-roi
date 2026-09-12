"""Entrypoint for `python -m app.doctor`."""

import sys
if "--recovery" in sys.argv:
    from app.doctor.recovery import main
else:
    from app.doctor.checks import main

raise SystemExit(main())
