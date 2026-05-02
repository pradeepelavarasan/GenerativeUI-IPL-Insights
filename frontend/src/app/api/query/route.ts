import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

/**
 * Executes a tool via the MCP Stdio Client
 */
async function runMcpTool(name: string, args: any, sessionId: string): Promise<string> {
    const venvPath = "/Users/pradeep/Library/CloudStorage/OneDrive-Personal/ML/2026 ML Projects/IPL 2026 Insights v2/venv/bin/python";
    const scriptPath = path.join(process.cwd(), "..", "cricket_server.py");

    // The Python server might fail to parse --session if FastMCP doesn't allow custom args.
    // Instead, we will pass it as an environment variable or simply just not pass it since FastMCP handles it.
    // Actually, our updated cricket_server.py parses sys.argv manually before FastMCP runs, so it's safe.
    const transport = new StdioClientTransport({
        command: venvPath,
        args: [scriptPath, "--session", sessionId],
        stderr: "pipe"
    });

    const client = new Client({
        name: "Nextjs-Cricket-Client",
        version: "1.0.0"
    }, { capabilities: {} });

    try {
        await client.connect(transport);
        
        // Call tool
        const result = await client.callTool({
            name,
            arguments: args
        }, undefined, { timeout: 300000 });

        // FastMCP tools return strings via the content block
        if (result.content && result.content.length > 0) {
            const textContent = result.content.find(c => c.type === 'text');
            if (textContent && textContent.text) {
                 return textContent.text;
            }
        }
        throw new Error("No text content returned from tool");
    } finally {
        try {
            await client.close();
        } catch (e) {
            console.error("Error closing MCP client", e);
        }
    }
}

/**
 * Agent Bridge: Handles new queries (POST) and historical rendering (PATCH)
 */
export async function POST(req: Request) {
  try {
    const { query } = await req.json();
    const sessionId = new Date().toISOString().replace(/[:.]/g, '-');
    console.log(`[BRIDGE] Starting Session ${sessionId} for: ${query}`);

    // 1. API FETCH
    const rawData = await runMcpTool("smart_query", { user_input: query }, sessionId);
    if (rawData.includes('"error":')) {
        return NextResponse.json({ error: JSON.parse(rawData).error });
    }

    // 2. RENDERING (VISUAL FIRST)
    const blueprintStr = await runMcpTool("agentic_render", { data_str: rawData }, sessionId);
    const blueprint = JSON.parse(blueprintStr);

    // 3. STORAGE (BACKGROUND)
    runMcpTool("save_history_entry", { data_str: rawData }, sessionId).catch(e => console.error("History Save Failed", e));

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
        const blueprintStr = await runMcpTool("agentic_render", { data_str: JSON.stringify(entry.data) }, sessionId);
        const blueprint = JSON.parse(blueprintStr);

        return NextResponse.json({ blueprint });
    } catch (error: any) {
        console.error('History Render Error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
