# Getting Started

> From zero to passive income in under five minutes.

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | Windows 10+, macOS 12+, Linux (Debian/Ubuntu) | WSL2 supported on Windows |
| Docker | Docker Engine 20.10+ or Docker Desktop | `m4b setup` can install it for you |
| Python | 3.10+ | Only needed when running from source |

## Option A - Download the Binary (Recommended)

1. Go to **[Releases](https://github.com/MRColorR/money4band/releases/latest)** and
   download the asset for your platform:

   | Platform | Asset |
   |----------|-------|
   | Windows amd64 | `Money4Band-windows-amd64.exe` |
   | Linux amd64 | `Money4Band-linux-amd64` |
   | Linux arm64 | `Money4Band-linux-arm64` |
   | Linux armv7 | `Money4Band-linux-armv7` |
   | macOS arm64 (Apple Silicon) | `Money4Band-macos-arm64` |
   | macOS amd64 (Intel) | `Money4Band-macos-amd64` |

   Check your architecture with `uname -m` (`x86_64` = amd64, `aarch64` = arm64,
   `armv7l` = armv7). On Windows: **Settings > System > About > System type**.

2. Put it in its own directory. First run creates `config/`, `template/` and
   `.m4b/` next to the executable.

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

Running the binary with no arguments opens the interactive menu, which covers
everything. The `m4b <command>` form in these docs is the CLI surface, for
scripting and one-shot actions:

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

The third surface is the REST API, started with `dashboard start` and documented
in [Dashboard & API](dashboard-api.md). All three expose the same capabilities.

### Verify the download (optional)

Every release publishes `checksums.sha256`. Download it alongside the binary:

```bash
sha256sum -c checksums.sha256 --ignore-missing        # Linux
shasum -a 256 -c checksums.sha256 --ignore-missing    # macOS
```

```powershell
# compare the output against the matching line in checksums.sha256
Get-FileHash .\Money4Band-windows-amd64.exe -Algorithm SHA256
```

`m4b update` verifies against the same file on every self-update.

The interactive menu takes over from here.

## Option B - Run from Source

```bash
git clone https://github.com/MRColorR/money4band.git
cd money4band

# Using uv (recommended)
uv sync
uv run python main.py

# Or using pip
pip install -r requirements.txt
python main.py
```

## First-Time Setup

When you launch M4B for the first time, choose **Setup Apps** from the menu (or run `m4b setup`):

1. **Docker check** - M4B verifies Docker is installed. If not, it offers to install it.
2. **App selection** - Pick the apps you want to run. Each app shows its IP policy (residential / datacenter / universal) and payout info.
3. **Credentials** - Enter the credentials required by each selected app (email, token, etc.). Credentials are encrypted with Fernet (AES-128-CBC) and stored in `config/user-config.json`.
4. **Generation** - M4B generates your `docker-compose.yaml` and `.env` file.
5. **Start** - Launch the stack with `m4b stack start` or choose **Start Stack** from the menu.

## Verifying Everything Works

```bash
# Check container status
m4b status

# View IP quality score (important for earnings)
m4b ip

# Open the web dashboard (optional)
m4b dashboard start
```

## Next Steps

- [CLI Reference](cli-reference.md) - all 24 subcommands
- [App Management](app-management.md) - enable / disable apps, community plugins
- [Proxy Setup](proxy-setup.md) - scale across multiple proxies
- [Dashboard & API](dashboard-api.md) - web UI for monitoring
- [Security](security.md) - how your credentials are protected
