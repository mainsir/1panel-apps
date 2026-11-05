## Introduction

This package provides HTTP and SOCKS5 proxy services. Credentials, ports, and DNS resolvers are configured in the installation form. The image is maintained by [tarampampam/3proxy-docker](https://github.com/tarampampam/3proxy-docker).

## Default ports

| Purpose | Host port | Container port |
|---|---|---|
| HTTP proxy | 3128 | 3128 |
| SOCKS5 proxy | 1080 | 1080 |

## Usage

Set a proxy username and password during installation. In the client, select HTTP or SOCKS5 and enter the server address, corresponding port, and credentials.

The connection limit applies separately to each protocol and supports 128, 256, 512, or 1024 connections. The container file descriptor limit is 8192. The application joins `1panel-network` for communication with applications on that network.

## Configuration and backup

Configuration is generated from environment variables. There is no persistent application-data mount. Preserve the instance Compose file and `.env` parameters when backing up or migrating.

## Runtime

- Image: `ghcr.io/tarampampam/3proxy:2.3.0`
- Architectures: amd64, arm64, arm/v7
