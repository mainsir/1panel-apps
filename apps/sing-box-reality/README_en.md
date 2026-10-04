## Introduction

This application deploys a **VLESS** inbound with **Reality** TLS based on [sing-box](https://sing-box.sagernet.org/).  
It is packaged for one-click installation via 1Panel local apps.

## Features

- Protocol: VLESS over TCP, Reality TLS, Vision flow
- Auto-generates UUID, Reality keypair, and shortId on first start
- Exports client connection info (`share.link` / `client.txt`)
- Host networking; architecture: amd64

## Defaults

| Item | Value |
|---|---|
| Listen port | 38443 |
| SNI | www.nvidia.com |
| Handshake target | www.nvidia.com:443 |
| Fingerprint | chrome |

## Usage

1. Set the public IP or domain as the client connection address during install.
2. Import `share.link` or parameters from `client.txt` into your client.
3. After changing port, SNI, or handshake settings, re-export and re-import the link.

## Data

- `./data/keys.env` — secrets (keep private)
- `./data/config.json` — runtime config
- `./data/share.link` — share URI
- `./data/client.txt` — human-readable client parameters

## Image

`ghcr.io/sagernet/sing-box:v1.13.14`
