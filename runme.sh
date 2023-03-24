#!/bin/bash

### Colors ##
ESC=$(printf '\033') RESET="${ESC}[0m" RED="${ESC}[31m"
GREEN="${ESC}[32m" YELLOW="${ESC}[33m" BLUE="${ESC}[34m" MAGENTA="${ESC}[35m"
CYAN="${ESC}[36m"

### Color Functions ##

greenprint() { printf "${GREEN}%s${RESET}\n" "$1"; }
blueprint() { printf "${BLUE}%s${RESET}\n" "$1"; }
redprint() { printf "${RED}%s${RESET}\n" "$1"; }
yellowprint() { printf "${YELLOW}%s${RESET}\n" "$1"; }
magentaprint() { printf "${MAGENTA}%s${RESET}\n" "$1"; }
cyanprint() { printf "${CYAN}%s${RESET}\n" "$1"; }

### Links ##
readonly EARNAPP_LNK="EARNAPP | https://earnapp.com/i/3zulx7k"
readonly EARNAPP_IMG='fazalfarhan01/earnapp'

readonly HONEYGAIN_LNK="HONEYGAIN | https://r.honeygain.me/MINDL15721"
readonly HONEYGAIN_IMG='honeygain/honeygain'

readonly IPROYALPAWNS_LNK="IPROYALPAWNS | https://pawns.app?r=MiNe"
readonly IPROYALPAWNS_IMG='iproyal/pawns-cli'

readonly PACKETSTREAM_LNK="PACKETSTREAM | https://packetstream.io/?psr=3zSD"
readonly PACKETSTREAM_IMG='packetstream/psclient'

readonly PEER2PROFIT_LNK="PEER2PROFIT | https://p2pr.me/165849012262da8d0aa13c8"
readonly PEER2PROFIT_IMG='peer2profit/peer2profit_linux'

readonly TRAFFMONETIZER_LNK="TRAFFMONETIZER | https://traffmonetizer.com/?aff=366499"
readonly TRAFFMONETIZER_IMG='traffmonetizer/cli'

readonly REPOCKET_LNK="REPOCKET | https://link.repocket.co/hr8i"
readonly REPOCKET_IMG='repocket/repocket'

readonly PROXYRACK_LNK="PROXYRACK | https://peer.proxyrack.com/ref/myoas6qttvhuvkzh8ffx90ns1ouhwgilfgamo5ex"
readonly PROXYRACK_IMG='proxyrack/pop'

readonly BITPING_LNK="BITPING | https://app.bitping.com?r=qm7mIuX3"
readonly BITPING_IMG='bitping/bitping-node'

### .env File Prototype Link##
readonly ENV_SRC='https://github.com/MRColorR/money4band/raw/main/.env';

### docker compose.yaml Prototype Link##
readonly DKCOM_FILENAME="docker-compose.yaml"
readonly DKCOM_SRC="https://github.com/MRColorR/money4band/raw/main/$DKCOM_FILENAME";

### Resources, Scripts and Files folders
readonly RESOURCES_DIR="$PWD/.resources"
readonly SCRIPTS_DIR="$RESOURCES_DIR/.scripts"
readonly FILES_DIR="$RESOURCES_DIR/.files"

## Achitecture default
ARCH='unknown'
DKARCH='unknown'

### Proxy config #
PROXY_CONF='false' ;
PROXY_CONF_ALL='false' ;
STACK_HTTP_PROXY='';
STACK_HTTPS_PROXY='';

### Functions ##
fn_bye() { printf "Bye bye."$'\n'; exit 0; }
fn_fail() { printf "Wrong option."; exit 1; }
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
                cyanprint "7) $REPOCKET_LNK";
                cyanprint "8) $PROXYRACK_LNK";
                cyanprint "9) $BITPING_LNK";
                read -r -p "Press enter to go back to mainmenu"
    
    }

