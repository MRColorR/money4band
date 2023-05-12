#!/bin/bash

### Colors ###
ESC=$(printf '\033') DEFAULT="${ESC}[0m"
declare -A colors=( [GREEN]="${ESC}[32m" [BLUE]="${ESC}[34m" [RED]="${ESC}[31m" [YELLOW]="${ESC}[33m" [MAGENTA]="${ESC}[35m" [CYAN]="${ESC}[36m" [PURPLE]="${ESC}[35;1m")

### Color Functions ###
colorprint() { printf "${colors[$1]}%s${DEFAULT}\n" "$2"; }
errorprint() { printf "%s\n" "$1" >&2; }

### Links ###
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

readonly PROXYLITE_LNK="PROXYLITE | https://proxylite.ru/?r=PJTKXWN3"
readonly PROXYLITE_IMG='proxylite/proxyservice'

### .env File Prototype Link ###
readonly ENV_SRC='https://github.com/MRColorR/money4band/raw/main/.env'

### docker compose.yaml Prototype Link ###
readonly DKCOM_FILENAME="docker-compose.yaml"
readonly DKCOM_SRC="https://github.com/MRColorR/money4band/raw/main/$DKCOM_FILENAME"

### Resources, Scripts and Files folders ###
readonly RESOURCES_DIR="$PWD/.resources"
readonly SCRIPTS_DIR="$RESOURCES_DIR/.scripts"
readonly FILES_DIR="$RESOURCES_DIR/.files"

### Architecture default ###
ARCH='unknown'
DKARCH='unknown'

### Proxy config ###
PROXY_CONF='false'
STACK_PROXY=''

### Functions ###
fn_bye(){
    colorprint "GREEN" "Share this app with your friends thank you!"
    colorprint "GREEN" "Exiting the application...Bye!Bye!"
    exit 0
}

fn_fail() { errorprint "Wrong option."; exit 1; }

fn_unknown() { colorprint "RED" "Unknown choice $REPLY, please choose a valid option"; }


### Sub-menu Functions ###
fn_showLinks(){
    clear;
    colorprint "GREEN" "Use CTRL+Click to open links or copy them:";
                colorprint "CYAN" "1) $EARNAPP_LNK";
                colorprint "CYAN" "2) $HONEYGAIN_LNK";
                colorprint "CYAN" "3) $IPROYALPAWNS_LNK";
                colorprint "CYAN" "4) $PACKETSTREAM_LNK";
                colorprint "CYAN" "5) $PEER2PROFIT_LNK";
                colorprint "CYAN" "6) $TRAFFMONETIZER_LNK";
                colorprint "CYAN" "7) $REPOCKET_LNK";
                colorprint "CYAN" "8) $BITPING_LNK";
                read -r -p "Press enter to go back to mainmenu"
}


fn_dockerInstall() {
    colorprint "YELLOW" "This menu item will launch a script that will attempt to install Docker"
    colorprint "YELLOW" "Use it only if you do not know how to perform the manual Docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some rare cases and depending on the distros may fail to install Docker correctly."
    
    while true; do
        read -r -p "Do you wish to proceed with the Docker automatic installation Y/N? " yn
        case $yn in
            [Yy]* )
                if curl -fsSL https://get.docker.com -o "$SCRIPTS_DIR/get-docker.sh"; then
                    if sudo sh "$SCRIPTS_DIR/get-docker.sh"; then
                        colorprint "GREEN" "Docker installed"
                        read -r -p "Press Enter to go back to mainmenu"
                    else
                        errorprint "Failed to install Docker automatically. Please try to install Docker manually by following the instructions on Docker website."
                    fi
                else
                    errorprint "Failed to download the Docker installation script."
                fi
                break
                ;;
            [Nn]* )
                colorprint "BLUE" "Docker unattended installation canceled. Make sure you have Docker installed before proceeding with the other steps."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * )
                colorprint "RED" "Please answer yes or no."
                ;;
        esac
    done
}

