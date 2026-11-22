"""Preview by default. Execute approved SELECTs only as app_reader.

Preview: .venv/bin/python -B evals/check_reference.py --hunt-date YYYY-MM-DD
Run: add --run (reads APP_DATABASE_URL; no weather API requests).
Later comparison: --run --compare data/raw/evals/<baseline>.json
Snapshots are private, ignored local files, not published evaluation claims.
"""
import argparse
import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ['id','question','category','reference_sql','correct_behavior','source']
CATEGORIES = {'lookup','aggregate','trend','compare','should_decline'}


def load_questions(path):
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError('CSV columns do not match required format')
        rows = list(reader)
    if len(rows) < 15 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Need at least 15 unique question IDs')
    if sum(r['source']=='baseline' for r in rows) < 8:
        raise ValueError('Need at least eight baseline/running-list questions')
    if sum(r['category']=='should_decline' for r in rows) < 3:
        raise ValueError('Need at least three should_decline questions')
    for row in rows:
        if row['category'] not in CATEGORIES or row['source'] not in {'baseline','other'}:
            raise ValueError('Invalid category or source')
        if not re.fullmatch(r'Q\d{2,}',row['id']) or not row['correct_behavior'].strip():
            raise ValueError('Invalid ID or missing expected behavior')
        query=row['reference_sql'].strip()
        if row['category']=='should_decline':
            if query:
                raise ValueError('should_decline SQL must be empty')
        elif not query or not re.match(r'(?i)^(SELECT|WITH)\b',query) or ';' in query:
            raise ValueError('Reference must be one SELECT/CTE statement without semicolons')
    return rows


def encode(value):
    if isinstance(value,(date,datetime)):
        return value.isoformat()
    if isinstance(value,Decimal):
        return str(value)
    raise TypeError('Unsupported snapshot value')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hunt-date',type=date.fromisoformat)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--compare',type=Path)
    args=parser.parse_args()
    try:
        questions=load_questions(ROOT/'evals/golden_questions.csv')
        baseline=json.loads(args.compare.read_text()) if args.compare else None
        hunt_date=args.hunt_date or (date.fromisoformat(baseline['hunt_date']) if baseline else None)
        if hunt_date is None:
            parser.error('Specify an explicit --hunt-date, or --compare an existing baseline')
        if baseline and hunt_date.isoformat()!=baseline['hunt_date']:
            parser.error('Comparison must use the same hunting date as baseline')
    except (ValueError,OSError,KeyError):
        print('FAIL: invalid question set, date, or baseline file. No connection made.')
        return 1
    print(f'Questions={len(questions)}; reference SQL={sum(bool(q["reference_sql"]) for q in questions)}; hunt date={hunt_date}')
    if not args.run:
        print('PREVIEW ONLY: CSV validated; no credentials read, connections, or SQL executed.')
        return 0
    from dotenv import dotenv_values
    import psycopg
    config={**dotenv_values(ROOT/'.env'),**os.environ}
    url=config.get('APP_DATABASE_URL')
    if not url:
        print('FAIL: APP_DATABASE_URL missing. Admin connection is never used.')
        return 1
    results={}
    failed=False
    as_of=datetime.now(timezone.utc)
    try:
        with psycopg.connect(url,connect_timeout=10,autocommit=True,
                options='-c default_transaction_read_only=on') as conn:
            user=conn.execute('SELECT current_user').fetchone()[0]
            if user!='app_reader':
                print('FAIL: not connected as app_reader; stopped before reference queries.')
                return 1
            print('Connected as app_reader; transactions are read-only.')
            with conn.transaction():
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                conn.execute("SET LOCAL statement_timeout='15s'")
                conn.execute("SET LOCAL lock_timeout='3s'")
                for question in questions:
                    key=question['id']
                    if question['category']=='should_decline':
                        results[key]={'status':'not_executed_should_decline'}
                        print(key+': should_decline — no SQL; future chatbot behavior still untested')
                        continue
                    try:
                        with conn.transaction():
                            cur=conn.execute(question['reference_sql'],{'hunt_date':hunt_date,'as_of':as_of})
                            names=[c.name for c in cur.description]
                            rows=cur.fetchmany(5001)
                            if not rows or len(rows)>5000:
                                raise ValueError('Empty or oversized reference result')
                            results[key]={'status':'pass','rows':[dict(zip(names,r)) for r in rows]}
                            print(f'{key}: PASS, {len(rows)} rows')
                    except Exception as error:
                        # Never echo SQL errors or connection strings containing secrets.
                        results[key]={'status':'fail','error_type':type(error).__name__}
                        print(f'{key}: FAIL ({type(error).__name__}); details withheld')
                        failed=True
                scheduled=conn.execute('''SELECT run_id,started_at,finished_at FROM public.sync_runs
                    WHERE status='success' AND trigger='schedule' AND details->>'mode'='live'
                    AND finished_at IS NOT NULL ORDER BY run_id''').fetchall()
        scheduled_ids=[r[0] for r in scheduled]
        snapshot={'measured_at':as_of.isoformat(),'hunt_date':hunt_date.isoformat(),
            'database_user':user,'scheduled_runs':[{'run_id':r[0],'started_at':r[1],
            'finished_at':r[2]} for r in scheduled], 'questions':questions,'results':results,
            'all_reference_queries_passed':not failed}
        if baseline:
            if questions!=baseline['questions']:
                print('FAIL: question definitions changed; establish a new baseline before comparing.')
                return 1
            baseline_time=datetime.fromisoformat(baseline['measured_at'])
            old_ids={r['run_id'] for r in baseline['scheduled_runs']}
            new_ids=sorted(r[0] for r in scheduled if r[0] not in old_ids and r[1]>=baseline_time)
            changed=[q for q in results if json.loads(json.dumps(results[q],default=encode)) != baseline['results'].get(q)]
            snapshot['comparison']={'new_scheduled_run_ids':new_ids,'changed_question_ids':changed,
                'two_additional_scheduled_runs_confirmed':len(new_ids)>=2}
            print('Additional successful scheduled runs:',len(new_ids))
            print('Changed reference answers:',', '.join(changed) or 'none')
            if len(new_ids)<2:
                print('WAIT: fewer than two additional scheduled syncs; required later check is not complete.')
        directory=ROOT/'data/raw/evals'
        directory.mkdir(parents=True,exist_ok=True)
        path=directory/(as_of.strftime('reference_%Y%m%dT%H%M%S_%fZ')+'.json')
        path.write_text(json.dumps(snapshot,default=encode,indent=2)+'\n')
        print('Snapshot saved locally:',path.relative_to(ROOT))
        print('Results confirm SQL execution/nonempty outputs, not recommendation quality or complete forecast coverage.')
        return 1 if failed else 0
    except Exception as error:
        print(f'FAIL ({type(error).__name__}); check connection/permissions privately. No success claimed.')
        return 1


if __name__=='__main__':
    raise SystemExit(main())
