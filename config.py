import os
import ast
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # --- Server Configuration ---
    PORT = int(os.environ.get("PORT", 5000))
    HOST = os.environ.get("HOST", "0.0.0.0")

    # --- Location Configuration ---
    # AUTO_LOCATION: If True, dynamically resolves location (lat, lon, city, timezone) via IP
    AUTO_LOCATION = os.environ.get("AUTO_LOCATION", "True").lower() in ("true", "1", "yes")
    # Fallback coordinates & city if AUTO_LOCATION is False or IP lookup fails
    LATITUDE = float(os.environ.get("LATITUDE", "39.90420"))
    LONGITUDE = float(os.environ.get("LONGITUDE", "116.40740"))
    CITY_NAME = os.environ.get("CITY_NAME", "Beijing")
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Shanghai")

    # --- Screen Configuration ---
    SCREEN_WIDTH = int(os.environ.get("SCREEN_WIDTH", 1680))
    SCREEN_HEIGHT = int(os.environ.get("SCREEN_HEIGHT", 1264))
    
    # --- Renderer Configuration ---
    RENDER_TIMEOUT = int(os.environ.get("RENDER_TIMEOUT", 60000))

    # --- Locale & Localization ---
    LANGUAGE = os.environ.get("LANGUAGE", "CN") # CN or EN
    HOLIDAY_COUNTRY = os.environ.get("HOLIDAY_COUNTRY", "CN") # Country code for `holidays` library
    
    # --- Cache Durations (in seconds) ---
    CACHE_TTL_WEATHER = int(os.environ.get("CACHE_TTL_WEATHER", 600))     # 10 minutes
    CACHE_TTL_RENDER = int(os.environ.get("CACHE_TTL_RENDER", 60))        # 1 minute

    # --- Work/Commute Logic ---
    WORK_START_HOUR = int(os.environ.get("WORK_START_HOUR", 10))
    WORK_END_HOUR = int(os.environ.get("WORK_END_HOUR", 18))

    # --- Todo System Configuration ---
    TODO_DATA_DIR = os.environ.get("TODO_DATA_DIR", "data")
