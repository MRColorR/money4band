#!/bin/pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force

### Variables and constants ###
## Script variables ##
# Script version #
$SCRIPT_VERSION = "2.2.0" # used for checking updates

# Script name #
$SCRIPT_NAME = $MyInvocation.MyCommand.Name # save the script name in a variable, not the full path

# Script URL for update #
$UPDATE_SCRIPT_URL = "https://raw.githubusercontent.com/MRColorR/money4band/main/$SCRIPT_NAME"

# Script debug log file #
$DEBUG_LOG = "debug_$SCRIPT_NAME.log"

## Env file related constants and variables ##
# .env file prototype link #
$ENV_SRC = 'https://github.com/MRColorR/money4band/raw/main/.env'
# Env file default #
$DEVICE_NAME_PLACEHOLDER = 'yourDeviceName'
$script:DEVICE_NAME = 'yourDeviceName'
# Proxy config #
$script:PROXY_CONF = $false
$script:STACK_PROXY = ''
$script:NEW_STACK_PROXY = ''

## Config file related constants and variables ##
$CONFIG_JSON_FILE = "config.json"

## Docker compose related constants and variables ##
# docker compose yaml file name #
$DKCOM_FILENAME = "docker-compose.yaml"
# docker compose yaml prototype file link #
$DKCOM_SRC = "https://github.com/MRColorR/money4band/raw/main/$DKCOM_FILENAME"

### Docker installer script for Windows source link ##
$DKINST_WIN_SRC = 'https://github.com/MRColorR/money4band/raw/main/.resources/.scripts/install-docker-win.ps1'
### Docker installer script for Mac source link ##
$DKINST_MAC_SRC = 'https://github.com/MRColorR/money4band/raw/main/.resources/.scripts/install-docker-mac.ps1'

### Resources, Scripts and Files folders ###
$script:RESOURCES_DIR = "$PWD\.resources"
$script:CONFIG_DIR = "$RESOURCES_DIR\.www\.configs"
$script:SCRIPTS_DIR = "$RESOURCES_DIR\.scripts"
$script:FILES_DIR = "$RESOURCES_DIR\.files"

## Architecture and OS related constants and variables ##
# Architecture default. Also define a map for the recognized architectures #

$script:ARCH = 'unknown'
$script:DKARCH = 'unknown'
$arch_map = @{
    "x86_64"  = "amd64";
    "amd64"   = "amd64";
    "aarch64" = "arm64";
    "arm64"   = "arm64";
    "x86"     = "x86";
}

# OS default. Also define a map for the recognized OSs #
$script:OS_TYPE = 'unknown'
# Define the OS type map
$os_map = @{
    "win32nt"    = "Windows"
    "windows_nt" = "Windows"
    "windows"    = "Windows"
    "linux"      = "Linux";
    "darwin"     = "MacOS";
    "macos"      = "MacOS";
    "macosx"     = "MacOS";
    "osx"        = "MacOS";
    "cygwin"     = "Cygwin";
    "mingw"      = "MinGw";
    "msys"       = "Msys";
    "freebsd"    = "FreeBSD";
}

## Colors ##
# Colors used inside the script #
$colors = @{
    "default" = [System.ConsoleColor]::White
    "green"   = [System.ConsoleColor]::Green
    "blue"    = [System.ConsoleColor]::Blue
    "red"     = [System.ConsoleColor]::Red
    "yellow"  = [System.ConsoleColor]::Yellow
    "magenta" = [System.ConsoleColor]::Magenta
    "cyan"    = [System.ConsoleColor]::Cyan
    "purple"  = [System.ConsoleColor]::DarkMagenta
}

# Color functions #
function colorprint($color, $text) {
    $color = $color.ToLower()
    $prevColor = [System.Console]::ForegroundColor
    if ($colors.ContainsKey($color)) {
        [System.Console]::ForegroundColor = $colors[$color]
        Write-Output $text
        [System.Console]::ForegroundColor = $prevColor
    }
    else {
        Write-Output "Unknown color: $color. Available colors are: $($colors.Keys -join ', ')"
    }
}

# Function to manage unexpected choices of flags #
function fn_unknown($REPLY) {
    colorprint "Red" "Unknown choice $REPLY, please choose a valid option"
}

# Function to exit the script gracefully #
function fn_bye {
    colorprint "Green" "Share this app with your friends thank you!"
    print_and_log "Green" "Exiting the application...Bye!Bye!"
    exit 0
}

### Log, Update and Utility functions ###
## Enable or disable logging using debug mode ##
# Check if the first argument is -d or --debug if so, enable debug mode
if ($args[0] -eq '-d' -or $args[0] -eq '--debug') {
    $script:DEBUG = $true
    # shift the arguments array to remove the debug flag consumed
    $args = $args[1..$args.Length]
    debug "[DEBUG]: Debug mode enabled."
}
else {
    $script:DEBUG = $false
}

# Function to write debug messages to the debug log file #
function debug($text) {
    if ($script:DEBUG) {
        [DateTime]::Now.ToString("yyyy-MM-dd HH:mm:ss") + " - $text" | Out-File -FilePath $script:DEBUG_LOG -Append
    }
}

# Function to print an info message that will be also logged to the debug log file #
function print_and_log($color, $message) {
    colorprint $color $message
    debug "[INFO]: $message"
}

# Function to print an error message and write it to the debug log file #
function errorprint_and_log($text) {
    Write-Error $text
    debug "[ERROR]: $text"
}

# Function to print criticals errors that will stop the script execution, write them to the debug log file and exit the script with code 1 #
function fn_fail($text) {
    errorprint_and_log $text
    Read-Host -Prompt "Press Enter to exit..."
    exit 1
}

