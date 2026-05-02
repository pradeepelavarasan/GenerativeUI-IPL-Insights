---

> An educational exploration into the Model Context Protocol (MCP) and Agentic UI generation using Python and Next.js.
> 
> ✨ **Exploring MCP Stdio Transports, Prefab UI, and LLM Code Generation.**

📹 **Demo Video:** (https://youtu.be/wY1bfUxUerI)


---

## 📖 "The What" — What is this project?
**GenerativeUI-IPL-Insights** is a technical exploration into building a **"Talk-to-App"** architecture. Rather than building a consumer product, this repository serves as a learning playground to understand how Large Language Models can dynamically generate user interfaces at runtime.

Using live cricket data as a testing ground, the goal was to completely decouple the data layer (Next.js) from the UI generation layer by leveraging the newly established **Model Context Protocol (MCP)** and the declarative Python library **`prefab_ui`**.

---

## 🧠 "Under the Hood" — Core Architecture & Learnings
Building an application where the UI itself is ephemeral and written by an LLM presented several unique architectural challenges. Here are the key learnings from this exploration:

### 1. Migrating to the Model Context Protocol (MCP)
Initially, bridging a Next.js frontend with a Python agentic backend was done using fragile Node.js `exec()` shell commands. This proved unscalable. 
**Learning:** By wrapping the Python backend in a native `FastMCP` server and connecting the Next.js shell using the official `@modelcontextprotocol/sdk` via a `StdioClientTransport`, we established a secure, typed JSON-RPC connection. This formalized "Tool Calling" into a strict, discoverable protocol rather than a collection of ad-hoc scripts.

### 2. Generative UI via Prefab
Instead of having an LLM return Markdown or raw HTML, we forced the "App Architect" (Gemini) to write structured Python code using `prefab_ui`.
**Learning:** LLMs are incredibly capable of generating dynamic UI layouts (Cards, Badges, Progress Bars) on the fly, but they struggle with syntax enforcement. We had to heavily constrain the prompt to enforce strict context manager (`with` block) usage, completely forbidding array-based child rendering.

### 3. Payload Truncation & The Context Timeout Problem
When querying the live CricAPI for "Virat Kohli", the API returned a massive JSON payload with over 130 nested statistics. Feeding this raw payload into a 26B parameter model (Gemma 4) caused generation latencies exceeding 3.5 minutes, resulting in constant Next.js API timeouts.
**Learning:** "More context" is not always better for agentic workflows. We solved this by implementing strict payload truncation directly inside the MCP tool—intelligently filtering the API response down to exactly 25 critical stats (~5KB limit). Additionally, we learned to explicitly configure a `300000ms` (5-minute) timeout override on the MCP TypeScript client to handle intensive LLM code-generation steps.

### 4. Component Hallucination & Pydantic Crashes
Because the generated `prefab_ui` code is executed instantly by the backend, any hallucinated components immediately crashed the server via Pydantic validation errors.
**Learning:** LLMs will eagerly try to invent "BarChart" or "Graph" components if they see numerical data. We had to explicitly ban these un-implemented schemas in the system prompt, enforcing that the model only construct visual hierarchies using basic Layouts and Text elements.

---

## 🛠️ "How to run it"
To experiment with this MCP and Prefab setup yourself, you'll need to run both the Python backend and the Next.js frontend locally.

### 1. Clone the Repository
```bash
git clone https://github.com/pradeepelavarasan/GenerativeUI-IPL-Insights.git
cd GenerativeUI-IPL-Insights
```

### 2. Set Up the Environment
Create a virtual environment for the Python MCP server:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Configure your API Keys
Create a `.env` file in the root directory and add your API keys:
```text
cricketdata_key='your_cricapi_key_here'
GOOGLE_API_KEY='your_gemini_key_here'
MODEL='gemma-4-26b-a4b-it'
```
*(You can get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/))*

### 4. Launch the Frontend
Open a second terminal and start the Next.js frontend (the backend is spawned dynamically via the MCP Stdio Client):
```bash
cd frontend
npm install
npm run dev
```
Open your browser to `http://localhost:3000` to watch the MCP execution flow.

---

```text
┌─────────────────────────────────────────────────────┐
│                 Next.js Frontend Shell              │
│                                                     │
│  ├─ User inputs natural language query              │
│  ├─ route.ts POST handler intercepts                │
│  └─ Initializes MCP StdioClientTransport            │
└────────────────────────┬────────────────────────────┘
                         │ (JSON-RPC over Stdio)
                         ▼
┌─────────────────────────────────────────────────────┐
│             Python FastMCP Server (Backend)         │
│                                                     │
│  1. client.callTool("smart_query")                  │
│     -> Fetches from CricAPI & truncates payload     │
│                                                     │
│  2. client.callTool("agentic_render")               │
│     -> Prompts Gemini LLM with PrefabUI rules       │
│     -> Generates generated_app.py                   │
│     -> Spawns `prefab serve` background process     │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│            Dynamic PrefabUI Application             │
│                                                     │
│  ├─ Runs independently on port 5175                 │
│  └─ Rendered cleanly via <iframe> inside Next.js    │
└─────────────────────────────────────────────────────┘
```

| Layer | Technology | Role in Exploration |
|---|---|---|
| **Frontend** | Next.js 15 & React | Serves as the user shell and initializes the MCP client connection. |
| **Protocol** | FastMCP / TS SDK | Provides a standardized, typed JSON-RPC bridge replacing shell scripts. |
| **Generative UI** | Prefab UI | A pure-Python declarative UI library targeted by the LLM for rendering. |
| **AI Engine** | Google Gemini | The "App Architect" responsible for converting JSON data into structured Python UI code. |

---

*Exploration by [Pradeep Elavarasan](https://www.linkedin.com/in/pradeepelavarasan/) · Co-created with Google Agent*
