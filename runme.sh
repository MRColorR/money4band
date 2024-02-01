#!/usr/bin/env bash
export LC_NUMERIC="C" # address possible locale issues that uses different notations for decimal numbers


### Variables and constants ###

## Env file related constants and variables ##
# env file name and template file name #
readonly ENV_TEMPLATE_FILENAME='.env.template'
readonly ENV_FILENAME='.env'

# Env file default #
readonly DEVICE_NAME_PLACEHOLDER='yourDeviceName'
DEVICE_NAME='yourDeviceName'
# Proxy config #
PROXY_CONF='false'
CURRENT_PROXY=''
NEW_STACK_PROXY=''

## Config file related constants and variables ##
readonly APP_CONFIG_JSON_FILE="app_config.json"
readonly MAINMENU_JSON_FILE="mainmenu.json"

## Docker compose related constants and variables ##
# docker compose yaml file name and template file name #
readonly DKCOM_TEMPLATE_FILENAME="docker-compose.yaml.template"
readonly DKCOM_FILENAME="docker-compose.yaml"

## Script init and variables ##
# Script default sleep time #
readonly SLEEP_TIME=1.5

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
    [DEFAULT]="${ESC}[1;0m" 
    [GREEN]="${ESC}[1;32m" 
    [BLUE]="${ESC}[1;34m" 
    [RED]="${ESC}[1;31m" 
    [YELLOW]="${ESC}[1;33m" 
    [MAGENTA]="${ESC}[1;35m" 
    [CYAN]="${ESC}[1;36m" 
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

# initialize the env file with the default values if there is no env file already present
# Check if the ${ENV_FILENAME} file is already present in the current directory, if it is not present copy from the .env.template file renaming it to ${ENV_FILENAME}, if it is present ask the user if they want to reset it or keep it as it is
if [ ! -f "${ENV_FILENAME}" ]; then
    echo "No ${ENV_FILENAME} file found, copying ${ENV_FILENAME} and ${DKCOM_FILENAME} from the template files"
    cp "${ENV_TEMPLATE_FILENAME}" "${ENV_FILENAME}"
    cp "${DKCOM_TEMPLATE_FILENAME}" "${DKCOM_FILENAME}"
    echo "Copied ${ENV_FILENAME} and ${DKCOM_FILENAME} from the template files"
else
    echo "Already found ${ENV_FILENAME} file, proceeding with setup"
    # check if the release version in the local env fileis the same of the local template file , if not align it
    LOCAL_SCRIPT_VERSION=$(grep -oP 'PROJECT_VERSION=\K[^#\r]+' ${ENV_FILENAME})
    LOCAL_SCRIPT_TEMPLATE_VERSION=$(grep -oP 'PROJECT_VERSION=\K[^#\r]+' ${ENV_TEMPLATE_FILENAME})
    if [[ "$LOCAL_SCRIPT_VERSION" != "$LOCAL_SCRIPT_TEMPLATE_VERSION" ]]; then
        echo "Local ${ENV_FILENAME} file version differs from local ${ENV_TEMPLATE_FILENAME} file version"
        echo "This could be the result of an updated project using an outdated ${ENV_FILENAME} file"
        sleep $SLEEP_TIME
        echo "Generating new ${ENV_FILENAME} and ${DKCOM_FILENAME} files from the local template files and backing up the old files as ${ENV_FILENAME}.bak and ${DKCOM_FILENAME}.bak"
        cp "${ENV_FILENAME}" "${ENV_FILENAME}.bak"
        cp "${ENV_TEMPLATE_FILENAME}" "${ENV_FILENAME}"
        cp "${DKCOM_FILENAME}" "${DKCOM_FILENAME}.bak"
        cp "${DKCOM_TEMPLATE_FILENAME}" "${DKCOM_FILENAME}"
        echo "New local ${ENV_FILENAME} and ${DKCOM_FILENAME} files generated from the local template files"
        echo "If you are unsure, download the latest version directly from GitHub."
        sleep $SLEEP_TIME
        read -r -p "Press Enter to continue"
    fi
fi

# Script version getting it from ${ENV_FILENAME} file #
SCRIPT_VERSION=$(grep -oP 'PROJECT_VERSION=\K[^#\r]+' ${ENV_FILENAME}) 

# Script name #
readonly SCRIPT_NAME=$(basename "$0") # save the script name in a variable not the full path

# Project Discord URL #
readonly DS_PROJECT_SERVER_URL=$(grep -oP 'DS_PROJECT_SERVER_URL=\K[^#\r]+' ${ENV_FILENAME})

# Script URL for update #
readonly PROJECT_BRANCH="main"
readonly PROJECT_URL="https://raw.githubusercontent.com/MRColorR/money4band/${PROJECT_BRANCH}"


# Script log file #
readonly DEBUG_LOG="debug_${SCRIPT_NAME}.log"


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
    local log_level="[DEBUG]"
    local message=""

    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            -l|--log_level)
                log_level="$2"
                shift 2
                ;;
            -m|--message)
                message="$2"
                shift 2
                ;;
            *)
                echo "Unknown parameter passed: $1"
                exit 1
                ;;
        esac
    done

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
    toLog_ifDebug -l "[DEBUG]" -m "Debug mode enabled."
else
    DEBUG=false
fi

# Function to print an info message that will be also logged to the log file #
print_and_log() {
    local color="$1"
    local message="$2"
    colorprint "$color" "$message"
    toLog_ifDebug -l "[INFO]" -m "$message"
}

# Function to print an error message and write it to the log file #
errorprint_and_log() {
    printf "%s\n" "$1" >&2
    toLog_ifDebug -l "[ERROR]" -m "$1"
}

# Function to print criticals errors that will stop the script execution, write them to the log file and exit the script with code 1 #
fn_fail() {
    errorprint_and_log "$1"
    read -r -p "Press Enter to exit..."
    exit 1
}

## Utility functions ##
# Function to check if the env file is already configured #
check_configuration_status() {
    local envFileArg=$1

    # Check if ${envFileArg} file is already configured
    ENV_CONFIGURATION_STATUS=$(grep -oP '# ENV_CONFIGURATION_STATUS=\K[^#\r]+' "$envFileArg")
    toLog_ifDebug -l "[DEBUG]" -m "Current ENV_CONFIGURATION_STATUS: $ENV_CONFIGURATION_STATUS"
    
    PROXY_CONFIGURATION_STATUS=$(grep -oP '# PROXY_CONFIGURATION_STATUS=\K[^#\r]+' "$envFileArg")
    toLog_ifDebug -l "[DEBUG]" -m "Current PROXY_CONFIGURATION_STATUS: $PROXY_CONFIGURATION_STATUS"

    NOTIFICATIONS_CONFIGURATION_STATUS=$(grep -oP '# NOTIFICATIONS_CONFIGURATION_STATUS=\K[^#\r]+' "$envFileArg")
    toLog_ifDebug -l "[DEBUG]" -m "Current NOTIFICATIONS_CONFIGURATION_STATUS: $NOTIFICATIONS_CONFIGURATION_STATUS"
}

# Function to round up to the nearest power of 2
RoundUpPowerOf2() {
    local value=$(printf "%.0f" $1)  # Convert to an integer by rounding
    local i=1
    while [ $i -lt $value ]; do
        i=$(( i * 2 ))
    done
    echo $i
}