## Utility functions ##
# Function to detect OS
function detect_os {
    debug "Detecting OS..."
    try {
        if ($PSVersionTable.Platform) {
            $OSStr = $PSVersionTable.Platform.ToString().ToLower()
        }
        elseif ($env:OS) {
            $OSStr = $env:OS.ToString().ToLower()
        }
        else {
            $OSStr = (uname -s).ToLower()
        }
        # check if OSStr contains any known OS substring
        $script:OS_TYPE = $os_map.Keys | Where-Object { $OSStr.Contains($_) } | Select-Object -First 1
    }
    catch {
        debug "Neither PS OS detection commands nor uname were found, OS detection failed. OS type will be set to 'unknown'."
        $script:OS_TYPE = 'unknown'        
    }
    debug "OS type detected: $script:OS_TYPE"
}

# Function to detect OS architecture and set the relative Docker architecture
function detect_architecture {
    debug "Detecting system architecture..."
    try {
        # Try to use the new PowerShell command
        if (Get-Command 'System.Runtime.InteropServices.RuntimeInformation::OSArchitecture' -ErrorAction SilentlyContinue) {
            $archStr = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLower()
        } 
        # Fallback to using uname if on a Unix-like system
        elseif (Get-Command 'uname' -ErrorAction SilentlyContinue) {
            $archStr = (uname -m).ToLower()
        } 
        # Final fallback to older PowerShell/Windows method
        else {
            $archStr = $env:PROCESSOR_ARCHITECTURE.ToLower()
        }

        $script:ARCH = $archStr
        $script:DKARCH = $arch_map[$archStr]
        if ($null -eq $script:DKARCH) {
            $script:DKARCH = "unknown"
        }
    }
    catch {
        debug "Neither PS arch detection commands nor uname were found, architecture detection failed. Architecture will be set to 'unknown'."
        $script:ARCH = 'unknown'
        $script:DKARCH = 'unknown'
    }

    debug "System architecture detected: $script:ARCH, Docker architecture has been set to $script:DKARCH"
}


# experimanetal function that provide support for installing packages using Chocolatey
function fn_install_packages {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $REQUIRED_PACKAGES
    )
    if ($script:OS_TYPE -eq "Windows") {
        # Check if Chocolatey is installed
        if (-not(Get-Command 'choco' -ErrorAction SilentlyContinue)) {
            colorprint "Yellow" "Chocolatey is not installed, this script will now attempt to install it for you."
            colorprint "Yellow" "Installing Chocolatey..."
            $ProgressPreference = 'SilentlyContinue'
            Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
            $ProgressPreference = 'Continue'
            # check if the installation was successful
            if (-not(Get-Command 'choco' -ErrorAction SilentlyContinue)) {
                fn_fail "Chocolatey installation failed. Please install Chocolatey manually and then try again."
            }
            colorprint "Green" "Chocolatey installed successfully."
        }
        # Install required packages
        foreach ($package in $REQUIRED_PACKAGES) {
            if (-not(choco list --local-only --exact $package)) {
                colorprint "Yellow" "$package not installed, Trying to install it now..."
                $ProgressPreference = 'SilentlyContinue'
                if (-not (choco install $package -y)) {
                    colorprint "Red" "Failed to install $package. Please install it manually and then try again."
                }
                $ProgressPreference = 'Continue'
                else {
                    colorprint "Green" "$package installed successfully."
                }
            }
            else {
                colorprint "Green" "$package already installed."
            }
        }
    }
    elseif ($script:OS_TYPE -eq "MacOS") {
        # Check if Homebrew is installed
        if (-not(Get-Command 'brew' -ErrorAction SilentlyContinue)) {
            colorprint "Yellow" "Homebrew is not installed, this script will now attempt to install it for you."
            colorprint "Yellow" "Installing Homebrew..."
            $ProgressPreference = 'SilentlyContinue'
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            $ProgressPreference = 'Continue'
            # check if the installation was successful
            if (-not(Get-Command 'brew' -ErrorAction SilentlyContinue)) {
                fn_fail "Homebrew installation failed. Please install Homebrew manually and then try again."
            }
            else {
                colorprint "Green" "Homebrew installed successfully."
            }
        }
        # Install required packages
        foreach ($package in $REQUIRED_PACKAGES) {
            if (-not(brew list --versions $package)) {
                print_and_log "Default" "$package not installed, Trying to install it now..."
                $ProgressPreference = 'SilentlyContinue'
                if (-not (brew install $package)) {
                    print_and_log "Failed to install $package. Please install it manually and then try again."
                }
                $ProgressPreference = 'Continue'
                else {
                    colorprint "Green" "$package installed successfully."
                }
            }
            else {
                colorprint "Green" "$package already installed."
            }
        }
    }
    elseif ($script:OS_TYPE -eq "Linux") {
        # Check which package manager is installed
        if (Get-Command apt -ErrorAction SilentlyContinue) {
            PKG_MANAGER = "apt"
            PKG_CHECK="dpkg -l"
            PKG_INSTALL="sudo apt install -y"
        }
        elseif (Get-Command yum -ErrorAction SilentlyContinue) {
            PKG_MANAGER = "yum"
            PKG_CHECK="rpm -qa"
            PKG_INSTALL="sudo yum install -y"
        }
        elseif (Get-Command dnf -ErrorAction SilentlyContinue) {
            PKG_MANAGER = "dnf"
            PKG_CHECK="rpm -q"
            PKG_INSTALL="sudo dnf install -y"
        }
        elseif (Get-Command pacman -ErrorAction SilentlyContinue) {
            PKG_MANAGER = "pacman"
            PKG_CHECK="pacman -Q"
            PKG_INSTALL="sudo pacman -S --noconfirm"
        }
        elseif (Get-Command zypper -ErrorAction SilentlyContinue) {
            PKG_MANAGER = "zypper"
            PKG_CHECK="rpm -q"
            PKG_INSTALL="sudo zypper install -y"
        }
        elseif (Get-Command apk -ErrorAction SilentlyContinue) {
            PKG_MANAGER = "apk"
            PKG_CHECK="apk info"
            PKG_INSTALL="sudo apk add"
        }
        elseif (Get-Command emerge -ErrorAction SilentlyContinue) {
            PKG_MANAGER = "emerge"
            PKG_CHECK="qlist -I"
            PKG_INSTALL="sudo emerge --ask n"
        }
        else {
            print_and_log "Red" "Your package manager has not been recognized by this script. Please install the following packages manually: $($REQUIRED_PACKAGES -join ', ')"
            Read-Input -Prompt "Press enter to continue"
            return
        }
        debug "Package manager detected: $PKG_MANAGER"
        # Install required packages
        foreach ($package in $REQUIRED_PACKAGES) {
            # Using Invoke-Expression to execute the package check command
            if (-not (Invoke-Expression "$PKG_CHECK $package")) {
                print_and_log "Default" "$package not installed, Trying to install it now..."
                $ProgressPreference = 'SilentlyContinue'
                # Using Invoke-Expression to execute the package install command
                if (-not (Invoke-Expression "$PKG_INSTALL $package")) {
                    print_and_log "Red" "Failed to install $package. Please install it manually and then try again."
                }
                else {
                    colorprint "Green" "$package installed successfully."
                }
                $ProgressPreference = 'Continue'
            }
            else {
                colorprint "Green" "$package already installed."
            }
        }
    }
    else {
        print_and_log "Red" "Your operating system has not been recognized or is not supported by this function. Please install the following packages manually: $($REQUIRED_PACKAGES -join ', ')"
        Read-Input -Prompt "Press enter to continue"
        return
    }
    debug "Required packages installation completed."
}