fn_setupNotifications() {
    clear
    colorprint "YELLOW" "This step will setup notifications about containers updates using shoutrrr"
    colorprint "DEFAULT" "The resulting SHOUTRRR_URL should have the format: <app>://<token>@<webhook>."
    colorprint "DEFAULT" "Where <app> is one of the supported messaging apps on Shoutrrr (e.g. Discord), and <token> and <webhook> are specific to your messaging app."
    colorprint "DEFAULT" "To obtain the SHOUTRRR_URL, create a new webhook for your messaging app and rearrange its URL to match the format above."
    colorprint "DEFAULT" "For more details, visit https://containrrr.dev/shoutrrr/ and select your messaging app."
    colorprint "DEFAULT" "Now a Discord notification setup example will be shown (Remember: you can also use a different supported app)."
    read -r -p "Press enter to continue"
    clear
    colorprint "PURPLE" "Create a new Discord server, go to server settings > integrations, and create a webhook."
    colorprint "PURPLE" "Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken."
    colorprint "PURPLE" "To obtain the SHOUTRRR_URL, rearrange it to look like this: discord://YourToken@YourWebhookid."
    read -r -p "Press enter to proceed."
    clear
    colorprint "YELLOW" "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"
    read -r SHOUTRRR_URL
    if [[ "$SHOUTRRR_URL" =~ ^[a-zA-Z]+:// ]]; then
        sed -i "s~# SHOUTRRR_URL=yourApp:yourToken@yourWebHook~SHOUTRRR_URL=$SHOUTRRR_URL~" .env
        sed -i "s~# - WATCHTOWER_NOTIFICATIONS=shoutrrr~  - WATCHTOWER_NOTIFICATIONS=shoutrrr~" "$DKCOM_FILENAME"
        sed -i "s~# - WATCHTOWER_NOTIFICATION_URL~  - WATCHTOWER_NOTIFICATION_URL~" "$DKCOM_FILENAME"
        sed -i "s~# - WATCHTOWER_NOTIFICATIONS_HOSTNAME~  - WATCHTOWER_NOTIFICATIONS_HOSTNAME~" "$DKCOM_FILENAME"
        read -r -p "Notifications setup complete. If the link is correct, you will receive a notification for each update made on the app container images. Press enter to continue."
    else
        colorprint "RED" "Invalid link format. Please make sure to use the correct format."
    fi
    clear
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
                while true; do
                    colorprint "DEFAULT" "Enter your ${CURRENT_APP} Email:"
                    read -r APP_EMAIL
                    if [[ "$APP_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
                        sed -i "s/your${CURRENT_APP}Mail/$APP_EMAIL/" .env
                        break
                    else
                        colorprint "RED" "Invalid email address. Please try again."
                    fi
                done
                ;;
            --password)
                while true; do
                    colorprint "DEFAULT" "Note: If you are using login with Google, remember to set also a password for your ${CURRENT_APP} account!"
                    colorprint "DEFAULT" "Enter your ${CURRENT_APP} Password:"
                    read -r APP_PASSWORD
                    if [[ -z "$APP_PASSWORD" ]]; then
                        colorprint "RED" "Password cannot be empty. Please try again."
                    else
                        sed -i "s/your${CURRENT_APP}Pw/$APP_PASSWORD/" .env
                        break
                    fi
                done
                ;;
            --apikey)
                colorprint "DEFAULT" "Find/Generate your APIKey inside your ${CURRENT_APP} dashboard/profile."
                colorprint "DEFAULT" "Enter your ${CURRENT_APP} APIKey:"
                read -r APP_APIKEY
                sed -i "s/your${CURRENT_APP}APIKey/$APP_APIKEY/" .env
                ;;
            --userid)
                colorprint "DEFAULT" "Find your UserID inside your ${CURRENT_APP} dashboard/profile/dowload page near your account name."
                colorprint "DEFAULT" "Enter your ${CURRENT_APP} UserID:"
                read -r APP_USERID
                sed -i "s/your${CURRENT_APP}UserID/$APP_USERID/" .env
                ;;
            --uuid)
                colorprint "DEFAULT" "Starting UUID generation/import for ${CURRENT_APP}"
                shift
                SALT="$1""$RANDOM"
                UUID="$(echo -n "$SALT" | md5sum | cut -c1-32)"
                while true; do
                    colorprint "DEFAULT" "Do you want to use a previously registered sdk-node-uuid for ${CURRENT_APP}? (Y/N)"
                    read -r USE_EXISTING_UUID
                    case $USE_EXISTING_UUID in
                        [Yy]* )
                            while true; do
                                colorprint "DEFAULT" "Please enter the 32 char long alphanumeric part of the existing sdk-node-uuid for ${CURRENT_APP}:"
                                colorprint "DEFAULT" "E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4"
                                read -r EXISTING_UUID
                                if [[ ! "$EXISTING_UUID" =~ ^[a-f0-9]{32}$ ]]; then
                                    colorprint "RED" "Invalid UUID entered, it should be an md5 hash and 32 characters long."
                                    colorprint "DEFAULT" "Do you want to try again? (Y/N)"
                                    read -r TRY_AGAIN
                                    case $TRY_AGAIN in
                                        [Nn]* ) break ;;
                                        * ) continue ;;
                                    esac
                                else
                                    UUID="$EXISTING_UUID"
                                    break
                                fi
                            done
                            break
                            ;;
                        [Nn]* )
                            break
                            ;;
                        * )
                            colorprint "RED" "Please answer yes or no."
                            ;;
                    esac
                done
                sed -i "s/your${CURRENT_APP}MD5sum/$UUID/" .env
                colorprint "DEFAULT" "${CURRENT_APP} UUID setup: done"
                colorprint "CYAN" "Save the following link somewhere to claim your earnapp node after completing the setup and after starting the apps stack: https://earnapp.com/r/sdk-node-$UUID. A new file containing this link has been created for you"
                printf "https://earnapp.com/r/sdk-node-%s\n" "$UUID" > ClaimEarnappNode.txt
                ;;

            --cid)
                colorprint "DEFAULT" "Enter your ${CURRENT_APP} CID."
                colorprint "DEFAULT" "You can find it going in your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
                read -r APP_CID
                sed -i "s/your${CURRENT_APP}CID/$APP_CID/" .env
                ;;
            --token)
                colorprint "DEFAULT" "Enter your ${CURRENT_APP} Token."
                colorprint "DEFAULT" "You can find it going in your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
                read -r APP_TOKEN
                sed -i "s^your${CURRENT_APP}Token^$APP_TOKEN^" .env
                ;;
            --customScript)
                shift
                ESCAPED_PATH="$(echo "$1" | sed 's/"/\\"/g')"
                chmod u+x "$ESCAPED_PATH"
                source "$ESCAPED_PATH"
                ;;
            *)
                colorprint "RED" "Unknown flag: $1"
                exit 1
                ;;
        esac
        shift
    done

    # App Docker image architecture adjustments
    TAG='latest'
    DKHUBRES=$(curl -L -s "https://registry.hub.docker.com/v2/repositories/$APP_IMAGE/tags" | jq --arg DKARCH "$DKARCH" '[.results[] | select(.images[].architecture == $DKARCH) | .name]')
    TAGSNUMBER=$(echo $DKHUBRES | jq '. | length')
    if [ $TAGSNUMBER -gt 0 ]; then 
        colorprint "DEFAULT" "There are $TAGSNUMBER tags supporting $DKARCH arch for this image"
        colorprint "DEFAULT" "Let's see if $TAG tag is in there"
        LATESTPRESENT=$(echo $DKHUBRES | jq --arg TAG "$TAG" '[.[] | contains($TAG)] | any')
        if [ $LATESTPRESENT == "true" ]; then 
            colorprint "DEFAULT" "OK, $TAG tag present and it supports $DKARCH arch, nothing to do"
        else 
            colorprint "DEFAULT" "$TAG tag does not support $DKARCH arch but other tags do, the newer tag supporting $DKARCH will be selected"
            NEWTAG=$(echo $DKHUBRES | jq -r '.[0]')
            sed -i "s^$APP_IMAGE:latest^$APP_IMAGE:$NEWTAG^" $DKCOM_FILENAME
        fi
    else 
        colorprint "DEFAULT" "No native image tag found for $DKARCH arch, nothing to do, emulation layer will try to run this app image anyway (make sure it has been installed)"
    fi

    read -r -p "${CURRENT_APP} configuration complete, press enter to continue to the next app"
}

