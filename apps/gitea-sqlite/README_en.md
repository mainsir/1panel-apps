## Introduction

This package deploys Gitea in a single container with SQLite. It provides Git hosting, code review, issue tracking, and collaboration without a separate database service.

## Features

- HTTP and SSH repository access.
- Application data stored in SQLite.
- Pull requests, issues, and code review.
- Gitea Actions support; job execution requires a separately configured runner.

## Default ports

| Purpose | Host port | Container port |
|---|---|---|
| Web | 3000 | 3000 |
| SSH | 222 | 22 |

Set the actual public address in the Gitea installation wizard.

Changing the SSH port in the installation parameters updates the port displayed in SSH clone URLs. Check `ROOT_URL` when using a reverse proxy or changing the Web port.

## Data directory

`./data` maps to `/data` and contains configuration, repositories, and the SQLite database. The initialization script sets UID/GID to 1000. Back up this directory before upgrading or uninstalling.

## Runtime

- Image: `gitea/gitea:1.27.3`
- Architectures: amd64, arm64
