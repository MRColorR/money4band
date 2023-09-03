#!/bin/bash

### Variables and constants ###
## Script variables ##
# Script version #
readonly SCRIPT_VERSION="2.1.0" # used for checking updates
# Script name #
readonly SCRIPT_NAME=$(basename "$0") # save the script name in a variable not the full path
# Script url for update #
readonly UPDATE_SCRIPT_URL="https://raw.githubusercontent.com/MRColorR/money4band/main/${SCRIPT_NAME}"
# Script debug log file #
readonly DEBUG_LOG="debug_${SCRIPT_NAME}.log"

## Colors ##
# Colors used inside the script #
ESC=$(printf '\033') DEFAULT="${ESC}[0m"
declare -A colors=( [GREEN]="${ESC}[32m" [BLUE]="${ESC}[34m" [RED]="${ESC}[31m" [YELLOW]="${ESC}[33m" [MAGENTA]="${ESC}[35m" [CYAN]="${ESC}[36m" [PURPLE]="${ESC}[35;1m" [DEFAULT]="${ESC}[0m")
# Color functions #
colorprint() { printf "${colors[$1]}%s${DEFAULT}\n" "$2"; }
# Function to print an error message and write it to the debug log file #
errorprint_and_log() {
    printf "%s\n" "$1" >&2
    debug "[ERROR]: $1"
}
# Function to print criticals errors that will stop the script and make it exit with error code 1 #
fn_fail() {
    errorprint_and_log "$1"
    read -p "Press Enter to exit..."
    exit 1
}
# Function to manage unexpected choices of flags #
fn_unknown() { colorprint "RED" "Unknown choice $REPLY, please choose a valid option"; }
# Function to exit the script gracefully #
fn_bye(){
    colorprint "GREEN" "Share this app with your friends thank you!"
    colorprint "GREEN" "Exiting the application...Bye!Bye!"
    debug "Exiting the application...Bye!Bye!"
    exit 0
}

## Env file related constants and variables ##
# .env file prototype link #
readonly ENV_SRC='https://github.com/MRColorR/money4band/raw/main/.env'
# Env file default #
DEVICE_NAME='yourDeviceName'
# Proxy config #
PROXY_CONF='false'
STACK_PROXY=''

## Docker compose related constants and variables ##
# docker compose yaml file name #
readonly DKCOM_FILENAME="docker-compose.yaml"
# docker compose yaml prototype file link #
readonly DKCOM_SRC="https://github.com/MRColorR/money4band/raw/main/$DKCOM_FILENAME"
# Architecture default #
ARCH='unknown'
DKARCH='unknown'
# OS default #
OS_TYPE='unknown'

### Resources, Scripts and Files folders ###
readonly RESOURCES_DIR="$PWD/.resources"
readonly CONFIG_DIR="$RESOURCES_DIR/.www/.configs"
readonly SCRIPTS_DIR="$RESOURCES_DIR/.scripts"
readonly FILES_DIR="$RESOURCES_DIR/.files"

### Log, Update and Utility functions ###
## Enable or disable logging using debug mode ##
# Check if the first argument is -d or --debug if so, enable debug mode
if [[ $1 == '-d' || $1 == '--debug' ]]; then
    DEBUG=true
    # Remove the first argument so it doesn't interfere with the rest of the script
    shift
fi

# Function to write debug messages to the debug log file #
debug() {
    if [ $DEBUG ]; then
        echo "[DEBUG] $@" >> "$DEBUG_LOG"
    fi
}
# Function to print an info message that will be also logged to the debug log file #
print_and_log() {
    local color="$1"
    local message="$2"
    colorprint "$color" "$message"
    debug "$message"
}

