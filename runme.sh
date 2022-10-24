#!/bin/bash

### Colors ##
ESC=$(printf '\033') RESET="${ESC}[0m" BLACK="${ESC}[30m" RED="${ESC}[31m"
GREEN="${ESC}[32m" YELLOW="${ESC}[33m" BLUE="${ESC}[34m" MAGENTA="${ESC}[35m"
CYAN="${ESC}[36m" WHITE="${ESC}[37m" DEFAULT="${ESC}[39m"

### Color Functions ##

greenprint() { printf "${GREEN}%s${RESET}\n" "$1"; }
blueprint() { printf "${BLUE}%s${RESET}\n" "$1"; }
redprint() { printf "${RED}%s${RESET}\n" "$1"; }
yellowprint() { printf "${YELLOW}%s${RESET}\n" "$1"; }
magentaprint() { printf "${MAGENTA}%s${RESET}\n" "$1"; }
cyanprint() { printf "${CYAN}%s${RESET}\n" "$1"; }

### Links ##
readonly EARNAPP_LNK="Earnapp | https://earnapp.com/i/3zulx7k"
readonly HONEYGAIN_LNK="HoneyGain | https://r.honeygain.me/MINDL15721"
readonly IPROYALPAWNS_LNK="IPROYAL | https://pawns.app?r=MiNe"
readonly PACKETSTREAM_LNK="PACKETSTREAM | https://packetstream.io/?psr=3zSD"
readonly PEER2PROFIT_LNK="PEER2PROFIT | https://p2pr.me/165849012262da8d0aa13c8"
readonly TRAFFMONETIZER_LNK="TRAFFMONETIZER | https://traffmonetizer.com/?aff=366499"
readonly BITPING_LNK="BITPING | https://app.bitping.com?r=qm7mIuX3"

### .env File Prototype Link##
readonly ENV_SRC='https://github.com/MRColorR/money4band/raw/main/.env';

### docker-compose.yml Prototype Link##
readonly DKCOM_SRC='https://github.com/MRColorR/money4band/raw/main/docker-compose.yml';

### Functions ##
fn_bye() { echo "Bye bye."; exit 0; }
fn_fail() { echo "Wrong option." exit 1; }
fn_unknown() { redprint "Unknown choice $REPLY, please choose a valid option";}

### Sub-menu Functions ##
fn_showLinks(){
    clear;
    greenprint "Use CTRL+Click to open links or copy them:";
                cyanprint "1) $EARNAPP_LNK";
                cyanprint "2) $HONEYGAIN_LNK";
                cyanprint "3) $IPROYALPAWNS_LNK";
                cyanprint "4) $PACKETSTREAM_LNK";
                cyanprint "5) $PEER2PROFIT_LNK";
                cyanprint "6) $TRAFFMONETIZER_LNK";
                cyanprint "7) $BITPING_LNK";
                read -p "Press enter to go back to mainmenu"
    
    }

fn_dockerInstall(){
    yellowprint "This menu item will launch a script that will attempt to install docker"
    yellowprint "Use it only if you do not know how to perform the manual docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some rare cases and depending on the distros may fail to install docker correctly."
    read -p "Do you wish to proceed with the Docker automatic installation Y/N?  " yn
    case $yn in
        [Yy]* ) curl -fsSL https://get.docker.com -o get-docker.sh; sudo sh get-docker.sh; greenprint "Docker installed"; mainmenu;;
        [Nn]* ) blueprint "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps."; read -p "Press Enter to go back to mainmenu"; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
}

