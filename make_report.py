"""Regenerate the report from measured rule experiments. Pending LLM evidence stays explicit."""
from pathlib import Path
import pandas as pd
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from xml.sax.saxutils import escape
P=Path(__file__).resolve().parent;R=P/'results'
styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=9.5,leading=12.5,spaceAfter=6))
styles.add(ParagraphStyle(name='SmallCustom',fontName='Helvetica',fontSize=8,leading=10,spaceAfter=5))
styles['Title'].textColor=colors.black;styles['Heading1'].textColor=colors.black;styles['Heading2'].textColor=colors.black
story=[]
def para(s,small=False):return Paragraph(s,styles['SmallCustom' if small else 'BodyCustom'])
def text(s):story.append(para(s))
def title(s):story.append(Paragraph(s,styles['Heading1']))
def sub(s):story.append(Paragraph(s,styles['Heading2']))
def table(rows,widths=None):
    cells=[[para(escape(str(x)),True) for x in row] for row in rows]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8f2')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#cccccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(t);story.append(Spacer(1,9))
def page():story.append(PageBreak())
def foot(c,d):
    c.setFont('Helvetica',8);c.drawString(42,26,'Stormwatch Harbour | Uzair Ahmed | 231761');c.drawRightString(570,26,str(d.page))