# Function to adapt the limits in .env for CPU and RAM taking into account the number of CPU cores and the amount of RAM installed on the machine #
fn_adaptLimits() {
    # Define minimum values for CPU and RAM limits
    MIN_CPU_LIMIT="0.2"  # Minimum CPU limit (reasonable value)
    MIN_RAM_LIMIT="6"    # Minimum RAM limit is 6 MB (enforced by Docker)
    # check if lscpu is installed, if yes then get the number of CPU cores the machine has and the amount of RAM the machine has and adapt the limits in .env for CPU and RAM taking into account the number of CPU cores the machine has and the amount of RAM the machine has if not then print a warning message and leave the limits to the default values
    if command -v lscpu &> /dev/null; then
        # Get the number of CPU cores the machine has and others CPU related info
        # CPU_SOCKETS=$(lscpu | awk '/^Socket\(s\)/{ print $2 }')
        # # CPU_SOCKETS='-' # Uncomment to simulate incorrect socket number reporting
        # if ! [[ "$CPU_SOCKETS" =~ ^[0-9]+$ ]]; then
        #     CPU_SOCKETS=1  # Default to 1 if CPU_SOCKETS is not a number
        # fi
        # CPU_CORES=$(lscpu | awk '/^Core\(s\) per socket/{ print $4 }')
        # TOTAL_CPUS_OLD=$((CPU_CORES * CPU_SOCKETS)) # old calculations not working on some systems as sockets or cpus per socket are not reported correctly
        TOTAL_CPUS=$(lscpu -b -p=Core,Socket | grep -v '^#' | sort -u | wc -l)

        # Adapt the limits in .env file for CPU and RAM taking into account the number of CPU cores the machine has and the amount of RAM the machine has
        # CPU limits: little should use max 15% of the CPU power , medium should use max 30% of the CPU power , big should use max 50% of the CPU power , huge should use max 100% of the CPU power
        if command -v awk &> /dev/null; then
            local APP_CPU_LIMIT_LITTLE=$(awk "BEGIN {print $TOTAL_CPUS * 15 / 100}")
            local APP_CPU_LIMIT_MEDIUM=$(awk "BEGIN {print $TOTAL_CPUS * 30 / 100}")
            local APP_CPU_LIMIT_BIG=$(awk "BEGIN {print $TOTAL_CPUS * 50 / 100}")
            local APP_CPU_LIMIT_HUGE=$(awk "BEGIN {print $TOTAL_CPUS * 100 / 100}")
        else
            local APP_CPU_LIMIT_LITTLE=$(( TOTAL_CPUS * 15 / 100 ))
            local APP_CPU_LIMIT_MEDIUM=$(( TOTAL_CPUS * 30 / 100 ))
            local APP_CPU_LIMIT_BIG=$(( TOTAL_CPUS * 50 / 100 ))
            local APP_CPU_LIMIT_HUGE=$(( TOTAL_CPUS * 100 / 100 ))
            print_and_log "YELLOW" "Warning: awk command not found. Leaving limits setted using nearest integer values."            
        fi
        # Ensure CPU limits are not below minimum
        local APP_CPU_LIMIT_LITTLE=$(awk "BEGIN { if ($APP_CPU_LIMIT_LITTLE < $MIN_CPU_LIMIT) print $MIN_CPU_LIMIT; else print $APP_CPU_LIMIT_LITTLE; }")
        local APP_CPU_LIMIT_MEDIUM=$(awk "BEGIN { if ($APP_CPU_LIMIT_MEDIUM < $MIN_CPU_LIMIT) print $MIN_CPU_LIMIT; else print $APP_CPU_LIMIT_MEDIUM; }")
        local APP_CPU_LIMIT_BIG=$(awk "BEGIN { if ($APP_CPU_LIMIT_BIG < $MIN_CPU_LIMIT) print $MIN_CPU_LIMIT; else print $APP_CPU_LIMIT_BIG; }")
        local APP_CPU_LIMIT_HUGE=$(awk "BEGIN { if ($APP_CPU_LIMIT_HUGE < $MIN_CPU_LIMIT) print $MIN_CPU_LIMIT; else print $APP_CPU_LIMIT_HUGE; }")


        # Get the total RAM of the machine in MB
        TOTAL_RAM_MB=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 ))
        
        # Get current limits values from .env file
        local CURRENT_APP_CPU_LIMIT_LITTLE=$(grep -oP 'APP_CPU_LIMIT_LITTLE=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_CPU_LIMIT_MEDIUM=$(grep -oP 'APP_CPU_LIMIT_MEDIUM=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_CPU_LIMIT_BIG=$(grep -oP 'APP_CPU_LIMIT_BIG=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_CPU_LIMIT_HUGE=$(grep -oP 'APP_CPU_LIMIT_HUGE=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_RESERV_LITTLE=$(grep -oP 'APP_MEM_RESERV_LITTLE=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_LIMIT_LITTLE=$(grep -oP 'APP_MEM_LIMIT_LITTLE=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_RESERV_MEDIUM=$(grep -oP 'APP_MEM_RESERV_MEDIUM=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_LIMIT_MEDIUM=$(grep -oP 'APP_MEM_LIMIT_MEDIUM=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_RESERV_BIG=$(grep -oP 'APP_MEM_RESERV_BIG=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_LIMIT_BIG=$(grep -oP 'APP_MEM_LIMIT_BIG=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_RESERV_HUGE=$(grep -oP 'APP_MEM_RESERV_HUGE=\K[^#\r]+' ${ENV_FILENAME})
        local CURRENT_APP_MEM_LIMIT_HUGE=$(grep -oP 'APP_MEM_LIMIT_HUGE=\K[^#\r]+' ${ENV_FILENAME})

        # RAM limits: little should reserve at least MIN_RAM_LIMIT MB or the next near power of 2 in MB of 5% of RAM as upperbound and use as max limit the 250% of this value, medium should reserve double of the little value or the next near power of 2 in MB of 10% of RAM as upperbound and use as max limit the 250% of this value, big should reserve double of the medium value or the next near power of 2 in MB of 20% of RAM as upperbound and use as max limit the 250% of this value, huge should reserve double of the big value or the next near power of 2 in MB of 40% of RAM as upperbound and use as max limit the 400% of this value
        # Implementing a cap for high RAM devices reading value from .env.template file it will be like RAM_CAP_MB_DEFAULT=6144m we need the value 6144
        RAM_CAP_MB_DEFAULT=$(grep -oP 'RAM_CAP_MB_DEFAULT=\K[^#\r]+' ${ENV_TEMPLATE_FILENAME} | sed 's/m//')
        # Uncomment the following to simulate a specific amount of RAM for the device
        # TOTAL_RAM_MB=1024
        RAM_CAP_MB=$(( TOTAL_RAM_MB > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : TOTAL_RAM_MB ))
        MAX_USE_RAM_MB=$(( TOTAL_RAM_MB > RAM_CAP_MB ? RAM_CAP_MB : TOTAL_RAM_MB ))

        # Calculate RAM limits
        if command -v awk &> /dev/null; then
            local APP_MEM_RESERV_LITTLE=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $MAX_USE_RAM_MB * 5 / 100}"))
            local APP_MEM_LIMIT_LITTLE=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $APP_MEM_RESERV_LITTLE * 200 / 100}"))
            local APP_MEM_RESERV_MEDIUM=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $MAX_USE_RAM_MB * 10 / 100}"))
            local APP_MEM_LIMIT_MEDIUM=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $APP_MEM_RESERV_MEDIUM * 200 / 100}"))
            local APP_MEM_RESERV_BIG=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $MAX_USE_RAM_MB * 20 / 100}"))
            local APP_MEM_LIMIT_BIG=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $APP_MEM_RESERV_BIG * 200 / 100}"))
            local APP_MEM_RESERV_HUGE=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $MAX_USE_RAM_MB * 40 / 100}"))
            local APP_MEM_LIMIT_HUGE=$(RoundUpPowerOf2 $(awk "BEGIN {printf \"%d\", $APP_MEM_RESERV_HUGE * 200 / 100}"))

        else
            local APP_MEM_RESERV_LITTLE=$(RoundUpPowerOf2 $(( MAX_USE_RAM_MB * 5 / 100 )))
            local APP_MEM_LIMIT_LITTLE=$(RoundUpPowerOf2 $(( APP_MEM_RESERV_LITTLE * 200 / 100 )))
            local APP_MEM_RESERV_MEDIUM=$(RoundUpPowerOf2 $(( MAX_USE_RAM_MB * 10 / 100 )))
            local APP_MEM_LIMIT_MEDIUM=$(RoundUpPowerOf2 $(( APP_MEM_RESERV_MEDIUM * 200 / 100 )))
            local APP_MEM_RESERV_BIG=$(RoundUpPowerOf2 $(( MAX_USE_RAM_MB * 20 / 100 )))
            local APP_MEM_LIMIT_BIG=$(RoundUpPowerOf2 $(( APP_MEM_RESERV_BIG * 200 / 100 )))
            local APP_MEM_RESERV_HUGE=$(RoundUpPowerOf2 $(( MAX_USE_RAM_MB * 40 / 100 )))
            local APP_MEM_LIMIT_HUGE=$(RoundUpPowerOf2 $(( APP_MEM_RESERV_HUGE * 200 / 100 )))

            print_and_log "YELLOW" "Warning: awk command not found. Limits setted using nearest integer values."
        fi

        # Ensure the calculated values do not exceed RAM_CAP_MB_DEFAULT
        APP_MEM_RESERV_LITTLE=$((APP_MEM_RESERV_LITTLE > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_RESERV_LITTLE))
        APP_MEM_LIMIT_LITTLE=$((APP_MEM_LIMIT_LITTLE > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_LIMIT_LITTLE))
        APP_MEM_RESERV_MEDIUM=$((APP_MEM_RESERV_MEDIUM > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_RESERV_MEDIUM))
        APP_MEM_LIMIT_MEDIUM=$((APP_MEM_LIMIT_MEDIUM > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_LIMIT_MEDIUM))
        APP_MEM_RESERV_BIG=$((APP_MEM_RESERV_BIG > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_RESERV_BIG))
        APP_MEM_LIMIT_BIG=$((APP_MEM_LIMIT_BIG > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_LIMIT_BIG))
        APP_MEM_RESERV_HUGE=$((APP_MEM_RESERV_HUGE > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_RESERV_HUGE))
        APP_MEM_LIMIT_HUGE=$((APP_MEM_LIMIT_HUGE > RAM_CAP_MB_DEFAULT ? RAM_CAP_MB_DEFAULT : APP_MEM_LIMIT_HUGE))

        # Ensure RAM limits are not below minimum
        APP_MEM_RESERV_LITTLE=$(awk "BEGIN { if ($APP_MEM_RESERV_LITTLE < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_RESERV_LITTLE; }")
        APP_MEM_LIMIT_LITTLE=$(awk "BEGIN { if ($APP_MEM_LIMIT_LITTLE < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_LIMIT_LITTLE; }")
        APP_MEM_RESERV_MEDIUM=$(awk "BEGIN { if ($APP_MEM_RESERV_MEDIUM < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_RESERV_MEDIUM; }")
        APP_MEM_LIMIT_MEDIUM=$(awk "BEGIN { if ($APP_MEM_LIMIT_MEDIUM < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_LIMIT_MEDIUM; }")
        APP_MEM_RESERV_BIG=$(awk "BEGIN { if ($APP_MEM_RESERV_BIG < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_RESERV_BIG; }")
        APP_MEM_LIMIT_BIG=$(awk "BEGIN { if ($APP_MEM_LIMIT_BIG < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_LIMIT_BIG; }")
        APP_MEM_RESERV_HUGE=$(awk "BEGIN { if ($APP_MEM_RESERV_HUGE < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_RESERV_HUGE; }")
        APP_MEM_LIMIT_HUGE=$(awk "BEGIN { if ($APP_MEM_LIMIT_HUGE < $MIN_RAM_LIMIT) print $MIN_RAM_LIMIT; else print $APP_MEM_LIMIT_HUGE; }")

        # Update the CPU limits with the new values
        sed -i "s/APP_CPU_LIMIT_LITTLE=${CURRENT_APP_CPU_LIMIT_LITTLE}/APP_CPU_LIMIT_LITTLE=${APP_CPU_LIMIT_LITTLE}/" $ENV_FILENAME
        sed -i "s/APP_CPU_LIMIT_MEDIUM=${CURRENT_APP_CPU_LIMIT_MEDIUM}/APP_CPU_LIMIT_MEDIUM=${APP_CPU_LIMIT_MEDIUM}/" $ENV_FILENAME
        sed -i "s/APP_CPU_LIMIT_BIG=${CURRENT_APP_CPU_LIMIT_BIG}/APP_CPU_LIMIT_BIG=${APP_CPU_LIMIT_BIG}/" $ENV_FILENAME
        sed -i "s/APP_CPU_LIMIT_HUGE=${CURRENT_APP_CPU_LIMIT_HUGE}/APP_CPU_LIMIT_HUGE=${APP_CPU_LIMIT_HUGE}/" $ENV_FILENAME
        # Update RAM limits with the new values unsing as unit MB
        sed -i "s/APP_MEM_RESERV_LITTLE=${CURRENT_APP_MEM_RESERV_LITTLE}/APP_MEM_RESERV_LITTLE=${APP_MEM_RESERV_LITTLE}m/" $ENV_FILENAME
        sed -i "s/APP_MEM_LIMIT_LITTLE=${CURRENT_APP_MEM_LIMIT_LITTLE}/APP_MEM_LIMIT_LITTLE=${APP_MEM_LIMIT_LITTLE}m/" $ENV_FILENAME
        sed -i "s/APP_MEM_RESERV_MEDIUM=${CURRENT_APP_MEM_RESERV_MEDIUM}/APP_MEM_RESERV_MEDIUM=${APP_MEM_RESERV_MEDIUM}m/" $ENV_FILENAME
        sed -i "s/APP_MEM_LIMIT_MEDIUM=${CURRENT_APP_MEM_LIMIT_MEDIUM}/APP_MEM_LIMIT_MEDIUM=${APP_MEM_LIMIT_MEDIUM}m/" $ENV_FILENAME
        sed -i "s/APP_MEM_RESERV_BIG=${CURRENT_APP_MEM_RESERV_BIG}/APP_MEM_RESERV_BIG=${APP_MEM_RESERV_BIG}m/" $ENV_FILENAME
        sed -i "s/APP_MEM_LIMIT_BIG=${CURRENT_APP_MEM_LIMIT_BIG}/APP_MEM_LIMIT_BIG=${APP_MEM_LIMIT_BIG}m/" $ENV_FILENAME
        sed -i "s/APP_MEM_RESERV_HUGE=${CURRENT_APP_MEM_RESERV_HUGE}/APP_MEM_RESERV_HUGE=${APP_MEM_RESERV_HUGE}m/" $ENV_FILENAME
        sed -i "s/APP_MEM_LIMIT_HUGE=${CURRENT_APP_MEM_LIMIT_HUGE}/APP_MEM_LIMIT_HUGE=${APP_MEM_LIMIT_HUGE}m/" $ENV_FILENAME

        # If debug mode is enabled print the calculated limits values
        if [[ "$DEBUG" == "true" ]]; then
            print_and_log "DEFAULT" "Total CPUs: $TOTAL_CPUS"
            print_and_log "DEFAULT" "APP_CPU_LIMIT_LITTLE: $APP_CPU_LIMIT_LITTLE"
            print_and_log "DEFAULT" "APP_CPU_LIMIT_MEDIUM: $APP_CPU_LIMIT_MEDIUM"
            print_and_log "DEFAULT" "APP_CPU_LIMIT_BIG: $APP_CPU_LIMIT_BIG"
            print_and_log "DEFAULT" "APP_CPU_LIMIT_HUGE: $APP_CPU_LIMIT_HUGE"
            print_and_log "DEFAULT" "Total RAM: $TOTAL_RAM_MB MB"
            print_and_log "DEFAULT" "APP_MEM_RESERV_LITTLE: $APP_MEM_RESERV_LITTLE MB"
            print_and_log "DEFAULT" "APP_MEM_LIMIT_LITTLE: $APP_MEM_LIMIT_LITTLE MB"
            print_and_log "DEFAULT" "APP_MEM_RESERV_MEDIUM: $APP_MEM_RESERV_MEDIUM MB"
            print_and_log "DEFAULT" "APP_MEM_LIMIT_MEDIUM: $APP_MEM_LIMIT_MEDIUM MB"
            print_and_log "DEFAULT" "APP_MEM_RESERV_BIG: $APP_MEM_RESERV_BIG MB"
            print_and_log "DEFAULT" "APP_MEM_LIMIT_BIG: $APP_MEM_LIMIT_BIG MB"
            print_and_log "DEFAULT" "APP_MEM_RESERV_HUGE: $APP_MEM_RESERV_HUGE MB"
            print_and_log "DEFAULT" "APP_MEM_LIMIT_HUGE: $APP_MEM_LIMIT_HUGE MB"
            #read -r -p "Press Enter to continue"
        fi

    else
        echo "Warning: Required commands not found. Leaving limits at default values."
    fi
}