fn_dockerInstall(){
    yellowprint "This menu item will launch a script that will attempt to install docker"
    yellowprint "Use it only if you do not know how to perform the manual docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some rare cases and depending on the distros may fail to install docker correctly."
    read -r -p "Do you wish to proceed with the Docker automatic installation Y/N?  " yn
    case $yn in
        [Yy]* ) curl -fsSL https://get.docker.com -o "$SCRIPTS_DIR/get-docker.sh"; sudo sh "$SCRIPTS_DIR/get-docker.sh"; greenprint "Docker installed"; mainmenu;;
        [Nn]* ) blueprint "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps."; read -r -p "Press Enter to go back to mainmenu"; mainmenu;;
        * ) printf "Please answer yes or no.";;
    esac
}

fn_setupNotifications(){
    clear;
    printf "This step will setup notifications about containers updates using shoutrrr"$'\n'
    printf "The resulting configured SHOUTRRR_URL should looks like this <app>://<token>@<webhook> . Where <app> is one of the supported messaging apps supported by shoutrrr (E.g. a private Discord server)."
    printf "For more apps and details visit https://containrrr.dev/shoutrrr/, select your desider app (service) and paste the required SHOUTRRR_URL in this script when prompted "$'\n'
    read -r -p "Press enter to proceed and show the discord notification setup example (Remember: you can also use a different supported app, just enter the link correctly)"
    clear;
    printf "CREATE A NEW DISCORD SERVER, GO TO SERVER SETTINGS>INTEGRATIONS AND CREATE A WEBHOOK"$'\n'
    printf "Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken to obtain the SHOUTRRR_URL you should rearrange it to look like this: discord://yourToken@yourWebhookid"$'\n'
    read -r -p "Press enter to continue"
    clear;
    printf "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"$'\n'
    read -r SHOUTRRR_URL
    sed -i "s^# SHOUTRRR_URL=yourApp:yourToken@yourWebHook^SHOUTRRR_URL=$SHOUTRRR_URL^" .env
    sed -i "s/# - WATCHTOWER_NOTIFICATIONS=shoutrrr/- WATCHTOWER_NOTIFICATIONS=shoutrrr/" $DKCOM_FILENAME
    sed -i "s/# - WATCHTOWER_NOTIFICATION_URL/- WATCHTOWER_NOTIFICATION_URL/" $DKCOM_FILENAME
    sed -i "s/# - WATCHTOWER_NOTIFICATIONS_HOSTNAME/- WATCHTOWER_NOTIFICATIONS_HOSTNAME/" $DKCOM_FILENAME
    read -r -p "Notifications setup complete. If the link is correct, you will receive a notification for each update made on the app container images. Now press enter to continue"
    clear;
}

