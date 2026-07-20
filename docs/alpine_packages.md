# Alpine APK Packages

The Mint development machine builds and signs two Alpine 3.24 AArch64
packages for the Idun cartridge:

- `idun_action` installs all 31 Linux commands, the external SQLite help
  catalog, the C64 target service, Action libraries, and linkable 6502 runtime
  objects.
- `idun_action_full` depends on the exact matching `idun_action` release and
  adds a complete workspace template, examples, and graphics resources. Run
  `idun-action-new-workspace [directory]` after installation to copy that
  template into a writable directory.

The static AArch64 multicall executable is installed only once. Command names
under `/usr/bin` and `/usr/share/actionc64u/TOOLS` are symbolic links, avoiding
the roughly 140 MiB duplication present in a flat export.

## Build And Sign

Run the complete AArch64 export verification and APK build with:

```sh
make apk
```

For a quicker rebuild from an already verified static export:

```sh
make apk-existing
```

The first build creates a persistent 4096-bit RSA key pair. The private key is
stored with mode `0600` at:

```text
/home/quincy/idun_fork/.apk-keys/idun-action-apk.rsa
```

Do not publish or copy that private key to the Idun machine. The generated,
web-safe repository is always rebuilt at:

```text
/home/quincy/idun_fork/build/alpine-apk/repository/
├── idun-action-apk.rsa.pub
└── aarch64/
    ├── APKINDEX.tar.gz
    ├── Packages.adb
    ├── SHA256SUMS
    ├── idun_action-<version>-r<release>.apk
    └── idun_action_full-<version>-r<release>.apk
```

Both the legacy signed index and apk-tools 3 native signed index are emitted.
The build finishes by creating a clean Alpine root, trusting only the generated
public key, installing `idun_action_full` from the local repository, and
checking the complete command and data layout. Repeat that check with
`make apk-verify`.

Change `packaging/alpine/VERSION` for a new upstream version. Use
`--pkgrel NUMBER` with `tools/build_alpine_packages.sh` when rebuilding the
same upstream version as a revised Alpine package.

## Mint Web Server

Install the dedicated lightweight web service once with:

```sh
make web-install
```

This installs lighttpd, validates its configuration, and creates
`idun-action-apk.service`. Both that dedicated service and the distribution's
ordinary `lighttpd.service` are left stopped and disabled. The configured URL
on this Mint host is:

```text
http://192.168.0.26:8088/
```

When the project is ready to publish, explicitly start the dedicated service:

```sh
sudo systemctl start idun-action-apk.service
```

Starting it does not enable it across reboots. Enable it only when that is
deliberately wanted.

## Idun Client Setup

Once the Mint service is running, trust the public key and add the repository
on the Idun Alpine machine as root:

```sh
wget -O /etc/apk/keys/idun-action-apk.rsa.pub \
  http://192.168.0.26:8088/idun-action-apk.rsa.pub
printf '%s\n' 'http://192.168.0.26:8088' >> /etc/apk/repositories
apk update
apk add idun_action
```

Install the expanded package instead with:

```sh
apk add idun_action_full
```

The Idun machine consumes this repository but does not host it.
