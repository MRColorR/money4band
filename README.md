# Money4Band 
<img src="./.resources/.assets/M4B_logo_small.png?raw=true" width="96"> - **Leave a star ⭐ if you like this project 🙂 thank you.**

**|Easy automatic multi app passive income project with Webdasboard, Auto Updater and Proxy Support :dollar::satisfied::+1:|**

## Quick Overview 🚀
**Money4Band** leverages unused internet bandwidth allowing you to make money with something you have and would otherwise be wasted.** It utilizes containerized version of apps like EarnApp, Honeygain, IPRoyal Pawns, PacketStream, Peer2Profit, Repocket, Earnfm, Proxyrack, Proxylite, Bitping and so on but it's also safer than installing and using these native apps on your host system.

✨ **Key Features:**
- **Multiplatform** and lightweight docker stack.
- **Automatic Updates** to keep your applications up-to-date.
- **Web Dashboard** for easy monitoring.
- **Proxy Support** for enhanced flexibility.

🌐 For a detailed overview and FAQ, visit the [Wiki](https://github.com/MRColorR/money4band/wiki) or join our [Discord Community](#-join-the-money4band-community-on-discord).

## Getting Started 🚥
### Prerequisites
- Ensure that you have a 64-bit operating system, virtualization functions are enabled and Docker is installed and able to auto start up on system boot.
- (Optional) For ARM devices like Raspberry Pi, installing an emulation layer for non-ARM native Docker images is recommended. Even though the script can assist with the installation, we recommend users to install an emulation layer by themselves following the [Wiki](https://github.com/MRColorR/money4band/wiki) guide.
- (Optional) On Windows, ensure the Virtualization platform and Windows Subsystem for Linux are active as Docker requires these features. Even though the script can assist with the installation, we recommend users to enable these windows functions by themselves following the [Wiki](https://github.com/MRColorR/money4band/wiki) guide.



### Quick Setup Guide
1. **Download** the latest version of Money4Band from the [Releases](https://github.com/MRColorR/money4band/releases) or git clone the project.
   - OR you can also use on Linux/MacOS a bash command like: `wget https://github.com/MRColorR/money4band/archive/refs/heads/main.zip && unzip main.zip`
   - OR on Windows use a pwsh command like:`Invoke-WebRequest -Uri https://github.com/MRColorR/money4band/archive/refs/heads/main.zip -OutFile main.zip; Expand-Archive -Path main.zip -DestinationPath .\ `
3. **Register** accounts on the application websites. [Here's a list of availabe apps](#app-compatibility-and-sign-up-links-)
4. **Run** the guided setup:
   - **Linux:** 
     ```bash
     sudo chmod +x runme.sh && ./runme.sh 
     ```
   - **Windows:**
     ```powershell
     Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass -Force; .\runme.ps1 
     ```
5. **Start Earning** passively and monitor your performance through the web dashboard.

## App Compatibility and Sign Up Links 📋
Register an account on the app's sites clicking each apps' names in the following compatibility matrix

- :moneybag: Registering trough these links on the apps' sites, you should also receive a welcome bonus and at the same time you will effortlessly show that you appreciate my work, thank you so much 	:slightly_smiling_face:.

- :key: If you are using login with google, remember to set also a password for your app account!

| App Name & Link | Residential/Home/Mobile IP or equivalent Proxy's IP | VPS/Datacenter/Hosting/Cloud IP or equivalent Proxy's IP | Max devices per Account | Max Devices per IP | 
|  :--- |  :---: |  :---: | :---: | :---: |
| Go to [Earnapp](https://earnapp.com/i/3zulx7k)  | :white_check_mark:	  | :x: | 15|1|
| Go to [HoneyGain](https://r.honeygain.me/MINDL15721) | :white_check_mark:	  | :x: |10|1|
| Go to [IPROYAL](https://pawns.app?r=MiNe)  | :white_check_mark:	  | :x: |Unlimited|1|
| Go to [PEER2PROFIT](https://t.me/peer2profit_app_bot?start=165849012262da8d0aa13c8)  | :white_check_mark:	  | :white_check_mark:	 | Unlimited|Unlimited|
| Go to [PACKETSTREAM](https://packetstream.io/?psr=3zSD)  | :white_check_mark:	  | :x: |Unlimited|1|
| Go to [TRAFFMONETIZER](https://traffmonetizer.com/?aff=366499) | :white_check_mark:	  | :white_check_mark: |Unlimited|Unlimited|
| Go to [REPOCKET](https://link.repocket.co/hr8i)  | :white_check_mark:	  | :white_check_mark: |Unlimited|2|
| Go to [EARNFM](https://earn.fm/ref/MATTTAV6)  | :white_check_mark:	  | :x: |Unlimited|1|
| Go to [PROXYRACK](https://peer.proxyrack.com/ref/myoas6qttvhuvkzh8ffx90ns1ouhwgilfgamo5ex)  | :white_check_mark:	  | :white_check_mark: |500|1|
| Go to [PROXYLITE](https://proxylite.ru/?r=PJTKXWN3) | :white_check_mark:	  | :white_check_mark: |Unlimited|1|
| Go to [BITPING](https://app.bitping.com?r=qm7mIuX3) | :white_check_mark:	  | :white_check_mark: |Unlimited|1|
| Go to [MYSTNODE](https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9) | :white_check_mark:	  | :white_check_mark: |Unlimited|Unlimited|

## Compatibility and tested environments
This Docker Stack should work on anything that may have docker installed. In particular, it has been tested on: 
| | Windows 11 x86_64\amd64 | Linux Ubuntu x86_64\amd64 | Raspbian OS arm64 | MacOS Intel x86_64 | MacOS silicon arm64 | 
|  :---: |  :---: |  :---: |  :---: | :---: | :---: |
| Tested | :green_circle: | :green_circle: | :green_circle: | :yellow_circle: | :yellow_circle:|
| on device | Desktop/Laptop PC | Desktop/Laptop PC | Raspberry Pi3/Pi4 | _not tested_ | _not tested_ |

:green_circle:: All functions supported, Auto/manual setup supported
:yellow_circle:: All functions supported but not tested, Auto/manual setup supported


## Need Help or Found an Issue? ❓
- For discussions, info, and feature requests, use the [Discussion tab](https://github.com/MRColorR/money4band/discussions) or join our [Discord Community](#-join-the-money4band-community-on-discord).
- F.A.Q., Alternatve Manual Setup, How To Update, other useful guides and more details inside the [Wiki](https://github.com/MRColorR/money4band/wiki)

- For issues and bug reporting, use the [Issue tab](https://github.com/MRColorR/money4band/issues).

## 🚀 Join the Money4Band Community on Discord! 
We've launched a Discord server! It's a space for you to share your experiences, ask questions, and discuss everything related to Money4Band and its related projects like custom docker images created for M4B and so on. 
[Join the Money4Band Discord Community](https://discord.com/invite/Fq8eeazBAD)

---
### :warning: Disclaimer
Always check that the laws of your country and the contractual terms of your internet plan allow the use of such applications. In any case, I do not take any responsibility for any consequences deriving from the use of such apps. This stack proposed by me simply brings these apps together, allows easy configuration even for the less experienced and updates the apps' images automatically. 
This project and its artifacts are provided "as is" and without warranty of any kind. 
The author makes no warranties, express or implied, that this script is free of errors, defects, or suitable for any particular purpose.  
The author shall not be retained liable for any damages suffered by any user of this script, whether direct, indirect, incidental, consequential, or special, arising from the use of or inability to use this script or its documentation, even if the author has been advised of the possibility of such damages.  

## :hash: License
[GPL 3.0](https://www.gnu.org/licenses/gpl-3.0.html)
