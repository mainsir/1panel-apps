"""Hysteria2 1.0.2 keeps UDP listen off 1Panel's TCP port check."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'apps/hysteria2'
VERSION = APP / '1.0.2'
ENTRY = VERSION / 'scripts/entrypoint.sh'
MOCK = '''#!/bin/sh
touch "$DATA_DIR/started"
exit 0
'''


class HysteriaPackageTests(unittest.TestCase):
    def test_udp_port_is_not_a_panel_tcp_port(self):
        form = yaml.safe_load((VERSION / 'data.yml').read_text())
        fields = {field['envKey']: field for field in form['additionalProperties']['formFields']}
        self.assertNotIn('PANEL_APP_PORT', ''.join(fields))
        port = fields['HY2_UDP_PORT']
        self.assertEqual(port['default'], 443)
        self.assertEqual(port['type'], 'number')
        self.assertEqual(port['rule'], 'paramPort')
        self.assertTrue(port['required'])
        self.assertTrue(port['edit'])
        self.assertEqual(port['labelZh'], 'UDP 监听端口（建议 443）')
        for key in ('TZ', 'CERT_FILE', 'KEY_FILE', 'BANDWIDTH_UP', 'BANDWIDTH_DOWN',
                    'IGNORE_CLIENT_BANDWIDTH', 'MASQUERADE_TYPE', 'LINK_NAME'):
            self.assertNotIn(key, fields)
        for key in ('SOCKS5_HOST', 'SOCKS5_PORT', 'SOCKS5_USER', 'SOCKS5_PASS'):
            self.assertEqual(fields[key]['default'], '')
            self.assertFalse(fields[key]['required'])
        self.assertEqual(fields['SOCKS5_PASS']['type'], 'password')
        self.assertEqual(fields['MASQUERADE_URL']['default'], 'https://www.microsoft.com')

        compose_text = (VERSION / 'docker-compose.yml').read_text()
        self.assertNotIn('PANEL_APP_PORT', compose_text)
        compose = yaml.safe_load(compose_text)
        service = compose['services']['hysteria2']
        self.assertEqual(service['image'], 'tobyxdd/hysteria:v2.13.0')
        self.assertEqual(service['network_mode'], 'host')
        self.assertEqual(service['restart'], 'always')
        self.assertNotIn('ports', service)
        self.assertNotIn('networks', service)
        self.assertEqual(service['environment']['HY2_UDP_PORT'], '${HY2_UDP_PORT}')
        self.assertEqual(set(service['environment']), set(fields))
        used = set(__import__('re').findall(r'\$\{([A-Za-z0-9_]+)\}', compose_text))
        self.assertTrue(used <= set(fields) | {'CONTAINER_NAME'})
        self.assertTrue(os.access(ENTRY, os.X_OK))
        self.assertIn('HY2_UDP_PORT', ENTRY.read_text())
        self.assertIn('listen: :$PORT', ENTRY.read_text())

        root = yaml.safe_load((APP / 'data.yml').read_text())
        self.assertEqual(root['additionalProperties']['key'], 'hysteria2')
        self.assertTrue(root['additionalProperties']['crossVersionUpdate'])
        self.assertIn('TCP 443', root['additionalProperties']['description']['zh'])
        self.assertTrue((APP / '1.0.1' / 'docker-compose.yml').is_file())
        self.assertTrue((VERSION / 'www/index.html').is_file())


class HysteriaEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.bin = self.work / 'bin'
        self.bin.mkdir()
        mock = self.bin / 'hysteria'
        mock.write_text(MOCK)
        mock.chmod(0o755)
        self.data = self.work / 'data'
        self.certs = self.work / 'certs'
        self.certs.mkdir()
        (self.certs / 'fullchain.pem').write_text('cert')
        (self.certs / 'privkey.pem').write_text('key')

    def start(self, **values):
        cleared = (
            'HY2_UDP_PORT', 'PANEL_APP_PORT_UDP', 'PUBLIC_HOST', 'PASSWORD',
            'MASQUERADE_URL', 'SOCKS5_HOST', 'SOCKS5_PORT', 'SOCKS5_USER',
            'SOCKS5_PASS', 'CERT_DIR', 'PANEL_ENV_FILE', 'CERT_MOUNT')
        env = {k: v for k, v in os.environ.items() if k not in cleared}
        env.update(PATH=f'{self.bin}:{env["PATH"]}', DATA_DIR=str(self.data),
                   CERT_MOUNT=str(self.certs),
                   PANEL_ENV_FILE=str(self.work / 'missing.env'))
        env.update(values)
        return subprocess.run(['sh', str(ENTRY)], env=env, capture_output=True, text=True)

    def config(self):
        return yaml.safe_load((self.data / 'config.yaml').read_text())

    def link(self):
        return next(line for line in (self.data / 'client.txt').read_text().splitlines()
                    if line.startswith('hysteria2://'))

    def test_default_listen_and_share_link(self):
        result = self.start(PUBLIC_HOST='hy2.example.com', PASSWORD='secret')
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.config()
        self.assertEqual(config['listen'], ':443')
        self.assertEqual(config['auth'], {'type': 'password', 'password': 'secret'})
        self.assertEqual(config['tls']['cert'], str(self.certs / 'fullchain.pem'))
        self.assertEqual(config['tls']['key'], str(self.certs / 'privkey.pem'))
        self.assertTrue(config['ignoreClientBandwidth'])
        self.assertNotIn('outbounds', config)
        self.assertEqual(config['masquerade']['type'], 'proxy')
        self.assertEqual(config['masquerade']['proxy']['url'], 'https://www.microsoft.com')
        parsed = urlsplit(self.link())
        self.assertEqual(parsed.scheme, 'hysteria2')
        self.assertEqual(parsed.username, 'secret')
        self.assertEqual(parsed.hostname, 'hy2.example.com')
        self.assertEqual(parsed.port, 443)
        self.assertIn('sni=hy2.example.com', parsed.query)
        self.assertIn('insecure=0', parsed.query)
        self.assertEqual(unquote(parsed.fragment), 'Hysteria2')
        self.assertIn('udp=:443', result.stdout)
        self.assertIn('egress=direct', result.stdout)
        for name in ('config.yaml', 'keys.env', 'client.txt'):
            self.assertEqual((self.data / name).stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.data / 'started').exists())

    def test_renamed_port_and_old_key_fallback(self):
        result = self.start(PUBLIC_HOST='hy2.example.com', PASSWORD='secret', HY2_UDP_PORT='08443')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config()['listen'], ':8443')
        self.assertEqual(urlsplit(self.link()).port, 8443)

        env_file = self.work / 'panel.env'
        env_file.write_text('PANEL_APP_PORT_UDP=9443\nPUBLIC_HOST=old.example.com\n')
        result = self.start(PUBLIC_HOST='from-env.example', PASSWORD='secret',
                            PANEL_ENV_FILE=str(env_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config()['listen'], ':9443')
        self.assertEqual(urlsplit(self.link()).hostname, 'old.example.com')

        env_file.write_text('HY2_UDP_PORT="10443"\nPANEL_APP_PORT_UDP=9443\nPUBLIC_HOST=new.example.com\n')
        result = self.start(PUBLIC_HOST='from-env.example', PASSWORD='secret',
                            HY2_UDP_PORT='443', PANEL_ENV_FILE=str(env_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config()['listen'], ':10443')
        self.assertEqual(urlsplit(self.link()).hostname, 'new.example.com')

    def test_password_and_socks_preserve_literals(self):
        marker = self.work / 'pwned'
        env_file = self.work / 'panel.env'
        env_file.write_text(
            'PUBLIC_HOST=hy2.example.com\n'
            'PASSWORD=p@ss"w$ord\n'
            'MASQUERADE_URL=https://example.com/a$b\n'
            'SOCKS5_HOST=proxy.example.com\n'
            'SOCKS5_PORT=01080\n'
            'SOCKS5_USER=file user\n'
            f'SOCKS5_PASS=p@ss"w$ord $(touch {marker})\n')
        result = self.start(PUBLIC_HOST='from-env.example', PASSWORD='expanded',
                            SOCKS5_HOST='env.example', SOCKS5_PORT='1',
                            SOCKS5_USER='env', SOCKS5_PASS='env',
                            PANEL_ENV_FILE=str(env_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.config()
        self.assertEqual(config['auth']['password'], 'p@ss"w$ord')
        self.assertEqual(config['masquerade']['proxy']['url'], 'https://example.com/a$b')
        outbound = config['outbounds'][0]
        self.assertEqual(outbound['type'], 'socks5')
        self.assertEqual(outbound['socks5']['addr'], 'proxy.example.com:1080')
        self.assertEqual(outbound['socks5']['username'], 'file user')
        self.assertEqual(outbound['socks5']['password'], f'p@ss"w$ord $(touch {marker})')
        self.assertFalse(marker.exists())
        self.assertIn('egress=socks5://proxy.example.com:1080', result.stdout)
        self.assertIn('出口:     socks5://proxy.example.com:1080', (self.data / 'client.txt').read_text())

    def test_empty_socks_stays_direct_and_password_persists(self):
        result = self.start(PUBLIC_HOST='hy2.example.com')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('outbounds', self.config())
        password = (self.data / 'keys.env').read_text().split('=', 1)[1].strip()
        self.assertTrue(password)
        result = self.start(PUBLIC_HOST='hy2.example.com', HY2_UDP_PORT='443', PASSWORD='')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config()['auth']['password'], password)
        self.assertIn('egress=direct', result.stdout)
        self.assertIn('出口:     direct', (self.data / 'client.txt').read_text())

    def test_invalid_values_do_not_start(self):
        cases = [
            {},
            dict(PUBLIC_HOST='https://hy2.example.com'),
            dict(PUBLIC_HOST='hy2.example.com:443'),
            dict(PUBLIC_HOST='hy2.example.com', HY2_UDP_PORT='0'),
            dict(PUBLIC_HOST='hy2.example.com', HY2_UDP_PORT='65536'),
            dict(PUBLIC_HOST='hy2.example.com', HY2_UDP_PORT='abc'),
            dict(PUBLIC_HOST='hy2.example.com', SOCKS5_HOST='proxy.example.com'),
            dict(PUBLIC_HOST='hy2.example.com', SOCKS5_PORT='1080'),
            dict(PUBLIC_HOST='hy2.example.com', MASQUERADE_URL='www.microsoft.com'),
        ]
        for values in cases:
            with self.subTest(values=values):
                started = self.data / 'started'
                if started.exists():
                    started.unlink()
                result = self.start(**values)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertFalse(started.exists())


if __name__ == '__main__':
    unittest.main()
