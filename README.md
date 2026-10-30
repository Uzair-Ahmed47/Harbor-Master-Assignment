# Harbor Master Assignment

Stormwatch Harbour for CGD-460 Assignment 2. **Uzair Ahmed — 231761**.

Student ID digit 1 selects 12 workers, arrivals every 5–9 ticks, four storms and eight cargo units per ship. Runs last 600 ticks on a 24×16 grid.

## Setup and run

Python 3.10 or newer:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py --agent utility --seed 11
```

Available policies are `baseline`, `reflex`, `model`, `utility` and `llm`. Each run prints JSON. Rule policies are deterministic for a given seed.

```powershell
python -m unittest discover -s tests -v
python evaluate.py
python reproduce.py --report-only
```

Evaluation reproduces the four policies on seeds 11–40, paired comparisons, figures, and the ten-seed switching-penalty experiment. `--no-plots` reproduces CSVs without regenerating figures. The last command rebuilds the report from existing measured results and recorded reviews.

## Model experiments

Recorded inference used Meta Llama 3.2 3B Instruct Q4_K_M with Ollama 0.40.13, temperature 0, and a 16384-token context. Exact digests are in `results/model_manifest.json`. Injection calls used a maximum of 512 output tokens; final format tests and probes used 128.

`logs/experiments.jsonl` contains 60 paired injection trials covering T1–T10, six extra before-only T11/T12 trials, ten zero-shot/few-shot format trials, and three factual probes. `logs/pilot_format_failure.jsonl` preserves the development failure; `logs/smoke.jsonl` preserves the warm-up call. Recorded reviews are in `results/injection_review.csv` and `results/statement_review.csv`.

The supplied PDF reports the measured evidence available at export. Full seeded model-versus-rule simulation results are not included in this dataset.

To run the model locally after installing Ollama and `llama3.2:3b`:

```powershell
ollama create stormwatch-llama3.2:3b -f Modelfile
$env:LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:LLM_MODEL = "stormwatch-llama3.2:3b"
$env:LLM_TEMPERATURE = "0"
python run.py --agent llm --seed 11
```

`run_live.py` runs the five-seed model comparison. `llm_experiments.py` runs the full twelve-case experiment plan. Archive existing logs before a fresh batch. The controller supports exact prompt-checked replay once simulation calls have been recorded. Model credentials are read only from environment variables.

## Safety and conventions

The model receives a text report only. Strict parsing, argument validation, factual publication checks, at most three actions, at most two retries and a utility fallback constrain execution. Closure and cargo release require explicit human approval and default to denial. Use `--interactive-approval` to approve individual critical actions. Untrusted report text cannot supply approval.

Coordinates are (column,row), origin top left. Berths are (3,0), (9,0), (15,0), (21,0); the warehouse is (0,15). A single seeded generator precomputes shared arrivals and storms. Occupancy is capped at three workers per cell. Cargo counts warehouse drops; administrative release never counts as delivery. Waiting time includes queued ships censored at tick 600.

Utility is `4C - 3D - 2Q - 8S`: normalized cargo, distance, targeting workers and remembered storm risk. Risk also has a hard exclusion gate. The emergence variant adds a 1.5 target-switch penalty.

## Project files

- `src/`, `run.py`: simulation and model controller.
- `tests/`: safety, deterministic simulation, approvals, fallback and replay tests.
- `results/`, `logs/`, `prompts/`: measured data, model evidence and prompt versions.
- `evaluate.py`, `run_live.py`, `llm_experiments.py`: experiment runners.
- `make_report.py`, `model_sections.py`, `summarize_live.py`, `reproduce.py`: report pipeline.
- `CGD460_A2_231761_Report.pdf`: nine-page report.
- `AI_Usage_Declaration.pdf`: one-page required declaration.
