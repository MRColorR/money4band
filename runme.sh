#!/usr/bin/env bash

### Variables and constants ###
## Script variables ##
# Script version #
readonly SCRIPT_VERSION="2.3.0" # used for checking updates

# Script name #
readonly SCRIPT_NAME=$(basename "$0") # save the script name in a variable not the full path

# Script URL for update #
readonly UPDATE_SCRIPT_URL="https://raw.githubusercontent.com/MRColorR/money4band/main/${SCRIPT_NAME}"

# Script log file #
readonly DEBUG_LOG="debug_${SCRIPT_NAME}.log"

# Script default sleep time #
readonly SLEEP_TIME=1

## Env file related constants and variables ##
# .env file prototype link #
readonly ENV_SRC='https://github.com/MRColorR/money4band/raw/main/.env'
# Env file default #
readonly DEVICE_NAME_PLACEHOLDER='yourDeviceName'
DEVICE_NAME='yourDeviceName'
# Proxy config #
PROXY_CONF='false'
CURRENT_PROXY=''
NEW_STACK_PROXY=''

## Config file related constants and variables ##
readonly CONFIG_JSON_FILE="config.json"
readonly MAINMENU_JSON_FILE="mainmenu.json"

## Docker compose related constants and variables ##
# docker compose yaml file name #
readonly DKCOM_FILENAME="docker-compose.yaml"
# docker compose yaml prototype file link #
readonly DKCOM_SRC="https://github.com/MRColorR/money4band/raw/main/$DKCOM_FILENAME"

## Dashboard related constants and variables ##
# Dashboard URL #
readonly DASHBOARD_URL="http://localhost:8081/"

### Resources, Scripts and Files folders ###
readonly RESOURCES_DIR="$PWD/.resources"
readonly CONFIG_DIR="$RESOURCES_DIR/.www/.configs"
readonly SCRIPTS_DIR="$RESOURCES_DIR/.scripts"
readonly FILES_DIR="$RESOURCES_DIR/.files"

## Architecture and OS related constants and variables ##
# Architecture default. Also define a map for the recognized architectures #
ARCH='unknown'
DKARCH='unknown'
declare -A arch_map=(
    ["x86_64"]="amd64"
    ["amd64"]="amd64"
    ["aarch64"]="arm64"
    ["arm64"]="arm64"
)
# OS default. Also define a map for the recognized OSs #
OS_TYPE='unknown'
declare -A os_map=(
    ["win32nt"]="Windows"
    ["windows_nt"]="Windows"
    ["windows"]="Windows"
    ["linux"]="Linux"
    ["darwin"]="MacOS"
    ["macos"]="MacOS"
    ["macosx"]="MacOS"
    ["mac"]="MacOS"
    ["osx"]="MacOS"    
    ["cygwin"]="Cygwin"
    ["mingw"]="MinGw"
    ["msys"]="Msys"
    ["freebsd"]="FreeBSD"
)

## Colors ##
# Colors used inside the script #
ESC=$(printf '\033') DEFAULT="${ESC}[0m"
declare -A colors=( 
    [DEFAULT]="${ESC}[0m" 
    [GREEN]="${ESC}[32m" 
    [BLUE]="${ESC}[34m" 
    [RED]="${ESC}[31m" 
    [YELLOW]="${ESC}[33m" 
    [MAGENTA]="${ESC}[35m" 
    [CYAN]="${ESC}[36m" 
    [PURPLE]="${ESC}[35;1m" 
    )

# Color functions #
colorprint() {
    if [[ -n "${colors[$1]}" ]]; then
        printf "${colors[$1]}%s${DEFAULT}\n" "$2"
    else
        # Join the array elements into a string
        color_list=$(IFS=','; echo "${!colors[*]}")
        
        printf "Unknown color: %s. Available colors are: %s\n" "$1" "$color_list"
    fi
}

# Function to manage unexpected choices of flags #
fn_unknown() { 
    colorprint "RED" "Unknown choice $REPLY, please choose a valid option"; 
    }

# Function to exit the script gracefully #
fn_bye(){
    colorprint "GREEN" "Share this app with your friends thank you!"
    print_and_log "GREEN" "Exiting the application...Bye!Bye!"
    exit 0
}

