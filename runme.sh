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
readonly IPROYAL_LNK="IPROYAL | https://pawns.app?r=MiNe"
readonly PACKETSTREAM_LNK="PACKETSTREAM | https://packetstream.io/?psr=3zSD"
readonly PEER2PROFIT_LNK="PEER2PROFIT | https://p2pr.me/165849012262da8d0aa13c8"
readonly TRAFFMONETIZER_LNK="TRAFFMONETIZER | https://traffmonetizer.com/?aff=366499"
readonly BITPING_LNK="BITPING | https://app.bitping.com?r=qm7mIuX3"

### .env File Prototype Link##
readonly ENV_SRC='https://github.com/MRColorR/money4band/raw/main/.env'

### Functions ##
fn_bye() { echo "Bye bye."; exit 0; }
fn_fail() { echo "Wrong option." exit 1; }
fn_unknown() { redprint "Unknown choice $REPLY, please choose a valid option";}

### Sub-menu Functions ##
fn_showLinks(){
    greenprint "Use CTRL+Click to open links or copy them:";
    PS3="Select item please:";
    items=("$EARNAPP_LNK" "$HONEYGAIN_LNK" "$IPROYAL_LNK" "$PACKETSTREAM_LNK" "$PEER2PROFIT_LNK" "$TRAFFMONETIZER_LNK" "$BITPING_LNK")    
        select item in "${items[@]}" "Go back"
        do
        clear;
            case $REPLY in
                1) cyanprint "$EARNAPP_LNK";fn_showLinks;;
                2) cyanprint "$HONEYGAIN_LNK";fn_showLinks;;
                3) cyanprint "$IPROYAL_LNK"; fn_showLinks;;
                4) cyanprint "$PACKETSTREAM_LNK"; fn_showLinks;;
                5) cyanprint "$PEER2PROFIT_LNK"; fn_showLinks;;
                6) cyanprint "$TRAFFMONETIZER_LNK"; fn_showLinks;;
                7) cyanprint "$BITPING_LNK"; fn_showLinks;;
                $((${#items[@]}+1))) mainmenu;;
                *) fn_unknown; fn_showLinks;;
            esac
        done
    
    }

fn_dockerInstall(){
    yellowprint "This menu item will launch a script that will attempt to install docker"
    yellowprint "Use it only if you do not know how to perform the manual docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some rare cases and depending on the distros may fail to install docker correctly."
    read -p "Do you wish to proceed with the Docker automatic installation Y/N?  " yn
    case $yn in
        [Yy]* ) curl -fsSL https://get.docker.com -o get-docker.sh; sudo sh get-docker.sh; greenprint "Docker installed"; mainmenu;;
        [Nn]* ) blueprint "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps. You will be redirected to the main menu"; sleep 9; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
}

