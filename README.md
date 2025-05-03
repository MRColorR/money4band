# Money4Band

<img  src="./.resources/.assets/M4B_logo_small.png?raw=true"  width="96"> - **Leave a star ⭐ if you like this project 🙂 thank you.**

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/MRColorR/money4band/release-on-tag.yml?style=flat-square&link=https%3A%2F%2Fgithub.com%2FMRColorR%2Fmoney4band)

**|Easy automatic multi-app passive income project with Web Dashboard, Auto Updater, and Proxy Support :dollar::satisfied:|**

## 🔍 Quick Overview

**Money4Band (M4B)** leverages unused internet bandwidth, allowing you to make money with something you have and would otherwise be wasted. It utilizes containerized versions of apps like EarnApp, Honeygain, IPRoyal Pawns, PacketStream, Peer2Profit, Repocket, Earnfm, Proxyrack, Proxylite, Bitping, Grass, Packetshare, Gradient and more. It's also safer than installing and using these native apps on your host system. - all managed through a single tool with:

✨ **Key Features:**

- **🧊 Multiplatform and Lightweight** Docker stack.

- **🔄 Automatic Updates** to keep your applications up-to-date.

- **📊 Web Dashboard** for easy monitoring.

- **🌍 Multi-proxy support** for enhanced flexibility.

- **🔒 Safer than installing each app directly**: Runs in isolated containers, ensuring your host system remains unaffected.

