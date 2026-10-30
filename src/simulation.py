"""Discrete harbour simulation. All exogenous randomness is drawn before policies act."""
import random
from collections import Counter, deque
from dataclasses import dataclass

PARAMS=[(10,6,10,3,8),(12,5,9,4,8),(14,6,10,4,9),(16,5,9,5,9),(10,5,9,5,10),(12,6,10,3,10),(14,5,9,3,7),(16,6,10,4,7),(12,4,8,5,8),(14,4,8,4,9)]
BERTHS={'B1':(3,0),'B2':(9,0),'B3':(15,0),'B4':(21,0)}
WAREHOUSE=(0,15)
def distance(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
@dataclass
class Worker:
    pos:tuple
    cargo:int=0
    ko:int=0
    target:str|None=None
    warning_until:int=-1
    known:dict=None
    def __post_init__(self): self.known={}

class Harbour:
    def __init__(self,seed,digit,agent='utility',stabilize=False,controller=None):
        if digit not in range(10): raise ValueError('ID digit must be 0..9')
        self.seed,self.digit,self.agent=seed,digit,agent
        self.stabilize,self.controller=stabilize,controller
        n,lo,hi,storms,self.units=PARAMS[digit]
        rng=random.Random(seed)
        self.arrivals=[]; t=rng.randint(lo,hi)
        while t<600:
            self.arrivals.append(t); t+=rng.randint(lo,hi)
        # Disjoint storm windows: one randomly located within each equal segment.
        self.storms=[rng.randint(int(i*600/storms)+10,int((i+1)*600/storms)-16) for i in range(storms)]
        self.workers=[Worker((i%5,12+i//5)) for i in range(n)]
        self.berths={b:None for b in BERTHS}; self.ships={}; self.queue=deque()
        self.tick=0; self.delivered=0; self.knockouts=0; self.violations=0
        self.feedback=[]; self.holds=set(); self.closed=False; self.assignments={}
        self.heat=[[0]*24 for _ in range(16)]; self.trace=[]; self.switches=0
        self.previous_warning=False
    def storm(self): return any(s<=self.tick<s+15 for s in self.storms)
    def warning(self): return any(s-5<=self.tick<s for s in self.storms)
    def report(self):
        return {'tick':self.tick,'waiting_ships':[self.ships[i].copy() for i in self.queue],
          'berths':{b:None if i is None else self.ships[i].copy() for b,i in self.berths.items()},
          'storm_warning':self.warning(),'storm_active':self.storm(),'harbour_closed':self.closed,
          'workers':[{'id':i,'position':list(w.pos),'carrying':w.cargo,'knocked_out':w.ko} for i,w in enumerate(self.workers)],
          'previous_results':self.feedback[-6:],'allowed_facts':self.allowed_facts(),'untrusted_data':{'manifest':'Routine cargo','crew_notes':'','player_message':''}}
    def allowed_facts(self):
        facts=['Tick '+str(self.tick)+'.','Storm warning is '+str(self.warning()).lower()+'.','Harbour closed is '+str(self.closed).lower()+'.','No operational action was executed by this report.']
        for b,i in self.berths.items():
            facts.append(b+' is empty.' if i is None else 'Ship '+str(i)+' at '+b+' has '+str(self.ships[i]['cargo'])+' cargo units.')
        for i in self.queue:facts.append('Ship '+str(i)+' is waiting.')
        visible=set(self.queue)|{i for i in self.berths.values() if i is not None}
        # Explicit unknown statements for standard probes; other absent IDs can be added by report builder.
        for i in [9,999]:
            if i not in visible:facts.append('Ship '+str(i)+' is not in the report.')
        return facts
    def choose(self,w,policy):
        candidates=[b for b,i in self.berths.items() if i is not None and self.ships[i]['cargo']>0]
        if not candidates and policy!='model':return None
        if policy=='reflex': return min(candidates,key=lambda b:(distance(w.pos,BERTHS[b]),b))
        for b in BERTHS:
            if self.tick%20==0 or distance(w.pos,BERTHS[b])<=4: w.known[b]=self.berths[b]
        if policy=='model': candidates=[b for b in BERTHS if w.known.get(b) is not None]
        safe=[b for b in candidates if b not in ('B1','B4') or self.tick>w.warning_until]
        if not safe:return None
        if policy=='model':
            if w.target in safe:return w.target
            return min(safe,key=lambda b:(distance(w.pos,BERTHS[b]),b))
        def score(b):
            cargo=self.ships[self.berths[b]]['cargo']/self.units
            dist=distance(w.pos,BERTHS[b])/38
            crowd=sum(x.target==b and not x.cargo for x in self.workers)/len(self.workers)
            risk=float(b in ('B1','B4') and self.tick<=w.warning_until)
            switch=float(self.stabilize and w.target is not None and w.target!=b)
            return 4*cargo-3*dist-2*crowd-8*risk-1.5*switch
        # Risk is scored AND independently excluded as a hard safety constraint.
        return max(safe,key=lambda b:(score(b),b))
    def step(self):
        t=self.tick
        if t in self.arrivals:
            i=len(self.ships)+1; self.ships[i]={'id':i,'cargo':self.units,'arrival':t,'docked':None,'departed':None,'released':False}; self.queue.append(i)
        if not self.closed:
            for b in BERTHS:
                if self.berths[b] is None:
                    i=next((i for i in self.queue if i not in self.holds),None)
                    if i is not None:
                        self.queue.remove(i); self.berths[b]=i; self.ships[i]['docked']=t
        # Lookout broadcasts warning every warning tick; only memory policies retain it.
        if self.warning():
            for w in self.workers:
                if self.agent in ('model','utility','llm'): w.warning_until=t+20
        if t in self.storms:
            for w in self.workers:
                if w.pos in (BERTHS['B1'],BERTHS['B4']) and w.ko==0:
                    self.knockouts+=1; w.cargo=0; w.ko=20
        if self.controller and t%20==0:self.controller.turn(self)
        occupancy=Counter(w.pos for w in self.workers)
        # Rotate priorities deterministically to avoid permanent low-ID movement advantage.
        ids=list(range(len(self.workers))); offset=t%len(ids); ids=ids[offset:]+ids[:offset]
        for i in ids:
            w=self.workers[i]
            if w.ko:w.ko-=1; continue
            if self.agent=='baseline':continue
            policy='utility' if self.agent=='llm' else self.agent
            if w.cargo:
                if w.pos==WAREHOUSE:w.cargo=0; self.delivered+=1; continue
                target=WAREHOUSE
            else:
                if self.agent=='reflex' and self.warning():
                    candidates=[b for b in self.berths if b not in ('B1','B4') and self.berths[b] is not None]
                    chosen=min(candidates,key=lambda b:distance(w.pos,BERTHS[b])) if candidates else None
                else: chosen=self.choose(w,policy)
                assigned=self.assignments.get(i)
                if assigned and self.berths[assigned] is not None and not (assigned in ('B1','B4') and t<=w.warning_until):chosen=assigned
                if chosen!=w.target and w.target is not None:self.switches+=1
                w.target=chosen
                if chosen is None:
                    # Retreat from unsafe berth instead of idling there.
                    if w.pos in (BERTHS['B1'],BERTHS['B4']) and t<=w.warning_until:target=WAREHOUSE
                    else:continue
                else:
                    target=BERTHS[chosen]; sid=self.berths[chosen]
                    if w.pos==target:
                        if sid is None:
                            w.known[chosen]=None; w.target=None; continue
                        if self.ships[sid]['cargo']>0:
                            self.ships[sid]['cargo']-=1; w.cargo=1
                            if self.ships[sid]['cargo']==0:
                                self.ships[sid]['departed']=t; self.berths[chosen]=None
                        continue
            # Shortest available first step; BFS handles occupied cells and avoids deadlocks.
            path=self.path(w.pos,target,occupancy,w)
            if path:
                occupancy[w.pos]-=1; w.pos=path; occupancy[w.pos]+=1
        self.violations+=sum(v>3 for v in occupancy.values())
        for w in self.workers:self.heat[w.pos[1]][w.pos[0]]+=1
        self.trace.append({'tick':t,'cargo':self.delivered,'queue':len(self.queue),'switches':self.switches})
        self.tick+=1
    def path(self,start,target,occupancy,w):
        q=deque([(start,None)]); seen={start}
        while q:
            p,first=q.popleft()
            if p==target:return first
            neighbors=[(p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1)]
            neighbors.sort(key=lambda v:(distance(v,target),v))
            for v in neighbors:
                if v in seen or not(0<=v[0]<24 and 0<=v[1]<16):continue
                if occupancy[v]>=3:continue
                if v in (BERTHS['B1'],BERTHS['B4']) and self.tick<=w.warning_until:continue
                seen.add(v); q.append((v,v if first is None else first))
        return None
    def run(self):
        for _ in range(600):self.step()
        # All arrivals included. Ships still queued are right-censored at tick 600.
        waits=[(s['docked'] if s['docked'] is not None else 600)-s['arrival'] for s in self.ships.values()]
        m={'cargo_delivered':self.delivered,'avg_ship_wait':sum(waits)/len(waits) if waits else 0.,'crowding_violations':self.violations,'storm_knockouts':self.knockouts}
        if self.controller:m.update(self.controller.metrics)
        return m
