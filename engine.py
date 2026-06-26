# Game Mechanics and Reward Engine for Anki-City
import random

# Building Cost Definitions
BUILDING_COSTS = {
    # HOUSE
    "HOUSE_lvl1": {"straw": 4, "wood": 1},
    "HOUSE_lvl2": {"straw": 6, "wood": 2},
    "HOUSE_lvl3": {"straw": 15, "wood": 4, "stone": 1},
    "HOUSE_lvl4": {"straw": 20, "wood": 8, "stone": 4, "gold": 4},
    
    # TAVERN (Marketplace replacement)
    "TAVERN_lvl1": {"straw": 1, "wood": 1, "stone": 2},
    "TAVERN_lvl2": {"straw": 2, "wood": 3, "stone": 3},
    "TAVERN_lvl3": {"straw": 2, "wood": 3, "stone": 11, "gold": 1},
    "TAVERN_lvl4": {"straw": 7, "wood": 6, "stone": 16, "gold": 6},
    
    # STRAW_MILL
    "STRAW_MILL_lvl1": {"straw": 6, "wood": 1},
    "STRAW_MILL_lvl2": {"straw": 5, "wood": 6},
    "STRAW_MILL_lvl3": {"straw": 9, "wood": 20, "stone": 3, "gold": 1},
    "STRAW_MILL_lvl4": {"straw": 15, "wood": 35, "stone": 6, "gold": 5},
    
    # SAWMILL
    "SAWMILL_lvl1": {"wood": 1, "stone": 3},
    "SAWMILL_lvl2": {"straw": 3, "wood": 7, "stone": 4},
    "SAWMILL_lvl3": {"straw": 7, "wood": 14, "stone": 14, "gold": 1},
    "SAWMILL_lvl4": {"straw": 6, "wood": 24, "stone": 27, "gold": 6},
    
    # QUARRY
    "QUARRY_lvl1": {"straw": 1, "wood": 1, "stone": 3},
    "QUARRY_lvl2": {"straw": 1, "wood": 3, "stone": 5},
    "QUARRY_lvl3": {"straw": 6, "wood": 7, "stone": 15, "gold": 2},
    "QUARRY_lvl4": {"straw": 7, "wood": 13, "stone": 32, "gold": 6},
    
    # GOLD_MINE
    "GOLD_MINE_lvl1": {"straw": 1, "wood": 1, "stone": 3, "gold": 1},
    "GOLD_MINE_lvl2": {"straw": 2, "wood": 5, "stone": 4},
    "GOLD_MINE_lvl3": {"straw": 6, "wood": 7, "stone": 15, "gold": 3},
    "GOLD_MINE_lvl4": {"straw": 7, "wood": 14, "stone": 40, "gold": 21},
    
    # TOWNHALL (Anki Efficiency Engine)
    "TOWNHALL_lvl1": {"straw": 6, "wood": 2, "stone": 1, "gold": 1},
    "TOWNHALL_lvl2": {"straw": 2, "wood": 14, "stone": 3, "gold": 1},
    "TOWNHALL_lvl3": {"straw": 8, "wood": 26, "stone": 17, "gold": 4},
    "TOWNHALL_lvl4": {"straw": 12, "wood": 26, "stone": 25, "gold": 23},
    
    # CRAFTING_HUT
    "CRAFTING_HUT_lvl2": {"straw": 15, "wood": 10, "stone": 5, "gold": 0},
    "CRAFTING_HUT_lvl3": {"straw": 17, "wood": 11, "stone": 6, "gold": 1},
    "CRAFTING_HUT_lvl4": {"straw": 18, "wood": 12, "stone": 8, "gold": 2},
    "CRAFTING_HUT_lvl5": {"straw": 20, "wood": 13, "stone": 9, "gold": 3}
}