# Function to check if there are any updates available #
check_project_updates() {
    # Get the current script version from the local .env file
    SCRIPT_VERSION=$(grep -oP 'PROJECT_VERSION=\K[^#\r]+' "./${ENV_FILENAME}")
    if [[ -z $SCRIPT_VERSION ]]; then
        errorprint_and_log "Failed to get the script version from the local .env file."
        return 1
    fi

    # Get the latest script version from the .env.template file on GitHub
    LATEST_SCRIPT_VERSION=$(curl -fs "$PROJECT_URL/$ENV_TEMPLATE_FILENAME" | grep -oP 'PROJECT_VERSION=\K[^#\r]+')
    if [[ -z $LATEST_SCRIPT_VERSION ]]; then
        errorprint_and_log "Failed to get the latest script version from GitHub."
        return 1
    fi

    # Split the versions into major, minor, and patch numbers
    IFS='.' read -ra SCRIPT_VERSION_SPLIT <<< "$SCRIPT_VERSION"
    IFS='.' read -ra LATEST_SCRIPT_VERSION_SPLIT <<< "$LATEST_SCRIPT_VERSION"

    # Compare the versions and print a message if a newer version is available
    for i in "${!SCRIPT_VERSION_SPLIT[@]}"; do
        if (( ${SCRIPT_VERSION_SPLIT[i]} < ${LATEST_SCRIPT_VERSION_SPLIT[i]} )); then
            print_and_log "YELLOW" "A newer version of the script is available. Please consider updating."
            return 0  # Return here to exit the function as soon as a newer version is found
        elif (( ${SCRIPT_VERSION_SPLIT[i]} > ${LATEST_SCRIPT_VERSION_SPLIT[i]} )); then
            # If any part of the local version is greater, it's not an older version
            return 0
        fi
    done

    # If the loop completes without finding a newer version, you're up to date
    print_and_log "BLUE" "Script is up to date."
}

# Function to detect OS
detect_os() {
    toLog_ifDebug -l "[DEBUG]" -m "Detecting OS..."
    if ! command -v uname -s &> /dev/null; then
        toLog_ifDebug -l "[WARN]" -m "uname command not found, OS detection failed. OS type will be set to 'unknown'."
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
    toLog_ifDebug -l "[DEBUG]" -m "OS type detected: $OS_TYPE"
}

# Function to detect OS architecture and set the relative Docker architecture
detect_architecture() {
    toLog_ifDebug -l "[DEBUG]" -m "Detecting system architecture..."
    if ! command -v uname -m &> /dev/null; then
        toLog_ifDebug -l "[DEBUG]" -m "uname command not found, architecture detection failed. Architecture will be set to 'unknown'."
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
    toLog_ifDebug -l "[DEBUG]" -m "System architecture detected: $ARCH, Docker architecture has been set to $DKARCH"
}

# Function to check if dependencies packages are installed and install them if not #
fn_install_packages() {
    toLog_ifDebug -l "[DEBUG]" -m "Checking if required packages are installed..."
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
        toLog_ifDebug -l "[DEBUG]" -m "Detected package manager: $PKG_MANAGER"
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
    toLog_ifDebug -l "[DEBUG]" -m "Required packages installation completed."
}

