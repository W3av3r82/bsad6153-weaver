"""Verify app_reader permissions without changing data.

Run from the project folder: .venv/bin/python scripts/check_permissions.py
Reads APP_DATABASE_URL privately. Never uses the admin connection.
"""
from pathlib import Path
import sys

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    url = dotenv_values(ROOT / '.env').get('APP_DATABASE_URL')
    if not url:
        print('[FAIL] APP_DATABASE_URL is missing. No connection attempted.')
        return 1
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            # Bound each statement and lock wait; commit nothing during testing.
            conn.execute("SET statement_timeout = '10s'")
            conn.execute("SET lock_timeout = '3s'")
            user = conn.execute('SELECT current_user').fetchone()[0]
            conn.rollback()
            if user != 'app_reader':
                print('[FAIL] Connected user is not app_reader; stopped before tests.')
                return 1
            print('[ok] Database user: app_reader')
            passed = True
            select = 'SELECT count(*) FROM public.hourly_weather'
            print('SQL:', select)
            try:
                count = conn.execute(select).fetchone()[0]
                print(f'[ok] SELECT succeeded: {count} hourly records')
            except psycopg.Error as error:
                print(f'[FAIL] SELECT failed; SQLSTATE={error.sqlstate}')
                passed = False
            finally:
                conn.rollback()
            tests = (
                ('DELETE', 'DELETE FROM public.hourly_weather WHERE FALSE'),
                ('INSERT', '''INSERT INTO public.locations
                    (name, latitude, longitude, timezone)
                    SELECT 'permission_test', 0, 0, 'UTC' WHERE FALSE'''),
            )
            for label, sql in tests:
                # WHERE FALSE selects no rows, so even unexpected write access
                # cannot insert or delete records. Roll back regardless.
                print('SQL:', ' '.join(sql.split()))
                try:
                    conn.execute(sql)
                except psycopg.errors.InsufficientPrivilege:
                    print(f'[ok] {label}: permission denied (SQLSTATE 42501)')
                except psycopg.Error as error:
                    print(f'[FAIL] {label}: unexpected failure; SQLSTATE={error.sqlstate}')
                    passed = False
                else:
                    print(f'[FAIL] {label} was allowed; zero rows targeted, rolling back')
                    passed = False
                finally:
                    conn.rollback()
            print('PASS: read allowed; INSERT and DELETE denied.' if passed
                  else 'FAIL: expected permissions not confirmed; review grants.')
            print('No test changes committed. This checks the named tables/operations only.')
            return 0 if passed else 1
    except psycopg.Error:
        # Parsing/connection errors can contain credentials: do not print them.
        print('[FAIL] Connection/check failed. Details withheld to protect credentials.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