def get_building_upgrade_cost(building_id: str, next_tier: int, haggler_discount: dict = None) -> dict:
    cost_key = f"{building_id}_lvl{next_tier}"
    cost = BUILDING_COSTS.get(cost_key, {})
    if haggler_discount and haggler_discount.get("building_id") == building_id:
        pct = haggler_discount.get("discount_percent", 0)
        discounted = {}
        for res, amt in cost.items():
            if amt > 0:
                discounted[res] = max(1, round(amt * (1 - pct / 100)))
            else:
                discounted[res] = 0
        return discounted
    return cost

# Trade conversions: 3 of current tier to 1 of next tier
TRADE_RULES = {
    ("straw", "wood"): 3,
    ("wood", "stone"): 3,
    ("stone", "gold"): 3
}

def roll_resource(street_lineup: list = None) -> str:
    """Rolls a new resource based on weighted probabilities."""
    has_gold_mine_lvl4 = False
    if street_lineup:
        for cell in street_lineup:
            if cell.get("id") == "GOLD_MINE" and cell.get("tier") == 4:
                has_gold_mine_lvl4 = True
                break
                
    r = random.randint(1, 100)
    if has_gold_mine_lvl4:
        # Lvl 4 Gold Mine: Gold: 10% (91-100), Stone: 14% (77-90), Wood: 33% (44-76), Straw: 43% (1-43)
        if r <= 43:
            return "straw"
        elif r <= 76:
            return "wood"
        elif r <= 90:
            return "stone"
        else:
            return "gold"
    else:
        # Standard: Gold: 5% (96-100), Stone: 15% (81-95), Wood: 35% (46-80), Straw: 45% (1-45)
        if r <= 45:
            return "straw"
        elif r <= 80:
            return "wood"
        elif r <= 95:
            return "stone"
        else:
            return "gold"

def get_double_chance(street_lineup: list, resource_type: str) -> float:
    """
    Calculates the chance of doubling a resource drop based on building tier plus permanent bonuses.
    """
    res_to_building = {
        "straw": "STRAW_MILL",
        "wood": "SAWMILL",
        "stone": "QUARRY",
        "gold": "GOLD_MINE"
    }
    
    target_type = res_to_building.get(resource_type)
    if not target_type:
        return 0.0
        
    max_tier = 0
    extra_bonus = 0.0
    for cell in street_lineup:
        building_id = cell.get("id", "")
        if building_id == target_type:
            tier = cell.get("tier", 1)
            if tier > max_tier:
                max_tier = tier
            extra_bonus += cell.get("extra_double", 0.0)
                
    # Chance mappings: T1 -> 5%, T2 -> 12%, T3 -> 25%, T4 -> 40%
    chance_map = {0: 0.0, 1: 0.05, 2: 0.12, 3: 0.25, 4: 0.40}
    return chance_map.get(max_tier, 0.0) + extra_bonus

def can_afford(resources: dict, cost: dict) -> bool:
    """Checks if the user has enough resources to cover a cost."""
    for res, amount in cost.items():
        if resources.get(res, 0) < amount:
            return False
    return True

def deduct_resources(resources: dict, cost: dict) -> dict:
    """Deducts resources and returns a new resources dictionary."""
    updated = resources.copy()
    for res, amount in cost.items():
        updated[res] = max(0, updated.get(res, 0) - amount)
    return updated

from typing import Optional, Tuple