fn_setupApp() {
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --app)
                CURRENT_APP="$2"
                shift
                ;;
            --image)
                APP_IMAGE="$2"
                shift
                ;;
            --email)
                printf "Note: If you are using login with google, remember to set also a password for your app account!"$'\n'
                printf "Enter your %s Email"$'\n' "$CURRENT_APP"
                read -r APP_EMAIL
                sed -i "s/your$CURRENT_APPMail/$APP_EMAIL/" .env
                ;;
            --password)
                printf "Now enter your %s Password"$'\n' "$CURRENT_APP"
                read -r APP_PASSWORD
                sed -i "s/your$CURRENT_APPPw/$APP_PASSWORD/" .env
                ;;
            --apikey)
                printf "Now enter your %s APIKey. You can find/generate it inside your %s dashboard/profile."$'\n' "$CURRENT_APP" "$CURRENT_APP"
                read -r APP_APIKEY
                sed -i "s/your$CURRENT_APPAPIKey/$APP_APIKEY/" .env
                ;;
            --uuid)
                printf "Starting UUID generation/import for %s\n" "$CURRENT_APP"
                SALT="$2""$RANDOM"
                UUID="$(echo -n "$SALT" | md5sum | cut -c1-32)"
                printf "(Enter y to import an existing UUID OR Enter n to let the script auto generate a new one) \n"
                printf "Do you want to use a previously registered sdk-node-uuid for %s? (Y/N)\n" "$CURRENT_APP"
                read -r USE_EXISTING_UUID
                if [ "$USE_EXISTING_UUID" == "Y" ] || [ "$USE_EXISTING_UUID" == "y" ]; then
                    while true; do
                        printf "Please enter the 32 char long alphanumeric part of the existing sdk-node-uuid for %s:\n" "$CURRENT_APP"
                        printf "E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4 \n"
                        read -r EXISTING_UUID
                        if [[ ! "$EXISTING_UUID" =~ ^[a-f0-9]{32}$ ]]; then
                            redprint "Invalid UUID entered, it should be an md5 hash and 32 characters long."
                            printf "(Enter y to try again OR Enter n to let the script auto generate a new UUID) \n"
                            printf "Do you want to try again? (Y/N)\n"
                            read -r TRY_AGAIN
                            if [ "$TRY_AGAIN" == "N" ] || [ "$TRY_AGAIN" == "n" ]; then
                                break
                            fi
                        else
                            UUID="$EXISTING_UUID"
                            break
                        fi
                    done
                fi
                sed -i "s/your$CURRENT_APPMD5sum/$UUID/" .env
                printf "%s UUID setup: done\n" "$CURRENT_APP"
                cyanprint "Save the following link somewhere to claim your earnapp node after completing the setup and after starting the apps stack: https://earnapp.com/r/sdk-node-$UUID. A new file containing this link has been created for you"
                printf "https://earnapp.com/r/sdk-node-%s\n" "$UUID" > ClaimEarnappNode.txt
                ;;
            --cid)
                printf "Enter your %s CID."$'\n' "$CURRENT_APP"
                printf "You can find it going in your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"$'\n'
                read -r APP_CID
                sed -i "s/your$CURRENT_APPCID/$APP_CID/" .env
                ;;
            --token)
                printf "Enter your %s Token."$'\n' "$CURRENT_APP"
                printf "You can find it going in your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"$'\n'
                read -r APP_TOKEN
                sed -i "s^your$CURRENT_APPToken^$APP_TOKEN^" .env
                ;;
            --customScript)
                ESCAPED_PATH="$(echo "$2" | sed 's/"/\\"/g')"
                chmod u+x "$ESCAPED_PATH"
                source "$ESCAPED_PATH"
                shift
                ;;
            *)
                printf "Unknown flag: %s\n" "$1"
                exit 1
                ;;
        esac
        shift
    done

    # Global and per app proxy config trigger
    if [ "$PROXY_CONF" == 'true' ] ; then 
        if [ "$PROXY_CONF_ALL" == 'true' ] ; then
            sed -i "s^# $CURRENT_APP_HTTP_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port^$CURRENT_APP_HTTP_PROXY=$STACK_HTTP_PROXY^" .env ;
            sed -i "s^# $CURRENT_APP_HTTPS_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port^$CURRENT_APP_HTTPS_PROXY=$STACK_HTTPS_PROXY^" .env ;
        else 
            printf "Insert the designed HTTP proxy to use with %s (also socks5h is supported)."$'\n' "$CURRENT_APP"
            read -r APP_HTTP_PROXY
            printf "Insert the designed HTTPS proxy to use with %s (you can also use the same of the HTTP proxy and also socks5h is supported)."$'\n' "$CURRENT_APP";
            read -r APP_HTTPS_PROXY
            sed -i "s^# $CURRENT_APP_HTTP_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port^$CURRENT_APP_HTTP_PROXY=$APP_HTTP_PROXY^" .env ;
            sed -i "s^# $CURRENT_APP_HTTPS_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port^$CURRENT_APP_HTTPS_PROXY=$APP_HTTPS_PROXY^" .env ;

        fi
        sed -i "s^#- $CURRENT_APP_HTTP_PROXY^- HTTP_PROXY^" $DKCOM_FILENAME ;
        sed -i "s^#- $CURRENT_APP_HTTPS_PROXY^- HTTPS_PROXY^" $DKCOM_FILENAME ;
        sed -i "s^#- $CURRENT_APP_NO_PROXY^- NO_PROXY^" $DKCOM_FILENAME ;
    fi

    # App Docker image architecture adjustments
    TAG='latest'
    DKHUBRES=`curl -L -s "https://registry.hub.docker.com/v2/repositories/$APP_IMAGE/tags?page=\$page_index&page_size=\$page_size" | jq --arg DKARCH "$DKARCH" '[.results[] | select(.images[].architecture == $DKARCH) | .name]'`
    TAGSNUMBER=`echo $DKHUBRES | jq '. | length'`
    if [ $TAGSNUMBER -gt 0 ]; then 
        echo "there are $TAGSNUMBER tags supporting $DKARCH arch for this image";
        echo "Let's see if $TAG tag is in there"
        LATESTPRESENT=`echo $DKHUBRES | jq --arg TAG "$TAG" '[.[] | contains($TAG)] | any'`
        if [ $LATESTPRESENT == "true" ]; then 
            echo "ok, $TAG tag present and it supports $DKARCH arch, nothing to do"; 
        else 
            echo "$TAG tag does not support $DKARCH arch but other tags do, the newer tag supporting $DKARCH will be selected";
            NEWTAG=`echo $DKHUBRES | jq -r '.[0]'`;
            sed -i "s^$APP_IMAGE:latest^$APP_IMAGE:$NEWTAG^" $DKCOM_FILENAME ;

        fi
    else 
        echo "no native image tag found for $DKARCH arch, nothing to do, emulation layer will try to run this app image anyway (make sure it has been installed)"; 
    fi

    read -r -p "$CURRENT_APP configuration complete, press enter to continue to the next app"
}


