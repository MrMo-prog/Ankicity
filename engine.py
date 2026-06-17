# Game Mechanics and Reward Engine for Anki-City
import random

# Building Cost Definitions
BUILDING_COSTS = {
    # HOUSE
    "HOUSE_lvl1": {"straw": 4},
    "HOUSE_lvl2": {"straw": 8, "wood": 1},
    "HOUSE_lvl3": {"wood": 8, "stone": 4, "gold": 1},
    "HOUSE_lvl4": {"stone": 16, "wood": 8, "gold": 2},
    
    # TAVERN (Marketplace replacement)
    "TAVERN_lvl1": {"wood": 8, "straw": 3},
    "TAVERN_lvl2": {"wood": 5, "straw": 4},
    "TAVERN_lvl3": {"wood": 20, "stone": 12, "gold": 1},
    "TAVERN_lvl4": {"wood": 36, "stone": 28, "gold": 4},
    
    # STRAW_MILL
    "STRAW_MILL_lvl1": {"straw": 4},
    "STRAW_MILL_lvl2": {"straw": 5, "wood": 2},
    "STRAW_MILL_lvl3": {"straw": 16, "wood": 6, "stone": 2},
    "STRAW_MILL_lvl4": {"straw": 32, "wood": 12, "stone": 8, "gold": 2},
    
    # SAWMILL
    "SAWMILL_lvl1": {"wood": 8},
    "SAWMILL_lvl2": {"wood": 10, "straw": 3},
    "SAWMILL_lvl3": {"wood": 16, "stone": 10, "gold": 1},
    "SAWMILL_lvl4": {"wood": 32, "stone": 22, "gold": 6},
    
    # QUARRY
    "QUARRY_lvl1": {"stone": 8},
    "QUARRY_lvl2": {"stone": 10, "straw": 3},
    "QUARRY_lvl3": {"stone": 16, "wood": 10, "gold": 1},
    "QUARRY_lvl4": {"stone": 32, "wood": 22, "gold": 6},
    
    # GOLD_MINE
    "GOLD_MINE_lvl1": {"stone": 12, "wood": 8},
    "GOLD_MINE_lvl2": {"stone": 6, "wood": 4, "straw": 3},
    "GOLD_MINE_lvl3": {"gold": 3, "stone": 22, "wood": 14},
    "GOLD_MINE_lvl4": {"gold": 10, "stone": 38, "wood": 22},
    
    # TOWNHALL (Anki Efficiency Engine)
    "TOWNHALL_lvl1": {"wood": 4, "straw": 4},
    "TOWNHALL_lvl2": {"wood": 12, "stone": 2, "straw": 4},
    "TOWNHALL_lvl3": {"wood": 24, "stone": 14, "gold": 2},
    "TOWNHALL_lvl4": {"stone": 42, "gold": 8}
}

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
    Calculates the chance of doubling a resource drop based on building tier.
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
    for cell in street_lineup:
        building_id = cell.get("id", "")
        if building_id == target_type:
            tier = cell.get("tier", 1)
            if tier > max_tier:
                max_tier = tier
                
    # Chance mappings: T1 -> 5%, T2 -> 12%, T3 -> 25%, T4 -> 40%
    chance_map = {0: 0.0, 1: 0.05, 2: 0.12, 3: 0.25, 4: 0.40}
    return chance_map.get(max_tier, 0.0)

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

def process_card_answer(config: dict) -> Tuple[dict, Optional[str], bool]:
    """
    Decrements review counter, rolls resources, and calculates passive multipliers.
    Returns (updated_config, awarded_resource_or_none, was_doubled_bool).
    """
    street_lineup = config.get("street_lineup", [])
    
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

def trade_resources(resources: dict, from_res: str, to_res: str) -> tuple[bool, dict, str]:
    """
    Executes a trade: exchange 3 of 'from_res' for 1 of 'to_res'.
    Returns (success_bool, updated_resources_dict, message_str).
    """
    rule_key = (from_res, to_res)
    if rule_key not in TRADE_RULES:
        return False, resources, "Invalid trade path."
        
    cost = TRADE_RULES[rule_key]
    if resources.get(from_res, 0) < cost:
        return False, resources, f"Insufficient {from_res.capitalize()}."
        
    updated = resources.copy()
    updated[from_res] -= cost
    updated[to_res] = updated.get(to_res, 0) + 1
    
    return True, updated, f"Successfully traded {cost}x {from_res.capitalize()} for 1x {to_res.capitalize()}."


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
            # We hit a new milestone threshold! Roll 5 resources using standard roll_resource
            rewards_list = []
            for _ in range(5):
                rewards_list.append(roll_resource(street_lineup))
            
            # Count the rolled rewards
            counts = {"straw": 0, "wood": 0, "stone": 0, "gold": 0}
            for r in rewards_list:
                counts[r] += 1
                
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
