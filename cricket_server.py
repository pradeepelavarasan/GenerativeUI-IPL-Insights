import os
import sys
import json
import logging
import datetime
import subprocess
import requests
import time
from google import genai
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths and logger
BASE_DIR = "/Users/pradeep/Library/CloudStorage/OneDrive-Personal/ML/2026 ML Projects/IPL 2026 Insights v2"
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Shared memory paths for Zero-Argument architecture (Fixed safeParse bug)
SHARED_DATA_PATH = os.path.join(BASE_DIR, "latest_data.json")
SHARED_CODE_PATH = os.path.join(BASE_DIR, "generated_app.py")

logger = logging.getLogger("IPL_Server_V2")
logger.setLevel(logging.DEBUG)

def setup_session_logger():
    session_id = os.environ.get("SESSION_ID")
    if not session_id:
        session_id = f"session_{datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"
    log_file = os.path.join(LOG_DIR, f"{session_id}.log")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)
    return session_id

# 🆕 Modern GenAI Client (Matches AgenticMCPUse.py standard)
genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = os.getenv("MODEL", "gemini-1.5-flash")

API_RESPONSES_DIR = os.path.join(BASE_DIR, "api_responses")
os.makedirs(API_RESPONSES_DIR, exist_ok=True)

# Initialize FastMCP server
mcp = FastMCP("Cricket Insights V2")

# =================================================================
# TOOL 1: FETCH POINTS TABLE
# =================================================================
@mcp.tool()
def get_points_table() -> str:
    """Fetches the current IPL 2026 points table from CricAPI."""
    setup_session_logger()
    logger.info("[STEP 1: API] Fetching IPL Points Table")
    try:
        api_key = os.environ.get("cricketdata_key")
        url = f"https://api.cricapi.com/v1/series_points?apikey={api_key}&id=76f0d2c9-63a2-4a7b-a113-d49d0123"
        resp = requests.get(url)
        data = resp.json()
        
        # Log to individual file for history
        filename = f"points_table_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(os.path.join(API_RESPONSES_DIR, filename), "w") as f:
            json.dump(data, f)

        # Save to Shared Memory for the Zero-Argument bridge
        with open(SHARED_DATA_PATH, "w") as f:
            json.dump(data, f)
            
        logger.info("[STEP 1: API] Success. Saved to latest_data.json")
        return "Success"
    except Exception as e:
        logger.error(f"[STEP 1: API] Error: {str(e)}")
        return f"Error: {str(e)}"

# =================================================================
# TOOL 2: FETCH PLAYER STATISTICS
# =================================================================
@mcp.tool()
def get_player_stats(player_name: str) -> str:
    """Fetches career statistics for a specific player."""
    setup_session_logger()
    logger.info(f"[STEP 1: API] Fetching stats for player: {player_name}")
    try:
        api_key = os.environ.get("cricketdata_key")
        search_url = f"https://api.cricapi.com/v1/players?apikey={api_key}&offset=0&search={player_name}"
        search_resp = requests.get(search_url).json()
        
        if not search_resp.get("data"):
            return "Error: Player not found"
            
        player_id = search_resp["data"][0]["id"]
        info_url = f"https://api.cricapi.com/v1/players_info?apikey={api_key}&id={player_id}"
        info_resp = requests.get(info_url).json()
        
        # Log to individual file
        filename = f"player_{player_name.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(os.path.join(API_RESPONSES_DIR, filename), "w") as f:
            json.dump(info_resp, f)

        # Save to Shared Memory
        with open(SHARED_DATA_PATH, "w") as f:
            json.dump(info_resp, f)
            
        logger.info("[STEP 1: API] Success. Saved to latest_data.json")
        return "Success"
    except Exception as e:
        return f"Error: {str(e)}"

