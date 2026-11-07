# Getting Started

Choose a release executable or run from a Git checkout. Both use Docker to run the apps.

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | Windows 10+, macOS 12+, Linux (Debian/Ubuntu) | WSL2 supported on Windows |
| Docker | Docker Engine with Compose v2 or Docker Desktop | On Windows, use Docker Desktop with the WSL2 backend. |
| Python | 3.10+ | Only needed when running from source |

## Option A - Download the Binary (Recommended)

1. Open the [latest stable release](https://github.com/MRColorR/money4band/releases/latest)
   or choose a prerelease from [all releases](https://github.com/MRColorR/money4band/releases).
   Download the executable for your platform.

   Check your architecture with `uname -m` (`x86_64` = amd64, `aarch64` = arm64,
   `armv7l` = armv7). On Windows: **Settings > System > About > System type**.

2. Put the executable in its own directory. First run creates `config/`,
   `template/` and `.m4b/` next to it. Choose the separate source ZIP if
   you want an archive.

3. Run it.

### Windows

Double-click `Money4Band-windows-amd64.exe`. It opens a console window with the
interactive menu.

To pass CLI subcommands, or to keep the output visible after the program exits,
run it from PowerShell instead:

```powershell
cd $HOME\Money4Band
.\Money4Band-windows-amd64.exe
```

The binary is unsigned, so SmartScreen shows "Windows protected your PC" on
first launch. Click **More info > Run anyway**. Docker Desktop must be running
on the WSL2 backend.

### Linux

```bash
cd ~/Money4Band
chmod +x Money4Band-linux-amd64
./Money4Band-linux-amd64
```

Downloads arrive without the executable bit, hence the `chmod`.

M4B needs Docker access. Add your user to the `docker` group
(`sudo usermod -aG docker $USER`, then re-login) or run with `sudo`.

`noexec` mounts refuse to run the binary. Common on `/tmp`, USB sticks and NAS
shares. Keep it under `$HOME`.

### macOS

```bash
cd ~/Money4Band
xattr -d com.apple.quarantine Money4Band-macos-arm64
chmod +x Money4Band-macos-arm64
./Money4Band-macos-arm64
```

Use `-macos-arm64` on Apple Silicon, `-macos-amd64` on Intel. The build is
unsigned: without the `xattr` call Gatekeeper reports "cannot be opened because
the developer cannot be verified". **System Settings > Privacy & Security >
Open Anyway** does the same thing.

After those two commands, double-clicking in Finder works as well. Docker
Desktop must be running.

### Getting the `m4b` command

Running with no arguments opens the interactive menu. For commands shown as
`m4b <command>`, use your executable or `python run.py` from a source checkout.

```bash
./Money4Band-linux-amd64            # interactive menu
./Money4Band-linux-amd64 status     # CLI, same capability
```

Source installs get the short `m4b` name from the console script. Binary
installs do not. To use the docs verbatim, rename the file and put its
directory on `PATH`:

```bash
# Linux / macOS
mv Money4Band-linux-amd64 m4b
export PATH="$HOME/Money4Band:$PATH"     # add to ~/.bashrc or ~/.zshrc
```

```powershell
# Windows
Rename-Item .\Money4Band-windows-amd64.exe m4b.exe
$env:PATH += ";$HOME\Money4Band"         # persist via System Properties > Environment Variables
```

Rename rather than symlink. `m4b update` replaces the running executable in
place, so it needs write access to the directory it lives in. A symlink in
`/usr/local/bin` would make the updater overwrite the link as root and leave the
original file stale.

For automation over HTTP, see [Dashboard & API](dashboard-api.md).

### Verify the download (optional)

Every release publishes `checksums.sha256`. Download it alongside the binary:

```bash
sha256sum Money4Band-linux-amd64     # Linux
shasum -a 256 Money4Band-macos-arm64  # macOS
```

```powershell
Get-FileHash .\Money4Band-windows-amd64.exe -Algorithm SHA256
```

Compare the output with the line for your asset in `checksums.sha256`.

## Option B - Run from Source

```bash
git clone https://github.com/MRColorR/money4band.git
cd money4band

python run.py
```

The launcher uses `uv` if available or creates a local virtual environment
with pip. Use `python3` if your system exposes Python under that name.

## Upgrade an existing installation

Stop the stack and dashboard and back up the installation before upgrading v5.

- **Stable release.** Open **System Info**, choose **Check for updates**,
  and confirm the offered update. The CLI equivalent is `m4b update`.
- **Specific release or prerelease.** Run `m4b update --version X.Y.Z` with
  the desired release version.
- **Manual executable update.** Download the desired release,
  [verify the file](#verify-the-download-optional), and replace the executable
  in your installation directory. Keep the existing configuration and
  encryption key.

The binary updater requires a matching checksum and keeps the previous
executable beside the new one with a `.bak` suffix. Restart Money4Band after
an update and follow the [catalog refresh steps](app-management.md#removed-apps)
before restarting the stack.

If you are coming from v4, back up the v4 directory and install v5 in its own
directory. Use the v5 setup wizard to configure the apps you still use.

## First-Time Setup

Start Docker and choose **Setup Apps** in the menu, or run `m4b setup`.

1. Leave proxy use disabled for a direct connection. For one or more proxy
   endpoints, see [Proxy Setup](proxy-setup.md).
2. Select your apps and enter the credentials they request. See
   [provider onboarding](app-management.md#provider-onboarding) for apps with
   extra steps.
3. Finish setup to generate your Compose and environment files. Choose
   **Start apps stack** or run `m4b stack start`.

## Verifying Everything Works

Open the [dashboard](dashboard-api.md#starting-the-dashboard) or use `m4b status`
to check that the containers are running. Confirm enrollment and traffic in
each provider's dashboard. If setup or startup fails, see
[FAQ & Troubleshooting](faq.md).

## Next Steps

- [CLI Reference](cli-reference.md) - command reference
- [App Management](app-management.md) - enable / disable apps, community plugins
- [Proxy Setup](proxy-setup.md) - scale across multiple proxies
- [Dashboard & API](dashboard-api.md) - web UI for monitoring
- [Security](security.md) - how your credentials are protected
