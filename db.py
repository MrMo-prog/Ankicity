# Database and Streak Utilities for Anki-City
from aqt import mw

def get_streak(installation_time: int = 0) -> int:
    """
    Calculates the current consecutive study streak in days.
    Adjusts review timestamps using Anki's scheduler cutoff time to handle 
    timezones and the user's custom 'Next day starts at' setting.
    """
    if not mw.col or installation_time <= 0:
        return 0

    try:
        # Get the current scheduler day cutoff timestamp in seconds
        cutoff = mw.col.sched.day_cutoff
        
        # Limit reviews query to the last 365 days to keep execution extremely fast
        time_limit_ms = (cutoff - 365 * 86400) * 1000
        
        # Determine installation threshold
        installation_time_ms = installation_time * 1000
        
        # Query distinct days represented as relative integer offsets from cutoff
        # Filter reviews to only count those completed after the installation timestamp
        days = mw.col.db.list(
            "SELECT DISTINCT CAST((id/1000 - ?) / 86400 AS INTEGER) "
            "FROM revlog "
            "WHERE id > ? AND id > ? AND (id/1000 - ?) / 86400 < 1 "
            "ORDER BY id DESC",
            cutoff,
            time_limit_ms,
            installation_time_ms,
            cutoff
        )
        
        if not days:
            return 0

        # Create a set of relative days.
        # Map any day index >= -1 to -1 to handle potential clock skews safely.
        days_set = {d if d < -1 else -1 for d in days}
        
        streak = 0
        # If they reviewed today
        if -1 in days_set:
            streak = 1
            check_day = -2
            while check_day in days_set:
                streak += 1
                check_day -= 1
        # If they haven't reviewed today yet, but did yesterday (streak is still active)
        elif -2 in days_set:
            streak = 1
            check_day = -3
            while check_day in days_set:
                streak += 1
                check_day -= 1
        else:
            streak = 0
            
        return streak
        
    except Exception as e:
        print(f"Anki-City: Error calculating streak: {e}")
        return 0
