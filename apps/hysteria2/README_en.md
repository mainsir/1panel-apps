## Introduction

This application deploys **Hysteria2** (QUIC / UDP) from the official image [`tobyxdd/hysteria`](https://hub.docker.com/r/tobyxdd/hysteria). TLS uses existing host Let's Encrypt certificates (for example the `ssl` folder of a 1Panel OpenResty site). Built-in **masquerade** makes ordinary visitors see a normal HTTPS site (by default a reverse proxy to Microsoft's website) instead of an empty 404.

Use a dedicated domain that already has certificates. The protocol is **UDP** and can share the host with OpenResty on **TCP 443**. Prefer **UDP 443** and open that port in the firewall / security group.

> **Isolation:** Deploy this proxy on a **separate subdomain**. Do not share the same domain or reverse-proxy site with Bitwarden / password vaults, mail, or other sensitive services.

## Features

- Protocol: Hysteria2 (UDP / QUIC) with password auth
- TLS: read-only mount of the host certificate directory; filenames configurable (defaults `fullchain.pem` / `privkey.pem`)
- Masquerade: `proxy` (default, reverse-proxy a public site) or `file` (bundled static page under `/www/masq`)
- Generates a password on first start into `keys.env`; empty form keeps it; a non-empty form password replaces it
- Rewrites `config.yaml` from the form on every start and writes an importable `hysteria2://` link to `client.txt`
- Optional up/down bandwidth limits; default `ignoreClientBandwidth: true`
- Host networking for UDP 443; architectures: amd64 / arm64

## Defaults

| Item | Value | Notes |
|---|---|---|
| UDP port | 443 | Ideal camouflage port; use 8443 if busy |
| Domain | Set at install | Share link and SNI |
| Password | Empty = auto | Stored in `keys.env` |
| Cert directory | `/opt/1panel/www/sites/your.domain/ssl` | Change to the real site path |
| Masquerade type | proxy | Or `file` |
| Masquerade URL | `https://www.microsoft.com` | Proxy mode |
| Ignore client bandwidth | true | |
| Link name | Hysteria2 | |
| Timezone | Asia/Shanghai | |

## Usage

1. Prepare a **dedicated subdomain** (for example `hy2.example.com`), point DNS at this host, and issue Let's Encrypt via 1Panel OpenResty. Cert path is usually:  
   `/opt/1panel/www/sites/hy2.example.com/ssl`
2. Install with domain, that cert directory, and UDP port (prefer 443). Password may be left empty.
3. Allow the **UDP** port in the cloud security group and host firewall (TCP need not be opened for this app alone).
4. After start, open `client.txt` in the data directory and import the `hysteria2://` link.
5. Camouflage check: visit `https://your-domain:port` with an HTTP/3-capable browser (Chrome: `--origin-to-force-quic-on=domain:port`). You should see the masquerade site, not a proxy fingerprint page.

### Coexistence with OpenResty

- OpenResty keeps **TCP 80/443** for sites and certificate renewal.
- Hysteria2 uses **UDP 443** (or another UDP port). They do not conflict.
- This app does **not** enable `listenHTTP` / `listenHTTPS` by default, so it will not steal OpenResty's TCP ports. QUIC masquerade is enough for typical probes.

### Firewall examples

```bash
ufw allow 443/udp
# or
firewall-cmd --add-port=443/udp --permanent && firewall-cmd --reload
```

## Data

| Path | Description |
|---|---|
| `./data/keys.env` | Password (persisted) |
| `./data/config.yaml` | Hysteria2 runtime config |
| `./data/client.txt` | Node link and client parameters |
| `./www/` | Static site for file masquerade |

Back up the app in 1Panel, or save the `data` directory, before uninstalling. Uninstalling may remove the instance directory. A reinstall without `keys.env` generates a new password and invalidates old links.

## Image

`tobyxdd/hysteria:v2.13.0`