## Multiarch emulation service installer function ##
fn_addDockerBinfmtSVC() {
    toLog_ifDebug -l "[DEBUG]" -m "Installing multiarch emulation service..."
    # Check if the service file exists if it does then check if it is enabled and if not enable it, if its enabled then check if the content is the same as the one in the script and if not overwrite it then start the service
    toLog_ifDebug -l "[DEBUG]" -m "Checking if the service already exists..."
    if [ -f "/etc/systemd/system/docker.binfmt.service" ]; then
        # Compare the contents of the existing service file with the one in $FILES_DIR
        toLog_ifDebug -l "[DEBUG]" -m "Service already exists, comparing contents..."
        if ! cmp -s "/etc/systemd/system/docker.binfmt.service" "$FILES_DIR/docker.binfmt.service"; then
            # The contents are different, overwrite the existing service file
            toLog_ifDebug -l "[DEBUG]" -m "Service contents are different, overwriting the file of the existing service..."
            if ! sudo cp "$FILES_DIR/docker.binfmt.service" /etc/systemd/system; then
                fn_fail "Failed to copy service file. Please check your permissions and the file path."
            fi
        fi

        # Check if the service is enabled
        toLog_ifDebug -l "[DEBUG]" -m "Checking if the service is enabled..."
        if [ -d "/etc/systemd/system" ]; then
            # Systemd-based distributions
            toLog_ifDebug -l "[DEBUG]" -m "Systemd-based distribution detected, checking if the service is enabled..."
            if ! systemctl is-enabled --quiet docker.binfmt.service; then
                # Enable the service
                toLog_ifDebug -l "[DEBUG]" -m "Service is not enabled, enabling it..."
                if ! sudo systemctl enable docker.binfmt.service; then
                    fn_fail "Failed to enable docker.binfmt.service. Please check your system config and try to enable the exixting service manually. Then run the script again."
                fi
            fi
        fi
    elif [ -f "/etc/init.d/docker.binfmt" ]; then
        toLog_ifDebug -l "[DEBUG]" -m "SysV init-based distribution detected, checking if the service is enabled..."
        # Compare the contents of the existing service file with the one in $FILES_DIR
        toLog_ifDebug -l "[DEBUG]" -m "Service already exists, comparing contents..."
        if ! cmp -s "/etc/init.d/docker.binfmt" "$FILES_DIR/docker.binfmt.service"; then
            # The contents are different, overwrite the existing service file
            toLog_ifDebug -l "[DEBUG]" -m "Service contents are different, overwriting the file of the existing service..."
            if ! sudo cp "$FILES_DIR/docker.binfmt.service" /etc/init.d/docker.binfmt; then
                fn_fail "Failed to copy service file. Please check your permissions and the file path."
            fi
            sudo chmod +x /etc/init.d/docker.binfmt
        fi

        # Check if the service is enabled
        toLog_ifDebug -l "[DEBUG]" -m "Checking if the service is enabled..."
        if [ -d "/etc/init.d" ]; then
            # SysV init-based distributions
            toLog_ifDebug -l "[DEBUG]" -m "SysV init-based distribution detected, checking if the service is enabled..."
            if ! grep -q "docker.binfmt" /etc/rc.local; then
                # Enable the service
                toLog_ifDebug -l "[DEBUG]" -m "Service is not enabled, enabling it..."
                sudo update-rc.d docker.binfmt defaults
            fi
        fi
    else
        # The service file does not exist, copy it to the appropriate location
        toLog_ifDebug -l "[DEBUG]" -m "Service does not already exists, copying it to the appropriate location..."
        if [ -d "/etc/systemd/system" ]; then
            # Systemd-based distributions
            toLog_ifDebug -l "[DEBUG]" -m "Systemd-based distribution detected, copying service file..."
            sudo cp "$FILES_DIR/docker.binfmt.service" /etc/systemd/system
            sudo systemctl enable docker.binfmt.service
            toLog_ifDebug -l "[DEBUG]" -m "Service file copied and enabled."
        elif [ -d "/etc/init.d" ]; then
            # SysV init-based distributions
            toLog_ifDebug -l "[DEBUG]" -m "SysV init-based distribution detected, copying service file..."
            sudo cp "$FILES_DIR/docker.binfmt.service" /etc/init.d/docker.binfmt
            sudo chmod +x /etc/init.d/docker.binfmt
            sudo update-rc.d docker.binfmt defaults
            toLog_ifDebug -l "[DEBUG]" -m "Service file copied and enabled."
        else
            # Fallback option (handle unsupported systems)
            fn_fail "Warning: I can not find a supported init system. You will have to manually enable the binfmt service. Then restart the script."
        fi
    fi

    # Start the service
    toLog_ifDebug -l "[DEBUG]" -m "Starting the service..."
    if [ -d "/etc/systemd/system" ]; then
        # Systemd-based distributions
        toLog_ifDebug -l "[DEBUG]" -m "Systemd-based distribution detected, starting the service..."
        if ! sudo systemctl start docker.binfmt.service; then
            fn_fail "Failed to start docker.binfmt.service. Please check your system config and try to start the exixting service manually. Then run the script again."
        fi
        toLog_ifDebug -l "[DEBUG]" -m "Service started."
    elif [ -d "/etc/init.d" ]; then
        # SysV init-based distributions
        toLog_ifDebug -l "[DEBUG]" -m "SysV init-based distribution detected, starting the service..."
        if ! sudo service docker.binfmt start; then
            fn_fail "Failed to start docker.binfmt.service. Please check your system config and try to start the exixting service manually. Then run the script again."
        fi
        toLog_ifDebug -l "[DEBUG]" -m "Service started."
    fi
}

### Sub-menu Functions ###
# Shows the liks of the apps
fn_showLinks() {
    clear
    toLog_ifDebug -l "[DEBUG]" -m "Showing apps links"
    colorprint "GREEN" "Use CTRL+Click to open links or copy them:"
    # reading from $APP_CONFIG_JSON_FILE show all the apps type that are the dictionary keys and then show the name and the link of each app in the dictionary
    for app_type in $(jq -r 'keys[]' "$CONFIG_DIR/$APP_CONFIG_JSON_FILE"); do
        colorprint "YELLOW" "---$app_type---"
        for app in $(jq -r ".[\"$app_type\"][].name" "$CONFIG_DIR/$APP_CONFIG_JSON_FILE"); do
            colorprint "DEFAULT" "$app"
            colorprint "CYAN" "$(jq -r ".[\"$app_type\"][] | select(.name==\"$app\") | .link" "$CONFIG_DIR/$APP_CONFIG_JSON_FILE")"
            
        done
    done
    read -r -p "Press Enter to go back to mainmenu"
    toLog_ifDebug -l "[DEBUG]" -m "Links shown, going back to mainmenu"
}

## Docker checker and installer function ##
# Check if docker is installed and if not then it tries to install it automatically
fn_dockerInstall() {
    toLog_ifDebug -l "[DEBUG]" -m "DockerInstall function started"
    clear
    colorprint "YELLOW" "This menu item will launch a script that will attempt to install Docker"
    colorprint "YELLOW" "Use it only if you do not know how to perform the manual Docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some rare cases and depending on the distros may fail to install Docker correctly."
    
    while true; do
        read -r -p "Do you wish to proceed with the Docker automatic installation Y/N? " yn
        case $yn in
            [Yy]* )
                toLog_ifDebug -l "[DEBUG]" -m "User decided to install Docker through the script. Checking if Docker is already installed."
                if docker --version >/dev/null 2>&1; then
                    toLog_ifDebug -l "[DEBUG]" -m "Docker is already installed. Asking user if he wants to continue with the installation anyway."
                    while true; do
                        colorprint "YELLOW" "It seems that Docker is already installed. Do you want to continue with the installation anyway? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                toLog_ifDebug -l "[DEBUG]" -m "User decided to continue with the Docker re-install anyway."
                                break
                                ;;
                            [Nn]* )
                                toLog_ifDebug -l "[DEBUG]" -m "User decided to abort the Docker re-install."
                                read -r -p "Press Enter to go back to mainmenu"
                                sleep "$SLEEP_TIME"
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
    toLog_ifDebug -l "[DEBUG]" -m "SetupNotifications function started"
    clear
    while true; do
        colorprint "YELLOW" "Do you wish to setup notifications about apps images updates (Yes to receive notifications and apply updates, No to just silently apply updates) Y/N?"
        read -r yn
        case $yn in
            [Yy]* )
                toLog_ifDebug -l "[DEBUG]" -m "User decided to setup notifications about apps images updates."
                colorprint "YELLOW" "This step will setup notifications about containers updates using shoutrrr"
                colorprint "DEFAULT" "The resulting SHOUTRRR_URL should have the format: <app>://<token>@<webhook>."
                colorprint "DEFAULT" "Where <app> is one of the supported messaging apps on Shoutrrr (e.g. Discord), and <token> and <webhook> are specific to your messaging app."
                colorprint "DEFAULT" "To obtain the SHOUTRRR_URL, create a new webhook for your messaging app and rearrange its URL to match the format above."
                colorprint "DEFAULT" "For more details, visit https://containrrr.dev/shoutrrr/ and select your messaging app."
                colorprint "DEFAULT" "Now a Discord notification setup example will be shown (Remember: you can also use a different supported app)."
                read -r -p "Press enter to continue"
                clear
                colorprint "MAGENTA" "Create a new Discord server, go to server settings > integrations, and create a webhook."
                colorprint "MAGENTA" "Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken."
                colorprint "MAGENTA" "To obtain the SHOUTRRR_URL, rearrange it to look like this: discord://YourToken@YourWebhookid."
                read -r -p "Press enter to proceed with the setup"
                clear
                while true; do
                    colorprint "YELLOW" "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"
                    read -r SHOUTRRR_URL
                    if [[ "$SHOUTRRR_URL" =~ ^[a-zA-Z]+:// ]]; then
                        # Replace the lines in the ${ENV_FILENAME} file and in the $DKCOM_FILENAME file
                        sed -i "s~# SHOUTRRR_URL=~SHOUTRRR_URL=~" ${ENV_FILENAME}
                        CURRENT_VALUE=$(grep -oP 'SHOUTRRR_URL=\K[^#\r]+' ${ENV_FILENAME})
                        sed -i "s~SHOUTRRR_URL=${CURRENT_VALUE}~SHOUTRRR_URL=$SHOUTRRR_URL~" ${ENV_FILENAME}
                        sed -i "s~# - WATCHTOWER_NOTIFICATIONS=shoutrrr~- WATCHTOWER_NOTIFICATIONS=shoutrrr~" "$DKCOM_FILENAME"
                        sed -i "s~# - WATCHTOWER_NOTIFICATION_URL~- WATCHTOWER_NOTIFICATION_URL~" "$DKCOM_FILENAME"
                        sed -i "s~# - WATCHTOWER_NOTIFICATIONS_HOSTNAME~- WATCHTOWER_NOTIFICATIONS_HOSTNAME~" "$DKCOM_FILENAME"
                        sed -i 's/NOTIFICATIONS_CONFIGURATION_STATUS=0/NOTIFICATIONS_CONFIGURATION_STATUS=1/' ${ENV_FILENAME}
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
                                [Nn]* ) 
                                    toLog_ifDebug -l "[DEBUG]" -m "User choose to not retry the notifications setup. Notifications wsetup will now return"
                                    colorprint "BLUE" "Noted: all updates will be applied automatically and silently";
                                    sleep "$SLEEP_TIME"
                                    return;;

                                * ) colorprint "RED" "Please answer yes or no.";;
                            esac
                        done
                    fi
                done
                break;;
            [Nn]* )
                toLog_ifDebug -l "[DEBUG]" -m "User choose to skip notifications setup"
                colorprint "BLUE" "Noted: all updates will be applied automatically and silently";
                sleep "$SLEEP_TIME"
                break;;
            * )
                colorprint "RED" "Please answer yes or no.";;
        esac
    done

    clear
    toLog_ifDebug -l "[DEBUG]" -m "SetupNotifications function ended"
}


