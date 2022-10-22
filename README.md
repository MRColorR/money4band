# Money4Band
A multiplatform self updating, lightweight docker stack that runs many passive income applications like Honeygain, EarnApp, IPRoyal Pawns, PacketStream, Peer2Profit, Bitping etc. that pay you in USD or in crypto to share your unused internet bandwidth. This docker stack makes it easier to set up and use those apps and it also includes an auto updater and web dasboard. You can also choose to use only some of the offered applications if that's what you want. All of them use a very small percentage of your unused internet bandwidth to perform searches such as Price Comparison, Brand Protection, Web Scraping, Ad Verification, QA Testing.  According to the creators of the various apps used here, all of these activities are safe and carried out only on behalf of verified customers who have passed their security standards such as companies and brands that have business relationships with them; So their use should be safe and risk-free.

This Docker Stack should work on anything that may have docker installed. In particular, it has been tested on: Windows 11 and Linux Ubuntu 64 Bit on x86_64 / amd64 PC, Linux Raspbian OS 64 bit on arm64 Raspberry Pi3 and Pi4.


### Prerequisites
- A 64-bit operating system is strongly recommended.
- Virtualization function in the BIOS must be active to use Docker.
- (Optional) To run on Windows, Virtualization platform and Windows Subsystem for Linux must be active as this two functions are required by Docker. If they're not already enabled, please enable them or use the built-in script to turn them on and install Docker.
- Docker must already be installed and able to run on startup. If it is not already installed you can follow the instructions for your platform at https://docs.docker.com/get-docker/ or use the built-in script to install it.
- (Optional) On arm devices (like Raspberry) to support also non-arm native docker images it is recommended to install an emulation layer with 
```bash
sudo docker run --privileged --rm tonistiigi/binfmt --install all
```
You can also make a service to run the emulation layer at system startup (this should be needed only on arm devices): To do so open a terminal in the folder containing the docker.binfmt.service file, then copy that file in /etc/systemmd/system and finally enable its service using the following commands:
```bash
sudo cp ${PWD}/docker.binfmt.service /etc/systemd/system
sudo systemctl enable docker.binfmt.service
sudo systemctl start docker.binfmt.service
```
## How to run (guided setup)
### 1) Get the latest version
Using your preferred method get the latest version of this project and unzip it.
For example you can download the zip of the project using the following command in a linux or windows terminal:
```bash
curl -o Money4Band.zip https://github.com/MRColorR/money4band/archive/refs/heads/main.zip
```
### 2) Register an account on the app's sites using the following links
Using the following referral links, register on the apps' sites. You should also receive a welcome bonus and at the same time you will effortlessly show that you appreciate my work (thank you so much).
- Go to [Earnapp](https://earnapp.com/i/3zulx7k)
- Go to [HoneyGain](https://r.honeygain.me/MINDL15721)
- Go to [IPROYAL](https://pawns.app?r=MiNe)
- Go to [PACKETSTREAM](https://packetstream.io/?psr=3zSD)
- Go to [PEER2PROFIT](https://p2pr.me/165849012262da8d0aa13c8)
- Go to [TRAFFMONETIZER](https://traffmonetizer.com/?aff=366499)
- Go to [BITPING](https://app.bitping.com?r=qm7mIuX3)

### 3) Complete the automatic guided setup using runme.sh (linux) or runme.ps1 (Windows/linux)
* On linux oper a terminal in the project folder or navigate to it then use the following commands to add execute permission and run the guided script to configure the .env file and then start the stack:
```bash
sudo chmod +x runme.sh
bash ./runme.sh
```


* (On Windows) Open a Powershell (as Administrator) in the project folder or navigate to it then use the following commands to set the execution policy and run the guided script to configure the .env file and then start the stack:
```pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force
.\runme.ps1
```

In any case, within the script menu there are many options dedicated to:
- Register for the various apps,
- Automatically install docker for the less experienced who cannot perform the recommended manual installation,
- Setup of the .env file,
- Application stack start helper,
- Tools to reset the configurations made in case of problems.

If you already have docker installed the only mandatory items you need to use are the env file setup entry and the start app stack entry of the menu.
### Enjoy your passive income

- Keep in mind if you have several ip, you can run a stack on each ip to increase revenue, but running several time this stack on same ip should not give you more. You can also install some of this apps on your smartphone and use also your mobile network to earn.  
- While the docker stack is running you can access the web dashboard navigating with your browser to http://localhost:8081/

## Need help or Found an issue/bug ? 
- For Info, Help and new features requesto use the [Discussion tab](https://github.com/MRColorR/money4band/discussions)
- For issues and bug report use the [Issue tab](https://github.com/MRColorR/money4band/issues)

---

## (Alternative) Manual setup

If you don't want to use the automatic setup scripts you can follow these alternative steps to do the manual setup.

### 3) Edit the .env file, adding where required the data to access the accounts you just created. You can find more detailed instructions directly inside the .env file
- Device_name : set any name you like
- Earnapp_Device_uuid: it must start with sdk-node- followed by an md5sum of a string of your choice
- HoneyGain _email and _password: just insert your account credentials
- Iproyalpawns _email and _password: just insert your account credentials
- Peer2profit_email: just enter your account email
- Packetstream_cid: enter the cid of your account. It's like a short token and you can find it in your packetstream's dashboard
- traffmonetizer_token: enter your token you can copy it from your traffmonetizer's dashboard
- (Optional) shoutrrr_url: you can choose to receive notifications about the updates performed on all the containers when a new version is pushed out from the app's developers. You can ignore this variable if you want to disable the notifications: to do so just comment the watchtower's notification parameters at the end of the docker-compose.yml file.

### 3.a) (Optional) Edit the docker-compose.yml file
- (Optional) If you don't want to use an app just comment or delete the corresponding section in docker-compose.yml.
- (Optional) Some apps have multiple configurations in the compose file to choose from (like the usage of docker volumes instead of volumes binding to folder). Comment on the ones you don't want to use. Obviously all this is optional since the default configuration is already sufficient to make everything work without the need for modifications.
### 4) First Startup
- 4.a) (For BitPing) This step is not needed if bitping is not used. Bitping needs to be started at least once in interactive mode for the first connection: before running the entire stack with all the apps. You can configure the bitping data opening a terminal and using the following command in the folder where you have already put the .env and docker-compose.yml files: 
```bash
sudo docker run --rm -it -v ${PWD}/.data/.bitping/:/root/.bitping bitping/bitping-node:latest
```
This will create a subfolder containing all the necessary data, then enter your credential when prompted. 
Once this is done, use CTRL+C to stop the container and then proceed to the standard startup as shown in 4.b).
- 4.b) Start all the apps just opening a terminal in the same folder where the .env and docker-compose.yml files are placed and using the command below:
```bash
sudo docker compose up -d
```
After a few minutes you should be able to see the device in the dashboards of the various apps as active, connected and earning.
- 4.c) (For EarnApp) This step is not needed if EarnApp is not used. For EarnApp after the first start-up phase it is necessary to claim your device in your account. To do so just go to the earnapp dashboard and then register it by copying the node_UUID previously saved in the .env file in this URL prototype (https://earnapp.com/r/<your_device_uuid>) and then copy the resulting real URL into your web browser. Your url should look like this: https://earnapp.com/r/sdk-node-dtrbf9f1437a4287947fd58b5ka4d7. Navigating to your url should register your node in your dashboard. 

### Enjoy your passive income
- Keep in mind if you have several ip, you can run a stack on each ip to increase revenue, but running several time this stack on same ip should not give you more. You can also install some of this apps on your smartphone and use also your mobile network to earn.  
- While the docker stack is running you can acess the web dashboard navigating with your browser to http://localhost:8081/

### Disclaimer
Always check that the laws of your country and the contractual terms of your internet plan allow the use of such applications. In any case, I do not take any responsibility for any consequences deriving from the use of such apps. This stack proposed by me simply brings them together, allows easy configuration even for the less experienced and updates the apps' images automatically. 

## License
[GNU](https://www.gnu.org/licenses/gpl-3.0.html)
