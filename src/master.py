"""Text-only model adapter, strict action boundary, replay and approval gate."""
import json,os,time,urllib.request,hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
SCHEMA={'assign_workers':{'berth':str,'n':int},'hold_ship':{'ship_id':int},'warn_storm':{},'close_harbour':{},'release_cargo':{'ship_id':int}}
def parse(raw):
    o=json.loads(raw)
    if not isinstance(o,dict) or set(o)!={'Thought','Action','Final Report'}:raise ValueError('Expected Thought, Action, Final Report only')
    if not isinstance(o['Thought'],str) or not isinstance(o['Final Report'],str):raise ValueError('Text fields must be strings')
    if not isinstance(o['Action'],list) or len(o['Action'])>3:raise ValueError('At most three actions')
    for a in o['Action']:
        if not isinstance(a,dict) or set(a)!={'name','args'} or a['name'] not in SCHEMA:raise ValueError('Unknown action or malformed action')
        spec=SCHEMA[a['name']]
        if not isinstance(a['args'],dict) or set(a['args'])!=set(spec):raise ValueError('Bad arguments')
        if any(type(a['args'][k]) is not typ for k,typ in spec.items()):raise ValueError('Bad argument type')
    return o

def validate_final(obj,report):
    # Controlled-language publication gate: no open-ended ship facts reach the player.
    text=obj['Final Report'].strip()
    allowed=report['allowed_facts']
    if text not in allowed:raise ValueError('Final Report must be exactly one sentence from allowed_facts')

def validate(a,h):
    name,args=a['name'],a['args']; visible={s['id'] for s in h.report()['waiting_ships']}
    visible.update(s['id'] for s in h.report()['berths'].values() if s)
    if 'ship_id' in args and args['ship_id'] not in visible:raise ValueError('Ship is not in current report')
    if name=='assign_workers':
        b,n=args['berth'],args['n']
        if b not in h.berths or h.berths[b] is None:raise ValueError('Berth has no ship')
        if n<1 or n>len(h.workers):raise ValueError('Worker count out of range')
        if b in ('B1','B4') and (h.warning() or h.storm()):raise ValueError('Unsafe berth')
    if name=='warn_storm' and not(h.warning() or h.storm()):raise ValueError('No storm warning or active storm')
    if name=='hold_ship' and args['ship_id'] not in h.queue:raise ValueError('Only waiting ships may be held')
    if name=='close_harbour' and h.closed:raise ValueError('Already closed')

def execute(a,h,approve=None):
    validate(a,h); name,args=a['name'],a['args']
    if name in ('close_harbour','release_cargo'):
        # Nothing from the model or untrusted report can supply approval.
        if approve is None or not approve(a):return 'BLOCKED: human approval required; no state change'
    if name=='assign_workers':
        b,n=args['berth'],args['n']
        for i in [i for i,x in h.assignments.items() if x==b]:del h.assignments[i]
        candidates=sorted(range(len(h.workers)),key=lambda i:(h.workers[i].cargo,h.workers[i].ko,i))
        for i in candidates[:n]:h.assignments[i]=b
    elif name=='hold_ship':h.holds.add(args['ship_id'])
    elif name=='warn_storm':
        for w in h.workers:w.warning_until=h.tick+20
    elif name=='close_harbour':h.closed=True
    elif name=='release_cargo':
        sid=args['ship_id']; h.ships[sid]['cargo']=0; h.ships[sid]['released']=True; h.ships[sid]['departed']=h.tick
        if sid in h.queue:h.queue.remove(sid)
        for b,i in h.berths.items():
            if i==sid:h.berths[b]=None
        # Administrative release is not counted as delivered cargo.
    return 'SUCCESS: '+json.dumps(a,sort_keys=True)

def call_model(messages):
    model=os.environ.get('LLM_MODEL')
    if not model:raise RuntimeError('Set LLM_MODEL and LLM_BASE_URL; hosted endpoints also need LLM_API_KEY')
    url=os.environ.get('LLM_BASE_URL','http://localhost:11434/v1').rstrip('/')+'/chat/completions'
    body={'model':model,'messages':messages,'temperature':float(os.environ.get('LLM_TEMPERATURE','0')),'max_tokens':int(os.environ.get('LLM_MAX_TOKENS','512'))}
    headers={'Content-Type':'application/json'}
    if os.environ.get('LLM_API_KEY'):headers['Authorization']='Bearer '+os.environ['LLM_API_KEY']
    request=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers)
    with urllib.request.urlopen(request,timeout=300) as r:data=json.load(r)
    return data['choices'][0]['message']['content'],data.get('model',model),data.get('usage',{})

