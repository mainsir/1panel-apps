## Introduction

Gitea is a lightweight, open-source self-hosted Git service. This package provides a single-container deployment with an embedded SQLite3 database. It requires no external database such as MySQL or PostgreSQL and runs smoothly even on entry-level servers with 1 vCPU and 1 GB RAM.

## Features

- Git repository hosting with HTTP and SSH clone support
- Embedded SQLite3 database in a single container
- Issue tracking, pull requests, and code review
- Built-in Gitea Actions support for CI/CD
- Low resource usage, responsive web UI, and dark mode support

## Default Ports

| Purpose | Host (default) | Container |
|---|---|---|
| Web (HTTP) | 3000 | 3000 |
| SSH (Git) | 222 | 22 |

Changing the SSH port in 1Panel parameters also updates the port shown in Gitea SSH clone URLs. Set the public URL in the Gitea installation wizard, and check ROOT_URL when using a reverse proxy or changing the Web port.

## Data Directory

`./data` (contains Gitea configuration, repositories, and `gitea.db`)

## Security and Upgrades

- Finish the setup wizard right after installing. Until then, anyone who can reach the port can open it, so consider restricting access with a firewall first.
- Self-registration is disabled by default on new installs, so you must create an admin account in the wizard. You can change this later in `data/gitea/conf/app.ini`.
- Keep the wizard's HTTP port at `3000`. It is the port inside the container and is reset on container start. Change the public port only in the 1Panel parameters.
- Back up before upgrading from 1.27.x to 28.x. Version 28.0 changed the egress rules: `ALLOWED_DOMAINS`, `BLOCKED_DOMAINS` and `ALLOW_LOCALNETWORKS` are deprecated, and `ALLOWED_HOST_LIST` no longer restricts public hosts in the default mode. Retest after upgrading if you use these settings, mirrors or repository migration.
