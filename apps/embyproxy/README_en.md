## Introduction

EmbyProxy is a proxy service for Emby. It can be installed in 1Panel with a configurable host Web port and admin token.

## Features

- Custom host Web port at install time
- Admin token supports random generation
- Persistent data under `./data` for backup/migration
- Bridge networking + `1panel-network` (**not host mode**)

## Default Ports

| Purpose | Host (default) | Container |
|---|---|---|
| Web | 8787 | 8787 (fixed) |

Change the host port in the install form if needed.

## Network

- Mode: bridge (port publish)
- Network: `1panel-network` (external)
- **Not** `network_mode: host`

## Data Directory

`./data` (includes `proxy.db` and related runtime files)