### Sub-menu Functions ###
# Shows the liks of the apps
function fn_showLinks {
    Clear-Host
    colorprint "Green" "Use CTRL+Click to open links or copy them:"
    $configPath = Join-Path -Path $CONFIG_DIR -ChildPath $CONFIG_JSON_FILE
    $configData = Get-Content -Path $configPath -Raw | ConvertFrom-Json
    # Iterate over the top-level keys (app types) in the JSON
    foreach ($appType in $configData.PSObject.Properties.Name) {
        colorprint "Yellow" "---$appType---"
        # Iterate over the apps in each type
        foreach ($app in $configData.$appType) {
            colorprint "Default" $app.name
            colorprint "Blue" $app.link
        }
    }
    Read-Host -Prompt "Press Enter to go back to mainmenu"
}

<#
.SYNOPSIS
Function that will attempt to install Docker on different OSs

.DESCRIPTION
This function will attempt to install Docker on different OSs. It will ask the user to choose the OS and then it will launch the appropriate script to install Docker on the selected OS. If Docker is already installed it will ask the user if he wants to proceed with the installation anyway.

.EXAMPLE
Just call fn_dockerInstall

.NOTES
This function has been tested until v 2.0.0 on windows and mac but not on linux yet. The new version has not been tested as its assume that the logic is the same as the previous one just more refined. 
#>
function fn_dockerInstall {
    Clear-Host
    debug "DockerInstall function started"
    colorprint "Yellow" "This menu item will launch a script that will attempt to install Docker"
    colorprint "Yellow" "Use it only if you do not know how to perform the manual Docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some cases and depending on the OS you are using may fail to install Docker correctly."
    
    while ($true) {
        $yn = (Read-Host -Prompt "Do you wish to proceed with the Docker automatic installation Y/N?").ToLower()
        if ($yn -eq 'y' -or $yn -eq 'yes') {
            debug "User decided to install Docker through the script. Checking if Docker is already installed."
            try {
                $dockerVersion = docker --version
                if ($dockerVersion) {
                    debug "Docker is already installed. Asking user if he wants to continue with the installation anyway."
                    while ($true) {
                        colorprint "Yellow" "Docker seems to be installed already. Do you want to continue with the installation anyway? (Y/N)"
                        $yn = (Read-Host -Prompt "").ToLower()
                        if ($yn -eq 'n' -or $yn -eq 'no') {
                            debug "User decided to abort the Docker re-install."
                            colorprint "Blue" "Returning to main menu..."
                            return
                        }
                        elseif ($yn -eq 'y' -or $yn -eq 'yes' ) {
                            debug "User decided to continue with the Docker re-install anyway."
                            break
                        }
                        else {
                            colorprint "Red" "Please answer yes or no."
                        }
                    }
                }
            }
            catch {
                print_and_log "DEFAULT" "Proceeding with Docker installation."
            }

            Clear-Host
            print_and_log "Yellow" "Installing Docker for $script:OS_TYPE"
            $InstallStatus = $false;
            
            Switch ($OSTYPE) {
                "Linux" {
                    Clear-Host
                    colorprint "Yellow" "Starting Docker for linux auto installation script"
                    $ProgressPreference = 'SilentlyContinue'
                    Invoke-WebRequest https://get.docker.com -o "$SCRIPTS_DIR/get-docker.sh"
                    $ProgressPreference = 'Continue'
                    sudo sh get-docker.sh;
                    $InstallStatus = $true;
                }
                "Windows" {
                    Clear-Host
                    colorprint "Yellow" "Starting Docker for Windows auto installation script"
                    $ProgressPreference = 'SilentlyContinue'
                    Invoke-WebRequest $DKINST_WIN_SRC -o "$SCRIPTS_DIR\install-docker-win.ps1"
                    $ProgressPreference = 'Continue'
                    Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -command `"$SCRIPTS_DIR\install-docker-win.ps1 -filesPath $FILES_DIR`"" -Wait
                    $InstallStatus = $true;              
                }
                "MacOS" {
                    Clear-Host
                    colorprint "Yellow" "Starting Docker for MacOS auto installation script"  
                    $ProgressPreference = 'SilentlyContinue'
                    Invoke-WebRequest $DKINST_MAC_SRC -o "$SCRIPTS_DIR\install-docker-mac.ps1"
                    $ProgressPreference = 'Continue'
                    colorprint "Yellow" "Select your CPU type"
                    colorprint "Yellow" "1) Apple silicon M1, M2...CPUs"
                    colorprint "Yellow" "2) Intel i5, i7...CPUs"
                    $cpuSel = Read-Host
                    switch ($cpuSel) {
                        1 {
                            Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -command `"$SCRIPTS_DIR\install-docker-mac.ps1 -filesPath $FILES_DIR`"" -Wait
                            $InstallStatus = $true;
                        }
                        2 {
                            Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -command `"$SCRIPTS_DIR\install-docker-mac.ps1 -filesPath $FILES_DIR -IntelCPU `"" -Wait
                            $InstallStatus = $true;
                        }
                        Default { fn_unknown "$cpuSel" }
                    }
                    
                }
                DEFAULT {
                    fn_unknown "$OSSel"
                }
            }
            if ($InstallStatus) {
                colorprint "Green" "Script completed. If no errors appeared Docker should be installed. Please restart your machine and then proceed to .env file config and stack startup."
            }
            else {
                colorprint "Red" "Something went wrong (maybe bad choice or incomplete installation), failed to install Docker automatically. Please try to install Docker manually by following the instructions on Docker website."
            }
            Read-Host -Prompt "Press enter to go back to mainmenu"
            break
        }
        elseif ($yn -eq 'n' -or $yn -eq 'no') {
            Clear-Host
            colorprint "Blue" "Docker unattended installation canceled. Make sure you have Docker installed before proceeding with the other steps."
            Read-Host -prompt "Press enter to go back to the menu"
            return
        }
        else {
            colorprint "Red" "Please answer yes or no."
        }
    }
}


