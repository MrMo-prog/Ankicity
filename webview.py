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
previous_config = None

def validate_and_sanitize_street(street) -> list:
    default_lineup = [
        {"id": "CRAFTING_HUT", "tier": 1},
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
        
    # Migrate 15-building format to 16-building format by inserting Crafting Hut at index 0
    if isinstance(street, list) and len(street) == 15:
        street = [{"id": "CRAFTING_HUT", "tier": 1}] + list(street)
        
    if not isinstance(street, list) or len(street) == 0:
        return default_lineup
        
    valid_ids = {"CRAFTING_HUT", "HOUSE", "SAWMILL", "TAVERN", "TOWNHALL", "STRAW_MILL", "QUARRY", "GOLD_MINE"}
    id_mapping = {
        "crafting_hut": "CRAFTING_HUT",
        "workshop": "CRAFTING_HUT",
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
            max_tier = 5 if clean_id == "CRAFTING_HUT" else 4
            if not (1 <= tier <= max_tier):
                tier = 1
        except:
            tier = 1
            
        cell_dict = {"id": clean_id, "tier": tier}
        if "skin" in item:
            cell_dict["skin"] = item["skin"]
        if "extra_pop" in item:
            cell_dict["extra_pop"] = item["extra_pop"]
            
        sanitized.append(cell_dict)
        
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


def check_daily_streak_reward(config: dict) -> dict:
    """Checks if a new day has started, and awards 1-4 free resources based on consecutive study streak."""
    if not mw.col:
        return config
        
    try:
        cutoff = mw.col.sched.day_cutoff
        last_claim = config.get("last_streak_claim_cutoff", 0)
        
        # If it's a new scheduler day (using a 12-hour tolerance to prevent timezone/clock changes from causing double claims)
        if last_claim == 0 or cutoff - last_claim > 43200:
            # Reset daily claimed milestones
            config["claimed_streak_milestones_today"] = []
            
            installation_time = config.get("installation_time", 0)
            streak = db.get_streak(installation_time)
            
            # If they have a streak of at least 1 day, roll rewards
            if streak >= 1:
                count = min(streak, 4)
                rewards = {"straw": 0, "wood": 0, "stone": 0, "gold": 0}
                for _ in range(count):
                    res = engine.roll_resource(config.get("street_lineup", []))
                    rewards[res] = rewards.get(res, 0) + 1
                    
                # Add to inventory
                resources = config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0})
                for r, c in rewards.items():
                    resources[r] = resources.get(r, 0) + c
                config["resources"] = resources
                
                # Store pending reward for modal popup display
                config["pending_streak_reward"] = {
                    "streak": streak,
                    "rewards": rewards
                }
                
            # Lock the day so we don't check again today
            config["last_streak_claim_cutoff"] = cutoff
            
    except Exception as e:
        print(f"Anki-City Error in check_daily_streak_reward: {e}")
        
    return config


def check_daily_artisan_draw(config: dict) -> dict:
    """Checks if a new day has started, and generates a random pool of 3 artisans to draw from."""
    if not mw.col:
        return config
    try:
        import random
        cutoff = mw.col.sched.day_cutoff
        last_draw = config.get("last_artisan_draw_cutoff", 0)
        
        # Using a 12-hour tolerance to prevent timezone/clock changes from causing premature resets
        if last_draw == 0 or cutoff - last_draw > 43200:
            # Clear active artisan session
            config["active_artisan"] = None
            config["artisan_reviews_remaining"] = 0
            config["artisan_reviews_clicked"] = 0
            
            # Generate artisan options
            artisans = ["builder", "merchant", "haggler", "alchemist"]
            last_chosen = config.get("last_chosen_artisan")
            
            if last_chosen is None:
                # If they have not chosen anyone before, show all 4
                drawn = artisans
            else:
                # Pool: exclude last chosen
                pool = [a for a in artisans if a != last_chosen]
                if len(pool) < 3:
                    pool = artisans
                # Draw exactly 3 unique options
                drawn = random.sample(pool, 3)
                
            config["artisan_options"] = drawn
            config["last_artisan_draw_cutoff"] = cutoff
            
    except Exception as e:
        print(f"Anki-City Error in check_daily_artisan_draw: {e}")
        
    return config