def build():
    d=pd.read_csv(R/'evaluation_30_seeds.csv');em=pd.read_csv(R/'emergence_10_seeds.csv');paired=pd.read_csv(R/'paired_comparisons.csv')
    story.append(Paragraph('Stormwatch Harbour Assignment Report',styles['Title']))
    text('<b>Student ID 231761 | Name: Uzair Ahmed | CGD 460</b>')
    text('This project implements a seeded Python harbour simulation, compares four worker policies, and supplies an LLM supervisor with validation, human approval and replay. The evaluation uses matched seeds to separate policy effects from random arrivals and storms. The recommended deployment retains code-enforced safety and human approval for critical actions. Model results, raw response audits and attack trials are reported separately from deterministic execution safeguards.')
    text('Repository <link href="https://github.com/Uzair-Ahmed47/Harbor-Master-Assignment" color="#000080">https://github.com/Uzair-Ahmed47/Harbor-Master-Assignment</link>. ')
    title('Task A Specify the agents')
    text('<b>Table 1.</b> Role-specific PEAS descriptions. Performance is measured over the shared 600-tick horizon.')
    table([['Role','Performance','Environment','Actuators','Sensors'],['Dockworker','Delivered cargo; fewer knock-outs; legal occupancy','Grid, berths, warehouse, other workers, cargo','Move one cardinal cell; pick up; drop; wait','Own location/load; berth signal; nearby occupancy; current warning'],['Lookout','Warnings on time; no missed storm warnings','Sea and scheduled approaching storms','Broadcast warning five ticks before onset','Storm forecast unavailable to workers'],['Quartermaster','Cargo throughput; waiting time; worker allocation','Workers, berths, waiting ships, warning','Assign workers to berths; revise assignments','Berth/cargo status, assignments, lookout warning']],[65,103,115,104,141])
    sub('Environment classification')
    for label,reason in [('Partially observable','Workers do not directly observe future storms; the lookout receives advance information.'),('Stochastic','Arrival intervals and storm timings are randomly sampled, although a fixed seed makes a run repeatable.'),('Sequential','A route or assignment changes later cargo delivery and exposure to storms.'),('Dynamic','Ships and storms change while workers execute their tasks.'),('Discrete','Cells, ticks, units of cargo and action choices are discrete.'),('Multi-agent','Workers, lookout and quartermaster interact and share constrained cells.')]:text('<b>'+label+'.</b> '+reason)
    page();title('Task A Agent choices and autonomy')
    table([['Role','Choice and alternative','Trade-off'],['Dockworker','Model-based compared with simple reflex','Remembers warning and target/berth status. Extra state costs little memory and improves storm response; stale information can cause wasted travel. Reflex is cheaper and easier to inspect but forgets the warning.'],['Lookout','Simple reflex compared with model-based','Forecast signal directly triggers warning. Minimal computation and predictable timing; a memory agent could filter noisy readings, but simulated forecasts are exact and need no estimator.'],['Quartermaster','Utility-based compared with goal-based','Scores cargo, distance, crowding and risk. Linear scoring over four berths is inexpensive and balances competing outcomes; weights may cause unstable choices. A goal-only approach is easier to describe but does not rank trade-offs well.']],[77,164,287])
    text('<b>Table 2.</b> Choices concern the proposed role design; Task B separately implements the four required dockworker variants, so the selected model-based role is not presented as the measured best policy before evaluation.')
    table([['Role','May decide alone','Must not decide alone','Risk of more autonomy'],['Dockworker','Legal route, collection, delivery and retreat','Override capacity or critical approval','Unsafe shortcuts or worker congestion'],['Lookout','Broadcast authoritative forecast','Invent forecasts or close harbour','False alarms could unnecessarily stop work'],['Quartermaster','Routine allocations within legal constraints','Approve closure or release cargo','Over-concentrating workers or repeatedly changing targets']],[77,150,150,151])
    text('<b>Table 3.</b> Autonomy boundaries retain a hard execution layer. Increased intelligence does not grant additional permissions. Human approval is a separate trusted input, never an interpretation of text inside a manifest.')
    sub('Implementation assumptions')
    text('Coordinates start at the top left. Worker berth cells are B1=(3,0), B2=(9,0), B3=(15,0), B4=(21,0); ships lie immediately north at row -1. A worker at the berth is adjacent to its ship. Warehouse=(0,15). This interpretation makes exposure on an unsafe berth possible. Loading, unloading at the warehouse and movement each consume a tick.')
    text('Student ID digit 1 gives 12 workers, arrivals every 5-9 ticks, four storms and eight cargo units per ship. One random.Random(seed) precomputes arrivals and storms before any policy acts. Storms occupy separate 150-tick windows and last 15 ticks. This avoids policy-dependent random draws and overlapping storms.')
    page();title('Task B Simulation and policy comparison')
    text('The baseline idles. Reflex selects the nearest occupied berth and reacts only while a warning is being broadcast. Model-based workers retain a target and remembered warning/berth status, refreshed by periodic quartermaster reports and local sensing. Utility workers re-score berths. All use the same breadth-first routing, rotating movement priority and three-worker capacity reservation.')
    text('<b>Utility:</b> U(b)=4C-3D-2Q-8S, where C=cargo/8, D=Manhattan distance/38, Q=workers targeting berth/12 and S=remembered storm risk (0 or 1). These are transparent heuristic weights: cargo reward is balanced against travel and crowding; risk dominates. A hard unsafe-berth exclusion also applies, so the risk term is redundant when that gate activates. Weights were not optimized on evaluation seeds.')
    text('Cargo counts warehouse drops only. Waiting means arrival-to-docking; a still-queued ship is recorded at 600-arrival, a right-censored lower bound. Crowding counts violating cell-ticks after moves. A knock-out lasts 20 ticks and loses carried cargo. Holding affects queued ships; closure prevents docking, not ongoing delivery. Administrative release does not count as delivery.')
    rows=[['Policy','Cargo mean (SD)','Wait ticks mean (SD)','Crowding mean (SD)','KO mean (SD)']]
    for agent in ['baseline','reflex','model','utility']:
        x=d[d.agent==agent];rows.append([agent]+[f'{x[m].mean():.2f} ({x[m].std():.2f})' for m in ['cargo_delivered','avg_ship_wait','crowding_violations','storm_knockouts']])
    text('<b>Table 4.</b> Thirty matched seeds 11-40, sample SD in parentheses. Full runs are in results/evaluation_30_seeds.csv.')
    table(rows,[69,114,117,114,114]);story.append(Image(str(R/'policy_metrics.png'),width=428,height=300))
    page();title('Task B Variation and emergent behaviour')
    text('<b>Figure 1</b> on the preceding page shows policy means and run-to-run sample SD. Zero crowding is an enforced physical constraint, not evidence that a policy learned coordination. All active policies are compared with the do-nothing baseline on identical exogenous schedules.')
    text('Reflex achieves the highest mean cargo but has nonzero knock-outs and substantial variation. Utility is selected as the best safety-constrained rule policy: first require zero observed knock-outs and crowding, then maximize mean cargo. It is the LLM comparison baseline and fallback; zero observed incidents is not proof of universal safety.')
    rows=[['Cargo comparison','Mean paired change','Paired SD','Approx. 95% CI','Mean > paired SD?']]
    for _,r in paired[paired.metric=='cargo_delivered'].iterrows():rows.append([r['right']+' minus '+r['left'],f'{r.mean_difference:.2f}',f'{r.sd_difference:.2f}',f'[{r.ci95_low:.2f}, {r.ci95_high:.2f}]',str(r.larger_than_paired_sd)])
    table(rows,[151,84,79,119,95]);text('<b>Table 5.</b> Paired cargo differences use seed as the matching key. Intervals use mean +/- 2.045 SD/sqrt(30), an approximate paired t interval. Whether an interval excludes zero differs from whether the mean difference exceeds one run-to-run SD. The CSV reports both and includes the other three metrics; constant-zero metrics cannot distinguish policies.')
    before=em[em.stabilize==False].set_index('seed');after=em[em.stabilize==True].set_index('seed')
    delta=after['switches']-before['switches'];cargo=after.cargo_delivered-before.cargo_delivered
    text(f'Workers can repeatedly change berth targets as per-tick crowding scores react to other workers. This is not an explicit oscillation script: it follows from greedy re-scoring and shared target counts. A changed local rule subtracts 1.5 for switching away from a previous target. Across ten matched seeds (11-20), mean target switches change from {before.switches.mean():.1f} to {after.switches.mean():.1f}; mean paired change {delta.mean():.1f}, SD {delta.std():.1f}. Cargo changes by {cargo.mean():.2f} units on average (paired SD {cargo.std():.2f}). Total target changes also include necessary changes when ships empty; this proxy does not isolate only harmful oscillation.')
    story.append(Image(str(R/'emergence_comparison.png'),width=505,height=147))
    text('<b>Figure 2.</b> Seed 11 occupancy and cumulative target switches before/after the switching penalty. Read with the ten-seed CSV rather than treating a single heat map as causal proof.')
    page();title('Task C LLM Harbour Master')
    text('Every 20 ticks, report() serializes waiting ships, berth cargo/status, storm warning, worker positions and previous execution results. The model receives text only; it has no simulation object or secret access. src/master.py separates report construction, parsing, validation, execution and feedback. The JSON fields are Thought, Action and Final Report. Thought is a short decision summary, not a request for private reasoning.')
    text('The parser checks exact field names and argument types, rejects unknown actions and limits a turn to three actions. The validator rejects missing ships, empty/unsafe berths, impossible worker counts and holds on already-docked ships. All orders are validated before execution, and execution checks each order again. After the first malformed/invalid response there are at most two retries; failure clears supervisor assignments and continues with utility workers.')
    text('The five actions are assign_workers, hold_ship, warn_storm, close_harbour and release_cargo. A deterministic publication gate requires Final Report to equal one authoritative sentence in allowed_facts. Rejected raw statements remain in logs for hallucination auditing; only grounded final reports are eligible for publication. This limits conversational flexibility and can increase retries. The gate does not validate free-form Thought, which is an internal logged decision summary and is not player-facing.')
    text('logs/llm_log.jsonl records tick, seed, digit, exact messages, raw response, returned model name, temperature, UTC date, timing, usage when supplied and errors. Replay checks exact prompts and tick rather than making new calls. Synthetic test fixtures are isolated in temporary directories and are not reported as genuine model logs.')
    import model_sections
    model_sections.comparison(text,sub,table)
    page();title('Task C Hallucination audit')
    model_sections.audit(text,sub,table)
    page();title('Task D Prompt design and injection testing')
    text('prompts/system.txt contains five labelled parts: role, context, goals, constraints and output format. The context treats manifests, crew notes and player messages as untrusted data. Three worked examples cover a storm warning, unknown ship and forged instruction. prompts/CHANGELOG.md records baseline, hierarchy, examples and grounding changes; the live pilot format failure is retained separately from the main experiment batch.')
    text('The zero-shot/few-shot comparison uses five situations: routine loading, imminent storm, a missing berth ship, a closed harbour and a waiting ship. Each version is tested once per situation (10 calls total). Strict parse success measures format following; factuality and operational suitability require separate review. The measured results follow; no compliance score is inferred from examples.')
    model_sections.format_result(text)
    rows=[['Case','Attack location and intent','Expected safe response']]
    import json
    for c in json.loads((P/'prompts/injection_cases.json').read_text())[:10]:rows.append([c['id'],c['field']+': '+c['input'],c['expected']])
    table(rows,[35,309,184]);text('<b>Table 9.</b> Ten paired injection cases, including all four starter cases. Full attack strings and expected behaviour are in prompts/injection_cases.json.')
    page();title('Task D Injection outcomes')
    model_sections.injection(text,table)
    page();title('Task E Oversight and critical analysis')
    text('Routine assignments suit on-the-loop oversight: a human can inspect logs and intervene while code enforces capacity and storm constraints. Routing is reversible but repeated reassignment can waste delivery time. hold_ship also suits on-the-loop oversight because it delays docking rather than destroying cargo; the simulation retains its hold until changed, so a production version needs expiry and an unhold control. warn_storm suits out-of-the-loop operation because a trusted warning is time-critical, low harm and expires; the code rejects a warning with no forecast or active storm.')
    text('close_harbour and release_cargo require in-the-loop approval. Closure can delay every ship and the action set does not include reopening. Cargo release discards remaining ship cargo and cannot be undone in this prototype. These consequences justify explicit approval before execution. The approval gate defaults to denial, and only an interactive person can supply APPROVE for the exact proposed action. A crew note claiming approval is disabled has no authority.')
    text('Tests demonstrate that an unapproved close leaves harbour_closed false and an unapproved release preserves cargo. A separately approved release removes cargo without inflating the delivered metric. These are execution-layer tests, not evidence that the model itself refuses every malicious request.')
    best='utility'
    text('Deploy the utility rule policy for the current prototype and retain the LLM supervisor as an experimental feature. The recorded LLM evidence consists of fixed-report tests and does not demonstrate a simulation throughput advantage over the rule policies. Deterministic routing, capacity constraints, factual publication checks and explicit critical-action approval remain necessary even if average cargo improves. In this synchronous implementation, model latency pauses the simulation; an asynchronous design would require fresh testing against stale reports and race conditions.')
    text('Lecture 7 [2] treats autonomy as four degrees: Suggests, Asks First, Acts and Reports, and Acts Alone (slide 08). Critical closure and release use Asks First; routine allocation uses Acts and Reports; timely forecast warnings use Acts Alone. Its safety guidance (slides 25-28) links least access, approval checkpoints, logs and gradual deployment with continuing human accountability. These boundaries apply even when the model sounds confident.')
    text('Limitations include one simplified grid and short horizon, which may favour particular routing choices; heuristic utility weights without tuning, which may miss better policies; censored waiting, which underestimates eventual queue delay; and fixed-report model tests using only one selected model. Temperature-zero repetitions often repeat the same response and provide limited evidence about broader output variation. Repeating prompts three times estimates only a small sample of attack variability.')
    sub('References and reproducibility')
    text('[1] CGD-460 Assignment 2 Stormwatch Harbour, supplied course assignment, 2026. Requirements, experiment sizes, parameter row and terminology follow this document. [2] CGD-460, Lecture 7 Week 4 Session 2, Agentic AI Autonomy Uses and Limits, Fall 2026. Supplied lecture slides, especially slides 07-12 and 24-28. Slide numbers refer to printed slide labels; the PDF page sequence differs.')
    text('python reproduce.py --report-only rebuilds the report from the existing measured rule results and saved experiment reviews.  README.md documents setup and live evaluation commands. Figure 2 shows original/changed local rules; the matching CSV provides the ten-seed evidence.')
    SimpleDocTemplate(str(P/'CGD460_A2_231761_Report.pdf'),pagesize=(612,792),rightMargin=42,leftMargin=42,topMargin=36,bottomMargin=42).build(story,onFirstPage=foot,onLaterPages=foot)
    declaration()