<#
.SYNOPSIS
Function that will setup notifications about containers updates using shoutrrr

.DESCRIPTION
This function will setup notifications about containers updates using shoutrrr. It will ask the user to enter a link for notifications and then it will update the .env file and the docker-compose.yaml file accordingly.

.EXAMPLE
Just call fn_setupNotifications

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupNotifications() {
    Clear-Host
    colorprint "Yellow" "This step will setup notifications about containers updates using shoutrrr"
    colorprint "Default" "The resulting SHOUTRRR_URL should have the format: <app>://<token>@<webhook>."
    colorprint "Default" "Where <app> is one of the supported messaging apps on Shoutrrr (e.g. Discord), and <token> and <webhook> are specific to your messaging app."
    colorprint "Default" "To obtain the SHOUTRRR_URL, create a new webhook for your messaging app and rearrange its URL to match the format above."
    colorprint "Default" "For more details, visit https://containrrr.dev/shoutrrr/ and select your messaging app."
    colorprint "Default" "Now a Discord notification setup example will be shown (Remember: you can also use a different supported app)."
    Read-Host -Prompt "Press enter to continue"
    Clear-Host
    colorprint "Magenta" "Create a new Discord server, go to server settings > integrations, and create a webhook."
    colorprint "Magenta" "Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken."
    colorprint "Magenta" "To obtain the SHOUTRRR_URL, rearrange it to look like this: discord://YourToken@YourWebhookid."
    Read-Host -Prompt "Press enter to proceed."
    Clear-Host
    while ($true) {
        colorprint "Yellow" "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"
        $SHOUTRRR_URL = Read-Host
        if ($SHOUTRRR_URL -match '^[a-zA-Z]+://') {
            (Get-Content .\.env).replace('# SHOUTRRR_URL=yourApp:yourToken@yourWebHook', "SHOUTRRR_URL=$SHOUTRRR_URL") | Set-Content .\.env
            (Get-Content .\$DKCOM_FILENAME).replace('# - WATCHTOWER_NOTIFICATIONS=shoutrrr', "  - WATCHTOWER_NOTIFICATIONS=shoutrrr") | Set-Content .\$DKCOM_FILENAME
            (Get-Content .\$DKCOM_FILENAME).replace('# - WATCHTOWER_NOTIFICATION_URL', "  - WATCHTOWER_NOTIFICATION_URL") | Set-Content .\$DKCOM_FILENAME
            (Get-Content .\$DKCOM_FILENAME).replace('# - WATCHTOWER_NOTIFICATIONS_HOSTNAME', "  - WATCHTOWER_NOTIFICATIONS_HOSTNAME") | Set-Content .\$DKCOM_FILENAME
            colorprint "DEFAULT" "Notifications setup complete. If the link is correct, you will receive a notification for each update made on the app container images."
            Read-Host -p "Press enter to continue"
            break
        }
        else {
            colorprint "Red" "Invalid link format. Please make sure to use the correct format."
            while ($true) {
                colorprint "Yellow" "Do you wish to try again or leave the notifications disabled and continue with the setup script? (Yes to try again, No to continue without notifications) Y/N?"
                $yn = Read-Host
                $yn = $yn.ToLower()
                if ($yn -eq 'y' -or $yn -eq 'yes') {
                    break
                }
                elseif ($yn -eq 'n' -or $yn -eq 'no') {
                    return
                }
                else {
                    colorprint "Red" "Please answer yes or no."
                }
            }
        }
    }
    Clear-Host
}

<#
.SYNOPSIS
This function will manage the setup of each app in the stack

.DESCRIPTION
This function will manage the setup of each app in the stack. It will ask the user to enter the required data for each app and then it will update the .env file and the docker-compose.yaml file accordingly.

.PARAMETER app
App name and image are required parameters. The app name is used to identify the app in the setup process.

.PARAMETER image
the image is used to feryfy if the image supports the current architecture and to update the docker-compose.yaml file accordingly.

