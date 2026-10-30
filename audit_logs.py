"""Create a reviewable statement audit from actual model logs, never synthetic claims."""
import json,csv,re
from pathlib import Path
P=Path(__file__).resolve().parent
rows=[]
for name in ['llm_log.jsonl','experiments.jsonl']:
    path=P/'logs'/name
    if not path.exists():continue
    for ln,line in enumerate(path.read_text().splitlines(),1):
        r=json.loads(line)
        if not r.get('response'):continue
        try:o=json.loads(r['response'])
        except ValueError:continue
        report=r['messages'][1]['content']
        for field in ['Thought','Final Report']:
            for statement in re.split(r'(?<=[.!?])\s+',o.get(field,'')):
                if statement.strip():rows.append(dict(log=name,line=ln,tick=r['tick'],field=field,statement=statement,report=report,supported='',reason=''))
with (P/'results/hallucination_audit.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['log','line','tick','field','statement','report','supported','reason']);w.writeheader();w.writerows(rows[:30])
judged=[r for r in rows if r['supported'] in ('yes','no')]
print(f'Prepared {min(len(rows),30)} statements. Review at least 10, mark supported yes/no, explain decisions. No support rate is inferred from string matching.')