fn_setupProxy(){
    if [ "$PROXY_CONF" == 'false' ] ; then
        read -r -p "Do you wish to use a proxy? Y/N? Note that if you want to run multiple instances of the same app you will need to configure different env files each in different project folders (copy the project to multiple different folders and configure them using different proxies)"$'\n' yn
        case $yn in
            [Yy]* ) clear;
                printf "Proxy setup started.";
                read -r -p "Do you wish to use the same proxy for all the apps in this stack? Y/N?" yn ;
                case $yn in
                    [Yy]* ) 
                        printf "Insert the designed HTTP proxy to use. Eg: http://proxyUsername:proxyPassword@proxy_url:proxy_port or just http://proxy_url:proxy_port if auth is not needed, also socks5h is supported."$'\n';
                        read -r STACK_HTTP_PROXY;
                        printf "Ok, %s will be used as proxy for all apps in this stack"$'\n' "$STACK_HTTP_PROXY"
                        read -r -p "Press enter to continue"
                        clear
                        printf "Insert the designed HTTPS proxy to use (you can also use the same of the HTTP proxy), also socks5h is supported."$'\n'
                        read -r STACK_HTTPS_PROXY;
                        printf "Ok, %s will be used as secure proxy for all apps in this stack"$'\n' "$STACK_HTTPS_PROXY"
                        read -r -p "Press enter to continue"
                        PROXY_CONF_ALL='true' ;
                        PROXY_CONF='true' ;
                        ;;
                    [Nn]* ) 
                    PROXY_CONF_ALL='false' ;
                    PROXY_CONF='true' ;
                    blueprint "Ok, later you will be asked for a proxy for each application";;
                    * ) printf "Please answer yes or no."; fn_setupProxy;;
                esac
                # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                sed -i "s^COMPOSE_PROJECT_NAME=Money4Band^COMPOSE_PROJECT_NAME=Money4Band_$RANDOM^" .env ;;
            [Nn]* ) blueprint "Ok, no proxy added to configuration.";;
            * ) printf "Please answer yes or no."; fn_setupProxy ;;
        esac 
    fi
}

