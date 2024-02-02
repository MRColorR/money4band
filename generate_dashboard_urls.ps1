#!/bin/pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force

# Function to generate dashboard URLs for a given compose project name and device name.
# If the parameters are not provided, it tries to read them from the .env file.
# If the .env file is not found or the parameters are not set, it returns an error.
# The generated dashboard URLs are written to a file named "dashboards_URLs_<compose_project_name>-<device_name>.txt".
# The function uses the "docker ps" command to get the running containers and extract the port information.
# It then writes the URLs to the dashboard file if the port mapping is available.
# The function returns 0 on success and 1 on failure.

function Generate-DashboardUrls {
    param (
        [string]$composeProjectName,
        [string]$deviceName,
        [string]$envFile = ".env"
    )

    $envfile_path = Join-Path $PWD $envFile

    # If parameters are not provided, try to read from .env file
    if (-not $composeProjectName -or -not $deviceName) {
        if (Test-Path $envfile_path) {
            Write-Host "Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from $envFile..."
            $envContent = Get-Content $envfile_path -Raw
            $composeProjectName = [Regex]::Match($envContent, '(?<=COMPOSE_PROJECT_NAME=)[^\r\n#]+').Value
            $deviceName = [Regex]::Match($envContent, '(?<=DEVICE_NAME=)[^\r\n#]+').Value
        } else {
            Write-Host "Error: Parameters not provided and $envFile not found."
            return 1
        }
    }

    # Validate if COMPOSE_PROJECT_NAME and DEVICE_NAME are set
    if (-not $composeProjectName -or -not $deviceName) {
        Write-Host "Error: COMPOSE_PROJECT_NAME and DEVICE_NAME must be provided."
        return 1
    }

    $dashboardFile = "dashboards_URLs_${composeProjectName}_${deviceName}.txt"
    "------ Dashboards ${composeProjectName}-${deviceName} ------" | Out-File $dashboardFile

    # Get running docker containers and extract port 
    $dockerOutput = docker ps --format "{{.Ports}} {{.Names}}"
    foreach ($line in $dockerOutput) {
        # Adjusted regex pattern to account for potential format variations
        if ($line -match '0.0.0.0:(\d+)->\d+/tcp\s+(.*)') {
            $port = $matches[1]
            $name = $matches[2]
            #"Match found: Port=$port, Name=$name"
            "If enabled you can visit the $name web dashboard on http://localhost:$port" | Out-File $dashboardFile -Append
        } else {
            "No match found"
        }
    }
    Write-Host "Dashboard URLs have been written to $dashboardFile"
}

# Call the function with arguments or read from .env
Generate-DashboardUrls -composeProjectName $args[0] -deviceName $args[1]
