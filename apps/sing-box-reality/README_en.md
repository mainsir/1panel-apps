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

| Item | Value |
|---|---|
| Listen port | 38443 |
| SNI | www.nvidia.com |
| Handshake target | www.nvidia.com:443 |
| Fingerprint | chrome |
| Egress proxy (Socks5) | Empty (direct by default) |

## Usage

1. Set the public IP or domain as the client connection address during install.
2. Import the node link or parameters from `client.txt` into your client.
3. After changing port, SNI, or handshake settings, re-export and re-import the link.
4. To specify an egress proxy (e.g. for streaming unlock or residential IP), configure the optional egress proxy host and port in parameters.

## Data

- `./data/keys.env` — secrets (persisted automatically)
- `./data/config.json` — runtime config
- `./data/client.txt` — node link and client parameters

## Image

`ghcr.io/sagernet/sing-box:v1.13.14`
