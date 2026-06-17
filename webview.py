# Webview and UI Controller for Anki-City
import json
import os
from aqt import mw, gui_hooks
from aqt.webview import AnkiWebView
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QSizePolicy

from . import db
from . import engine
from . import exporter

# Global reference to prevent garbage collection
city_view_instance = None
dashboard_visible = True

def validate_and_sanitize_street(street) -> list:
    default_lineup = [
        {"id": "HOUSE", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "SAWMILL", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "TAVERN", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "TOWNHALL", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "STRAW_MILL", "tier": 1},
        {"id": "QUARRY", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "HOUSE", "tier": 1},
        {"id": "GOLD_MINE", "tier": 1}
    ]
    
    # Migrate old 11-building format to 15-building format safely
    if isinstance(street, list) and len(street) == 11:
        migrated = list(street)
        migrated.insert(1, {"id": "HOUSE", "tier": 1})
        migrated.insert(6, {"id": "HOUSE", "tier": 1})
        migrated.insert(9, {"id": "HOUSE", "tier": 1})
        migrated.insert(13, {"id": "HOUSE", "tier": 1})
        street = migrated
        
    if not isinstance(street, list) or len(street) == 0:
        return default_lineup
        
    valid_ids = {"HOUSE", "SAWMILL", "TAVERN", "TOWNHALL", "STRAW_MILL", "QUARRY", "GOLD_MINE"}
    id_mapping = {
        "house": "HOUSE",
        "sawmill": "SAWMILL",
        "tavern": "TAVERN",
        "townhall": "TOWNHALL",
        "town_hall": "TOWNHALL",
        "windmill": "STRAW_MILL",
        "straw_mill": "STRAW_MILL",
        "quarry": "QUARRY",
        "goldmine": "GOLD_MINE",
        "gold_mine": "GOLD_MINE"
    }
    
    sanitized = []
    for item in street:
        if not isinstance(item, dict):
            continue
        b_id = item.get("id", "")
        if not isinstance(b_id, str):
            continue
        
        b_id_upper = b_id.upper()
        if b_id_upper in valid_ids:
            clean_id = b_id_upper
        elif b_id.lower() in id_mapping:
            clean_id = id_mapping[b_id.lower()]
        else:
            continue
            
        tier = item.get("tier", 1)
        try:
            tier = int(tier)
            if not (1 <= tier <= 4):
                tier = 1
        except:
            tier = 1
            
        sanitized.append({"id": clean_id, "tier": tier})
        
    if len(sanitized) == 0 or len(sanitized) != len(default_lineup):
        return default_lineup
        
    return sanitized


def recalculate_efficiency(config: dict) -> dict:
    """Recalculates cards_per_resource and clamps current_counter based on Town Hall tier."""
    street_lineup = config.get("street_lineup", [])
    town_hall_tier = 1
    for cell in street_lineup:
        if cell.get("id", "") == "TOWNHALL":
            town_hall_tier = cell.get("tier", 1)
            break
            
    reps_map = {1: 20, 2: 19, 3: 17, 4: 15}
    cards_per_resource = reps_map.get(town_hall_tier, 20)
    config["cards_per_resource"] = cards_per_resource
    
    if config.get("current_counter", 20) > cards_per_resource:
        config["current_counter"] = cards_per_resource
        
    return config


