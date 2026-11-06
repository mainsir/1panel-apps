## Introduction

This application deploys a **VLESS + WebSocket** inbound based on [sing-box](https://sing-box.sagernet.org/). TLS terminates at a front OpenResty or nginx reverse proxy. sing-box listens on localhost only, and its configuration has no Reality block.

Use it when the host already has a website certificate (Let's Encrypt). Proxy the WebSocket path to the local port. Clients connect to the domain on port 443 and do not connect to sing-box directly.

The app is named **VLESS WS TLS**, with directory and app key `vless-ws-tls`. Only the current version `1.0.5` is offered.

## Features

- Protocol: VLESS over WebSocket, UUID only, no Vision flow
- Configurable WebSocket path, 2048-byte early data, header `Sec-WebSocket-Protocol`
- No TLS or Reality inside sing-box; the reverse proxy presents the certificate
- Generates a UUID on first start and stores it in `keys.env`; later restarts reuse it
- Rewrites `config.json` from the form on every start and writes an importable link to `client.txt`
- Optional egress: when Socks5 is set, inbound traffic leaves through that proxy; otherwise direct
- Host networking, always listening on `127.0.0.1`, so OpenResty on the same machine can reach it; architecture: amd64
- The install form has no timezone, listen address, or link name. The container keeps the image timezone; the inbound is fixed at `127.0.0.1`; the share-link remark is fixed as `VLESS-WS-TLS`

## Defaults

| Item | Value | Description |
|---|---|---|
| Local listen port | 18443 | For the reverse proxy only; clients do not use this port |
| Listen address | 127.0.0.1 | Fixed loopback; not a form field |
| WebSocket path | `/cdn-cgi/assets/v7kQm2pLx9nR` | Keep the default; it does not change automatically. Match the reverse proxy and client |
| Client domain | Set at install | Used for the share link, SNI, and Host |
| Link name | VLESS-WS-TLS | Fixed in the share link; not a form field |
| Fingerprint | chrome | Written into the share link |
| SOCKS5 egress | Empty (direct) | Leave all four fields empty for direct access; set host and port for a proxy, with credentials only if needed |

## Usage

1. Enter a domain that already points at this machine and already has a certificate on OpenResty or nginx, without `https://` or a path. For direct access, only enter the domain: keep the default port and WS path, and leave all four SOCKS5 fields empty. Change the local port if it is already occupied.
2. Add the WebSocket location below to that site. The location must match the WebSocket path, and the `proxy_pass` port must match the local listen port.
3. After startup, open `client.txt` in the data directory and import the node link. The client address is **domain:443**.

Back up the app in 1Panel, or save the `data` directory, before uninstalling. Uninstalling may remove the instance directory. A new install generates a new UUID and invalidates old links.

### OpenResty / nginx

TLS terminates on the site's port 443 with the existing Let's Encrypt certificate. The example uses the default path and port. If you change the form, use those values instead.

OpenResty must be able to reach `127.0.0.1` on the host (this is true when 1Panel OpenResty uses host networking). Do not expose the local listen port to the public internet.

```nginx
location = /cdn-cgi/assets/v7kQm2pLx9nR {
    proxy_pass http://127.0.0.1:18443;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
}
```

### Egress proxy

For a direct outbound, leave the SOCKS5 host, port, username, and password empty. To change the egress address, set the SOCKS5 host and port together. When the proxy requires authentication, set both username and password. Ports must be from 1 to 65535. A partial setting makes the container refuse to start.

## Users and access limits

Each instance configures one UUID, generated once and stored in `data/keys.env`. Restarts and container recreation reuse it while this file is preserved. Multiple devices and source IPs can share the UUID; there is no separate multi-user management.

The package configures no source IP allowlist, concurrent IP or device limit, bandwidth limit, traffic quota, or account expiry. The 1Panel `limit: 1` setting only limits the number of app installations to one. Limits configured separately in the reverse proxy, firewall, or upstream SOCKS5 service may still apply.

## Credentials and package upgrades

Version `1.0.5` uses the `vless-ws-tls` app identifier and the `VLESS-WS-TLS` link remark, retaining the default WS path and UUID persistence behavior.

Existing `keys.env` files are read without rewriting; a missing or invalid UUID prevents startup. New credentials are published atomically, and runtime configuration is replaced only after validation.

Back up and preserve `data`. For existing installations with the same app key, select `1.0.5` in 1Panel to upgrade. The front OpenResty or nginx provides public IPv4/IPv6 access; the backend remains on `127.0.0.1`.

## Data

| Path | Description |
|---|---|
| `./data/keys.env` | UUID (persisted automatically) |
| `./data/config.json` | sing-box runtime config |
| `./data/client.txt` | Node link and client parameters |

## Image

`ghcr.io/sagernet/sing-box:v1.13.14`