### Log, Update and Utility functions ###
# Function to write info/debug/warn/error messages to the log file if debug flag is true #
toLog_ifDebug() {
    local log_level
    local message

    # If only one argument is passed, default to DEBUG log level
    if [[ $# -eq 1 ]]; then
        log_level="[DEBUG]"
        message="$1"
    else
        log_level="$1"
        message="$2"
    fi

    # Only log if DEBUG mode is enabled
    if [[ "$DEBUG" == "true" ]]; then
        echo "$(date +'%Y-%m-%d %H:%M:%S') - $log_level - $message" >> "$DEBUG_LOG"
    fi
}
## Enable or disable logging using debug mode ##
# Check if the first argument is -d or --debug if so, enable debug mode
if [[ $1 == '-d' || $1 == '--debug' ]]; then
    DEBUG=true
    # Remove the first argument so it doesn't interfere with the rest of the script
    shift
    toLog_ifDebug "[DEBUG]" "Debug mode enabled."
else
    DEBUG=false
fi

# Function to print an info message that will be also logged to the log file #
print_and_log() {
    local color="$1"
    local message="$2"
    colorprint "$color" "$message"
    toLog_ifDebug "[INFO]" "$message"
}

# Function to print an error message and write it to the log file #
errorprint_and_log() {
    printf "%s\n" "$1" >&2
    toLog_ifDebug "[ERROR]" "$1"
}

# Function to print criticals errors that will stop the script execution, write them to the log file and exit the script with code 1 #
fn_fail() {
    errorprint_and_log "$1"
    read -r -p "Press Enter to exit..."
    exit 1
}

## Utility functions ##
# Function to detect OS
detect_os() {
    toLog_ifDebug "Detecting OS..."
    if ! command -v uname -s &> /dev/null; then
        toLog_ifDebug "uname command not found, OS detection failed. OS type will be set to 'unknown'."
        OS_TYPE="unknown"
    else
        OSStr="$(uname -s | tr '[:upper:]' '[:lower:]')"  # Convert to lowercase
        # Use a for loop to check if OSStr contains any known OS substring
        for key in "${!os_map[@]}"; do
            if [[ $OSStr == *"$key"* ]]; then
                OS_TYPE="${os_map[$key]}"
                break
            else
                OS_TYPE="unknown"
            fi
        done
    fi
    toLog_ifDebug "OS type detected: $OS_TYPE"
}

# Function to detect OS architecture and set the relative Docker architecture
detect_architecture() {
    toLog_ifDebug "Detecting system architecture..."
    if ! command -v uname -m &> /dev/null; then
        toLog_ifDebug "uname command not found, architecture detection failed. Architecture will be set to 'unknown'."
        ARCH="unknown"
        DKARCH="unknown"
    else
        archStr=$(uname -m | tr '[:upper:]' '[:lower:]')  # Convert to lowercase
        # Use a for loop to check if archStr contains any known architecture substring
        for key in "${!arch_map[@]}"; do
            if [[ $archStr == *"$key"* ]]; then
                ARCH="${archStr}"
                DKARCH="${arch_map[$key]}"
                break
            else
                DKARCH="unknown"
            fi
        done
    fi
    toLog_ifDebug "System architecture detected: $ARCH, Docker architecture has been set to $DKARCH"
}

# Function to check if dependencies packages are installed and install them if not #
fn_install_packages() {
    toLog_ifDebug "Checking if required packages are installed..."
    REQUIRED_PACKAGES=("$@")

    if [[ "$OS_TYPE" == "Linux" ]]; then
        # Check which package manager is installed
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
        elif command -v apk &> /dev/null ; then
            PKG_MANAGER="apk"
            PKG_CHECK="apk info"
            PKG_INSTALL="sudo apk add"
        elif command -v emerge &> /dev/null ; then
            PKG_MANAGER="emerge"
            PKG_CHECK="qlist -I"
            PKG_INSTALL="sudo emerge --ask n"
        else
            print_and_log "RED" "Your package manager has not been recognized by this script. Please install the following packages manually: ${REQUIRED_PACKAGES[*]}"
            read -r -p "Press Enter to continue"
            return
        fi
        toLog_ifDebug "Detected package manager: $PKG_MANAGER"
        # Install required packages
        for package in "${REQUIRED_PACKAGES[@]}"
        do
            if ! $PKG_CHECK | grep -q "^ii  $package"; then
                print_and_log "DEFAULT" "$package is not installed. Trying to install now..."
                if ! $PKG_INSTALL "${package}"; then
                    print_and_log "RED" "Failed to install $package. Please install it manually."
                fi
            else
                print_and_log "DEFAULT" "$package is already installed."
            fi
        done
    elif [[ "$OS_TYPE" == "MacOS" ]]; then
        if ! command -v brew &> /dev/null; then
            print_and_log "DEFAULT" "Homebrew is not installed. Trying to install now..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        for package in "${REQUIRED_PACKAGES[@]}"
        do
            if ! brew list --versions "$package" > /dev/null; then
                print_and_log "DEFAULT" "$package is not installed. Trying to install now..."
                if ! brew install "$package"; then
                    print_and_log "RED" "Failed to install $package. Please install it manually."
                fi
            else
                print_and_log "DEFAULT" "$package is already installed."
            fi
        done
    elif [[ "$OS_TYPE" == "Windows" ]]; then
        if ! command -v choco &> /dev/null; then
            print_and_log "DEFAULT" "Chocolatey is not installed. Trying to install now..."
            if ! powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"; then
                print_and_log "RED" "Failed to install Chocolatey. Please install it manually."
            fi
        fi
        for package in "${REQUIRED_PACKAGES[@]}"
        do
            if ! choco list --local-only --exact "$package" > /dev/null; then
                print_and_log "DEFAULT" "$package is not installed. Trying to install now..."
                if ! choco install "$package" -y; then
                    print_and_log "RED" "Failed to install $package. Please install it manually."
                fi
            else
                print_and_log "DEFAULT" "$package is already installed."
            fi
        done
    else
        print_and_log "RED" "Your operating system has not been recognized or is not supported by this function. Please install the following packages manually: ${REQUIRED_PACKAGES[*]}"
        read -r -p "Press Enter to continue"
        return
    fi
    toLog_ifDebug "Required packages installation completed."
}

## Multiarch emulation service installer function ##
fn_addDockerBinfmtSVC() {
    toLog_ifDebug "Installing multiarch emulation service..."
    # Check if the service file exists if it does then check if it is enabled and if not enable it, if its enabled then check if the content is the same as the one in the script and if not overwrite it then start the service
    toLog_ifDebug "Checking if the service already exists..."
    if [ -f "/etc/systemd/system/docker.binfmt.service" ]; then
        # Compare the contents of the existing service file with the one in $FILES_DIR
        toLog_ifDebug "Service already exists, comparing contents..."
        if ! cmp -s "/etc/systemd/system/docker.binfmt.service" "$FILES_DIR/docker.binfmt.service"; then
            # The contents are different, overwrite the existing service file
            toLog_ifDebug "Service contents are different, overwriting the file of the existing service..."
            if ! sudo cp "$FILES_DIR/docker.binfmt.service" /etc/systemd/system; then
                fn_fail "Failed to copy service file. Please check your permissions and the file path."
            fi
        fi

        # Check if the service is enabled
        toLog_ifDebug "Checking if the service is enabled..."
        if [ -d "/etc/systemd/system" ]; then
            # Systemd-based distributions
            toLog_ifDebug "Systemd-based distribution detected, checking if the service is enabled..."
            if ! systemctl is-enabled --quiet docker.binfmt.service; then
                # Enable the service
                toLog_ifDebug "Service is not enabled, enabling it..."
                if ! sudo systemctl enable docker.binfmt.service; then
                    fn_fail "Failed to enable docker.binfmt.service. Please check your system config and try to enable the exixting service manually. Then run the script again."
                fi
            fi
        fi
    elif [ -f "/etc/init.d/docker.binfmt" ]; then
        toLog_ifDebug "SysV init-based distribution detected, checking if the service is enabled..."
        # Compare the contents of the existing service file with the one in $FILES_DIR
        toLog_ifDebug "Service already exists, comparing contents..."
        if ! cmp -s "/etc/init.d/docker.binfmt" "$FILES_DIR/docker.binfmt.service"; then
            # The contents are different, overwrite the existing service file
            toLog_ifDebug "Service contents are different, overwriting the file of the existing service..."
            if ! sudo cp "$FILES_DIR/docker.binfmt.service" /etc/init.d/docker.binfmt; then
                fn_fail "Failed to copy service file. Please check your permissions and the file path."
            fi
            sudo chmod +x /etc/init.d/docker.binfmt
        fi

        # Check if the service is enabled
        toLog_ifDebug "Checking if the service is enabled..."
        if [ -d "/etc/init.d" ]; then
            # SysV init-based distributions
            toLog_ifDebug "SysV init-based distribution detected, checking if the service is enabled..."
            if ! grep -q "docker.binfmt" /etc/rc.local; then
                # Enable the service
                toLog_ifDebug "Service is not enabled, enabling it..."
                sudo update-rc.d docker.binfmt defaults
            fi
        fi
    else
        # The service file does not exist, copy it to the appropriate location
        toLog_ifDebug "Service does not already exists, copying it to the appropriate location..."
        if [ -d "/etc/systemd/system" ]; then
            # Systemd-based distributions
            toLog_ifDebug "Systemd-based distribution detected, copying service file..."
            sudo cp "$FILES_DIR/docker.binfmt.service" /etc/systemd/system
            sudo systemctl enable docker.binfmt.service
            toLog_ifDebug "Service file copied and enabled."
        elif [ -d "/etc/init.d" ]; then
            # SysV init-based distributions
            toLog_ifDebug "SysV init-based distribution detected, copying service file..."
            sudo cp "$FILES_DIR/docker.binfmt.service" /etc/init.d/docker.binfmt
            sudo chmod +x /etc/init.d/docker.binfmt
            sudo update-rc.d docker.binfmt defaults
            toLog_ifDebug "Service file copied and enabled."
        else
            # Fallback option (handle unsupported systems)
            fn_fail "Warning: I can not find a supported init system. You will have to manually enable the binfmt service. Then restart the script."
        fi
    fi

    # Start the service
    toLog_ifDebug "Starting the service..."
    if [ -d "/etc/systemd/system" ]; then
        # Systemd-based distributions
        toLog_ifDebug "Systemd-based distribution detected, starting the service..."
        if ! sudo systemctl start docker.binfmt.service; then
            fn_fail "Failed to start docker.binfmt.service. Please check your system config and try to start the exixting service manually. Then run the script again."
        fi
        toLog_ifDebug "Service started."
    elif [ -d "/etc/init.d" ]; then
        # SysV init-based distributions
        toLog_ifDebug "SysV init-based distribution detected, starting the service..."
        if ! sudo service docker.binfmt start; then
            fn_fail "Failed to start docker.binfmt.service. Please check your system config and try to start the exixting service manually. Then run the script again."
        fi
        toLog_ifDebug "Service started."
    fi
}

### Sub-menu Functions ###
# Shows the liks of the apps
fn_showLinks() {
    clear
    toLog_ifDebug "Showing apps links"
    colorprint "GREEN" "Use CTRL+Click to open links or copy them:"
    # reading from $CONFIG_JSON_FILE show all the apps type that are the dictionary keys and then show the name and the link of each app in the dictionary
    for app_type in $(jq -r 'keys[]' "$CONFIG_DIR/$CONFIG_JSON_FILE"); do
        colorprint "YELLOW" "---$app_type---"
        for app in $(jq -r ".[\"$app_type\"][].name" "$CONFIG_DIR/$CONFIG_JSON_FILE"); do
            colorprint "DEFAULT" "$app"
            colorprint "BLUE" "$(jq -r ".[\"$app_type\"][] | select(.name==\"$app\") | .link" "$CONFIG_DIR/$CONFIG_JSON_FILE")"
            
        done
    done
    read -r -p "Press Enter to go back to mainmenu"
    toLog_ifDebug "Links shown, going back to mainmenu"
}

## Docker checker and installer function ##
# Check if docker is installed and if not then it tries to install it automatically
fn_dockerInstall() {
    toLog_ifDebug "DockerInstall function started"
    clear
    colorprint "YELLOW" "This menu item will launch a script that will attempt to install Docker"
    colorprint "YELLOW" "Use it only if you do not know how to perform the manual Docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some rare cases and depending on the distros may fail to install Docker correctly."
    
    while true; do
        read -r -p "Do you wish to proceed with the Docker automatic installation Y/N? " yn
        case $yn in
            [Yy]* )
                toLog_ifDebug "User decided to install Docker through the script. Checking if Docker is already installed."
                if docker --version >/dev/null 2>&1; then
                    toLog_ifDebug "Docker is already installed. Asking user if he wants to continue with the installation anyway."
                    while true; do
                        colorprint "YELLOW" "It seems that Docker is already installed. Do you want to continue with the installation anyway? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                toLog_ifDebug "User decided to continue with the Docker re-install anyway."
                                break
                                ;;
                            [Nn]* )
                                toLog_ifDebug "User decided to abort the Docker re-install."
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
    toLog_ifDebug "SetupNotifications function started"
    clear
    while true; do
        colorprint "YELLOW" "Do you wish to setup notifications about apps images updates (Yes to receive notifications and apply updates, No to just silently apply updates) Y/N?"
        read -r yn
        case $yn in
            [Yy]* )
                toLog_ifDebug "User decided to setup notifications about apps images updates."
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
                        sed -i "s~# SHOUTRRR_URL=~SHOUTRRR_URL=~" .env
                        CURRENT_VALUE=$(grep -oP 'SHOUTRRR_URL=\K[^#\r]+' .env)
                        sed -i "s~SHOUTRRR_URL=${CURRENT_VALUE}~SHOUTRRR_URL=$SHOUTRRR_URL~" .env
                        sed -i "s~# - WATCHTOWER_NOTIFICATIONS=shoutrrr~  - WATCHTOWER_NOTIFICATIONS=shoutrrr~" "$DKCOM_FILENAME"
                        sed -i "s~# - WATCHTOWER_NOTIFICATION_URL~  - WATCHTOWER_NOTIFICATION_URL~" "$DKCOM_FILENAME"
                        sed -i "s~# - WATCHTOWER_NOTIFICATIONS_HOSTNAME~  - WATCHTOWER_NOTIFICATIONS_HOSTNAME~" "$DKCOM_FILENAME"
                        sed -i 's/NOTIFICATIONS_CONFIGURATION_STATUS=0/NOTIFICATIONS_CONFIGURATION_STATUS=1/' .env
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
                break;;
            [Nn]* )
                toLog_ifDebug "User chose to skip notifications setup"
                colorprint "BLUE" "Noted: all updates will be applied automatically and silently";
                read -r -p "Press enter to continue."
                break;;
            * )
                colorprint "RED" "Please answer yes or no.";;
        esac
    done

    clear
    toLog_ifDebug "SetupNotifications function ended"
}


