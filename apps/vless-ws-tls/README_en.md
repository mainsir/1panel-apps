## Introduction

A VLESS + WebSocket proxy powered by [sing-box](https://sing-box.sagernet.org/), with TLS provided by OpenResty or nginx. Supports direct and SOCKS5 outbound connections and generates an importable client link.

## Installation and usage

1. Prepare a domain pointing to the server with an HTTPS certificate configured.
2. Install `1.0.5`, enter the domain, and keep the default port and WS path. Leave the SOCKS5 fields empty for direct access. For a proxy, enter its host and port, with credentials if required.
3. Add the reverse proxy configuration below to the domain's HTTPS site.
4. After startup, open `data/client.txt` in the instance directory and import the link into your client. The default node name is `VLESS-WS-TLS`, and the client connects on port `443`.

## Reverse proxy

This example uses the default port and path. Update the corresponding values if you change the installation parameters. The reverse proxy must be able to reach `127.0.0.1:18443` on the host.

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

## Data and credentials

| File | Purpose |
|---|---|
| `data/client.txt` | Client settings and import link |
| `data/keys.env` | UUID credentials |
| `data/config.json` | Generated runtime configuration |

Each instance uses one UUID, which multiple devices can share. Restarts and container recreation preserve the UUID while `data/keys.env` is retained. Back up the `data` directory before upgrading or uninstalling.