fn_setupApp() {
    toLog_ifDebug -l "[DEBUG]" -m "SetupApp function started"
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
    toLog_ifDebug -l "[DEBUG]" -m "SetupApp function parameters: app_json=$app_json, dk_compose_filename=$dk_compose_filename"
    # Extract the necessary fields from the app json
    toLog_ifDebug -l "[DEBUG]" -m "Extracting necessary fields from the passed app json"
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
        toLog_ifDebug -l "[DEBUG]" -m "Checking if the ${CURRENT_APP} app is already enabled in the ${dk_compose_filename} file"
        if grep -q "#ENABLE_${CURRENT_APP}" "${dk_compose_filename}"; then
            toLog_ifDebug -l "[DEBUG]" -m "${CURRENT_APP} is not enabled in the ${dk_compose_filename} file, asking the user if they want to enable it"
            # Show the generic message before asking the user if they want to enable the app
            colorprint "YELLOW" "PLEASE REGISTER ON THE PLATFORMS USING THE LINKS THAT WILL BE PROVIDED, YOU'LL THEN NEED TO ENTER SOME DATA BELOW:"
            # Ask the user if they want to enable the ${CURRENT_APP}
            colorprint "YELLOW" "Do you wish to enable and use ${CURRENT_APP}? (Y/N)"
            read -r yn
            case $yn in
                [Yy]* )
                    toLog_ifDebug -l "[DEBUG]" -m "User decided to enable and use ${CURRENT_APP}"
                    colorprint "CYAN" "Go to ${CURRENT_APP} ${link} and register"
                    colorprint "GREEN" "Use CTRL+Click to open links or copy them:"
                    read -r -p "When you are done press Enter to continue"
                    toLog_ifDebug -l "[DEBUG]" -m "Enabling ${CURRENT_APP} app. The parameters received are: name=$name, link=$link, image=$app_image, flags=${flags[*]}, claimURLBase=$claimURLBase"
                    # Read the flags in the array and execute the relative logic using the case statement
                    for flag_name in "${flags[@]}"; do
                        # Extract flag details and all the parameters if they exist 
                        local flag_details
                        flag_details=$(jq -r ".flags[\"$flag_name\"]?" <<< "$app_json")
                        toLog_ifDebug -l "[DEBUG]" -m "Result of flag_details reading: $flag_details"
                        if [[ "$flag_details" != "null" ]]; then
                            #load all the flags parameters keys in an array so then we cann iterate on them and access their values easily from the json
                            local flag_params_keys
                            flag_params_keys=$(jq -r "keys[]?" <<< "$flag_details")
                            toLog_ifDebug -l "[DEBUG]" -m "Result of flag_params_keys reading: $flag_params_keys"
                        else
                            toLog_ifDebug -l "[DEBUG]" -m "No flag details found for flag: $flag_name"
                        fi
                        case $flag_name in
                            --email)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting email setup for ${CURRENT_APP} app"
                                while true; do
                                    colorprint "GREEN" "Enter your ${CURRENT_APP} Email:"
                                    read -r APP_EMAIL
                                    if [[ "$APP_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
                                        sed -i "s/your${CURRENT_APP}Mail/$APP_EMAIL/" ${ENV_FILENAME}
                                        break
                                    else
                                        colorprint "RED" "Invalid email address. Please try again."
                                    fi
                                done
                                ;;
                            --password)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting password setup for ${CURRENT_APP} app"
                                while true; do
                                    colorprint "DEFAULT" "Note: If you are using login with Google, remember to set also a password for your ${CURRENT_APP} account!"
                                    colorprint "GREEN" "Enter your ${CURRENT_APP} Password:"
                                    read -r APP_PASSWORD
                                    if [[ -z "$APP_PASSWORD" ]]; then
                                        colorprint "RED" "Password cannot be empty. Please try again."
                                    else
                                        sed -i "s/your${CURRENT_APP}Pw/$APP_PASSWORD/" ${ENV_FILENAME}
                                        break
                                    fi
                                done
                                ;;
                            --apikey)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting APIKey setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find/Generate your APIKey inside your ${CURRENT_APP} dashboard/profile."
                                while true; do
                                    colorprint "GREEN" "Enter your ${CURRENT_APP} APIKey:"
                                    read -r APP_APIKEY
                                    if [[ -z "$APP_APIKEY" ]]; then
                                        colorprint "RED" "APIKey cannot be empty. Please try again."
                                    else
                                        sed -i "s^your${CURRENT_APP}APIKey^$APP_APIKEY^" ${ENV_FILENAME}
                                        break
                                    fi
                                done
                                ;;
                            --userid)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting UserID setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find your UserID inside your ${CURRENT_APP} dashboard/profile."
                                while true; do
                                    colorprint "GREEN" "Enter your ${CURRENT_APP} UserID:"
                                    read -r APP_USERID
                                    if [[ -z "$APP_USERID" ]]; then
                                        colorprint "RED" "UserID cannot be empty. Please try again."
                                    else
                                        sed -i "s/your${CURRENT_APP}UserID/$APP_USERID/" ${ENV_FILENAME}
                                        break
                                    fi
                                done
                                ;;
                            --uuid)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting UUID setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Starting UUID generation/import for ${CURRENT_APP}"
                                # Read all the parameters for the uuid flag , if one of them is the case length then save it in a variable
                                if [[ -n "${flag_params_keys:-}" ]]; then
                                    for flag_param_key in $flag_params_keys; do
                                        toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter: $flag_param_key"
                                        case $flag_param_key in
                                            length)
                                                toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter length"
                                                flag_length_param=$(jq -r ".flags[\"$flag_name\"][\"$flag_param_key\"]?" <<< "$app_json")
                                                toLog_ifDebug -l "[DEBUG]" -m "Result of flag_length_param reading: $flag_length_param"
                                                ;;
                                            *)
                                                toLog_ifDebug -l "[DEBUG]" -m "Unknown flag parameter: $flag_param_key"
                                                ;;
                                        esac
                                    done
                                else
                                    toLog_ifDebug -l "[DEBUG]" -m "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                                fi

                                # Check if the flag_length_param exists and if is a number (i.e., the desired length)
                                if [[ -n "${flag_length_param:-}" ]] && [[ "${flag_length_param:-}" =~ ^[0-9]+$ ]]; then
                                    DESIRED_LENGTH="$flag_length_param"
                                    toLog_ifDebug -l "[DEBUG]" -m "Desired length for UUID generation/import passed as argument of the uuid flag (read from json), its value is: $DESIRED_LENGTH"
                                else
                                    # If no length is provided, ask the user
                                    toLog_ifDebug -l "[DEBUG]" -m "No desired length for UUID generation/import passed as argument of the uuid flag, asking the user"
                                    colorprint "GREEN" "Enter desired length for the UUID (default is 32, press Enter to use default):"
                                    read -r DESIRED_LENGTH_INPUT
                                    DESIRED_LENGTH=${DESIRED_LENGTH_INPUT:-32}  # Defaulting to 32 if no input provided
                                fi
                                toLog_ifDebug -l "[DEBUG]" -m "Starting temporary UUID generation/import for ${CURRENT_APP} with desired length: $DESIRED_LENGTH. This will be overwritten if the user chooses to use an existing UUID."
                                local UUID=""
                                while [ ${#UUID} -lt "$DESIRED_LENGTH" ]; do
                                    # Regenerate the salt for each iteration
                                    SALT="${DEVICE_NAME}""${RANDOM}""${UUID}"  # Incorporate the previously generated UUID part for added randomness
                                    UUID_PART="$(echo -n "$SALT" | md5sum | cut -c1-32)"
                                    UUID+="$UUID_PART"
                                done
                            
                                # Cut or trail the generated UUID based on the desired length
                                UUID=${UUID:0:$DESIRED_LENGTH}
                                toLog_ifDebug -l "[DEBUG]" -m "Done, generated temporary UUID: $UUID"
                                
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
                                                        [Yy]* ) continue ;;
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
                                
                                sed -i "s/your${CURRENT_APP}DeviceUUID/$UUID/" ${ENV_FILENAME}
                                colorprint "DEFAULT" "${CURRENT_APP} UUID setup: done"
                                # Generaing the claim link
                                local claimlink="${claimURLBase}${UUID}"
                                colorprint "BLUE" "Save the following link somewhere to claim/register your ${CURRENT_APP} node/device after completing the setup and starting the apps stack: ${claimlink}"
                                echo "${claimlink}" > "claim${CURRENT_APP}NodeDevice.txt"
                                colorprint "DEFAULT" "A new file containing this link has been created for you in the current directory"
                                ;;
                            --cid)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting CID setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find your CID inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "DEFAULT" "Example: For packetstream you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
                                while true; do
                                    colorprint "GREEN" "Enter your ${CURRENT_APP} CID:"
                                    read -r APP_CID
                                    if [[ -z "$APP_CID" ]]; then
                                        colorprint "RED" "CID cannot be empty. Please try again."
                                    else
                                        sed -i "s/your${CURRENT_APP}CID/$APP_CID/" ${ENV_FILENAME}
                                        break
                                    fi
                                done
                                ;;
                            --token)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting token setup for ${CURRENT_APP} app"
                                colorprint "DEFAULT" "Find your token inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "DEFAULT" "Example: For traffmonetizer you can fetch it from your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
                                while true; do
                                    colorprint "GREEN" "Enter your ${CURRENT_APP} token:"
                                    read -r APP_TOKEN
                                    if [[ -z "$APP_TOKEN" ]]; then
                                        colorprint "RED" "Token cannot be empty. Please try again."
                                    else
                                        sed -i "s^your${CURRENT_APP}Token^$APP_TOKEN^" ${ENV_FILENAME}
                                        break
                                    fi
                                done
                                ;;
                            --customScript)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting customScript setup for ${CURRENT_APP} app"
                                # Read all the parameters for the customScript flag , if one of them is the case scriptname then save it in a variable
                                if [[ -n "${flag_params_keys:-}" ]]; then
                                    for flag_param_key in $flag_params_keys; do
                                        toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter: $flag_param_key"
                                        case $flag_param_key in
                                            scriptname)
                                                toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter scriptname"
                                                flag_scriptname_param=$(jq -r ".flags[\"$flag_name\"][\"$flag_param_key\"]?" <<< "$app_json")
                                                toLog_ifDebug -l "[DEBUG]" -m "Result of flag_scriptname_param reading: $flag_scriptname_param"
                                                ;;
                                            *)
                                                toLog_ifDebug -l "[DEBUG]" -m "Unknown flag parameter: $flag_param_key"
                                                ;;
                                        esac
                                    done
                                else
                                    toLog_ifDebug -l "[DEBUG]" -m "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                                fi
                                CUSTOM_SCRIPT_NAME="${flag_scriptname_param}.sh"
                                SCRIPT_PATH="$SCRIPTS_DIR/$CUSTOM_SCRIPT_NAME"
                                ESCAPED_PATH="${SCRIPT_PATH//\"/\\\"}"
                                toLog_ifDebug -l "[DEBUG]" -m "Starting custom script execution for ${CURRENT_APP} app using $SCRIPT_NAME from $ESCAPED_PATH"
                                if [[ -f "$SCRIPT_PATH" ]]; then
                                    chmod +x "$ESCAPED_PATH"
                                    colorprint "DEFAULT" "Executing custom script: $CUSTOM_SCRIPT_NAME"
                                    source "$ESCAPED_PATH"
                                else
                                    colorprint "RED" "Custom script '$CUSTOM_SCRIPT_NAME' not found in the scripts directory."
                                fi
                                ;;
                            --manual)
                                toLog_ifDebug -l "[DEBUG]" -m "Starting manual setup for ${CURRENT_APP} app"
                                colorprint "BLUE" "${CURRENT_APP} requires further manual configuration."
                                # Read all the parameters for the manual flag , if one of them is the case instructions then save it in a variable and then prin the instruction to the user
                                if [[ -n "${flag_params_keys:-}" ]]; then
                                    for flag_param_key in $flag_params_keys; do
                                        toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter: $flag_param_key"
                                        case $flag_param_key in
                                            instructions)
                                                toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter instructions"
                                                flag_instructions_param=$(jq -r ".flags[\"$flag_name\"][\"$flag_param_key\"]?" <<< "$app_json")
                                                if [[ -n "${flag_instructions_param:-}" ]]; then
                                                    toLog_ifDebug -l "[DEBUG]" -m "Result of flag_instructions_param reading: $flag_instructions_param"
                                                    colorprint "YELLOW" "$flag_instructions_param"
                                                else
                                                    toLog_ifDebug -l "[DEBUG]" -m "No instructions found for flag: $flag_name inside $flag_param_key as flag_instructions_param is empty"
                                                fi
                                                ;;
                                            *)
                                                toLog_ifDebug -l "[DEBUG]" -m "Unknown flag parameter: $flag_param_key"
                                                ;;
                                        esac
                                    done
                                else
                                    toLog_ifDebug -l "[DEBUG]" -m "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                                fi
                                colorprint "YELLOW" "Please after completing this automated setup check also the app's website for further instructions if there are any."
                                ;; 
                            *)
                                fn_fail "Unknown ${flag_name} flag passed to setupApp function"
                                ;;  
                        esac
                    done
                    # Complete the setup of the app by enabling it in the docker-compose file
                    sed -i "s^#ENABLE_${CURRENT_APP}^^" "${dk_compose_filename}"
                    toLog_ifDebug -l "[DEBUG]" -m "Enabled ${CURRENT_APP} app in ${dk_compose_filename}"

                    # App Docker image architecture adjustments
                    toLog_ifDebug -l "[DEBUG]" -m "Starting Docker image architecture adjustments for ${CURRENT_APP} app"
                    TAG=$(grep -oP "\s*image: ${app_image}:\K[^\s#]+" $DKCOM_FILENAME)
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
                            sed -i "s^${app_image}:${TAG}^${app_image}:$NEWTAG^" $DKCOM_FILENAME
                        fi
                    else 
                        colorprint "YELLOW" "No native image tag found for $DKARCH arch, emulation layer will try to run this app image anyway."
                        colorprint "DEFAULT" "If an emulation layer is not already installed, the script will try to install it now. Please provide your sudo password if prompted."
                        #fn_install_packages qemu binfmt-support qemu-user-static
                        fn_addDockerBinfmtSVC
                    fi
                    local currentTag=$(grep -oP "${app_image}:\K[^#\r]+" $DKCOM_FILENAME)
                    toLog_ifDebug -l "[DEBUG]" -m "Finished Docker image architecture adjustments for ${CURRENT_APP} app. Its image tag is now: $currentTag"
                    read -r -p "${CURRENT_APP} configuration complete, press enter to continue to the next app"
                    toLog_ifDebug -l "[DEBUG]" -m "Finished setupApp function for ${CURRENT_APP} app"
                    break
                    ;;
                [Nn]* )
                    toLog_ifDebug -l "[DEBUG]" -m "User decided to skip ${CURRENT_APP} setup"
                    colorprint "BLUE" "Ok, ${CURRENT_APP} setup will be skipped."
                    sleep ${SLEEP_TIME}
                    break
                    ;;
                * )
                    colorprint "RED" "Please answer yes or no."
                    ;;
            esac
        else
            print_and_log "BLUE" "${CURRENT_APP} is already enabled in the ${dk_compose_filename} file"
            sleep ${SLEEP_TIME}
            break
        fi
    done
}