fn_setupApp() {
    toLog_ifDebug "SetupApp function started"
    local app_json=""
    local dk_compose_filename="docker-compose.yaml"
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --app-json)
                app_json="$2"
                shift
                ;;
            --dk-compose-filename)
                dk_compose_filename="$2"
                shift
                ;;
            *)
                colorprint "RED" "Unknown parameter passed to fn_setupApp: $1"
                ;;
        esac
        shift
    done
    # Extract the necessary fields from the app json
    toLog_ifDebug "Extracting necessary fields from the passed app json"
    local name
    name=$(jq -r '.name' <<< "$app_json")
    local link
    link=$(jq -r '.link' <<< "$app_json")
    local app_image
    app_image=$(jq -r '.image' <<< "$app_json")
    local flags_raw
    flags_raw=$(jq -r 'keys[]' <<< "$(jq '.flags?' <<< "$app_json")")
    # Load the flags thata are extracted by jq as a string in an array
    local flags=()
    while read -r line; do
        flags+=("$line")
    done <<< "$flags_raw"
    local claimURLBase
    claimURLBase=$(jq -r '.claimURLBase? // .link' <<< "$app_json") # The ? is to make the claimURLBase field optional if not present in the json it will be set to the link field
    local CURRENT_APP
    CURRENT_APP=$(echo "${name}" | tr '[:lower:]' '[:upper:]')
    while true; do
        # Check if the ${CURRENT_APP} is already enabled in the ${dk_compose_filename} file and if it is not (if there is a #ENABLE_$CURRENTAPP) then ask the user if they want to enable it
        toLog_ifDebug "Checking if the ${CURRENT_APP} app is already enabled in the ${dk_compose_filename} file"
        if grep -q "#ENABLE_${CURRENT_APP}" "${dk_compose_filename}"; then
            toLog_ifDebug "${CURRENT_APP} is not enabled in the ${dk_compose_filename} file, asking the user if they want to enable it"
            # Show the generic message before asking the user if they want to enable the app
            colorprint "YELLOW" "PLEASE REGISTER ON THE PLATFORMS USING THE LINKS THAT WILL BE PROVIDED, YOU'LL THEN NEED TO ENTER SOME DATA BELOW:"
            # Ask the user if they want to enable the ${CURRENT_APP}
            colorprint "YELLOW" "Do you wish to enable and use ${CURRENT_APP}? (Y/N)"
            read -r yn
            case $yn in
                [Yy]* )
                    toLog_ifDebug "User decided to enable and use ${CURRENT_APP}"
                    colorprint "CYAN" "Go to ${CURRENT_APP} ${link} and register"
                    colorprint "GREEN" "Use CTRL+Click to open links or copy them:"
                    read -r -p "When you are done press Enter to continue"
                    toLog_ifDebug "Enabling ${CURRENT_APP} app. The parameters received are: name=$name, link=$link, image=$app_image, flags=${flags[*]}, claimURLBase=$claimURLBase"
                    # Read the flags in the array and execute the relative logic using the case statement
                    for flag_name in "${flags[@]}"; do
                        # Extract flag details and all the parameters if they exist 
                        local flag_details
                        flag_details=$(jq -r ".flags[\"$flag_name\"]?" <<< "$app_json")
                        toLog_ifDebug "Result of flag_details reading: $flag_details"
                        if [[ "$flag_details" != "null" ]]; then
                            #load all the flags parameters keys in an array so then we cann iterate on them and access their values easily from the json
                            local flag_params_keys
                            flag_params_keys=$(jq -r "keys[]?" <<< "$flag_details")
                            toLog_ifDebug "Result of flag_params_keys reading: $flag_params_keys"
                        else
                            toLog_ifDebug "No flag details found for flag: $flag_name"
                        fi
                        case $flag_name in
                            --email)
                                toLog_ifDebug "Starting email setup for ${CURRENT_APP} app"
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
                                toLog_ifDebug "Starting password setup for ${CURRENT_APP} app"
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
                                toLog_ifDebug "Starting APIKey setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find/Generate your APIKey inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "GREEN" "Enter your ${CURRENT_APP} APIKey:"
                                read -r APP_APIKEY
                                sed -i "s^your${CURRENT_APP}APIKey^$APP_APIKEY^" .env
                                ;;
                            --userid)
                                toLog_ifDebug "Starting UserID setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find your UserID inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "GREEN" "Enter your ${CURRENT_APP} UserID:"
                                read -r APP_USERID
                                sed -i "s/your${CURRENT_APP}UserID/$APP_USERID/" .env
                                ;;
                            --uuid)
                                toLog_ifDebug "Starting UUID setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Starting UUID generation/import for ${CURRENT_APP}"
                                # Read all the parameters for the uuid flag , if one of them is the case length then save it in a variable
                                if [[ -n "${flag_params_keys:-}" ]]; then
                                    for flag_param_key in $flag_params_keys; do
                                        toLog_ifDebug "Reading flag parameter: $flag_param_key"
                                        case $flag_param_key in
                                            length)
                                                toLog_ifDebug "Reading flag parameter length"
                                                flag_length_param=$(jq -r ".flags[\"$flag_name\"][\"$flag_param_key\"]?" <<< "$app_json")
                                                toLog_ifDebug "Result of flag_length_param reading: $flag_length_param"
                                                ;;
                                            *)
                                                toLog_ifDebug "Unknown flag parameter: $flag_param_key"
                                                ;;
                                        esac
                                    done
                                else
                                    toLog_ifDebug "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                                fi

                                # Check if the flag_length_param exists and if is a number (i.e., the desired length)
                                if [[ -n "${flag_length_param:-}" ]] && [[ "${flag_length_param:-}" =~ ^[0-9]+$ ]]; then
                                    DESIRED_LENGTH="$flag_length_param"
                                    toLog_ifDebug "Desired length for UUID generation/import passed as argument of the uuid flag (read from json), its value is: $DESIRED_LENGTH"
                                else
                                    # If no length is provided, ask the user
                                    toLog_ifDebug "No desired length for UUID generation/import passed as argument of the uuid flag, asking the user"
                                    colorprint "GREEN" "Enter desired length for the UUID (default is 32, press Enter to use default):"
                                    read -r DESIRED_LENGTH_INPUT
                                    DESIRED_LENGTH=${DESIRED_LENGTH_INPUT:-32}  # Defaulting to 32 if no input provided
                                fi
                                toLog_ifDebug "Starting temporary UUID generation/import for ${CURRENT_APP} with desired length: $DESIRED_LENGTH. This will be overwritten if the user chooses to use an existing UUID."
                                local UUID=""
                                while [ ${#UUID} -lt "$DESIRED_LENGTH" ]; do
                                    # Regenerate the salt for each iteration
                                    SALT="${DEVICE_NAME}""${RANDOM}""${UUID}"  # Incorporate the previously generated UUID part for added randomness
                                    UUID_PART="$(echo -n "$SALT" | md5sum | cut -c1-32)"
                                    UUID+="$UUID_PART"
                                done
                            
                                # Cut or trail the generated UUID based on the desired length
                                UUID=${UUID:0:$DESIRED_LENGTH}
                                toLog_ifDebug "Done, generated temporary UUID: $UUID"
                                
                                while true; do
                                    colorprint "YELLOW" "Do you want to use a previously registered uuid for ${CURRENT_APP}? (Y/N)"
                                    read -r USE_EXISTING_UUID
                                    case $USE_EXISTING_UUID in
                                        [Yy]* )
                                            while true; do
                                                colorprint "GREEN" "Please enter the alphanumeric part of the existing uuid for ${CURRENT_APP}, it should be $DESIRED_LENGTH characters long."
                                                colorprint "DEFAULT" "E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4"
                                                read -r EXISTING_UUID
                                                if [[ ! "$EXISTING_UUID" =~ ^[a-f0-9]{$DESIRED_LENGTH}$ ]]; then
                                                    colorprint "RED" "Invalid UUID entered, it should be an alphanumeric string and $DESIRED_LENGTH characters long."
                                                    colorprint "DEFAULT" "Do you want to try again? (Y/N)"
                                                    read -r TRY_AGAIN
                                                    case $TRY_AGAIN in
                                                        [Nn]* ) break ;;
                                                        * ) continue ;;
                                                    esac
                                                else
                                                    UUID="$EXISTING_UUID"
                                                    print_and_log "DEFAULT" "Using user provided existing UUID: $UUID"
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
                                
                                sed -i "s/your${CURRENT_APP}DeviceUUID/$UUID/" .env
                                colorprint "DEFAULT" "${CURRENT_APP} UUID setup: done"
                                # Generaing the claim link
                                local claimlink="${claimURLBase}${UUID}"
                                colorprint "BLUE" "Save the following link somewhere to claim/register your ${CURRENT_APP} node/device after completing the setup and starting the apps stack: ${claimlink}"
                                echo "${claimlink}" > "claim${CURRENT_APP}NodeDevice.txt"
                                colorprint "DEFAULT" "A new file containing this link has been created for you in the current directory"
                                ;;
                            --cid)
                                toLog_ifDebug "Starting CID setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find your CID inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "DEFAULT" "Example: For packetstream you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
                                colorprint "GREEN" "Enter your ${CURRENT_APP} CID:"
                                read -r APP_CID
                                sed -i "s/your${CURRENT_APP}CID/$APP_CID/" .env
                                ;;
                            --token)
                                toLog_ifDebug "Starting token setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find your token inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "DEFAULT" "Example: For traffmonetizer you can fetch it from your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
                                colorprint "GREEN" "Enter your ${CURRENT_APP} token:"
                                read -r APP_TOKEN
                                sed -i "s/your${CURRENT_APP}Token/$APP_TOKEN/" .env
                                ;;
                            --customScript)
                                toLog_ifDebug "Starting customScript setup for ${CURRENT_APP} app"
                                # Read all the parameters for the customScript flag , if one of them is the case scriptname then save it in a variable
                                if [[ -n "${flag_params_keys:-}" ]]; then
                                    for flag_param_key in $flag_params_keys; do
                                        toLog_ifDebug "Reading flag parameter: $flag_param_key"
                                        case $flag_param_key in
                                            scriptname)
                                                toLog_ifDebug "Reading flag parameter scriptname"
                                                flag_scriptname_param=$(jq -r ".flags[\"$flag_name\"][\"$flag_param_key\"]?" <<< "$app_json")
                                                toLog_ifDebug "Result of flag_scriptname_param reading: $flag_scriptname_param"
                                                ;;
                                            *)
                                                toLog_ifDebug "Unknown flag parameter: $flag_param_key"
                                                ;;
                                        esac
                                    done
                                else
                                    toLog_ifDebug "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                                fi
                                CUSTOM_SCRIPT_NAME="${flag_scriptname_param}.sh"
                                SCRIPT_PATH="$SCRIPTS_DIR/$CUSTOM_SCRIPT_NAME"
                                ESCAPED_PATH="${SCRIPT_PATH//\"/\\\"}"
                                toLog_ifDebug "Starting custom script execution for ${CURRENT_APP} app using $SCRIPT_NAME from $ESCAPED_PATH"
                                if [[ -f "$SCRIPT_PATH" ]]; then
                                    chmod +x "$ESCAPED_PATH"
                                    colorprint "DEFAULT" "Executing custom script: $CUSTOM_SCRIPT_NAME"
                                    source "$ESCAPED_PATH"
                                else
                                    colorprint "RED" "Custom script '$CUSTOM_SCRIPT_NAME' not found in the scripts directory."
                                fi
                                ;;
                            --manual)
                                toLog_ifDebug "Starting manual setup for ${CURRENT_APP} app"
                                colorprint "YELLOW" "${CURRENT_APP} requires further manual configuration."
                                colorprint "YELLOW" "Please after completing this automated setup follow the manual steps described on the app's website."
                                ;; 
                            *)
                                fn_fail "Unknown ${flag_name} flag passed to fn_setupApp"
                                ;;  
                        esac
                    done
                    # Complete the setup of the app by enabling it in the docker-compose file
                    sed -i "s^#ENABLE_${CURRENT_APP}^^" "${dk_compose_filename}"
                    toLog_ifDebug "Enabled ${CURRENT_APP} app in ${dk_compose_filename}"

                    # App Docker image architecture adjustments
                    toLog_ifDebug "Starting Docker image architecture adjustments for ${CURRENT_APP} app"
                    TAG='latest'
                    DKHUBRES=$(curl -L -s "https://registry.hub.docker.com/v2/repositories/${app_image}/tags" | jq --arg DKARCH "$DKARCH" '[.results[] | select(.images[].architecture == $DKARCH) | .name]')
                    TAGSNUMBER=$(echo "$DKHUBRES" | jq '. | length')
                    if [ "$TAGSNUMBER" -gt 0 ]; then 
                        colorprint "DEFAULT" "There are $TAGSNUMBER tags supporting $DKARCH arch for this image"
                        colorprint "DEFAULT" "Let's see if $TAG tag is in there"
                        LATESTPRESENT=$(echo "$DKHUBRES" | jq --arg TAG "$TAG" '[.[] | contains($TAG)] | any')
                        if [ "$LATESTPRESENT" == "true" ]; then 
                            colorprint "GREEN" "OK, $TAG tag present and it supports $DKARCH arch, nothing to do"
                        else 
                            colorprint "YELLOW" "$TAG tag does not support $DKARCH arch but other tags do, the newer tag supporting $DKARCH will be selected"
                            NEWTAG=$(echo "$DKHUBRES" | jq -r '.[0]')
                            sed -i "s^${app_image}:latest^${app_image}:$NEWTAG^" $DKCOM_FILENAME
                        fi
                    else 
                        colorprint "YELLOW" "No native image tag found for $DKARCH arch, emulation layer will try to run this app image anyway."
                        colorprint "DEFAULT" "If an emulation layer is not already installed, the script will try to install it now. Please provide your sudo password if prompted."
                        #fn_install_packages qemu binfmt-support qemu-user-static
                        fn_addDockerBinfmtSVC
                    fi
                    toLog_ifDebug "Finished Docker image architecture adjustments for ${CURRENT_APP} app. Its image tag is now $(grep -oP "${app_image}:\K[^#\r]+" $DKCOM_FILENAME)"
                    read -r -p "${CURRENT_APP} configuration complete, press enter to continue to the next app"
                    toLog_ifDebug "Finished setupApp function for ${CURRENT_APP} app"
                    break
                    ;;
                [Nn]* )
                    toLog_ifDebug "User decided to skip ${CURRENT_APP} setup"
                    colorprint "BLUE" "${CURRENT_APP} setup will be skipped."
                    read -r -p "Press enter to continue to the next app"
                    break
                    ;;
                * )
                    colorprint "RED" "Please answer yes or no."
                    ;;
            esac
        else
            print_and_log "BLUE" "${CURRENT_APP} is already enabled."
            sleep ${SLEEP_TIME}
            break
        fi
    done
}

