import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
import functools

spec = importlib.util.spec_from_file_location('app', Path(__file__).parents[1] / 'smartdisplay.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = patch.object(app, 'DATA', self.root / 'data')
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_invalid_settings_preserve_previous_state(self):
        app.init()
        old = app.state()
        with self.assertRaises(ValueError): app.configure(interval=0)
        self.assertEqual(old, app.state())
        with self.assertRaises(ValueError): app.configure(mode='shell')
        self.assertEqual(old, app.state())

    def test_import_deduplicates_and_excludes_unsupported(self):
        source = self.root / 'source'; source.mkdir()
        (source / 'one.jpg').write_bytes(b'test-image')
        (source / 'two.jpg').write_bytes(b'test-image')
        (source / 'token.json').write_text('secret')
        app.import_photos(source)
        self.assertEqual(len(app.state()['photos']), 1)
        destination = self.root / 'build'
        app.build(destination)
        self.assertTrue((destination / 'index.html').is_file())
        self.assertFalse((destination / 'token.json').exists())

    def test_server_follows_atomic_release_switch(self):
        first = self.root / 'a'; second = self.root / 'b'
        first.mkdir(); second.mkdir()
        (first / 'state.json').write_text('{"version":1}')
        (second / 'state.json').write_text('{"version":2}')
        current = self.root / 'current'; current.symlink_to(first)
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(app.Handler, directory=str(current)))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        url = f'http://127.0.0.1:{server.server_port}/state.json'
        try:
            with urlopen(url) as response: self.assertEqual(json.load(response)['version'], 1)
            next_link = self.root / 'next'; next_link.symlink_to(second)
            next_link.replace(current)
            with urlopen(url) as response: self.assertEqual(json.load(response)['version'], 2)
        finally:
            server.shutdown(); thread.join(); server.server_close()

    def test_calendar_offsets_and_all_day_order(self):
        # 09:00 Taiwan is earlier than 02:00 UTC, despite its larger hour.
        taiwan = {'start': {'dateTime': '2026-09-23T09:00:00+08:00'}}
        utc = {'start': {'dateTime': '2026-09-23T02:00:00Z'}}
        all_day = {'start': {'date': '2026-09-23'}}
        self.assertLess(app.event_start(taiwan, 'Asia/Taipei'), app.event_start(utc, 'Asia/Taipei'))
        self.assertLess(app.event_start(all_day, 'Asia/Taipei'), app.event_start(taiwan, 'Asia/Taipei'))

    def test_untrusted_host_rejected_before_execution(self):
        with patch.object(app.subprocess, 'run') as run:
            for host in ['-oProxyCommand=x', 'pi; touch x', 'user@host', 'a b']:
                with self.assertRaises(ValueError): app.deploy(host)
            run.assert_not_called()


if __name__ == '__main__': unittest.main()
