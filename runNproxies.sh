#!/usr/bin/env bash

# This script will run N copies of Money4Band using N proxies provided as list in the file passed as argument --proxies-file <filename> , by default it will use proxies.txt
# It will create and subflder named "m4b_proxy_instances" and a subfolder with same name of the original COMPOSE_PROJECT_NAME<unique_suffix> the it will copy all the files from the root folder to the subfolder created for each instance and named like "m4b-<COMPOSE_PROJECT_NAME><unique_suffix>/<DEVICE_NAME><unique_suffix>" deriving this from the original instance running with or without proxy in the root folder that uses the original .env and docker-compose.yml files
# then it will change the COMPOSE_PROJECT_NAME and DEVICE_NAME in the subfolder .env file adding a random number of three digits to the original name already used for the name of the subfolder
# if files that starts with claim*.txt contains the neam of one app then open the file use this uuid to edit the same uuid inside the file and inside the env file to the variable containg it in full caps the same appname followed _DEVICE_UUID with a new one of the same lenght newly generated and saving the new one back.
# so if there's a file named claimEARNAPPNodeDevice.txt in the subfolder the uuid will be changed in the file and in the .env file to the new one for exampre EARNAPP_NODE_UUID=newUUID
# similarly for claimPROXYRACKNodeDevice.txt
# then it will run the docker-compose up -d command in the subfolder and move to the next one 
# for this change we should do this , search for file named like claim<APPNAME>NodeDevice.txt then serach in the .env file for the variable named like <APPNAME>_DEVICE_UUID , measure the lenght of the current value and generate a new one of the same lenght and replace the old one with the new one in the claim<APPNAME>NodeDevice.txt file and in the .env file
# the script will stop when it will have run all the proxies in the list and will print a message with the number of instances created  and a bye message


# Usage: ./runNproxies.sh <proxies file> <original_docker-compose file> <original_.env file> by default it will use proxies.txt, docker-compose.yml and .env prensent in the root folder

#!/usr/bin/env bash

# Default file names
PROXIES_FILE=${1:-"proxies.txt"}
DOCKER_COMPOSE_FILE=${2:-"docker-compose.yaml"}
ENV_FILE=${3:-".env"}

ROOT_DIR="$PWD"
# Directory for proxy instances
INSTANCES_DIR="${ROOT_DIR}/m4b_proxy_instances"
mkdir -p "$INSTANCES_DIR"

# Log file
LOG_FILE="multiproxies.log"
touch "$LOG_FILE"

# Function to log messages
echo_and_log_message() {
    echo "$1"
    echo "$(date): $1" >> "$LOG_FILE"
}

echo_and_log_message "Multiproxy instances setup script started."

