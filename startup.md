# Lucenta Startup & Configuration

## Configuring Models

Lucenta uses a tiered intelligence system to balance performance and power.

### 1. Default Model (Local)
The `DEFAULT_MODEL` handles intent classification (via NPU emulation), trivial tasks, and standard conversational turns.
- Edit `.env`:
  ```env
  LOCAL_PROVIDER=ollama
  DEFAULT_MODEL_NAME=llama3.1:latest
  DEFAULT_MODEL_BASE_URL=http://localhost:11434
  ```

### 2. Step-Up Model (Powerful)
High-complexity tasks (like Deep Research planning and reflection) trigger the 'Step-Up' logic. If configured, Lucenta will use a more capable model (e.g., GPT-4o or Claude 3.5).
- Edit `.env`:
  ```env
  STEP_UP_PROVIDER=openai
  STEP_UP_MODEL_NAME=gpt-4o
  STEP_UP_API_KEY=your-actual-api-key
  ```
- **Fallback**: If the `STEP_UP_MODEL` is not configured or fails, Lucenta silently falls back to the `DEFAULT_MODEL`.

## Running Deep Research

To trigger the Plan -> Reflect -> Act loop:
```bash
python -m lucenta.research.deep_research "Your complex research goal here"
```

## Docling Integration

Lucenta uses **Docling** for native structured Markdown parsing.
- All PDF, Docx, and Web scraping tasks use Docling to ensure the LLM receives structured data, not raw text.
- Ensure dependencies are installed: `pip install -r requirements.txt`