fn_setupNotifications(){
    echo "Starting Notifications setup:"
    echo "This step will setup notifications about containers updates using shoutrrr"
    echo "Now we will configure a SHOUTRRR_URL that should looks like this <app>://<token>@<webhook> . Where <app> is one of the supported messaging apps supported by shoutrrr (We will use a private discord server as example)."
    echo "For more apps and details visit https://containrrr.dev/shoutrrr/, select your desider app (service) and paste the required SHOUTRRR_URL in this script when prompted "
    echo "CREATE A NEW DISCORD SERVER, GO TO SERVER SETTINGS>INTEGRATIONS AND CREATE A WEBHOOK"
    echo " Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken to obtain the SHOUTRRR_URL you should rearrange it to look like this: discord://yourToken@yourWebhookid"
    read SHOUTRRR_URL -p " NOW INSERT IT HERE using THE SAME FORMAT WRITTEN ABOVE: discord://yourToken@yourWebhookid "
    sed -i "s/# SHOUTRRR_URL=discord://yourToken@yourWebhook/SHOUTRRR_URL=$SHOUTRRR_URL/" .env
    sed -i "s/# - WATCHTOWER_NOTIFICATIONS=shoutrrr/- WATCHTOWER_NOTIFICATIONS=shoutrrr/" docker-compose.yml
    sed -i "s/# - WATCHTOWER_NOTIFICATION_URL/- WATCHTOWER_NOTIFICATION_URL/" docker-compose.yml
    sed -i "s/# - WATCHTOWER_NOTIFICATIONS_HOSTNAME/- WATCHTOWER_NOTIFICATIONS_HOSTNAME/" docker-compose.yml
    read -p "Notifications setup complete. If the link is correct, you will receive a notification for each update made on the app container images. Now press enter to continue"
    clear;
}

fn_setupApp(){
    if [ "$2" == "email" ] ; then 
        read APP_EMAIL -p "Enter your $1 Email"$'\n'
        sed -i "s/your$1Mail/$APP_EMAIL/" .env
        if [ "$3" == "password" ] ; then 
        read APP_PASSWORD -p "Now enter your $1 Password"$'\n'
        sed -i "s/your$1Pw/$APP_PASSWORD/" .env

    elif [ "$2" == "uuid" ] ; then
        echo "generating an UUID for $1"$'\n'
        UUID="$(echo -n "$3" | md5sum | cut -c1-32)"
        sed -i "s/yourMD5sum/$UUID/" .env
        cyanprint "Save the following link somewhere to claim your earnapp node after completing the setup and after starting the apps stack: https://earnapp.com/r/sdk-node-$UUID. A new file containing this link has been created for you"
        printf "https://earnapp.com/r/sdk-node-$UUID" > ClaimEarnappNode.txt
    elif [ "$2" == "cid" ] ; then 
        echo "Enter your $1 CID."$'\n'
        echo "You can find it going in your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page (you can also use CTRL+F) you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"$'\n'
        read APP_CID
        sed -i "s/your$1CID/$APP_CID/" .env
    elif [ "$2" == "token" ] ; then 
        echo "Enter your $1 Token."$'\n'
        echo "You can find it going in your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"$'\n'
        read APP_TOKEN
        sed -i "s/your$1Token/$APP_TOKEN/" .env
    fi
}

