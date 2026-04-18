# Karnataka UBID Intelligence Platform — Python Edition

A full Python conversion of the original TypeScript/React frontend application.

## Project Structure

```
.
├── main.py                          # CLI entry point (replaces App.tsx)
├── types.py                         # Data models (replaces src/types.ts)
├── mock_data.py                     # Seed data (replaces src/mockData.ts)
├── requirements.txt
└── services/
    ├── fuzzy_matching_service.py    # replaces src/services/fuzzyMatchingService.ts
    ├── ubid_service.py              # replaces src/services/ubidService.ts
    ├── status_inference_service.py  # replaces src/services/statusInferenceService.ts
    └── ai_service.py               # replaces src/services/geminiService.ts (uses Anthropic)
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python main.py
```

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Feature Parity

| TypeScript Feature | Python Equivalent |
|----|-----|
| UBID generation (KA-XXXXXXXX-C) | `services/ubid_service.py::generate_unified_business_identifier()` |
| Fuzzy matching (Levenshtein + Soundex) | `services/fuzzy_matching_service.py` |
| Status inference engine | `services/status_inference_service.py::infer_business_status()` |
| Orphan signal detection | `services/status_inference_service.py::find_orphan_events()` |
| Entity resolution (two-pass) | `services/ubid_service.py::resolve_ubids()` |
| AI chat (Gemini → Claude) | `services/ai_service.py::get_general_chat_response()` |
| AI deep analysis | `services/ai_service.py::get_high_thinking_analysis()` |
| Area intelligence reports | `services/ai_service.py::get_maps_grounding_info()` |
| Error healer AI | `services/ai_service.py::get_healer_patch()` |
| Schema evolution AI | `services/ai_service.py::analyze_data_anomaly()` |
| Dashboard, Registry, Reviewer Queue, Orphan Resolver, Audit Ledger | `main.py` interactive menu |

## Notes

- The Gemini SDK (`@google/genai`) has been replaced with the **Anthropic Python SDK**.  
  Model used: `claude-opus-4-5`.
- The React UI has been replaced with an **interactive CLI** that covers all
  the same views: Dashboard, UBID Explorer, Registry, Reviewer Queue,
  Orphan Signals, Audit Ledger, AI Chat, AI Deep Analysis, and Entity Resolution.
- All core algorithms (Levenshtein, Soundex, Mod-36 checksum, djb2 hash) are
  implemented in pure Python with no external dependencies.