fn_setupProxy() {
    if [ "$PROXY_CONF" == 'false' ]; then
        while true; do
            colorprint "YELLOW" "Do you wish to setup a proxy for the apps in this stack Y/N?"
            read -r -p "Note that if you want to run multiple instances of the same app you will need to configure different env files each in different project folders (copy the project to multiple different folders and configure them using different proxies)"$'\n' yn
            case $yn in
                [Yy]* )
                    clear
                    colorprint "YELLOW" "Proxy setup started."
                    readonly RANDOM_VALUE=$RANDOM
                    colorprint "DEFAULT" "Insert the designed proxy to use. Eg: protocol://proxyUsername:proxyPassword@proxy_url:proxy_port or just protocol://proxy_url:proxy_port if auth is not needed"
                    read -r STACK_PROXY
                    colorprint "DEFAULT" "Ok, $STACK_PROXY will be used as proxy for all apps in this stack"
                    read -r -p "Press enter to continue"
                    PROXY_CONF='true'
                    # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                    sed -i "s^COMPOSE_PROJECT_NAME=money4band^COMPOSE_PROJECT_NAME=money4band_$RANDOM_VALUE^" .env
                    sed -i "s^DEVICE_NAME=$DEVICE_NAME^DEVICE_NAME=$DEVICE_NAME$RANDOM_VALUE^" .env
                    # uncomment .env and compose file
                    sed -i "s^# PROXY_STACK=^PROXY_STACK=$PROXY_STACK^" .env
                    sed -i "s^#PROXY_ENABLE^^" $DKCOM_FILENAME
                    sed -i "s^#PROXY_ENABLE^^" $DKCOM_FILENAME
                    sed -i "s^# network_mode^network_mode^" $DKCOM_FILENAME
                    break
                    ;;
                [Nn]* )
                    colorprint "BLUE" "Ok, no proxy added to configuration."
                    break
                    ;;
                * ) colorprint "RED" "Please answer yes or no." ;;
            esac
        done
    fi
}