class CityWebView(AnkiWebView):
    def __init__(self):
        super().__init__(title="Anki-City Dashboard")
        self.addon_package = mw.addonManager.addonFromModule(__name__)
        
        # UI sizing policy - height is set dynamically based on user preferences
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        config = mw.addonManager.getConfig(self.addon_package) or {}
        height = config.get("widget_height", 360)
        self.setFixedHeight(height)
        
        # Load dashboard content
        self.refresh_html()
        
        # Register JS bridge handler
        gui_hooks.webview_did_receive_js_message.append(self.on_js_message)

    def refresh_html(self):
        """Loads index.html into the webview, setting up local assets pathing."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <base href="/_addons/{self.addon_package}/web/">
            <link rel="stylesheet" href="style.css">
            <script src="app.js" defer></script>
        </head>
        <body>
            <div id="app"></div>
        </body>
        </html>
        """
        self.setHtml(html)

    def send_to_js(self, command: str, data: dict):
        """Helper to evaluate javascript inside the dashboard."""
        js = f"if (window.onAnkiData) {{ window.onAnkiData({json.dumps(command)}, {json.dumps(data)}); }}"
        self.eval(js)

    def refresh_ui(self):
        """Queries the latest state and pushes it to JavaScript."""
        config = mw.addonManager.getConfig(self.addon_package) or {}
        
        # Sanitize street lineup to prevent invalid configurations
        config["street_lineup"] = validate_and_sanitize_street(config.get("street_lineup", []))
        
        # Safely migrate configuration properties for milestones without resetting levels/resources
        needs_save = False
        if "last_milestone_claimed" not in config:
            config["last_milestone_claimed"] = 0
            needs_save = True
        if "pending_milestones" not in config:
            config["pending_milestones"] = []
            needs_save = True
        if not config.get("reset_state_v6"):
            config["reset_state_v6"] = True
            needs_save = True
            
        if needs_save:
            config = recalculate_efficiency(config)
            mw.addonManager.writeConfig(self.addon_package, config)
            
        # Determine fixed height based on visibility
        global dashboard_visible
        if dashboard_visible:
            self.setFixedHeight(config.get("widget_height", 360))
        else:
            self.setFixedHeight(48)
            
        streak = db.get_streak(config.get("installation_time", 0))
        
        data = {
            "resources": config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0}),
            "current_counter": config.get("current_counter", 20),
            "cards_per_resource": config.get("cards_per_resource", 20),
            "next_resource": config.get("next_resource", "straw"),
            "street_lineup": config.get("street_lineup", []),
            "unlocked_cosmetics": config.get("unlocked_cosmetics", ["default"]),
            "streak": streak,
            "costs": engine.BUILDING_COSTS,
            "pending_milestones": config.get("pending_milestones", []),
            "last_milestone_claimed": config.get("last_milestone_claimed", 0),
            "dashboard_visible": dashboard_visible
        }
        self.send_to_js("state_update", data)


    def on_js_message(self, handled: tuple[bool, any], message: str, context: any) -> tuple[bool, any]:
        global dashboard_visible
        # Ensure message is meant for this webview
        if not message.startswith("ankicity:"):
            return handled

        try:
            print(f"Anki-City Bridge Received message: {message}")
            # Parse command and payload
            # Format is "ankicity:cmd:payload"
            parts = message.split(":", 2)
            cmd = parts[1]
            payload = json.loads(parts[2]) if len(parts) > 2 else {}
            
            config = mw.addonManager.getConfig(self.addon_package) or {}
            
            if cmd == "ready":
                if config.get("installation_time", 0) == 0:
                    import time
                    config["installation_time"] = int(time.time())
                
                config["street_lineup"] = validate_and_sanitize_street(config.get("street_lineup", []))
                
                # Safely migrate configuration properties for milestones without resetting levels/resources
                needs_save = False
                if "last_milestone_claimed" not in config:
                    config["last_milestone_claimed"] = 0
                    needs_save = True
                if "pending_milestones" not in config:
                    config["pending_milestones"] = []
                    needs_save = True
                if not config.get("reset_state_v6"):
                    config["reset_state_v6"] = True
                    needs_save = True
                
                config = recalculate_efficiency(config)
                mw.addonManager.writeConfig(self.addon_package, config)
                self.refresh_ui()
                return True, "ready_acknowledged"
                    
            elif cmd == "upgrade":
                index = payload["index"]
                street = config.get("street_lineup", [])
                if 0 <= index < len(street):
                    cell = street[index]
                    current_id = cell["id"]
                    current_tier = cell["tier"]
                    
                    if current_tier < 4:
                        next_tier = current_tier + 1
                        cost_key = f"{current_id}_lvl{next_tier}"
                        cost = engine.BUILDING_COSTS.get(cost_key, {})
                        
                        if engine.can_afford(config["resources"], cost):
                            config["resources"] = engine.deduct_resources(config["resources"], cost)
                            cell["tier"] = next_tier
                            config = recalculate_efficiency(config)
                            config = engine.check_milestones(config)
                            mw.addonManager.writeConfig(self.addon_package, config)
                            self.refresh_ui()
                        else:
                            self.send_to_js("error", {"message": f"Cannot afford upgrade to Tier {next_tier}!"})
                    else:
                        self.send_to_js("error", {"message": "Building is already at maximum level!"})
                        
            elif cmd == "claim_milestone":
                threshold = payload.get("threshold")
                pending = config.get("pending_milestones", [])
                config["pending_milestones"] = [m for m in pending if m.get("threshold") != threshold]
                mw.addonManager.writeConfig(self.addon_package, config)
                self.refresh_ui()
                return True, "success"
                
            elif cmd == "trade":
                from_res = payload["from_res"]
                to_res = payload["to_res"]
                success, updated_res, msg = engine.trade_resources(config["resources"], from_res, to_res)
                
                if success:
                    config["resources"] = updated_res
                    mw.addonManager.writeConfig(self.addon_package, config)
                    self.refresh_ui()
                    self.send_to_js("toast", {"message": msg})
                else:
                    self.send_to_js("error", {"message": msg})
                    
            elif cmd == "resize":
                height = int(payload["height"])
                height = max(150, min(800, height))
                self.setFixedHeight(height)
                
            elif cmd == "resize_end":
                height = int(payload["height"])
                height = max(150, min(800, height))
                config = mw.addonManager.getConfig(self.addon_package) or {}
                config["widget_height"] = height
                mw.addonManager.writeConfig(self.addon_package, config)
                self.setFixedHeight(height)
                
            elif cmd == "hide_dashboard":
                dashboard_visible = False
                self.refresh_ui()
                
            elif cmd == "restore_dashboard":
                dashboard_visible = True
                self.refresh_ui()
                
            elif cmd == "export":
                exporter.export_city_snapshot(payload["image_data"])
                
            return True, "success"
        except Exception as e:
            print(f"Anki-City Bridge Error: {e}")
            return True, f"error: {e}"