## Utility functions ##
# Function to check the OS type #
detect_os_type() {
    debug "Checking OS type..."
    unameOut="$(uname -s)"
    case "${unameOut}" in
        Linux*)     OS_TYPE="Linux" ; echo "Linux" ;;
        Darwin*)    OS_TYPE="Mac" ; echo "Mac" ;;
        CYGWIN*)    OS_TYPE="Cygwin" ; echo "Cygwin" ;;
        MINGW*)     OS_TYPE="MinGw" ; echo "MinGw" ;;
        MSYS*)      OS_TYPE="Msys" ; echo "Msys" ;;
        FreeBSD*)   OS_TYPE="FreeBSD" ; echo "FreeBSD" ;;
        *)          OS_TYPE="unknown" echo "unknown" ;;
    esac
    debug "OS type detected: $OS_TYPE"
}
# Function to detect OS architecture and set the relative docker architecture #
detect_architecture() {
    debug "Detecting system architecture..."
    ARCH=$(uname -m)
    if [ "$ARCH" == "x86_64" ]; then 
        DKARCH='amd64'
    elif [ "$ARCH" == "aarch64" ]; then
        DKARCH='arm64'
    else 
        DKARCH=$ARCH
    fi
    debug "System architecture detected: $ARCH, Docker architecture has been set to $DKARCH"
}

# Function to check if dependencies packages are installed and install them if not #
fn_install_packages() {
    debug "Checking if required packages are installed..."
    REQUIRED_PACKAGES=("$@")

    if [[ "$OS_TYPE" == "Linux" ]]; then
        if command -v apt &> /dev/null ; then
            PKG_MANAGER="apt"
            PKG_CHECK="dpkg -l"
            PKG_INSTALL="sudo apt install -y"
        elif command -v yum &> /dev/null ; then
            PKG_MANAGER="yum"
            PKG_CHECK="rpm -q"
            PKG_INSTALL="sudo yum install -y"
        elif command -v dnf &> /dev/null ; then
            PKG_MANAGER="dnf"
            PKG_CHECK="rpm -q"
            PKG_INSTALL="sudo dnf install -y"
        elif command -v pacman &> /dev/null ; then
            PKG_MANAGER="pacman"
            PKG_CHECK="pacman -Q"
            PKG_INSTALL="sudo pacman -S --noconfirm"
        elif command -v zypper &> /dev/null ; then
            PKG_MANAGER="zypper"
            PKG_CHECK="rpm -q"
            PKG_INSTALL="sudo zypper install -y"
        elif command -v emerge &> /dev/null ; then
            PKG_MANAGER="emerge"
            PKG_CHECK="qlist -I"
            PKG_INSTALL="sudo emerge --ask n"
        else
            print_and_log "RED" "Your package manager has not been recognized. Please install the following packages manually: ${REQUIRED_PACKAGES[*]}"
            return
        fi
        debug "Detected package manager: $PKG_MANAGER"
        for package in "${REQUIRED_PACKAGES[@]}"
        do
            if ! $PKG_CHECK | grep -q "^ii  $package"; then
                print_and_log "DEFAULT" "$package is not installed. Trying to install now..."
                if ! $PKG_INSTALL $package; then
                    print_and_log "RED" "Failed to install $package. Please install it manually."
                fi
            else
                print_and_log "DEFAULT" "$package is already installed."
            fi
        done
    elif [[ "$OS_TYPE" == "macOS" ]]; then
        if ! command -v brew &> /dev/null; then
            print_and_log "DEFAULT" "Homebrew is not installed. Trying to install now..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        for package in "${REQUIRED_PACKAGES[@]}"
        do
            if ! brew list --versions $package > /dev/null; then
                print_and_log "DEFAULT" "$package is not installed. Trying to install now..."
                if ! brew install $package; then
                    print_and_log "RED" "Failed to install $package. Please install it manually."
                fi
            else
                print_and_log "DEFAULT" "$package is already installed."
            fi
        done
    else
        print_and_log "RED" "Your operating system has not been recognized. Please install the required packages manually."
    fi
    debug "Required packages installed."
}