def apply_artisan_effect(config: dict, artisan_id: str, level: int, threshold: int) -> dict:
    """
    Applies the effect of a specific daily artisan when crossing a review threshold.
    """
    street_lineup = config.get("street_lineup", [])
    if "pending_artisan_notifications" not in config:
        config["pending_artisan_notifications"] = []
        
    if artisan_id == "builder":
        if threshold == 100:
            resource_buildings = {"SAWMILL", "STRAW_MILL", "QUARRY", "GOLD_MINE"}
            # Collect all indices of houses and resource buildings
            valid_indices = [i for i, cell in enumerate(street_lineup) if cell.get("id") in ({"HOUSE"} | resource_buildings)]
            if valid_indices:
                chosen_idx = random.choice(valid_indices)
                cell = street_lineup[chosen_idx]
                b_id = cell.get("id")
                
                if b_id == "HOUSE":
                    bonus = 2 if level == 1 else 5
                    cell["extra_pop"] = cell.get("extra_pop", 0) + bonus
                    config["pending_artisan_notifications"].append(
                        f"🛠️ Builder completed shift! A House got +{bonus} permanent population!"
                    )
                else:
                    bonus_chance = 0.01 if level == 1 else 0.02
                    pct = 1 if level == 1 else 2
                    cell["extra_double"] = cell.get("extra_double", 0.0) + bonus_chance
                    
                    name_map = {
                        "SAWMILL": "Sawmill",
                        "STRAW_MILL": "Straw Mill",
                        "QUARRY": "Quarry",
                        "GOLD_MINE": "Gold Mine"
                    }
                    b_name = name_map.get(b_id, b_id.replace("_", " ").capitalize())
                    config["pending_artisan_notifications"].append(
                        f"🛠️ Builder completed shift! A {b_name} got +{pct}% permanent double-drop chance!"
                    )
    elif artisan_id == "merchant":
        if threshold in [100, 200]:
            num_drops = 1 if level == 1 else 2
            drops = []
            resources = config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0})
            for _ in range(num_drops):
                res = roll_resource(street_lineup)
                resources[res] = resources.get(res, 0) + 1
                drops.append(res)
            config["resources"] = resources
            emoji_map = {"straw": "🌾", "wood": "🪵", "stone": "🪨", "gold": "🪙"}
            drop_strs = [f"{emoji_map.get(d, '📦')} {d.capitalize()}" for d in drops]
            config["pending_artisan_notifications"].append(
                f"🪙 Merchant found drops at {threshold} reviews: {', '.join(drop_strs)}!"
            )
    elif artisan_id == "haggler":
        if threshold == 100:
            buildings = ["HOUSE", "SAWMILL", "TAVERN", "TOWNHALL", "STRAW_MILL", "QUARRY", "GOLD_MINE", "CRAFTING_HUT"]
            chosen_b = random.choice(buildings)
            discount = 10 if level == 1 else 15
            config["haggler_discount"] = {
                "building_id": chosen_b,
                "discount_percent": discount
            }
            b_name = chosen_b.replace("_", " ").capitalize()
            config["pending_artisan_notifications"].append(
                f"🏷️ Haggler secured {discount}% discount on all {b_name} upgrades!"
            )
    elif artisan_id == "alchemist":
        if threshold == 100:
            resources = config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0})
            if resources.get("straw", 0) >= 1:
                resources["straw"] -= 1
                if level == 1:
                    resources["stone"] = resources.get("stone", 0) + 1
                    config["pending_artisan_notifications"].append(
                        "🧪 Alchemist transmuted: 🌾 1x Straw ➔ 🪨 1x Stone!"
                    )
                else:
                    resources["gold"] = resources.get("gold", 0) + 1
                    config["pending_artisan_notifications"].append(
                        "🧪 Alchemist transmuted: 🌾 1x Straw ➔ 🪙 1x Gold!"
                    )
                config["resources"] = resources
            else:
                config["pending_artisan_notifications"].append(
                    "🧪 Alchemist tried to transmute, but you had no Straw!"
                )
    return config