# UI Integration Hooks
def toggle_dashboard_visibility():
    global city_view_instance, dashboard_visible
    if city_view_instance:
        dashboard_visible = not dashboard_visible
        city_view_instance.refresh_ui()

def on_main_window_init():
    global city_view_instance
    city_view_instance = CityWebView()
    mw.mainLayout.addWidget(city_view_instance)
    
    # Add a menu item to Tools menu to toggle dashboard visibility
    action = mw.form.menuTools.addAction("Toggle Anki-City Dashboard")
    action.setShortcut("Ctrl+Alt+C")
    action.triggered.connect(toggle_dashboard_visibility)
    
    # Set initial visibility state
    update_widget_visibility(mw.state, None)

def update_widget_visibility(new_state, old_state):
    global city_view_instance
    if city_view_instance:
        if new_state in ["deckBrowser", "overview"]:
            city_view_instance.show()
            city_view_instance.refresh_ui()
        else:
            city_view_instance.hide()

def show_in_study_notification(awarded: str, doubled: bool):
    awarded_esc = awarded.replace("'", "\\'")
    amount_str = "2" if doubled else "1"
    double_text_str = " (Double Drop! 🌟)" if doubled else ""
    
    js = """
    (function() {
        let container = document.getElementById("ankicity-notifications-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "ankicity-notifications-container";
            container.style.position = "fixed";
            container.style.bottom = "50px";
            container.style.right = "12px";
            container.style.zIndex = "100000";
            container.style.pointerEvents = "none";
            container.style.display = "flex";
            container.style.flexDirection = "column";
            container.style.gap = "8px";
            container.style.alignItems = "flex-end";
            document.body.appendChild(container);
        }

        const notification = document.createElement("div");
        notification.style.display = "flex";
        notification.style.alignItems = "center";
        notification.style.gap = "10px";
        notification.style.padding = "10px 16px";
        notification.style.borderRadius = "8px";
        notification.style.background = "rgba(30, 30, 30, 0.85)";
        notification.style.backdropFilter = "blur(10px)";
        notification.style.webkitBackdropFilter = "blur(10px)";
        notification.style.border = "1px solid rgba(255, 255, 255, 0.15)";
        notification.style.boxShadow = "0 8px 16px rgba(0, 0, 0, 0.25)";
        notification.style.color = "#ffffff";
        notification.style.fontFamily = "system-ui, -apple-system, sans-serif";
        notification.style.fontSize = "13px";
        notification.style.fontWeight = "bold";
        notification.style.opacity = "0";
        notification.style.transform = "translateX(50px)";
        notification.style.transition = "all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)";
        
        const emojis = { straw: "🌾", wood: "🪵", stone: "🪨", gold: "🪙" };
        const emoji = emojis['""" + awarded_esc + """'] || "📦";
        const amount = """ + amount_str + """;
        const resourceName = '""" + awarded_esc.upper() + """';
        const doubleText = '""" + double_text_str + """';
        
        notification.innerHTML = `<span>📜 Congrats! You just earned ${amount}x ${emoji} ${resourceName}${doubleText}</span>`;
        
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = "1";
            notification.style.transform = "translateX(0)";
        }, 50);
        
        setTimeout(() => {
            notification.style.opacity = "0";
            notification.style.transform = "translateX(50px)";
            setTimeout(() => {
                notification.remove();
            }, 400);
        }, 3500);
    })();
    """
    mw.reviewer.web.eval(js)