## Multiarch emulation service installer function ##
fn_addDockerBinfmtSVC() {
    debug "Installing multiarch emulation service..."
    # Check if the service file exists
    debug "Checking if the service already exists..."
    if [ -f "/etc/systemd/system/docker.binfmt.service" ]; then
        # Compare the contents of the existing service file with the one in $FILES_DIR
        debug "Service already exists, comparing contents..."
        if ! cmp -s "/etc/systemd/system/docker.binfmt.service" "$FILES_DIR/docker.binfmt.service"; then
            # The contents are different, overwrite the existing service file
            debug "Service contents are different, overwriting the file of the existing service..."
            if ! sudo cp "$FILES_DIR/docker.binfmt.service" /etc/systemd/system; then
                fn_fail "Failed to copy service file. Please check your permissions and the file path."
            fi
        fi

        # Check if the service is enabled
        debug "Checking if the service is enabled..."
        if [ -d "/etc/systemd/system" ]; then
            # Systemd-based distributions
            debug "Systemd-based distribution detected, checking if the service is enabled..."
            if ! systemctl is-enabled --quiet docker.binfmt.service; then
                # Enable the service
                debug "Service is not enabled, enabling it..."
                if ! sudo systemctl enable docker.binfmt.service; then
                    fn_fail "Failed to enable docker.binfmt.service. Please check your system config and try to enable the exixting service manually. Then run the script again."
                fi
            fi
        fi
    elif [ -f "/etc/init.d/docker.binfmt" ]; then
        debug "SysV init-based distribution detected, checking if the service is enabled..."
        # Compare the contents of the existing service file with the one in $FILES_DIR
        debug "Service already exists, comparing contents..."
        if ! cmp -s "/etc/init.d/docker.binfmt" "$FILES_DIR/docker.binfmt.service"; then
            # The contents are different, overwrite the existing service file
            debug "Service contents are different, overwriting the file of the existing service..."
            if ! sudo cp "$FILES_DIR/docker.binfmt.service" /etc/init.d/docker.binfmt; then
                fn_fail "Failed to copy service file. Please check your permissions and the file path."
            fi
            sudo chmod +x /etc/init.d/docker.binfmt
        fi

        # Check if the service is enabled
        debug "Checking if the service is enabled..."
        if [ -d "/etc/init.d" ]; then
            # SysV init-based distributions
            debug "SysV init-based distribution detected, checking if the service is enabled..."
            if ! grep -q "docker.binfmt" /etc/rc.local; then
                # Enable the service
                debug "Service is not enabled, enabling it..."
                sudo update-rc.d docker.binfmt defaults
            fi
        fi
    else
        # The service file does not exist, copy it to the appropriate location
        debug "Service does not already exists, copying it to the appropriate location..."
        if [ -d "/etc/systemd/system" ]; then
            # Systemd-based distributions
            debug "Systemd-based distribution detected, copying service file..."
            sudo cp "$FILES_DIR/docker.binfmt.service" /etc/systemd/system
            sudo systemctl enable docker.binfmt.service
            debug "Service file copied and enabled."
        elif [ -d "/etc/init.d" ]; then
            # SysV init-based distributions
            debug "SysV init-based distribution detected, copying service file..."
            sudo cp "$FILES_DIR/docker.binfmt.service" /etc/init.d/docker.binfmt
            sudo chmod +x /etc/init.d/docker.binfmt
            sudo update-rc.d docker.binfmt defaults
            debug "Service file copied and enabled."
        else
            # Fallback option (handle unsupported systems)
            fn_fail "Warning: I can not find a supported init system. You will have to manually enable the binfmt service. Then restart the script."
        fi
    fi

    # Start the service
    debug "Starting the service..."
    if [ -d "/etc/systemd/system" ]; then
        # Systemd-based distributions
        debug "Systemd-based distribution detected, starting the service..."
        if ! sudo systemctl start docker.binfmt.service; then
            fn_fail "Failed to start docker.binfmt.service. Please check your system config and try to start the exixting service manually. Then run the script again."
        fi
        debug "Service started."
    elif [ -d "/etc/init.d" ]; then
        # SysV init-based distributions
        debug "SysV init-based distribution detected, starting the service..."
        if ! sudo service docker.binfmt start; then
            fn_fail "Failed to start docker.binfmt.service. Please check your system config and try to start the exixting service manually. Then run the script again."
        fi
        debug "Service started."
    fi
}

### Sub-menu Functions ###
fn_showLinks() {
    debug "Showing apps links"
    clear
    colorprint "GREEN" "Use CTRL+Click to open links or copy them:"
    jq -r '.apps | to_entries[] | "\(.key+1) \(.value.name) | \(.value.link)"' "$CONFIG_DIR/config.json" |
    while read -r line; do
        colorprint "CYAN" "$line"
    done
    read -r -p "Press Enter to go back to mainmenu"
    debug "Links shown, going back to mainmenu"
}

