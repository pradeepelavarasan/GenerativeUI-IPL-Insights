import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Master Session Logging (IST AM/PM Sync)
SESSION_ID = os.environ.get("SESSION_ID")
if not SESSION_ID:
    # Fallback for direct execution
    SESSION_ID = f"session_{datetime.now().strftime('%Y-%m-%d_%I-%M-%S_%p')}"

SESSION_LOG = os.path.join(os.getcwd(), "logs", f"{SESSION_ID}.log")

def log_to_session(message: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    entry = f"{timestamp} - INFO - [ORCHESTRATOR] {message}\n"
    try:
        with open(SESSION_LOG, "a") as f:
            f.write(entry)
    except:
        pass
    print(message, file=sys.stderr)

# Configuration
MODEL = os.getenv("MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
MAX_ITERATIONS = 5

client = genai.Client(api_key=GEMINI_API_KEY)

async def main():
    if len(sys.argv) < 2:
        log_to_session("❌ No query provided")
        return

    query = sys.argv[1]
    log_to_session(f"--- 🆕 STARTING LOOP: {query} ---")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(base_dir, "venv", "bin", "python3")
    server_script = os.path.join(base_dir, "cricket_server.py")
    
    server_params = StdioServerParameters(
        command=venv_python,
        args=[server_script],
        env={**os.environ, "SESSION_ID": SESSION_ID} # Pass master ID to server
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                tools = (await session.list_tools()).tools
                log_to_session(f"Connected to server. Loaded {len(tools)} tools.")
                
                system_prompt = f"""You are the Cricket Analytics Orchestrator. 
                Follow this 3-Step Plan to solve the task:
                1. DATA: Call get_points_table() or get_player_stats(player_name).
                2. RENDER: Call agentic_render() with NO arguments. 
                3. STORAGE: Call save_history_entry() with NO arguments.
                
                CRITICAL: The mission ends ONLY after you call save_history_entry(). 
                You MUST call save_history_entry() AFTER agentic_render() to ensure the generated code is archived.

                Format your response EXACTLY as:
                FUNCTION_CALL: tool_name|arg1|arg2...
                Or when finished:
                FINAL_ANSWER: <summary>
                """

                history = []
                final_result = None

                final_output = None
                for iteration in range(1, MAX_ITERATIONS + 1):
                    prompt = f"{system_prompt}\nTask: {query}\nHistory:\n" + "\n".join(history)
                    
                    response = client.models.generate_content(model=MODEL, contents=prompt)
                    raw_text = (response.text or "").strip()
                    if not raw_text:
                        log_to_session(f"Iteration {iteration} - ⚠️  Empty response from LLM. History: {len(history)} items.")
                        continue
                    
                    text = raw_text.splitlines()[0].strip()
                    log_to_session(f"Iteration {iteration} - LLM Thought: {text}")

                    if text.startswith("FINAL_ANSWER:"):
                        summary_text = text.split("FINAL_ANSWER:")[1].strip()
                        log_to_session(f"Iteration {iteration} - Finalizing Pipeline.")
                        
                        # Merge dashboard data and summary
                        if final_result and isinstance(final_result, dict):
                            final_output = {**final_result, "summary": summary_text}
                        else:
                            final_output = {"status": "success", "summary": summary_text, "dashboard": final_result}
                        break

                    if not text.startswith("FUNCTION_CALL:"):
                        continue

                    _, call = text.split(":", 1)
                    parts = [p.strip() for p in call.split("|")]
                    func_name, raw_args = parts[0], parts[1:]

                    log_to_session(f"Iteration {iteration} - 🛠️  Executing: {func_name}")
                    
                    try:
                        arguments = {}
                        if func_name == "get_player_stats" and raw_args:
                            arguments = {"player_name": raw_args[0]}
                        
                        result = await session.call_tool(func_name, arguments=arguments)
                        payload = result.content[0].text if result.content else str(result)
                        
                        log_to_session(f"Iteration {iteration} - ✅ {func_name} Success.")
                        history.append(f"Called {func_name} -> {payload}")
                        
                        if func_name == "agentic_render":
                            try:
                                final_output = json.loads(payload)
                                render_time = final_output.get("render_time", "Unknown")
                                log_to_session(f"Iteration {iteration} - ✅ {func_name} Success. Render Time: {render_time}")
                            except:
                                pass

                        if func_name == "save_history_entry":
                            log_to_session("✨ Dashboard archived. Mission complete.")
                            if final_output:
                                print(json.dumps(final_output))
                            else:
                                print(json.dumps({"status": "success", "message": "History saved"}))
                            return
                    except Exception as e:
                        log_to_session(f"Iteration {iteration} - ❌ Error in {func_name}: {str(e)}")
                        history.append(f"Error in {func_name}: {str(e)}")

                # Output final unified result as JSON with a clear marker for the JS bridge
                print("\n===RESULT_START===")
                if final_output:
                    print(json.dumps(final_output))
                else:
                    # Fallback if the loop ended without a FINAL_ANSWER
                    print(json.dumps(final_result or {"status": "error", "message": "Pipeline incomplete"}))
                print("===RESULT_END===")
                
                log_to_session("✨ Pipeline Complete.")

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        log_to_session(f"💥 CRITICAL ERROR:\n{error_msg}")
        print(json.dumps({"error": str(e), "details": error_msg}))

if __name__ == "__main__":
    # Ensure stdout is ONLY for our JSON result
    asyncio.run(main())
