## Introduction

This application deploys a **VLESS + WebSocket** inbound based on [sing-box](https://sing-box.sagernet.org/). TLS terminates at a front OpenResty or nginx reverse proxy. sing-box listens on localhost only, and its configuration has no Reality block.

Use it when the host already has a website certificate (Let's Encrypt). Proxy one hidden WebSocket path to the local port. Clients connect to the domain on port 443 and do not connect to sing-box directly.

## Features

- Protocol: VLESS over WebSocket, UUID only, no Vision flow
- Configurable WebSocket path, 2048-byte early data, header `Sec-WebSocket-Protocol`
- No TLS or Reality inside sing-box; the reverse proxy presents the certificate
- Generates a UUID on first start and stores it in `keys.env`; later restarts reuse it
- Rewrites `config.json` from the form on every start and writes an importable link to `client.txt`
- Optional egress: when Socks5 is set, inbound traffic leaves through that proxy; otherwise direct
- Host networking, always listening on `127.0.0.1`, so OpenResty on the same machine can reach it; architecture: amd64
- From **1.0.3**, the install form has no timezone, listen address, or link name. The container keeps the image timezone; the inbound is fixed at `127.0.0.1`; the share-link remark is fixed as `SingBox-WS`

## Defaults

| Item | Value | Description |
|---|---|---|
| Local listen port | 18443 | For the reverse proxy only; clients do not use this port |
| Listen address | 127.0.0.1 | Fixed loopback; not a form field |
| WebSocket path | `/cdn-cgi/assets/v7kQm2pLx9nR` | Change this to your own hidden path |
| Client domain | Set at install | Used for the share link, SNI, and Host |
| Link name | SingBox-WS | Fixed in the share link; not a form field |
| Fingerprint | chrome | Written into the share link |
| SOCKS5 egress | Empty (direct) | Empty host and port mean direct; username and password are optional |

## Usage

1. Enter a domain that already points at this machine and already has a certificate on OpenResty or nginx.
2. Add the WebSocket location below to that site. The location must match the WebSocket path, and the `proxy_pass` port must match the local listen port.
3. After startup, open `client.txt` in the data directory and import the node link. The client address is **domain:443**.
4. Upgrading from 1.0.1 (Reality) keeps the UUID in `keys.env` and stops using Reality keys. After the reverse proxy is in place, import the new `client.txt`. Old Reality links no longer work.

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

To change the egress address, set the SOCKS5 host and port together. Leave both empty for a direct outbound. When the proxy requires authentication, set both username and password. Ports must be from 1 to 65535. A partial setting makes the container refuse to start.

## Data

| Path | Description |
|---|---|
| `./data/keys.env` | UUID (persisted automatically) |
| `./data/config.json` | sing-box runtime config |
| `./data/client.txt` | Node link and client parameters |

## Image

`ghcr.io/sagernet/sing-box:v1.13.14`
