# 1Panel Local App Repository

This repository contains third-party packages for the 1Panel local app store. Application configuration, installation forms, and lifecycle scripts are versioned together.

[简体中文](README.md) · [Packaging specification](1Panel本地应用制作规范.md)

## Requirements

- A Linux host with 1Panel installed.
- Bash, Git, rsync, and flock (provided by util-linux).
- Write access to the local app store directory.

On Debian / Ubuntu:

```bash
apt-get install -y git rsync util-linux curl
```

## Synchronization

Download and run the synchronization script:

```bash
curl -fsSL https://raw.githubusercontent.com/mainsir/1panel-apps/main/scripts/sync-to-1panel.sh \
  -o /tmp/1panel-apps-sync.sh && bash /tmp/1panel-apps-sync.sh
```

Each run fetches the specified repository's default branch. It does not read or update an existing working tree at `/opt/1panel-apps`. A fetch failure stops synchronization.

| Variable | Default | Description |
|---|---|---|
| `REPO_URL` | `https://github.com/mainsir/1panel-apps.git` | Repository URL or local Git repository path |
| `LOCAL_DIR` | `/opt/1panel/resource/apps/local` | Local app store directory |

To select another source or destination:

```bash
REPO_URL=https://github.com/example/apps.git \
LOCAL_DIR=/opt/1panel/resource/apps/local \
bash /tmp/1panel-apps-sync.sh
```

To use a local Git repository:

```bash
REPO_URL=/opt/1panel-apps bash /opt/1panel-apps/scripts/sync-to-1panel.sh
```

Only committed content is copied from local repositories. `USE_TMP` has been removed; all sources are read through a temporary clone.

### Scope

- Each source app replaces the matching app-key directory, including removal of obsolete versions and files.
- Other app-key directories are preserved. Different sources should not share an app key.
- Apps removed entirely from the source are retained in the destination for manual review and removal.
- Installed instances and their data are not updated. Upgrade instances separately in 1Panel.
- Concurrent synchronization to the same destination is rejected. A failure returns a nonzero exit status; completed app updates are not rolled back. Resolve the error and rerun the script.

Point `LOCAL_DIR` to the app store, not to installed instances. Local changes within matching package directories are overwritten.

## Installation and upgrades

1. Synchronize the packages and open the 1Panel app store.
2. Select **Update App List**, then the **Local** category.
3. Select an application and complete its installation form.

Back up existing instances before upgrading through 1Panel. Changing a package without changing its version does not update installed instances; publish a new package version for behavior changes.

For scheduled synchronization, create a Shell task in 1Panel and use the download-and-run command above.

## Applications

| Application | Architectures | Description |
|---|---|---|
| [3proxy](apps/3proxy) | amd64, arm64, arm/v7 | HTTP and SOCKS5 proxy with username/password authentication |
| [Gitea SQLite](apps/gitea-sqlite) | amd64, arm64 | Single-container Git hosting with SQLite |
| [Kasm Chrome](apps/kasmweb-chrome) | amd64 | Browser-accessible Chrome desktop with a persistent user directory |
| [VLESS Reality](apps/sing-box-reality) | amd64 | VLESS Reality inbound service based on sing-box |

## Validation

Local development and CI use the same validation entry point:

```bash
python3 -m pip install pyyaml pillow
python3 scripts/validate-apps.py
python3 -m unittest discover -s tests -v
```

Tests use temporary directories and do not synchronize the live app store. Set `SING_BOX_BINARY` to the sing-box executable matching the image version to validate real configuration and IPv4/IPv6 TCP listeners. These two checks are skipped when no binary is available. Installation and upgrade behavior still require testing in 1Panel.

See the [packaging specification](1Panel本地应用制作规范.md) before adding an application.

## License

This repository is distributed under the [MIT License](LICENSE). Upstream software and container images retain their respective licenses.
