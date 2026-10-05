## Introduction

3proxy is a tiny, battle-tested free proxy server supporting HTTP/HTTPS and SOCKS4/5. This package uses an environment-variable based Docker image for one-click install in 1Panel, with authentication enabled by default.

## Features

- HTTP and SOCKS5 listeners at the same time
- Ports, credentials, and DNS are configured via install form
- Joins `1panel-network` for communication with other 1Panel apps
- Env-based config is easy to back up and migrate

## Default Ports

| Purpose | Host (default) | Container |
|---|---|---|
| HTTP proxy | 3128 | 3128 |
| SOCKS5 proxy | 1080 | 1080 |

## Usage

After install:

- HTTP: `http://user:pass@SERVER_IP:HTTP_PORT`
- SOCKS5: `socks5://user:pass@SERVER_IP:SOCKS_PORT`

> Do not expose an open (no-auth) proxy to the public internet.

The connection limit applies to each protocol and supports 128, 256, 512, or 1024 connections. The file descriptor limit is 8192 to allow both listeners and additional overhead.

## Data Directory

This package is env-config based and has no persistent business data volume. For full custom `3proxy.cfg`, use a config-file mount approach instead.
