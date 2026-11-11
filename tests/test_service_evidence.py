"""Synthetic fixtures exercise publication checks; they are not service observations."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_labs import check_service_evidence

MODEL = 'a' * 64
URL = 'https://example.test'
TIME = '2026-11-11T20:00:00+00:00'


class ServiceEvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'labs/service').mkdir(parents=True)
        self.status = {'deployment_verified': True, 'public_url': URL, 'docs_url': URL + '/docs', 'verified_at': TIME}
        self.probe = {
            'observed_at_utc': TIME, 'finished_at_utc': TIME, 'base_url': URL,
            'expected_model_sha256': MODEL, 'latency_budget_ms_per_request': 5000, 'ok': True,
            'contracts': {key: True for key in ('health', 'ready', 'model_identity_and_features', 'booking_prediction_without_distance')},
            'checks': [{'path': path, 'method': method, 'status': 200, 'elapsed_ms': 10,
                        'within_latency_budget': True, 'transport_ok': True, 'error': None}
                       for path, method in (('/health', 'GET'), ('/ready', 'GET'), ('/model', 'GET'), ('/predict', 'POST'))],
            'prediction': {'low_minutes': 1, 'predicted_minutes': 2, 'high_minutes': 3,
                           'model_version': 'taxi-booking-duration-' + MODEL[:12]},
        }
        self.evidence = {'schema_version': 1, 'deployment': {'public_url': URL, 'code_commit': 'b' * 40},
                         'observation': {'report_path': 'labs/service/probe.json', 'observed_at_utc': TIME,
                                         'workflow_head_sha': 'c' * 40,
                                         'workflow_run_url': 'https://github.com/VasilenData/taxi-eta-service/actions/runs/123'}}

    def write(self):
        raw = (json.dumps(self.probe) + '\n').encode()
        self.evidence['observation']['report_sha256'] = hashlib.sha256(raw).hexdigest()
        (self.root / 'labs/service/probe.json').write_bytes(raw)
        for relative, data in (('labs/service-status.json', self.status), ('labs/service/deployment-evidence.json', self.evidence),
                               ('labs/service/report.json', {'model_sha256': MODEL})):
            (self.root / relative).write_text(json.dumps(data), encoding='utf-8')

    def test_complete_matching_observation_passes(self):
        self.write()
        check_service_evidence(self.root)

    def test_false_or_missing_contract_fails_even_if_overall_ok(self):
        for replacement in (False, None):
            with self.subTest(replacement=replacement):
                self.probe['contracts']['ready'] = replacement
                self.write()
                with self.assertRaises(ValueError):
                    check_service_evidence(self.root)

    def test_model_url_and_prediction_identity_are_bound(self):
        original = copy.deepcopy(self.probe)
        for key, value in (('expected_model_sha256', 'd' * 64), ('base_url', 'https://other.test')):
            with self.subTest(key=key):
                self.probe = copy.deepcopy(original)
                self.probe[key] = value
                self.write()
                with self.assertRaises(ValueError):
                    check_service_evidence(self.root)
        self.probe = original
        self.probe['prediction']['model_version'] = 'different-model'
        self.write()
        with self.assertRaises(ValueError):
            check_service_evidence(self.root)

    def test_missing_endpoint_and_failed_transport_fail(self):
        original = copy.deepcopy(self.probe)
        self.probe['checks'].pop()
        self.write()
        with self.assertRaises(ValueError):
            check_service_evidence(self.root)
        self.probe = original
        self.probe['checks'][0]['transport_ok'] = False
        self.write()
        with self.assertRaises(ValueError):
            check_service_evidence(self.root)

    def test_nonfinite_or_over_budget_observation_fails(self):
        for value in (float('nan'), float('inf'), -1, 5001, True):
            with self.subTest(value=value):
                self.probe['checks'][0]['elapsed_ms'] = value
                self.write()
                with self.assertRaises(ValueError):
                    check_service_evidence(self.root)

    def test_changed_probe_bytes_fail_without_rewriting_identity(self):
        self.write()
        path = self.root / 'labs/service/probe.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            check_service_evidence(self.root)

    def test_timestamp_and_path_scope_are_checked(self):
        self.probe['finished_at_utc'] = '2026-11-11T19:00:00+00:00'
        self.write()
        with self.assertRaises(ValueError):
            check_service_evidence(self.root)
        self.probe['finished_at_utc'] = TIME
        self.evidence['observation']['report_path'] = '../outside.json'
        self.write()
        with self.assertRaises(ValueError):
            check_service_evidence(self.root)

    def test_unverified_status_does_not_require_deployment_evidence(self):
        self.status['deployment_verified'] = False
        self.write()
        (self.root / 'labs/service/deployment-evidence.json').unlink()
        check_service_evidence(self.root)


if __name__ == '__main__':
    unittest.main()