.PARAMETER flags
Optional parameter. If the app requires an email to be setup, this parameter will be used to update the .env file.

.EXAMPLE
fn_setupApp -app "HONEYGAIN" -image "honeygain/honeygain" -email "email" -password "password"

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupApp {
    param (
        [Parameter(Mandatory = $true)]
        [string]$app,
        [Parameter(Mandatory = $true)]
        [string]$image,
        [Parameter(Mandatory = $false)]
        [string[]]$flags
    )
    $APP_NAME = $app
    $APP_IMAGE = $image
    $uuid = $false
    $email = $false
    $password = $false
    $apikey = $false
    $userid = $false
    $uuid = $false
    $cid = $false
    $token = $false
    $customScript = $null
    $manual = $false

    #Write-Output "passed parameters: APP: $app, IMG: $image, FLAGS: $flags"
    #Read-Host -Prompt "This is for debug Press enter to continue"
    $CURRENT_APP = $APP_NAME
    if ($app) { (Get-content $script:DKCOM_FILENAME) -replace "#${CURRENT_APP}_ENABLE", "" | Set-Content $script:DKCOM_FILENAME }

    for ($i = 0; $i -lt $flags.Count; $i++) {
        switch ($flags[$i]) {
            "--email" { $email = $true }
            "--password" { $password = $true }
            "--apikey" { $apikey = $true }
            "--userid" { $userid = $true }
            "--uuid" { $uuid = $true }
            "--cid" { $cid = $true }
            "--token" { $token = $true }
            "--customScript" {
                $customScript = $flags[$i + 1] # consider the element after --customScript as the script name
                $i++ # increment the index to skip the next element
            }
            "--manual" { $manual = $true }
            default { colorprint "RED" "Unknown flag: $($flags[$i])" }
        }
    }
    
    if ($email) {
        while ($true) {
            colorprint "GREEN" "Enter your ${CURRENT_APP} Email:"
            $APP_EMAIL = Read-Host
            if ($APP_EMAIL -match '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-zA-Z]{2,}$') {
                (Get-Content .env) -replace "your${CURRENT_APP}Mail", $APP_EMAIL | Set-Content .env
                break
            }
            else {
                colorprint "RED" "Invalid email address. Please try again."
            }
        }
    }

    if ($password) {
        while ($true) {
            colorprint "DEFAULT" "Note: If you are using login with Google, remember to set also a password for your ${CURRENT_APP} account!"
            colorprint "GREEN" "Enter your ${CURRENT_APP} Password:"
            $APP_PASSWORD = Read-Host
            if ($APP_PASSWORD) {
                (Get-Content .env) -replace "your${CURRENT_APP}Pw", $APP_PASSWORD | Set-Content .env
                break
            }
            else {
                colorprint "RED" "Password cannot be empty. Please try again."
            }
        }
    }

    if ($apikey) {
        colorprint "DEFAULT" "Find/Generate your APIKey inside your ${CURRENT_APP} dashboard/profile."
        colorprint "GREEN" "Enter your ${CURRENT_APP} APIKey:"
        $APP_APIKEY = Read-Host
        (Get-Content .env) -replace "your${CURRENT_APP}APIKey", $APP_APIKEY | Set-Content .env
    }

    if ($userid) {
        colorprint "DEFAULT" "Find your UserID inside your ${CURRENT_APP} dashboard/profile."
        colorprint "GREEN" "Enter your ${CURRENT_APP} UserID:"
        $APP_USERID = Read-Host
        (Get-Content .env) -replace "your${CURRENT_APP}UserID", $APP_USERID | Set-Content .env
    }

    if ($uuid) {
        colorprint "DEFAULT" "Starting UUID generation/import for ${CURRENT_APP}"
        $SALT = "$script:DEVICE_NAME$((Get-Random))"
        $UUID = New-Object System.Security.Cryptography.MD5CryptoServiceProvider
        $hash = $UUID.ComputeHash([System.Text.Encoding]::ASCII.GetBytes($SALT))
        $UUID = ([System.BitConverter]::ToString($hash) -replace '-', '')
        while ($true) {
            colorprint "YELLOW" "Do you want to use a previously registered sdk-node-uuid for ${CURRENT_APP}? (yes/no)"
            $USE_EXISTING_UUID = Read-Host
            $USE_EXISTING_UUID = $USE_EXISTING_UUID.ToLower()
        
            if ($USE_EXISTING_UUID -eq "yes" -or $USE_EXISTING_UUID -eq "y") {
                while ($true) {
                    colorprint "GREEN" "Please enter the 32 char long alphanumeric part of the existing sdk-node-uuid for ${CURRENT_APP}:"
                    colorprint "DEFAULT" "E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4"
                    $EXISTING_UUID = Read-Host
                    if ($EXISTING_UUID -notmatch '^[a-f0-9]{32}$') {
                        colorprint "RED" "Invalid UUID entered, it should be an md5 hash and 32 characters long."
                        colorprint "DEFAULT" "Do you want to try again? (yes/no)"
                        $TRY_AGAIN = Read-Host
                        $TRY_AGAIN = $TRY_AGAIN.ToLower()
                        if ($TRY_AGAIN -eq "no" -or $TRY_AGAIN -eq "n") { break }
                    }
                    else {
                        $UUID = $EXISTING_UUID
                        break
                    }
                }
                break
            }
            elseif ($USE_EXISTING_UUID -eq "no" -or $USE_EXISTING_UUID -eq "n") {
                break
            }
            else {
                colorprint "RED" "Please answer yes or no."
            }
        }   
        $UUID = $UUID.ToLower() 
        (Get-Content .env) -replace "your${CURRENT_APP}MD5sum", $UUID | Set-Content .env
        colorprint "DEFAULT" "${CURRENT_APP} UUID setup: done"
        colorprint "BLUE" "Save the following link somewhere to claim your ${CURRENT_APP} node after completing the setup and starting the apps stack: https://earnapp.com/r/sdk-node-$UUID."
        colorprint "DEFAULT" "A new file containing this link has been created for you in the current directory"
        "https://earnapp.com/r/sdk-node-$UUID" | Out-File -FilePath 'ClaimEarnappNode.txt'
    }

    if ($cid) {
        colorprint "DEFAULT" "Find your CID, you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on ->View your configuration file<-."
        colorprint "GREEN" "Enter your ${CURRENT_APP} CID:"
        $APP_CID = Read-Host
        (Get-Content .env) -replace "your${CURRENT_APP}CID", $APP_CID | Set-Content .env
    }

    if ($token) {
        colorprint "DEFAULT" "Find your Token inside your ${CURRENT_APP} dashboard/profile."
        colorprint "GREEN" "Enter your ${CURRENT_APP} Token:"
        $APP_TOKEN = Read-Host
        (Get-Content .env) -replace "your${CURRENT_APP}Token", $APP_TOKEN | Set-Content .env
    }

    if ($customScript) {
        $SCRIPT_NAME = "${customScript}.ps1"
        $SCRIPT_PATH = Join-Path -Path $script:SCRIPTS_DIR -ChildPath $SCRIPT_NAME
        if (Test-Path -Path $SCRIPT_PATH) {
            Set-Content $SCRIPT_PATH -Value (Get-Content $SCRIPT_PATH) -Encoding UTF8
            colorprint "DEFAULT" "Executing custom script: $SCRIPT_NAME"
            Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -command `"cd '$pwd'; & '$SCRIPT_PATH';`"" -wait
        }
        else {
            colorprint "RED" "Custom script '$SCRIPT_NAME' not found in the scripts directory."
        }
    }
    if ($manual) {
        colorprint "DEFAULT" "${CURRENT_APP} requires further manual configuration."
        colorprint "DEFAULT" "Please after completing this automated setup follow the manual steps described on the app's website."
    }
    # App Docker image architecture adjustments
    $TAG = 'latest'

    # Ensure $supported_tags is an array
    $supported_tags = @()

    # Send a request to DockerHub for a list of tags
    $page_index = 1
    $page_size = 500
    $ProgressPreference = 'SilentlyContinue'
    $json = Invoke-WebRequest -Uri "https://registry.hub.docker.com/v2/repositories/${APP_IMAGE}/tags?page=${page_index}&page_size=${page_size}" -UseBasicParsing | ConvertFrom-Json
    $ProgressPreference = 'Continue'

    # Filter out the tags that do not support the specified architecture
    $json.results | ForEach-Object {
        $ntag = $_.name
        if (($_.images | Where-Object { $_.architecture -eq $DKARCH })) {
            $supported_tags += $ntag
        }
    }

    # Check if there are any tags that support the given architecture
    if ($supported_tags) {
        colorprint "default" "There are $($supported_tags.Count) tags supporting $DKARCH arch for this image"
        colorprint "default" "Let's see if $TAG tag is in there"
        
        # Check if 'latest' tag is among them
        if ($supported_tags -contains $TAG) {
            colorprint "green" "OK, $TAG tag present and it supports $DKARCH arch, nothing to do"
        }
        else {
            colorprint "yellow" "$TAG tag does not support $DKARCH arch but other tags do, the newer tag supporting $DKARCH will be selected"
            # Replace 'latest' tag with the first one that supports the given architecture in your Docker compose file
            $newTag = $supported_tags[0]
        (Get-Content $script:DKCOM_FILENAME).replace("${APP_IMAGE}:$TAG", "${APP_IMAGE}:$newTag") | Set-Content $DKCOM_FILENAME
        }
    }
    else {
        colorprint "yellow" "No native image tag found for $DKARCH arch, emulation layer will try to run this app image anyway."
        #colorprint "default" "If an emulation layer is not already installed, the script will try to install it now. Please provide your sudo password if prompted."
    }
    
    Write-Host "$app configuration complete, press enter to continue to the next app"
    Read-Host
}

