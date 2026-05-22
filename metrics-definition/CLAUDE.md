# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project generates business-friendly metric definitions and formulas for the WestK measurement library. It processes an Excel file containing indicator metrics and user traits, enriching them with:
- **Formulas**: Technical calculation logic in English and Chinese
- **Business Logic**: Plain-language descriptions explaining why stakeholders care about each metric

The project uses DeepSeek API to generate these descriptions via LLM.

## Key Files

- **TP1_PoC Matrix and Traits Definition.xlsx** — Input file with indicator metrics and user traits
- **generate_formulas.py** — Generates formula descriptions (calculation logic)
- **generate_business_logic.py** — Generates business logic descriptions (plain language explanations)
- **formulas.json** — Cache of generated formulas (used to resume interrupted runs)
- **TP1_PoC Matrix and Traits Definition_with_formula.xlsx** — Output file with formulas added

## Architecture

### Data Flow

1. **Input**: Excel file with columns:
   - Scenario Category, Sub-category, Indicator Name (EN/CN), Definition (EN/CN)
   - User Traits sheet with similar structure

2. **Processing**:
   - Scripts read Excel rows and extract indicator metadata
   - Each indicator is sent to DeepSeek API with system prompt + context
   - API returns JSON with `en` and `cn` keys
   - Results are written back to Excel columns G-H (formulas) or Y-Z (business logic)

3. **Output**: Enriched Excel file with new columns populated

### Key Design Decisions

- **Caching via JSON**: `formulas.json` stores generated formulas to allow resuming interrupted runs without re-calling the API
- **Batch processing**: Scripts process all rows in one run, with 0.2-0.5s delays between API calls to avoid rate limiting
- **Error handling**: Failed rows are marked with "ERROR: {message}" in the output
- **Bilingual output**: All descriptions generated in both English and Chinese

## Common Commands

### Generate Formulas
```bash
python3 generate_formulas.py
```
Reads indicators from Excel, generates formula descriptions, saves to `TP1_PoC Matrix and Traits Definition_with_formula.xlsx`. Uses `formulas.json` cache to skip already-processed rows.

### Generate Business Logic
```bash
python3 generate_business_logic.py
```
Reads indicators from Excel, generates business logic descriptions, saves to `TP1_PoC Matrix and Traits Definition_with_logic.xlsx`.

### Resume Interrupted Runs
Both scripts check for existing output files and cached JSON before starting. To resume:
1. Ensure `formulas.json` exists (for formula generation)
2. Run the script again — it will skip cached rows and continue from where it left off

To force regeneration of all rows, delete `formulas.json` before running.

## Configuration

### Environment Variables
Create `.env.local` in the project root:
```
DEEPSEEK_API_KEY=sk_...
```

The scripts load this via `load_dotenv()`.

### API Settings
- **Base URL**: `https://api.deepseek.com`
- **Model**: `deepseek-chat` (standard model for cost-effective generation)
- **Max tokens**: 2000 per request
- **Rate limiting**: 0.2-0.5s delay between requests

## Troubleshooting

### API Errors
- **"Invalid model"**: Ensure `deepseek-chat` is the correct model name for your API key
- **"Timeout"**: DeepSeek API may be slow; increase delays in scripts if needed
- **"Invalid API key"**: Check `.env.local` has correct `DEEPSEEK_API_KEY`

### JSON Parsing Errors
If the API returns malformed JSON:
1. Check the raw response in console output (scripts print first 100 chars)
2. Verify the system prompt is clear about JSON format
3. Consider increasing `max_tokens` if responses are truncated

### Resuming After Errors
- Delete the problematic row from `formulas.json` to regenerate it
- Or delete the entire `formulas.json` to start fresh

## Testing

Run `test_deepseek.py` to verify API connectivity:
```bash
python3 test_deepseek.py
```

This tests basic API calls and parameter compatibility without processing the full Excel file.
