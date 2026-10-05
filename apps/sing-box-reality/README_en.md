## Introduction

This application deploys a **VLESS** inbound with **Reality** TLS based on [sing-box](https://sing-box.sagernet.org/).  
It is packaged for one-click installation via 1Panel local apps.

## Features

- Protocol: VLESS over TCP, Reality TLS, Vision flow
- Auto-generates UUID, Reality keypair, and shortId on first start
- Exports client connection info and node link (`client.txt`)
- Optional egress proxy: forward traffic through an upstream Socks5 proxy (direct by default)
- Host networking; architecture: amd64

## Defaults

| Item | Value | Description |
|---|---|---|
| Listen port | 38443 | Reality listen port |
| SNI | www.nvidia.com | Camouflage domain (handshake target automatically synced to 443) |
| Fingerprint | chrome | Default standard fingerprint |
| Egress proxy (Socks5) | Empty (direct by default) | Optional upstream proxy |

## Usage

1. Install directly with default settings, or customize listen port and SNI domain as needed.
2. View `client.txt` in the data directory and copy the node link to import into your client.
3. UUID and Reality keypair are generated automatically on first start and persisted in `keys.env`.
4. To specify an egress proxy (e.g. for streaming unlock or residential IP), configure the optional egress proxy host and port in parameters.
5. Proxy host and port must be provided together. When authentication is needed, provide both username and password. Ports must be between 1 and 65535; incomplete or invalid parameters prevent startup.
6. Set the public host for an importable share link. If left blank, replace `<服务器IP>` in the link with your server address. IPv6 addresses are automatically enclosed in brackets.

Back up the app through 1Panel or save the `data` directory before uninstalling. Uninstalling may remove the installation directory and keys; new keys generated after reinstallation invalidate old client links.

## Data

- `./data/keys.env` — secrets (persisted automatically)
- `./data/config.json` — runtime config
- `./data/client.txt` — node link and client parameters

## Image

`ghcr.io/sagernet/sing-box:v1.13.14`
