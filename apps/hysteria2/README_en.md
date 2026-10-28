## Introduction

Deploys **Hysteria2** (QUIC / UDP) from [`tobyxdd/hysteria`](https://hub.docker.com/r/tobyxdd/hysteria) with host Let's Encrypt certs and built-in masquerade.

Prefer **UDP 443**; coexists with OpenResty on **TCP 443**.

## Slim form

| Field | Notes |
|---|---|
| UDP port | Default 443 |
| Domain | SNI / share link |
| Password | Empty = auto |
| Cert directory | Host `ssl` dir (`fullchain.pem` / `privkey.pem` fixed) |
| Masquerade URL | Default `https://www.microsoft.com` |
| [Advanced] SOCKS5 | All empty = **direct**; set host+port for SOCKS5 egress |

Removed from the form: timezone, cert/key filenames, masquerade type, bandwidth limits, ignoreClientBandwidth, link name. Edit `data/config.yaml` for advanced tweaks.

## Image

`tobyxdd/hysteria:v2.13.0`