fn_setupEnv(){
    while true; do
        colorprint "YELLOW" "Do you wish to proceed with the .env file guided setup Y/N? (This will also adapt the $DKCOM_FILENAME file accordingly)"
        read -r yn
        case $yn in
            [Yy]* ) 
                clear
                break
                ;;
            [Nn]* ) 
                colorprint "BLUE" ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no."
        esac
    done
    if ! grep -q "DEVICE_NAME=yourDeviceName" .env  ; then 
        colorprint "DEFAULT" "The current .env file appears to have already been modified. A fresh version will be downloaded and used.";
        curl -fsSL $ENV_SRC -o ".env"
        curl -fsSL $DKCOM_SRC -o "$DKCOM_FILENAME"
    fi
    colorprint "YELLOW" "beginnning env file guided setup"$'\n'
    CURRENT_APP='';
    colorprint "YELLOW" "PLEASE ENTER A NAME FOR YOUR DEVICE:"
    read -r DEVICE_NAME
    sed -i "s/yourDeviceName/$DEVICE_NAME/" .env
    clear ;
    fn_setupProxy ;
    clear ;

    # if not installed, install JQ as it will be used during app config
    colorprint "YELLOW" "Now a small useful package named JQ used to manage JSON files will be installed if not already present"$'\n'
    colorprint "YELLOW" "Please, if prompted, enter your sudo password to proceed"$'\n'
    sudo apt install jq -y
    clear;

    colorprint "YELLOW" "PLEASE REGISTER ON THE PLATFORMS USING THE FOLLOWING LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
    colorprint "GREEN" "Use CTRL+Click to open links or copy them:"

    # EarnApp app env setup
    CURRENT_APP='EARNAPP';
    colorprint "CYAN" "Go to $EARNAPP_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$EARNAPP_IMG" --uuid "$DEVICE_NAME"

    # HoneyGain app env setup
    clear;
    CURRENT_APP='HONEYGAIN';
    colorprint "CYAN" "Go to $HONEYGAIN_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$HONEYGAIN_IMG" --email --password

    # IProyalPawns app env setup
    clear;
    CURRENT_APP='IPROYALPAWNS'
    colorprint "CYAN" "Go to $IPROYALPAWNS_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$IPROYALPAWNS_IMG" --email --password

    # Peer2Profit app env setup
    clear;
    CURRENT_APP='PEER2PROFIT'
    colorprint "CYAN" "Go to $PEER2PROFIT_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$PEER2PROFIT_IMG" --email

    # PacketStream app env setup
    clear;
    CURRENT_APP='PACKETSTREAM'
    colorprint "CYAN" "Go to $PACKETSTREAM_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$PACKETSTREAM_IMG" --cid

    # TraffMonetizer app env setup
    clear;
    CURRENT_APP='TRAFFMONETIZER'
    colorprint "CYAN" "Go to $TRAFFMONETIZER_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$TRAFFMONETIZER_IMG" --token

    # Repocket app env setup
    clear;
    CURRENT_APP='REPOCKET'
    colorprint "CYAN" "Go to $REPOCKET_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$REPOCKET_IMG" --email --apikey

    # Proxyrack/pop app env setup
    clear;
    CURRENT_APP='PROXYRACK'
    colorprint "CYAN" "Go to $PROXYRACK_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$PROXYRACK_IMG" --apikey

    # Proxylite app env setup
    clear;
    CURRENT_APP='PROXYLITE'
    colorprint "CYAN" "Go to $PROXYLITE_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$PROXYLITE_IMG" --userid

    # Bitping app env setup
    clear;
    CURRENT_APP='BITPING'
    colorprint "CYAN" "Go to $BITPING_LNK and register"
    read -r -p "When done, press enter to continue"$'\n'
    fn_setupApp --app "${CURRENT_APP}" --image "$BITPING_IMG" --customScript "$SCRIPTS_DIR/bitpingSetup.sh"

    # Notifications setup
    clear;
    read -r -p "Do you wish to setup notifications about apps images updates (Yes to receive notifications and apply updates, No to just silently apply updates) Y/N?  " yn
    case $yn in
        [Yy]* ) fn_setupNotifications;;
        [Nn]* ) colorprint "YELLOW" "Noted: all updates will be applied automatically and silently";;
        * ) colorprint "RED" "Please answer yes or no."; fn_setupNotifications;;
    esac

    colorprint "GREEN" "env file setup complete.";
    read -n 1 -s -r -p "Press any key to go back to the menu"$'\n'

    mainmenu;
}