def process_card_answer(config: dict) -> Tuple[dict, Optional[str], bool]:
    """
    Decrements review counter, rolls resources, and calculates passive multipliers.
    Returns (updated_config, awarded_resource_or_none, was_doubled_bool).
    """
    street_lineup = config.get("street_lineup", [])
    
    # Process active artisan reviews
    active_artisan = config.get("active_artisan")
    reviews_remaining = config.get("artisan_reviews_remaining", 0)
    
    if active_artisan and reviews_remaining > 0:
        reviews_remaining -= 1
        config["artisan_reviews_remaining"] = reviews_remaining
        
        clicked = config.get("artisan_reviews_clicked", 0) + 1
        config["artisan_reviews_clicked"] = clicked
        
        levels = config.get("artisan_levels", {"builder": 1, "merchant": 1, "haggler": 1, "alchemist": 1})
        level = levels.get(active_artisan, 1)
        
        if clicked in [100, 200]:
            config = apply_artisan_effect(config, active_artisan, level, clicked)
                    
        if reviews_remaining <= 0:
            config["active_artisan"] = None
            if "pending_artisan_notifications" not in config:
                config["pending_artisan_notifications"] = []
            config["pending_artisan_notifications"].append(
                f"👋 {active_artisan.capitalize()}'s shift has ended!"
            )

    # Calculate current Town Hall tier and set dynamic cards per resource
    town_hall_tier = 1
    for cell in street_lineup:
        if cell.get("id", "") == "TOWNHALL":
            town_hall_tier = cell.get("tier", 1)
            break
            
    reps_map = {1: 20, 2: 19, 3: 17, 4: 15}
    cards_per_resource = reps_map.get(town_hall_tier, 20)
    config["cards_per_resource"] = cards_per_resource
    
    # Decrement counter
    current = config.get("current_counter", 20) - 1
    
    # Clamp counter if it somehow exceeds the new cards_per_resource
    if current > cards_per_resource:
        current = cards_per_resource
        
    awarded = None
    doubled = False
    
    if current <= 0:
        # Reset counter
        current = cards_per_resource
        
        # Award the current 'next_resource'
        awarded = config.get("next_resource", "straw")
        quantity = 1
        
        # Check double drop logic
        chance = get_double_chance(street_lineup, awarded)
        if chance > 0 and random.random() < chance:
            quantity = 2
            doubled = True
            
        # Add to resources
        resources = config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0})
        resources[awarded] = resources.get(awarded, 0) + quantity
        config["resources"] = resources
        
        # Roll a NEW 'next_resource'
        config["next_resource"] = roll_resource(street_lineup)
            
    config["current_counter"] = current
    return config, awarded, doubled

def trade_resources(resources: dict, from_res: str, to_res: str, street_lineup: list = None) -> tuple[bool, dict, str]:
    """
    Executes a trade: exchange 3 of 'from_res' for 1 of 'to_res'.
    If Tavern level is 4, allows:
      - 1 Gold -> 3 Stone (Lossless)
      - 1 Stone -> 2 Wood (Taxed)
    Returns (success_bool, updated_resources_dict, message_str).
    """
    rule_key = (from_res, to_res)
    
    # Reverse trade rules: (from, to) -> yield
    reverse_rules = {
        ("gold", "stone"): 3,
        ("stone", "wood"): 2
    }
    
    if rule_key in reverse_rules:
        # Check Tavern tier (must be >= 4 for reverse trading)
        tavern_tier = 1
        if street_lineup:
            for cell in street_lineup:
                if cell.get("id") == "TAVERN":
                    tavern_tier = cell.get("tier", 1)
                    break
        if tavern_tier < 4:
            return False, resources, "Requires a Level 4 Tavern to reverse trade."
            
        cost = 1
        gain = reverse_rules[rule_key]
        if resources.get(from_res, 0) < cost:
            return False, resources, f"Insufficient {from_res.capitalize()}."
            
        updated = resources.copy()
        updated[from_res] -= cost
        updated[to_res] = updated.get(to_res, 0) + gain
        return True, updated, f"Successfully traded 1x {from_res.capitalize()} for {gain}x {to_res.capitalize()}."
        
    if rule_key not in TRADE_RULES:
        return False, resources, "Invalid trade path."
        
    cost = TRADE_RULES[rule_key]
    if resources.get(from_res, 0) < cost:
        return False, resources, f"Insufficient {from_res.capitalize()}."
        
    updated = resources.copy()
    updated[from_res] -= cost
    updated[to_res] = updated.get(to_res, 0) + 1
    
    return True, updated, f"Successfully traded {cost}x {from_res.capitalize()} for 1x {to_res.capitalize()}."