fn_setupProxy() {
    toLog_ifDebug "Starting setupProxy function"
    if [ "$PROXY_CONF" == 'false' ]; then
        while true; do
            colorprint "YELLOW" "Do you wish to setup a proxy for the apps in this stack Y/N?"
            colorprint "DEFAULT" "Note that if you want to run multiple instances of the same app you will need to configure different env files each in different project folders (copy the project to multiple different folders and configure them using different proxies)"
            read -r yn
            case $yn in
                [Yy]* )
                    clear
                    toLog_ifDebug "User chose to setup a proxy"
                    colorprint "YELLOW" "Proxy setup started."
                    readonly RANDOM_VALUE=$RANDOM
                    colorprint "GREEN" "Insert the designed proxy to use. Eg: protocol://proxyUsername:proxyPassword@proxy_url:proxy_port or just protocol://proxy_url:proxy_port if auth is not needed"
                    read -r NEW_STACK_PROXY
                    # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                    # ATTENTION: if a random value has been already added to the project and devicename during a previous setup it should remain the same to mantain consistency withthe devices name registered on the apps sites but the proxy url could be changed
                    sed -i "s^COMPOSE_PROJECT_NAME=money4band^COMPOSE_PROJECT_NAME=money4band_$RANDOM_VALUE^" .env 
                    sed -i "s^DEVICE_NAME=${DEVICE_NAME}^DEVICE_NAME=${DEVICE_NAME}$RANDOM_VALUE^" .env
                    # Obtaining the line of STACK_PROXY= in the .env file and then replace the line with the new proxy also uncomment the line if it was commented
                    sed -i "s^# STACK_PROXY=^STACK_PROXY=^" .env # if it was already uncommented it does nothing
                    CURRENT_VALUE=$(grep -oP 'STACK_PROXY=\K[^#\r]+' .env)
                    sed -i "s^$CURRENT_VALUE^$NEW_STACK_PROXY^" .env
                    sed -i "s^#ENABLE_PROXY^^" $DKCOM_FILENAME
                    sed -i "s^# network_mode^network_mode^" $DKCOM_FILENAME
                    PROXY_CONF='true'
                    sed -i 's/PROXY_CONFIGURATION_STATUS=0/PROXY_CONFIGURATION_STATUS=1/' .env
                    colorprint "DEFAULT" "Ok, $NEW_STACK_PROXY will be used as proxy for all apps in this stack"
                    read -r -p "Press enter to continue"
                    toLog_ifDebug "Proxy setup finished"
                    break
                    ;;
                [Nn]* )
                    toLog_ifDebug "User chose not to setup a proxy"
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
    print_and_log "BLUE" "Starting setupEnv function for $app_type"
    # Check if .env file is already configured if 1 then it is already configured, if 0 then it is not configured
    ENV_CONFIGURATION_STATUS=$(grep -oP '# ENV_CONFIGURATION_STATUS=\K[^#\r]+' .env)
    toLog_ifDebug "Current ENV_CONFIGURATION_STATUS: $ENV_CONFIGURATION_STATUS"
    PROXY_CONFIGURATION_STATUS=$(grep -oP '# PROXY_CONFIGURATION_STATUS=\K[^#\r]+' .env)
    toLog_ifDebug "Current PROXY_CONFIGURATION_STATUS: $PROXY_CONFIGURATION_STATUS"
    NOTIFICATIONS_CONFIGURATION_STATUS=$(grep -oP '# NOTIFICATIONS_CONFIGURATION_STATUS=\K[^#\r]+' .env)
    toLog_ifDebug "Current NOTIFICATIONS_CONFIGURATION_STATUS: $NOTIFICATIONS_CONFIGURATION_STATUS"
    if [ "$ENV_CONFIGURATION_STATUS" == "1" ] && [ "$app_type" == "apps" ]; then
        colorprint "YELLOW" "The current .env file appears to have already been configured. Do you wish to reset it? (Y/N)"
        read -r yn
        case $yn in
            [Yy]* )
                print_and_log "DEFAULT" "Downloading a fresh .env file.";
                curl -fsSL $ENV_SRC -o ".env"
                curl -fsSL $DKCOM_SRC -o "$DKCOM_FILENAME"
                clear
                ;;
            [Nn]* )
                print_and_log "BLUE" "Keeping the existing .env file."
                read -r -p "Press enter to continue"
                ;;
            * )
                colorprint "RED" "Invalid input. Please answer yes or no."
                return 1
                ;;
        esac
    elif [ "$ENV_CONFIGURATION_STATUS" == "1" ] && [ "$app_type" != "apps" ]; then
        print_and_log "BLUE" "Proceeding with $app_type setup without resetting .env file as it should already be configured by the main apps setup."
        read -r -p "Press enter to continue"
    fi
    while true; do
        colorprint "YELLOW" "Do you wish to proceed with the .env file guided setup Y/N? (This will also adapt the $DKCOM_FILENAME file accordingly)"
        read -r yn
        case $yn in
            [Yy]* ) 
                clear
                toLog_ifDebug "User chose to proceed with the .env file guided setup for $app_type"
                colorprint "YELLOW" "beginnning env file guided setup"
                sed -i 's/ENV_CONFIGURATION_STATUS=0/ENV_CONFIGURATION_STATUS=1/' .env
                if grep -q "DEVICE_NAME=${DEVICE_NAME_PLACEHOLDER}" .env  ; then
                    toLog_ifDebug "Device name is still the default one, asking user to change it"
                    colorprint "YELLOW" "PLEASE ENTER A NAME FOR YOUR DEVICE:"
                    read -r DEVICE_NAME
                    sed -i "s/DEVICE_NAME=${DEVICE_NAME_PLACEHOLDER}/DEVICE_NAME=${DEVICE_NAME}/" .env
                else
                    toLog_ifDebug "Device name is already set, skipping user input"
                    DEVICE_NAME=$(grep -oP 'DEVICE_NAME=\K[^#\r]+' .env)
                fi
                clear ;
                if [ "$PROXY_CONFIGURATION_STATUS" == "1" ]; then
                    CURRENT_PROXY=$(grep -oP 'STACK_PROXY=\K[^#\r]+' .env)
                    print_and_log "BLUE" "Proxy is already set up."
                    while true; do
                        colorprint "YELLOW" "The current proxy is: ${CURRENT_PROXY} . Do you wish to change it? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                PROXY_CONF='false'
                                toLog_ifDebug "User chose to change the proxy that was already configured"
                                fn_setupProxy;
                                break;;
                            [Nn]* )
                                toLog_ifDebug "User chose not to change the proxy that was already configured"
                                print_and_log "BLUE" "Keeping the existing proxy."
                                break;;
                            * )
                                colorprint "RED" "Invalid input. Please answer yes or no.";;
                        esac
                    done                        
                else
                    toLog_ifDebug "Asking user if they want to setup a proxy as it is not already configured"
                    fn_setupProxy;
                fi
                clear ;
                toLog_ifDebug "Loading $app_type from ${CONFIG_JSON_FILE}..."
                apps=$(jq -c ".[\"$app_type\"][]" "${CONFIG_DIR}/${CONFIG_JSON_FILE}")
                toLog_ifDebug "$app_type loaded from ${CONFIG_JSON_FILE}"
                for app in $apps; do
                    clear
                    fn_setupApp --app-json "$app" --dk-compose-filename "$DKCOM_FILENAME"
                    clear
                done

                # Notifications setup
                clear;
                if [ "$NOTIFICATIONS_CONFIGURATION_STATUS" == "1" ]; then
                    print_and_log "BLUE" "Notifications are already set up."
                    while true; do
                        CURRENT_SHOUTRRR_URL=$(grep -oP 'SHOUTRRR_URL=\K[^#\r]+' .env)
                        colorprint "YELLOW" "The current notifications setup uses: ${CURRENT_SHOUTRRR_URL}. Do you wish to change it? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                toLog_ifDebug "User chose to change the notifications setup that was already configured"
                                fn_setupNotifications;
                                break;;
                            [Nn]* )
                                toLog_ifDebug "User chose not to change the notifications setup that was already configured"
                                print_and_log "BLUE" "Keeping the existing notifications setup."
                                break;;
                            * )
                                colorprint "RED" "Invalid input. Please answer yes or no.";;
                        esac
                    done
                else
                    toLog_ifDebug "Asking user if they want to setup notifications as they are not already configured"
                    fn_setupNotifications;
                fi
                print_and_log "GREEN" "env file setup complete.";
                read -n 1 -s -r -p "Press enter to go back to the menu"$'\n'
                break
                ;;
            [Nn]* )
                toLog_ifDebug "User chose not to proceed with the .env file guided setup for $app_type"
                colorprint "BLUE" ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no."
        esac
    done
}
#Setup main apps
fn_setupApps(){
    fn_setupEnv "apps"  # Call fn_setupEnv with "apps"
}
# Setup extra apps
fn_setupExtraApps(){
    fn_setupEnv "extra-apps"  # Call fn_setupEnv with "extra_apps"
}