## Docker checker and installer function ##
# Check if docker is installed and if not then it tries to install it automatically
fn_dockerInstall() {
    debug "DockerInstall function started"
    clear
    colorprint "YELLOW" "This menu item will launch a script that will attempt to install Docker"
    colorprint "YELLOW" "Use it only if you do not know how to perform the manual Docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some rare cases and depending on the distros may fail to install Docker correctly."
    
    while true; do
        read -r -p "Do you wish to proceed with the Docker automatic installation Y/N? " yn
        case $yn in
            [Yy]* )
                debug "User decided to install Docker through the script. Checking if Docker is already installed."
                if docker --version >/dev/null 2>&1; then
                    debug "Docker is already installed. Asking user if he wants to continue with the installation anyway."
                    while true; do
                        colorprint "YELLOW" "It seems that Docker is already installed. Do you want to continue with the installation anyway? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                debug "User decided to continue with the Docker re-install anyway."
                                break
                                ;;
                            [Nn]* )
                                debug "User decided to abort the Docker re-install."
                                read -r -p "Press Enter to go back to mainmenu"
                                return
                                ;;
                            * ) 
                                colorprint "RED" "Please answer yes or no."
                                continue
                                ;;
                        esac
                    done
                fi
                print_and_log "DEFAULT" "Proceeding with Docker installation. Please provide your sudo password if prompted."
                if curl -fsSL https://get.docker.com -o "$SCRIPTS_DIR/get-docker.sh"; then
                    if sudo sh "$SCRIPTS_DIR/get-docker.sh"; then
                        print_and_log "GREEN" "Docker installed"
                        read -r -p "Press Enter to go back to mainmenu"
                    else
                        errorprint_and_log "Failed to install Docker automatically. Please try to install Docker manually by following the instructions on Docker website."
                        read -r -p "Press Enter to go back to mainmenu"
                    fi
                else
                    errorprint_and_log "Failed to download the Docker installation script."
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

## Notifications setup function ##
# This function will setup notifications about containers updates using shoutrrr
fn_setupNotifications() {
    debug "SetupNotifications function started"
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
    while true; do
        colorprint "YELLOW" "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"
        read -r SHOUTRRR_URL
        if [[ "$SHOUTRRR_URL" =~ ^[a-zA-Z]+:// ]]; then
            sed -i "s~# SHOUTRRR_URL=yourApp:yourToken@yourWebHook~SHOUTRRR_URL=$SHOUTRRR_URL~" .env
            sed -i "s~# - WATCHTOWER_NOTIFICATIONS=shoutrrr~  - WATCHTOWER_NOTIFICATIONS=shoutrrr~" "$DKCOM_FILENAME"
            sed -i "s~# - WATCHTOWER_NOTIFICATION_URL~  - WATCHTOWER_NOTIFICATION_URL~" "$DKCOM_FILENAME"
            sed -i "s~# - WATCHTOWER_NOTIFICATIONS_HOSTNAME~  - WATCHTOWER_NOTIFICATIONS_HOSTNAME~" "$DKCOM_FILENAME"
            colorprint "DEFAULT" "Notifications setup complete. If the link is correct, you will receive a notification for each update made on the app container images."
            read -r -p "Press enter to continue."
            break
        else
            colorprint "RED" "Invalid link format. Please make sure to use the correct format."
            while true; do
                colorprint "YELLOW" "Do you wish to try again or leave the notifications disabled and continue with the setup script? (Yes to try again, No to continue without notifications) Y/N?"
                read -r yn
                case $yn in
                    [Yy]* ) break;;
                    [Nn]* ) return;;
                    * ) colorprint "RED" "Please answer yes or no.";;
                esac
            done
        fi
    done
    clear
    debug "SetupNotifications function ended"
}