fn_setupEnv(){
    read -p "Do you wish to proceed with the .env file guided setup Y/N?  " yn
    case $yn in
        [Yy]* ) clear;;
        [Nn]* ) blueprint ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup. You will be redirected to the main menu"; sleep 9; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
    echo "beginnning env file guided setup"
    read -n 1 -s -r -p "Press any key to continue"$'\n'
    touch .env
    yellowprint "PLEASE ENTER A NAME FOR YOUR DEVICE:"
    read DEVICE_NAME
    sed -i "s/yourDeviceName/$DEVICE_NAME/" .env

    yellowprint "PLEASE REGISTER ON THE PLATFORMS USING THIS LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
    greenprint "Use CTRL+Click to open links or copy them:"

    #EarnApp app env setup
    cyanprint "Go to $EARNAPP_LNK and register"
    read -n 1 -s -r -p "When done, press any key to continue"$'\n'
    echo "generating an UUID for earnapp"$'\n'
    UUID="$(echo -n "$DEVICE_NAME" | md5sum | cut -c1-32)"
    sed -i "s/yourMD5sum/$UUID/" .env
    cyanprint "Save the following link somewhere to claim your earnapp node after completing the setup and after starting the apps stack: https://earnapp.com/r/sdk-node-$UUID"

    #HoneyGain app env setup
    cyanprint "Go to $HONEYGAIN_LNK and register"
    read -n 1 -s -r -p "When done, press any key to continue"$'\n'
    echo "Enter your HoneyGain Email"$'\n'
    read HG_EMAIL
    sed -i "s/yourHGMail/$HG_EMAIL/" .env
    echo "Now enter your HoneyGain Password"$'\n'
    read HG_PASSWORD
    sed -i "s/yourHGPw/$HG_PASSWORD/" .env

    #Pawn IPRoyal app env setup
    cyanprint "Go to $IPROYAL_LNK and register"
    read -n 1 -s -r -p "When done, press any key to continue"$'\n'
    echo "Enter your Pawn IPRoyal Email"$'\n'
    read IR_EMAIL
    sed -i "s/yourIRMail/$IR_EMAIL/" .env
    echo "Now enter your HoneyGain Password"$'\n'
    read IR_PASSWORD
    sed -i "s/yourIRPw/$IR_PASSWORD/" .env

    #Peer2Profit app env setup
    cyanprint "Go to $PEER2PROFIT_LNK and register"
    read -n 1 -s -r -p "When done, press any key to continue"$'\n'
    echo "Enter your Peer2Profit Email"$'\n'
    read P2P_EMAIL
    sed -i "s/yourP2PMail/$P2P_EMAIL/" .env

    #PacketStream app env setup
    cyanprint "Go to $PACKETSTREAM_LNK and register"
    read -n 1 -s -r -p "When done, press any key to continue"$'\n'
    echo "Enter your PacketStream CID."$'\n'
    echo "You can find it going in your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page (you can also use CTRL+F) you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 3zSD)"$'\n'
    read PS_CID
    sed -i "s/yourPSCID/$PS_CID/" .env

    # TraffMonetizer app env setup
    cyanprint "Go to $TRAFFMONETIZER_LNK and register"
    read -n 1 -s -r -p "When done, press any key to continue"$'\n'
    echo "Enter your TraffMonetizer Token."$'\n'
    echo "You can find it going in your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"$'\n'
    read TM_TOKEN
    sed -i "s/yourTMToken/$TM_TOKEN/" .env
    
    # Bitping app env setup
    cyanprint "Go to $BITPING_LNK and register"
    read -n 1 -s -r -p "When done, press any key to continue"$'\n'
    echo "To configure this app we will need to start an interactive container (so Docker needs to be already installed), then wait and enter your bitping email and password in it when prompted , hit enter and then close it as we will not need it anymore"$'\n'
    echo "To do that open a new terminal in this same folder (this project folder) and run bitpingSetup.sh "$'\n'
    #read -n 1 -s -r -p "When ready to start, press any key to continue"$'\n'
    #sudo docker run --rm -it -v ${PWD}/.data/.bitping/:/root/.bitping bitping/bitping-node:latest

    greenprint "env file setup complete."
    read -n 1 -s -r -p "Press any key to go back to the menu"$'\n'

    mainmenu;
    }

fn_startStack(){
    yellowprint "This menu item will launch all the apps using the configured .env file and the docker-compose.yml file (Docker must be already installed and running)"
    read -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) sudo docker compose up -d; greenprint "All Apps started. If not already done use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details."; mainmenu;;
        [Nn]* ) blueprint "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps"; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
}

fn_resetEnv(){
    redprint "Now a fresh env file will be downloaded and will need to be reconfigured to be used again"
    read -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) curl -LJO $ENV_SRC; greenprint ".env file resetted, remember to reconfigure it";;
        [Nn]* ) blueprint ".env file reset aborted. The file is left as it is"; mainmenu;;
        * ) echo "Please answer yes or no.";;
    esac
    

    

}

### Main Menu ##
mainmenu() {
    clear;
    PS3="Select item please: "

    items=("Show apps' links to register or go to dashboard", "Install Docker", "Setup .env file", "Start apps stack", "Reset .env File")

    select item in "${items[@]}" Quit
    do
        case $REPLY in
            1) clear; fn_showLinks; break;;
            2) clear; fn_dockerInstall; break;;
            3) clear; fn_setupEnv; break;;
            4) clear; fn_startStack; break;;
            5) clear; fn_resetEnv; break;;
            $((${#items[@]}+1))) fn_bye;;
            *) clear; fn_unknown; break;;
        esac
    done
}

### Startup ##


while true; do
    mainmenu
done