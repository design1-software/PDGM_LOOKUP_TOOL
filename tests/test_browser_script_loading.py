"""Compile the rendered page's scripts together to catch global redeclarations."""
from html.parser import HTMLParser
from urllib.parse import urlsplit
import shutil
import subprocess

import pytest


class PageScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            attrs = dict(attrs)
            self.current = {'src': attrs.get('src'), 'type': attrs.get('type', ''), 'text': ''}

    def handle_data(self, data):
        if self.current is not None:
            self.current['text'] += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.scripts.append(self.current)
            self.current = None


@pytest.mark.parametrize('client_fixture', ['client', 'anon_client'])
def test_lookup_page_scripts_have_no_duplicate_sources_or_global_declarations(request, client_fixture):
    client = request.getfixturevalue(client_fixture)
    response = client.get('/')
    assert response.status_code == 200
    parser = PageScripts()
    parser.feed(response.get_data(as_text=True))
    seen = set()
    scripts = []
    for script in parser.scripts:
        if script['type'] not in ('', 'text/javascript', 'application/javascript'):
            continue
        if script['src']:
            url = urlsplit(script['src'])
            if url.netloc:
                continue
            assert url.path not in seen, f'Duplicate script: {url.path}'
            seen.add(url.path)
            asset = client.get(script['src'])
            assert asset.status_code == 200, script['src']
            scripts.append(asset.get_data(as_text=True))
        else:
            scripts.append(script['text'])
    assert '/static/fixed_interactive_followup.js' in seen
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is required for cross-script JavaScript syntax verification')
    result = subprocess.run([node, '--check'], input='\n;\n'.join(scripts),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
