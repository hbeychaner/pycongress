"""Package-level configuration read from environment variables.

Consumers should set these via a ``.env`` file or shell environment.
The main project's ``settings.py`` takes priority when the SDK is used
within ``usa-congress-monitor``; this module provides the same values
when the SDK is used as a standalone package.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Walk up from this file looking for a .env file so local development
# "just works" whether the SDK is installed editable or as a package.
_here = Path(__file__).resolve()
for _parent in [_here.parent, _here.parent.parent, _here.parent.parent.parent]:
    _dotenv = _parent / ".env"
    if _dotenv.exists():
        load_dotenv(_dotenv, override=False)
        break

CONGRESS_API_KEY: str = os.getenv("CONGRESS_API_KEY", "")
CONGRESS_API_URL: str = os.getenv("CONGRESS_API_URL", "")
CONGRESS_STRICT_FIELD_CHECK: bool = os.getenv(
    "CONGRESS_STRICT_FIELD_CHECK", "false"
).lower() in ("1", "true", "yes")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
TIMEOUT_SECS: int = int(os.getenv("TIMEOUT_SECS", "30"))
