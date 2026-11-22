"""Offline validation tests; no secrets or connections."""
import csv
from pathlib import Path
import tempfile
import unittest
from check_reference import COLUMNS, ROOT, load_questions

class ReferenceTests(unittest.TestCase):
    def test_real_set(self):
        rows=load_questions(ROOT/'evals/golden_questions.csv')
        self.assertEqual(len(rows),15)
        self.assertEqual(sum(r['category']=='should_decline' for r in rows),4)
        self.assertEqual(sum(bool(r['reference_sql']) for r in rows),11)

    def test_bad_sets_rejected(self):
        rows=load_questions(ROOT/'evals/golden_questions.csv')
        for change in ('write','multiple','decline_sql','duplicate','too_few'):
            altered=[dict(r) for r in rows]
            if change=='write':altered[0]['reference_sql']='DELETE FROM public.locations'
            if change=='multiple':altered[0]['reference_sql']='SELECT 1; SELECT 2'
            if change=='decline_sql':altered[-1]['reference_sql']='SELECT 1'
            if change=='duplicate':altered[-1]['id']=altered[0]['id']
            if change=='too_few':altered=altered[:10]
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                p=Path(directory,'q.csv')
                with p.open('w',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(altered)
                with self.assertRaises(ValueError):load_questions(p)

if __name__=='__main__':unittest.main()