def show_custom_notification(text: str):
    text_esc = text.replace("'", "\\'")
    js = f"""
    (function() {{
        let container = document.getElementById("ankicity-notifications-container");
        if (!container) {{
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
        }}

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
        
        notification.innerHTML = `<span>📜 {text_esc}</span>`;
        
        container.appendChild(notification);
        
        setTimeout(() => {{
            notification.style.opacity = "1";
            notification.style.transform = "translateX(0)";
        }}, 50);
        
        setTimeout(() => {{
            notification.style.opacity = "0";
            notification.style.transform = "translateX(50px)";
            setTimeout(() => {{
                notification.remove();
            }}, 400);
        }}, 4500);
    }})();
    """
    mw.reviewer.web.eval(js)


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
        import time
        t = int(time.time())
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <base href="/_addons/{self.addon_package}/web/">
            <link rel="stylesheet" href="style.css?t={t}">
            <script src="app.js?t={t}" defer></script>
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
        
        orig_streak_cutoff = config.get("last_streak_claim_cutoff", 0)
        config = check_daily_streak_reward(config)
        streak_changed = config.get("last_streak_claim_cutoff", 0) != orig_streak_cutoff
        
        orig_draw_cutoff = config.get("last_artisan_draw_cutoff", 0)
        config = check_daily_artisan_draw(config)
        draw_changed = config.get("last_artisan_draw_cutoff", 0) != orig_draw_cutoff
        
        # Sanitize street lineup to prevent invalid configurations
        config["street_lineup"] = validate_and_sanitize_street(config.get("street_lineup", []))
        
        # Safely migrate configuration properties for milestones without resetting levels/resources
        needs_save = streak_changed or draw_changed
        if "last_milestone_claimed" not in config:
            config["last_milestone_claimed"] = 0
            needs_save = True
        if "pending_milestones" not in config:
            config["pending_milestones"] = []
            needs_save = True
        if "claimed_streak_milestones_today" not in config:
            config["claimed_streak_milestones_today"] = []
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
            
        streak_details = db.get_streak_details(config.get("installation_time", 0))
        
        data = {
            "resources": config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0}),
            "current_counter": config.get("current_counter", 20),
            "cards_per_resource": config.get("cards_per_resource", 20),
            "next_resource": config.get("next_resource", "straw"),
            "street_lineup": config.get("street_lineup", []),
            "unlocked_cosmetics": config.get("unlocked_cosmetics", ["default"]),
            "unlocked_skins": config.get("unlocked_skins", ["default"]),
            "streak": streak_details["days"],
            "streak_milestone": streak_details["milestone"],
            "costs": engine.BUILDING_COSTS,
            "pending_milestones": config.get("pending_milestones", []),
            "pending_streak_reward": config.get("pending_streak_reward", None),
            "last_milestone_claimed": config.get("last_milestone_claimed", 0),
            "dashboard_visible": dashboard_visible,
            
            # Phase 3 Artisan fields
            "artisan_levels": config.get("artisan_levels", {"builder": 1, "merchant": 1, "haggler": 1, "alchemist": 1}),
            "active_artisan": config.get("active_artisan", None),
            "artisan_reviews_remaining": config.get("artisan_reviews_remaining", 0),
            "artisan_reviews_clicked": config.get("artisan_reviews_clicked", 0),
            "artisan_options": config.get("artisan_options", None),
            "haggler_discount": config.get("haggler_discount", None)
        }
        self.send_to_js("state_update", data)


    def on_js_message(self, handled: tuple[bool, any], message: str, context: any) -> tuple[bool, any]:
        global dashboard_visible, previous_config
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
                if "claimed_streak_milestones_today" not in config:
                    config["claimed_streak_milestones_today"] = []
                    needs_save = True
                if "unlocked_skins" not in config:
                    config["unlocked_skins"] = ["default"]
                    needs_save = True
                if "artisan_levels" not in config:
                    config["artisan_levels"] = {
                        "builder": 1,
                        "merchant": 1,
                        "haggler": 1,
                        "alchemist": 1
                    }
                    needs_save = True
                if "active_artisan" not in config:
                    config["active_artisan"] = None
                    needs_save = True
                if "artisan_reviews_remaining" not in config:
                    config["artisan_reviews_remaining"] = 0
                    needs_save = True
                if "artisan_reviews_clicked" not in config:
                    config["artisan_reviews_clicked"] = 0
                    needs_save = True
                if "last_chosen_artisan" not in config:
                    config["last_chosen_artisan"] = None
                    needs_save = True
                if "last_artisan_draw_cutoff" not in config:
                    config["last_artisan_draw_cutoff"] = 0
                    needs_save = True
                if "artisan_options" not in config:
                    config["artisan_options"] = None
                    needs_save = True
                if "haggler_discount" not in config:
                    config["haggler_discount"] = None
                    needs_save = True
                if not config.get("reset_state_v7"):
                    config["reset_state_v7"] = True
                    needs_save = True
                
                config = recalculate_efficiency(config)
                mw.addonManager.writeConfig(self.addon_package, config)
                self.refresh_ui()
                return True, "ready_acknowledged"
                    
            elif cmd == "upgrade":
                previous_config = None
                index = payload["index"]
                street = config.get("street_lineup", [])
                if 0 <= index < len(street):
                    cell = street[index]
                    current_id = cell["id"]
                    current_tier = cell["tier"]
                    
                    max_tier = 5 if current_id == "CRAFTING_HUT" else 4
                    if current_tier < max_tier:
                        next_tier = current_tier + 1
                        
                        # Check population gates
                        allowed, err_msg = engine.can_upgrade_building(street, index, next_tier)
                        if not allowed:
                            self.send_to_js("error", {"message": err_msg})
                            return True, "success"
                            
                        # Apply Haggler discount if active
                        cost = engine.get_building_upgrade_cost(current_id, next_tier, config.get("haggler_discount"))
                        
                        if engine.can_afford(config["resources"], cost):
                            config["resources"] = engine.deduct_resources(config["resources"], cost)
                            cell["tier"] = next_tier
                            
                            # Crafting Hut upgrade custom random artisan level up
                            if current_id == "CRAFTING_HUT":
                                import random
                                levels = config.get("artisan_levels", {
                                    "builder": 1, "merchant": 1, "haggler": 1, "alchemist": 1
                                })
                                lvl1_artisans = [art for art, lvl in levels.items() if lvl == 1]
                                if lvl1_artisans:
                                    chosen_art = random.choice(lvl1_artisans)
                                    levels[chosen_art] = 2
                                    config["artisan_levels"] = levels
                                    
                                    if "pending_artisan_notifications" not in config:
                                        config["pending_artisan_notifications"] = []
                                    config["pending_artisan_notifications"].append(
                                        f"✨ Crafting Hut Tier Up! {chosen_art.capitalize()} is now Level 2!"
                                    )
                                    
                            config = recalculate_efficiency(config)
                            config = engine.check_milestones(config)
                            
                            # Show any pending artisan notifications
                            notifications = config.get("pending_artisan_notifications", [])
                            if notifications:
                                for msg in notifications:
                                    self.send_to_js("toast", {"message": msg})
                                config["pending_artisan_notifications"] = []
                                
                            mw.addonManager.writeConfig(self.addon_package, config)
                            self.refresh_ui()
                        else:
                            self.send_to_js("error", {"message": f"Cannot afford upgrade to Tier {next_tier}!"})
                    else:
                        self.send_to_js("error", {"message": "Building is already at maximum level!"})
                        
            elif cmd == "claim_milestone":
                previous_config = None
                threshold = payload.get("threshold")
                pending = config.get("pending_milestones", [])
                config["pending_milestones"] = [m for m in pending if m.get("threshold") != threshold]
                mw.addonManager.writeConfig(self.addon_package, config)
                self.refresh_ui()
                return True, "success"
                
            elif cmd == "claim_streak_reward":
                previous_config = None
                config["pending_streak_reward"] = None
                mw.addonManager.writeConfig(self.addon_package, config)
                self.refresh_ui()
                return True, "success"
                
            elif cmd == "trade":
                previous_config = None
                from_res = payload["from_res"]
                to_res = payload["to_res"]
                success, updated_res, msg = engine.trade_resources(config["resources"], from_res, to_res, config.get("street_lineup", []))
                
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
                
            elif cmd == "set_house_skin":
                previous_config = None
                index = payload["index"]
                skin_id = payload["skin_id"]
                
                street = config.get("street_lineup", [])
                if 0 <= index < len(street):
                    cell = street[index]
                    if cell.get("id") == "HOUSE" and cell.get("tier") == 4:
                        unlocked = config.get("unlocked_skins", ["default"])
                        if skin_id in unlocked:
                            cell["skin"] = skin_id
                            mw.addonManager.writeConfig(self.addon_package, config)
                            self.refresh_ui()
                        else:
                            self.send_to_js("error", {"message": "Skin not unlocked!"})
                            
            elif cmd == "buy_house_skin":
                previous_config = None
                skin_id = payload["skin_id"]
                index = payload.get("index")
                skin_costs = {
                    "Skin1": {"straw": 36, "wood": 12, "stone": 2, "gold": 0},
                    "Skin2": {"straw": 18, "wood": 6, "stone": 10, "gold": 1},
                    "Skin3": {"straw": 12, "wood": 5, "stone": 4, "gold": 5},
                    "Skin4": {"straw": 24, "wood": 12, "stone": 6, "gold": 7}
                }
                
                if skin_id not in skin_costs:
                    self.send_to_js("error", {"message": "Invalid skin ID."})
                    return True, "success"
                    
                cost = skin_costs[skin_id]
                unlocked = config.get("unlocked_skins", ["default"])
                if skin_id in unlocked:
                    self.send_to_js("error", {"message": "Skin already unlocked!"})
                    return True, "success"
                    
                if engine.can_afford(config["resources"], cost):
                    config["resources"] = engine.deduct_resources(config["resources"], cost)
                    if "unlocked_skins" not in config:
                        config["unlocked_skins"] = ["default"]
                    config["unlocked_skins"].append(skin_id)
                    
                    # Auto-apply to the house immediately
                    if index is not None:
                        street = config.get("street_lineup", [])
                        if 0 <= index < len(street):
                            cell = street[index]
                            if cell.get("id") == "HOUSE" and cell.get("tier") == 4:
                                cell["skin"] = skin_id
                                
                    mw.addonManager.writeConfig(self.addon_package, config)
                    self.refresh_ui()
                    self.send_to_js("toast", {"message": "Successfully unlocked skin!"})
                else:
                    self.send_to_js("error", {"message": "Cannot afford to unlock this skin!"})
                    
            elif cmd == "select_artisan":
                previous_config = None
                artisan_id = payload["artisan_id"]
                if artisan_id not in ["builder", "merchant", "haggler", "alchemist"]:
                    self.send_to_js("error", {"message": "Invalid artisan ID."})
                    return True, "success"
                    
                options = config.get("artisan_options")
                if not options or artisan_id not in options:
                    self.send_to_js("error", {"message": "Artisan choice not available today!"})
                    return True, "success"
                    
                # Query reviews done today and credit them toward the artisan's shift
                today_reviews = db.get_today_reviews()
                
                config["active_artisan"] = artisan_id
                config["artisan_reviews_clicked"] = today_reviews
                
                levels = config.get("artisan_levels", {"builder": 1, "merchant": 1, "haggler": 1, "alchemist": 1})
                level = levels.get(artisan_id, 1)
                
                if artisan_id == "merchant":
                    target = 200
                else:
                    target = 100
                    
                config["artisan_reviews_remaining"] = max(0, target - today_reviews)
                
                # Check and apply rewards immediately if threshold(s) were already passed
                if "pending_artisan_notifications" not in config:
                    config["pending_artisan_notifications"] = []
                    
                if artisan_id == "merchant":
                    if today_reviews >= 200:
                        config = engine.apply_artisan_effect(config, artisan_id, level, 100)
                        config = engine.apply_artisan_effect(config, artisan_id, level, 200)
                        config["active_artisan"] = None
                    elif today_reviews >= 100:
                        config = engine.apply_artisan_effect(config, artisan_id, level, 100)
                else:
                    if today_reviews >= 100:
                        config = engine.apply_artisan_effect(config, artisan_id, level, 100)
                        config["active_artisan"] = None
                        
                if config["active_artisan"] is None:
                    config["pending_artisan_notifications"].append(
                        f"👋 {artisan_id.capitalize()}'s shift has ended!"
                    )
                    
                config["last_chosen_artisan"] = artisan_id
                config["artisan_options"] = None
                config["haggler_discount"] = None
                
                # Display any pending notifications immediately
                notifications = config.get("pending_artisan_notifications", [])
                if notifications:
                    for msg in notifications:
                        self.send_to_js("toast", {"message": msg})
                    config["pending_artisan_notifications"] = []
                
                mw.addonManager.writeConfig(self.addon_package, config)
                self.refresh_ui()
                self.send_to_js("toast", {"message": f"{artisan_id.capitalize()} is now active!"})
                
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
        
        const emojis = { 
            straw: "🌾", 
            wood: "🪵", 
            stone: "🪨", 
            gold: '<span style="display:inline-block; filter: sepia(1) saturate(5) hue-rotate(10deg) brightness(1.1);">🪙</span>' 
        };
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
    global previous_config
    addon_package = mw.addonManager.addonFromModule(__name__)
    config = mw.addonManager.getConfig(addon_package)
    if not config:
        return
        
    # Save copy of the current state for undo protection
    import copy
    previous_config = copy.deepcopy(config)
    
    # Check for daily draw reset before processing reviews
    config = check_daily_artisan_draw(config)
        
    # Process card answer to reward progression
    config, awarded, doubled = engine.process_card_answer(config)
    
    # Check for daily study streak milestones reached today
    today_reviews = db.get_today_reviews()
    claimed = config.get("claimed_streak_milestones_today", [])
    milestone_hit = False
    for threshold in [50, 100, 200, 500]:
        if today_reviews >= threshold and threshold not in claimed:
            claimed.append(threshold)
            config["claimed_streak_milestones_today"] = claimed
            
            # Grant 1 random resource drop
            awarded_res = engine.roll_resource(config.get("street_lineup", []))
            resources = config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0})
            resources[awarded_res] = resources.get(awarded_res, 0) + 1
            config["resources"] = resources
            
            # Show overlay study notification
            emoji_map = {"straw": "🌾", "wood": "🪵", "stone": "🪨", "gold": "🪙"}
            res_emoji = emoji_map.get(awarded_res, "📦")
            notification_msg = f"🔥 Streak milestone reached: {threshold} reviews today! Awarded 1x {res_emoji} {awarded_res.upper()}"
            show_custom_notification(notification_msg)
            milestone_hit = True
            
    # Process and display any artisan notifications
    notifications = config.get("pending_artisan_notifications", [])
    if notifications:
        for msg in notifications:
            show_custom_notification(msg)
        config["pending_artisan_notifications"] = []
        
    mw.addonManager.writeConfig(addon_package, config)
    
    # Push update to reviewer HUD text
    update_reviewer_hud(config)
    
    # Trigger overlay notification if resource was earned
    if awarded:
        show_in_study_notification(awarded, doubled)
        
    # If a milestone was hit, refresh the city view dashboard
    global city_view_instance
    if milestone_hit and city_view_instance:
        city_view_instance.refresh_ui()

