import os
import json
import logging
import uuid
import datetime
import sys
import subprocess
import httpx
from dotenv import load_dotenv
import google.generativeai as genai
# from openai import OpenAI

# --- Setup ---
load_dotenv()
BASE_DIR = "/Users/pradeep/Library/CloudStorage/OneDrive-Personal/ML/2026 ML Projects/IPL 2026 Insights v2"
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

session_id = "default"
for i, arg in enumerate(sys.argv):
    if arg == "--session" and i + 1 < len(sys.argv):
        session_id = sys.argv[i+1]
        break

log_filename = os.path.join(BASE_DIR, "logs", f"session_{session_id}.log")
logger = logging.getLogger("IPL_Server_V2")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_filename, mode='a')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL_NAME = os.getenv("MODEL", "gemini-2.5-flash") # Fallback to gemini if not specified
# nv_client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY) if NVIDIA_API_KEY else None

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

API_KEY = os.getenv("cricketdata_key")

# =================================================================
# TOOL 1: INQUIRING ABOUT CRICKET INFORMATION
# =================================================================
def smart_query(user_input: str) -> str:
    logger.info(f"[STEP 1: API] Fetching '{user_input}'")
    try:
        base_url = "https://api.cricapi.com/v1"
        if any(k in user_input.lower() for k in ["points", "table", "standings"]):
            r = httpx.get(f"{base_url}/series_points?apikey={API_KEY}&id=87c62aac-bc3c-4738-ab93-19da0690488f", timeout=15.0)
            data = {"type": "PointsTable", "title": "IPL 2026 Standings", "headers": ["Team", "P", "W", "L", "NRR", "Pts"], "rows": [dict(zip(["team", "p", "w", "l", "nrr", "pts"], [t.get("teamname"), str(t.get("matches")), str(t.get("wins")), str(t.get("loss")), str(t.get("netrr")), str(t.get("pts"))])) for t in r.json().get("data", [])]}
        else:
            name = user_input.replace("info", "").strip()
            r_s = httpx.get(f"{base_url}/players?apikey={API_KEY}&search={name}", timeout=15.0)
            pid = r_s.json()["data"][0]["id"]
            details = httpx.get(f"{base_url}/players_info?apikey={API_KEY}&id={pid}", timeout=15.0).json()["data"]
            data = {"type": "PlayerProfile", "name": details.get("name"), "country": details.get("country"), "role": details.get("role"), "stats": details.get("stats", []), "playerImg": details.get("playerImg", "")}
        logger.info(f"[STEP 1: API] Status: Success")
        return json.dumps(data)
    except Exception as e:
        logger.error(f"[STEP 1: API] Status: Failed - {e}")
        return json.dumps({"error": str(e)})

# =================================================================
# TOOL 2: COMMITTING THE HISTORY ENTRY
# =================================================================
def save_history_entry(data_str: str) -> str:
    logger.info("[STEP 3: STORAGE] Committing to history")
    try:
        data = json.loads(data_str)
        eid = str(uuid.uuid4())
        h_path = os.path.join(BASE_DIR, "ipl_history_v2.json")
        history = json.load(open(h_path)) if os.path.exists(h_path) else {}
        history[eid] = {"id": eid, "data": data, "type": data.get("type"), "timestamp": datetime.datetime.now().isoformat()}
        json.dump(history, open(h_path, "w"), indent=4)
        logger.info(f"[STEP 3: STORAGE] Status: Success")
        return eid
    except Exception as e:
        logger.error(f"[STEP 3: STORAGE] Status: Failed - {e}")
        return "Error"

# =================================================================
# TOOL 3: APP ARCHITECT (WRITES AND RUNS generated_app.py)
# =================================================================
def agentic_render(data_str):
    logger.info(f"[STEP 2: RENDER] The App Architect is generating the Prefab App...")
    
    prompt = f"""
    You are the App Architect. Your goal is to write a complete, standalone Python file using the `prefab_ui` library to visualize the provided data.
    
    DATA TO RENDER:
    {data_str}
    
    COMPONENTS AVAILABLE (`prefab_ui.components`):
    - Badge, Button, Card, CardContent, CardHeader, CardTitle
    - Checkbox, Column, H1, H2, H3, Muted, Progress, Ring, Row
    - Tab, Tabs, Text
    
    RULES:
    1. Output your code wrapped in a ```python ... ``` markdown block. Do not output raw text without the block.
    2. Start the file by importing `PrefabApp` and the necessary components from `prefab_ui.components`.
    3. CRITICAL: You MUST use context managers (`with`) for all nested components. DO NOT use `.add()` or `children=[...]` arrays!
    4. CRITICAL: DO NOT import or use any chart components (like BarChart, ChartSeries, etc.). They are currently unsupported and will crash the app. Use only basic Layouts and Cards.
    5. CRITICAL: DO NOT wrap the `with PrefabApp(...)` block inside a `def main():` function. It MUST be at the root module level so the prefab CLI can find it. Do NOT include `if __name__ == '__main__':`.
       
       CORRECT EXAMPLE:
       with PrefabApp(css_class="max-w-5xl mx-auto p-6") as app:
           with Column(gap=4):
               with Card():
                   with CardHeader():
                       CardTitle('Insights')
                   with CardContent():
                       H1('Stats')
                       Text('Values')

    4. Design a clean, professional dashboard for the provided cricket data using this strict context-manager syntax.
    """
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        code = response.text
        
        # Extract only the code inside ```python ... ```
        if "```python" in code:
            code = code.split("```python")[-1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[-1].split("```")[0].strip()
        
        # If the LLM completely ignored markdown block rules, aggressively extract from the last import
        if "from prefab_ui" in code and not code.startswith("from prefab_ui"):
            code = "from prefab_ui" + code.rsplit("from prefab_ui", 1)[-1]
        
        app_path = os.path.join(BASE_DIR, "generated_app.py")
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Kill any existing Prefab server
        os.system("pkill -f 'prefab serve'")
        
        # Launch the new app in the background using the official prefab CLI
        subprocess.Popen(["prefab", "serve", "generated_app.py", "--port", "5175"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        logger.info(f"[STEP 2: RENDER] Status: Success - App generated and running on port 5175")
        
        # Return a simple JSON response telling the Next.js frontend to refresh its iframe
        return json.dumps({"status": "success", "action": "refresh_iframe", "url": "http://127.0.0.1:5175"})
    except Exception as e:
        logger.error(f"[STEP 2: RENDER] Status: Failed - {e}")
        return json.dumps({"error": f"Failed to generate app: {e}"})

# --- Tool Execution Bridge ---
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run-tool":
        try:
            tool_name, args_json = sys.argv[2], sys.argv[3]
            args_dict = json.loads(args_json)
            if tool_name == "smart_query":
                print(smart_query(args_dict.get("user_input", "")))
            elif tool_name == "render_ui":
                d_str = args_dict.get("data_str") or args_json
                print(agentic_render(d_str))
            elif tool_name == "save_history_entry":
                d_str = args_dict.get("data_str") or args_json
                print(save_history_entry(d_str))
        except Exception as e:
            sys.stderr.write(f"CRASH: {e}\n")
        sys.exit(0)
