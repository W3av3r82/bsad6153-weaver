"""Offline loader checks: no secrets, API requests, or database connections."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from load import prepare


class PreparationTests(unittest.TestCase):
    def payload(self):
        # Both instants are local 01:00 on the Kansas fall-back day.
        return dict(latitude=38.5529, longitude=-97.8339,
            timezone='America/Chicago', resolvedAddress='Marquette, KS',
            stations={'KSLN': dict(id='KSLN', name='Station', latitude=38, longitude=-97)},
            days=[dict(datetime='2026-11-01', sunrise='06:58:00',
                moonphase=0.7, hours=[dict(datetimeEpoch=t, source='fcst',
                temp=None, winddir=180, windspeed=5, precipprob=10,
                precip=0, stations=None) for t in (1793512800, 1793516400)])])

    def prepare_files(self, *payloads):
        with tempfile.TemporaryDirectory() as directory:
            for i, payload in enumerate(payloads):
                Path(directory, f'{i}.json').write_text(json.dumps(payload))
            return prepare(Path(directory))

    def test_dst_and_nulls(self):
        data, counts = self.prepare_files(self.payload())
        self.assertEqual(len(data['hourly_weather']), 2)
        self.assertEqual(counts['missing_measurements'], 2)
        self.assertEqual(len(data['weather_station_links']), 0)
        self.assertTrue(all(v[0][3] is None for v in data['hourly_weather'].values()))

    def test_repeated_input_is_deduplicated(self):
        data, counts = self.prepare_files(self.payload(), self.payload())
        self.assertEqual(len(data['hourly_weather']), 2)
        self.assertEqual(counts['duplicate_input_hours'], 2)

    def test_observation_preferred_in_either_file_order(self):
        forecast = self.payload()
        observed = copy.deepcopy(forecast)
        for hour in observed['days'][0]['hours']:
            hour.update(source='obs', stations=['KSLN'], temp=60)
        for files in ((observed, forecast), (forecast, observed)):
            data, _ = self.prepare_files(*files)
            self.assertTrue(all(v[0][2] == 'obs' for v in data['hourly_weather'].values()))
            self.assertEqual(len(data['weather_station_links']), 2)

    def test_invalid_values_and_orphan_stations_stop_load(self):
        for field, value in [('precipprob', 101), ('stations', ['UNKNOWN']),
                              ('datetimeEpoch', 0), ('source', 'unexpected')]:
            payload = self.payload()
            payload['days'][0]['hours'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.prepare_files(payload)


if __name__ == '__main__':
    unittest.main()
