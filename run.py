import argparse,json,os
from src.simulation import Harbour
from src.master import Master

def main():
    p=argparse.ArgumentParser();p.add_argument('--agent',required=True,choices=['baseline','reflex','model','utility','llm']);p.add_argument('--seed',type=int,required=True);p.add_argument('--id-digit',type=int,default=1);p.add_argument('--replay');p.add_argument('--interactive-approval',action='store_true');p.add_argument('--stabilize',action='store_true');a=p.parse_args()
    if a.agent=='llm' and not a.replay and not os.environ.get('LLM_MODEL'):p.error('Set LLM_MODEL and LLM_BASE_URL before a live LLM run, or supply --replay.')
    c=Master(a.seed,a.id_digit,a.replay,a.interactive_approval) if a.agent=='llm' else None
    print(json.dumps(Harbour(a.seed,a.id_digit,a.agent,a.stabilize,c).run(),sort_keys=True))
if __name__=='__main__':main()
