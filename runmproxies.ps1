#!/bin/pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force

# This script will run N copies of Money4Band using N proxies provided as list in the file passed as argument --proxies-file <filename> , by default it will use proxies.txt
# It will create and subflder named "m4b_proxy_instances" and a subfolder with same name of the original COMPOSE_PROJECT_NAME<unique_suffix> the it will copy all the files from the root folder to the subfolder created for each instance and named like "m4b-<COMPOSE_PROJECT_NAME><unique_suffix>/<DEVICE_NAME><unique_suffix>" deriving this from the original instance running with or without proxy in the root folder that uses the original .env and docker-compose.yaml files
# then it will change the COMPOSE_PROJECT_NAME and DEVICE_NAME in the subfolder .env file adding a random number of three digits to the original name already used for the name of the subfolder
# if files that starts with claim*.txt contains the neam of one app then open the file use this uuid to edit the same uuid inside the file and inside the env file to the variable containg it in full caps the same appname followed _DEVICE_UUID with a new one of the same lenght newly generated and saving the new one back.
# so if there's a file named claimEARNAPPNodeDevice.txt in the subfolder the uuid will be changed in the file and in the .env file to the new one for exampre EARNAPP_NODE_UUID=newUUID
# similarly for claimPROXYRACKNodeDevice.txt
# then it will run the docker-compose up -d command in the subfolder and move to the next one 
# for this change we should do this , search for file named like claim<APPNAME>NodeDevice.txt then serach in the .env file for the variable named like <APPNAME>_DEVICE_UUID , measure the lenght of the current value and generate a new one of the same lenght and replace the old one with the new one in the claim<APPNAME>NodeDevice.txt file and in the .env file
# the script will stop when it will have run all the proxies in the list and will print a message with the number of instances created  and a bye message


# Usage: ./runmproxies.ps1 <proxies file> <original_docker-compose file> <original_.env file> by default it will use proxies.txt, docker-compose.yaml and .env prensent in the root folder


# Default file names and paths if provided as arguments use the arguments otherwise use the default values
$proxiesFile = If ($args[0] -ne $null) { $args[0] } Else { "proxies.txt" }
$dockerComposeFile = If ($args[1] -ne $null) { $args[1] } Else { "docker-compose.yaml" }
$envFile = If ($args[2] -ne $null) { $args[2] } Else { ".env" }

# rootdir is the folder where the script is located
$rootDir = Get-Location
# Directory for proxy instances
$instancesDir = Join-Path -Path $rootDir -ChildPath "m4b_proxy_instances"
$logFile = Join-Path -Path $rootDir -ChildPath "multiproxies.log"

# Ensure the instances directory exists
if (-not (Test-Path -Path $instancesDir)) {
    New-Item -Path $instancesDir -ItemType Directory | Out-Null
}
# Ensure the log file exists
if (-not (Test-Path -Path $logFile)) {
    New-Item -Path $logFile -ItemType File | Out-Null
}

