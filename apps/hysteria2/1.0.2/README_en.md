## Introduction

Deploys **Hysteria2** (QUIC / UDP) from [`tobyxdd/hysteria`](https://hub.docker.com/r/tobyxdd/hysteria) with host Let's Encrypt certs and built-in masquerade.

Prefer **UDP 443**; coexists with OpenResty on **TCP 443**. From **1.0.2**, the UDP port field is not checked as a 1Panel TCP port, so install succeeds while OpenResty already listens on TCP 443.

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

Upgrades from 1.0.0 / 1.0.1 keep the previous UDP listen port. Before the new field is saved, the parameter form may show the default 443; if the old port was not 443, set it back before saving.

## Image

`tobyxdd/hysteria:v2.13.0`