fn_setupApp() {
    debug "SetupApp function started"
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --app)
                CURRENT_APP="$2"
                sed -i "s^#${CURRENT_APP}_ENABLE^^" $DKCOM_FILENAME
                shift
                ;;
            --image)
                APP_IMAGE="$2"
                shift
                ;;
            --email)
                while true; do
                    colorprint "GREEN" "Enter your ${CURRENT_APP} Email:"
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
                    colorprint "GREEN" "Enter your ${CURRENT_APP} Password:"
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
                colorprint "GREEN" "Enter your ${CURRENT_APP} APIKey:"
                read -r APP_APIKEY
                sed -i "s^your${CURRENT_APP}APIKey^$APP_APIKEY^" .env
                ;;
            --userid)
                colorprint "DEFAULT" "Find your UserID inside your ${CURRENT_APP} dashboard/profile."
                colorprint "GREEN" "Enter your ${CURRENT_APP} UserID:"
                read -r APP_USERID
                sed -i "s/your${CURRENT_APP}UserID/$APP_USERID/" .env
                ;;
            --uuid)
                colorprint "DEFAULT" "Starting UUID generation/import for ${CURRENT_APP}"
                shift
                SALT="${DEVICE_NAME}""${RANDOM}"
                UUID="$(echo -n "$SALT" | md5sum | cut -c1-32)"
                while true; do
                    colorprint "YELLOW" "Do you want to use a previously registered sdk-node-uuid for ${CURRENT_APP}? (Y/N)"
                    read -r USE_EXISTING_UUID
                    case $USE_EXISTING_UUID in
                        [Yy]* )
                            while true; do
                                colorprint "GREEN" "Please enter the 32 char long alphanumeric part of the existing sdk-node-uuid for ${CURRENT_APP}:"
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
                colorprint "BLUE" "Save the following link somewhere to claim your ${CURRENT_APP} node after completing the setup and starting the apps stack: https://earnapp.com/r/sdk-node-$UUID."
                colorprint "DEFAULT" "A new file containing this link has been created for you in the current directory"
                printf "https://earnapp.com/r/sdk-node-%s\n" "$UUID" > ClaimEarnappNode.txt
                ;;

            --cid)
                colorprint "DEFAULT" "Find your CID, you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
                colorprint "GREEN" "Enter your ${CURRENT_APP} CID."
                read -r APP_CID
                sed -i "s/your${CURRENT_APP}CID/$APP_CID/" .env
                ;;
            --token)
                colorprint "DEFAULT" "Find your token, you can fetch it from your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
                colorprint "GREEN" "Enter your ${CURRENT_APP} Token."
                read -r APP_TOKEN
                sed -i "s^your${CURRENT_APP}Token^$APP_TOKEN^" .env
                ;;
            --customScript)
                shift
                SCRIPT_NAME="$1.sh"
                SCRIPT_PATH="$SCRIPTS_DIR/$SCRIPT_NAME"
                ESCAPED_PATH="$(echo "$SCRIPT_PATH" | sed 's/"/\\"/g')"
                if [[ -f "$SCRIPT_PATH" ]]; then
                    chmod +x "$ESCAPED_PATH"
                    colorprint "DEFAULT" "Executing custom script: $SCRIPT_NAME"
                    source "$ESCAPED_PATH"
                else
                    colorprint "RED" "Custom script '$SCRIPT_NAME' not found in the scripts directory."
                fi
                ;;
            --manual)
                colorprint "DEFAULT" "${CURRENT_APP} requires further manual configuration."
                colorprint "DEFAULT" "Please after completing this automated setup follow the manual steps described on the app's website."
                ;;
            *)
                colorprint "RED" "Unknown flag: $1"
                exit 1
                ;;
        esac
        shift
    done
    debug "Finished parsing arguments of setupApp function for $CURRENT_APP app"

    # App Docker image architecture adjustments
    debug "Starting Docker image architecture adjustments for $CURRENT_APP app"
    TAG='latest'
    DKHUBRES=$(curl -L -s "https://registry.hub.docker.com/v2/repositories/$APP_IMAGE/tags" | jq --arg DKARCH "$DKARCH" '[.results[] | select(.images[].architecture == $DKARCH) | .name]')
    TAGSNUMBER=$(echo $DKHUBRES | jq '. | length')
    if [ $TAGSNUMBER -gt 0 ]; then 
        colorprint "DEFAULT" "There are $TAGSNUMBER tags supporting $DKARCH arch for this image"
        colorprint "DEFAULT" "Let's see if $TAG tag is in there"
        LATESTPRESENT=$(echo $DKHUBRES | jq --arg TAG "$TAG" '[.[] | contains($TAG)] | any')
        if [ $LATESTPRESENT == "true" ]; then 
            colorprint "GREEN" "OK, $TAG tag present and it supports $DKARCH arch, nothing to do"
        else 
            colorprint "YELLOW" "$TAG tag does not support $DKARCH arch but other tags do, the newer tag supporting $DKARCH will be selected"
            NEWTAG=$(echo $DKHUBRES | jq -r '.[0]')
            sed -i "s^$APP_IMAGE:latest^$APP_IMAGE:$NEWTAG^" $DKCOM_FILENAME
        fi
    else 
        colorprint "YELLOW" "No native image tag found for $DKARCH arch, emulation layer will try to run this app image anyway."
        colorprint "DEFAULT" "If an emulation layer is not already installed, the script will try to install it now. Please provide your sudo password if prompted."
        #fn_install_packages qemu binfmt-support qemu-user-static
        fn_addDockerBinfmtSVC
    fi
    debug "Finished Docker image architecture adjustments for $CURRENT_APP app"

    read -r -p "${CURRENT_APP} configuration complete, press enter to continue to the next app"
    debug "Finished setupApp function for $CURRENT_APP app"
}

