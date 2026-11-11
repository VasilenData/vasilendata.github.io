"""Check copied evidence bytes, local lab links and the existing three-project CV selections."""
from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


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