fn_startStack(){
    clear
    toLog_ifDebug "Starting startStack function"
    while true; do
        colorprint "YELLOW" "This menu item will launch all the apps using the configured .env file and the $DKCOM_FILENAME file (Docker must be already installed and running)"
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose up -d; then
                    print_and_log "GREEN" "All Apps started."
                    colorprint "GREEN" "You can visit the web dashboard on ${DASHBOARD_URL}. If not already done, use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details."
                else
                    errorprint_and_log "Error starting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                toLog_ifDebug "User chose not to start the stack"
                colorprint "BLUE" "Docker stack startup canceled."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no.";;
        esac
    done
    toLog_ifDebug "StartStack function ended"
}


fn_stopStack(){
    clear
    toLog_ifDebug "Starting stopStack function"
    while true; do
        colorprint "YELLOW" "This menu item will stop all the apps and delete the docker stack previously created using the configured .env file and the $DKCOM_FILENAME file."
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose down; then
                    print_and_log "GREEN" "All Apps stopped and stack deleted."
                else
                    errorprint_and_log "Error stopping and deleting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                toLog_ifDebug "User chose not to stop the stack"
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
    toLog_ifDebug "Starting resetEnv function"
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
    toLog_ifDebug "resetEnv function ended"
}

fn_resetDockerCompose(){
    clear
    toLog_ifDebug "Starting resetDockerCompose function"
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
    toLog_ifDebug "resetDockerCompose function ended"
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
    toLog_ifDebug "Dependencies check completed"
}