fn_setupEnv(){
    read -p "Do you wish to proceed with the .env file guided setup Y/N?  " yn
    case $yn in
        [Yy]* ) clear;;
        [Nn]* ) blueprint ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup."; read -p "Press Enter to go back to mainmenu"; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
    echo "beginnning env file guided setup"
    CURRENT_APP='';
    read -p "Press enter to continue"$'\n'
    yellowprint "PLEASE ENTER A NAME FOR YOUR DEVICE:"
    read DEVICE_NAME
    sed -i "s/yourDeviceName/$DEVICE_NAME/" .env

    yellowprint "PLEASE REGISTER ON THE PLATFORMS USING THE FOLLOWING LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
    greenprint "Use CTRL+Click to open links or copy them:"

    #EarnApp app env setup
    CURRENT_APP='EARNAPP';
    cyanprint "Go to $EARNAPP_LNK and register";
    read -p "When done, press enter to continue"$'\n'
    fn_setupApp $CURRENT_APP uuid $DEVICE_NAME;
    read -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

    #HoneyGain app env setup
    clear;
    CURRENT_APP='HONEYGAIN';
    cyanprint "Go to $HONEYGAIN_LNK and register"
    read -p "When done, press enter to continue"$'\n'
    fn_setupApp $CURRENT_APP email password
    read -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

    #Pawn IPRoyal app env setup
    clear;
    CURRENT_APP='IPROYALPAWNS'
    cyanprint "Go to $IPROYALPAWNS_LNK and register"
    read -p "When done, press enter to continue"$'\n'
    fn_setupApp $CURRENT_APP email password
    read -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

    #Peer2Profit app env setup
    clear;
    CURRENT_APP='PEER2PROFIT'
    cyanprint "Go to $PEER2PROFIT_LNK and register"
    read -p "When done, press enter to continue"$'\n'
    fn_setupApp $CURRENT_APP email
    read -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

    #PacketStream app env setup
    clear;
    CURRENT_APP='PACKETSTREAM'
    cyanprint "Go to $PACKETSTREAM_LNK and register"
    read -p "When done, press enter to continue"$'\n'
    fn_setupApp $CURRENT_APP cid
    read -p "$CURRENT_APP configuration complete, press enter to continue to the next app"


    # TraffMonetizer app env setup
    clear;
    CURRENT_APP='TRAFFMONETIZER'
    cyanprint "Go to $TRAFFMONETIZER_LNK and register"
    read -p "When done, press enter to continue"$'\n'
    fn_setupApp $CURRENT_APP token
    read -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

    
    # Bitping app env setup
    clear;
    cyanprint "Go to $BITPING_LNK and register"
    read -p "When done, press enter to continue"$'\n'
    echo "To configure this app we will need to start an interactive container (so Docker needs to be already installed)."
    echo "To do that we will open a new terminal in this same folder and run bitpingSetup.sh for you"$'\n'
    read -n 1 -s -r -p "When ready to start, press any key to continue"$'\n'
    chmod u+x ./bitpingSetup.sh;
    sudo sh -c './bitpingSetup.sh';

    read -p "Do you wish to setup notifications about apps images updates (Yes to recieve notifications and apply updates, No to just silently apply updates) Y/N?  " yn
    case $yn in
        [Yy]* ) fn_setupNotifications;;
        [Nn]* ) blueprint "Noted: all updates will be applied automatically and silently";;
        * ) echo "Please answer yes or no.";;
    esac

    greenprint "env file setup complete.";
    read -n 1 -s -r -p "Press any key to go back to the menu"$'\n'

    mainmenu;
    }

fn_startStack(){
    yellowprint "This menu item will launch all the apps using the configured .env file and the docker-compose.yml file (Docker must be already installed and running)"
    read -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) sudo docker compose up -d; greenprint "All Apps started you can visit the web dashboard on http://localhost:8081/ . If not already done use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details."; read -p "Now press enter to go back to the menu"; mainmenu;;
        [Nn]* ) blueprint "Docker stack startup canceled.";read -p "Press Enter to go back to mainmenu"; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
}

fn_resetEnv(){
    redprint "Now a fresh env file will be downloaded and will need to be reconfigured to be used again"
    read -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) curl -LJO $ENV_SRC; greenprint ".env file resetted, remember to reconfigure it";;
        [Nn]* ) blueprint ".env file reset canceled. The file is left as it is"; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
}

fn_resetDockerCompose(){
    redprint "Now a fresh docker-compose.yml file will be downloaded"
    read -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) curl -LJO $DKCOM_SRC; greenprint "docker-compose.yml file resetted, remember to reconfigure it if needed";;
        [Nn]* ) blueprint "docker-compose.yml file reset canceled. The file is left as it is"; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
}

### Main Menu ##
mainmenu() {
    clear;
    PS3="Select an option and press Enter "

    items=("Show apps' links to register or go to dashboard", "Install Docker", "Setup .env file", "Start apps stack", "Reset .env File", "Reset docker-compose.yml file")

    select item in "${items[@]}" Quit
    do
        case $REPLY in
            1) clear; fn_showLinks; break;;
            2) clear; fn_dockerInstall; break;;
            3) clear; fn_setupEnv; break;;
            4) clear; fn_startStack; break;;
            5) clear; fn_resetEnv; break;;
            6) clear; fn_resetDockerCompose; break;;
            $((${#items[@]}+1))) fn_bye;;
            *) clear; fn_unknown; break;;
        esac
    done
}

### Startup ##


while true; do
    mainmenu
done