fn_startStack(){
    while true; do
        colorprint "YELLOW" "This menu item will launch all the apps using the configured .env file and the $DKCOM_FILENAME file (Docker must be already installed and running)"
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose up -d; then
                    colorprint "GREEN" "All Apps started. You can visit the web dashboard on http://localhost:8081/. If not already done, use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details."
                else
                    colorprint "RED" "Error starting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                colorprint "BLUE" "Docker stack startup canceled."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no.";;
        esac
    done
}


fn_stopStack(){
    while true; do
        colorprint "YELLOW" "This menu item will stop all the apps and delete the docker stack previously created using the configured .env file and the $DKCOM_FILENAME file."
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose down; then
                    colorprint "GREEN" "All Apps stopped and stack deleted."
                else
                    colorprint "RED" "Error stopping and deleting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                colorprint "BLUE" "Docker stack removal canceled."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) 
                colorprint "RED" "Please answer yes or no.";;
        esac
    done
}


fn_resetEnv(){
    while true; do
        colorprint "RED" "Now a fresh env file will be downloaded and will need to be configured to be used again"
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if curl -fsSL $ENV_SRC -o ".env"; then
                    colorprint "GREEN" ".env file resetted, remember to reconfigure it"
                else
                    colorprint "RED" "Error resetting .env file. Please check your internet connection and try again."
                fi
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            [Nn]* ) 
                colorprint "BLUE" ".env file reset canceled. The file is left as it is"
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no.";;
        esac
    done
}

fn_resetDockerCompose(){
    while true; do
        colorprint "RED" "Now a fresh $DKCOM_FILENAME file will be downloaded"
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if curl -fsSL $DKCOM_SRC -o "$DKCOM_FILENAME"; then
                    colorprint "GREEN" "$DKCOM_FILENAME file resetted, remember to reconfigure it if needed"
                else
                    colorprint "RED" "Error resetting $DKCOM_FILENAME file. Please check your internet connection and try again."
                fi
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            [Nn]* ) 
                colorprint "BLUE" "$DKCOM_FILENAME file reset canceled. The file is left as it is"
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no.";;
        esac
    done
}



### Main Menu ##
mainmenu() {
    clear
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP"$'\n'"--------------------------------- "$'\n'
    
    # Detect OS architecture
    ARCH=$(uname -m)
    if [ "$ARCH" == "x86_64" ]; then 
        DKARCH='amd64'
    elif [ "$ARCH" == "aarch64" ]; then
        DKARCH='arm64'
    else 
        DKARCH=$ARCH
    fi
    colorprint "DEFAULT" "Detected OS architecture $ARCH"$'\n'"Docker $DKARCH image architecture will be used if the app's image permits it"$'\n'"--------------------------------- "$'\n'
    
    PS3="Select an option and press Enter "$'\n'
    options=("Show apps' links to register or go to dashboard" "Install Docker" "Setup .env file" "Start apps stack" "Stop apps stack" "Reset .env File" "Reset $DKCOM_FILENAME file" "Quit")

    select option in "${options[@]}"
    do
        case $REPLY in
            1) clear; fn_showLinks; break;;
            2) clear; fn_dockerInstall; break;;
            3) clear; fn_setupEnv; break;;
            4) clear; fn_startStack; break;;
            5) clear; fn_stopStack; break;;
            6) clear; fn_resetEnv; break;;
            7) clear; fn_resetDockerCompose; break;;
            ${#options[@]}) clear; fn_bye; break;;
            *) clear; fn_unknown; break;;
        esac
    done
}

### Startup ##
while true; do
    mainmenu
done