fn_setupEnv(){
    read -r -p "Do you wish to proceed with the .env file guided setup Y/N? (This will also adapt the $DKCOM_FILENAME file accordingly)"$'\n' yn
    case $yn in
        [Yy]* ) clear;;
        [Nn]* ) blueprint ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup."; read -r -p "Press Enter to go back to mainmenu"; mainmenu;;
        * ) printf "Please answer yes or no."; fn_setupEnv ;;
    esac
    if ! grep -q "DEVICE_NAME=yourDeviceName" .env  ; then 
        echo "The current .env file appears to have already been modified. A fresh version will be downloaded and used.";
        curl -fsSL $ENV_SRC -o ".env"
        curl -fsSL $DKCOM_SRC -o "$DKCOM_FILENAME"
    fi
    printf "beginnning env file guided setup"$'\n'
    CURRENT_APP='';
    yellowprint "PLEASE ENTER A NAME FOR YOUR DEVICE:"
    read -r DEVICE_NAME
    sed -i "s/yourDeviceName/$DEVICE_NAME/" .env
    clear ;
    fn_setupProxy ;
    clear ;

    # if not installed, install JQ as it will be used during app config
    printf "Now a small useful package named JQ used to manage JSON files will be installed if not already present"$'\n'
    printf "Please, if prompted, enter your sudo password to proceed"$'\n'
    sudo apt install jq -y
    clear;

    yellowprint "PLEASE REGISTER ON THE PLATFORMS USING THE FOLLOWING LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
    greenprint "Use CTRL+Click to open links or copy them:"

    # EarnApp app env setup
    CURRENT_APP='EARNAPP';
    cyanprint "Go to $EARNAPP_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$EARNAPP_IMG" --uuid "$DEVICE_NAME"

    # HoneyGain app env setup
    clear;
    CURRENT_APP='HONEYGAIN';
    cyanprint "Go to $HONEYGAIN_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$HONEYGAIN_IMG" --email --password

    # IProyalPawns app env setup
    clear;
    CURRENT_APP='IPROYALPAWNS'
    cyanprint "Go to $IPROYALPAWNS_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$IPROYALPAWNS_IMG" --email --password

    # Peer2Profit app env setup
    clear;
    CURRENT_APP='PEER2PROFIT'
    cyanprint "Go to $PEER2PROFIT_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$PEER2PROFIT_IMG" --email

    # PacketStream app env setup
    clear;
    CURRENT_APP='PACKETSTREAM'
    cyanprint "Go to $PACKETSTREAM_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$PACKETSTREAM_IMG" --cid

    # TraffMonetizer app env setup
    clear;
    CURRENT_APP='TRAFFMONETIZER'
    cyanprint "Go to $TRAFFMONETIZER_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$TRAFFMONETIZER_IMG" --token

    # Repocket app env setup
    clear;
    CURRENT_APP='REPOCKET'
    cyanprint "Go to $REPOCKET_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$REPOCKET_IMG" --email --apikey

    # Proxyrack/pop app env setup
    clear;
    CURRENT_APP='PROXYRACK'
    cyanprint "Go to $PROXYRACK_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$PROXYRACK_IMG" --email --apikey

    # Bitping app env setup
    clear;
    CURRENT_APP='BITPING'
    cyanprint "Go to $BITPING_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "$CURRENT_APP" --image "$BITPING_IMG" --customScript "$SCRIPTS_DIR/bitpingSetup.sh"

    # Notifications setup
    clear;
    read -r -p "Do you wish to setup notifications about apps images updates (Yes to recieve notifications and apply updates, No to just silently apply updates) Y/N?  " yn
    case $yn in
        [Yy]* ) fn_setupNotifications;;
        [Nn]* ) blueprint "Noted: all updates will be applied automatically and silently";;
        * ) printf "Please answer yes or no."; fn_setupNotifications;;
    esac

    greenprint "env file setup complete.";
    read -n 1 -s -r -p "Press any key to go back to the menu"$'\n'

    mainmenu;
    }