# Check if .env , docker-compose.yaml and proxies.txt files are present in the root folder
if [ ! -f "$ENV_FILE" ] || [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo_and_log_message "No .env (or docker-compose file) found in the root folder. Please configure the main instance first using a proxy and then run this script again to create the other instances using the proxies in the proxies.txt file. Exiting."
    exit 1
fi

if [ ! -f "$PROXIES_FILE" ]; then
    echo_and_log_message "No proxies.txt file found in the root folder. Please create a proxies.txt file with one proxy per line and then run this script again. Exiting."
    exit 1
fi

# Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from original .env file
COMPOSE_PROJECT_NAME=$(grep COMPOSE_PROJECT_NAME "$ENV_FILE" | cut -d'=' -f2)
echo_and_log_message "Original COMPOSE_PROJECT_NAME: $COMPOSE_PROJECT_NAME"
DEVICE_NAME=$(grep DEVICE_NAME "$ENV_FILE" | cut -d'=' -f2)
echo_and_log_message "Original DEVICE_NAME: $DEVICE_NAME"
# get total number of proxies and so max number of instances to create
total_proxies=$(wc -l < "$PROXIES_FILE")
echo_and_log_message "Total proxies: $total_proxies"

# Check if the original env file has been configured with proxies checking the # PROXY_CONFIGURATION_STATUS=1 if not exit telling the user to configure the original .env file with a proxy and then pass the others as list in the proxies.txt file
ORIG_ENV_PROXY_CONFIGURATION_STATUS=$(grep PROXY_CONFIGURATION_STATUS "$ENV_FILE" | cut -d'=' -f2)
echo_and_log_message "Original PROXY_CONFIGURATION_STATUS: $ORIG_ENV_PROXY_CONFIGURATION_STATUS"
if [ "$ORIG_ENV_PROXY_CONFIGURATION_STATUS" != "1" ]; then
    echo_and_log_message "The original .env file has not been configured with a proxy. Please configure the main instance first using a proxy and then run this script again to create the other instances using the proxies in the proxies.txt file. Exiting."
    exit 1
fi


# Check if INSTANCES_DIR is not empty
if [ "$(ls -A "$INSTANCES_DIR")" ]; then
    echo_and_log_message "The $INSTANCES_DIR directory is not empty."
    echo "Choose an option:"
    echo "1 - Just Cleanup: Stop and remove all current instances (Warning: This will delete all data in the instances directories without creating new ones)."
    echo "2 - Cleanup and Recreate: Stop and remove all current instances, new one will be created (Warning: This will delete all data in the instances directories)."
    echo "3 - Update: Update proxies for existing instances (you will need a number of proxies in the proxies.txt file equal or greater than the number of instances)."
    echo "4 - Exit without making changes."

    read -p "Enter your choice (1/2/3/4): " user_choice

    case $user_choice in
        1)
            echo_and_log_message "Stopping and removing all current instances..."
            for instance_dir in "$INSTANCES_DIR"/*/; do
                if [ -d "$instance_dir" ]; then
                    echo_and_log_message "Stopping and removing instance in $instance_dir"
                    cd "$instance_dir" 
                    if sudo docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} down ; then
                        echo_and_log_message "Docker compose down for $instance_dir succeeded"
                    else
                        echo_and_log_message "Docker compose down for $instance_dir failed"
                    fi
                fi
            done
            cd "$ROOT_DIR" || exit
            # Remove the instance directories after stopping the containers
            # Warning: This will delete all data in these directories
            sudo rm -rf "$INSTANCES_DIR"/*
            echo_and_log_message "Cleanup complete. Done stopping and removing all current instances. Exiting."
            exit 0
            ;;
        2)
            echo_and_log_message "Stopping and removing all current instances..."
                for instance_dir in "$INSTANCES_DIR"/*/; do
                    if [ -d "$instance_dir" ]; then
                        echo_and_log_message "Stopping and removing instance in $instance_dir"
                        cd "$instance_dir" 
                        if sudo docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} down ; then
                            echo_and_log_message "Docker compose down for $instance_dir succeeded"
                        else
                            echo_and_log_message "Docker compose down for $instance_dir failed"
                        fi
                    fi
                done
                cd "$ROOT_DIR" || exit
                # Remove the instance directories after stopping the containers
                # Warning: This will delete all data in these directories
                sudo rm -rf "$INSTANCES_DIR"/*
                echo_and_log_message "Cleanup complete. Done stopping and removing all current instances. Preparing to create new instances..."
            ;;
        3)
            echo_and_log_message "Updating proxies for existing instances..."
            # Ensure that the number of proxies is sufficient
            num_proxies_avail=$(wc -l < "$PROXIES_FILE")
            num_instances_to_upd=$(find "$INSTANCES_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)

            if [ "$num_proxies_avail" -ge "$num_instances_to_upd" ]; then
                echo_and_log_message "Sufficient proxies available. Proceeding with update..."
                # Update the proxy for each instance and restart it
                for instance_dir in "$INSTANCES_DIR"/*/; do
                    if [ -d "$instance_dir" ]; then
                        echo_and_log_message "Updating proxy for instance in $instance_dir"
                        cd "$instance_dir" || exit
                        # Get the proxy from the proxies.txt file using the instance number as line number
                        proxy=$(sed -n "$num_instances_to_upd"p "$PROXIES_FILE")
                        # Update the proxy in the .env file
                        sed -i "s/STACK_PROXY=.*/STACK_PROXY=${proxy}/" "${instance_dir}/.env"
                        echo_and_log_message "Updated .env file STACK_PROXY for $instance_dir"
                        # Restart the instance
                        if sudo docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} up -d ; then
                            echo_and_log_message "Docker compose up for $instance_dir succeeded"
                        else
                            echo_and_log_message "Docker compose up for $instance_dir failed"
                        fi
                        # Decrease the number of instances and proxies
                        ((num_instances_to_upd--))
                        ((num_proxies_avail--))
                    fi
                done
            else
                echo_and_log_message "Not enough proxies available. Cannot proceed with update. Exiting."
                exit 1
            fi
            echo_and_log_message "Done updating proxies. Exiting."
            exit 0
            ;;
        4)
            echo_and_log_message "Exiting without changes."
            exit 0
            ;;
        *)
            echo_and_log_message "Invalid choice. Exiting."
            exit 1
            ;;
    esac
fi

