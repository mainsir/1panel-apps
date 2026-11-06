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
ENTRY = ROOT / 'apps/vless-ws-tls/1.0.6/scripts/entrypoint.sh'
MOCK = '''#!/bin/sh
case "$1 $2" in
  'generate uuid') echo 11111111-1111-4111-8111-111111111111 ;;
  'check -c') python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$3" ;;
  'run -c') touch "$DATA_DIR/started" ;;
  *) exit 1 ;;
esac
'''


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

    def generate(self, entry=ENTRY, **values):
        result = subprocess.run(['sh', str(entry)], env=dict(self.env, **({'PUBLIC_HOST': 'cdn.example.com'} | values)),
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

    def test_current_ws_config_keeps_loopback_and_uuid(self):
        entry = ROOT / 'apps/vless-ws-tls/1.0.6/scripts/entrypoint.sh'
        self.generate(entry=entry, PUBLIC_HOST='cdn.example.com')
        keys = (self.data / 'keys.env').read_bytes()
        self.generate(entry=entry, PUBLIC_HOST='cdn.example.com', WS_PATH='/changed')
        self.assertEqual((self.data / 'keys.env').read_bytes(), keys)
        inbound = json.loads((self.data / 'config.json').read_text())['inbounds'][0]
        self.assertEqual(inbound['listen'], '127.0.0.1')
        self.assertEqual(inbound['transport']['path'], '/changed')
        self.assertNotIn('tls', inbound)

    def test_listener_accepts_ipv4_loopback(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
        except OSError as err:
            self.skipTest(f'Loopback unavailable: {err}')
        self.generate(PANEL_APP_PORT_TCP=str(port), PUBLIC_HOST='::1')
        with (self.work / 'server.log').open('w+') as log:
            proc = subprocess.Popen([SING_BOX, 'run', '-c', str(self.data / 'config.json')],
                                    stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 5
                for host in ['127.0.0.1']:
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


class SocksEntrypointTests(unittest.TestCase):
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
        self.entry = ROOT / 'apps/sing-box-socks5/1.13.21/scripts/entrypoint.sh'

    def start(self, **values):
        cleared = (
            'PANEL_APP_PORT_SOCKS', 'PROXY_USERNAME', 'PROXY_PASSWORD',
            'LOG_LEVEL', 'INBOUND_TYPE', 'TZ', 'NETWORK_MODE', 'PANEL_ENV_FILE')
        env = {k: v for k, v in os.environ.items() if k not in cleared}
        env.update(PATH=f'{self.bin}:{env["PATH"]}', DATA_DIR=str(self.data),
                   PANEL_ENV_FILE=str(self.work / 'missing.env'))
        env.update(values)
        return subprocess.run(['sh', str(self.entry)], env=env, capture_output=True, text=True)

    def config(self):
        return json.loads((self.data / 'config.json').read_text())

    def test_default_socks_config_requires_auth(self):
        result = self.start(PROXY_USERNAME='user', PROXY_PASSWORD='pass')
        self.assertEqual(result.returncode, 0, result.stderr)
        inbound = self.config()['inbounds'][0]
        self.assertEqual(self.config()['log'], {'level': 'warn', 'timestamp': True})
        self.assertEqual(inbound['type'], 'socks')
        self.assertEqual(inbound['tag'], 'socks-in')
        self.assertEqual(inbound['listen'], '0.0.0.0')
        self.assertEqual(inbound['listen_port'], 10001)
        self.assertEqual(inbound['users'], [{'username': 'user', 'password': 'pass'}])
        self.assertEqual(self.config()['outbounds'], [{'type': 'direct', 'tag': 'direct'}])
        self.assertNotIn('route', self.config())
        self.assertEqual((self.data / 'config.json').stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.data / 'started').exists())

    def test_credentials_preserve_special_characters(self):
        marker = self.work / 'pwned'
        passwords = ['ab"cd', r'ab\ncd', ' trailing space ', '中文\t密码\n\n',
                     f'$(touch {marker})', f'`touch {marker}`', '$PATH']
        for password in passwords:
            with self.subTest(password=password):
                result = self.start(PROXY_USERNAME=' user"\\ ', PROXY_PASSWORD=password)
                self.assertEqual(result.returncode, 0, result.stderr)
                user = self.config()['inbounds'][0]['users'][0]
                self.assertEqual(user['username'], ' user"\\ ')
                self.assertEqual(user['password'], password)
                self.assertFalse(marker.exists())

    def test_panel_env_file_preserves_dollar_password(self):
        env_file = self.work / 'panel.env'
        env_file.write_text('OTHER=1\nPROXY_USERNAME=file user\nPROXY_PASSWORD=p@ss"w$ord\n')
        result = self.start(PROXY_USERNAME='env-user', PROXY_PASSWORD='p@ss"w',
                            PANEL_ENV_FILE=str(env_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        user = self.config()['inbounds'][0]['users'][0]
        self.assertEqual(user['username'], 'file user')
        self.assertEqual(user['password'], 'p@ss"w$ord')
        env_file.write_text("PROXY_USERNAME='fileuser'\nPROXY_PASSWORD='keep$me'\n")
        result = self.start(PANEL_ENV_FILE=str(env_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        user = self.config()['inbounds'][0]['users'][0]
        self.assertEqual(user['username'], 'fileuser')
        self.assertEqual(user['password'], 'keep$me')

    def test_mixed_inbound_and_log_level(self):
        result = self.start(PROXY_USERNAME='user', PROXY_PASSWORD='pass',
                            INBOUND_TYPE='mixed', LOG_LEVEL='debug', PANEL_APP_PORT_SOCKS='01080')
        self.assertEqual(result.returncode, 0, result.stderr)
        inbound = self.config()['inbounds'][0]
        self.assertEqual(inbound['type'], 'mixed')
        self.assertEqual(inbound['tag'], 'mixed-in')
        self.assertEqual(inbound['listen_port'], 1080)
        self.assertEqual(self.config()['log']['level'], 'debug')

    def test_invalid_values_do_not_start(self):
        cases = [
            {},
            dict(PROXY_USERNAME='user'),
            dict(PROXY_PASSWORD='password'),
            dict(PROXY_USERNAME='user', PROXY_PASSWORD='password', PANEL_APP_PORT_SOCKS='0'),
            dict(PROXY_USERNAME='user', PROXY_PASSWORD='password', PANEL_APP_PORT_SOCKS='65536'),
            dict(PROXY_USERNAME='user', PROXY_PASSWORD='password', PANEL_APP_PORT_SOCKS='abc'),
            dict(PROXY_USERNAME='user', PROXY_PASSWORD='password', LOG_LEVEL='trace'),
            dict(PROXY_USERNAME='user', PROXY_PASSWORD='password', INBOUND_TYPE='http'),
            dict(PROXY_USERNAME='user', PROXY_PASSWORD='password', INBOUND_TYPE='socks;x'),
        ]
        for values in cases:
            with self.subTest(values=values):
                result = self.start(**values)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertFalse((self.data / 'started').exists())


class SocksPackageTests(unittest.TestCase):
    def setUp(self):
        self.version = ROOT / 'apps/sing-box-socks5/1.13.21'
        self.bridge = (self.version / 'docker-compose.yml').read_text()
        self.host = (self.version / 'scripts/docker-compose.host.yml').read_text()

    def test_network_mode_script_switches_compose(self):
        import yaml
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            scripts = work / 'scripts'
            scripts.mkdir()
            for name in ('apply-network.sh', 'docker-compose.host.yml'):
                source = self.version / 'scripts' / name
                target = scripts / name
                target.write_bytes(source.read_bytes())
                target.chmod(source.stat().st_mode & 0o777)
            (work / 'docker-compose.yml').write_text(self.bridge)
            (work / '.env').write_text('PROXY_PASSWORD=ab$cd\nNETWORK_MODE="host"\n')
            result = subprocess.run(['bash', './scripts/apply-network.sh'], cwd=work,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            host = yaml.safe_load((work / 'docker-compose.yml').read_text())
            service = host['services']['sing-box-socks5']
            self.assertEqual(service['network_mode'], 'host')
            self.assertNotIn('ports', service)
            self.assertNotIn('networks', service)
            self.assertNotIn('networks', host)

            (work / 'docker-compose.yml').write_text(self.bridge)
            (work / '.env').write_text('NETWORK_MODE=bridge\n')
            result = subprocess.run(['bash', './scripts/apply-network.sh'], cwd=work,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((work / 'docker-compose.yml').read_text(), self.bridge)

            (work / '.env').write_text('NETWORK_MODE=overlay\n')
            result = subprocess.run(['bash', './scripts/apply-network.sh'], cwd=work,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_compose_files_share_image_and_declared_variables(self):
        import yaml
        form = yaml.safe_load((self.version / 'data.yml').read_text())
        env_keys = {field['envKey'] for field in form['additionalProperties']['formFields']}
        images = set()
        for text in (self.bridge, self.host):
            data = yaml.safe_load(text)
            service = data['services']['sing-box-socks5']
            images.add(service['image'])
            self.assertEqual(service['restart'], 'always')
            self.assertIn('./.env:/run/panel.env:ro', service['volumes'])
            self.assertEqual(service['ulimits']['nofile'], {'soft': 65535, 'hard': 65535})
            self.assertEqual(set(service['environment']), env_keys)
            used = set(__import__('re').findall(r'\$\{([A-Za-z0-9_]+)\}', text))
            self.assertTrue(used <= env_keys | {'CONTAINER_NAME'})
        self.assertEqual(images, {'ghcr.io/sagernet/sing-box:v1.13.21'})
        bridge = yaml.safe_load(self.bridge)
        self.assertEqual(bridge['networks']['1panel-network']['external'], True)
        self.assertNotIn('network_mode', bridge['services']['sing-box-socks5'])
        self.assertFalse((ROOT / 'apps/3proxy').exists())


class WsEntrypointTests(unittest.TestCase):
    default_link_name = 'cdn'

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
        self.entry = ROOT / 'apps/vless-ws-tls/1.0.6/scripts/entrypoint.sh'

    def start(self, **values):
        cleared = (
            'PANEL_APP_PORT_TCP', 'LISTEN_HOST', 'PUBLIC_HOST', 'WS_PATH', 'LINK_NAME',
            'SOCKS5_HOST', 'SOCKS5_PORT', 'SOCKS5_USER', 'SOCKS5_PASS', 'TZ',
            'PANEL_ENV_FILE', 'FINGERPRINT', 'UUID', 'REALITY_SNI')
        env = {k: v for k, v in os.environ.items() if k not in cleared}
        env.update(PATH=f'{self.bin}:{env["PATH"]}', DATA_DIR=str(self.data),
                   PANEL_ENV_FILE=str(self.work / 'missing.env'))
        env.update(values)
        return subprocess.run(['sh', str(self.entry)], env=env, capture_output=True, text=True)

    def config(self):
        return json.loads((self.data / 'config.json').read_text())

    def link(self):
        return next(line for line in (self.data / 'client.txt').read_text().splitlines()
                    if line.startswith('vless://'))

    def test_default_ws_config_and_share_link(self):
        from urllib.parse import parse_qs, quote, unquote, urlsplit
        result = self.start(PUBLIC_HOST='cdn.example.com')
        self.assertEqual(result.returncode, 0, result.stderr)
        inbound = self.config()['inbounds'][0]
        self.assertEqual(inbound['type'], 'vless')
        self.assertEqual(inbound['tag'], 'vless-ws-in')
        self.assertEqual(inbound['listen'], '127.0.0.1')
        self.assertEqual(inbound['listen_port'], 18443)
        self.assertEqual(set(inbound['users'][0]), {'uuid'})
        self.assertNotIn('flow', inbound['users'][0])
        self.assertNotIn('tls', inbound)
        self.assertEqual(inbound['transport'], {
            'type': 'ws',
            'path': '/cdn-cgi/assets/v7kQm2pLx9nR',
            'max_early_data': 2048,
            'early_data_header_name': 'Sec-WebSocket-Protocol',
        })
        self.assertEqual(self.config()['outbounds'], [{'type': 'direct', 'tag': 'direct'}])
        rendered = (self.data / 'config.json').read_text()
        self.assertNotIn('reality', rendered)
        self.assertNotIn('xtls-rprx-vision', rendered)
        self.assertNotIn('"tls"', rendered)
        path = '/cdn-cgi/assets/v7kQm2pLx9nR'
        uid = '11111111-1111-4111-8111-111111111111'
        expected = (
            f'vless://{uid}@cdn.example.com:443?encryption=none&security=tls'
            f'&sni=cdn.example.com&fp=chrome&type=ws&host=cdn.example.com'
            f'&path={quote(path, safe="")}&ed=2048&eh=Sec-WebSocket-Protocol#{self.default_link_name}')
        self.assertEqual(self.link(), expected)
        parsed = urlsplit(self.link())
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.hostname, 'cdn.example.com')
        self.assertEqual(parsed.port, 443)
        self.assertEqual(unquote(query['path'][0]), path)
        self.assertEqual(query['eh'], ['Sec-WebSocket-Protocol'])
        self.assertNotIn('flow', query)
        self.assertEqual((self.data / 'config.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.data / 'keys.env').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.data / 'client.txt').stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.data / 'started').exists())
        self.assertIn('public=cdn.example.com:443', result.stdout)

    def test_public_host_is_required(self):
        result = self.start()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PUBLIC_HOST', result.stderr)
        self.assertFalse((self.data / 'started').exists())
        self.assertFalse((self.data / 'config.json').exists())

    def test_path_host_and_port_changes(self):
        from urllib.parse import parse_qs, unquote, urlsplit
        result = self.start(PUBLIC_HOST='[2001:db8::1]', WS_PATH='cdn-cgi/custom',
                            PANEL_APP_PORT_TCP='018443', LISTEN_HOST='::1',
                            LINK_NAME='中文 node#1 % &')
        self.assertEqual(result.returncode, 0, result.stderr)
        inbound = self.config()['inbounds'][0]
        self.assertEqual(inbound['listen'], '127.0.0.1')
        self.assertEqual(inbound['listen_port'], 18443)
        self.assertEqual(inbound['transport']['path'], '/cdn-cgi/custom')
        parsed = urlsplit(self.link())
        self.assertEqual(parsed.hostname, '2001:db8::1')
        self.assertEqual(parsed.port, 443)
        self.assertEqual(unquote(parse_qs(parsed.query)['path'][0]), '/cdn-cgi/custom')
        self.assertEqual(unquote(parse_qs(parsed.query)['sni'][0]), '2001:db8::1')
        self.assertEqual(unquote(parsed.fragment), '2001:db8::1')
        self.assertIn('本机入站: 127.0.0.1:18443', (self.data / 'client.txt').read_text())

    def test_node_name_uses_domain_prefix_without_changing_uuid(self):
        self.data.mkdir()
        uuid = '22222222-2222-4222-8222-222222222222'
        keys = self.data / 'keys.env'
        original = f'SB_UUID={uuid}\n'
        keys.write_text(original)
        modified = keys.stat().st_mtime_ns
        cases = [
            ('hk.example.com', 'hk'),
            (' example.com ', 'example'),
            ('us01.example.com', 'us01'),
            ('hk.edge.example.com', 'hk'),
            ('example.co.uk', 'example'),
            ('hk-01.example.com', 'hk-01'),
            ('192.0.2.10', '192.0.2.10'),
            ('[2001:db8::1]', '2001:db8::1'),
        ]
        for host, name in cases:
            with self.subTest(host=host):
                result = self.start(PUBLIC_HOST=host, CONTAINER_NAME='docker-name',
                                    LINK_NAME='manual-name')
                self.assertEqual(result.returncode, 0, result.stderr)
                link = urlsplit(self.link())
                self.assertEqual(unquote(link.fragment), name)
                self.assertEqual(link.username, uuid)
                self.assertEqual(keys.read_text(), original)
                self.assertEqual(keys.stat().st_mtime_ns, modified)

    def test_uuid_persists_across_parameter_changes_and_old_reality_keys(self):
        self.data.mkdir()
        original = ('SB_UUID=22222222-2222-4222-8222-222222222222\n'
                    'PRIVATE_KEY=legacy-key\nPUBLIC_KEY=legacy-key\nSHORT_ID=abcd\n')
        keys = self.data / 'keys.env'
        keys.write_text(original)
        before = keys.stat().st_mtime_ns
        for path in ['/one', '/two']:
            result = self.start(PUBLIC_HOST='cdn.example.com', WS_PATH=path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(keys.read_text(), original)
            self.assertEqual(keys.stat().st_mtime_ns, before)
            self.assertEqual(self.config()['inbounds'][0]['users'][0]['uuid'],
                             '22222222-2222-4222-8222-222222222222')

    def test_invalid_persisted_uuid_is_not_executed_or_replaced(self):
        self.data.mkdir()
        marker = self.work / 'executed'
        original = f'touch {marker}\nSB_UUID=not-a-uuid; touch {marker}\n'
        (self.data / 'keys.env').write_text(original)
        result = self.start(PUBLIC_HOST='cdn.example.com')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SB_UUID', result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.data / 'keys.env').read_text(), original)
        self.assertFalse((self.data / 'started').exists())

    def test_keys_file_is_not_executed(self):
        self.data.mkdir()
        marker = self.work / 'executed'
        original = f'touch {marker}\n'
        (self.data / 'keys.env').write_text(original)
        result = self.start(PUBLIC_HOST='cdn.example.com')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertEqual((self.data / 'keys.env').read_text(), original)
        self.assertFalse((self.data / 'started').exists())

    def test_special_characters_are_not_expanded(self):
        marker = self.work / 'pwned'
        payload = f'/x$(touch {marker})'
        for password in ['ab"cd', r'ab\ncd', ' trailing space ', '中文\t密码\n\n',
                         f'$(touch {marker})', '$PATH']:
            with self.subTest(password=password):
                result = self.start(PUBLIC_HOST='cdn.example.com', WS_PATH=payload,
                                    SOCKS5_HOST='proxy.example.com', SOCKS5_PORT='1080',
                                    SOCKS5_USER=' user"\\ ', SOCKS5_PASS=password)
                self.assertEqual(result.returncode, 0, result.stderr)
                outbound = self.config()['outbounds'][0]
                self.assertEqual(outbound['type'], 'socks')
                self.assertEqual(outbound['username'], ' user"\\ ')
                self.assertEqual(outbound['password'], password)
                self.assertEqual(self.config()['inbounds'][0]['transport']['path'], payload)
                self.assertFalse(marker.exists())
                self.assertIn(f'socks5://proxy.example.com:1080', (self.data / 'client.txt').read_text())

    def test_panel_env_preserves_dollar_values(self):
        env_file = self.work / 'panel.env'
        env_file.write_text(
            'PUBLIC_HOST=cdn.example.com\n'
            'WS_PATH=/a$b\n'
            'LISTEN_HOST=::1\n'
            'LINK_NAME=name$1\n'
            'TZ=Asia/Shanghai\n'
            'SOCKS5_HOST=proxy.example.com\n'
            'SOCKS5_USER=file user\n'
            'SOCKS5_PASS=p@ss"w$ord\n')
        result = self.start(PUBLIC_HOST='from-env.example', WS_PATH='/from-env',
                            LISTEN_HOST='0.0.0.0', LINK_NAME='from-env',
                            SOCKS5_HOST='proxy.example.com', SOCKS5_PORT='1080',
                            SOCKS5_USER='env-user', SOCKS5_PASS='expanded',
                            PANEL_ENV_FILE=str(env_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        inbound = self.config()['inbounds'][0]
        self.assertEqual(inbound['listen'], '127.0.0.1')
        self.assertEqual(inbound['transport']['path'], '/a$b')
        outbound = self.config()['outbounds'][0]
        self.assertEqual(outbound['username'], 'file user')
        self.assertEqual(outbound['password'], 'p@ss"w$ord')
        self.assertTrue(self.link().endswith('#' + self.default_link_name))
        self.assertNotIn('name%241', self.link())

    def test_invalid_values_do_not_start(self):
        cases = [
            dict(PUBLIC_HOST='https://cdn.example.com'),
            dict(PUBLIC_HOST='cdn.example.com:443'),
            dict(PUBLIC_HOST='cdn.example.com/path'),
            dict(PUBLIC_HOST='bad host.example'),
            dict(PUBLIC_HOST='cdn.example.com', PANEL_APP_PORT_TCP='0'),
            dict(PUBLIC_HOST='cdn.example.com', PANEL_APP_PORT_TCP='65536'),
            dict(PUBLIC_HOST='cdn.example.com', WS_PATH='/has\nnewline'),
            dict(PUBLIC_HOST='cdn.example.com', SOCKS5_HOST='proxy.example.com'),
            dict(PUBLIC_HOST='cdn.example.com', SOCKS5_PORT='1080'),
            dict(PUBLIC_HOST='cdn.example.com', SOCKS5_USER='user', SOCKS5_PASS='password'),
            dict(PUBLIC_HOST='cdn.example.com', SOCKS5_HOST='proxy.example.com',
                 SOCKS5_PORT='1080', SOCKS5_USER='user'),
            dict(PUBLIC_HOST='cdn.example.com', SOCKS5_HOST='proxy.example.com',
                 SOCKS5_PORT='01080', SOCKS5_PASS='password'),
            dict(PUBLIC_HOST='cdn.example.com', SOCKS5_HOST='proxy.example.com',
                 SOCKS5_PORT='abc'),
        ]
        for values in cases:
            with self.subTest(values=values):
                started = self.data / 'started'
                if started.exists():
                    started.unlink()
                result = self.start(**values)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertFalse(started.exists())

    def test_bad_listen_host_and_link_name_are_ignored(self):
        result = self.start(PUBLIC_HOST='cdn.example.com', LISTEN_HOST='127.0.0.1:18443',
                            LINK_NAME='bad\nname')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config()['inbounds'][0]['listen'], '127.0.0.1')
        self.assertTrue(self.link().endswith('#' + self.default_link_name))

    def test_write_failure_preserves_keys_and_last_config(self):
        self.assertEqual(self.start(PUBLIC_HOST='cdn.example.com').returncode, 0)
        before = {p.name: p.read_bytes() for p in self.data.iterdir() if p.is_file()}
        broken = self.bin / 'cat'
        broken.write_text('#!/bin/sh\nexit 1\n')
        broken.chmod(0o755)
        result = self.start(PUBLIC_HOST='cdn.example.com', WS_PATH='/changed')
        self.assertNotEqual(result.returncode, 0)
        for name, content in before.items():
            self.assertEqual((self.data / name).read_bytes(), content)
        self.assertFalse(list(self.data.glob('.startup-*')))

    def test_empty_existing_keys_do_not_rotate_uuid(self):
        self.data.mkdir()
        keys = self.data / 'keys.env'
        keys.write_bytes(b'')
        result = self.start(PUBLIC_HOST='cdn.example.com')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(keys.read_bytes(), b'')
        self.assertFalse((self.data / 'started').exists())

    def test_failed_first_key_write_does_not_publish_partial_file(self):
        broken = self.bin / 'cat'
        broken.write_text('#!/bin/sh\ncase "$(readlink /proc/$$/fd/1)" in */keys.env) exit 1 ;; esac\nexec /bin/cat "$@"\n')
        broken.chmod(0o755)
        result = self.start(PUBLIC_HOST='cdn.example.com')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.data / 'keys.env').exists())
        self.assertFalse((self.data / 'started').exists())


class WsPackageTests(unittest.TestCase):
    def setUp(self):
        self.app = ROOT / 'apps/vless-ws-tls'
        self.version = self.app / '1.0.6'

    def test_compose_matches_form_and_drops_reality(self):
        import yaml
        form = yaml.safe_load((self.version / 'data.yml').read_text())
        fields = {field['envKey']: field for field in form['additionalProperties']['formFields']}
        compose_text = (self.version / 'docker-compose.yml').read_text()
        compose = yaml.safe_load(compose_text)
        service = compose['services']['vless-ws-tls']
        self.assertEqual(service['image'], 'ghcr.io/sagernet/sing-box:v1.13.14')
        self.assertEqual(service['restart'], 'always')
        self.assertEqual(service['network_mode'], 'host')
        self.assertNotIn('ports', service)
        self.assertNotIn('networks', service)
        self.assertNotIn('networks', compose)
        self.assertEqual(service['entrypoint'], ['/bin/sh', '/entrypoint.sh'])
        self.assertEqual(service['labels']['createdBy'], 'Apps')
        self.assertIn('./data:/data', service['volumes'])
        self.assertIn('./scripts/entrypoint.sh:/entrypoint.sh:ro', service['volumes'])
        self.assertIn('./.env:/run/panel.env:ro', service['volumes'])
        self.assertEqual(set(service['environment']), set(fields))
        used = set(__import__('re').findall(r'\$\{([A-Za-z0-9_]+)\}', compose_text))
        self.assertTrue(used <= set(fields) | {'CONTAINER_NAME'})
        self.assertNotIn('REALITY_SNI', fields)
        self.assertNotIn('REALITY_SNI', compose_text)
        self.assertEqual(fields['PANEL_APP_PORT_TCP']['default'], 18443)
        self.assertEqual(fields['PANEL_APP_PORT_TCP']['type'], 'number')
        self.assertEqual(fields['PANEL_APP_PORT_TCP']['rule'], 'paramPort')
        self.assertEqual(fields['PUBLIC_HOST']['labelZh'], '已配置 HTTPS 证书的域名')
        self.assertTrue(fields['PUBLIC_HOST']['required'])
        self.assertEqual(fields['WS_PATH']['default'], '/cdn-cgi/assets/v7kQm2pLx9nR')
        self.assertEqual(fields['SOCKS5_PASS']['type'], 'password')
        entry = (self.version / 'scripts/entrypoint.sh').read_text()
        self.assertNotIn('reality', entry.lower())
        self.assertNotIn('xtls-rprx-vision', entry)
        self.assertTrue(os.access(self.version / 'scripts/entrypoint.sh', os.X_OK))

    def test_metadata_describes_ws_tls(self):
        import yaml
        root = yaml.safe_load((self.app / 'data.yml').read_text())
        props = root['additionalProperties']
        self.assertEqual(props['key'], 'vless-ws-tls')
        self.assertEqual(root['name'], 'VLESS WS TLS')
        self.assertEqual(props['name'], 'VLESS WS TLS')
        self.assertIn('WebSocket', props['shortDescZh'])
        self.assertIn('前置反代', props['description']['zh'])
        self.assertNotIn('Reality', props['shortDescZh'])
        self.assertNotIn('Reality', props['shortDescEn'])
        for name in ('README.md', 'README_en.md'):
            text = (self.app / name).read_text()
            self.assertIn('proxy_pass http://127.0.0.1:18443', text)
            self.assertIn('proxy_set_header Upgrade $http_upgrade', text)
            self.assertIn('WebSocket', text)
        self.assertIn('VLESS WS TLS', (ROOT / 'README.md').read_text())
        self.assertEqual({p.name for p in self.app.iterdir() if p.is_dir()}, {'1.0.6'})


class WsCurrentFormTests(unittest.TestCase):
    def setUp(self):
        self.app = ROOT / 'apps/vless-ws-tls'
        self.version = self.app / '1.0.6'

    def test_form_drops_tz_listen_host_and_link_name(self):
        import yaml
        form = yaml.safe_load((self.version / 'data.yml').read_text())
        fields = {field['envKey']: field for field in form['additionalProperties']['formFields']}
        compose_text = (self.version / 'docker-compose.yml').read_text()
        compose = yaml.safe_load(compose_text)
        service = compose['services']['vless-ws-tls']
        self.assertEqual(set(fields), {
            'PANEL_APP_PORT_TCP', 'PUBLIC_HOST', 'WS_PATH',
            'SOCKS5_HOST', 'SOCKS5_PORT', 'SOCKS5_USER', 'SOCKS5_PASS'})
        self.assertEqual(set(service['environment']), set(fields))
        used = set(__import__('re').findall(r'\$\{([A-Za-z0-9_]+)\}', compose_text))
        self.assertTrue(used <= set(fields) | {'CONTAINER_NAME'})
        for key in ('TZ', 'LISTEN_HOST', 'LINK_NAME'):
            self.assertNotIn(key, fields)
            self.assertNotIn('${%s}' % key, compose_text)
        self.assertEqual(service['image'], 'ghcr.io/sagernet/sing-box:v1.13.14')
        self.assertEqual(service['network_mode'], 'host')
        self.assertEqual(fields['PANEL_APP_PORT_TCP']['default'], 18443)
        self.assertEqual(fields['PANEL_APP_PORT_TCP']['type'], 'number')
        self.assertEqual(fields['PANEL_APP_PORT_TCP']['rule'], 'paramPort')
        socks = {
            'SOCKS5_HOST': ('SOCKS5 出口地址（可选）', 'SOCKS5 egress host (optional)'),
            'SOCKS5_PORT': ('SOCKS5 端口（可选）', 'SOCKS5 port (optional)'),
            'SOCKS5_USER': ('SOCKS5 账号（可选）', 'SOCKS5 username (optional)'),
            'SOCKS5_PASS': ('SOCKS5 密码（可选）', 'SOCKS5 password (optional)'),
        }
        for key, (zh, en) in socks.items():
            self.assertEqual(fields[key]['default'], '')
            self.assertFalse(fields[key]['required'])
            self.assertEqual(fields[key]['labelZh'], zh)
            self.assertEqual(fields[key]['labelEn'], en)
            self.assertNotIn('高级', fields[key]['labelZh'])
            self.assertNotIn('Advanced', fields[key]['labelEn'])
            self.assertNotIn('[', fields[key]['labelEn'])
            self.assertNotIn(']', fields[key]['labelEn'])
        self.assertEqual(fields['SOCKS5_PASS']['type'], 'password')
        entry = (self.version / 'scripts/entrypoint.sh').read_text()
        self.assertIn('\nLISTEN_HOST=127.0.0.1\n', entry)
        self.assertNotIn('load_panel_value LISTEN_HOST', entry)
        self.assertNotIn('load_panel_value LINK_NAME', entry)
        self.assertNotIn('TZ', entry)
        self.assertTrue(os.access(self.version / 'scripts/entrypoint.sh', os.X_OK))
        for name in ('README.md', 'README_en.md'):
            text = (self.app / name).read_text()
            self.assertIn('1.0.6', text)
            self.assertIn('127.0.0.1', text)
            self.assertIn('hk.example.com', text)
            self.assertNotIn('Asia/Shanghai', text)


class GiteaSqliteTests(unittest.TestCase):
    def test_new_version_forces_container_port_and_closed_registration(self):
        import yaml

        app = ROOT / 'apps/gitea-sqlite'
        compose = yaml.safe_load((app / '28.2.0/docker-compose.yml').read_text())
        service = compose['services']['gitea']
        self.assertEqual(service['image'], 'gitea/gitea:28.2.0')
        self.assertIn('${PANEL_APP_PORT_HTTP}:3000', service['ports'])
        self.assertIn('${PANEL_APP_PORT_SSH}:22', service['ports'])
        self.assertIn('GITEA__server__HTTP_PORT=3000', service['environment'])
        self.assertIn('DISABLE_REGISTRATION=true', service['environment'])
        self.assertNotIn('GITEA__service__DISABLE_REGISTRATION=true', service['environment'])
        self.assertTrue(os.access(app / '28.2.0/scripts/init.sh', os.X_OK))
        old = yaml.safe_load((app / '1.27.3/docker-compose.yml').read_text())
        self.assertEqual(old['services']['gitea']['image'], 'gitea/gitea:1.27.3')


if __name__ == '__main__':
    unittest.main()
