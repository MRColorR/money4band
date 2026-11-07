# Money4Band

<!-- Project README scaffold: https://github.com/MRColorR/project-template -->

<img align="right" src="money4band/resources/assets/M4B_logo.png" width="96" alt="Money4Band logo">

[**⬇️ Download Money4Band**](https://github.com/MRColorR/money4band/releases/latest) · [🚀 Quick start](#quick-start) · [📋 Browse apps](#supported-apps) · [💬 Join Discord](https://discord.com/invite/Fq8eeazBAD) · [🫶 Support the project](#support)

**Leave a star ⭐ if you like this project 🙂 Thank you!**

<p align="center">
  <a href="https://github.com/MRColorR/money4band/releases/latest"><img src="https://img.shields.io/github/v/release/MRColorR/money4band?style=flat&label=Version" alt="Version"></a>
  <a href="https://github.com/MRColorR/money4band/actions/workflows/release-on-tag.yml"><img src="https://img.shields.io/github/actions/workflow/status/MRColorR/money4band/release-on-tag.yml?style=flat&label=Build" alt="Build"></a>
  <a href="https://github.com/MRColorR/money4band/blob/main/LICENSE"><img src="https://img.shields.io/github/license/MRColorR/money4band?style=flat&color=purple" alt="License"></a>
  <a href="https://discord.com/invite/Fq8eeazBAD"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black" alt="Linux">
  <img src="https://img.shields.io/badge/macOS-444444?style=flat-square&logo=apple&logoColor=white" alt="macOS">
</p>

<a name="what-is-money4band"></a>
<a name="overview"></a>

## 🔍 Overview

**Money4Band (M4B)** turns your unused internet bandwidth into passive income. That bandwidth is there anyway whether you're using it or not. Why not put it to work? One command. All the bandwidth-sharing apps. Each one runs in its own isolated Docker container, so your system stays clean, your setup is safer than installing each app natively, and you earn more than any single app could deliver alone.

Our maintainers and community **research** every app, **verify** its background, **track** payout history, and **monitor** real-world behavior over time. You don't have to figure out which apps are legit and which are a waste of time.

<a name="key-features"></a>

### ✨ Key Features

- **🧊 Multiplatform and lightweight Docker stack.** Run the apps you select on Windows, macOS, or Linux and set CPU and memory limits per app. Choose the [release asset for your OS and CPU](docs/getting-started.md#option-a---download-the-binary-recommended).
- **🔄 Automatic app updates.** Optionally enable Watchtower to keep eligible app images up to date. Check for Money4Band updates through **System Info** or `m4b update`.
- **📊 Web dashboard.** Monitor container health and resource usage, then start, stop, or restart apps from your browser. Providers show earnings and payouts in their own dashboards.
- **🌍 Multi-proxy support.** Start with your own connection or create separate instances from a proxy list for apps that permit proxies. Check your connection with `m4b ip`.
- **🔒 Safer than installing each app directly.** Each app runs in its own Docker container, keeping its dependencies separate and reducing what you install on your host.
- **🚀 Guided setup and automation.** Pick your apps and enter your credentials. Money4Band generates the Compose configuration, and you can automate app and stack management through the [CLI](docs/cli-reference.md) or [REST API](docs/dashboard-api.md).
- **🛟 Backups and notifications.** Money4Band encrypts saved app credentials, provides backup and restore commands, and can send stack notifications to Discord or Telegram.

Explore [optional community apps and add-ons](docs/app-management.md), including reward-claim helpers for select providers, when their terms permit them.

<a name="getting-started"></a>

## 🚥 Getting started

<a name="quick-start"></a>

### 🚀 Quick Start

Download Money4Band from the [latest stable release](https://github.com/MRColorR/money4band/releases/latest).
The [installation guide](docs/getting-started.md#option-a---download-the-binary-recommended)
shows which file to pick for Windows, macOS, or Linux and how to open it.

![First run in three steps: start Docker, choose Setup Apps, then choose Start apps stack.](docs/quick-start.svg)

1. **Start Docker.** See the [requirements and setup instructions](docs/getting-started.md#prerequisites) for your system.
2. **Open Money4Band and choose Setup Apps.** Pick apps from the [table below](#supported-apps), create provider accounts, and enter the account details or keys they ask for.
3. **Choose Start apps stack** to run the apps you selected. Check whether they started in the [web dashboard](docs/dashboard-api.md) or with the [status command](docs/cli-reference.md#status).

> [!TIP]
> For a first run, leave proxies off to use your usual internet connection. You can set up a proxy later for apps that permit it. See the [proxy setup guide](docs/proxy-setup.md).

Prefer a Git checkout? Follow [Run from Source](docs/getting-started.md#option-b---run-from-source).
Already installed? See [Upgrade an existing installation](docs/getting-started.md#upgrade-an-existing-installation).

<a name="supported-apps"></a>

### 📋 Supported Apps

Start with a **built-in app** and select its name to visit the provider. Some links are referrals that support Money4Band.

- **Built into Money4Band** · Available in **Setup Apps**.
- **Optional community catalog** · Enable the [community catalog](docs/app-management.md) to add it.
- **Standalone install** · Use the provider’s own installer.
- **Candidate** · Tracked for evaluation. See the [app directory](docs/APPS.md) for details.
- **Archived** · Listed for reference and historical purposes, removed from M4B setup as they shutted down or not deemed reliabe enough.

<!-- BEGIN:APPS_TABLE -->
| App | How to run it |
| --- | --- |
| [**AntGain**](https://antgain.app) | Built into Money4Band |
| [**Bitping**](https://app.bitping.com?r=qm7mIuX3) | Built into Money4Band |
| [**Earn.FM**](https://earn.fm/ref/MATTTAV6) | Built into Money4Band |
| [**GaGaNode**](https://www.gaganode.com) | Optional community catalog |
| [**Honeygain**](https://r.honeygain.me/MINDL15721) | Built into Money4Band |
| [**Mysterium**](https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9) | Built into Money4Band |
| [**PacketStream**](https://packetstream.io/?psr=3zSD) | Built into Money4Band |
| [**Pawns (IPRoyal)**](https://pawns.app?r=MiNe) | Built into Money4Band |
| [**ProxyLite**](https://proxylite.ru/?r=PJTKXWN3) | Built into Money4Band |
| [**Proxyrack Peer Program**](https://peer.proxyrack.com/ref/myoas6qttvhuvkzh8ffx90ns1ouhwgilfgamo5ex) | Built into Money4Band |
| [**Repocket**](https://link.repocket.co/hr8i) | Built into Money4Band |
| [**Spide Network**](https://spide.network) | Optional community catalog |
| [**Titan Network**](https://titannet.io) | Built into Money4Band |
| [**TraffMonetizer**](https://traffmonetizer.com/?aff=366499) | Built into Money4Band |
| [**URnetwork**](https://urnetwork.com) | Built into Money4Band |
| [**EarnApp**](https://earnapp.com/i/3zulx7k) | Standalone install |
| [**Adnade**](https://adnade.com) | Candidate (see app directory) |
| [**ByteBenefit**](https://bytebenefit.com) | Candidate (see app directory) |
| [**Bytelixir**](https://bytelixir.com) | Candidate (see app directory) |
| [**Earn.cc**](https://earn.cc) | Candidate (see app directory) |
| [**Ebesucher**](https://www.ebesucher.com) | Candidate (see app directory) |
| [**NetYield**](https://netyield.io/) | Candidate (see app directory) |
| [**PassiveApp**](https://passiveapp.io) | Candidate (see app directory) |
| [**Salad**](https://salad.com) | Candidate (see app directory) |
| [**UpRock**](https://uprock.com) | Candidate (see app directory) |
| **BearShare** | Archived |
| [**Dawn Internet**](https://dawninternet.com?code=xo23vynw) | Archived |
| [**Gradient**](https://app.gradient.network/signup?code=9WOBKP) | Archived |
| [**Grass (Wynd Network)**](https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f) | Archived |
| **PacketShare** | Archived |
| [**Peer2Profit**](https://t.me/peer2profit_app_bot?start=165849012262da8d0aa13c8) | Archived |
| [**ProxyBase**](http://peer.proxybase.org/signup?ref=XfOz3zeURm) | Archived |
| [**SpeedShare**](https://speedshare.app/?ref=mindlessnerd) | Archived |
| [**Teneo Protocol**](https://dashboard.teneo.pro/?code=qPgLn) | Archived |
| [**Wipter**](https://wipter.com/signup?ref=money4band) | Archived |
| [**WizardGain**](https://wizardgain.com) | Archived |
<!-- END:APPS_TABLE -->

This table follows the `main` branch. See the [app directory](docs/APPS.md) for IP eligibility, device limits, and payout methods.

---

<a name="proxy-providers"></a>

### 🌍 Proxy Providers

For apps that support and permit proxy use, choose a provider for your
[multi-proxy setup](docs/proxy-setup.md). Referral links support Money4Band
through a commission on qualifying purchases.

| Provider | Description |
| --- | --- |
| [BirdProxies](https://birdproxies.com/@money4band) | Static ISP and residential proxies for dedicated connections in your multi-proxy setup.<br>Bonus code: `MONEY4BAND` - 10% off. |

<a name="documentation"></a>

## 📚 Documentation

| | |
|---|---|
| [Getting Started](docs/getting-started.md) | [CLI Reference](docs/cli-reference.md) |
| [Dashboard & API](docs/dashboard-api.md) | [Proxy Setup](docs/proxy-setup.md) and [Proxy Providers](docs/proxy-setup.md#proxy-providers) |
| [App Management](docs/app-management.md) | [Configuration](docs/configuration.md) |
| [Security](docs/security.md) | [Notifications](docs/notifications.md) |
| [FAQ & Troubleshooting](docs/faq.md) | [App Directory](docs/APPS.md) |

---

<a name="faq"></a>

### ❓ FAQ

- [How do I update Money4Band?](docs/faq.md#how-do-i-update-m4b)
- [How do I troubleshoot setup or containers?](docs/faq.md#setup-issues)

<a name="community--support"></a>

### 💬 Community & Support

💬 Come say hello, share your setup, or ask for a hand. We’d love to hear how you use Money4Band.

- [**Discord**](https://discord.com/invite/Fq8eeazBAD) for chat, help, and shared experiences
- [**Discussions**](https://github.com/MRColorR/money4band/discussions) for feature requests and ideas
- [**Issues**](https://github.com/MRColorR/money4band/issues) for bug reports

<a name="contributing"></a>

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](.github/CONTRIBUTING.md) and [Code of Conduct](.github/CODE_OF_CONDUCT.md) before opening a pull request.

Please include enough context to reproduce a problem or review a change.

---

<a name="support"></a>

## 🫶 Support

**🫶 Support the project**

Your contributions are vital in helping to sustain the development of open-source projects and tools made freely available to everyone. If you find value in my work and wish to show your support, kindly consider making a donation.

☕ [Support me on Ko-fi](https://ko-fi.com/mrcolorrain) · 💛 [Donate with cryptocurrency](https://github.com/MRColorR/MRColorR/blob/main/SPONSORS.md#cryptocurrency-wallets)

Thank you for helping me keep building and sharing! 🙏 See the [supporters and sponsors directory](https://github.com/MRColorR/MRColorR/blob/main/SPONSORS.md).

---

<a name="license"></a>

## 📄 License

Money4Band is licensed under [GPL-3.0](LICENSE).

<a name="disclaimer"></a>

### ⚠️ Disclaimer

This project and its artifacts are provided "as is" and without warranty of any kind. The author makes no warranties, express or implied, that this script is free of errors, defects, or suitable for any particular purpose. The author shall not be retained liable for any damages suffered by any user of this script, whether direct, indirect, incidental, consequential, or special, arising from the use of or inability to use this script or its documentation, even if the author has been advised of the possibility of such damages. Always verify that the laws of your country and your ISP's terms allow these applications.
