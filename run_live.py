"""Run the five live comparison seeds without repeating the rule experiments."""
import json, os
from pathlib import Path
import pandas as pd
from src.master import Master
from src.simulation import Harbour

ROOT = Path(__file__).resolve().parent

def main():
    if not os.environ.get('LLM_MODEL'):
        raise SystemExit('Set LLM_MODEL and LLM_BASE_URL first.')
    rules = pd.read_csv(ROOT/'results/evaluation_30_seeds.csv')
    eligible = rules.groupby('agent').agg(cargo=('cargo_delivered','mean'),ko=('storm_knockouts','sum'),crowd=('crowding_violations','sum')).drop('baseline')
    safe = eligible[(eligible.ko==0)&(eligible.crowd==0)]
    best = (safe if len(safe) else eligible).cargo.idxmax()
    rows = []
    for seed in range(11,16):
        controller = Master(seed,1)
        harbour = Harbour(seed,1,'llm',controller=controller)
        row = dict(agent='llm',seed=seed,digit=1,**harbour.run())
        rows.extend([row,rules[(rules.agent==best)&(rules.seed==seed)].iloc[0].to_dict()])
        pd.DataFrame(rows).to_csv(ROOT/'results/llm_comparison.csv',index=False)
        print(json.dumps(row),flush=True)

if __name__=='__main__': main()
