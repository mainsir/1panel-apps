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

- Image: `gitea/gitea:28.2.0`
- Architectures: amd64, arm64

## Security and Upgrades

- Finish the setup wizard right after installing. Until then, anyone who can reach the port can open it, so consider restricting access with a firewall first.
- Self-registration is disabled by default on new installs, so you must create an admin account in the wizard. You can change this later in `data/gitea/conf/app.ini`.
- Keep the wizard's HTTP port at `3000`. It is the port inside the container and is reset on container start. Change the public port only in the 1Panel parameters.
- Back up before upgrading from 1.27.x to 28.x. Version 28.0 changed the egress rules: `ALLOWED_DOMAINS`, `BLOCKED_DOMAINS` and `ALLOW_LOCALNETWORKS` are deprecated, and `ALLOWED_HOST_LIST` no longer restricts public hosts in the default mode. Retest after upgrading if you use these settings, mirrors or repository migration.
