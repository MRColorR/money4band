# Money4Band
A multi platform, self updating, lightweight docker stack that run many passive income applications like Honeygain, EarnApp, IPRoyal Pawns, PacketStream, Peer2Profit, Bitping etc that pay you in USD or in crypto to share your unused internet bandwidth. This docker stack makes it easier to set up and use those apps and it also includes an auto updater and web GUI. You can also choose to use only some of the offered applications if that's what you want. All of them use a very small percentage of your unused internet bandwidth to perform searches such as Price Comparison, Brand Protection, Web Scraping, Ad Verification, QA Testing. According to the creators of the various apps used here, all of these activities are safe and carried out only on behalf of verified customers who have passed their security standards such as companies and brands that have business relationships with them; So their use should be safe and risk-free.

This Docker Stack should work on anything that may have docker installed. In particular it has been tested on: Windows 11 and Linux Ubuntu 64 Bit on x86_64 / amd64 PC, Linux Raspbian OS 64bit on arm64 Raspberry Pi3 and Pi4.


## How to run
### Prerequisites
- A 64-bit operating system is strongly recommended.
- Docker must already be installed and able to run on startup. If it is not already installed you can follow the instructions for your platform at https://docs.docker.com/get-docker/
- (optional) On arm devices (like Raspberry) to support also non-arm native docker images it is recommended to install an emulation layer with 
```bash
sudo docker run --privileged --rm tonistiigi/binfmt --install all
```
you can also make a service to run the emulation layer at system startup.
### 1) Get the latest version
Usign your preferred method get the latest version of this project and place it in a new folder
### 2) Register an account on the app's sites using the following links
Using the following referral links, register on the apps' sites. You should also receive a welcome bonus and at the same time you will effortessly show that you appreciate my work (thank you so much).
- Go to [Earnapp](https://earnapp.com/i/3zulx7k)
- Go to [HoneyGain](https://r.honeygain.me/MINDL15721)
- Go to [IPROYAL](https://pawns.app?r=MiNe)
- Go to [PACKETSTREAM](https://packetstream.io/?psr=3zSD)
- Go to [PEER2PROFIT](https://p2pr.me/165849012262da8d0aa13c8)
- Go to [TRAFFMONETIZER](https://traffmonetizer.com/?aff=366499)
- Go to [BITPING](https://app.bitping.com?r=qm7mIuX3)

### 3) Edit the .env file adding where required the data to access the accounts you just created. You can find more detailed instructions directly inside the .env file.
- Device_name : set any name you like
- Earnapp_Device_uuid: it must start with sdk-node- followed by an md5sum of a string of your choice
- Honeygain _email and _password: just insert your account credentials
- iproyalpawns _email and _password: just insert your account credentials
- peer2profit_email: just enter your account email
- packetstream_cid: enter the cid of your account. It's like a short token and you can find it in your packetstream's dashboard
- traffmonetizer_token: enter your token you can copy it from your traffmonetizer's dashboard
-(optional) shoutrrr_url: you can choose to recieve notifications about the updates performed on all the containers when a new version is pushed out from the app developers. You can ignore this variable if you want to disable the notifications (to do so just comment the notification at the end of the docker-compose.yml file, more details below)

### 3.a) (Optional) Edit the docker-compose.yml file
- (Optional) If you don't want to use an app just comment or delete the corresponding section in docker-compose.yml.
- (Optional) Some apps have multiple configurations in the compose file to choose from (like the usage of docker volumes instead of volumes binding to folder). Comment on the ones you don't want to use. Obviously all this is optional since the default configuration is already sufficient to make everything work without the need for modifications.
### 4) First Startup
- 4.a) (not needed if bitping is not used) Bitping needs to be started at least once in interactive mode for the first connection: before running the entire stack whit all the apps you can configure the bitping data opening a terminal end using the following command in the folder where you have already put the .env and docker-compose.yml files: 
```bash
sudo docker run --rm -it -v ${PWD}/.data/.bitping/:/root/.bitping bitping/bitping-node:latest
```
this will create a subfolder containing all the necessary data, then enter your credential when prompted. 
Once this is done use CTRL+C to end the container and then proceed to the standard startup.
- 4.b) Start all the apps just opening a terminal in the same folder where the .env and docker-compose.yml files are placed and using the command below:
```bash
sudo docker compose up -d
```
After a few minutes you should be able to see the device in the dashboards of the various apps of your active and connected that is earning.
- 4.c) (not necessary if you do not use earnapp) for EarnApp after the first start-up phase it is necessary to claim the node in your account. To do so just go to the earnapp dashboard and then register the node by copying the node_UUID previously saved in the .env file in this URL prototype (https://earnapp.com/r/<your_device_uuid>) and then copy the resulting real URL into your web browser. Your url should look like this: https://earnapp.com/r/sdk-node-dtrbf9f1437a4287947fd58b5ka4d7. Navigating to your url should register your node in your dashboard (this is a one time process). 

### Enyoy your passive income

### Disclaimer
Always check that the laws of your country and the contractual conditions of your internet plan allow the use of such applications. In any case, I do not take any responsibility for any consequences deriving from the use of such apps. This stack proposed by me simply brings them together, allows easy configuration even for the less experienced and updates them automatically. 

## License
[GNU](https://www.gnu.org/licenses/gpl-3.0.html)