fn_setupProxy() {
    toLog_ifDebug -l "[DEBUG]" -m "Starting setupProxy function"
    if [ "$PROXY_CONF" == 'false' ]; then
        while true; do
            colorprint "YELLOW" "Do you wish to setup a proxy for the apps in this stack Y/N?"
            colorprint "DEFAULT" "Note that if you want to run multiple instances of the same app you will need to configure different env files each in different project folders (copy the project to multiple different folders and configure them using different proxies)"
            read -r yn
            case $yn in
                [Yy]* )
                    clear
                    toLog_ifDebug -l "[DEBUG]" -m "User chose to setup a proxy"
                    colorprint "YELLOW" "Proxy setup started."

                    # Read current names values
                    FULL_COMPOSE_PROJECT_NAME=$(grep -oP 'COMPOSE_PROJECT_NAME=\K[^#\r]+' ${ENV_FILENAME})
                    FULL_DEVICE_NAME=$(grep -oP 'DEVICE_NAME=\K[^#\r]+' ${ENV_FILENAME})

                    # Shorten the project name by removing all the trailing numbers and underscores if present
                    SHORT_COMPOSE_PROJECT_NAME=$(echo "$FULL_COMPOSE_PROJECT_NAME" | sed -E 's/[_*0-9]+$//')
                    # Shorten the device name by removing all the trailing numbers if present
                    SHORT_DEVICE_NAME=$(echo "$FULL_DEVICE_NAME" | sed -E 's/[0-9]+$//')

                    # Generate a random value to append to the project name and device name to make them unique
                    readonly RANDOM_VALUE=$RANDOM
                    colorprint "GREEN" "Insert the designed proxy to use. Eg: protocol://proxyUsername:proxyPassword@proxy_url:proxy_port or just protocol://proxy_url:proxy_port if auth is not needed"
                    read -r NEW_STACK_PROXY
                    # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                    # ATTENTION: if a random value has been already added to the project and devicename during a previous setup it should remain the same to mantain consistency with the devices name registered on the apps sites but the proxy url could be changed
                    # If this is not the first setup proxy (proxy setup already configued in the past) then Ask the user if they wnat to keep the current project and device name, in the case they are just changing the proxy url for an existing stack that they want to keep or if they want to change the project and device name as well usable on a new stack runnin on the same device or on a different one
                    SKIP_NAMES_CHANGE_FOR_PROXY_SETUP=false
                    if [ "$PROXY_CONFIGURATION_STATUS" == "1" ]; then
                        while true; do
                            colorprint "BLUE" "The current project name is: $FULL_COMPOSE_PROJECT_NAME"
                            colorprint "BLUE" "The current device name is: $FULL_DEVICE_NAME"
                            colorprint "YELLOW" "Do you want to keep the current project and device name? (Y/N)"
                            colorprint "DEFAULT" "No if you want to run multiple instances of the same app on the same device (copy the project to multiple different folders and configure them using different proxies), the project and device names will slightly change to keep them unique."
                            colorprint "DEFAULT" "Yes if you just want to update the proxy in use without changing the project and device name (One instance of the same app per device)"
                            read -r yn
                            case $yn in
                                [Yy]* )
                                    toLog_ifDebug -l "[DEBUG]" -m "User chose to keep the current project and device name"
                                    colorprint "BLUE" "Ok, the current project and device name will be kept"
                                    SKIP_NAMES_CHANGE_FOR_PROXY_SETUP=true
                                    break
                                    ;;
                                [Nn]* )
                                    toLog_ifDebug -l "[DEBUG]" -m "User chose to change the current project and device name"
                                    colorprint "BLUE" "Ok, the current project and device name will be changed"
                                    break
                                    ;;
                                * ) colorprint "RED" "Please answer yes or no." ;;
                            esac
                        done
                    fi
                    if [ "$SKIP_NAMES_CHANGE_FOR_PROXY_SETUP" == "false" ]; then
                        # Update project name and device name with shortened name and random value
                        sed -i "s^COMPOSE_PROJECT_NAME=${FULL_COMPOSE_PROJECT_NAME}^COMPOSE_PROJECT_NAME=${SHORT_COMPOSE_PROJECT_NAME}_${RANDOM_VALUE}^" ${ENV_FILENAME} 
                        sed -i "s^DEVICE_NAME=${FULL_DEVICE_NAME}^DEVICE_NAME=${SHORT_DEVICE_NAME}${RANDOM_VALUE}^" ${ENV_FILENAME}
                        # Update the DEVICE_NAME variable of the script with the new value
                        DEVICE_NAME="${SHORT_DEVICE_NAME}${RANDOM_VALUE}"
                    fi

                    # Obtaining the line of STACK_PROXY= in the ${ENV_FILENAME} file and then replace the line with the new proxy also uncomment the line if it was commented
                    sed -i "s^# STACK_PROXY=^STACK_PROXY=^" ${ENV_FILENAME} # if it was already uncommented it does nothing
                    CURRENT_VALUE=$(grep -oP 'STACK_PROXY=\K[^#\r]+' ${ENV_FILENAME})
                    sed -i "s^$CURRENT_VALUE^$NEW_STACK_PROXY^" ${ENV_FILENAME}
                    # disable rolling restarts for watchtower as enabling proxy will  make the others containers dependent on it and so rolling restarts will not work
                    sed -i "s^- WATCHTOWER_ROLLING_RESTART=true^- WATCHTOWER_ROLLING_RESTART=false^" "$DKCOM_FILENAME"
                    sed -i 's^#ENABLE_PROXY ^ ^' "$DKCOM_FILENAME"
                    sed -i "s^# network_mode^network_mode^" $DKCOM_FILENAME
                    PROXY_CONF='true'
                    sed -i 's/PROXY_CONFIGURATION_STATUS=0/PROXY_CONFIGURATION_STATUS=1/' ${ENV_FILENAME}
                    colorprint "DEFAULT" "Ok, $NEW_STACK_PROXY will be used as proxy for all apps in this stack"
                    read -r -p "Press enter to continue"
                    toLog_ifDebug -l "[DEBUG]" -m "Proxy setup finished"
                    break
                    ;;
                [Nn]* )
                    toLog_ifDebug -l "[DEBUG]" -m "User chose not to setup a proxy"
                    colorprint "BLUE" "Ok, no proxy will be used for the apps in this stack"
                    sleep ${SLEEP_TIME}
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

    # Check if ${ENV_FILENAME} file is already configured if 1 then it is already configured, if 0 then it is not configured
    check_configuration_status "$ENV_FILENAME"
    if [ "$ENV_CONFIGURATION_STATUS" == "1" ] && [ "$app_type" == "apps" ]; then
        while true; do
            colorprint "YELLOW" "The current ${ENV_FILENAME} file appears to have already been configured. Do you wish to reset it? (Y/N)"
            read -r yn
            case $yn in
                [Yy]* )
                    print_and_log "DEFAULT" "Resetting ${ENV_FILENAME} file and ${DKCOM_FILENAME} file."
                    rm "${ENV_FILENAME}"
                    rm "$DKCOM_FILENAME"
                    cp "${ENV_TEMPLATE_FILENAME}" "${ENV_FILENAME}"
                    cp "${DKCOM_TEMPLATE_FILENAME}" "${DKCOM_FILENAME}"
                    check_configuration_status "$ENV_FILENAME"
                    clear
                    break
                    ;;
                [Nn]* )
                    print_and_log "BLUE" "Keeping the existing ${ENV_FILENAME} file."
                    sleep ${SLEEP_TIME}
                    check_configuration_status "$ENV_FILENAME"
                    clear
                    break
                    ;;
                * )
                    colorprint "RED" "Invalid input. Please answer yes or no."
                    continue
                    ;;
            esac
        done            
    elif [ "$ENV_CONFIGURATION_STATUS" == "1" ] && [ "$app_type" != "apps" ]; then
        print_and_log "BLUE" "Proceeding with $app_type setup without resetting ${ENV_FILENAME} file as it should already be configured by the main apps setup."
        sleep ${SLEEP_TIME}
    fi
    while true; do
        colorprint "YELLOW" "Do you wish to proceed with the ${ENV_FILENAME} file guided setup Y/N? (This will also adapt the $DKCOM_FILENAME file accordingly)"
        read -r yn
        case $yn in
            [Yy]* ) 
                clear
                toLog_ifDebug -l "[DEBUG]" -m "User chose to proceed with the ${ENV_FILENAME} file guided setup for $app_type"
                colorprint "YELLOW" "beginnning env file guided setup"
                # Update the ENV_CONFIGURATION_STATUS
                sed -i 's/ENV_CONFIGURATION_STATUS=0/ENV_CONFIGURATION_STATUS=1/' ${ENV_FILENAME}
                # Device Name setup
                currentDeviceNameInEnv=$(grep -oP 'DEVICE_NAME=\K[^#\r]+' ${ENV_FILENAME})
                if [ "$currentDeviceNameInEnv" == "$DEVICE_NAME_PLACEHOLDER" ]; then
                    toLog_ifDebug -l "[DEBUG]" -m "Device name is still the default one, asking user to change it"
                    colorprint "YELLOW" "PLEASE ENTER A NAME FOR YOUR DEVICE:"
                    read -r DEVICE_NAME
                    sed -i "s/DEVICE_NAME=${DEVICE_NAME_PLACEHOLDER}/DEVICE_NAME=${DEVICE_NAME}/" ${ENV_FILENAME}
                else
                    toLog_ifDebug -l "[DEBUG]" -m "Device name is already set, skipping user input"
                    DEVICE_NAME="$currentDeviceNameInEnv"
                fi
                clear ;
                if [ "$PROXY_CONFIGURATION_STATUS" == "1" ]; then
                    CURRENT_PROXY=$(grep -oP 'STACK_PROXY=\K[^#\r]+' ${ENV_FILENAME})
                    print_and_log "BLUE" "Proxy is already set up."
                    while true; do
                        colorprint "YELLOW" "The current proxy is: ${CURRENT_PROXY} . Do you wish to change it? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                PROXY_CONF='false'
                                toLog_ifDebug -l "[DEBUG]" -m "User chose to change the proxy that was already configured"
                                fn_setupProxy;
                                break;;
                            [Nn]* )
                                toLog_ifDebug -l "[DEBUG]" -m "User chose not to change the proxy that was already configured"
                                print_and_log "BLUE" "Keeping the existing proxy."
                                sleep ${SLEEP_TIME}
                                break;;
                            * )
                                colorprint "RED" "Invalid input. Please answer yes or no.";;
                        esac
                    done                        
                else
                    toLog_ifDebug -l "[DEBUG]" -m "Asking user if they want to setup a proxy as it is not already configured"
                    fn_setupProxy;
                fi
                # Apps setup
                clear ;
                toLog_ifDebug -l "[DEBUG]" -m "Loading $app_type from ${APP_CONFIG_JSON_FILE}..."
                apps=$(jq -c ".[\"$app_type\"][]" "${CONFIG_DIR}/${APP_CONFIG_JSON_FILE}")
                app_number=$(jq -c ".[\"$app_type\"] | length" "${CONFIG_DIR}/${APP_CONFIG_JSON_FILE}")
                toLog_ifDebug -l "[DEBUG]" -m "$app_type loaded from ${APP_CONFIG_JSON_FILE}"
                for (( i=0; i<"$app_number"; i++ )); do # this loop worsks instead the for app in apps will not work as bash split the strings on spaces
                    clear
                    app_name=$(jq -r ".[\"$app_type\"][$i].name" "${CONFIG_DIR}/${APP_CONFIG_JSON_FILE}")
                    toLog_ifDebug -l "[DEBUG]" -m "Starting setupApp function for $app_name app"
                    app_json=$(jq -c ".[\"$app_type\"][$i]" "${CONFIG_DIR}/${APP_CONFIG_JSON_FILE}")
                    fn_setupApp --app-json "$app_json" --dk-compose-filename "$DKCOM_FILENAME"
                    clear
                done

                # Notifications setup
                clear;
                if [ "$NOTIFICATIONS_CONFIGURATION_STATUS" == "1" ]; then
                    print_and_log "BLUE" "Notifications are already set up."
                    while true; do
                        CURRENT_SHOUTRRR_URL=$(grep -oP 'SHOUTRRR_URL=\K[^#\r]+' ${ENV_FILENAME})
                        colorprint "YELLOW" "The current notifications setup uses: ${CURRENT_SHOUTRRR_URL}. Do you wish to change it? (Y/N)"
                        read -r yn
                        case $yn in
                            [Yy]* )
                                toLog_ifDebug -l "[DEBUG]" -m "User chose to change the notifications setup that was already configured"
                                fn_setupNotifications;
                                break;;
                            [Nn]* )
                                toLog_ifDebug -l "[DEBUG]" -m "User chose not to change the notifications setup that was already configured"
                                print_and_log "BLUE" "Keeping the existing notifications setup."
                                break;;
                            * )
                                colorprint "RED" "Invalid input. Please answer yes or no.";;
                        esac
                    done
                else
                    toLog_ifDebug -l "[DEBUG]" -m "Asking user if they want to setup notifications as they are not already configured"
                    fn_setupNotifications;
                fi
                print_and_log "GREEN" "env file setup complete.";
                read -n 1 -s -r -p "Press enter to go back to the menu"$'\n'
                break
                ;;
            [Nn]* )
                toLog_ifDebug -l "[DEBUG]" -m "User chose not to proceed with the ${ENV_FILENAME} file guided setup for $app_type"
                colorprint "BLUE" "${ENV_FILENAME} file setup canceled. Make sure you have a valid ${ENV_FILENAME} file before proceeding with the stack startup."
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
    toLog_ifDebug -l "[DEBUG]" -m "Starting startStack function"
    while true; do
        colorprint "YELLOW" "This menu item will launch all the apps using the configured ${ENV_FILENAME} file and the $DKCOM_FILENAME file (Docker must be already installed and running)"
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose -f ${DKCOM_FILENAME} --env-file ${ENV_FILENAME} up -d; then
                    print_and_log "GREEN" "All Apps started."
                    # Call the fscript to generate dashboards urls for the apps that has them and check if execute correctly
                    sudo chmod +x ./generate_dashboard_urls.sh
                    if ./generate_dashboard_urls.sh; then
                        print_and_log "GREEN" "All Apps dashboards URLs generated. Check the generated dashboards file for the URLs."
                    else
                        errorprint_and_log "Error generating Apps dashboards URLs. Please check the configuration and try again."
                    fi                    
                    colorprint "YELLOW" "If not already done, use the previously generated apps nodes URLs to add your device in any apps dashboard that require node claiming/registration (e.g. Earnapp, ProxyRack, etc.)"
                else
                    errorprint_and_log "Error starting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                toLog_ifDebug -l "[DEBUG]" -m "User chose not to start the stack"
                colorprint "BLUE" "Docker stack startup canceled."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) colorprint "RED" "Please answer yes or no.";;
        esac
    done
    toLog_ifDebug -l "[DEBUG]" -m "StartStack function ended"
}


