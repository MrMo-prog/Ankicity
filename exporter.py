# Canvas Snapshot Exporter for Anki-City
import base64
from aqt import mw
from aqt.qt import QFileDialog
from aqt.utils import tooltip

def export_city_snapshot(base64_data: str):
    """
    Decodes a base64 PNG data URL sent from JavaScript and
    prompts the user to save it via a native file save dialog.
    """
    try:
        # Check and strip data URL header
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
            
        # Decode base64 to raw PNG bytes
        img_bytes = base64.b64decode(base64_data)
        
        # Open the native save file dialog
        # Parented to mw (main window) to remain modal
        path, _ = QFileDialog.getSaveFileName(
            mw,
            "Save City Snapshot",
            "anki_city.png",
            "PNG Images (*.png)"
        )
        
        # If user did not cancel and selected a path
        if path:
            with open(path, "wb") as f:
                f.write(img_bytes)
            # Show a native Anki toast tooltip
            tooltip("City snapshot saved successfully!")
            
    except Exception as e:
        print(f"Anki-City: Failed to export snapshot: {e}")
        tooltip(f"Failed to export snapshot: {e}")
