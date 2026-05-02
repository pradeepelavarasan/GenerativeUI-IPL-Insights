import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';
import fs from 'fs';

/**
 * Agent Bridge: Handles new queries (POST) and historical rendering (PATCH)
 */
export async function POST(req: Request) {
  try {
    const { query } = await req.json();
    const sessionId = new Date().toISOString().replace(/[:.]/g, '-');
    console.log(`[BRIDGE] Starting Session ${sessionId} for: ${query}`);

    // 1. API FETCH
    const rawData = await runTool("smart_query", { user_input: query }, sessionId);
    if (rawData.includes('"error":')) {
        return NextResponse.json({ error: JSON.parse(rawData).error });
    }

    // 2. RENDERING (VISUAL FIRST)
    const blueprintStr = await runTool("render_ui", { data_str: rawData }, sessionId);
    const blueprint = JSON.parse(blueprintStr);

    // 3. STORAGE (BACKGROUND)
    runTool("save_history_entry", { data_str: rawData }, sessionId).catch(e => console.error("History Save Failed", e));

    return NextResponse.json({ blueprint });
  } catch (error: any) {
    console.error('Bridge Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function PATCH(req: Request) {
    try {
        const { entryId } = await req.json();
        const sessionId = `history-${entryId.slice(0, 8)}`;
        console.log(`[BRIDGE] Rendering History Entry: ${entryId}`);

        // Load the data from the history file
        const historyPath = path.join(process.cwd(), "..", "ipl_history_v2.json");
        const history = JSON.parse(fs.readFileSync(historyPath, 'utf-8'));
        const entry = history[entryId];

        if (!entry) throw new Error("Entry not found");

        // Render the UI blueprint from the existing data
        const blueprintStr = await runTool("render_ui", { data_str: JSON.stringify(entry.data) }, sessionId);
        const blueprint = JSON.parse(blueprintStr);

        return NextResponse.json({ blueprint });
    } catch (error: any) {
        console.error('History Render Error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}

/**
 * Executes the Python CLI tool
 */
function runTool(name: string, args: any, sessionId: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const venvPath = "/Users/pradeep/Library/CloudStorage/OneDrive-Personal/ML/2026 ML Projects/IPL 2026 Insights v2/venv/bin/python";
    const scriptPath = path.join(process.cwd(), "..", "cricket_server.py");
    const cmd = `"${venvPath}" "${scriptPath}" run-tool "${name}" '${JSON.stringify(args).replace(/'/g, "'\\''")}' --session "${sessionId}"`;

    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        console.error(`Tool ${name} failed:`, stderr);
        return reject(new Error(stderr || error.message));
      }
      resolve(stdout.trim());
    });
  });
}