def can_upgrade_building(street_lineup: list, index: int, next_tier: int) -> tuple[bool, str]:
    """
    Checks if a building upgrade is allowed based on population gates.
    Returns (allowed_bool, error_message_str).
    """
    if not (0 <= index < len(street_lineup)):
        return False, "Invalid building index."
        
    cell = street_lineup[index]
    b_id = cell.get("id")
    
    # We only gate the 4 resource production buildings: SAWMILL, STRAW_MILL, QUARRY, GOLD_MINE
    resource_buildings = {"SAWMILL", "STRAW_MILL", "QUARRY", "GOLD_MINE"}
    if b_id not in resource_buildings:
        return True, ""
        
    # Count how many OTHER resource buildings are already at or above next_tier before the upgrade
    k_other = sum(1 for c in street_lineup if c.get("id") in resource_buildings and c.get("tier", 1) >= next_tier)
    
    # Calculate required population based on updated progression gates
    if next_tier == 2:
        req_pop = 45 + 10 * k_other
    elif next_tier == 3:
        req_pop = 120 + 20 * k_other
    elif next_tier == 4:
        req_pop = 300 + 40 * k_other
    else:
        return True, ""
        
    # Get current population (before the upgrade)
    current_pop = get_population(street_lineup)
    
    if current_pop < req_pop:
        name_map = {
            "SAWMILL": "Sawmill",
            "STRAW_MILL": "Straw Mill",
            "QUARRY": "Quarry",
            "GOLD_MINE": "Gold Mine"
        }
        b_name = name_map.get(b_id, b_id)
        return False, f"Requires {req_pop} population to upgrade to a Level {next_tier} {b_name} (Current: {current_pop}). Upgrade your Houses to increase population!"
        
    return True, ""


def get_population(street_lineup: list) -> int:
    """Calculates total city population based on building types and levels."""
    pop = 0
    for cell in street_lineup:
        b_id = cell.get("id")
        tier = cell.get("tier", 1)
        if b_id == "HOUSE":
            if tier == 1:
                pop += 5
            elif tier == 2:
                pop += 15
            elif tier == 3:
                pop += 50
            elif tier == 4:
                pop += 120
        elif b_id == "TOWNHALL":
            if tier == 1:
                pop += 10
            elif tier == 2:
                pop += 30
            elif tier == 3:
                pop += 100
            elif tier == 4:
                pop += 250
    return pop


def check_milestones(config: dict) -> dict:
    """Checks for new population milestones and awards 5 random resources if met."""
    street_lineup = config.get("street_lineup", [])
    pop = get_population(street_lineup)
    
    last_milestone = config.get("last_milestone_claimed", 0)
    pending = config.get("pending_milestones", [])
    
    # Check all milestone thresholds of 100 up to current population
    current_threshold = 100
    while current_threshold <= pop:
        if current_threshold > last_milestone:
            # We hit a new milestone threshold! Roll resources using standard roll_resource
            num_rewards = 5 + (current_threshold - 100) // 100
            rewards_list = []
            for _ in range(num_rewards):
                rewards_list.append(roll_resource(street_lineup))
            
            # Count the rolled rewards
            counts = {"straw": 0, "wood": 0, "stone": 0, "gold": 0}
            for r in rewards_list:
                counts[r] = counts.get(r, 0) + 1
                
            # Add resources to player inventory immediately
            resources = config.get("resources", {"straw": 0, "wood": 0, "stone": 0, "gold": 0})
            for r, c in counts.items():
                resources[r] = resources.get(r, 0) + c
            config["resources"] = resources
            
            # Add to pending milestones for UI display
            pending.append({
                "threshold": current_threshold,
                "rewards": counts
            })
            
            # Update last_milestone_claimed
            last_milestone = current_threshold
            
        current_threshold += 100
        
    config["last_milestone_claimed"] = last_milestone
    config["pending_milestones"] = pending
    return config
