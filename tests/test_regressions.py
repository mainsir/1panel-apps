"""Regression checks for generated credentials and safe repository synchronization."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'apps/sing-box-reality/1.0.1/scripts/entrypoint.sh'
MOCK = '''#!/bin/sh
case "$1 $2" in
  'generate uuid') echo 11111111-1111-4111-8111-111111111111 ;;
  'generate reality-keypair') printf 'PrivateKey: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\\nPublicKey: BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB\\n' ;;
  'generate rand') echo abcd1234 ;;
  'check -c') python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$3" ;;
  'run -c') touch "$DATA_DIR/started" ;;
  *) exit 1 ;;
esac
'''


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.bin = self.work / 'bin'
        self.bin.mkdir()
        mock = self.bin / 'sing-box'
        mock.write_text(MOCK)
        mock.chmod(0o755)
        self.data = self.work / 'data'

    def start(self, **values):
        env = {k: v for k, v in os.environ.items() if k not in (
            'PANEL_APP_PORT_TCP', 'REALITY_SNI', 'PUBLIC_HOST', 'LINK_NAME',
            'SOCKS5_HOST', 'SOCKS5_PORT', 'SOCKS5_USER', 'SOCKS5_PASS')}
        env.update(PATH=f'{self.bin}:{env["PATH"]}', DATA_DIR=str(self.data))
        env.update(values)
        return subprocess.run(['sh', str(ENTRY)], env=env, capture_output=True, text=True)

    def config(self):
        return json.loads((self.data / 'config.json').read_text())

    def test_credentials_preserve_special_characters(self):
        for password in ['ab"cd', r'ab\ncd', ' trailing space ', '中文\t密码\n\n']:
            with self.subTest(password=password):
                result = self.start(SOCKS5_HOST='proxy.example.com', SOCKS5_PORT='1080',
                                    SOCKS5_USER=' user"\\ ', SOCKS5_PASS=password)
                self.assertEqual(result.returncode, 0, result.stderr)
                outbound = self.config()['outbounds'][0]
                self.assertEqual(outbound['username'], ' user"\\ ')
                self.assertEqual(outbound['password'], password)
                self.assertEqual((self.data / 'config.json').stat().st_mode & 0o777, 0o600)

    def test_ports_normalize_and_reject_invalid_values(self):
        result = self.start(PANEL_APP_PORT_TCP='038443', SOCKS5_HOST='proxy.example.com',
                            SOCKS5_PORT='01080')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config()['inbounds'][0]['listen_port'], 38443)
        self.assertEqual(self.config()['outbounds'][0]['server_port'], 1080)
        for port in ['0', '-1', '65536', '1.5', 'abc', '999999999999999999999']:
            with self.subTest(port=port):
                result = self.start(SOCKS5_HOST='proxy.example.com', SOCKS5_PORT=port)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('SOCKS5_PORT', result.stderr)

    def test_incomplete_proxy_settings_fail(self):
        cases = [dict(SOCKS5_HOST='proxy.example.com'), dict(SOCKS5_PORT='1080'),
                 dict(SOCKS5_USER='user', SOCKS5_PASS='password'),
                 dict(SOCKS5_HOST='proxy.example.com', SOCKS5_PORT='1080', SOCKS5_USER='user'),
                 dict(SOCKS5_HOST='proxy.example.com', SOCKS5_PORT='1080', SOCKS5_PASS='password')]
        for values in cases:
            with self.subTest(values=values):
                self.assertNotEqual(self.start(**values).returncode, 0)
                self.assertFalse((self.data / 'started').exists())

    def test_keys_persist_and_parameter_changes_take_effect(self):
        self.assertEqual(self.start().returncode, 0)
        keys = (self.data / 'keys.env').read_bytes()
        result = self.start(PANEL_APP_PORT_TCP='40443', REALITY_SNI='example.com')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.data / 'keys.env').read_bytes(), keys)
        self.assertEqual(self.config()['inbounds'][0]['listen_port'], 40443)
        self.assertEqual(self.config()['inbounds'][0]['tls']['server_name'], 'example.com')

    def test_share_link_supports_ipv6_and_encoded_names(self):
        name = '中文 node#1 % &'
        for host in ['2001:db8::1', '[2001:db8::1]']:
            result = self.start(PUBLIC_HOST=host, LINK_NAME=name)
            self.assertEqual(result.returncode, 0, result.stderr)
            link = next(line for line in (self.data / 'client.txt').read_text().splitlines()
                        if line.startswith('vless://'))
            parsed = urlsplit(link)
            self.assertEqual(parsed.hostname, '2001:db8::1')
            self.assertEqual(parsed.port, 38443)
            self.assertEqual(unquote(parsed.fragment), name)

    def test_keys_file_is_not_executed(self):
        self.data.mkdir()
        marker = self.work / 'executed'
        (self.data / 'keys.env').write_text(f'touch {marker}\n')
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())


class SyncTests(unittest.TestCase):
    def test_failed_pull_does_not_reset_or_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            repo = work / 'repository'
            (repo / '.git').mkdir(parents=True)
            (repo / 'apps').mkdir()
            (repo / 'apps/local-change').write_text('keep me')
            mock = work / 'git'
            mock.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\nexit 1\n')
            mock.chmod(0o755)
            # Redirect the production default path into an isolated fixture.
            script = (ROOT / 'scripts/sync-to-1panel.sh').read_text().replace(
                '/opt/1panel-apps', str(repo))
            env = os.environ.copy()
            env.update(PATH=f'{work}:{env["PATH"]}', LOCAL_DIR=str(work / 'store'),
                       USE_TMP='0', CALL_LOG=str(work / 'calls'))
            result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            calls = (work / 'calls').read_text()
            self.assertIn('pull --ff-only', calls)
            self.assertNotIn('reset', calls)
            self.assertNotIn('fetch', calls)
            self.assertEqual((repo / 'apps/local-change').read_text(), 'keep me')
            self.assertEqual(list((work / 'store').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
