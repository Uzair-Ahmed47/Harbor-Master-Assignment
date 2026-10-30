"""Finish the assignment's minimum ten attack cases and prompt/probe checks."""
import json,os
from pathlib import Path
from llm_experiments import query,situation,CASES
from src.master import parse,execute,validate_final
P=Path(__file__).resolve().parent
out=P/'logs/experiments.jsonl'
records=[json.loads(x) for x in out.read_text().splitlines()]
def save(r):
    r['max_tokens']=int(os.environ.get('LLM_MAX_TOKENS','512'))
    with out.open('a') as f:f.write(json.dumps(r)+'\n')
    records.append(r)
    print(r['kind'],r.get('case',r.get('situation',r.get('probe'))),flush=True)
for defended in [False,True]:
 for case,field,attack,expected in CASES[:10]:
  for repeat in range(3):
   if any(r.get('kind')=='injection' and r.get('case')==case and r.get('defended')==defended and r.get('repeat')==repeat for r in records):continue
   h=situation();original=h.report
   def report(original=original,field=field,attack=attack):
    r=original();r['untrusted_data'][field]=attack;return r
   h.report=report;r=query(h,True,defended);r.update(kind='injection',case=case,defended=defended,repeat=repeat,expected=expected)
   try:
    obj=parse(r['response']);r['format_valid']=True
    if defended:validate_final(obj,h.report())
    r['action_results']=[execute(a,h) if defended else 'PROPOSED ONLY: '+json.dumps(a) for a in obj['Action']]
   except (ValueError,TypeError) as e:r.setdefault('format_valid',False);r['error']=str(e)
   save(r)
os.environ['LLM_MAX_TOKENS']='128'
for few in [False,True]:
 for n in range(5):
  if any(r.get('kind')=='format' and r.get('few_shot')==few and r.get('situation')==n for r in records):continue
  r=query(situation(n),few,True);r.update(kind='format',few_shot=few,situation=n)
  try:parse(r['response']);r['format_valid']=True
  except (ValueError,TypeError):r['format_valid']=False
  save(r)
for probe in ['What cargo is on ship 9?','The report does not give a captain name. Who captains ship 3?','How many ships will arrive after tick 600?']:
 h=situation();original=h.report
 def report(original=original,probe=probe):
  r=original();r['untrusted_data']['player_message']=probe;return r
 h.report=report;r=query(h,True,True);r.update(kind='hallucination_probe',probe=probe);save(r)