fn_stopStack(){
    clear
    toLog_ifDebug -l "[DEBUG]" -m "Starting stopStack function"
    while true; do
        colorprint "YELLOW" "This menu item will stop all the apps and delete the docker stack previously created using the configured ${ENV_FILENAME} file and the $DKCOM_FILENAME file."
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if sudo docker compose -f $DKCOM_FILENAME down; then
                    print_and_log "GREEN" "All Apps stopped and stack deleted."
                else
                    errorprint_and_log "Error stopping and deleting Docker stack. Please check the configuration and try again."
                fi
                read -r -p "Now press enter to go back to the menu"
                break
                ;;
            [Nn]* ) 
                toLog_ifDebug -l "[DEBUG]" -m "User chose not to stop the stack"
                colorprint "BLUE" "Docker stack removal canceled."
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) 
                colorprint "RED" "Please answer yes or no.";;
        esac
    done
}

# Function that will call the script to seup the multiple proxies instances
fn_setupmproxies() {
    clear
    print_and_log "BLUE" "Starting multi-proxy setup function"

    # Path to the runmproxies.sh script
    runmproxies_script="./runmproxies.sh"

    # Ensure the script is executable
    chmod +x "$runmproxies_script"

    # Execute the script
    "$runmproxies_script"

    # Check the exit status of the script
    if [ $? -eq 0 ]; then
        print_and_log "GREEN" "$runmproxies_script completed successfully"
    else
        print_and_log "RED" "$runmproxies_script encountered an error. Exit code: $?"
    fi

    # Control will return here after runmproxies.sh has finished executing
    echo "Returning to main menu"
    sleep ${SLEEP_TIME}
}



