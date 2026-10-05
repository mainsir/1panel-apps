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
