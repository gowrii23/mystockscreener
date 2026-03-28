import pandas as pd
from datetime import datetime, timedelta

class StaleDataError(Exception):
    pass

def check_data_freshness(csv_path: str, max_age_days: int = 7) -> tuple[bool, str]:
    """
    Checks the freshness of the qualified_universe.csv file.
    Returns (is_fresh, message).
    """
    try:
        df = pd.read_csv(csv_path)
        last_updated_str = df['last_updated'].iloc[0]
        last_updated = pd.to_datetime(last_updated_str)
        age = datetime.now() - last_updated

        if age > timedelta(days=max_age_days):
            message = f"StaleDataError: qualified_universe.csv is {age.days} days old. Run Engine A."
            return False, message
        
        return True, f"Data is fresh ({age.days} days old)."

    except (FileNotFoundError, IndexError, KeyError) as e:
        return False, f"Could not check data freshness: {e}"