###############SETUP MULTI PROXIES INSTANCES#####################
# move back to the root folder
cd "$ROOT_DIR" || exit
#check if INSTANCES_DIR exists if yes proceed if not exit
if [ -d "$INSTANCES_DIR" ]; then
    echo_and_log_message "Setting up multi proxies instances..."
    # Reading the proxy list and creating instances counting and increasing the number of instances created and running
    created_instance_count=0
    # to check the content of the array
    # while IFS= read -r proxy; do
    #     echo "Proxy value: $proxy"
    # done < "$PROXIES_FILE"
    while IFS= read -r proxy; do
        # Generating a unique suffix for each instance
        echo_and_log_message "Setting up new instance using proxy: $proxy"
        unique_suffix=$(tr -dc 0-9 </dev/urandom | head -c 3 ; echo '')

        # Instance directory name and path
        instance_name="m4b_${COMPOSE_PROJECT_NAME}-${DEVICE_NAME}-${unique_suffix}"
        instance_dir="${INSTANCES_DIR}/${instance_name}"
        mkdir -p "$instance_dir"

        for item in "$ROOT_DIR"/* "$ROOT_DIR"/.*; do
            # Skip if item is the current or parent directory
            if [ "$item" = "$ROOT_DIR/." ] || [ "$item" = "$ROOT_DIR/.." ]; then
                continue
            fi

            # Extract just the name of the item (without path)
            item_name=$(basename "$item")

            # Skip if item is the instances directory, .data directory, starts with .git (like .git, .github, .gitignore, etc.) or is a .log file
            if [ "$item_name" = "$(basename "$INSTANCES_DIR")" ] || [ "$item_name" = ".data" ] || [[ "$item_name" =~ ^\.git.*$ ]] || [[ "$item_name" =~ ^.*\.log$ ]]; then
                continue
            fi

            # Copy item to instance directory
            cp -r "$item" "$instance_dir/"
        done

        # Update .env file with unique COMPOSE_PROJECT_NAME and DEVICE_NAME appending to the old one the unique suffix and updte the old proxy with the new one
        sed -i "s/COMPOSE_PROJECT_NAME=.*/COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}-${unique_suffix}/" "${instance_dir}/.env"
        sed -i "s/DEVICE_NAME=.*/DEVICE_NAME=${DEVICE_NAME}${unique_suffix}/" "${instance_dir}/.env"
        sed -i "s/STACK_PROXY=.*/STACK_PROXY=${proxy}/" "${instance_dir}/.env"
        echo_and_log_message "Updated .env file COMPOSE_PROJECT_NAME, DEVICE_NAME and STACK_PROXY for $instance_name"


        # Find all files starting with claim and put them in an array and if the array is not empty then loop through the array and update the UUID in the .env file
        claim_files=()
        # Inserting files in array without breaking paths with spaces
        while IFS= read -r -d $'\0' file; do
            claim_files+=("$file")
        done < <(find "$instance_dir" -type f -name "claim*.txt" -print0)

        # To check the content of the array
        # for file in "${claim_files[@]}"; do
        #     echo "$file"
        # done

        if [ ${#claim_files[@]} -eq 0 ]; then
            echo_and_log_message "No claim files found in $instance_name, skipping UUID update"

        else
            # Loop through claim files identify the app name and update its UUID in .env file
            for claim_file in "${claim_files[@]}"; do
                echo_and_log_message "Updating UUID for $claim_file"

                # Get app name from claim file name (e.g., claimEARNAPPNodeDevice.txt -> EARNAPP)
                app_name=$(echo "$claim_file" | sed -n 's/.*claim\(.*\)NodeDevice.*/\1/p')
                echo_and_log_message "App name: $app_name"

                # Get env variable name from app name
                env_var="${app_name}_DEVICE_UUID"
                echo_and_log_message "Env variable name to search: $env_var"

                # Get old UUID from .env file
                old_uuid=$(grep "$env_var" "${instance_dir}/.env" | cut -d'=' -f2)
                echo_and_log_message "Old UUID extracted from .env file: $old_uuid"

                # Check if the old uuid contains a prefix like 'sdk-node-'
                prefix=""
                if [[ $old_uuid == sdk-node-* ]]; then
                    prefix="sdk-node-"
                    # Extract the UUID part after the prefix
                    old_uuid=${old_uuid#sdk-node-}
                fi

                # Generate new md5 UUID of same length as the old UUID
                new_uuid=$(tr -dc a-f0-9 </dev/urandom | head -c ${#old_uuid} ; echo '')  

                # Append the prefix if it was present
                full_new_uuid="${prefix}${new_uuid}"
                echo_and_log_message "New UUID generated: $full_new_uuid"

                # Replace UUID in claim file and .env file
                sed -i "s/$old_uuid/$full_new_uuid/" "$claim_file"
                sed -i "s/${env_var}=.*/${env_var}=${full_new_uuid}/" "${instance_dir}/.env"
            done

        fi
        # Run docker-compose up -d in the instance directory amd increase instance count
        cd "$instance_dir" || exit
        #execute a dry run do not start the containers for now
        # if sudo docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} up --no-start ; then
        if sudo docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} up -d ; then
            ((created_instance_count++))
            echo_and_log_message "Docker compose up for $instance_name succeeded"
        else
            echo_and_log_message "Docker compose up for $instance_name failed"
        fi
        
    done < "$PROXIES_FILE"

    # Final message and log

    echo_and_log_message "Created and ran $created_instance_count instances out of $total_proxies proxies available. Bye!"
    exit 0
else
    echo_and_log_message "The $INSTANCES_DIR directory does not exist. Exiting."
    exit 1
fi