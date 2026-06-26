# Database and Streak Utilities for Anki-City
from aqt import mw

def get_today_reviews() -> int:
    """
    Counts the number of card reviews completed today (in the current scheduler day).
    """
    if not mw.col:
        return 0
    try:
        cutoff = mw.col.sched.day_cutoff
        start_of_day_ms = (cutoff - 86400) * 1000
        count = mw.col.db.scalar(
            "SELECT count(*) FROM revlog WHERE id >= ?",
            start_of_day_ms
        )
        return count or 0
    except Exception as e:
        print(f"Anki-City: Error getting today's reviews: {e}")
        return 0

def get_streak_details(installation_time: int = 0) -> dict:
    """
    Calculates the current consecutive study streak in days and today's current milestone.
    A day is only counted in the study streak if it has at least 50 reviews.
    """
    if not mw.col:
        return {"days": 0, "milestone": 0}

    try:
        # Get the current scheduler day cutoff timestamp in seconds
        cutoff = mw.col.sched.day_cutoff
        
        # Limit reviews query to the last 365 days to keep execution extremely fast
        time_limit_ms = (cutoff - 365 * 86400) * 1000
        
        # Query raw review timestamps from SQLite
        # id represents the review time in milliseconds
        timestamps = mw.col.db.list(
            "SELECT id/1000 "
            "FROM revlog "
            "WHERE id > ? "
            "ORDER BY id DESC",
            time_limit_ms
        )
        
        if not timestamps:
            return {"days": 0, "milestone": 0}

        import math
        # Count reviews per relative day
        day_counts = {}
        for ts in timestamps:
            d = math.floor((ts - cutoff) / 86400.0)
            if d < 1:  # Only count days before the next cutoff
                actual_d = d if d < -1 else -1
                day_counts[actual_d] = day_counts.get(actual_d, 0) + 1
        
        # Calculate yesterday's streak (consecutive days of >= 50 reviews prior to today)
        yesterday_streak = 0
        check_day = -2
        while day_counts.get(check_day, 0) >= 50:
            yesterday_streak += 1
            check_day -= 1
            
        today_reviews = day_counts.get(-1, 0)
        if today_reviews >= 50:
            days = yesterday_streak + 1
            
            # Milestone is determined based only on today's reviews
            if today_reviews >= 500:
                milestone = 500
            elif today_reviews >= 200:
                milestone = 200
            elif today_reviews >= 100:
                milestone = 100
            else:
                milestone = 50
        else:
            days = yesterday_streak
            milestone = 0
            
        return {"days": days, "milestone": milestone}
        
    except Exception as e:
        print(f"Anki-City: Error calculating streak details: {e}")
        return {"days": 0, "milestone": 0}

def get_streak(installation_time: int = 0) -> int:
    """Calculates the current consecutive study streak in days."""
    return get_streak_details(installation_time)["days"]
