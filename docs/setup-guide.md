# ⚙️ Setup & Verification Guide: FabGuard

This guide provides exact, step-by-step instructions for judges and engineers to clone, configure, run, and test **FabGuard** locally.

---

## 1. Prerequisites

- **Python**: Version **3.10** or **3.11** (tested on 3.11.5).
- **Git**: Installed and available in terminal.
- **Operating System**: Windows, macOS, or Linux.
- **API Key (At least one)**:
  - **IBM watsonx.ai**: `WATSONX_API_KEY` & `WATSONX_PROJECT_ID` (for IBM Granite 3.0)
  - **Google Gemini**: `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)
  - **Groq**: `GROQ_API_KEY`
  *(Note: The system includes a resilient deterministic fallback engine that runs even if external LLM APIs are offline).*

---

## 2. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp src/.env.example .env
   # or on Windows PowerShell:
   Copy-Item src\.env.example .env
   ```

2. Open `.env` and fill in your preferred provider credentials:
   ```ini
   # LLM Provider selection: watsonx | gemini | groq
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-2.5-flash
   LLM_TEMPERATURE=0.3
   LLM_MAX_TOKENS=512

   # Google Gemini Configuration
   GEMINI_API_KEY=your_gemini_api_key_here

   # Groq API Configuration (Fast Fallback)
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=qwen/qwen3.8-27b

   # IBM watsonx.ai Configuration
   WATSONX_API_KEY=your_ibm_cloud_api_key
   WATSONX_PROJECT_ID=your_watsonx_project_id
   WATSONX_URL=https://us-south.ml.cloud.ibm.com
   WATSONX_MODEL=ibm/granite-3-8b-instruct
   ```

---

## 3. Installation

Run from the root of the repository:

```bash
# Optional: Create and activate virtual environment
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r src/requirements.txt
```

---

## 4. How to Run the Project

### Option A: Running the MCP Server for IBM Bob
To start the Model Context Protocol (MCP) server listening over standard input/output (stdio) for IBM Bob or Claude Desktop:

```bash
python src/mcp_server.py
```

#### Configuring IBM Bob to Connect to FabGuard MCP
In your IBM Bob MCP configuration file (`mcp_config.json`):
```json
{
  "mcpServers": {
    "fabguard": {
      "command": "python",
      "args": ["src/mcp_server.py"],
      "env": {
        "LLM_PROVIDER": "watsonx",
        "WATSONX_API_KEY": "your_api_key",
        "WATSONX_PROJECT_ID": "your_project_id"
      }
    }
  }
}
```
*Once configured, open IBM Bob and type:*
`@bob analyze LOT-2231` or `@bob predict_batch_risk`

---

### Option B: Interactive CLI Demonstration
To test all 4 tools interactively from the command line:

```bash
# Test in-progress batch risk assessment
python -X utf8 -c "from src.mcp_server import predict_batch_risk; print(predict_batch_risk())"

# Test full lot diagnostics briefing
python -X utf8 -c "from src.mcp_server import analyze_lot; print(analyze_lot('LOT-2231'))"

# Test raw root-cause telemetry extraction
python -X utf8 -c "from src.mcp_server import get_root_cause_findings; print(get_root_cause_findings('LOT-2231'))"

# Test natural language chat with Ask Bob
python -X utf8 -c "from src.mcp_server import ask_fab_copilot; print(ask_fab_copilot('Why did lot LOT-2231 fail?', 'LOT-2231'))"
```

---

## 5. Verification & Automated Test Suite

To run all automated verification tests:

```bash
# Run complete test suite (Person B Analytics + Person C Copilot)
pytest

# Run Copilot live end-to-end scenarios specifically
pytest src/copilot/tests/test_live_scenarios.py -v
```

All 6 live scenarios will execute:
- ✅ Scenario 1: `LOT-2231` (Etch Chamber Pressure / Edge-Ring Signature)
- ✅ Scenario 2: `LOT-2232` (CMP Scratch Signature)
- ✅ Scenario 3: `LOT-2233` (CVD Center-Cluster Signature)
- ✅ Scenario 4: `LOT-2240` (Real SQLite database lot)
- ✅ Scenario 5: Multi-turn "Ask Bob" session with honesty & DOE caveat checks
- ✅ Scenario 6: Provider failover verification (Gemini & Groq)

---

## 6. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| `UnicodeEncodeError: 'charmap'` | Windows console default encoding (CP1252) cannot display emoji characters in terminal output. | Run python commands with `python -X utf8` or set `$env:PYTHONIOENCODING="utf-8"`. |
| `HTTP 429 Too Many Requests` | External LLM provider quota exhausted. | The system will automatically fall back to Groq or deterministic domain templates. Ensure `GROQ_API_KEY` is set in `.env`. |
| `ModuleNotFoundError: No module named 'src'` | Working directory is not the repo root. | Ensure you execute commands from the repository root, or install package in editable mode with `pip install -e .`. |
| `WATSONX_API_KEY not set` | Attempting to use `LLM_PROVIDER=watsonx` without credentials. | Set credentials in `.env`, or switch `LLM_PROVIDER=gemini` or `LLM_PROVIDER=groq`. |
