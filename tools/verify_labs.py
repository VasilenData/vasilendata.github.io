"""Check copied evidence bytes, local lab links and the existing three-project CV selections."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def check_service_evidence(root):
    """A published deployment label requires a retained, matching HTTP observation."""
    status = json.loads((root / 'labs/service-status.json').read_text(encoding='utf-8'))
    if type(status['deployment_verified']) is not bool:
        raise ValueError('deployment_verified must be boolean')
    if not status['deployment_verified']:
        return
    evidence = json.loads((root / 'labs/service/deployment-evidence.json').read_text(encoding='utf-8'))
    deployment, observation = evidence['deployment'], evidence['observation']
    base = status['public_url']
    url = urlsplit(base)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password or url.query
            or url.fragment or base.endswith('/') or deployment['public_url'] != base
            or status['docs_url'] != base + '/docs'):
        raise ValueError('deployment URL identity differs')
    if (evidence['schema_version'] != 1 or not re.fullmatch(r'[0-9a-f]{40}', deployment['code_commit'])
            or not re.fullmatch(r'[0-9a-f]{40}', observation['workflow_head_sha'])
            or not re.fullmatch(r'https://github.com/VasilenData/taxi-eta-service/actions/runs/\d+', observation['workflow_run_url'])):
        raise ValueError('missing deployment or workflow identity')
    report_path = (root / observation['report_path']).resolve()
    if not report_path.is_relative_to((root / 'labs/service').resolve()):
        raise ValueError('probe report must remain inside the service evidence folder')
    raw = report_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != observation['report_sha256']:
        raise ValueError('probe evidence hash differs')
    probe = json.loads(raw)
    booking = json.loads((root / 'labs/service/report.json').read_text(encoding='utf-8'))
    if probe['ok'] is not True or probe['base_url'] != base or probe['expected_model_sha256'] != booking['model_sha256']:
        raise ValueError('probe did not pass for the published model and URL')
    expected_contracts = {'health', 'ready', 'model_identity_and_features', 'booking_prediction_without_distance'}
    if set(probe['contracts']) != expected_contracts or not all(v is True for v in probe['contracts'].values()):
        raise ValueError('probe contracts are incomplete or failed')
    expected_requests = [('/health', 'GET'), ('/ready', 'GET'), ('/model', 'GET'), ('/predict', 'POST')]
    if [(item['path'], item['method']) for item in probe['checks']] != expected_requests:
        raise ValueError('four endpoint observations are required')
    budget = probe['latency_budget_ms_per_request']
    if type(budget) not in (int, float) or not math.isfinite(budget) or budget <= 0:
        raise ValueError('invalid observation latency budget')
    for item in probe['checks']:
        elapsed = item['elapsed_ms']
        if (item['status'] != 200 or item['transport_ok'] is not True or item['within_latency_budget'] is not True
                or item['error'] is not None or type(elapsed) not in (int, float)
                or not math.isfinite(elapsed) or not 0 <= elapsed <= budget):
            raise ValueError('an endpoint observation failed')
    started = datetime.fromisoformat(probe['observed_at_utc'])
    finished = datetime.fromisoformat(probe['finished_at_utc'])
    if (started.utcoffset() is None or finished.utcoffset() is None or finished < started
            or status['verified_at'] != probe['observed_at_utc'] or observation['observed_at_utc'] != status['verified_at']):
        raise ValueError('observation timestamps differ or are invalid')
    values = [probe['prediction'][key] for key in ('low_minutes', 'predicted_minutes', 'high_minutes')]
    if (not all(type(value) in (int, float) and math.isfinite(value) for value in values)
            or not 0 < values[0] <= values[1] <= values[2]
            or probe['prediction']['model_version'] != 'taxi-booking-duration-' + booking['model_sha256'][:12]):
        raise ValueError('booking prediction or model version differs')


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.capabilities = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if 'id' in attributes:
            self.ids.append(attributes['id'])
            self.capabilities += attributes['id'].startswith('capability-')
        for key in ('src', 'href'):
            if key in attributes:
                self.links.append(attributes[key])


def main():
    errors = []
    try:
        check_service_evidence(ROOT)
    except (KeyError, ValueError, TypeError, OSError) as error:
        errors.append(f'service deployment evidence invalid: {error}')
    manifest = json.loads((ROOT / 'labs/source-manifest.json').read_text(encoding='utf-8'))
    for artifact in manifest['mirrored_artifacts']:
        path = ROOT / artifact['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
            errors.append(f"copied evidence differs: {artifact['path']}")
    pages = sorted((ROOT / 'labs').rglob('*.html'))
    for path in pages:
        parser = References()
        parser.feed(path.read_text(encoding='utf-8'))
        if len(parser.ids) != len(set(parser.ids)):
            errors.append(f'duplicate ids in {path.relative_to(ROOT)}')
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = ROOT / unquote(parsed.path.lstrip('/')) if parsed.path.startswith('/') else path.parent / unquote(parsed.path)
            if not parsed.path:
                target = path
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                errors.append(f'{path.relative_to(ROOT)} links to missing {link}')
        if path == ROOT / 'labs/index.html' and parser.capabilities != 7:
            errors.append('hub must contain exactly seven capability cards')
    css = (ROOT / 'labs/lab.css').read_text(encoding='utf-8')
    for reference in re.findall(r"url\(['\"]?([^)'\"]+)", css):
        if not (ROOT / 'labs' / reference).is_file():
            errors.append(f'font asset missing: {reference}')
    for report in (ROOT / 'labs').rglob('*.json'):
        json.loads(report.read_text(encoding='utf-8'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    cv = json.loads((ROOT / 'tools/cv_data.json').read_text(encoding='utf-8'))
    for name, variant in cv['variants'].items():
        if len(variant['projects']) != 3 or not (ROOT / variant['filename']).is_file():
            errors.append(f'{name}: preserve three projects and an existing PDF')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(json.dumps({'html_pages_checked': len(pages), 'mirrored_artifacts': len(manifest['mirrored_artifacts']),
                      'capabilities': 7, 'cv_variants': len(cv['variants']), 'status': 'passed'}))


if __name__ == '__main__':
    main()
