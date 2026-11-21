"""Entry point for Phusion Passenger (cPanel "Setup Python App" on Namecheap hosting).

Passenger looks for this exact filename in the application root and imports
`application` from it. It just delegates to Django's real WSGI app.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

from backend.wsgi import application  # noqa: E402
