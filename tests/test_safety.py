import unittest,json,tempfile
from contextlib import contextmanager
from uuid import uuid4
import shutil

@contextmanager
def test_directory():
    root=(Path(__file__).resolve().parents[1]/"test_scratch").resolve()
    root.mkdir(exist_ok=True)
    target=root/uuid4().hex
    target.mkdir(mode=0o777)
    try: yield str(target)
    finally:
        assert target.resolve().parent==root
        shutil.rmtree(target)

from pathlib import Path
from src.simulation import Harbour,PARAMS
from src.master import parse,execute,validate,Master

class SafetyTests(unittest.TestCase):
    def harbour(self):
        h=Harbour(1,1);h.ships[1]={'id':1,'cargo':8,'arrival':0,'docked':0,'departed':None,'released':False};h.berths['B2']=1;return h
    def test_id_parameters(self):self.assertEqual(PARAMS[1],(12,5,9,4,8))
    def test_strict_parser(self):
        for raw in ['oops',json.dumps({'Thought':'x','Action':[{'name':'delete_all','args':{}}],'Final Report':'x'}),json.dumps({'Thought':'x','Action':[{'name':'assign_workers','args':{'berth':'B2','n':True}}],'Final Report':'x'})]:
            with self.assertRaises((ValueError,TypeError)):parse(raw)
    def test_approval_default_deny(self):
        h=self.harbour()
        self.assertIn('BLOCKED',execute({'name':'close_harbour','args':{}},h));self.assertFalse(h.closed)
        self.assertIn('BLOCKED',execute({'name':'release_cargo','args':{'ship_id':1}},h));self.assertEqual(h.ships[1]['cargo'],8)
    def test_explicit_approval(self):
        h=self.harbour();execute({'name':'release_cargo','args':{'ship_id':1}},h,lambda a:True)
        self.assertIsNone(h.berths['B2']);self.assertEqual(h.delivered,0)
    def test_grounding_gate(self):
        from src.master import validate_final
        h=self.harbour()
        validate_final({'Final Report':'Ship 1 at B2 has 8 cargo units.'},h.report())
        with self.assertRaises(ValueError):validate_final({'Final Report':'Ship 9 has gold.'},h.report())
    def test_missing_ship(self):
        with self.assertRaises(ValueError):execute({'name':'hold_ship','args':{'ship_id':999}},self.harbour())
    def test_storm_assignment_rejected(self):
        h=self.harbour();h.berths['B1']=1;h.tick=h.storms[0]-5
        with self.assertRaises(ValueError):execute({'name':'assign_workers','args':{'berth':'B1','n':2}},h)
    def test_determinism_and_shared_world(self):
        for policy in ['baseline','reflex','model','utility']:
            h=Harbour(3,1,policy);g=Harbour(3,1,policy)
            self.assertEqual(h.arrivals,g.arrivals);self.assertEqual(h.run(),g.run())
    def test_capacity_and_cargo(self):
        for policy in ['baseline','reflex','model','utility']:
            h=Harbour(2,1,policy);m=h.run();self.assertEqual(m['crowding_violations'],0)
            remaining=sum(s['cargo'] for s in h.ships.values())
            carried=sum(w.cargo for w in h.workers)
            self.assertLessEqual(remaining+carried+m['cargo_delivered'],len(h.ships)*8)
    def test_replay_matches_and_fails_closed(self):
        from src.master import prompt
        h=self.harbour();msgs=[{'role':'system','content':prompt()},{'role':'user','content':json.dumps(h.report(),sort_keys=True)}]
        record=dict(seed=1,digit=1,tick=0,messages=msgs,response=json.dumps({'Thought':'No action','Action':[],'Final Report':'Tick 0.'}),model='synthetic-test-only',seconds=0.1)
        with test_directory() as d:
            p=Path(d)/'replay.jsonl';p.write_text(json.dumps(record)+'\n');c=Master(1,1,str(p));c.turn(h);self.assertEqual(c.metrics['calls'],1)
            with self.assertRaises(ValueError):c.turn(h)
    def test_retry_limit_and_fallback(self):
        from unittest.mock import patch
        h=self.harbour();c=Master(1,1)
        # Patch log root to prevent synthetic fixtures entering genuine model logs.
        import src.master as mm
        with test_directory() as d,patch.object(mm,'ROOT',Path(d)),patch.object(mm,'prompt',return_value='test'),patch.object(mm,'call_model',return_value=('malformed','synthetic-test-only',{})):
            c.turn(h)
        self.assertEqual(c.metrics['calls'],3);self.assertEqual(c.metrics['retries'],2);self.assertEqual(c.metrics['fallbacks'],1)

if __name__=='__main__':unittest.main()
