## Introduction

Kasm Chrome provides a browser-accessible Chrome desktop through KasmVNC. This package persists the user directory on the host.

## Features

- HTTPS access to the Chrome desktop.
- Clipboard and file transfer support.
- Persistent browser settings, bookmarks, extensions, and downloads stored in the user directory.

## Access

| Parameter | Default |
|---|---|
| Host port | 6901 |
| Container port | 6901 |
| Protocol | HTTPS |
| Username | `kasm_user` |

Open `https://SERVER_IP:6901` and sign in with the password configured in the installation form. Use the updated address if you change the host port.

The image uses a self-signed certificate by default. A reverse proxy can provide a trusted certificate for domain-based access. The initial URL and timezone are configurable in the installation form.

## Data directory

`./data` maps to `/home/kasm-user` and contains user settings and downloads. The initialization script sets directory ownership. Back up this directory before upgrading or uninstalling.

## Runtime

- Image: `kasmweb/chrome:1.19.0`
- Architecture: amd64
- Shared memory limit: 1 GiB