<#
.SYNOPSIS
Function that will setup the proxy for the apps in the stack

.DESCRIPTION
This function will setup the proxy for the apps in the stack. It will ask the user to enter the proxy to use and then it will update the .env file and the docker-compose.yaml file accordingly.

.EXAMPLE
Just call fn_setupProxy

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupProxy() {
    if ($script:PROXY_CONF -eq $false) {
        while ($true) {
            colorprint "YELLOW" "Do you wish to setup a proxy for the apps in this stack Y/N?"
            colorprint "DEFAULT" "Note that if you want to run multiple instances of the same app, you will need to configure different env files in different project folders (copy the project to multiple different folders and configure them using different proxies)."
            $yn = Read-Host

            if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                Clear-Host
                colorprint "YELLOW" "Proxy setup started."
                $script:RANDOM_VALUE = Get-Random
                colorprint "GREEN" "Insert the designed proxy to use. Eg: protocol://proxyUsername:proxyPassword@proxy_url:proxy_port or just protocol://proxy_url:proxy_port if auth is not needed:"
                $script:STACK_PROXY = Read-Host 
                colorprint "DEFAULT" "Ok, $script:STACK_PROXY will be used as proxy for all apps in this stack"
                Read-Host -p "Press enter to continue"
                $script:PROXY_CONF = $true
                # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                (Get-Content .\.env).replace("COMPOSE_PROJECT_NAME=money4band", "COMPOSE_PROJECT_NAME=money4band_$($script:RANDOM_VALUE)") | Set-Content .\.env
                (Get-Content .\.env).replace("DEVICE_NAME=$($script:DEVICE_NAME)", "DEVICE_NAME=$($script:DEVICE_NAME)$($script:RANDOM_VALUE)") | Set-Content .\.env
                # uncomment .env and compose file
                (Get-Content .\.env).replace("# STACK_PROXY=", "STACK_PROXY=$($script:STACK_PROXY)") | Set-Content .\.env
                (Get-Content "$script:DKCOM_FILENAME").replace("#PROXY_ENABLE", "") | Set-Content "$script:DKCOM_FILENAME"
                (Get-Content "$script:DKCOM_FILENAME").replace("# network_mode", "network_mode") | Set-Content "$script:DKCOM_FILENAME"
                break
            }
            elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                colorprint "BLUE" "Ok, no proxy added to configuration."
                Start-Sleep -Seconds 1
                break
            }
            else {
                colorprint "RED" "Please answer yes or no."
            }
        }
    }
}


