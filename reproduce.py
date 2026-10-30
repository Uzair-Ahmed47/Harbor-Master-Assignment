"""Reproduce the tables and PDF from saved calls without contacting a model."""
import argparse, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def run(*args):
    subprocess.run([sys.executable,*args],cwd=ROOT,check=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--report-only',action='store_true',help='Rebuild summaries and PDFs from existing evaluation CSVs.')
    a=p.parse_args()
    if not a.report_only:
        run('evaluate.py','--no-plots','--llm','--replay','logs/llm_log.jsonl')
    run('summarize_live.py')
    run('make_report.py')

if __name__=='__main__':main()