### Main Menu ##
mainmenu() {
    clear
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v:${SCRIPT_VERSION}"$'\n'"------------------------------------------ "
    colorprint "DEFAULT" "Detected OS type: ${OS_TYPE}"$'\n'"Detected architecture: $ARCH"$'\n'"Docker $DKARCH image architecture will be used if the app's image permits it"$'\n'"------------------------------------------ "$'\n'
    
    PS3="Select an option and press Enter "$'\n'
    toLog_ifDebug "Loading menu options"
    # Reset the menuItems array
    menuItems=()
    # Read labels from the JSON file without splitting them
    while IFS= read -r label; do
        menuItems+=("$label")
    done < <(jq -r '.[].label? // empty' "$CONFIG_DIR/$MAINMENU_JSON_FILE")
    
    toLog_ifDebug "Menu options loaded. Showing menu options, ready to select"
    select option in "${menuItems[@]}"
    do
        if [[ -n $option ]]; then
            clear
            # Fetch the function name associated with the chosen menu item
            functionName=$(jq -r --arg chosen "$option" '.[] | select(.label == $chosen).function? // empty' "$CONFIG_DIR/$MAINMENU_JSON_FILE")
            if [[ -n $functionName ]]; then
                # Invoke the function
                $functionName
            else
                colorprint "RED" "Error: Unable to find the function associated with the selected option."
                toLog_ifDebug "Error in JSON: Missing function for menu item $option"
            fi
            break
        else
            clear
            fn_unknown
            break
        fi
    done
}

### Startup ##
toLog_ifDebug "Starting ${SCRIPT_NAME} v${SCRIPT_VERSION}"
clear

# Detect the operating system
detect_os

# Detect the architecture and set the correct docker image architecture
detect_architecture

# Check dependencies
fn_checkDependencies

# Start the main menu
toLog_ifDebug "Starting main menu..."
while true; do
    mainmenu
done
