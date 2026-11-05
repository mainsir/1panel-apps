"""Regression checks for generated credentials and safe repository synchronization."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import socket
import time
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'apps/sing-box-reality/1.0.2/scripts/entrypoint.sh'
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
        inode = (self.data / 'keys.env').stat().st_ino
        mtime = (self.data / 'keys.env').stat().st_mtime_ns
        result = self.start(PANEL_APP_PORT_TCP='40443', REALITY_SNI='example.com')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.data / 'keys.env').read_bytes(), keys)
        self.assertEqual((self.data / 'keys.env').stat().st_ino, inode)
        self.assertEqual((self.data / 'keys.env').stat().st_mtime_ns, mtime)
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
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertFalse((self.data / 'started').exists())

    def test_failed_write_preserves_existing_identity_and_config(self):
        self.assertEqual(self.start().returncode, 0)
        before = {p.name: p.read_bytes() for p in self.data.iterdir() if p.is_file()}
        broken = self.bin / 'cat'
        broken.write_text('#!/bin/sh\nexit 1\n')
        broken.chmod(0o755)
        result = self.start(PANEL_APP_PORT_TCP='40443')
        self.assertNotEqual(result.returncode, 0)
        for name, content in before.items():
            self.assertEqual((self.data / name).read_bytes(), content)
        self.assertFalse(list(self.data.glob('.startup-*')))
        broken.unlink()
        self.assertEqual(self.start().returncode, 0)
        self.assertEqual((self.data / 'keys.env').read_bytes(), before['keys.env'])

    def test_failed_first_key_write_does_not_publish_partial_file(self):
        broken = self.bin / 'cat'
        broken.write_text('#!/bin/sh\ncase "$(readlink /proc/$$/fd/1)" in */keys.env) exit 1 ;; esac\nexec /bin/cat "$@"\n')
        broken.chmod(0o755)
        result = self.start()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.data / 'keys.env').exists())
        self.assertFalse((self.data / 'started').exists())
        self.assertFalse(list(self.data.glob('.startup-*')))

    def test_existing_incomplete_or_invalid_keys_are_not_regenerated(self):
        self.assertEqual(self.start().returncode, 0)
        original = (self.data / 'keys.env').read_text()
        (self.data / 'started').unlink()
        cases = ['', original.replace('PUBLIC_KEY=', 'MISSING_KEY='),
                 original.replace('abcd1234', 'not-hex'),
                 original.replace('11111111-1111-4111-8111-111111111111', 'bad-uuid')]
        for damaged in cases:
            with self.subTest(damaged=damaged[:10]):
                (self.data / 'keys.env').write_text(damaged)
                result = self.start()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.data / 'keys.env').read_text(), damaged)
                self.assertFalse((self.data / 'started').exists())

    def test_legacy_keys_without_final_newline_are_preserved(self):
        self.assertEqual(self.start().returncode, 0)
        keys = (self.data / 'keys.env').read_bytes().rstrip(b'\n')
        (self.data / 'keys.env').write_bytes(keys)
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.data / 'keys.env').read_bytes(), keys)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.repo = self.work / 'source'
        self.repo.mkdir()
        self.store = self.work / 'store'
        self.store.mkdir()
        self.git('init', '-q')
        app = self.repo / 'apps/demo/1.0.0/scripts'
        app.mkdir(parents=True)
        (app / 'uninstall.sh').write_text('old hook')
        (app.parent / 'data.yml').write_text('old version')
        (app.parent.parent / 'data.yml').write_text('name: demo')
        (app.parent.parent / 'README.md').write_text('Demo')
        self.commit()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Test',
                               '-c', 'user.email=test@example.invalid', *args],
                              check=True, capture_output=True, text=True)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-qm', 'fixture')

    def sync(self, **extra):
        env = dict(os.environ, REPO_URL=str(self.repo), LOCAL_DIR=str(self.store))
        env.update(extra)
        return subprocess.run(['bash', str(ROOT / 'scripts/sync-to-1panel.sh')],
                              env=env, capture_output=True, text=True)

    def test_explicit_source_is_used_without_touching_worktree(self):
        (self.repo / 'uncommitted').write_text('keep')
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.store / 'demo/data.yml').read_text(), 'name: demo')
        self.assertEqual((self.repo / 'uncommitted').read_text(), 'keep')
        self.assertIn('?? uncommitted', self.git('status', '--short').stdout)

    def test_mirror_deletes_old_versions_and_hooks_but_keeps_other_apps(self):
        self.assertEqual(self.sync().returncode, 0)
        app = self.repo / 'apps/demo'
        (app / '1.0.0/scripts/uninstall.sh').unlink()
        self.commit()
        self.assertEqual(self.sync().returncode, 0)
        self.assertFalse((self.store / 'demo/1.0.0/scripts/uninstall.sh').exists())
        shutil.rmtree(app / '1.0.0')
        (app / '1.0.1').mkdir()
        (app / '1.0.1/data.yml').write_text('new version')
        self.commit()
        other = self.store / 'other-source'
        other.mkdir()
        (other / 'keep').write_text('unrelated')
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.store / 'demo/1.0.0').exists())
        self.assertEqual((self.store / 'demo/1.0.1/data.yml').read_text(), 'new version')
        self.assertEqual((other / 'keep').read_text(), 'unrelated')

    def test_failed_clone_leaves_destination_unchanged(self):
        marker = self.store / 'keep'
        marker.write_text('keep')
        result = self.sync(REPO_URL=str(self.work / 'missing-repo'))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.store.iterdir()), [marker])
        self.assertEqual(marker.read_text(), 'keep')

    def test_incomplete_source_does_not_delete_installed_packages(self):
        self.assertEqual(self.sync().returncode, 0)
        (self.repo / 'apps/demo/data.yml').unlink()
        self.commit()
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.store / 'demo/data.yml').read_text(), 'name: demo')

    def test_destination_symlink_is_rejected(self):
        outside = self.work / 'outside'
        outside.mkdir()
        (outside / 'keep').write_text('keep')
        (self.store / 'demo').symlink_to(outside, target_is_directory=True)
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((outside / 'keep').read_text(), 'keep')
        self.assertEqual(len(list(outside.iterdir())), 1)

    def test_parallel_sync_is_rejected(self):
        with (self.store / '.1panel-apps-sync.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.sync()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('another synchronization', result.stderr)
            self.assertFalse((self.store / 'demo').exists())


SING_BOX = os.environ.get('SING_BOX_BINARY') or shutil.which('sing-box')


@unittest.skipUnless(SING_BOX, 'set SING_BOX_BINARY to run real sing-box checks')
class RealSingBoxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.data = self.work / 'data'
        tools = self.work / 'bin'
        tools.mkdir()
        shim = tools / 'sing-box'
        shim.write_text('#!/bin/sh\n[ "$1" != run ] || exit 0\nexec "$REAL_SING_BOX" "$@"\n')
        shim.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{tools}:{os.environ["PATH"]}',
                        DATA_DIR=str(self.data), REAL_SING_BOX=str(Path(SING_BOX).resolve()))
        for key in ['SOCKS5_HOST', 'SOCKS5_PORT', 'SOCKS5_USER', 'SOCKS5_PASS',
                    'PUBLIC_HOST', 'REALITY_SNI', 'PANEL_APP_PORT_TCP']:
            self.env.pop(key, None)

    def generate(self, **values):
        result = subprocess.run(['sh', str(ENTRY)], env=dict(self.env, **values),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_config_validation_and_key_reuse(self):
        self.generate()
        keys = (self.data / 'keys.env').read_bytes()
        self.generate(SOCKS5_HOST='proxy.example.com', SOCKS5_PORT='1080',
                      SOCKS5_USER='user', SOCKS5_PASS='中文"\\password')
        self.assertEqual((self.data / 'keys.env').read_bytes(), keys)
        outbound = json.loads((self.data / 'config.json').read_text())['outbounds'][0]
        self.assertEqual(outbound['password'], '中文"\\password')

    def test_listener_accepts_ipv4_and_ipv6(self):
        try:
            with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as sock:
                sock.bind(('::1', 0))
                port = sock.getsockname()[1]
        except OSError as err:
            self.skipTest(f'IPv6 loopback unavailable: {err}')
        self.generate(PANEL_APP_PORT_TCP=str(port), PUBLIC_HOST='::1')
        with (self.work / 'server.log').open('w+') as log:
            proc = subprocess.Popen([SING_BOX, 'run', '-c', str(self.data / 'config.json')],
                                    stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 5
                for host in ['::1', '127.0.0.1']:
                    while True:
                        try:
                            with socket.create_connection((host, port), timeout=0.2):
                                break
                        except OSError:
                            if proc.poll() is not None or time.monotonic() > deadline:
                                log.seek(0)
                                self.fail(f'{host} was not reachable: {log.read()}')
                            time.sleep(0.05)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


if __name__ == '__main__':
    unittest.main()
