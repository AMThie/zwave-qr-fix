"""Allow ``python -m zwave_qr_fix``."""

import sys

from .cli import main

sys.exit(main())
