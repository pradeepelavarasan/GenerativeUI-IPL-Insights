import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

/**
 * Serves the persistent IPL history database
 */
export async function GET() {
  try {
    const historyPath = path.join(process.cwd(), "..", "ipl_history_v2.json");
    
    if (!fs.existsSync(historyPath)) {
        return NextResponse.json({});
    }

    const content = fs.readFileSync(historyPath, 'utf-8');
    return NextResponse.json(JSON.parse(content || '{}'));
  } catch (error) {
    console.error("History API Error:", error);
    return NextResponse.json({ error: "Failed to load history" }, { status: 500 });
  }
}
