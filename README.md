# Money4Band
<img src="./.resources/.assets/M4B_logo_small.png?raw=true" width="96"> - Leave a star ⭐ if you like this project 🙂 thank you.

Money4Band Leverages unused internet bandwidth allowing you to make money with something you have and would otherwise be wasted. It use containerized version of apps like EarnApp, Honeygain, IPRoyal Pawns, PacketStream, Peer2Profit, Repocket, Proxyrack, Bitping and so on but it's safer than installing and using these native apps on your host system. More info and FAQ in the [Wiki](https://github.com/MRColorR/money4band/wiki).

- This is a multiplatform, self updating, lightweight docker stack that runs many passive income applications that pay you in USD or in crypto to share your unused internet bandwidth. This docker stack makes it easier to set up and use those apps and it also includes an auto updater, notification system and web dashboard.

- This is a set and forget project, just follow the automatic setup steps and start earning something doing nothing.

This Docker Stack should work on anything that may have docker installed [Windows, Linux, Mac, Raspberry and so on]. In particular, it has been tested on: Windows 11 and Linux Ubuntu 64 Bit on x86_64 / amd64 PC, Linux Raspbian OS 64 bit on arm64 Raspberry Pi3 and Pi4.

### Prerequisites
- A 64-bit operating system is strongly recommended.
- Virtualization function in the BIOS must be active to use Docker.
- (Optional) To run on Windows, Virtualization platform and Windows Subsystem for Linux must be active as this two functions are required by Docker. If they're not already enabled, please enable them or use the built-in script to turn them on and install Docker.
- Docker must already be installed and able to run on startup. If it is not already installed you can follow the instructions for your platform at https://docs.docker.com/get-docker/ or use the built-in script to install it.
- (Optional) On arm devices (such as Raspberry) to support non-arm native docker images it is strongly recommended to install an emulation layer and set it as a service to start automatically: to do this, you can follow the steps explained in the [Wiki](https://github.com/MRColorR/money4band/wiki) prerequisites page.
## How to run (guided setup)
### 1) Get the latest version
Using your preferred method get the latest version of this project and unzip it.
For example you can go to the [Releases](https://github.com/MRColorR/money4band/releases) to download the latest version.
### 2) Register an account on the app's sites clicking each apps' names in the following compatibility matrix

:moneybag: Registering trough these links on the apps' sites, you should also receive a welcome bonus and at the same time you will effortlessly show that you appreciate my work (thank you so much).

:information_source: If you are using login with google, remember to set also a password for your app account!

| App Name & Link | Residential/Home/Mobile IP or equivalent Proxy's IP | Datacenter/Hosting/VPS/Cloud IP or equivalent Proxy's IP | Max devices per Account | Max Devices per IP | 
|  :--- |  :---: |  :---: | :---: | :---: |
| Go to [Earnapp](https://earnapp.com/i/3zulx7k)  | :white_check_mark:	  | :x: | 15|1|
| Go to [HoneyGain](https://r.honeygain.me/MINDL15721) | :white_check_mark:	  | :x: |10|1|
| Go to [IPROYAL](https://pawns.app?r=MiNe)  | :white_check_mark:	  | :x: |Unlimited|1|
| Go to [PACKETSTREAM](https://packetstream.io/?psr=3zSD)  | :white_check_mark:	  | :x: |Unlimited|1|
| Go to [PEER2PROFIT](https://p2pr.me/165849012262da8d0aa13c8)  | :white_check_mark:	  | :white_check_mark:	 | Unlimited|Unlimited|
| Go to [TRAFFMONETIZER](https://traffmonetizer.com/?aff=366499) | :white_check_mark:	  | :white_check_mark: |Unlimited|Unlimited|
| Go to [REPOCKET](https://link.repocket.co/hr8i)  | :white_check_mark:	  | :white_check_mark: |Unlimited|2|
| Go to [PROXYRACK](https://peer.proxyrack.com/ref/myoas6qttvhuvkzh8ffx90ns1ouhwgilfgamo5ex)  | :white_check_mark:	  | :white_check_mark: |500|1|
| Go to [PROXYLITE](https://proxylite.ru/?r=PJTKXWN3) | :white_check_mark:	  | :white_check_mark: |Unlimited|1|
| Go to [BITPING](https://app.bitping.com?r=qm7mIuX3) | :white_check_mark:	  | :white_check_mark: |Unlimited|1|

### 3) Complete the automatic guided setup using runme.sh (linux) or runme.ps1 (Windows/linux)
* (On linux) open a terminal in the project folder or navigate to it then use the following commands to add execute permission and run the guided script to configure the .env file and then start the stack:
```bash
sudo chmod +x runme.sh
bash ./runme.sh
```

* (On Windows) Open a Powershell (as Administrator) in the project folder or navigate to it then use the following commands to set the execution policy and run the guided script to configure the .env file and then start the stack:
```pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force
.\runme.ps1
```

Within the script menu there are many options dedicated to:
- Register for the various apps,
- Automatically install docker for the less experienced who cannot perform the manual installation,
- Setup of the .env file,
- Application stack start/stop helper,
- Tools to reset the configurations made in case of problems.

If you already have docker installed the only mandatory items you need to use are the env file setup entry and the start app stack entry of the menu.

### 4) Enjoy your passive income

- Keep in mind if you have several ip, you can run a stack on each ip to increase revenue, but running several time this stack on same ip should not give you more. You can also install some of this apps on your smartphone and use also your mobile network to earn.  
- While the docker stack is running you can access the web dashboard navigating with your browser to http://localhost:8081/

## Wiki (F.A.Q., Alternatve Manual Setup, How To Update,...)

* Go to the [Wiki](https://github.com/MRColorR/money4band/wiki) to find F.A.Q., Alternatve Manual Setup, How To Update, other useful guides and more details.



## Need help or Found an issue/bug ? 
- For Info, Help and new features requesto use the [Discussion tab](https://github.com/MRColorR/money4band/discussions)
- For issues and bug report use the [Issue tab](https://github.com/MRColorR/money4band/issues)

---

### Disclaimer
Always check that the laws of your country and the contractual terms of your internet plan allow the use of such applications. In any case, I do not take any responsibility for any consequences deriving from the use of such apps. This stack proposed by me simply brings them together, allows easy configuration even for the less experienced and updates the apps' images automatically. 

## License
[GNU](https://www.gnu.org/licenses/gpl-3.0.html)
