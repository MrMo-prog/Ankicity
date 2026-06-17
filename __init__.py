# Anki-City add-on initialization
from aqt import mw

# Register web assets folder so AnkiWebView can load them using /_addons/ankicity/web/...
mw.addonManager.setWebExports(__name__, r"web/.*")

# Import modules to register hooks and bridge handlers
from . import webview
