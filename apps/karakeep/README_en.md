## Introduction

Karakeep (formerly Hoarder) is a self-hosted bookmark / read-it-later app with crawling, archiving, full-text search, and optional AI tagging.

This package follows the official Docker Compose layout. It does **not** require PostgreSQL: app state uses embedded **SQLite**, search uses bundled Meilisearch, and crawling uses headless Chrome.

## Features

- Bookmarks / read-later with page snapshots
- Full-text search via Meilisearch (deployed with the app)
- Optional OpenAI auto-tagging
- Browser extensions and mobile apps (see upstream docs)

## Services

| Service | Role |
|---|---|
| web | Karakeep app (port 3000 inside container) |
| chrome | Headless browser for rendering / screenshots |
| meilisearch | Search index |

## Default Port

| Purpose | Default host port | Container port |
|---|---|---|
| Web | 3000 | 3000 |

Set **NEXTAUTH_URL** to the real public entrypoint, e.g. `http://192.168.1.10:3000` or `https://karakeep.example.com`.

## Data Directories

| Path | Content |
|---|---|
| `./data` | SQLite DB and crawled assets |
| `./meili_data` | Meilisearch index data |

Back up both directories plus the instance `.env`.

## Database

- No external PostgreSQL / MySQL is required
- Primary store is SQLite under `/data`
- SQLite WAL mode is enabled by default
