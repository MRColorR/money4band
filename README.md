<p align="center">
  <img src="money4band/resources/assets/M4B_logo.png" width="128" alt="Money4Band Logo">
</p>

<h1 align="center">Money4Band</h1>

<h3 align="center">Run bandwidth-sharing apps with Docker Compose.</h3>

<p align="center">
  <a href="https://github.com/MRColorR/money4band/releases/latest"><img src="https://img.shields.io/github/v/release/MRColorR/money4band?style=flat&label=Version" alt="Version"></a>
  <a href="https://github.com/MRColorR/money4band/actions/workflows/release-on-tag.yml"><img src="https://img.shields.io/github/actions/workflow/status/MRColorR/money4band/release-on-tag.yml?style=flat&label=Build" alt="Build"></a>
  <a href="https://github.com/MRColorR/money4band/stargazers"><img src="https://img.shields.io/github/stars/MRColorR/money4band?style=flat&logo=github&color=orange" alt="Stars"></a>
  <a href="https://github.com/MRColorR/money4band/blob/main/LICENSE"><img src="https://img.shields.io/github/license/MRColorR/money4band?style=flat&color=purple" alt="License"></a>
  <a href="https://discord.com/invite/Fq8eeazBAD"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black" alt="Linux">
  <img src="https://img.shields.io/badge/macOS-444444?style=flat-square&logo=apple&logoColor=white" alt="macOS">
</p>

## What is Money4Band?

Money4Band (M4B) is an open-source manager for bandwidth-sharing apps such as
Honeygain, Pawns, PacketStream, and Repocket. Choose the apps you want, enter
their provider credentials, and run them together in Docker Compose.

- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Supported Apps](#supported-apps)
- [Documentation](#documentation)
- [FAQ](#faq)
- [Community & Support](#community--support)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

1. Start Docker. Check the [platform requirements](docs/getting-started.md#prerequisites).
2. Download the executable for your platform from the
   [latest stable release](https://github.com/MRColorR/money4band/releases/latest),
   or pick a prerelease from [all releases](https://github.com/MRColorR/money4band/releases).
   Follow the [platform-specific launch steps](docs/getting-started.md#option-a---download-the-binary-recommended).
3. Open **Setup Apps**, select your apps, and provide the requested credentials.
   Leave proxies off for a direct connection, or follow the [proxy setup guide](docs/proxy-setup.md).
4. Choose **Start Stack**, then check the containers in the dashboard or with
   the [status command](docs/cli-reference.md#status).

Prefer a Git checkout? Follow [Run from Source](docs/getting-started.md#option-b---run-from-source).
Already installed? See [Upgrade an existing installation](docs/getting-started.md#upgrade-an-existing-installation).

## Key Features

- Guided setup, scriptable CLI, and a web dashboard with a REST API
- Direct, single-proxy, and multi-proxy Docker Compose stacks
- Encrypted saved credentials, configuration profiles, and backup and restore
- Optional app image updates with Watchtower, plus a separate Money4Band updater
- Per-app resource limits, notifications, and opt-in community catalogs

## Supported Apps

The table covers the built-in catalog on this branch. See the [app directory](docs/APPS.md)
for details and the [community catalog](https://github.com/MRColorR/money4band-community-catalog)
for opt-in entries.

> [ok] Built in. [x] Removed from default setup.
>
> Some app links below include referral codes that support the project.

<!-- BEGIN:APPS_TABLE -->
| Type | App | Residential | VPS/DC | Payout |
|:----:|-----|:-----------:|:------:|--------|
| [ok] | [**AntGain**](https://antgain.app) | [ok] | - | - |
| [ok] | [**Bitping**](https://app.bitping.com?r=qm7mIuX3) | [ok] | [ok] | BITPING token (crypto), USDC |
| [ok] | [**Earn.FM**](https://earn.fm/ref/MATTTAV6) | [ok] | [ok] | PayPal, USDT, gift cards |
| [ok] | [**Honeygain**](https://r.honeygain.me/MINDL15721) | [ok] | [x] | JumpToken (crypto), PayPal (via JumpTask) |
| [ok] | [**Mysterium**](https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9) | [ok] | [ok] | MYST token, ETH, BNB |
| [ok] | [**PacketStream**](https://packetstream.io/?psr=3zSD) | [ok] | [x] | PayPal |
| [ok] | [**Pawns (IPRoyal)**](https://pawns.app?r=MiNe) | [ok] | [x] | PayPal, crypto, gift cards |
| [ok] | [**ProxyLite**](https://proxylite.ru/?r=PJTKXWN3) | [ok] | [ok] | crypto |
| [ok] | [**Proxyrack Peer Program**](https://peer.proxyrack.com/ref/myoas6qttvhuvkzh8ffx90ns1ouhwgilfgamo5ex) | [ok] | [ok] | PayPal, crypto |
| [ok] | [**Repocket**](https://link.repocket.co/hr8i) | [ok] | [ok] | PayPal, crypto |
| [ok] | [**Titan Network**](https://titannet.io) | [ok] | - | - |
| [ok] | [**TraffMonetizer**](https://traffmonetizer.com/?aff=366499) | [ok] | [x] | PayPal, crypto, wire transfer |
| [ok] | [**URnetwork**](https://urnetwork.com) | [ok] | - | - |
| [x] | **BearShare** | [ok] | - | - |
| [x] | **PacketShare** | [ok] | - | - |
<!-- END:APPS_TABLE -->

> **[Registration links, IP eligibility, and payout methods](docs/APPS.md)**

### Apps you install yourself

Run EarnApp directly on an eligible personal device using the provider's
installer. See the [standalone apps list](docs/APPS.md#standalone-apps).

---

## Documentation

| | |
|---|---|
| [Getting Started](docs/getting-started.md) | [CLI Reference](docs/cli-reference.md) |
| [Dashboard & API](docs/dashboard-api.md) | [Proxy & Multi-Proxy](docs/proxy-setup.md) |
| [App Management](docs/app-management.md) | [Configuration](docs/configuration.md) |
| [Security](docs/security.md) | [Notifications](docs/notifications.md) |
| [FAQ & Troubleshooting](docs/faq.md) | [App Directory](docs/APPS.md) |

---

## FAQ

- [Why is EarnApp missing from setup?](docs/faq.md#why-is-earnapp-missing-from-setup)
- [How do I update Money4Band?](docs/faq.md#how-do-i-update-m4b)
- [How do I troubleshoot setup or containers?](docs/faq.md#setup-issues)

## Community & Support

- [**Discord**](https://discord.com/invite/Fq8eeazBAD) for chat, help, and shared experiences
- [**Discussions**](https://github.com/MRColorR/money4band/discussions) for feature requests and ideas
- [**Issues**](https://github.com/MRColorR/money4band/issues) for bug reports

## Contributing

Contributions are welcome! Please read the [Contributing Guide](.github/CONTRIBUTING.md) and [Code of Conduct](.github/CODE_OF_CONDUCT.md) before opening a pull request.

---

## Support

Ko-fi supports Mattia / MrColorRain's work across projects.

Support ongoing development, testing and documentation through
[Ko-fi](https://ko-fi.com/mrcolorrain). One-time contributions and monthly
memberships are welcome, and you can pledge above a tier's minimum.
Technical decisions remain independent.

See the [supporters and sponsors directory](https://github.com/MRColorR/MRColorR/blob/main/SPONSORS.md)
for acknowledgments.

---

## Stargazers

[![Stargazers over time](https://starchart.cc/MRColorR/money4band.svg?variant=adaptive)](https://starchart.cc/MRColorR/money4band)

---

## License

Money4Band is licensed under [GPL-3.0](LICENSE).

## [!] Disclaimer

This project and its artifacts are provided "as is" and without warranty of any kind. The author makes no warranties, express or implied, that this script is free of errors, defects, or suitable for any particular purpose. The author shall not be retained liable for any damages suffered by any user of this script, whether direct, indirect, incidental, consequential, or special, arising from the use of or inability to use this script or its documentation, even if the author has been advised of the possibility of such damages. Always verify that the laws of your country and your ISP's terms allow these applications.
