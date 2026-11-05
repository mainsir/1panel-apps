## Introduction

This package provides a VLESS over TCP inbound using sing-box, Reality TLS, and `xtls-rprx-vision`. It supports IPv4, IPv6, and an optional SOCKS5 outbound proxy.

## Defaults

| Parameter | Default | Description |
|---|---|---|
| Listen port | 38443 | Listens directly on the host using host networking |
| SNI | www.nvidia.com | Reality handshake target on port 443 |
| Client fingerprint | chrome | Included in the client link |
| Outbound proxy | Empty | Connects directly to destination servers |

## Usage

1. Set the listen port, SNI, and public address in the installation form. Enter an IP address or domain without a scheme, port, or path.
2. Read `client.txt` in the data directory for client settings and the share link. If the public address is empty, replace `<服务器IP>` in the link manually.
3. IPv6 addresses are enclosed in brackets automatically. IPv6 access requires a reachable host IPv6 address and an allowed firewall port.
4. Provide both SOCKS5 host and port when configuring an outbound proxy. Provide both username and password when authentication is required.
5. Parameter changes regenerate the runtime configuration on container startup without replacing existing node credentials.

## Credentials and upgrades

On first startup, the package generates a UUID, Reality keypair, and short ID, then saves `keys.env` after validating the configuration. Existing credentials are read without rewriting the file. Missing or malformed fields stop startup; the package does not automatically replace the node identity. Restore a valid backup to recover.

Package version `1.0.2` fixes credential publication and IPv6 listening. The image remains at `v1.13.14`. Back up `data` before upgrading an existing instance through 1Panel. Valid credentials from earlier packages are preserved.

Uninstalling may delete the instance directory. Restore the original `keys.env` before starting a reinstalled instance to retain existing client settings.

## Data directory

| Path | Contents |
|---|---|
| `./data/keys.env` | UUID, Reality keypair, and short ID |
| `./data/config.json` | Validated runtime configuration |
| `./data/client.txt` | Client settings and share link |

## Runtime

- Image: `ghcr.io/sagernet/sing-box:v1.13.14`
- Architecture: amd64
- Network: host; listens on `::` for IPv4/IPv6 TCP connections
