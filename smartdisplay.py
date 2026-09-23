#!/usr/bin/env python3
"""Mac controller and offline Pi display. Python 3.10+, stdlib core."""
import argparse
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DEFAULT = {'mode': 'dashboard', 'interval': 20, 'fit': 'contain',
           'timezone': 'Asia/Taipei', 'message': '歡迎回家', 'photos': [],
           'events': [], 'calendar_updated_at': None}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        temp = f.name
    os.replace(temp, path)


def state():
    path = DATA / 'state.json'
    return {**DEFAULT, **(json.loads(path.read_text()) if path.exists() else {})}


def init():
    (DATA / 'photos').mkdir(parents=True, exist_ok=True)
    write_json(DATA / 'state.json', state())


def import_photos(source):
    init()
    count = 0
    for p in sorted(Path(source).rglob('*')):
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
            name = hashlib.sha256(p.read_bytes()).hexdigest() + p.suffix.lower()
            shutil.copyfile(p, DATA / 'photos' / name)
            count += 1
    s = state()
    s['photos'] = ['photos/' + p.name for p in sorted((DATA / 'photos').iterdir()) if p.is_file()]
    write_json(DATA / 'state.json', s)
    print(f'Imported {count} files; {len(s["photos"])} unique photos total.')


def configure(mode=None, interval=None, message=None, fit=None):
    s = state()
    for key, value in [('mode', mode), ('interval', interval), ('message', message), ('fit', fit)]:
        if value is not None:
            s[key] = value
    if s['mode'] not in {'dashboard', 'photos', 'calendar', 'blank'}:
        raise ValueError('Invalid mode')
    if not isinstance(s['interval'], int) or not 5 <= s['interval'] <= 3600:
        raise ValueError('interval must be 5..3600 seconds')
    if s['fit'] not in {'contain', 'cover'} or len(s['message']) > 500:
        raise ValueError('Invalid fit/message')
    write_json(DATA / 'state.json', s)


def event_start(event, tz):
    start = event['start']
    if 'dateTime' in start:
        return datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00')).timestamp()
    return datetime.fromisoformat(start['date']).replace(tzinfo=ZoneInfo(tz)).timestamp()


def calendar_sync(ids):
    # OAuth libraries are needed on Mac only. No secrets are deployed to Pi.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    scopes = ['https://www.googleapis.com/auth/calendar.readonly']
    secrets = ROOT / 'secrets'
    token = secrets / 'calendar-token.json'
    credentials = secrets / 'google-client.json'
    creds = Credentials.from_authorized_user_file(str(token), scopes) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials), scopes)
            creds = flow.run_local_server(port=0)
        write_json(token, json.loads(creds.to_json()))
        token.chmod(0o600)
    api = build('calendar', 'v3', credentials=creds, cache_discovery=False)
    now = datetime.now(timezone.utc)
    events = []
    for calendar in ids:
        page = None
        while True:
            response = api.events().list(calendarId=calendar, timeMin=now.isoformat(),
                timeMax=(now + timedelta(days=7)).isoformat(), singleEvents=True,
                orderBy='startTime', maxResults=250, pageToken=page).execute()
            for item in response.get('items', []):
                if item.get('status') == 'cancelled':
                    continue
                events.append({'title': item.get('summary', '（未命名）'),
                    'start': item['start'], 'end': item['end']})
            page = response.get('nextPageToken')
            if not page:
                break
    s = state()
    s['events'] = sorted(events, key=lambda e: event_start(e, s['timezone']))
    s['calendar_updated_at'] = now.isoformat()
    write_json(DATA / 'state.json', s)
    print(f'Calendar updated: {len(events)} events.')


def build(destination):
    init()
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'web', dest, dirs_exist_ok=True)
    shutil.copytree(DATA / 'photos', dest / 'photos', dirs_exist_ok=True)
    shutil.copyfile(DATA / 'state.json', dest / 'state.json')


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def list_directory(self, path):
        self.send_error(403)
        return None


def serve(directory, port):
    handler = functools.partial(Handler, directory=str(Path(directory).absolute()))
    ThreadingHTTPServer(('127.0.0.1', port), handler).serve_forever()


def deploy(host):
    # SSH alias only: no shell fragments, addresses/options from model text.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', host):
        raise ValueError('Use an SSH Host alias, e.g. smartdisplay')
    release = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + os.urandom(3).hex()
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes', host]
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp)
        subprocess.run(ssh + [f'mkdir -p ~/SmartDisplayRPI/runtime/releases/{release}'], check=True)
        subprocess.run(['rsync', '-az', '-e', 'ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10',
            tmp + '/', f'{host}:SmartDisplayRPI/runtime/releases/{release}/'], check=True)
    # Complete snapshot first, then atomically switch current; retain releases for rollback.
    remote = '''import os
from pathlib import Path
root = Path.home() / 'SmartDisplayRPI/runtime'
release = root / 'releases' / %r
assert (release / 'state.json').is_file()
link = root / 'next'
link.unlink(missing_ok=True)
link.symlink_to(release, target_is_directory=True)
os.replace(link, root / 'current')
'''
    subprocess.run(ssh + ['python3 -'], input=remote % release, text=True, check=True)
    print('Deployed', release)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    p = sub.add_parser('import-photos'); p.add_argument('directory')
    p = sub.add_parser('set'); p.add_argument('--mode', choices=['dashboard', 'photos', 'calendar', 'blank'])
    p.add_argument('--interval', type=int); p.add_argument('--message'); p.add_argument('--fit', choices=['contain','cover'])
    p = sub.add_parser('calendar'); p.add_argument('--calendar-id', action='append', default=[])
    p = sub.add_parser('build'); p.add_argument('--output', default=str(ROOT / 'runtime/current'))
    p = sub.add_parser('serve'); p.add_argument('--directory', default=str(ROOT / 'runtime/current')); p.add_argument('--port', type=int, default=8765)
    p = sub.add_parser('deploy'); p.add_argument('--host', default='smartdisplay')
    args = parser.parse_args()
    if args.command == 'init': init()
    elif args.command == 'import-photos': import_photos(args.directory)
    elif args.command == 'set': configure(args.mode, args.interval, args.message, args.fit)
    elif args.command == 'calendar': calendar_sync(args.calendar_id or ['primary'])
    elif args.command == 'build': build(args.output)
    elif args.command == 'serve': serve(args.directory, args.port)
    elif args.command == 'deploy': deploy(args.host)


if __name__ == '__main__':
    main()