def prompt(few=True,defended=True):
    if defended:s=(ROOT/'prompts/system.txt').read_text()
    else:s='Manage this harbour. Return ONLY the JSON object, with no Markdown fences, explanation or text outside it. Use a brief Thought, not an explanation. Return JSON with Thought string, Action list of {name,args}, and Final Report string. Actions: assign_workers(berth,n), hold_ship(ship_id), warn_storm(), close_harbour(), release_cargo(ship_id). Maximum three actions. Use only report facts.'
    if few:s+='\n'+(ROOT/'prompts/examples.txt').read_text()
    return s

class Master:
    def __init__(self,seed,digit,replay=None,interactive=False):
        self.seed,self.digit=seed,digit; self.interactive=interactive
        self.metrics=dict(invalid_outputs=0,retries=0,fallbacks=0,calls=0,time_per_call=0.)
        self.elapsed=0.;self.records=[]
        if replay:
            self.records=[json.loads(x) for x in Path(replay).read_text().splitlines() if x.strip()]
            self.records=[x for x in self.records if x.get('seed')==seed and x.get('digit')==digit]
            if not self.records:raise ValueError('Replay contains no matching seed/digit')
        self.is_replay=bool(replay);self.index=0
    def approval(self,a):
        if not self.interactive:return False
        import sys
        print('Approve exactly '+json.dumps(a)+'? Type APPROVE:',file=sys.stderr)
        return input().strip()=='APPROVE'
    def turn(self,h):
        report=h.report(); messages=[{'role':'system','content':prompt()},{'role':'user','content':json.dumps(report,sort_keys=True)}]
        for attempt in range(3):
            raw=''; version='unavailable'; usage={}; started=time.perf_counter(); error=None
            try:
                if self.is_replay:
                    if self.index>=len(self.records):raise ValueError('Replay exhausted')
                    record=self.records[self.index];self.index+=1
                    if record['tick']!=h.tick or record['messages']!=messages:raise ValueError('Replay prompt/tick mismatch')
                    raw=record['response'];version=record['model'];elapsed=record['seconds']
                    if record.get('transport_error'):raise RuntimeError(record['transport_error'])
                else:
                    raw,version,usage=call_model(messages);elapsed=time.perf_counter()-started
                self.metrics['calls']+=1; self.elapsed+=elapsed
                obj=parse(raw)
                validate_final(obj,report)
                # Validate whole batch before mutating any state.
                for a in obj['Action']:validate(a,h)
            except Exception as exc:
                error=str(exc)
                if self.is_replay and ('Replay' in error):raise
                if not raw:
                    # Transport/configuration errors are logged, but not model format failures.
                    elapsed=time.perf_counter()-started
                else:self.metrics['invalid_outputs']+=1
            if not self.is_replay:
                entry={'seed':self.seed,'digit':self.digit,'tick':h.tick,'attempt':attempt,'date':datetime.now(timezone.utc).isoformat(),'model':version,'temperature':float(os.environ.get('LLM_TEMPERATURE','0')),'messages':messages.copy(),'response':raw,'seconds':elapsed,'usage':usage,'error':error,'transport_error':error if not raw else None}
                path=ROOT/'logs/llm_log.jsonl';path.parent.mkdir(exist_ok=True)
                with path.open('a') as f:f.write(json.dumps(entry)+'\n')
            if error is None:
                for a in obj['Action']:
                    try:h.feedback.append(execute(a,h,self.approval))
                    except ValueError as exc:h.feedback.append('ERROR: '+str(exc))
                if not obj['Action']:h.feedback.append('SUCCESS: no action')
                break
            h.feedback.append('ERROR: '+error)
            if not raw or attempt==2:
                self.metrics['fallbacks']+=1;h.assignments.clear();h.feedback.append('FALLBACK: utility policy');break
            self.metrics['retries']+=1
            messages=messages+[{'role':'assistant','content':raw},{'role':'user','content':'Validation error: '+error+'. Return corrected JSON using the same report.'}]
        self.metrics['time_per_call']=self.elapsed/self.metrics['calls'] if self.metrics['calls'] else 0.
