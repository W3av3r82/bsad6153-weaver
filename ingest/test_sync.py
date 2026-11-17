"""Offline tests only: no credentials or network/database connection."""
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal
import tempfile
import json
from pathlib import Path
import requests
import sync


class SyncTests(unittest.TestCase):
    def query(self, exists, changed):
        conn = Mock()
        conn.execute.side_effect = [Mock(fetchone=Mock(return_value=(1,) if exists else None)),
                                   Mock(fetchone=Mock(return_value=(1,) if changed else None))]
        result = sync.upsert(conn,'hourly_weather',{'location_id':1,'valid_at':'time'},
            {'location_id':1,'valid_at':'time','source':'fcst','temperature_f':Decimal('50')})
        return result, conn.execute.call_args_list[-1].args[0].as_string()

    def test_insert_update_and_noop_classification(self):
        for exists,changed,want in [(False,True,'inserted'),(True,True,'updated'),(True,False,'unchanged')]:
            with self.subTest(want=want):
                result,query=self.query(exists,changed)
                self.assertEqual(result,want)
                self.assertIn('IS DISTINCT FROM',query)
                self.assertIn('last_updated_at=now()',query)
                self.assertIn('EXCLUDED.source',query)
                self.assertIn('%s',query)

    def test_forecast_requests_have_no_historical_date_and_bounded_allowance(self):
        payload={'queryCost':1,'days':[{'hours':[{'source':'fcst'}]}]}
        response=Mock();response.json.return_value=payload
        with tempfile.TemporaryDirectory() as directory, patch.object(sync,'get_response',return_value=(response,1)) as request:
            cost,attempts=sync.fetch_forecasts('fake-test-key',directory)
            self.assertEqual((cost,attempts),(2,2))
            self.assertEqual(request.call_count,2)
            for call in request.call_args_list:
                self.assertEqual(call.args[2]['include'],'days,hours,fcst')
                self.assertNotIn('/2026-',call.args[1])

    def test_unexpected_cost_stops(self):
        response=Mock();response.json.return_value={'queryCost':24,'days':[{'hours':[{}]}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(sync,'get_response',return_value=(response,1)), self.assertRaises(ValueError):
            sync.fetch_forecasts('fake',directory)

    def test_errors_hide_arbitrary_messages_but_explain_known_checks(self):
        hidden = sync.safe_error(ValueError('secret-password-and-url'), 'validate payload')
        self.assertNotIn('secret-password', hidden)
        self.assertEqual(hidden, 'validate payload: ValueError')
        known = sync.safe_error(sync.SyncValidationError('Empty forecast response'), 'fetch')
        self.assertEqual(known, 'fetch: Empty forecast response')

    def test_elapsed_unlabeled_excluded_future_unlabeled_rejected(self):
        payload = dict(latitude=38.5,longitude=-97.8,timezone='America/Chicago',
            resolvedAddress='Test',days=[dict(datetime='2026-11-01',
            hours=[dict(datetimeEpoch=1793512800),
                   dict(datetimeEpoch=1793516400,source='fcst')])])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory,'0.json')
            path.write_text(json.dumps(payload))
            data,_,omitted=sync.prepare_forecasts(Path(directory))
            self.assertEqual(omitted,1)
            self.assertEqual(len(data['hourly_weather']),1)
            self.assertNotIn('source',json.loads(path.read_text())['days'][0]['hours'][0])
            payload['days'][0]['hours'][0]['datetimeEpoch']=4102444800
            path.write_text(json.dumps(payload))
            with self.assertRaises(sync.SyncValidationError):
                sync.prepare_forecasts(Path(directory))

    def test_request_failure_stops(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sync,'get_response',return_value=(None,4)), self.assertRaises(RuntimeError):
            sync.fetch_forecasts('fake',directory)


if __name__=='__main__':
    unittest.main()