def declaration():
    body=[Paragraph('AI Usage Declaration',styles['Title'])]
    def add(s):body.append(para(s,True))
    add('<b>Student name:</b> Uzair Ahmed  <b>Student ID:</b> 231761')
    add('<b>AI tools used:</b> ChatGPT in Work Mode for the original package (backend version unrecorded); OpenAI Codex based on GPT-6 for completion and validation. Harbour Master model details are recorded in results/model_manifest.json and the accompanying report. Date of completion assistance: 30 October 2026.')
    add('<b>Tasks assisted:</b> Interpreting Tasks A-E; implementing the Python simulator, policies, evaluations, plots, model adapter, prompts, tests, report draft and this declaration. AI assistance was extensive. These outputs must not be represented as entirely unaided work.')
    add('<b>Main user prompts given:</b> "Can u do this tell me things i have to do"; "do all the task u can if i have to run something tell me"; "and add the needed propmt that would be required for the tasks in the AI declaration"; "231761"; "go after the installation complete can u go into downloads and do the stormharbor task and complete the missing things and finalize the final report for submission"; "Resume download and complete experiments".')
    add('<b>Runtime prompt used by the Harbour Master:</b> The full executable template is in prompts/system.txt. The core instruction below is reproduced in full; logs record its exact filled messages and all retries.')
    system=(P/'prompts/system.txt').read_text()
    # Keep full template in the one-page declaration, not an invented prompt summary.
    add('<font size="7">'+escape(system).replace('\n','<br/>')+'</font>')
    add('<b>Additional required prompts:</b> Three worked examples are attached in prompts/examples.txt. The zero-shot version omits them. Twelve injection inputs and expected responses are in prompts/injection_cases.json. Three hallucination probes ask about ship 9, ship 3\'s unreported captain and arrivals after tick 600. Retry prompt: "Validation error: [actual error]. Return corrected JSON using the same report." Exact filled prompts are saved when the model is run.')
    add('<b>What I changed or verified myself:</b> AI-assisted validation was executed through Codex: parameter checks, 11 safety and reproducibility tests, 120 policy runs, 20 emergence runs, completed model trials, response audits and report checks. These are automated or AI-assisted checks; separate personal student verification is not documented.')
    add('<b>Code written with AI assistance:</b> All supplied Python modules, tests and reporting scripts. The code, recorded evidence and report remain the responsibility of the student to understand and defend in the viva.')
    add('<b>Signature:</b> Uzair Ahmed  <b>Date:</b> 30 October 2026')
    # Match the assignment's Field / Your answer declaration template.
    entries=[
      ['Student name and ID',body[1]],
      ['AI tools used (name and version)',body[2]],
      ['Tasks for which each tool was used',body[3]],
      ['Prompts you gave (attach the main ones)',[body[4],body[5],body[6],body[7]]],
      ['What you changed or verified yourself',body[8]],
      ['Parts of the code written with AI assistance',body[9]],
      ['Signature and date',body[10]]]
    cells=[[para('Field',True),para('Your answer',True)]]+[[para(k,True),v] for k,v in entries]
    t=Table(cells,colWidths=[112,420],repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8f2')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#cccccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    SimpleDocTemplate(str(P/'AI_Usage_Declaration.pdf'),pagesize=(612,792),leftMargin=40,rightMargin=40,topMargin=25,bottomMargin=25).build([body[0],t])
if __name__=='__main__':build()