# =================================================================
# TOOL 3: APP ARCHITECT (Zero-Argument Stability)
# =================================================================
@mcp.tool()
def agentic_render() -> str:
    """Generates a dynamic dashboard using a two-stage Analyst-Architect pattern."""
    setup_session_logger()
    start_time = time.perf_counter()
    logger.info(f"[STEP 2: RENDER] Starting Analyst-Architect process via {MODEL_NAME}...")
    
    try:
        if not os.path.exists(SHARED_DATA_PATH):
            logger.error("[STEP 2: RENDER] Shared data file not found.")
            return json.dumps({"status": "error", "message": "No data found"})
            
        with open(SHARED_DATA_PATH, "r") as f:
            data_str = f.read()

        prompt = f"""
        STAGE 1: ANALYST
        Analyze this player's JSON data: {data_str}
        1. Identify the player's primary role (e.g., Opening Batsman, Death Bowler, All-rounder).
        2. Select exactly the Top 10 most impactful metrics.
        
        STAGE 2: ARCHITECT
        Generate a PURE PREFAB UI dashboard (Python code) for ONLY those 10 metrics.
        
        RULES:
        1. DO NOT use streamlit or st.
        2. Use ONLY prefab_ui components.
        3. Imports: 
           from prefab_ui.app import PrefabApp
           from prefab_ui.components import (Card, CardHeader, CardContent, CardTitle, CardDescription, H1, H2, H3, Text, Row, Column, Metric, Badge, Separator)
        
        4. CONTEXT MANAGER RULES (CRITICAL):
           - ONLY use 'with' for: Card, CardContent, Row, Column.
           - NEVER use 'with' for: Metric, Separator, Text, Badge, H1, H2, H3, CardHeader, CardTitle, CardDescription.
           - Example: 
             with Row():
                 Metric(label="X", value="Y") # NO 'with' here!
             Separator() # NO 'with' here!
        
        5. COMPONENT RULES:
           - Metric MUST use keyword arguments: Metric(label="Name", value="Value").
           - Every 'with' block MUST contain at least one component.
        
        6. DASHBOARD LAYOUT:
           - Use a main Card as the 'view'.
           - End with 'app = PrefabApp(view=view)'.
        """
        
        # Using the NEW SDK generation pattern (google-genai v1)
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={'temperature': 0.1}
        )
        
        code = response.text.strip()
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
            
        with open(SHARED_CODE_PATH, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Spawn Prefab Service
        os.system("pkill -f 'prefab serve'")
        prefab_bin = os.path.join(BASE_DIR, "venv", "bin", "prefab")
        
        # Capture stderr to log startup crashes
        log_file = os.path.join(BASE_DIR, "logs", "prefab_startup.log")
        # Suppress auto-open behavior by setting BROWSER=none
        env = os.environ.copy()
        env["BROWSER"] = "none"
        
        with open(log_file, "w") as f_err:
            subprocess.Popen([prefab_bin, "serve", "generated_app.py", "--port", "5175"], 
                             cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=f_err, env=env)
            
        # Poll Port 5175 until ready (max 10s)
        logger.info("[STEP 2: RENDER] Waiting for Prefab server to bind to port 5175...")
        import socket
        success = False
        for _ in range(20): # 20 * 0.5s = 10s
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", 5175)) == 0:
                    logger.info("[STEP 2: RENDER] Server ready.")
                    success = True
                    break
            time.sleep(0.5)
        
        if success:
            logger.info("[STEP 2: RENDER] Dashboard ready for iframe injection.")
        else:
            with open(log_file, "r") as f:
                err_msg = f.read()
            logger.error(f"[STEP 2: RENDER] Prefab failed to start: {err_msg}")
            return json.dumps({"status": "error", "message": f"Server crash: {err_msg}"})
        
        end_time = time.perf_counter()
        render_duration = end_time - start_time
        logger.info(f"[STEP 2: RENDER] Success. Render Time: {render_duration:.2f}s")
        
        return json.dumps({
            "status": "success", 
            "blueprint": {
                "action": "refresh_iframe",
                "url": "http://127.0.0.1:5175"
            },
            "render_time": f"{render_duration:.2f}s",
            "metrics_count": 10
        })
    except Exception as e:
        logger.error(f"[STEP 2: RENDER] Fatal Error: {str(e)}")
        return json.dumps({"status": "error", "message": str(e)})

# =================================================================
# TOOL 4: SESSION STORAGE
# =================================================================
@mcp.tool()
def save_history_entry() -> str:
    """Archives the finalized dashboard code to the history folder."""
    setup_session_logger()
    logger.info("[STEP 3: STORAGE] Archiving dashboard to history/ folder...")
    try:
        if not os.path.exists(SHARED_DATA_PATH) or not os.path.exists(SHARED_CODE_PATH):
            return json.dumps({"status": "error", "message": "Missing data or code to archive"})

        with open(SHARED_DATA_PATH, "r") as f:
            data = json.load(f)
        with open(SHARED_CODE_PATH, "r") as f:
            code = f.read()

        # Create history directory
        history_dir = os.path.join(BASE_DIR, "history")
        os.makedirs(history_dir, exist_ok=True)

        # Generate professional filename: YYYYMMDD_HHMMSS_PlayerName.py
        # Smart extraction: check 'data' -> 'name' or 'player' -> 'name'
        player_name = "Unknown_Player"
        if isinstance(data.get("data"), dict):
            player_name = data["data"].get("name", "Unknown_Player")
        elif isinstance(data.get("player"), dict):
            player_name = data["player"].get("name", "Unknown_Player")
        
        player_name = player_name.replace(" ", "_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{player_name}.py"
        filepath = os.path.join(history_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        logger.info(f"[STEP 3: STORAGE] Success. Archived to {filename}")
        return json.dumps({
            "status": "success", 
            "archive_path": filename,
            "player": player_name
        })
    except Exception as e:
        logger.error(f"[STEP 3: STORAGE] Error: {str(e)}")
        return json.dumps({"status": "error", "message": str(e)})

# =================================================================
# TOOL 5: HISTORICAL PLAYBACK
# =================================================================
@mcp.tool()
def render_stored_code(code: str) -> str:
    """Renders previously generated code from history."""
    setup_session_logger()
    logger.info("[PLAYBACK] Rendering stored code")
    try:
        with open(SHARED_CODE_PATH, "w", encoding="utf-8") as f:
            f.write(code)
        
        os.system("pkill -f 'prefab serve'")
        prefab_bin = os.path.join(BASE_DIR, "venv", "bin", "prefab")
        env = os.environ.copy()
        env["BROWSER"] = "none"
        
        subprocess.Popen([prefab_bin, "serve", "generated_app.py", "--port", "5175"], 
                         cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        
        # webbrowser.open("http://127.0.0.1:5175")
        return json.dumps({"status": "success", "url": "http://127.0.0.1:5175"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    mcp.run()
