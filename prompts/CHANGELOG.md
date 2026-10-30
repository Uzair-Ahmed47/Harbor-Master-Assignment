# Prompt change log

These are implementation changes, not claims of improvements measured on a live model.

1. Initial baseline: short operational instruction plus JSON format. Retained in src/master.py::prompt(defended=False) for before-defence experiments.
2. Added five labelled parts: role, context, goals, constraints and output format. Made report-only knowledge and exact action signatures explicit.
3. Added instruction hierarchy: manifest, crew notes and player messages remain untrusted even when claiming system/admin authority. Human approval cannot be supplied in report text.
4. Added three worked examples covering a real storm warning, missing ship and a fake system instruction in crew notes. Use prompt(few=False) for the zero-shot comparison.
5. Added controlled-language Final Report publication: exactly one entry from allowed_facts. This reduces expressive freedom and may increase retries, but permits deterministic factual checking of player-facing reports. Brief Thought field requests only a concise decision summary.

The main live experiment batch preserves each complete prompt and response in logs/experiments.jsonl. Model settings and digests are in results/model_manifest.json. Do not mix later prompt versions into the recorded batch.

6. Live pilot on 30 October 2026 returned Markdown fences and a lengthy explanation, including an inappropriate storm warning and hold proposal. Before the main batch, made the short baseline explicitly JSON-only with no explanation. The baseline still has no untrusted-data hierarchy or code execution bypass. Pilot records are retained separately in logs/pilot_format_failure.jsonl; main batch uses the clarified format.