<#
.SYNOPSIS
Function that will setup the .env file and the docker compose file

.DESCRIPTION
This function will setup the .env file and the docker compose file. It will ask the user to enter the required data for each app and then it will update the .env file and the docker-compose.yaml file accordingly.

.EXAMPLE
Just call fn_setupEnv

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupEnv() {
    while ($true) {
        colorprint "YELLOW" "Do you wish to proceed with the .env file guided setup Y/N? (This will also adapt the $($script:DKCOM_FILENAME) file accordingly)"
        $yn = Read-Host

        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            Clear-Host
            if ((Get-Content .\.env) -NotContains "DEVICE_NAME=$($script:DEVICE_NAME)") {
                colorprint "DEFAULT" "The current .env file appears to have already been modified. A fresh version will be downloaded and used."
                $ProgressPreference = 'SilentlyContinue'
                Invoke-WebRequest -Uri $script:ENV_SRC -OutFile ".env"
                Invoke-WebRequest -Uri $script:DKCOM_SRC -OutFile "$($script:DKCOM_FILENAME)"
                $ProgressPreference = 'Continue'
                Clear-Host
            }
            colorprint "YELLOW" "beginning env file guided setup"
            $script:CURRENT_APP = ''
            colorprint "YELLOW" "PLEASE ENTER A NAME FOR YOUR DEVICE:"
            $script:DEVICE_NAME = Read-Host
            (Get-Content .\.env).replace("yourDeviceName", $script:DEVICE_NAME) | Set-Content .\.env
            Clear-Host
            fn_setupProxy
            Clear-Host

            $apps = Get-Content "$script:CONFIG_DIR/config.json" | ConvertFrom-Json | Select-Object -ExpandProperty apps

            foreach ($app in $apps) {
                Clear-Host
                colorprint "YELLOW" "PLEASE REGISTER ON THE PLATFORMS USING THE FOLLOWING LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
                colorprint "GREEN" "Use CTRL+Click to open links or copy them:"
                $name = $app.name
                $link = $app.link
                $image = $app.image
                $flags = $app.flags

                $script:CURRENT_APP = $name.ToUpper()

                while ($true) {
                    colorprint "YELLOW" "Do you wish to enable and use $($script:CURRENT_APP)? (Y/N)"
                    $yn = Read-Host

                    if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                        try {
                            colorprint "CYAN" "Go to ${name} ${link} and register"
                            Read-Host -p "When done, press enter to continue"
                            # Pass the flags string to the function
                            fn_setupApp "$($script:CURRENT_APP)" "$image" $flags
                            Clear-Host
                            break
                        }
                        catch {
                            colorprint "RED" "An error occurred while setting up $($script:CURRENT_APP). Please try again."
                            Read-Host -p "Press enter to continue to the next app"
                            break
                        }
                    }
                    elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                        colorprint "BLUE" "$($script:CURRENT_APP) setup will be skipped."
                        Read-Host -p "Press enter to continue to the next app"
                        break
                    }
                    else {
                        colorprint "RED" "Please answer yes or no."
                    }
                }
            }

            # Notifications setup
            Clear-Host
            while ($true) {
                colorprint "YELLOW" "Do you wish to setup notifications about apps images updates (Yes to receive notifications and apply updates, No to just silently apply updates) Y/N?"
                $yn = Read-Host
                if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                    fn_setupNotifications
                    break
                }
                elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                    colorprint "BLUE" "Noted: all updates will be applied automatically and silently"
                    break
                }
                else {
                    colorprint "RED" "Invalid input. Please answer yes or no."
                }
            }

            colorprint "GREEN" "env file setup complete."
            Read-Host -p "Press any key to go back to the menu"
            break
        }
        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
            colorprint "BLUE" ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup."
            Read-Host -p "Press Enter to go back to mainmenu"
            return
        }
        else {
            colorprint "RED" "Please answer yes or no."
        }
    }
}

<#
.SYNOPSIS
Function that will start the apps stack using the configured .env file and the docker compose file.

.DESCRIPTION
This function will start the apps stack using the configured .env file and the docker compose file.

.EXAMPLE
Just call fn_startStack

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_startStack() {
    Clear-Host
    while ($true) {
        colorprint "YELLOW" "This menu item will launch all the apps using the configured .env file and the $($script:DKCOM_FILENAME) file (Docker must be already installed and running)"
        $yn = Read-Host "Do you wish to proceed Y/N?"
        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            if (docker compose up -d) {
                colorprint "GREEN" "All Apps started. You can visit the web dashboard on http://localhost:8081/. If not already done, use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details."
            }
            else {
                colorprint "RED" "Error starting Docker stack. Please check the configuration and try again."
            }
            Read-Host "Now press enter to go back to the menu"
            break
        }
        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
            colorprint "BLUE" "Docker stack startup canceled."
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        else {
            colorprint "RED" "Please answer yes or no."
        }
    }
}

<#
.SYNOPSIS
Function that will stop all the apps and delete the docker stack previously created using the configured .env file and the docker compose file.

.DESCRIPTION
This function will stop all the apps and delete the docker stack previously created using the configured .env file and the docker compose file.