def on_card_answered(reviewer, card, ease):
    addon_package = mw.addonManager.addonFromModule(__name__)
    config = mw.addonManager.getConfig(addon_package)
    if not config:
        return
        
    # Process card answer to reward progression
    config, awarded, doubled = engine.process_card_answer(config)
    mw.addonManager.writeConfig(addon_package, config)
    
    # Push update to reviewer HUD text
    update_reviewer_hud(config)
    
    # Trigger overlay notification if resource was earned
    if awarded:
        show_in_study_notification(awarded, doubled)

def update_reviewer_hud(config):
    next_res = config.get("next_resource", "straw")
    counter = config.get("current_counter", 20)
    
    emoji_map = {
        "straw": "🌾 Straw",
        "wood": "🪵 Wood",
        "stone": "🪨 Stone",
        "gold": "🪙 Gold"
    }
    res_label = emoji_map.get(next_res, next_res.capitalize())
    
    js = f"""
    (function() {{
        let hud = document.getElementById("ankicity-reviewer-hud");
        if (!hud) {{
            hud = document.createElement("div");
            hud.id = "ankicity-reviewer-hud";
            hud.style.position = "fixed";
            hud.style.bottom = "12px";
            hud.style.right = "12px";
            hud.style.fontSize = "11px";
            hud.style.color = "#a0a0a0";
            hud.style.backgroundColor = "rgba(30, 30, 30, 0.75)";
            hud.style.border = "1px solid rgba(255, 255, 255, 0.1)";
            hud.style.padding = "4px 8px";
            hud.style.borderRadius = "6px";
            hud.style.zIndex = "99999";
            hud.style.fontFamily = "system-ui, -apple-system, sans-serif";
            hud.style.pointerEvents = "none";
            hud.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.2)";
            document.body.appendChild(hud);
        }}
        hud.innerHTML = "📦 Next: {res_label} ({counter} left)";
    }})();
    """
    mw.reviewer.web.eval(js)

def inject_reviewer_hud(card):
    addon_package = mw.addonManager.addonFromModule(__name__)
    config = mw.addonManager.getConfig(addon_package)
    if config:
        update_reviewer_hud(config)

# Register hooks
gui_hooks.main_window_did_init.append(on_main_window_init)
gui_hooks.state_did_change.append(update_widget_visibility)
gui_hooks.reviewer_did_answer_card.append(on_card_answered)
gui_hooks.reviewer_did_show_question.append(inject_reviewer_hud)
gui_hooks.reviewer_did_show_answer.append(inject_reviewer_hud)