🌐 For a detailed overview and FAQ join our [Discord Community](#-join-the-money4band-community-on-discord).

## 🚥 Getting Started

### 🛠️ Requirements

- 64-bit Operating System with Docker installed and running
> 💡**Note:** Turn on the `auto-start on system boot` in Docker settings to ensure the stack starts automatically when your system boots.

> 💡**Note:** For ARM devices like Raspberry Pi, installing an emulation layer for non-ARM native Docker images is recommended. Even though the script can assist with the installation, we recommend users install an emulation layer by themselves.

### ⬇️ Download and Run

You can run Money4Band in two simple ways:

#### Option 1: Run from source code 🔀

If you want to run the project from source code, you can do so by following these steps:

> ℹ️**Note:** This method requires Python 3.8 or higher.

1.  **Clone or download** the source code:

    - Option A: Use git

      - `git clone https://github.com/MRColorR/money4band.git && cd money4band`

    - Option B: download the ZIP and extract it using one of the options below
      - `wget https://github.com/MRColorR/money4band/archive/refs/heads/main.zip && unzip main.zip && cd money4band-main`
      - `Invoke-WebRequest -Uri https://github.com/MRColorR/money4band/archive/refs/heads/main.zip -OutFile main.zip; Expand-Archive -Path main.zip -DestinationPath .\ ; cd money4band*`

2.  **Install dependencies and run:** `pip install -r requirements.txt && python3 main.py`
    > 💡**Optional:** create a virtual environment to avoid affecting your system Python: `python3 -m venv venvm4b`
    > Remember to activate the virtual environment by using:
    > - (Linux/Mac): `source venvm4b/bin/activate`
    > - (Windows): `venvm4b\.Scripts\activate`

#### Option 2: Download a Pre-Built Release Artifact 📦

You can download a pre-built release artifact for your OS and run it directly without needing to clone the repository or install any dependencies.

1. Go to the [Releases Page](https://github.com/MRColorR/money4band/releases)
2. Download the latest release for your OS
3. Extract the downloaded release (.zip or .tar.gz) to a folder of your choice
4. Open the extracted folder and run the application:
   - **On Windows:** Run `money4band.exe`
   - **On Linux/macOS:** Run `./money4band`

> 💡**Note:** If you're using Windows and see a security warning from SmartScreen, click `"More info" → "Run anyway"` to proceed

> 💡**Note:** If you're using Linux and see a permission error, you may need to make the script executable by running `chmod +x money4band` in the terminal

### ⚙️ Setup and Configuration

Follow these steps to set up and configure your Money4Band instance:

1.  **Register** for accounts on the apps you want (see table below).

2.  **Launch M4B and follow the guided setup** to configure the apps.

3.  **Start the stack** after completing the setup.

4.  **Enjoy passive Earnings** monitoring your performance through the web dashboard.

## 📋 App Compatibility and Sign Up Links

Register an account on the app's sites clicking each apps' names in the following compatibility matrix

- :moneybag: Registering trough these links on the apps' sites, you should also receive a welcome bonus and at the same time you will effortlessly show that you appreciate my work, thank you so much :slightly_smiling_face:.

- :key: If you are using login with google, remember to set also a password for your app account!

|                                          App Name & Link                                          | Residential/Home/Mobile IP or equivalent Proxy's IP | VPS/Datacenter/Hosting/Cloud IP or equivalent Proxy's IP | Max devices per Account |
| :-----------------------------------------------------------------------------------------------: | :-------------------------------------------------: | :------------------------------------------------------: | :---------------------: |
|                          Go to [Earnapp](https://earnapp.com/i/3zulx7k)                           |                 :white_check_mark:                  |                           :x:                            |           15            |
|                       Go to [HoneyGain](https://r.honeygain.me/MINDL15721)                        |                 :white_check_mark:                  |                           :x:                            |           10            |
|                             Go to [IPROYAL](https://pawns.app?r=MiNe)                             |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|        Go to [PEER2PROFIT](https://t.me/peer2profit_app_bot?start=165849012262da8d0aa13c8)        |                 :white_check_mark:                  |                    :white_check_mark:                    |        Unlimited        |
|                      Go to [PACKETSTREAM](https://packetstream.io/?psr=3zSD)                      |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|                  Go to [TRAFFMONETIZER](https://traffmonetizer.com/?aff=366499)                   |                 :white_check_mark:                  |                    :white_check_mark:                    |        Unlimited        |
|                          Go to [REPOCKET](https://link.repocket.co/hr8i)                          |                 :white_check_mark:                  |                    :white_check_mark:                    |        Unlimited        |
|                           Go to [EARNFM](https://earn.fm/ref/MATTTAV6)                            |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|    Go to [PROXYRACK](https://peer.proxyrack.com/ref/myoas6qttvhuvkzh8ffx90ns1ouhwgilfgamo5ex)     |                 :white_check_mark:                  |                    :white_check_mark:                    |           500           |
|                        Go to [PROXYLITE](https://proxylite.ru/?r=PJTKXWN3)                        |                 :white_check_mark:                  |                    :white_check_mark:                    |        Unlimited        |
|                        Go to [BITPING](https://app.bitping.com?r=qm7mIuX3)                        |                 :white_check_mark:                  |                    :white_check_mark:                    |        Unlimited        |
|                   Go to [SPEEDSHARE](https://speedshare.app/?ref=mindlessnerd)                    |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|           Go to [GRASS](https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f)           |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|              Go to [PACKETSHARE](https://www.packetshare.io/?code=A260871CFD822E35)               |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
| Go to [GRADIENT](https://app.gradient.network/signup?code=9WOBKP) using code `9WOBKP` or `2WEG9X` |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|  Go to [MYSTNODE](https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9)   |                 :white_check_mark:                  |                    :white_check_mark:                    |        Unlimited        |
|            Go to [DAWN](https://dawninternet.com?code=xo23vynw) using code: `xo23vynw`            |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|            Go to [TENEO](https://dashboard.teneo.pro/?code=qPgLn) using code: `qPgLn`             |                 :white_check_mark:                  |                           :x:                            |        Unlimited        |
|                Go to [PROXYBASE](http://dash.proxybase.org/signup?ref=XfOz3zeURm)                 |                 :white_check_mark:                  |                    :white_check_mark:                    |        Unlimited        |

## 🌐 Scale Up with Multi-Proxy Support

**Money4Band** has the ability to create multiple instances also using a proxy list, ideal for scaling up your setup. Quickly set up numerous instances each linked to a different proxy with ease.

To run multiple instances using different proxies:

1.  **Prepare Proxies**: Create a `proxies.txt` file in the root folder of M4B, listing each proxy on a separate line and ending with a new line.
2.  **Start M4B and do the Setup**: During setup, answer yes when asked to enable multi-proxy.

> 💡**Note:** Proxy entries can be formatted in one of the following ways:
> - **With Authentication:** `protocol://proxyUsername:proxyPassword@proxy_url:proxy_port`
> - **Without Authentication:** `protocol://proxy_url:proxy_port`

> ⚠️**Note:** While using multiple proxies, be aware that only certain apps permit proxy usage per their Terms of Service. We recommend using personal, private proxies with IPs not flagged as proxies and always respecting the ToS of each app.

## 🧪 Compatibility and tested environments

This Docker Stack should work on anything that may have docker installed. In particular, it has been tested on:

|           | Windows 11 amd64/arm64 |     Linux Debian amd64/arm64     | MacOS amd64/arm64 |
| :-------: | :--------------------: | :------------------------------: | :---------------: |
|  Tested   |     :green_circle:     |          :green_circle:          |  :green_circle:   |
| on device |   Desktop/Laptop PC    | Desktop/Laptop PC / Raspberry Pi |    MacBook Pro    |

:green_circle:: All functions supported, Auto/manual setup supported

:yellow_circle:: All functions supported but not tested, Auto/manual setup supported

## ❓ Need Help or Found an Issue?

- For discussions, info, and feature requests, use the [Discussion tab](https://github.com/MRColorR/money4band/discussions) or join our [Discord Community](#-join-the-money4band-community-on-discord).

- F.A.Q., Alternative Manual Setup, How To Update, other useful guides and more details inside our [Discord Community](#-join-the-money4band-community-on-discord).

- For issues and bug reporting, use the [Issue tab](https://github.com/MRColorR/money4band/issues).

## 🚀 Join the Money4Band Community on Discord!

Join our Discord server! It's a space for you to share your experiences, ask questions, and discuss everything related to Money4Band and its related projects like custom docker images created for M4B and so on.

[Join the Money4Band Discord Community](https://discord.com/invite/Fq8eeazBAD)

## 🫶 Support the Projects

Your contributions are vital in helping to sustain the development of open-source projects and tools made freely available to everyone. If you find value in my work and wish to show your support, kindly consider making a donation:

### Cryptocurrency Wallets

- **Bitcoin (BTC):** `1EzBrKjKyXzxydSUNagAP8XLeRzBTxfHcg`
- **Ethereum (ETH):** `0xE65c32004b968cd1b4084bC3484C0dA051eeD3ee`
- **Solana (SOL):** `6kUAWW8q5169qnUJdxxLsNMPpaKPvbUSmryKDYTb9epn`
- **Polygon (MATIC):** `0xE65c32004b968cd1b4084bC3484C0dA051eeD3ee`
- **BNB (Binance Smart Chain):** `0xE65c32004b968cd1b4084bC3484C0dA051eeD3ee`

### Support via Other Platforms

- **Patreon:** [Support me on Patreon](https://patreon.com/mrcolorrain)
- **Buy Me a Coffee:** [Buy me a coffee](https://buymeacoffee.com/mrcolorrain)
- **Ko-fi:** [Support me on Ko-fi](https://ko-fi.com/mrcolorrain)

Your support, no matter how small, is enormously appreciated and directly fuels ongoing and future developments. Thank you for your generosity! 🙏

---

### :warning: Disclaimer

Always check that the laws of your country and the contractual terms of your internet plan allow the use of such applications. In any case, I do not take any responsibility for any consequences deriving from the use of such apps. This stack proposed by me simply brings these apps together, allows easy configuration even for the less experienced, and updates the apps' images automatically.

This project and its artifacts are provided "as is" and without warranty of any kind.

The author makes no warranties, express or implied, that this script is free of errors, defects, or suitable for any particular purpose.

The author shall not be held liable for any damages suffered by any user of this script, whether direct, indirect, incidental, consequential, or special, arising from the use of or inability to use this script or its documentation, even if the author has been advised of the possibility of such damages.

## :hash: License

[GPL 3.0](https://www.gnu.org/licenses/gpl-3.0.html)
