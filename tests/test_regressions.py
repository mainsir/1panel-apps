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


if __name__ == '__main__':
    unittest.main()
