import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';
import { promisify } from 'util';
import fs from 'fs';

const execPromise = promisify(exec);

function logToSession(sessionId: string, message: string) {
  const logPath = path.join(process.cwd(), "..", "logs", `${sessionId}.log`);
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 23);
  const entry = `${timestamp} - INFO - [BRIDGE] ${message}\n`;
  try {
    fs.appendFileSync(logPath, entry);
  } catch (e) {}
  console.log(`[${sessionId}] ${message}`);
}

export async function POST(req: NextRequest) {
  // 1. Generate the Master Session ID in IST (Asia/Kolkata)
  const now = new Date();
  const istDate = now.toLocaleDateString('en-GB', { timeZone: 'Asia/Kolkata' }).split('/').reverse().join('-');
  const istTime = now.toLocaleTimeString('en-US', { timeZone: 'Asia/Kolkata', hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(/:/g, '-').replace(/ /g, '_');
  const sessionId = `session_${istDate}_${istTime}`;
  
  try {
    const { query } = await req.json();
    logToSession(sessionId, `--- 🆕 NEW REQUEST: ${query} ---`);

    const pythonPath = path.join(process.cwd(), "..", "venv", "bin", "python3");
    const orchestratorPath = path.join(process.cwd(), "..", "orchestrator.py");

    // 2. Pass the Master Session ID to Python
    const command = `"${pythonPath}" "${orchestratorPath}" "${query.replace(/"/g, '\\"')}"`;
    
    const { stdout, stderr } = await execPromise(command, {
      env: { ...process.env, SESSION_ID: sessionId },
      cwd: path.join(process.cwd(), "..")
    });

    if (stderr && !stdout) {
      logToSession(sessionId, `❌ Orchestrator Error: ${stderr}`);
      throw new Error(stderr);
    }

    logToSession(sessionId, `✅ Orchestrator Task Complete.`);
    const rawOutput = stdout.trim();
    logToSession(sessionId, `📦 Raw Orchestrator Output Snippet: ${rawOutput.substring(0, 500)}`);
    
    // Extract JSON between markers
    const startMarker = "===RESULT_START===";
    const endMarker = "===RESULT_END===";
    const startIndex = rawOutput.indexOf(startMarker);
    const endIndex = rawOutput.indexOf(endMarker);

    if (startIndex !== -1 && endIndex !== -1) {
      const jsonStr = rawOutput.substring(startIndex + startMarker.length, endIndex).trim();
      const result = JSON.parse(jsonStr);
      return NextResponse.json(result);
    } else {
      // Fallback for direct JSON output
      try {
        const result = JSON.parse(rawOutput);
        return NextResponse.json(result);
      } catch (e) {
        logToSession(sessionId, `❌ JSON Parse Error. Markers not found and raw parse failed.`);
        throw new Error("Invalid orchestrator response format");
      }
    }

  } catch (error: any) {
    logToSession(sessionId, `❌ Final Bridge Error: ${error.message}`);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