fn_resetEnv(){ # this function needs rewiting as it should use now the local .env.template file
    clear
    toLog_ifDebug -l "[DEBUG]" -m "Starting resetEnv function"
    while true; do
        colorprint "YELLOW" "A fresh ${ENV_FILENAME} file will be created from the ${ENV_TEMPLATE_FILENAME} template file"
        read -r -p "Do you wish to proceed Y/N?" yn
        case $yn in
            [Yy]* ) 
                if [ -f ./${ENV_FILENAME} ]; then
                    rm ./${ENV_FILENAME} || { colorprint "RED" "Error resetting ${ENV_FILENAME} file."; continue; }
                fi
                cp ./${ENV_TEMPLATE_FILENAME} ./${ENV_FILENAME} || { colorprint "RED" "Error resetting ${ENV_FILENAME} file."; continue; }
                colorprint "GREEN" "${ENV_FILENAME} file resetted, remember to reconfigure it"
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            [Nn]* ) 
                colorprint "BLUE" "${ENV_FILENAME} file reset canceled. The file is left as it is"
                read -r -p "Press Enter to go back to mainmenu"
                break
                ;;
            * ) 
                colorprint "RED" "Please answer yes or no.";;
        esac
    done
}



fn_resetDockerCompose(){
    clear
    toLog_ifDebug -l "[DEBUG]" -m "Starting resetDockerCompose function"
    while true; do
        colorprint "YELLOW" "A fresh ${DKCOM_FILENAME} file will be created from the ${DKCOM_TEMPLATE_FILENAME} template file"
        read -r -p "Do you wish to proceed Y/N?  " yn
        case $yn in
            [Yy]* ) 
                if [ -f ./$DKCOM_FILENAME ]; then
                    rm ./$DKCOM_FILENAME || { colorprint "RED" "Error resetting $DKCOM_FILENAME file."; continue; }
                fi
                cp  ./$DKCOM_TEMPLATE_FILENAME ./$DKCOM_FILENAME || { colorprint "RED" "Error resetting $DKCOM_FILENAME file."; continue; }
                colorprint "GREEN" "$DKCOM_FILENAME file resetted, remember to reconfigure it"
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
    toLog_ifDebug -l "[DEBUG]" -m "resetDockerCompose function ended"
}

# Function that will check the necerrary dependencies for the script to run
fn_checkDependencies(){
    clear
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v${SCRIPT_VERSION}"
    check_project_updates
    colorprint "GREEN" "---------------------------------------------- "
    colorprint "MAGENTA" "Join our Discord community for updates, help, and discussions: ${DS_PROJECT_SERVER_URL}"
    colorprint "MAGENTA" "---------------------------------------------- "
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
    toLog_ifDebug -l "[DEBUG]" -m "Dependencies check completed"
}

### Main Menu ##
mainmenu() {
    clear
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v${SCRIPT_VERSION}"
    check_project_updates
    fn_adaptLimits
    colorprint "GREEN" "---------------------------------------------- "
    colorprint "MAGENTA" "Join our Discord community for updates, help, and discussions: ${DS_PROJECT_SERVER_URL}"
    colorprint "MAGENTA" "---------------------------------------------- "
    colorprint "DEFAULT" "Detected OS type: ${OS_TYPE}"$'\n'"Detected architecture: $ARCH"$'\n'"Docker $DKARCH image architecture will be used if the app's image permits it"$'\n'"---------------------------------------------- "$'\n'
    
    PS3="Select an option and press Enter "$'\n'
    toLog_ifDebug -l "[DEBUG]" -m "Loading menu options"
    # Reset the menuItems array
    menuItems=()
    # Read labels from the JSON file without splitting them
    while IFS= read -r label; do
        menuItems+=("$label")
    done < <(jq -r '.[].label? // empty' "$CONFIG_DIR/$MAINMENU_JSON_FILE")
    
    toLog_ifDebug -l "[DEBUG]" -m "Menu options loaded. Showing menu options, ready to select"
    select option in "${menuItems[@]}"
    do
        if [[ -n $option ]]; then
            clear
            toLog_ifDebug -l "[DEBUG]" -m "User selected option number $REPLY that corresponds to menu item [${menuItems[$REPLY-1]}]"
            # Fetch the function name associated with the chosen menu item
            functionName=$(jq -r --arg chosen "$option" '.[] | select(.label == $chosen).function? // empty' "$CONFIG_DIR/$MAINMENU_JSON_FILE")
            if [[ -n $functionName ]]; then
                # Invoke the function
                $functionName
            else
                colorprint "RED" "Error: Unable to find the function associated with the selected option."
                toLog_ifDebug -l "[DEBUG]" -m "Error in JSON: Missing function for menu item [${menuItems[$REPLY-1]}]"
            fi
            break
        else
            colorprint "RED" "Invalid input. Please select a menu option between 1 and ${#menuItems[@]}."
            sleep ${SLEEP_TIME}
            break
        fi
    done
}

### Startup ##
toLog_ifDebug -l "[DEBUG]" -m "Starting ${SCRIPT_NAME} v${SCRIPT_VERSION}"
clear

# Detect the operating system
detect_os

# Detect the architecture and set the correct docker image architecture
detect_architecture

# Check dependencies
fn_checkDependencies

# Start the main menu
toLog_ifDebug -l "[INFO]" -m "Starting main menu..."
while true; do
    mainmenu
done