# Function to log messages with optional color
function echo_and_log_message {
    Param (
        [string]$Message,
        [string]$Type = "INFO",
        [string]$Color = "White"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp [$Type] $Message" | Out-File -FilePath $logFile -Append
    if ($Type -eq "ERROR") {
        Write-Host -ForegroundColor Red $Message
    } else {
        Write-Host -ForegroundColor $Color $Message
        # reset color to default
        Write-Host -ForegroundColor White ""
    }
}

# Print a starting message 
Clear-Host
echo_and_log_message -Message "Starting Multiproxy instances setup script" -Color "Green"

# Check if .env, docker-compose.yaml, and proxies.txt files are present
if (-not (Test-Path -Path $envFile)) {
    echo_and_log_message -Message "Error: $envFile not found." -Type "ERROR"
    exit 1
}
if (-not (Test-Path -Path $dockerComposeFile)) {
    echo_and_log_message -Message "Error: $dockerComposeFile not found." -Type "ERROR"
    exit 1
}
if (-not (Test-Path -Path $proxiesFile)) {
    echo_and_log_message -Message "Error: $proxiesFile not found." -Type "ERROR"
    exit 1
}

# Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from original .env file
$envContent = Get-Content -Path $envFile
$composeProjectName = ($envContent | Where-Object { $_ -match "^COMPOSE_PROJECT_NAME=" }) -split '=', 2 | Select-Object -Last 1
echo_and_log_message -Message "Original COMPOSE_PROJECT_NAME: $composeProjectName" -Color "Green"
$deviceName = ($envContent | Where-Object { $_ -match "^DEVICE_NAME=" }) -split '=', 2 | Select-Object -Last 1
echo_and_log_message -Message "Original DEVICE_NAME: $deviceName" -Color "Green"
$num_proxies_avail = (Get-Content -Path $proxiesFile).Count
echo_and_log_message -Message "Number of proxies available: $num_proxies_avail" -Color "Green"

# Check if the original env file has been configured with proxies checking the # PROXY_CONFIGURATION_STATUS=1 if not exit telling the user to configure the original .env file with a proxy and then pass the others as list in the proxies.txt file
$orig_env_proxy_config_status = ($envContent | Where-Object { $_ -match "^# PROXY_CONFIGURATION_STATUS=" }) -split '=', 2 | Select-Object -Last 1
if ($orig_env_proxy_config_status -ne "1") {
    echo_and_log_message -Message "Error: The original .env file has not been configured with a proxy." -Type "ERROR"
    echo_and_log_message -Message "Please configure the original .env file with a proxy and then pass the others as list in the proxies.txt file. Exiting..." -Type "ERROR"
    exit 1
}

# Check if INSTANCES_DIR is not empty and if is not empty ask the user what to do
if ((Get-ChildItem -Path $instancesDir).Count -gt 0) {
    echo_and_log_message -Message "The $instancesDir directory is not empty."
    Write-Output "Choose an option:"
    Write-Output "1) Just Cleanup: Stop and remove all current instances (Warning: This will delete all data in the instances directories without creating new ones)."
    Write-Output "2) Cleanup and Recreate: Stop and remove all current instances, new one will be created (Warning: This will delete all data in the instances directories)."
    Write-Output "3) Update: Update proxies for existing instances (you will need a number of proxies in the proxies.txt file equal or greater than the number of instances)."
    Write-Output "4) Exit without making changes."
    $user_choice = Read-Host "Enter your choice"
    
    switch ($user_choice) {
        "1" {
            echo_and_log_message -Message "Stopping and removing all current instances..."
            Get-ChildItem -Path $instancesDir -Directory | ForEach-Object {
                $instanceDir = $_.FullName
                Set-Location $instanceDir
                try {
                    docker-compose -f $dockerComposeFile --env-file $envFile down 
                    echo_and_log_message -Message "Docker compose down for $instanceDir succeeded."
                } catch {
                    echo_and_log_message -Message "Docker compose down for $instanceDir failed." -Type "ERROR"
                }
            }
            Set-Location $rootDir
            # Remove the instance directories after stopping the containers
            # Warning: This will delete all data in these directories
            Remove-Item -Path $instancesDir -Recurse -Force
            echo_and_log_message -Message "Cleanup complete. All current multiproxy instances have been removed. Exiting..."
            exit 0
        }
        "2" {
            echo_and_log_message -Message "Stopping and removing all current instances..."
            Get-ChildItem -Path $instancesDir -Directory | ForEach-Object {
                $instanceDir = $_.FullName
                Set-Location $instanceDir
                try {
                    docker-compose -f $dockerComposeFile --env-file $envFile down 
                    echo_and_log_message -Message "Docker compose down for $instanceDir succeeded."
                } catch {
                    echo_and_log_message -Message "Docker compose down for $instanceDir failed." -Type "ERROR"
                }
            }
            Set-Location $rootDir
            # Remove the instance directories after stopping the containers
            # Warning: This will delete all data in these directories
            Remove-Item -Path $instancesDir -Recurse -Force
            echo_and_log_message -Message "Cleanup complete. All current multiproxy instances have been removed. Preparing to create new instances..."
        }
        "3" {
            echo_and_log_message -Message "Updating proxies for existing instances..."
            # Ensure that the number of proxies is sufficient for the number of instances
            $num_instances_to_upd = (Get-ChildItem -Path $instancesDir -Directory).Count
            # Check that availabe proxies and instaces are greater than zero
            if ($num_proxies_avail -gt 0 -and $num_instances_to_upd -gt 0) {
                if ($num_proxies_avail -ge $num_instances_to_upd) {
                    echo_and_log_message -Message "Sufficient proxies available. Proceeding with update..."
                    Get-ChildItem -Path $instancesDir -Directory | ForEach-Object {
                        # Copy the new proxy file from the root folder to the instance folder
                        $instanceDir = $_.FullName
                        echo_and_log_message -Message "Copying new $proxiesFile from $rootDir to $instanceDir..."
                        Copy-Item -Path (Join-Path -Path $rootDir -ChildPath $proxiesFile) -Destination  (Join-Path -Path $instanceDir -ChildPath $proxiesFile) -Force
                        echo_and_log_message -Message "Updating proxy for instance in $instanceDir..."
                        Set-Location $instanceDir
                        # Get the proxy from the proxies.txt file using the instance number as line number
                        $proxy = Get-Content -Path $proxiesFile -TotalCount $num_instances_to_upd | Select-Object -Index ($num_instances_to_upd - 1)
                        echo_and_log_message -Message "New proxy to use: $proxy"
                        # Update the proxy in the .env file
                        (Get-Content -Path $envFile) -replace "STACK_PROXY=.*", "STACK_PROXY=$proxy" | Set-Content -Path $envFile
                        echo_and_log_message -Message "Updated .env file STACK_PROXY for $instanceDir"
                        # Restart the instance
                        try {
                            docker-compose -f $dockerComposeFile --env-file $envFile up -d 
                            echo_and_log_message -Message "Docker compose up for $instanceDir succeeded."
                        } catch {
                            echo_and_log_message -Message "Docker compose up for $instanceDir failed." -Type "ERROR"
                        }
                        # Decrease the number of instances and proxies available
                        $num_instances_to_upd--
                        $num_proxies_avail--  
                    }
                } else {
                    echo_and_log_message -Message "Error: Insufficient proxies available. Exiting..." -Type "ERROR"
                    exit 1
                }
            } else {
                echo_and_log_message -Message "No proxies or instances available. Exiting..." -Color "Yellow"
                exit 1
            }
            echo_and_log_message -Message "Done updating proxies." -Color "Green"
            exit 0
        }
        "4" {
            echo_and_log_message -Message "Exiting without changes..."
            exit 0
        }
        default {
            echo_and_log_message -Message "Invalid choice. Exiting..." -Type "ERROR"
        }
    }
} else {
    echo_and_log_message -Message "The $instancesDir directory is clean. Proceeding with setup..."
}

###############SETUP MULTI PROXIES INSTANCES#####################
# Move back to the root folder
Set-Location $rootDir

# If instancesDir is not present then create it and proceed
if (-not (Test-Path -Path $instancesDir)) {
    New-Item -Path $instancesDir -ItemType Directory | Out-Null
}
# Check if INSTANCES_DIR exists if yes proceed if not exit
if (Test-Path -Path $instancesDir) {
    echo_and_log_message "Setting up multiproxy instances in $instancesDir"
    # Reading the proxy list and creating instances counting and increasing the number of instances created and running
    $num_instances_created = 0
    $proxies = Get-Content -Path $proxiesFile
    foreach ($proxy in $proxies) {
        # Generating a unique suffix for each instance
        echo_and_log_message "Setting up new instance using proxy: $proxy"
        $uniqueSuffix = Get-Random -Minimum 100 -Maximum 999

        # Instance directory name and path
        $instanceName = "m4b_${composeProjectName}-${deviceName}-${uniqueSuffix}"
        $instanceDir = Join-Path -Path $instancesDir -ChildPath $instanceName
    
        # Create instance directory
        New-Item -Path $instanceDir -ItemType Directory | Out-Null
    
        # Copy files from root directory to instance directory, excluding certain directories and files
        $items = Get-ChildItem -Path $rootDir
        $instancesDir_name = $instancesDir | Split-Path -Leaf
        foreach ($item in $items) {
            if ($item.Name -ne $instancesDir_name -and $item.Name -ne ".data" -and $item.Name -notlike ".git*" -and $item.Name -notlike "*.log") {
                Copy-Item -Path $item.FullName -Destination $instanceDir -Recurse -Force
            }
        }

        # Update .env file with unique COMPOSE_PROJECT_NAME and DEVICE_NAME appending to the old one the unique suffix and updte the old proxy with the new one
        $envFilePath = Join-Path -Path $instanceDir -ChildPath ".env"
        (Get-Content -Path $envFilePath) `
            -replace 'COMPOSE_PROJECT_NAME=.*', "COMPOSE_PROJECT_NAME=${composeProjectName}-${uniqueSuffix}" `
            -replace 'DEVICE_NAME=.*', "DEVICE_NAME=${deviceName}${uniqueSuffix}" `
            -replace 'STACK_PROXY=.*', "STACK_PROXY=$proxy" | 
        Set-Content -Path $envFilePath

        # Update the ports present in the .env file like MYSTNODE_DASHBOARD_PORT M4B_DASHBOARD_PORT and so on increasing their value by $num_instances_created+1
        # Increment value for any variable ending with _DASHBOARD_PORTe
        $envContent = Get-Content -Path $envFilePath
        $envContent | ForEach-Object {
            if ($_ -match '^(.*_DASHBOARD_PORT=)(\d+)$') {
                $prefix = $matches[1]
                $port = [int]$matches[2]
                $newPort = $port + $num_instances_created + 1
                $prefix + $newPort
                echo_and_log_message "Updating port for $prefix to $newPort in $instancedir"
            } else {
                $_
            }
        } | Set-Content -Path $envFilePath

        echo_and_log_message -Message "Updated .env file with unique COMPOSE_PROJECT_NAME, DEVICE_NAME, and STACK_PROXY for $instanceName"
        # Find all files starting with claim and put them in an array and if the array is not empty then loop through the array and update the UUID in the .env file
        $claimFiles = Get-ChildItem -Path $instanceDir -Filter "claim*.txt"
        # if the array is empty then print a message and skip the UUID update
        if ($claimFiles.Count -eq 0) {
            echo_and_log_message -Message "No claim*.txt files found in $instanceDir. Skipping UUID update."
        } else {
            # Loop through claim files identify the app name and update its UUID in .env file
            foreach ($file in $claimFiles) {
                $fileName = $file.Name
                $appName = $fileName -replace '^claim', '' -replace 'NodeDevice.txt$', ''
                echo_and_log_message -Message "Updating UUID for $fileName"
        
                $envVarName = "${appName}_DEVICE_UUID"
                $envContent = Get-Content -Path $envFilePath
                $oldUUID = ($envContent | Where-Object { $_ -match "$envVarName=" }) -split '=', 2 | Select-Object -Last 1
                echo_and_log_message -Message "Old UUID extracted from .env file: $oldUUID"
        
                $uuidPrefixes = @("sdk-node-")
                $prefix = ""
                $modifiedUUID = $oldUUID
        
                foreach ($pfx in $uuidPrefixes) {
                    if ($modifiedUUID.StartsWith($pfx)) {
                        $prefix = $pfx
                        $modifiedUUID = $modifiedUUID.Substring($pfx.Length)
                        break
                    }
                }
        
                # Generate new UUID of the same length as the modified old UUID
                $newUUID = ""
                while ($newUUID.Length -lt $modifiedUUID.Length) {
                    $newUUID +=   [System.BitConverter]::ToString([System.Security.Cryptography.MD5]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))).Replace("-", "").ToLower()
                }
                # Cut or trail the generated UUID based on the desired length
                $newUUID = $newUUID.Substring(0, $modifiedUUID.Length)
                # Append the prefix if it was present
                $fullNewUUID = $prefix + $newUUID
                echo_and_log_message -Message "New UUID generated: $fullNewUUID"

                # Replace UUID in claim file and .env file
                # Update UUID in claim file
                (Get-Content -Path $file.FullName) -replace $oldUUID, $fullNewUUID | Set-Content -Path $file.FullName
                # Update UUID in .env file
                $envContent = Get-Content -Path $envFilePath
                $envContent -replace "$envVarName=.*", "$envVarName=$fullNewUUID" | Set-Content -Path $envFilePath
            }
        }

        # Run docker-compose up -d in the instance directory
        Set-Location -Path $instanceDir
        try {
            docker-compose -f $dockerComposeFile --env-file $envFile up -d 
            # Increase the instance count
            $num_instances_created++
            echo_and_log_message -Message "Docker compose up for $instanceName succeeded." -Color "Green"
            # Call the script to generate dashboards urls for the apps that has them and check if execute correctly
            $dashboardsScriptPath = Join-Path -Path $instanceDir -ChildPath "generate_dashboard_urls.ps1"
            if (Test-Path -Path $dashboardsScriptPath) {
                echo_and_log_message -Message "Generating dashboards file for $instanceName..."
                & $dashboardsScriptPath 
            } else {
                echo_and_log_message -Message "Error: $dashboardsScriptPath not found." -Type "ERROR"
            }
        } catch {
            echo_and_log_message -Message "Docker compose up for $instanceName failed." -Type "ERROR"
        }
    }
    
    # Return to root directory
    Set-Location -Path $rootDir

    echo_and_log_message -Message "Updating dashboard urls aggreting new information from all instances..."
    # Call the script generate_dashboard_urls to aggregate the dashboards urls from all instances
    $dashboardsScriptPath = Join-Path -Path $rootDir -ChildPath "generate_dashboard_urls.ps1"
    if (Test-Path -Path $dashboardsScriptPath) {
        & $dashboardsScriptPath 
        if ($LASTEXITCODE -ne 0) {
            echo_and_log_message -Message "Failed to update dashboards file." -Type "ERROR"
        } else {
            echo_and_log_message -Message "Dashboards file updated successfully." -Color "Green"
        }
    } else {
        echo_and_log_message -Message "Error: $dashboardsScriptPath not found." -Type "ERROR"
    }
  
    
    # Final message indicating completion
    echo_and_log_message -Message "Created and ran $num_instances_created instances out of $num_proxies_avail proxies available. Bye!" -Color "Green"
    echo_and_log_message -Message "Check the generated dashboards file and claim nodes files for their URLs." -Color "Yellow" 
    Start-Sleep -Seconds 3
    exit 0   
} else {
    echo_and_log_message -Message "The Instances directory $instancesDir does not exist. Exiting..." -Type "ERROR"
    exit 1
}