fn_setupProxy() {
    debug "Starting setupProxy function"
    if [ "$PROXY_CONF" == 'false' ]; then
        while true; do
            colorprint "YELLOW" "Do you wish to setup a proxy for the apps in this stack Y/N?"
            colorprint "DEFAULT" "Note that if you want to run multiple instances of the same app you will need to configure different env files each in different project folders (copy the project to multiple different folders and configure them using different proxies)"$'\n'
            read -r yn
            case $yn in
                [Yy]* )
                    clear
                    debug "User chose to setup a proxy"
                    colorprint "YELLOW" "Proxy setup started."
                    readonly RANDOM_VALUE=$RANDOM
                    colorprint "GREEN" "Insert the designed proxy to use. Eg: protocol://proxyUsername:proxyPassword@proxy_url:proxy_port or just protocol://proxy_url:proxy_port if auth is not needed"
                    read -r STACK_PROXY
                    colorprint "DEFAULT" "Ok, $STACK_PROXY will be used as proxy for all apps in this stack"
                    read -r -p "Press enter to continue"
                    PROXY_CONF='true'
                    # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                    sed -i "s^COMPOSE_PROJECT_NAME=money4band^COMPOSE_PROJECT_NAME=money4band_$RANDOM_VALUE^" .env
                    sed -i "s^DEVICE_NAME=${DEVICE_NAME}^DEVICE_NAME=${DEVICE_NAME}$RANDOM_VALUE^" .env
                    # uncomment .env and compose file
                    sed -i "s^# STACK_PROXY=^STACK_PROXY=$STACK_PROXY^" .env
                    sed -i "s^#PROXY_ENABLE^^" $DKCOM_FILENAME
                    sed -i "s^# network_mode^network_mode^" $DKCOM_FILENAME
                    debug "Proxy setup finished"
                    break
                    ;;
                [Nn]* )
                    debug "User chose not to setup a proxy"
                    colorprint "BLUE" "Ok, no proxy added to configuration."
                    sleep 1
                    break
                    ;;
                * ) colorprint "RED" "Please answer yes or no." ;;
            esac
        done
    fi
}