def on_state_did_undo(changes):
    global previous_config
    if previous_config is not None:
        addon_package = mw.addonManager.addonFromModule(__name__)
        mw.addonManager.writeConfig(addon_package, previous_config)
        previous_config = None
        
        # Refresh current dashboard UI view
        global city_view_instance
        if city_view_instance:
            city_view_instance.refresh_ui()

gui_hooks.state_did_undo.append(on_state_did_undo)

def update_reviewer_hud(config):
    next_res = config.get("next_resource", "straw")
    counter = config.get("current_counter", 20)
    
    emoji_map = {
        "straw": "🌾 Straw",
        "wood": "🪵 Wood",
        "stone": "🪨 Stone",
        "gold": '<span style="display:inline-block; filter: sepia(1) saturate(5) hue-rotate(10deg) brightness(1.1);">🪙</span> Gold'
    }
    res_label = emoji_map.get(next_res, next_res.capitalize())
    hud_text = f"📦 Next: {res_label} ({counter} left)"
    
    active_art = config.get("active_artisan")
    rem = config.get("artisan_reviews_remaining", 0)
    if active_art and rem > 0:
        art_emojis = {"builder": "🛠️", "merchant": "🪙", "haggler": "🏷️", "alchemist": "🧪"}
        art_emoji = art_emojis.get(active_art, "👤")
        levels = config.get("artisan_levels", {})
        lvl = levels.get(active_art, 1)
        hud_text += f" | {art_emoji} {active_art.capitalize()} Lvl {lvl}: {rem} left"
    
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
        hud.innerHTML = '{hud_text}';
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