fn_startStack(){
    yellowprint "This menu item will launch all the apps using the configured .env file and the $DKCOM_FILENAME file (Docker must be already installed and running)"
    read -r -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) sudo docker compose up -d; greenprint "All Apps started you can visit the web dashboard on http://localhost:8081/ . If not already done use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details."; read -r -p "Now press enter to go back to the menu"; mainmenu;;
        [Nn]* ) blueprint "Docker stack startup canceled.";read -r -p "Press Enter to go back to mainmenu"; mainmenu;;
        * ) printf "Please answer yes or no.";;
    esac
}

fn_stopStack(){
    yellowprint "This menu item will stop all the apps and delete the docker stack previously created using the configured .env file and the $DKCOM_FILENAME file."
    yellowprint "You don't need to use this command to temporarily pause apps or to update the stack. Use it only in case of uninstallation!"
    read -r -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) sudo docker compose down; greenprint "All Apps stopped and stack deleted."; read -r -p "Now press enter to go back to the menu"; mainmenu;;
        [Nn]* ) blueprint "Docker stack removal canceled.";read -r -p "Press Enter to go back to mainmenu"; mainmenu;;
        * ) printf "Please answer yes or no.";;
    esac
}

fn_resetEnv(){
    redprint "Now a fresh env file will be downloaded and will need to be configured to be used again"
    read -r -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) curl -fsSL $ENV_SRC -o ".env"; greenprint ".env file resetted, remember to reconfigure it";;
        [Nn]* ) blueprint ".env file reset canceled. The file is left as it is"; mainmenu;;
        * ) printf "Please answer yes or no.";;
    esac
}

fn_resetDockerCompose(){
    redprint "Now a fresh $DKCOM_FILENAME file will be downloaded"
    read -r -p "Do you wish to proceed Y/N?  " yn
    case $yn in
        [Yy]* ) curl -fsSL $DKCOM_SRC -o "$DKCOM_FILENAME"; greenprint "$DKCOM_FILENAME file resetted, remember to reconfigure it if needed";;
        [Nn]* ) blueprint "$DKCOM_FILENAME file reset canceled. The file is left as it is"; mainmenu;;
        * ) printf "Please answer yes or no.";;
    esac
}

### Main Menu ##
mainmenu() {
    clear;
    printf "MONEY4BAND AUTOMATIC GUIDED SETUP"$'\n'"--------------------------------- "$'\n'
    ## architecture detection
    ARCH=`uname -m`
    if [ "$ARCH" == "x86_64" ]; then 
        DKARCH='amd64'
    elif [ "$ARCH" == "aarch64" ]; then
        DKARCH='arm64'
    else 
        DKARCH=$ARCH
    fi
    printf "Detected OS architecture $ARCH"$'\n'"Docker $DKARCH image architecture will be used if the app's image permits it"$'\n'"--------------------------------- "$'\n'
    
    PS3="Select an option and press Enter "$'\n'
    items=("Show apps' links to register or go to dashboard" "Install Docker" "Setup .env file" "Start apps stack" "Stop apps stack" "Reset .env File" "Reset $DKCOM_FILENAME file")

    select item in "${items[@]}" Quit
    do
        case $REPLY in
            1) clear; fn_showLinks; break;;
            2) clear; fn_dockerInstall; break;;
            3) clear; fn_setupEnv; break;;
            4) clear; fn_startStack; break;;
            5) clear; fn_stopStack; break;;
            6) clear; fn_resetEnv; break;;
            7) clear; fn_resetDockerCompose; break;;
            $((${#items[@]}+1))) fn_bye;;
            *) clear; fn_unknown; break;;
        esac
    done
}

### Startup ##
while true; do
    mainmenu
done