fn_setupEnv(){
    local app_type="$1"  # Accept the type of apps as an argument
    debug "Starting setupEnv function for $app_type"

    # Check if .env file is already configured
    ENV_CONFIGURATION_STATUS=$(grep -oP 'ENV_CONFIGURATION_STATUS=\K[^#]+' .env)
    debug "Current ENV_CONFIGURATION_STATUS: $ENV_CONFIGURATION_STATUS"
    NOTIFICATIONS_CONFIGURATION_STATUS=$(grep -oP 'NOTIFICATIONS_CONFIGURATION_STATUS=\K[^#]+' .env)
    debug "Current NOTIFICATIONS_CONFIGURATION_STATUS: $NOTIFICATIONS_CONFIGURATION_STATUS"

    while true; do
        colorprint "YELLOW" "Do you wish to proceed with the .env file guided setup Y/N? (This will also adapt the $DKCOM_FILENAME file accordingly)"
        read -r yn
        case $yn in
            [Yy]* ) 
                clear
                debug "User chose to proceed with the .env file guided setup"

                if [ "$ENV_CONFIGURATION_STATUS" == "1" ] && [ "$app_type" == "apps" ]; then
                    colorprint "YELLOW" "The current .env file appears to have already been configured. Do you want to reset it? (Y/N)"
                    read -r yn
                    case $yn in
                        [Yy]* )
                            print_and_log "DEFAULT" "Downloading a fresh .env file.";
                            curl -fsSL $ENV_SRC -o ".env"
                            curl -fsSL $DKCOM_SRC -o "$DKCOM_FILENAME"
                            sed -i 's/ENV_CONFIGURATION_STATUS=1/ENV_CONFIGURATION_STATUS=0/' .env
                            clear
                            ;;
                        [Nn]* )
                            print_and_log "BLUE" "Keeping the existing .env file."
                            ;;
                        * )
                            colorprint "RED" "Invalid input. Please answer yes or no."
                            return 1
                            ;;
                    esac
                elif [ "$ENV_CONFIGURATION_STATUS" == "1" ] && [ "$app_type" != "apps" ]; then
                    print_and_log "BLUE" "Proceeding with $app_type setup without resetting .env file."
                fi

                colorprint "YELLOW" "beginnning env file guided setup"$'\n'
                CURRENT_APP='';
                colorprint "YELLOW" "PLEASE ENTER A NAME FOR YOUR DEVICE:"
                read -r DEVICE_NAME
                sed -i "s/yourDeviceName/${DEVICE_NAME}/" .env
                clear ;
                fn_setupProxy ;
                clear ;
                debug " Loading $app_type from config.json..."
                apps=$(jq -c ".${app_type}[]" "$CONFIG_DIR/config.json")
                debug " $app_type loaded from config.json"

                for app in $apps; do
                    clear
                    colorprint "YELLOW" "PLEASE REGISTER ON THE PLATFORMS USING THE FOLLOWING LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
                    colorprint "GREEN" "Use CTRL+Click to open links or copy them:"
                    name=$(jq -r '.name' <<< "$app")
                    link=$(jq -r '.link' <<< "$app")
                    image=$(jq -r '.image' <<< "$app")
                    flags=$(jq -r '.flags[]' <<< "$app")

                    CURRENT_APP=$(echo "$name" | tr '[:lower:]' '[:upper:]')
                    
                    while true; do
                        colorprint "YELLOW" "Do you wish to enable and use ${CURRENT_APP}? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                colorprint "CYAN" "Go to ${name} ${link} and register"
                                read -r -p "When done, press enter to continue"$'\n'
                                # Pass the flags string to the function
                                fn_setupApp --app "${CURRENT_APP}" --image "$image" ${flags}
                                clear
                                break
                                ;;
                            [Nn]* )
                                colorprint "BLUE" "${CURRENT_APP} setup will be skipped."
                                read -r -p "Press enter to continue to the next app"
                                break
                                ;;
                            * ) colorprint "RED" "Please answer yes or no." ;;
                        esac
                    done
                done

                # Notifications setup
                clear;
                if [ "$NOTIFICATIONS_CONFIGURATION_STATUS" == "1" ]; then
                    print_and_log "BLUE" "Notifications are already set up. Skipping notifications setup. Reset the .env file and do a new complete setup to set up different notification settings."
                else
                    debug "Asking user if they want to setup notifications"
                    while true; do
                        colorprint "YELLOW" "Do you wish to setup notifications about apps images updates (Yes to receive notifications and apply updates, No to just silently apply updates) Y/N?"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                debug "User chose to setup notifications"
                                fn_setupNotifications;
                                break;;
                            [Nn]* )
                                debug "User chose not to setup notifications"
                                colorprint "BLUE" "Noted: all updates will be applied automatically and silently";
                                break;;
                            * ) colorprint "RED" "Invalid input. Please answer yes or no.";;
                        esac
                    done
                fi

                sed -i 's/ENV_CONFIGURATION_STATUS=0/ENV_CONFIGURATION_STATUS=1/' .env
                print_and_log "GREEN" "env file setup complete.";
                read -n 1 -s -r -p "Press any key to go back to the menu"$'\n'
                break
                ;;
            [Nn]* )
                debug "User chose not to proceed with the .env file guided setup"
                colorprint "BLUE" ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no."
        esac
    done
}

