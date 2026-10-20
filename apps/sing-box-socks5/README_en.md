## Introduction

SOCKS5 proxy based on [sing-box](https://sing-box.sagernet.org/), suited to small VPS hosts with tight memory and process limits. sing-box handles connections with an event loop and requires a username and password by default.

This package replaces 3proxy. It does not open a separate HTTP proxy port.

## Features

- Authenticated SOCKS5 inbound with a direct outbound
- Optional HTTP on the same port: choose inbound `SOCKS5 + HTTP` (sing-box `mixed`)
- Port, username, password, log level, and timezone come from the install form
- Config is regenerated on every start, so parameter changes apply after a restart
- Joins `1panel-network` by default; host networking is available when Docker port publishing does not work
- `restart: always`, file descriptor limit 65535

## Defaults

| Item | Value | Description |
|---|---|---|
| Port | 10001 | Host and container use the same port in bridge mode |
| Username | proxy | Required |
| Password | random | A random suffix is appended to the default; save it |
| Inbound | SOCKS5 | Or SOCKS5 + HTTP |
| Log level | warn | |
| Timezone | Asia/Shanghai | |
| Network | bridge | host can be selected at install and cannot be edited later |

## Usage

- SOCKS5: `socks5://user:pass@SERVER_IP:PORT`
- With SOCKS5 + HTTP, the HTTP proxy uses the same endpoint: `http://user:pass@SERVER_IP:PORT`

Do not expose the proxy on the public internet without authentication. The container refuses to start when the username or password is empty.

### Network mode

**bridge** (default) attaches the external `1panel-network` and publishes the form port on the host for TCP and UDP.

On some LXC NAT hosts, published Docker ports never become reachable. Choose **host** during installation. Host mode does not join `1panel-network` and does not publish ports; sing-box listens on that port in the host network namespace.

The mode is written into the compose file on install and upgrade only. It cannot be changed from the parameter page; reinstall to switch. Upgrades re-apply the saved mode and do not turn a host install back into bridge.

If the host refuses a file descriptor limit of 65535, the container fails to start. Lower `nofile` in the compose file and recreate the container.

### Migrating from 3proxy

Stop the old instance, then install this app. For HTTP, select `SOCKS5 + HTTP`; it shares the port and credentials with SOCKS5. Sync does not delete the previous local package:

`rm -rf /opt/1panel/resource/apps/local/3proxy`

Installed 3proxy instances are left in place.

## Data

| Path | Description |
|---|---|
| `./data/config.json` | Runtime config generated at start, mode 600, includes the password |

## Image

`ghcr.io/sagernet/sing-box:v1.13.21`