.EXAMPLE
Just call fn_stopStack

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_stopStack() {
    Clear-Host
    while ($true) {
        colorprint "YELLOW" "This menu item will stop all the apps and delete the docker stack previously created using the configured .env file and the $($script:DKCOM_FILENAME) file."
        $yn = Read-Host "Do you wish to proceed Y/N?"

        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            if (docker compose down) {
                colorprint "GREEN" "All Apps stopped and stack deleted."
            }
            else {
                colorprint "RED" "Error stopping and deleting Docker stack. Please check the configuration and try again."
            }
            Read-Host "Now press enter to go back to the menu"
            break
        }
        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
            colorprint "BLUE" "Docker stack removal canceled."
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        else {
            colorprint "RED" "Please answer yes or no."
        }
    }
}

<#
.SYNOPSIS
Function that will reset the .env file

.DESCRIPTION
This function will reset the .env file to the original version downloading a fresh copy from the repository.

.EXAMPLE
Just call fn_resetEnv

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_resetEnv() {
    Clear-Host
    while ($true) {
        colorprint "YELLOW" "Now a fresh env file will be downloaded and will need to be configured to be used again"
        $yn = Read-Host "Do you wish to proceed Y/N?"
        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            try {
                $ProgressPreference = 'SilentlyContinue'
                Invoke-WebRequest -Uri $script:ENV_SRC -OutFile ".env"
                $ProgressPreference = 'Continue'
                colorprint "GREEN" ".env file resetted, remember to reconfigure it"
            }
            catch {
                colorprint "RED" "Error resetting .env file. Please check your internet connection and try again."
            }
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
            colorprint "BLUE" ".env file reset canceled. The file is left as it is"
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        else {
            colorprint "RED" "Please answer yes or no."
        }
    }
}


<#
.SYNOPSIS
Function that will reset the docker-compose.yaml file

.DESCRIPTION
This function will reset the docker-compose.yaml file to the original version downloading a fresh copy from the repository.

.EXAMPLE
Just call fn_resetDockerCompose

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_resetDockerCompose() {
    Clear-Host
    while ($true) {
        colorprint "YELLOW" "Now a fresh $($script:DKCOM_FILENAME) file will be downloaded"
        $yn = Read-Host "Do you wish to proceed Y/N?"
        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            try {
                $ProgressPreference = 'SilentlyContinue'
                Invoke-WebRequest -Uri $script:DKCOM_SRC -OutFile "$($script:DKCOM_FILENAME)"
                $ProgressPreference = 'Continue'
                colorprint "GREEN" "$($script:DKCOM_FILENAME) file resetted, remember to reconfigure it if needed"
            }
            catch {
                colorprint "RED" "Error resetting $($script:DKCOM_FILENAME) file. Please check your internet connection and try again."
            }
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
            colorprint "BLUE" "$($script:DKCOM_FILENAME) file reset canceled. The file is left as it is"
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        else {
            colorprint "RED" "Please answer yes or no."
        }
    }
}


<#
.SYNOPSIS
Function that will check the necerrary dependencies for the script to run
.DESCRIPTION
This function will check the necerrary dependencies for the script to run
.EXAMPLE
Just call fn_checkDependencies
.NOTES
This is a new function that has not been tested yet and currently is not really used in the script 
#>
function fn_checkDependencies() {
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP"
    colorprint "GREEN" "--------------------------------- "
    colorprint "YELLOW" "Checking dependencies..."
    # this need to be changed to dinamically read depenedncies for any platform and select and install all the dependencies for the current platform
    # Check if dependencies are installed
    if (!(Get-Command "jq" -ErrorAction SilentlyContinue)) { 
        #colorprint "YELLOW" "Now a small useful package named JQ used to manage JSON files will be installed if not already present"
        #colorprint "YELLOW" "Please, if prompted, enter your sudo password to proceed"
        #fn_install_packages "jq"
    }
    else {
        colorprint "BLUE" "Done, script ready to go"
    }
}

<#
.SYNOPSIS
Main menu function

.DESCRIPTION
This function will show the main menu and will call the other functions based on the user's choice.

.EXAMPLE
Just call mainmenu

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function mainmenu {
    Clear-Host       
    $options = @("Show supported apps' links", "Install Docker", "Setup .env file", "Start apps stack", "Stop apps stack", "Reset .env File", "Reset $($script:DKCOM_FILENAME) file", "Quit")
    
    Do {
        Clear-Host
        colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v$script:SCRIPT_VERSION"
        colorprint "GREEN" "------------------------------------------ "
        colorprint "DEFAULT" "Detected OS type: $($script:OS_TYPE)"
        colorprint "DEFAULT" "Detected architecture $($script:ARCH)"
        colorprint "DEFAULT" "Docker $($script:DKARCH) image architecture will be used if the app's image permits it"
        colorprint "DEFAULT" "------------------------------------------ "
        for ($i = 0; $i -lt $options.Length; $i++) {
            Write-Output "$($i + 1)) $($options[$i])"
        }

        $Select = Read-Host "Select an option and press Enter"

        Switch ($Select) {
            1 { Clear-Host; fn_showLinks }
            2 { Clear-Host; fn_dockerInstall }
            3 { Clear-Host; fn_setupEnv }
            4 { Clear-Host; fn_startStack }
            5 { Clear-Host; fn_stopStack }
            6 { Clear-Host; fn_resetEnv }
            7 { Clear-Host; fn_resetDockerCompose }
            $options.Length { fn_bye; break }
            DEFAULT { Clear-Host; fn_unknown; }
        }
    }
    While ($Select -ne $options.Length)
}

### Startup ##
debug "Starting $script:SCRIPT_NAME v$script:SCRIPT_VERSION"
Clear-Host

# Detect the operating system
detect_os

# Detect the architecture and set the correct docker image architecture
detect_architecture

# Check dependencies
fn_checkDependencies

# Start the main menu
mainmenu