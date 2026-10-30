"""One command reproduces rule-policy CSVs, paired comparisons and figures."""
import argparse,json,os
from pathlib import Path
import pandas as pd
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt=None
from src.simulation import Harbour
from src.master import Master
P=Path(__file__).resolve().parent/'results';P.mkdir(exist_ok=True)
METRICS=['cargo_delivered','avg_ship_wait','crowding_violations','storm_knockouts']
def emergence_figure(samples):
    fig,axs=plt.subplots(1,3,figsize=(12,3.5))
    for ax,stable in zip(axs[:2],[False,True]):
        ax.imshow(samples[stable].heat,origin='upper',cmap='magma',vmin=0,vmax=max(max(row) for h in samples.values() for row in h.heat))
        ax.set_title('With switch penalty' if stable else 'Original utility')
    for stable in [False,True]:
        h=samples[stable];axs[2].plot([r['tick'] for r in h.trace],[r['switches'] for r in h.trace],label='Penalty' if stable else 'Original')
    axs[2].legend();axs[2].set_title('Cumulative target switches');axs[2].set_xlabel('Tick')
    fig.suptitle('Figure 2. Seed 11 occupancy and local-rule change');fig.tight_layout();fig.savefig(P/'emergence_comparison.png',dpi=180);plt.close(fig)
def main():
    p=argparse.ArgumentParser();p.add_argument('--id-digit',type=int,default=1);p.add_argument('--llm',action='store_true');p.add_argument('--replay');p.add_argument('--no-plots',action='store_true');a=p.parse_args()
    if a.llm and not a.replay and not os.environ.get('LLM_MODEL'):p.error('Configure LLM_MODEL and LLM_BASE_URL first.')
    rows=[]
    for agent in ['baseline','reflex','model','utility']:
        for seed in range(11,41):
            h=Harbour(seed,a.id_digit,agent);m=h.run();rows.append(dict(agent=agent,seed=seed,digit=a.id_digit,**m))
        print('Completed '+agent,flush=True)
    d=pd.DataFrame(rows);d.to_csv(P/'evaluation_30_seeds.csv',index=False)
    summary=d.groupby('agent')[METRICS].agg(['mean','std']);summary.columns=['_'.join(c) for c in summary.columns];summary.to_csv(P/'summary.csv')
    pairs=[]
    for i,left in enumerate(['baseline','reflex','model','utility']):
        for right in ['baseline','reflex','model','utility'][i+1:]:
            for metric in METRICS:
                x=d[d.agent==right].set_index('seed')[metric]-d[d.agent==left].set_index('seed')[metric]
                se=x.std()/len(x)**.5
                pairs.append(dict(left=left,right=right,metric=metric,mean_difference=x.mean(),sd_difference=x.std(),ci95_low=x.mean()-2.045*se,ci95_high=x.mean()+2.045*se,larger_than_paired_sd=abs(x.mean())>x.std()))
    pd.DataFrame(pairs).to_csv(P/'paired_comparisons.csv',index=False)
    if not a.no_plots and plt is None:raise RuntimeError('Install matplotlib or use --no-plots for CSV-only reproduction.')
    if not a.no_plots:
        fig,axs=plt.subplots(2,2,figsize=(10,7))
        for ax,metric in zip(axs.flat,METRICS):
            s=d.groupby('agent')[metric].agg(['mean','std']).reindex(['baseline','reflex','model','utility'])
            ax.bar(s.index,s['mean'],yerr=s['std'],capsize=4,color=['#9ca3af','#60a5fa','#2563eb','#163d66']);ax.set_title(metric.replace('_',' '));ax.set_ylabel('Ticks' if metric=='avg_ship_wait' else 'Count')
        fig.suptitle('Figure 1. Thirty paired seeds; error bars show sample SD');fig.tight_layout();fig.savefig(P/'policy_metrics.png',dpi=170);plt.close(fig)
    emergent=[];samples={}
    for stable in [False,True]:
        for seed in range(11,21):
            h=Harbour(seed,a.id_digit,'utility',stable);m=h.run();emergent.append(dict(seed=seed,stabilize=stable,switches=h.switches,**m))
            if seed==11:
                samples[stable]=h
                if not a.no_plots:
                    fig,axs=plt.subplots(1,2,figsize=(10,3.5));im=axs[0].imshow(h.heat,origin='upper',cmap='magma');axs[0].set_title('Worker occupancy (all ticks)');fig.colorbar(im,ax=axs[0]);axs[1].plot([r['tick'] for r in h.trace],[r['switches'] for r in h.trace]);axs[1].set_title('Cumulative target switches');axs[1].set_xlabel('Tick');fig.suptitle('Figure 2. Utility '+('with' if stable else 'without')+' switch penalty');fig.tight_layout();fig.savefig(P/('emergence_stable.png' if stable else 'emergence_original.png'),dpi=170);plt.close(fig)
    pd.DataFrame(emergent).to_csv(P/'emergence_10_seeds.csv',index=False)
    if not a.no_plots:emergence_figure(samples)
    if a.llm:
        eligible=d.groupby('agent').agg(cargo=('cargo_delivered','mean'),ko=('storm_knockouts','sum'),crowd=('crowding_violations','sum'));eligible=eligible.drop('baseline');safe=eligible[(eligible.ko==0)&(eligible.crowd==0)];best=(safe if len(safe) else eligible).cargo.idxmax();r=[]
        for seed in range(11,16):
            c=Master(seed,a.id_digit,a.replay);h=Harbour(seed,a.id_digit,'llm',controller=c);r.append(dict(agent='llm',seed=seed,**h.run()))
            x=d[(d.agent==best)&(d.seed==seed)].iloc[0].to_dict();r.append(x)
        pd.DataFrame(r).to_csv(P/'llm_comparison.csv',index=False)
    (P/'metadata.json').write_text(json.dumps({'student_id':'231761','digit':a.id_digit,'evaluation_seeds':[11,40],'emergence_seeds':[11,20],'llm_executed':a.llm},indent=2))
if __name__=='__main__':main()
