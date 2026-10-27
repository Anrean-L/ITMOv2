"""Capture the existing csvpeek result using ChromeDriver's WebDriver API."""
import base64
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent / 'practice_04' / 'csvpeek'
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(PROJECT / 'src'), TMPDIR=str(HERE))
server = subprocess.Popen(['python', '-m', 'csvpeek.server', '--port', '18743'], cwd=PROJECT, env=env)
driver = subprocess.Popen(['chromedriver', '--port=19515'], cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
session = None

def call(path, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request('http://127.0.0.1:19515' + path, data=data, method=method, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)['value']

try:
    for _ in range(100):
        try:
            call('/status')
            break
        except OSError:
            time.sleep(.1)
    result = call('/session', {'capabilities': {'alwaysMatch': {'browserName': 'chrome', 'goog:chromeOptions': {'binary': '/usr/bin/chromium', 'args': ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--window-size=1440,1300', '--user-data-dir=' + str(HERE / '.chromium-profile')]}}}})
    session = result['sessionId']
    base = '/session/' + session
    call(base + '/url', {'url': 'http://127.0.0.1:18743/'})
    def element(selector):
        return call(base + '/element', {'using': 'css selector', 'value': selector})['element-6066-11e4-a52e-4f735466cecf']
    file_id = element('#file')
    call(base + '/element/' + file_id + '/value', {'text': str(PROJECT / 'examples/people.csv')})
    call(base + '/element/' + element('#analyze') + '/click', {})
    for _ in range(100):
        rows = call(base + '/execute/sync', {'script': 'return document.querySelector("#rows").textContent', 'args': []})
        if rows == '4':
            break
        time.sleep(.1)
    else:
        raise RuntimeError('Expected result not displayed')
    screenshot = call(base + '/screenshot')
    (HERE / 'csvpeek.png').write_bytes(base64.b64decode(screenshot))
    print('Screenshot saved: csvpeek.png; people.csv: 4 rows')
finally:
    if session:
        try:
            call('/session/' + session, method='DELETE')
        except Exception:
            pass
    driver.terminate()
    server.terminate()
    driver.wait()
    server.wait()