fn_setupApps(){
    fn_setupEnv "apps"  # Call fn_setupEnv with "apps"
}

fn_setupExtraApps(){
    fn_setupEnv "extra-apps"  # Call fn_setupEnv with "extra_apps"
}

fn_startStack(){
    clear
    debug "Starting startStack function"
    while true; do
        colorprint "YELLOW" "This menu item will launch all the apps using the configured .env file and the $DKCOM_FILENAME file (Docker must be already installed and running)"
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose up -d; then
                    print_and_log "GREEN" "All Apps started."
                    colorprint "GREEN" "You can visit the web dashboard on http://localhost:8081/. If not already done, use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details."
                else
                    errorprint_and_log "RED" "Error starting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                debug "User chose not to start the stack"
                colorprint "BLUE" "Docker stack startup canceled."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no.";;
        esac
    done
    debug "StartStack function ended"
}


fn_stopStack(){
    clear
    debug "Starting stopStack function"
    while true; do
        colorprint "YELLOW" "This menu item will stop all the apps and delete the docker stack previously created using the configured .env file and the $DKCOM_FILENAME file."
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose down; then
                    print_and_log "GREEN" "All Apps stopped and stack deleted."
                else
                    errorprint_and_log "RED" "Error stopping and deleting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                debug "User chose not to stop the stack"
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
    clear
    debug "Starting resetEnv function"
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
    debug "resetEnv function ended"
}

fn_resetDockerCompose(){
    clear
    debug "Starting resetDockerCompose function"
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
    debug "resetDockerCompose function ended"
}

# Function that will check the necerrary dependencies for the script to run
fn_checkDependencies(){
    clear
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v:${SCRIPT_VERSION}"$'\n'"------------------------------------------ "
    print_and_log "YELLOW" "Checking dependencies..."
    # this need to be changed to dinamically read depenedncies for any platform and select and install all the dependencies for the current platform
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        colorprint "YELLOW" "Now a small useful package named JQ used to manage JSON files will be installed if not already present"
        colorprint "YELLOW" "Please, if prompted, enter your sudo password to proceed"$'\n'
        
        fn_install_packages jq
    else
        colorprint "BLUE" "Done, script ready to go"
    fi
    debug "Dependencies check completed"
}

### Main Menu ##
mainmenu() {
    clear
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v:${SCRIPT_VERSION}"$'\n'"------------------------------------------ "
    colorprint "DEFAULT" "Detected OS type: ${OS_TYPE}"$'\n'"Detected architecture: $ARCH"$'\n'"Docker $DKARCH image architecture will be used if the app's image permits it"$'\n'"------------------------------------------ "$'\n'
    
    PS3="Select an option and press Enter "$'\n'
    debug "Loading menu options"
    options=("Show supported apps' links" "Install Docker" "Setup Apps" "Setup Extra Apps" "Start apps stack" "Stop apps stack" "Reset .env File" "Reset $DKCOM_FILENAME file" "Quit")
    debug "Menu options loaded. Showing menu options, ready to select"

    select option in "${options[@]}"
    do
        case $REPLY in
            1) clear; fn_showLinks; break;;
            2) clear; fn_dockerInstall; break;;
            3) clear; fn_setupApps; break;;
            4) clear; fn_setupExtraApps; break;;
            5) clear; fn_startStack; break;;
            6) clear; fn_stopStack; break;;
            7) clear; fn_resetEnv; break;;
            8) clear; fn_resetDockerCompose; break;;
            ${#options[@]}) fn_bye; break;;
            *) clear; fn_unknown; break;;
        esac
    done
}

### Startup ##
debug "${SCRIPT_NAME} v${SCRIPT_VERSION} started"
clear
# Check the operating system
detect_os_type
# Check the system architecture and set the related docker architecture
detect_architecture
#check dependencies
fn_checkDependencies
# Start the main menu
debug "Starting main menu..."
while true; do
    mainmenu
done