#!/usr/bin/env bash

generate_dashboard_urls() {
    local compose_project_name=$1
    local device_name=$2
    local env_file=".env"
    local dashboard_file

    # If parameters are not provided, try to read from .env file
    if [[ -z "$compose_project_name" ]] || [[ -z "$device_name" ]]; then
        if [ -f "$env_file" ]; then
            echo "Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from $env_file..."
            compose_project_name=$(grep -oP 'COMPOSE_PROJECT_NAME=\K[^#\r]+' "$env_file")
            device_name=$(grep -oP 'DEVICE_NAME=\K[^#\r]+' "$env_file")
        else
            echo "Error: Parameters not provided and $env_file not found."
            return 1
        fi
    fi

    # Validate if COMPOSE_PROJECT_NAME and DEVICE_NAME are set
    if [[ -z "$compose_project_name" ]] || [[ -z "$device_name" ]]; then
        echo "Error: COMPOSE_PROJECT_NAME and DEVICE_NAME must be provided."
        return 1
    fi

    dashboard_file="dashboards_URLs_${compose_project_name}-${device_name}.txt"
    echo "------Dashboards ${compose_project_name}-${device_name} ------" > "$dashboard_file"

    # Get running docker containers and extract port information
    while IFS= read -r line; do
        local container_info=$(echo "$line" | awk '{print $NF}')
        local port_mapping=$(echo "$line" | awk -F'0.0.0.0:' '{print $2}' | awk -F'->' '{print $1}')

        if [[ -n "$port_mapping" ]]; then
            echo "If enabled you can visit the $container_info web dashboard on http://localhost:$port_mapping" >> "$dashboard_file"
        fi
    done < <(docker ps --format "{{.Ports}} {{.Names}}")

    echo "Dashboard URLs have been written to $dashboard_file"
}

# Call the function with arguments or read from .env
generate_dashboard_urls "$1" "$2"
