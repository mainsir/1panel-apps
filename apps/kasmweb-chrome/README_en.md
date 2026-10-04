## Introduction

Kasm Chrome is a cloud-based desktop Chrome browser running inside Docker. Powered by KasmVNC WebRTC streaming technology, it delivers a near-native 60fps interactive browsing experience directly in any modern web browser.

This package includes full user profile persistence. Extensions, bookmarks, saved credentials, login sessions, and downloaded files remain intact across container restarts and updates.

## Features

- **Ultra-low latency streaming**: Smooth typing and scrolling via WebRTC, complete with audio support
- **Full persistence**: Mounts `/home/kasm-user` to persist bookmarks, extensions, preferences, and downloads
- **Convenient sidebar utility**: Built-in control panel for two-way clipboard sync and file transfer
- **Secure isolation**: Runs in an isolated sandbox with password-protected access

## Default Ports and Access

| Purpose | Host (default) | Container | Protocol |
|---|---|---|---|
| Web Access | 6901 | 6901 | HTTPS |

- Access URL: `https://<SERVER_IP>:6901`
- Default username: `kasm_user`
- Password: The password configured in the install form

> [!NOTE]
> The container uses a self-signed SSL certificate by default. When prompted by your browser, proceed through the security warning to access the web desktop.

## Data Directory

`./data` (mapped to `/home/kasm-user`, storing Chrome profiles, preferences, and downloads)
