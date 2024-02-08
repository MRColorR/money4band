#!/bin/pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force

# Set culture to Invariant Culture to ensure consistent number formatting
[System.Threading.Thread]::CurrentThread.CurrentCulture = [System.Globalization.CultureInfo]::InvariantCulture

### Variables and constants ###
## Env file related constants and variables ##
# env file name and template file name #
$script:ENV_TEMPLATE_FILENAME = '.env.template'
$script:ENV_FILENAME = '.env'

# Env file default #
$DEVICE_NAME_PLACEHOLDER = 'yourDeviceName'
$script:DEVICE_NAME = 'yourDeviceName'
# Proxy config #
$script:PROXY_CONF = $false
$script:CURRENT_PROXY = ''
$script:NEW_STACK_PROXY = ''

## Config file related constants and variables ##
$script:APP_CONFIG_JSON_FILE = "app_config.json"
$script:MAINMENU_JSON_FILE = "mainmenu.json"

## Docker compose related constants and variables ##
# docker compose yaml file name and template file name #
$DKCOM_TEMPLATE_FILENAME = "docker-compose.yaml.template"
$DKCOM_FILENAME = "docker-compose.yaml"

### Docker installer script for Windows source link ##
$DKINST_WIN_SRC = 'https://github.com/MRColorR/money4band/raw/main/.resources/.scripts/install-docker-win.ps1'
### Docker installer script for Mac source link ##
$DKINST_MAC_SRC = 'https://github.com/MRColorR/money4band/raw/main/.resources/.scripts/install-docker-mac.ps1'
## Script init and variables ##
# Script default sleep time #
$SLEEP_TIME = 1.5

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
    "mac"        = "MacOS";
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
}

# Color functions #
function colorprint($color, $text) {
    $color = $color.ToLower()
    #$prevColor = [System.Console]::ForegroundColor
    if ($colors.ContainsKey($color)) {
        [System.Console]::ForegroundColor = $colors[$color]
        Write-Output $text
        #[System.Console]::ForegroundColor = $prevColor
        [System.Console]::ForegroundColor = $colors["default"]
    }
    else {
        Write-Output "Unknown color: $color. Available colors are: $($colors.Keys -join ', ')"
    }
}

# initialize the env file with the default values if there is no env file already present
# Check if the ${ENV_FILENAME} file is already present in the current directory, if it is not present copy from the .env.template file renaming it to ${ENV_FILENAME}, if it is present ask the user if they want to reset it or keep it as it is
if (-not (Test-Path .\${ENV_FILENAME})) {
    Write-Output "No ${ENV_FILENAME} file found, copying ${ENV_FILENAME} and ${DKCOM_FILENAME} from the template files"
    Copy-Item .\${ENV_TEMPLATE_FILENAME} .\${ENV_FILENAME} -Force
    Copy-Item .\${DKCOM_TEMPLATE_FILENAME} .\${DKCOM_FILENAME} -Force
    Write-Output "Copied ${ENV_FILENAME} and ${DKCOM_FILENAME} from the template files"
}
else {
    Write-Output "Already found ${ENV_FILENAME} file, proceeding with setup"
    # check if the release version in the local env fileis the same of the local template file , if not align it
    $LOCAL_SCRIPT_VERSION = (Get-Content .\${ENV_FILENAME} | Select-String -Pattern "PROJECT_VERSION=" -SimpleMatch).ToString().Split("=")[1]
    $LOCAL_SCRIPT_TEMPLATE_VERSION = (Get-Content .\${ENV_TEMPLATE_FILENAME} | Select-String -Pattern "PROJECT_VERSION=" -SimpleMatch).ToString().Split("=")[1]
    if ($LOCAL_SCRIPT_VERSION -ne $LOCAL_SCRIPT_TEMPLATE_VERSION) {
        Write-Output "Local ${ENV_FILENAME} file version differs from local ${ENV_TEMPLATE_FILENAME} file version"
        Write-Output "This could be the result of an updated project using an outdated ${ENV_FILENAME} file"
        Start-Sleep -Seconds $SLEEP_TIME
        Write-Output "Generating new ${ENV_FILENAME} and ${DKCOM_FILENAME} files from the local template files and backing up the old files as ${ENV_FILENAME}.bak and ${DKCOM_FILENAME}.bak"
        Copy-Item "${ENV_FILENAME}" "${ENV_FILENAME}.bak" -Force
        Copy-Item "${ENV_TEMPLATE_FILENAME}" "${ENV_FILENAME}" -Force
        Copy-Item "${DKCOM_FILENAME}" "${DKCOM_FILENAME}.bak" -Force
        Copy-Item "${DKCOM_TEMPLATE_FILENAME}" "${DKCOM_FILENAME}" -Force
        Write-Output "New local ${ENV_FILENAME} and ${DKCOM_FILENAME} files generated from the local template files"
        Write-Output "If you are unsure, download the latest version directly from GitHub."
        Start-Sleep -Seconds $SLEEP_TIME
        Read-Host -Prompt "Press Enter to continue"
    }
}

# Script version getting it from ${ENV_FILENAME} file#
$SCRIPT_VERSION = (Get-Content .\${ENV_FILENAME} | Select-String -Pattern "PROJECT_VERSION=" -SimpleMatch).ToString().Split("=")[1]

# Script name #
$SCRIPT_NAME = $MyInvocation.MyCommand.Name # save the script name in a variable, not the full path

# Project Discord URL #
$DS_PROJECT_SERVER_URL = (Get-Content .\${ENV_FILENAME} | Select-String -Pattern "DS_PROJECT_SERVER_URL=" -SimpleMatch).ToString().Split("=")[1]

# Script URL for update #
$PROJECT_BRANCH = "main"
$PROJECT_URL = "https://raw.githubusercontent.com/MRColorR/money4band/${PROJECT_BRANCH}"

# Script debug log file #
$DEBUG_LOG = "debug_$SCRIPT_NAME.log"

# Function to manage unexpected choices of flags #
function fn_unknown($REPLY) {
    colorprint "Red" "Unknown choice $REPLY, please choose a valid option"
}

# Function to exit the script gracefully #
function fn_bye {
    colorprint "Green" "Share this app with your friends thank you!"
    colorprint "Cyan" "Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!"
    print_and_log "Green" "Exiting the application...Bye!Bye!"
    exit 0
}

### Log, Update and Utility functions ###
# Function to write info/debug/warn/error messages to the log file if debug flag is true #
function toLog_ifDebug {
    param (
        [Parameter(Mandatory = $false)]
        [Alias('l')]
        [string]$log_level = "[DEBUG]",

        [Parameter(Mandatory = $true)]
        [Alias('m')]
        [string]$message
    )

    # Only log if DEBUG mode is enabled
    if ($script:DEBUG) {
        "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) - $log_level - $message" | Out-File -Append -FilePath $script:DEBUG_LOG
    }
}


## Enable or disable logging using debug mode ##
# Check if the first argument is -d or --debug if so, enable debug mode
if ($args[0] -eq '-d' -or $args[0] -eq '--debug') {
    $script:DEBUG = $true
    # shift the arguments array to remove the debug flag consumed
    $args = $args[1..$args.Length]
    toLog_ifDebug -l "[DEBUG]" -m "Debug mode enabled."
}
else {
    $script:DEBUG = $false
}

# Function to print an info message that will be also logged to the debug log file #
function print_and_log($color, $message) {
    colorprint $color $message
    toLog_ifDebug -l "[INFO]" -m "$message"
}

# Function to print an error message and write it to the debug log file #
function errorprint_and_log($text) {
    Write-Error $text
    toLog_ifDebug -l "[ERROR]" -m "$text"
}

# Function to print criticals errors that will stop the script execution, write them to the debug log file and exit the script with code 1 #
function fn_fail($text) {
    errorprint_and_log $text
    Read-Host -Prompt "Press Enter to exit..."
    exit 1
}

## Utility functions ##
# Function to check if the env file is already configured #
function Check-ConfigurationStatus {
    param (
        [string]$envFileArg
    )
    # Check if ${envFileArg} file is already configured
    $script:ENV_CONFIGURATION_STATUS = (Get-Content $envFileArg | Select-String -Pattern "ENV_CONFIGURATION_STATUS=" -SimpleMatch).ToString().Split("=")[1]
    toLog_ifDebug -l "[DEBUG]" -m "Current ENV_CONFIGURATION_STATUS: $ENV_CONFIGURATION_STATUS"

    $script:PROXY_CONFIGURATION_STATUS = (Get-Content $envFileArg | Select-String -Pattern "PROXY_CONFIGURATION_STATUS=" -SimpleMatch).ToString().Split("=")[1]
    toLog_ifDebug -l "[DEBUG]" -m "Current PROXY_CONFIGURATION_STATUS: $PROXY_CONFIGURATION_STATUS"

    $script:NOTIFICATIONS_CONFIGURATION_STATUS = (Get-Content $envFileArg | Select-String -Pattern "NOTIFICATIONS_CONFIGURATION_STATUS=" -SimpleMatch).ToString().Split("=")[1]
    toLog_ifDebug -l "[DEBUG]" -m "Current NOTIFICATIONS_CONFIGURATION_STATUS: $NOTIFICATIONS_CONFIGURATION_STATUS"
}

# Function to round up to the nearest power of 2
function RoundUpPowerOf2 {
    param([float]$value)
    $value = ($value)  # Convert to an integer by rounding
    $i = 1
    while ($i -lt $value) {
        $i = $i * 2
    }
    return $i
}

function adaptLimits {
    # Define minimum values for CPU and RAM limits
    $MIN_CPU_LIMIT = 0.2 # Minimum CPU limit (reasonable value)
    $MIN_MEM_LIMIT = 6 # Minimum RAM limit is 6 MB (enforced by Docker)
    $COMPUTER_INFO = Get-CimInstance -ClassName Win32_ComputerSystem
    
    # Get the number of CPU cores the machine has and others CPU related info
    # $CPU_INFO = Get-CimInstance -ClassName Win32_Processor
    # $CPU_SOCKETS = $COMPUTER_INFO.NumberOfProcessors
    # #$CPU_SOCKETS = '-'  # Uncomment to simulate incorrect socket number reporting
    # if (-not [int]::TryParse($CPU_SOCKETS, [ref]$null)) {
    #     $CPU_SOCKETS = 1  # Default to 1 if CPU_SOCKETS is not a number
    # }
    # $CPU_CORES = $CPU_INFO.NumberOfCores
    # $TOTAL_CPUS_OLD = $CPU_CORES * $CPU_SOCKETS # commented ot as the absh equivalent calculations were not working on some systems as sockets or cpus per socket are not reported correctly
    $TOTAL_CPUS = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum

    # Adapt the limits in .env file for CPU and RAM taking into account the number of CPU cores the machine has and the amount of RAM the machine has
    # CPU limits: little should use max 25% of the CPU power , medium should use max 50% of the CPU power , big should use max 75% of the CPU power , huge should use max 100% of the CPU power
    $appCpuLimitLittle = ($TOTAL_CPUS * 25 / 100)
    $appCpuLimitMedium = ($TOTAL_CPUS * 50 / 100)
    $appCpuLimitBig = ($TOTAL_CPUS * 75 / 100)
    $appCpuLimitHuge = ($TOTAL_CPUS * 100 / 100)

    # Ensure CPU limits are not below minimum
    $appCpuLimitLittle = [math]::Max($appCpuLimitLittle, $MIN_CPU_LIMIT)
    $appCpuLimitMedium = [math]::Max($appCpuLimitMedium, $MIN_CPU_LIMIT)
    $appCpuLimitBig = [math]::Max($appCpuLimitBig, $MIN_CPU_LIMIT)
    $appCpuLimitHuge = [math]::Max($appCpuLimitHuge, $MIN_CPU_LIMIT)
    
    # Get the total RAM of the machine in MB
    $totalRamBytes = $COMPUTER_INFO | Select-Object -ExpandProperty TotalPhysicalMemory
    $totalRamMb = ($totalRamBytes / 1024)

    # Load current limits from .env file
    $envContent = Get-Content -Path $ENV_FILENAME
    $currentAppCpuLimitLittle = ($envContent | Where-Object { $_ -match 'APP_CPU_LIMIT_LITTLE=(.*)' }) -replace 'APP_CPU_LIMIT_LITTLE=', ''
    $currentAppCpuLimitMedium = ($envContent | Where-Object { $_ -match 'APP_CPU_LIMIT_MEDIUM=(.*)' }) -replace 'APP_CPU_LIMIT_MEDIUM=', ''
    $currentAppCpuLmitBig = ($envContent | Where-Object { $_ -match 'APP_CPU_LIMIT_BIG=(.*)' }) -replace 'APP_CPU_LIMIT_BIG=', ''
    $currentAppCpuLimitHuge = ($envContent | Where-Object { $_ -match 'APP_CPU_LIMIT_HUGE=(.*)' }) -replace 'APP_CPU_LIMIT_HUGE=', ''
    $currentAppMemReservLittle = ($envContent | Where-Object { $_ -match 'APP_MEM_RESERV_LITTLE=(.*)' }) -replace 'APP_MEM_RESERV_LITTLE=', ''
    $currentAppMemLimitLittle = ($envContent | Where-Object { $_ -match 'APP_MEM_LIMIT_LITTLE=(.*)' }) -replace 'APP_MEM_LIMIT_LITTLE=', ''
    $currentAppMemReservMedium = ($envContent | Where-Object { $_ -match 'APP_MEM_RESERV_MEDIUM=(.*)' }) -replace 'APP_MEM_RESERV_MEDIUM=', ''
    $currentAppMemLimitMedium = ($envContent | Where-Object { $_ -match 'APP_MEM_LIMIT_MEDIUM=(.*)' }) -replace 'APP_MEM_LIMIT_MEDIUM=', ''
    $currentAppMemReservBig = ($envContent | Where-Object { $_ -match 'APP_MEM_RESERV_BIG=(.*)' }) -replace 'APP_MEM_RESERV_BIG=', ''
    $currentAppMemLimitBig = ($envContent | Where-Object { $_ -match 'APP_MEM_LIMIT_BIG=(.*)' }) -replace 'APP_MEM_LIMIT_BIG=', ''
    $currentAppMemReservHuge = ($envContent | Where-Object { $_ -match 'APP_MEM_RESERV_HUGE=(.*)' }) -replace 'APP_MEM_RESERV_HUGE=', ''
    $currentAppMemLimitHuge = ($envContent | Where-Object { $_ -match 'APP_MEM_LIMIT_HUGE=(.*)' }) -replace 'APP_MEM_LIMIT_HUGE=', ''

    # RAM limits: little should reserve at least MIN_RAM_LIMIT MB or the next near power of 2 in MB of 5% of RAM as upperbound and use as max limit the 250% of this value, medium should reserve double of the little value or the next near power of 2 in MB of 10% of RAM as upperbound and use as max limit the 250% of this value, big should reserve double of the medium value or the next near power of 2 in MB of 20% of RAM as upperbound and use as max limit the 250% of this value, huge should reserve double of the big value or the next near power of 2 in MB of 40% of RAM as upperbound and use as max limit the 400% of this value
    # Implementing a cap for high RAM devices reading value from .env.template file it will be like RAM_CAP_MB_DEFAULT=6144m we need the value 6144
    $ramCapMbDefault = (Get-Content $ENV_TEMPLATE_FILENAME | Where-Object { $_ -match 'RAM_CAP_MB_DEFAULT=(.*)' }) -replace 'RAM_CAP_MB_DEFAULT=', '' -replace 'm', ''
    # Uncomment the following to simulate a specific amount of RAM for the device
    # $totalRamMb = 1024
    $ramCapMb = If ($totalRamMb -gt $ramCapMbDefault) { $ramCapMbDefault } else { $totalRamMb }
    $maxUseRamMb = [math]::Min($totalRamMb, $ramCapMb)

    # Calculate new RAM limits
    $appMemReservLittle = RoundUpPowerOf2 (($maxUseRamMb * 5 / 100))
    $appMemLimitLittle = RoundUpPowerOf2 (($appMemReservLittle * 200 / 100))
    $appMemReservMedium = RoundUpPowerOf2 (($maxUseRamMb * 10 / 100))
    $appMemLimitMedium = RoundUpPowerOf2 (($appMemReservMedium * 200 / 100))
    $appMemReservBig = RoundUpPowerOf2 (($maxUseRamMb * 20 / 100))
    $appMemLimitBig = RoundUpPowerOf2 (($appMemReservBig * 200 / 100))
    $appMemReservHuge = RoundUpPowerOf2 (($maxUseRamMb * 40 / 100))
    $appMemLimitHuge = RoundUpPowerOf2 (($appMemReservHuge * 200 / 100))

    # Ensure the calculated values do not exceed RAM_CAP_MB_DEFAULT
    $appMemReservLittle = [math]::Min($appMemReservLittle, $ramCapMbDefault)
    $appMemLimitLittle = [math]::Min($appMemLimitLittle, $ramCapMbDefault)
    $appMemReservMedium = [math]::Min($appMemReservMedium, $ramCapMbDefault)
    $appMemLimitMedium = [math]::Min($appMemLimitMedium, $ramCapMbDefault)
    $appMemReservBig = [math]::Min($appMemReservBig, $ramCapMbDefault)
    $appMemLimitBig = [math]::Min($appMemLimitBig, $ramCapMbDefault)
    $appMemReservHuge = [math]::Min($appMemReservHuge, $ramCapMbDefault)
    $appMemLimitHuge = [math]::Min($appMemLimitHuge, $ramCapMbDefault)

    # Ensure RAM limits are not below minimum
    $appMemReservLittle = [math]::Max($appMemReservLittle, $MIN_MEM_LIMIT)
    $appMemLimitLittle = [math]::Max($appMemLimitLittle, $MIN_MEM_LIMIT)
    $appMemReservMedium = [math]::Max($appMemReservMedium, $MIN_MEM_LIMIT)
    $appMemLimitMedium = [math]::Max($appMemLimitMedium, $MIN_MEM_LIMIT)
    $appMemReservBig = [math]::Max($appMemReservBig, $MIN_MEM_LIMIT)
    $appMemLimitBig = [math]::Max($appMemLimitBig, $MIN_MEM_LIMIT)
    $appMemReservHuge = [math]::Max($appMemReservHuge, $MIN_MEM_LIMIT)
    $appMemLimitHuge = [math]::Max($appMemLimitHuge, $MIN_MEM_LIMIT)
    
    # Update the CPU limits with the new values
    (Get-Content $ENV_FILENAME).Replace("APP_CPU_LIMIT_LITTLE=$currentAppCpuLimitLittle", "APP_CPU_LIMIT_LITTLE=$appCpuLimitLittle") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_CPU_LIMIT_MEDIUM=$currentAppCpuLimitMedium", "APP_CPU_LIMIT_MEDIUM=$appCpuLimitMedium") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_CPU_LIMIT_BIG=$currentAppCpuLmitBig", "APP_CPU_LIMIT_BIG=$appCpuLimitBig") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_CPU_LIMIT_HUGE=$currentAppCpuLimitHuge", "APP_CPU_LIMIT_HUGE=$appCpuLimitHuge") | Set-Content $ENV_FILENAME
    # Update RAM limits with the new values unsing as unit MB
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_RESERV_LITTLE=$currentAppMemReservLittle", "APP_MEM_RESERV_LITTLE=${appMemReservLittle}m") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_LIMIT_LITTLE=$currentAppMemLimitLittle", "APP_MEM_LIMIT_LITTLE=${appMemLimitLittle}m") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_RESERV_MEDIUM=$currentAppMemReservMedium", "APP_MEM_RESERV_MEDIUM=${appMemReservMedium}m") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_LIMIT_MEDIUM=$currentAppMemLimitMedium", "APP_MEM_LIMIT_MEDIUM=${appMemLimitMedium}m") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_RESERV_BIG=$currentAppMemReservBig", "APP_MEM_RESERV_BIG=${appMemReservBig}m") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_LIMIT_BIG=$currentAppMemLimitBig", "APP_MEM_LIMIT_BIG=${appMemLimitBig}m") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_RESERV_HUGE=$currentAppMemReservHuge", "APP_MEM_RESERV_HUGE=${appMemReservHuge}m") | Set-Content $ENV_FILENAME
    (Get-Content $ENV_FILENAME).Replace("APP_MEM_LIMIT_HUGE=$currentAppMemLimitHuge", "APP_MEM_LIMIT_HUGE=${appMemLimitHuge}m") | Set-Content $ENV_FILENAME


    # If debug mode is enabled print the calculated limits values
    if ($Debug -eq $true) {
        print_and_log "DEFAULT" "Total CPUs: $TOTAL_CPUS"
        print_and_log "DEFAULT" "APP_CPU_LIMIT_LITTLE: $appCpuLimitLittle"
        print_and_log "DEFAULT" "APP_CPU_LIMIT_MEDIUM: $appCpuLimitMedium"
        print_and_log "DEFAULT" "APP_CPU_LIMIT_BIG: $appCpuLimitBig"
        print_and_log "DEFAULT" "APP_CPU_LIMIT_HUGE: $appCpuLimitHuge"
        print_and_log "DEFAULT" "APP_MEM_RESERV_LITTLE: $appMemReservLittle"
        print_and_log "DEFAULT" "APP_MEM_LIMIT_LITTLE: $appMemLimitLittle"
        print_and_log "DEFAULT" "APP_MEM_RESERV_MEDIUM: $appMemReservMedium"
        print_and_log "DEFAULT" "APP_MEM_LIMIT_MEDIUM: $appMemLimitMedium"
        print_and_log "DEFAULT" "APP_MEM_RESERV_BIG: $appMemReservBig"
        print_and_log "DEFAULT" "APP_MEM_LIMIT_BIG: $appMemLimitBig"
        print_and_log "DEFAULT" "APP_MEM_RESERV_HUGE: $appMemReservHuge"
        print_and_log "DEFAULT" "APP_MEM_LIMIT_HUGE: $appMemLimitHuge"
        #Read-Host -Prompt "Press Enter to continue"
    }
}

# Function to check if there are any updates available #
function check_project_updates {
    # Get the current script version from the local .env file
    $SCRIPT_VERSION_MATCH = (Get-Content .\$ENV_FILENAME | Select-String -Pattern "PROJECT_VERSION=(\d+\.\d+\.\d+)").Matches
    if ($SCRIPT_VERSION_MATCH.Count -eq 0) {
        errorprint_and_log "Failed to get the script version from the local .env file."
        return
    }
    $SCRIPT_VERSION = $SCRIPT_VERSION_MATCH[0].Groups[1].Value

    # Get the latest script version from the .env.template file on GitHub
    try {
        $webClient = New-Object System.Net.WebClient
        $templateContent = $webClient.DownloadString("$PROJECT_URL/$ENV_TEMPLATE_FILENAME")
        $LATEST_SCRIPT_VERSION_MATCH = ($templateContent | Select-String -Pattern "PROJECT_VERSION=(\d+\.\d+\.\d+)").Matches
        if ($LATEST_SCRIPT_VERSION_MATCH.Count -eq 0) {
            errorprint_and_log "Failed to get the latest script version from GitHub."
            return
        }
        $LATEST_SCRIPT_VERSION = $LATEST_SCRIPT_VERSION_MATCH[0].Groups[1].Value
    } catch {
        print_and_log "Blue" "Updates check failed. Will try again later. Reason: $_"
        return
    }

    # Split the versions into major, minor, and patch numbers
    $SCRIPT_VERSION_SPLIT = $SCRIPT_VERSION.Split(".")
    $LATEST_SCRIPT_VERSION_SPLIT = $LATEST_SCRIPT_VERSION.Split(".")

    # Compare the versions and print a message if a newer version is available
    for ($i=0; $i -lt 3; $i++) {
        if ([int]$SCRIPT_VERSION_SPLIT[$i] -lt [int]$LATEST_SCRIPT_VERSION_SPLIT[$i]) {
            print_and_log "Yellow" "A newer version of the script is available. Please consider updating."
            return
        }
        elseif ([int]$SCRIPT_VERSION_SPLIT[$i] -gt [int]$LATEST_SCRIPT_VERSION_SPLIT[$i]) {
            return
        }
    }

    # If the loop completes without finding a newer version, print a message indicating that the script is up to date
    print_and_log "BLUE" "Script is up to date."
}

# Function to detect OS
function detect_os {
    toLog_ifDebug -l "[DEBUG]" -m "Detecting OS..."
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
        $script:OS_TYPE = $os_map.Keys | Where-Object { $OSStr.Contains($_) } | Select-Object -First 1 | ForEach-Object { $os_map[$_] }
    }
    catch {
        toLog_ifDebug -l "[WARN]" -m "Neither PS OS detection commands nor uname were found, OS detection failed. OS type will be set to 'unknown'."
        $script:OS_TYPE = 'unknown'        
    }
    toLog_ifDebug -l "[DEBUG]" -m "OS type detected: $script:OS_TYPE"
}

# Function to detect OS architecture and set the relative Docker architecture
function detect_architecture {
    toLog_ifDebug -l "[DEBUG]" -m "Detecting system architecture..."
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
        toLog_ifDebug -l "[DEBUG]" -m "Neither PS arch detection commands nor uname were found, architecture detection failed. Architecture will be set to 'unknown'."
        $script:ARCH = 'unknown'
        $script:DKARCH = 'unknown'
    }

    toLog_ifDebug -l "[DEBUG]" -m "System architecture detected: $script:ARCH, Docker architecture has been set to $script:DKARCH"
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
        toLog_ifDebug -l "[DEBUG]" -m "Package manager detected: $PKG_MANAGER"
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
    toLog_ifDebug -l "[DEBUG]" -m "Required packages installation completed."
}

### Sub-menu Functions ###
# Shows the liks of the apps
function fn_showLinks {
    Clear-Host
    toLog_ifDebug -l "[DEBUG]" -m "Showing apps links"
    colorprint "Green" "Use CTRL+Click to open links or copy them:"
    $configPath = Join-Path -Path $CONFIG_DIR -ChildPath $APP_CONFIG_JSON_FILE
    $configData = Get-Content -Path $configPath -Raw | ConvertFrom-Json
    # Iterate over the top-level keys (app types) in the JSON
    foreach ($appType in $configData.PSObject.Properties.Name) {
        colorprint "Yellow" "---$appType---"
        # Iterate over the apps in each type
        foreach ($app in $configData.$appType) {
            colorprint "Default" $app.name
            colorprint "Cyan" $app.link
        }
    }
    Read-Host -Prompt "Press Enter to go back to mainmenu"
    toLog_ifDebug -l "[DEBUG]" -m "Links shown, going back to main menu."
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
    toLog_ifDebug -l "[DEBUG]" -m "DockerInstall function started"
    colorprint "Yellow" "This menu item will launch a script that will attempt to install Docker"
    colorprint "Yellow" "Use it only if you do not know how to perform the manual Docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some cases and depending on the OS you are using may fail to install Docker correctly."
    
    while ($true) {
        $yn = (Read-Host -Prompt "Do you wish to proceed with the Docker automatic installation Y/N?").ToLower()
        if ($yn -eq 'y' -or $yn -eq 'yes') {
            toLog_ifDebug -l "[DEBUG]" -m "User decided to install Docker through the script. Checking if Docker is already installed."
            try {
                $dockerVersion = docker --version
                if ($dockerVersion) {
                    toLog_ifDebug -l "[DEBUG]" -m "Docker is already installed. Asking user if he wants to continue with the installation anyway."
                    while ($true) {
                        colorprint "Yellow" "Docker seems to be installed already. Do you want to continue with the installation anyway? (Y/N)"
                        $yn = (Read-Host).ToLower()
                        if ($yn -eq 'n' -or $yn -eq 'no') {
                            toLog_ifDebug -l "[DEBUG]" -m "User decided to abort the Docker re-install."
                            colorprint "Blue" "Returning to main menu..."
                            Start-Sleep -Seconds $SLEEP_TIME
                            return
                        }
                        elseif ($yn -eq 'y' -or $yn -eq 'yes' ) {
                            toLog_ifDebug -l "[DEBUG]" -m "User decided to continue with the Docker re-install anyway."
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
            print_and_log "Yellow" "Installing Docker for $script:OS_TYPE."
            $InstallStatus = $false;
            
            Switch ($script:OS_TYPE) {
                "Linux" {
                    Clear-Host
                    print_and_log "Yellow" "Starting Docker for Linux auto installation script"
                    $ProgressPreference = 'SilentlyContinue'
                    Invoke-WebRequest https://get.docker.com -o "$SCRIPTS_DIR/get-docker.sh"
                    $ProgressPreference = 'Continue'
                    sudo sh get-docker.sh;
                    $InstallStatus = $true;
                }
                "Windows" {
                    Clear-Host
                    print_and_log "Yellow" "Starting Docker for Windows auto installation script"
                    $ProgressPreference = 'SilentlyContinue'
                    Invoke-WebRequest $DKINST_WIN_SRC -o "$SCRIPTS_DIR\install-docker-win.ps1"
                    $ProgressPreference = 'Continue'
                    Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -command `"$SCRIPTS_DIR\install-docker-win.ps1 -filesPath $FILES_DIR`"" -Wait
                    $InstallStatus = $true;              
                }
                "MacOS" {
                    Clear-Host
                    print_and_log "Yellow" "Starting Docker for MacOS auto installation script"  
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
                    print_and_log "Red" "Your operating system (${OSTYPE}) has not been recognized or is not supported by this function. Please install Docker manually and then try again."
                }
            }
            if ($InstallStatus) {
                colorprint "Green" "Script completed. If no errors appeared Docker should be installed. Please restart your machine and then proceed to ${ENV_FILENAME} file config and stack startup."
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
This function will setup notifications about containers updates using shoutrrr. It will ask the user to enter a link for notifications and then it will update the ${ENV_FILENAME} file and the docker-compose.yaml file accordingly.

.EXAMPLE
Just call fn_setupNotifications

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupNotifications {
    toLog_ifDebug -l "[DEBUG]" -m "SetupNotifications function started"
    Clear-Host
    while ($true) {      
        colorprint "Yellow" "Do you wish to setup notifications about apps images updates (Yes to receive notifications and apply updates, No to just silently apply updates) Y/N?"
        $yn = Read-Host
        $yn = $yn.ToLower()
        if ($yn -eq 'y' -or $yn -eq 'yes') {
            toLog_ifDebug -l "[DEBUG]" -m "User decided to setup notifications about apps images updates."
            colorprint "Yellow" "This step will setup notifications about containers updates using shoutrrr"
            colorprint "Default" "The resulting SHOUTRRR_URL should have the format: <app>://<token>@<webhook>."
            colorprint "Default" "Where <app> is one of the supported messaging apps on Shoutrrr (e.g. Discord), and <token> and <webhook> are specific to your messaging app."
            colorprint "Default" "To obtain the SHOUTRRR_URL, create a new webhook for your messaging app and rearrange its URL to match the format above."
            colorprint "Default" "For more details, visit https://containrrr.dev/shoutrrr/ and select your messaging app."
            colorprint "Default" "Now a Discord notification setup example will be shown (Remember: you can also use a different supported app)."
            Read-Host -Prompt "Press enter to continue"
            Clear-Host
            colorprint "magenta" "Create a new Discord server, go to server settings > integrations, and create a webhook."
            colorprint "magenta" "Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken."
            colorprint "magenta" "To obtain the SHOUTRRR_URL, rearrange it to look like this: discord://YourToken@YourWebhookid."
            Read-Host -Prompt "Press enter to proceed with the setup"
            Clear-Host
            while ($true) {
                colorprint "Yellow" "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"
                $SHOUTRRR_URL = Read-Host
                if ($SHOUTRRR_URL -match '^[a-zA-Z]+://') {
                    # Replace the lines in ${ENV_FILENAME} and $DKCOM_FILENAME
                    (Get-Content .\${ENV_FILENAME}).replace('# SHOUTRRR_URL=', "SHOUTRRR_URL=") | Set-Content .\${ENV_FILENAME}
                    $CURRENT_VALUE = (Get-Content .\${ENV_FILENAME} | Select-String -Pattern "SHOUTRRR_URL=" -SimpleMatch).ToString().Split("=")[1]
                    (Get-Content .\${ENV_FILENAME}).replace("SHOUTRRR_URL=${CURRENT_VALUE}", "SHOUTRRR_URL=${SHOUTRRR_URL}") | Set-Content .\${ENV_FILENAME}
                    (Get-Content .\$DKCOM_FILENAME).replace('# - WATCHTOWER_NOTIFICATIONS=shoutrrr', "- WATCHTOWER_NOTIFICATIONS=shoutrrr") | Set-Content .\$DKCOM_FILENAME
                    (Get-Content .\$DKCOM_FILENAME).replace('# - WATCHTOWER_NOTIFICATION_URL', "- WATCHTOWER_NOTIFICATION_URL") | Set-Content .\$DKCOM_FILENAME
                    (Get-Content .\$DKCOM_FILENAME).replace('# - WATCHTOWER_NOTIFICATIONS_HOSTNAME', "- WATCHTOWER_NOTIFICATIONS_HOSTNAME") | Set-Content .\$DKCOM_FILENAME
                    (Get-Content .\${ENV_FILENAME}).replace("NOTIFICATIONS_CONFIGURATION_STATUS=0", "NOTIFICATIONS_CONFIGURATION_STATUS=1") | Set-Content .\${ENV_FILENAME}
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
                            toLog_ifDebug -l "[DEBUG]" -m "User choose to not retry the notifications setup. Notifications wsetup will now return"
                            colorprint "Blue" "Noted: all updates will be applied automatically and silently"
                            Start-Sleep -Seconds $SLEEP_TIME
                            return
                        }
                        else {
                            colorprint "Red" "Please answer yes or no."
                        }
                    }
                }
            }
            break
        }
        elseif ($yn -eq 'n' -or $yn -eq 'no') {
            toLog_ifDebug -l "[DEBUG]" -m "User choose to skip notifications setup"
            colorprint "Blue" "Noted: all updates will be applied automatically and silently"
            Start-Sleep -Seconds $SLEEP_TIME
            break
        }
        else {
            colorprint "Red" "Please answer yes or no."
        }
    }
    Clear-Host
    toLog_ifDebug -l "[DEBUG]" -m "Notifications setup ended."
}


<#
.SYNOPSIS
This function will manage the setup of each app in the stack

.DESCRIPTION
This function will manage the setup of each app in the stack. It will ask the user to enter the required data for each app and then it will update the ${ENV_FILENAME} file and the docker-compose.yaml file accordingly.

.PARAMETER app
App name and image are required parameters. The app name is used to identify the app in the setup process.

.PARAMETER image
the image is used to feryfy if the image supports the current architecture and to update the docker-compose.yaml file accordingly.

.PARAMETER flags
Optional parameter. If the app requires an email to be setup, this parameter will be used to update the ${ENV_FILENAME} file.

.EXAMPLE
fn_setupApp -app "HONEYGAIN" -image "honeygain/honeygain" -email "email" -password "password"

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupApp() {
    param(
        [Parameter(Mandatory = $true)]
        [string]$app_json,

        [Parameter(Mandatory = $false)]
        [string]$dk_compose_filename = "docker-compose.yaml"
    )
    toLog_ifDebug -l "[DEBUG]" -m "SetupApp function started"
    toLog_ifDebug -l "[DEBUG]" -m "SetupApp function parameters: app_json=$app_json, dk_compose_filename=$dk_compose_filename"
    
    $app_json_obj = $app_json | ConvertFrom-Json
    $name = $app_json_obj.name
    $link = $app_json_obj.link
    $app_image = $app_json_obj.image
    $flags_raw = $app_json_obj.flags.PSObject.Properties.Name
    $flags = @()
    foreach ($flag in $flags_raw) {
        $flags += $flag
    }
    $claimURLBase = if ($app_json_obj.claimURLBase) { $app_json_obj.claimURLBase } else { $link }
    $CURRENT_APP = $name.ToUpper()
    while ($true) {
        # Check if the ${CURRENT_APP} is already enabled in the ${dk_compose_filename} file and if it is not (if there is a #ENABLE_$CURRENTAPP) then ask the user if they want to enable it
        toLog_ifDebug -l "[DEBUG]" -m "Checking if the ${CURRENT_APP} app is already enabled in the ${dk_compose_filename} file"
        if ((Get-content $dk_compose_filename) -match "#ENABLE_${CURRENT_APP}") {
            toLog_ifDebug -l "[DEBUG]" -m "The ${CURRENT_APP} app is not enabled in the ${dk_compose_filename} file, asking user if they want to enable it"
            # Show the generic message before asking the user if they want to enable the app
            colorprint "YELLOW" "PLEASE REGISTER ON THE PLATFORMS USING THE LINKS THAT WILL BE PROVIDED, YOU'LL THEN NEED TO ENTER SOME DATA BELOW:"
            # Ask the user if they want to enable the ${CURRENT_APP}
            colorprint "Yellow" "Do you wish to enable the ${CURRENT_APP} app? (Y/N)"
            $yn = Read-Host
            $yn = $yn.ToLower()
            if ($yn -eq 'y' -or $yn -eq 'yes') {
                toLog_ifDebug -l "[DEBUG]" -m "User decided to enable the ${CURRENT_APP} app"
                colorprint "Cyan" "Go to ${CURRENT_APP} ${link} and register"
                colorprint "Green" "Use CTRL+Click to open links or copy them:"
                Read-Host -Prompt "When you are done press Enter to continue"
                toLog_ifDebug -l "[DEBUG]" -m "Enabling ${CURRENT_APP} app. The parameters received are: name=$name, link=$link, image=$app_image, flags=$flags, claimURLBase=$claimURLBase"
                # Read the flags in the array and execute the relative logic using the case statement
                foreach ($flag_name in $flags) {
                    #$flag_details = ($app_json_obj.flags | Get-Member -MemberType NoteProperty | Where-Object { $_.Name -eq $flag_name }).Value
                    $flag_details = $app_json_obj.flags.$flag_name
                    toLog_ifDebug -l "[DEBUG]" -m "Result of flag_details reading: $flag_details"
                    if ($null -ne $flag_details) {
                        $flag_params_keys = $flag_details.PSObject.Properties.Name
                        toLog_ifDebug -l "[DEBUG]" -m "Result of flag_params_keys reading: $flag_params_keys"
                    }
                    else {
                        toLog_ifDebug -l "[DEBUG]" -m "No flag details found for flag: $flag_name"
                    }
                    switch ($flag_name) {
                        "--email" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting email setup for ${CURRENT_APP} app"
                            while ($true) {
                                colorprint "GREEN" "Enter your ${CURRENT_APP} Email:"
                                $APP_EMAIL = Read-Host
                                if ($APP_EMAIL -match '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-zA-Z]{2,}$') {
                                    (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}Mail", $APP_EMAIL | Set-Content ${ENV_FILENAME}
                                    break
                                }
                                else {
                                    colorprint "RED" "Invalid email address. Please try again."
                                }
                            }
                        }
                        "--password" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting password setup for ${CURRENT_APP} app"
                            while ($true) {
                                colorprint "DEFAULT" "Note: If you are using login with Google, remember to set also a password for your ${CURRENT_APP} account!"
                                colorprint "GREEN" "Enter your ${CURRENT_APP} Password:"
                                $APP_PASSWORD = Read-Host
                                if ($APP_PASSWORD) {
                                    (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}Pw", $APP_PASSWORD | Set-Content ${ENV_FILENAME}
                                    break
                                }
                                else {
                                    colorprint "RED" "Password cannot be empty. Please try again."
                                }
                            }
                        }
                        "--apikey" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting APIKey setup for ${CURRENT_APP} app"
                            while ($true) {
                                colorprint "DEFAULT" "Find/Generate your APIKey inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "GREEN" "Enter your ${CURRENT_APP} APIKey:"
                                $APP_APIKEY = Read-Host
                                if ($APP_APIKEY) {
                                    (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}APIKey", $APP_APIKEY | Set-Content ${ENV_FILENAME}
                                    break
                                }
                                else {
                                    colorprint "RED" "APIKey cannot be empty. Please try again."
                                }
                            }
                        }
                        "--userid" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting UserID setup for ${CURRENT_APP} app"
                            while ($true) {
                                colorprint "DEFAULT" "Find your UserID inside your ${CURRENT_APP} dashboard/profile."
                                colorprint "GREEN" "Enter your ${CURRENT_APP} UserID:"
                                $APP_USERID = Read-Host
                                if ($APP_USERID) {
                                    (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}UserID", $APP_USERID | Set-Content ${ENV_FILENAME}
                                    break
                                }
                                else {
                                    colorprint "RED" "UserID cannot be empty. Please try again."
                                }
                            }
                        }
                        "--uuid" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting UUID setup for ${CURRENT_APP} app"
                            colorprint "DEFAULT" "Starting UUID generation/import for ${CURRENT_APP}"
                            # Read all the parameters for the uuid flag , if one of them is the case length then save it in a variable
                            if ($null -ne $flag_params_keys) {
                                foreach ($flag_param_key in $flag_params_keys) {
                                    toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter: $flag_param_key"
                                    switch ($flag_param_key) {
                                        'length' {
                                            toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter length"
                                            $flag_length_param = $app_json_obj.flags.$flag_name.$flag_param_key
                                            toLog_ifDebug -l "[DEBUG]" -m "Result of flag_length_param reading: $flag_length_param"
                                        }
                                        default {
                                            toLog_ifDebug -l "[DEBUG]" -m "Unknown flag parameter: $flag_param_key"
                                        }
                                    }
                                }
                            }
                            else {
                                toLog_ifDebug -l "[DEBUG]" -m "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                            }
                            # Check if the flag_length_param exists and if is a number (i.e., the desired length)
                            if (($null -ne $flag_length_param) -and ($flag_length_param -match "^\d+$")) {
                                $DESIRED_LENGTH = $flag_length_param
                                toLog_ifDebug -l "[DEBUG]" -m "Desired length for UUID generation/import passed as argument of the uuid flag (read from json), its value is: $DESIRED_LENGTH"
                            }
                            else {
                                # If no length is provided, ask the user
                                toLog_ifDebug -l "[DEBUG]" -m "No desired length for UUID generation/import passed as argument of the uuid flag, asking the user"
                                colorprint "GREEN" "Enter desired length for the UUID (default is 32, press Enter to use default):"
                                $DESIRED_LENGTH_INPUT = Read-Host
                                $DESIRED_LENGTH = if ($DESIRED_LENGTH_INPUT) { $DESIRED_LENGTH_INPUT } else { 32 } # Defaulting to 32 if no input provided
                            }
                        
                            toLog_ifDebug -l "[DEBUG]" -m "Starting temporary UUID generation/import for ${CURRENT_APP} with desired length: $DESIRED_LENGTH. This will be overwritten if the user chooses to use an existing UUID."
                            $UUID = ""
                            while ($UUID.Length -lt $DESIRED_LENGTH) {
                                # Regenerate the salt for each iteration
                                $SALT = "${DEVICE_NAME}${Get-Random}${UUID}" # Incorporate the previously generated UUID part for added randomness
                                $UUID_PART = [System.BitConverter]::ToString([System.Security.Cryptography.MD5]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($SALT))).Replace("-", "").Substring(0, 32).ToLower()
                                $UUID += $UUID_PART
                            }
                            # Cut or trail the generated UUID based on the desired length
                            $UUID = $UUID.Substring(0, $DESIRED_LENGTH)
                            toLog_ifDebug -l "[DEBUG]" -m "Done, generated temporary UUID: $UUID"
                            while ($true) {
                                colorprint "YELLOW" "Do you want to use a previously registered uuid for ${CURRENT_APP}? (Y/N)"
                                $USE_EXISTING_UUID = Read-Host
                                if ($USE_EXISTING_UUID -match "^[Yy].*") {
                                    while ($true) {
                                        colorprint "GREEN" "Please enter the alphanumeric part of the existing uuid for ${CURRENT_APP}, it should be $DESIRED_LENGTH characters long."
                                        colorprint "DEFAULT" "E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4"
                                        $EXISTING_UUID = Read-Host
                            
                                        if (-not ($EXISTING_UUID -match "^[a-f0-9]{$DESIRED_LENGTH}$")) {
                                            colorprint "RED" "Invalid UUID entered, it should be an alphanumeric string and $DESIRED_LENGTH characters long."
                                            colorprint "DEFAULT" "Do you want to try again? (Y/N)"
                                            $TRY_AGAIN = Read-Host
                            
                                            if ($TRY_AGAIN -match "^[Nn].*") {
                                                break
                                            }
                                            elseif ($TRY_AGAIN -match "^[Yy].*") {
                                                continue
                                            }
                                            else {
                                                colorprint "RED" "Please answer yes or no."
                                            }
                                        }
                                        else {
                                            $UUID = $EXISTING_UUID
                                            print_and_log "DEFAULT" "Using user provided existing UUID: $UUID"
                                            break
                                        }
                                    }
                                    break
                                }
                                elseif ($USE_EXISTING_UUID -match "^[Nn].*") {
                                    break
                                }
                                else {
                                    colorprint "RED" "Please answer yes or no."
                                }
                            }
                        
                            (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}DeviceUUID", $UUID | Set-Content ${ENV_FILENAME}
                            colorprint "DEFAULT" "${CURRENT_APP} UUID setup: done"
                            # Generaing the claim link
                            $claimlink = "${claimURLBase}${UUID}"
                            colorprint "BLUE" "Save the following link somewhere to claim/register your ${CURRENT_APP} node/device after completing the setup and starting the apps stack: ${claimlink}"
                            $claimlink | Out-File -Append "claim${CURRENT_APP}NodeDevice.txt"
                            colorprint "DEFAULT" "A new file containing this link has been created for you in the current directory"
                        }
                        "--cid" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting CID setup for ${CURRENT_APP} app"
                            colorprint "Default" "Find your CID inside your ${CURRENT_APP} dashboard/profile."
                            colorprint "Default" "Example: For packetstream you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
                            colorprint "Green" "Enter your ${CURRENT_APP} CID:"
                            $APP_CID = Read-Host
                            if ($APP_CID) {
                                (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}CID", $APP_CID | Set-Content ${ENV_FILENAME}
                            }
                            else {
                                colorprint "Red" "CID cannot be empty. Please try again."
                            }
                        }
                        "--code" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting auth code setup for ${CURRENT_APP} app"
                            colorprint "Default" "Find your auth code inside your ${CURRENT_APP} dashboard/profile."
                            colorprint "Green" "Enter your ${CURRENT_APP} auth code:"
                            $APP_CODE = Read-Host
                            if ($APP_CODE) {
                                (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}Code", $APP_CODE | Set-Content ${ENV_FILENAME}
                            }
                            else {
                                colorprint "Red" "Code cannot be empty. Please try again."
                            }
                        }
                        "--token" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting token setup for ${CURRENT_APP} app"
                            colorprint "DEFAULT" "Find your token inside your ${CURRENT_APP} dashboard/profile."
                            colorprint "DEFAULT" "Example: For traffmonetizer you can fetch it from your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
                            colorprint "GREEN" "Enter your ${CURRENT_APP} token:"
                            $APP_TOKEN = Read-Host
                            if ($APP_TOKEN) {
                                (Get-Content ${ENV_FILENAME}) -replace "your${CURRENT_APP}Token", $APP_TOKEN | Set-Content ${ENV_FILENAME}
                            }
                            else {
                                colorprint "RED" "Token cannot be empty. Please try again."
                            }                                
                        }
                        "--customScript" {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting customScript setup for ${CURRENT_APP} app"
                            # Read all the parameters for the customScript flag , if one of them is the case scriptname then save it in a variable
                            if ($null -ne $flag_params_keys) {
                                foreach ($flag_param_key in $flag_params_keys) {
                                    toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter: $flag_param_key"
                                    switch ($flag_param_key) {
                                        'scriptname' {
                                            toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter scriptname"
                                            $flag_scriptname_param = $app_json_obj.flags.$flag_name.$flag_param_key
                                            toLog_ifDebug -l "[DEBUG]" -m "Result of flag_scriptname_param reading: $flag_scriptname_param"
                                        }
                                        default {
                                            toLog_ifDebug -l "[DEBUG]" -m "Unknown flag parameter: $flag_param_key"
                                        }
                                    }
                                }
                            }
                            else {
                                toLog_ifDebug -l "[DEBUG]" -m "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                            }
                            
                            $CUSTOM_SCRIPT_NAME = "${flag_scriptname_param}.ps1"
                            $SCRIPT_PATH = Join-Path $SCRIPTS_DIR $CUSTOM_SCRIPT_NAME
                            toLog_ifDebug -l "[DEBUG]" -m "Starting custom script execution for ${CURRENT_APP} app using $SCRIPT_NAME from $SCRIPT_PATH"
                            if (Test-Path -Path $SCRIPT_PATH) {
                                Set-Content $SCRIPT_PATH -Value (Get-Content $SCRIPT_PATH) -Encoding UTF8
                                colorprint "DEFAULT" "Executing custom script: $SCRIPT_NAME"
                                Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -command `"cd '$pwd'; & '$SCRIPT_PATH';`"" -wait
                            }
                            else {
                                colorprint "RED" "Custom script '$SCRIPT_NAME' not found in the scripts directory."
                            }
                        }
                        
                        '--manual' {
                            toLog_ifDebug -l "[DEBUG]" -m "Starting manual setup for ${CURRENT_APP} app"
                            colorprint "Blue" "${CURRENT_APP} requires further manual configuration."
                            # Read all the parameters for the manual flag , if one of them is the case instructions then save it in a variable and then prin the instruction to the user
                            if ($null -ne $flag_params_keys) {
                                foreach ($flag_param_key in $flag_params_keys) {
                                    toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter: $flag_param_key"
                                    switch ($flag_param_key) {
                                        'instructions' {
                                            toLog_ifDebug -l "[DEBUG]" -m "Reading flag parameter instructions"
                                            $flag_instructions_param = $app_json_obj.flags.$flag_name.$flag_param_key
                                            if ($flag_instructions_param) {
                                                toLog_ifDebug -l "[DEBUG]" -m "Result of flag_instructions_param reading: $flag_instructions_param"
                                                colorprint "Yellow" "$flag_instructions_param"
                                            }
                                            else {
                                                toLog_ifDebug -l "[DEBUG]" -m "No instructions found for flag: $flag_name inside $flag_param_key as flag_instructions_param is empty"
                                            }
                                        }
                                        default {
                                            toLog_ifDebug -l "[DEBUG]" -m "Unknown flag parameter: $flag_param_key"
                                        }
                                    }
                                }
                            }
                            else {
                                toLog_ifDebug -l "[DEBUG]" -m "No flag parameters found for flag: $flag_name as flag_params_keys array is empty"
                            }
                            colorprint "YELLOW" "Please after completing this automated setup check also the app's website for further instructions if there are any."
                        }
                        default { colorprint "RED" "Unknown flag: $($flags[$i]) passed to setupApp function" }
                    }

                }
                # Complete the setup of the app by enabling it in the docker-compose file
                (Get-Content $dk_compose_filename) -replace "#ENABLE_${CURRENT_APP}", "" | Set-Content $dk_compose_filename
                toLog_ifDebug -l "[DEBUG]" -m "Enabled ${CURRENT_APP} in $dk_compose_filename"
                # App Docker image architecture adjustments                
                $TAG = Get-Content $dk_compose_filename | Select-String -Pattern "\s*image: ${APP_IMAGE}:(\S+)" | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -First 1
                        
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
                    (Get-Content $dk_compose_filename).replace("${APP_IMAGE}:$TAG", "${APP_IMAGE}:$newTag") | Set-Content $DKCOM_FILENAME
                    }
                }
                else {
                    colorprint "yellow" "No native image tag found for $DKARCH arch, emulation layer will try to run this app image anyway."
                    #colorprint "default" "If an emulation layer is not already installed, the script will try to install it now. Please provide your sudo password if prompted."
                }
                $currentTag = Get-Content $dk_compose_filename | Select-String -Pattern "\s*image: ${APP_IMAGE}:(\S+)" | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -First 1
                toLog_ifDebug -l "[DEBUG]" -m "Finished Docker image architecture adjustments for ${CURRENT_APP} app. Its image tag is now: $currentTag"
                Write-Host "${CURRENT_APP} configuration complete, press enter to continue to the next app"
                Read-Host
                toLog_ifDebug -l "[DEBUG]" -m "Finished setupApp function for ${CURRENT_APP} app"
                break

            }
            elseif ($yn -eq 'n' -or $yn -eq 'no') {
                toLog_ifDebug -l "[DEBUG]" -m "User decided to skip the ${CURRENT_APP} app setup"
                colorprint "Blue" "Ok, ${CURRENT_APP} setup will be skipped"
                Start-Sleep -Seconds $SLEEP_TIME
                break
            }
            else {
                colorprint "Red" "Please answer yes or no."
            }
        }
        else {
            print_and_log "BLUE" "The ${CURRENT_APP} app is already enabled in the ${dk_compose_filename} file"
            Start-Sleep -Seconds $SLEEP_TIME
            break
        }       
    }
}
<#
.SYNOPSIS
Function that will setup the proxy for the apps in the stack

.DESCRIPTION
This function will setup the proxy for the apps in the stack. It will ask the user to enter the proxy to use and then it will update the ${ENV_FILENAME} file and the docker-compose.yaml file accordingly.

.EXAMPLE
Just call fn_setupProxy

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupProxy() {
    toLog_ifDebug -l "[DEBUG]" -m "Starting setupProxy function"
    if ($script:PROXY_CONF -eq $false) {
        while ($true) {
            colorprint "YELLOW" "Do you wish to setup a proxy for the apps in this stack Y/N?"
            colorprint "DEFAULT" "Note that if you want to run multiple instances of the same app, you will need to configure different env files in different project folders (copy the project to multiple different folders and configure them using different proxies)."
            $yn = Read-Host
            if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                Clear-Host
                toLog_ifDebug -l "[DEBUG]" -m "User chose to setup a proxy"
                colorprint "YELLOW" "Proxy setup started."

                # Read current names values
                $envContent = Get-Content .\$ENV_FILENAME
                $fullComposeProjectName = ($envContent | Where-Object { $_ -match "^COMPOSE_PROJECT_NAME=" }) -replace 'COMPOSE_PROJECT_NAME=', ''
                $fullDeviceName = ($envContent | Where-Object { $_ -match "^DEVICE_NAME=" }) -replace 'DEVICE_NAME=', ''

                # Shorten the project and device names
                $shortComposeProjectName = $fullComposeProjectName -replace '[_*0-9]+$'
                $shortDeviceName = $fullDeviceName -replace '[0-9]+$'
                
                # Generate a random value to append to the project name and device name to make them unique
                $script:RANDOM_VALUE = Get-Random -Maximum 32767 # 32767 is the maximum value for the $RANDOM function in bash
                colorprint "GREEN" "Insert the designed proxy to use. Eg: protocol://proxyUsername:proxyPassword@proxy_url:proxy_port or just protocol://proxy_url:proxy_port if auth is not needed:"
                $script:NEW_STACK_PROXY = Read-Host 
                # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                # ATTENTION: if a random value has been already added to the project and devicename during a previous setup it should remain the same to mantain consistency withthe devices name registered on the apps sites but the proxy url could be changed
                # If this is not the first setup proxy (proxy setup already configued in the past) then Ask the user if they wnat to keep the current project and device name, in the case they are just changing the proxy url for an existing stack that they want to keep or if they want to change the project and device name as well usable on a new stack runnin on the same device or on a different one
                $SKIP_NAMES_CHANGE_FOR_PROXY_SETUP = $false
                if ($script:PROXY_CONFIGURATION_STATUS -eq "1") {
                    while ($true) {
                        colorprint "BLUE" "The current project name is: $fullComposeProjectName"
                        colorprint "BLUE" "The current device name is: $fullDeviceName"
                        colorprint "YELLOW" "Do you want to keep the current project and device name? (Y/N)"
                        colorprint "DEFAULT" "No if you want to run multiple instances of the same app on the same device (copy the project to multiple different folders and configure them using different proxies), the project and device names will slightly change to keep them unique."
                        colorprint "DEFAULT" "Yes if you just want to update the proxy in use without changing the project and device name (One instance of the same app per device)"
                        $yn = Read-Host
                        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                            toLog_ifDebug -l "[DEBUG]" -m "User chose to keep the current project and device name"
                            colorprint "BLUE" "Ok, the current project and device name will be kept"
                            $SKIP_NAMES_CHANGE_FOR_PROXY_SETUP = $true
                            break
                        }
                        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                            toLog_ifDebug -l "[DEBUG]" -m "User chose to change the current project and device name"
                            colorprint "BLUE" "Ok, the current project and device name will be changed"
                            break
                        }
                        else {
                            colorprint "RED" "Please answer yes or no."
                        }
                    }
                }
                if (-not $SKIP_NAMES_CHANGE_FOR_PROXY_SETUP) {
                    # Update project name and device name with shortened name and random value
                    $envContent = $envContent -replace "COMPOSE_PROJECT_NAME=$fullComposeProjectName", "COMPOSE_PROJECT_NAME=${shortComposeProjectName}_$($script:RANDOM_VALUE)"
                    $envContent = $envContent -replace "DEVICE_NAME=$fullDeviceName", "DEVICE_NAME=${shortDeviceName}$($script:RANDOM_VALUE)"
                    # Update the DEVICE_NAME variable of the script with the new value
                    $script:DEVICE_NAME = "${shortDeviceName}$($script:RANDOM_VALUE)"
                }

                # Update the proxy configuration
                $envContent = $envContent -replace "# STACK_PROXY=", "STACK_PROXY="
                $CURRENT_VALUE = ($envContent | Select-String -Pattern "STACK_PROXY=" -SimpleMatch).ToString().Split("=")[1]
                $envContent = $envContent -replace "STACK_PROXY=${CURRENT_VALUE}", "STACK_PROXY=$script:NEW_STACK_PROXY"
                Set-Content .\$ENV_FILENAME -Value $envContent

                # Disable rolling restarts for watchtower
                $dkComContent = Get-Content $script:DKCOM_FILENAME -Raw
                $dkComContent = $dkComContent -replace '- WATCHTOWER_ROLLING_RESTART=true', '- WATCHTOWER_ROLLING_RESTART=false'
                $dkComContent = $dkComContent -replace '(?<=^|[\r\n])#ENABLE_PROXY(?![a-zA-Z0-9])', ''
                $dkComContent = $dkComContent -replace '# network_mode: service:', 'network_mode: service:'
                Set-Content $script:DKCOM_FILENAME -Value $dkComContent

                $script:PROXY_CONF = $true
                $envContent = $envContent -replace "PROXY_CONFIGURATION_STATUS=0", "PROXY_CONFIGURATION_STATUS=1"
                Set-Content .\$ENV_FILENAME -Value $envContent

                colorprint "DEFAULT" "Ok, $script:NEW_STACK_PROXY will be used as proxy for all apps in this stack"
                Read-Host -p "Press enter to continue"
                toLog_ifDebug -l "[DEBUG]" -m "Proxy setup finished"
                break
            }
            elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                toLog_ifDebug -l "[DEBUG]" -m "User chose not to setup a proxy"
                colorprint "BLUE" "Ok, no proxy will be used for the apps in this stack"
                Start-Sleep -Seconds $SLEEP_TIME
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
Function that will setup the ${ENV_FILENAME} file and the docker compose file

.DESCRIPTION
This function will setup the ${ENV_FILENAME} file and the docker compose file. It will ask the user to enter the required data for each app and then it will update the ${ENV_FILENAME} file and the docker-compose.yaml file accordingly.

.EXAMPLE
Just call fn_setupEnv

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_setupEnv() {
    param(
        [string]$app_type # Accept the type of apps as an argument
    )
    print_and_log "BLUE" "Starting setupEnv function for $app_type"

    # Check if ${ENV_FILENAME} file is already configured if 1 then it is already configured, if 0 then it is not configured
    Check-ConfigurationStatus -envFileArg "${ENV_FILENAME}"

    if (($ENV_CONFIGURATION_STATUS -eq "1") -and ($app_type -eq "apps")) {
        while ($true) {
            colorprint "YELLOW" "The current ${ENV_FILENAME} file appears to have already been configured. Do you wish to reset it? (Y/N)"
            $yn = Read-Host

            if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                print_and_log "DEFAULT" "Resetting ${ENV_FILENAME} file and ${DKCOM_FILENAME} file."
                Remove-Item .\${ENV_FILENAME}
                Remove-Item .\${DKCOM_FILENAME}
                Copy-Item .\${ENV_TEMPLATE_FILENAME} .\${ENV_FILENAME} -Force
                Copy-Item .\${DKCOM_TEMPLATE_FILENAME} .\${DKCOM_FILENAME} -Force
                Check-ConfigurationStatus -envFileArg "${ENV_FILENAME}"
                Clear-Host
                break
            }
            elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                print_and_log "BLUE" "Keeping the existing ${ENV_FILENAME} file."
                Start-Sleep -Seconds $SLEEP_TIME
                Check-ConfigurationStatus -envFileArg "${ENV_FILENAME}"
                Clear-Host
                break
            }
            else {
                colorprint "RED" "Invalid input. Please answer yes or no."
                continue
            }
        }
    }
    elseif (($ENV_CONFIGURATION_STATUS -eq "1") -and ($app_type -ne "apps")) {
        print_and_log "Blue" "Proceeding with $app_type setup without resetting ${ENV_FILENAME} file as it should already be configured by the main apps setup."
        Start-Sleep -Seconds $SLEEP_TIME
    }

    while ($true) {
        colorprint "YELLOW" "Do you wish to proceed with the ${ENV_FILENAME} file guided setup Y/N? (This will also adapt the $($script:DKCOM_FILENAME) file accordingly)"
        $yn = Read-Host

        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            Clear-Host
            toLog_ifDebug -l "[DEBUG]" -m "User chose to proceed with the ${ENV_FILENAME} file guided setup for $app_type"
            colorprint "YELLOW" "beginning env file guided setup"
            # Update the ENV_CONFIGURATION_STATUS
            (Get-Content .\${ENV_FILENAME}).replace("ENV_CONFIGURATION_STATUS=0", "ENV_CONFIGURATION_STATUS=1") | Set-Content .\${ENV_FILENAME}
            # Device Name setup
            $currentDeviceNameInEnv = (Get-Content .\${ENV_FILENAME} | Select-String -Pattern "DEVICE_NAME=" -SimpleMatch).ToString().Split("=")[1].Trim()
            if ($currentDeviceNameInEnv -eq $DEVICE_NAME_PLACEHOLDER) {
                toLog_ifDebug -l "[DEBUG]" -m "Device name is still the default one, asking user to change it"
                colorprint "YELLOW" "PLEASE ENTER A NAME FOR YOUR DEVICE:"
                $script:DEVICE_NAME = Read-Host
                (Get-Content .\${ENV_FILENAME}).replace("DEVICE_NAME=${DEVICE_NAME_PLACEHOLDER}", "DEVICE_NAME=$script:DEVICE_NAME") | Set-Content .\${ENV_FILENAME}
            }
            else {
                toLog_ifDebug -l "[DEBUG]" -m "Device name is already set, skipping user input"
                $script:DEVICE_NAME = "$currentDeviceNameInEnv"
            }
            # Proxy setup
            Clear-Host
            if ($PROXY_CONFIGURATION_STATUS -eq 1) {
                $script:CURRENT_PROXY = (Get-Content .\${ENV_FILENAME} | Select-String -Pattern "STACK_PROXY=" -SimpleMatch).ToString().Split("=")[1]
                print_and_log "BLUE" "Proxy is already set up."
                while ($true) {
                    colorprint "YELLOW" "The current proxy is: ${CURRENT_PROXY}. Do you wish to change it? (Y/N)"
                    $yn = Read-Host
                    if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                        $script:PROXY_CONF = $false
                        toLog_ifDebug -l "[DEBUG]" -m "User chose to change the proxy that was already configured"
                        fn_setupProxy
                        break
                    }
                    elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                        toLog_ifDebug -l "[DEBUG]" -m "User chose not to change the proxy that was already configured"
                        colorprint "BLUE" "Keeping the existing proxy."
                        Start-Sleep -Seconds $SLEEP_TIME
                        break
                    }
                    else {
                        colorprint "RED" "Invalid input. Please answer yes or no."
                    }
                }
            }
            else {
                toLog_ifDebug -l "[DEBUG]" -m "Asking user if they want to setup a proxy as it is not already configured"
                fn_setupProxy
            }
            # Apps setup
            Clear-Host
            toLog_ifDebug -l "[DEBUG]" -m "Loading $app_type from ${APP_CONFIG_JSON_FILE}"
            $apps = Get-Content "$script:CONFIG_DIR/${APP_CONFIG_JSON_FILE}" | ConvertFrom-Json | Select-Object -ExpandProperty $app_type
            toLog_ifDebug -l "[DEBUG]" -m "$app_type loaded from ${APP_CONFIG_JSON_FILE}"
            foreach ($app in $apps) {
                Clear-Host
                toLog_ifDebug -l "[DEBUG]" -m "Starting setupApp function for $($app.name) app"
                toLog_ifDebug "[DEBUG]" "Current app json object: $app"
                $app_as_json = $app | ConvertTo-Json -Compress
                toLog_ifDebug "[DEBUG]" "Current app json object as json: $app_as_json"
                fn_setupApp $app_as_json $script:DKCOM_FILENAME
                clear-Host
            }

            # Notifications setup
            Clear-Host
            if ($NOTIFICATIONS_CONFIGURATION_STATUS -eq 1) {
                print_and_log "Blue" "Notifications are already set up."
                while ($true) {
                    $CURRENT_SHOUTRRR_URL = (Get-Content .\${ENV_FILENAME} | Select-String -Pattern "SHOUTRRR_URL=" -SimpleMatch).ToString().Split("=")[1]
                    colorprint "YELLOW" "The current notifications setup uses: ${CURRENT_SHOUTRRR_URL}. Do you wish to change it? (Y/N)"
                    $yn = Read-Host
                    if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
                        fn_setupNotifications
                        break
                    }
                    elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
                        toLog_ifDebug -l "[DEBUG]" -m "User chose not to change the notifications setup that was already configured"
                        print_and_log "BLUE" "Noted: all updates will be applied automatically and silently"
                        break
                    }
                    else {
                        colorprint "RED" "Invalid input. Please answer yes or no."
                    }
                }
            }
            else {
                toLog_ifDebug -l "[DEBUG]" -m "Asking user if they want to setup notifications as they are not already configured"
                fn_setupNotifications
            }
            (Get-Content .\${ENV_FILENAME}).replace("ENV_CONFIGURATION_STATUS=0", "ENV_CONFIGURATION_STATUS=1") | Set-Content .\${ENV_FILENAME}
            print_and_log "GREEN" "env file setup complete."
            Read-Host -p "Press enter to go back to the menu"
            break
        }
        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
            toLog_ifDebug -l "[DEBUG]" -m "User chose not to proceed with the ${ENV_FILENAME} file guided setup for $app_type"
            colorprint "BLUE" "${ENV_FILENAME} file setup canceled. Make sure you have a valid ${ENV_FILENAME} file before proceeding with the stack startup."
            Read-Host -p "Press Enter to go back to mainmenu"
            return
        }
        else {
            colorprint "RED" "Please answer yes or no."
        }
    }
}
#Setup main apps
function fn_setupApps {
    fn_setupEnv -app_type "apps"
}
# Setup extra apps
function fn_setupExtraApps {
    fn_setupEnv -app_type "extra-apps"
}

<#
.SYNOPSIS
Function that will start the apps stack using the configured ${ENV_FILENAME} file and the docker compose file.

.DESCRIPTION
This function will start the apps stack using the configured ${ENV_FILENAME} file and the docker compose file.

.EXAMPLE
Just call fn_startStack

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_startStack() {
    Clear-Host
    while ($true) {
        colorprint "YELLOW" "This menu item will launch all the apps using the configured ${ENV_FILENAME} file and the $($script:DKCOM_FILENAME) file (Docker must be already installed and running)"
        $yn = Read-Host "Do you wish to proceed Y/N?"
        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            if (docker compose -f ${DKCOM_FILENAME} --env-file ${ENV_FILENAME} up -d) {
                print_and_log "Green" "All Apps started"
                # Call the script to generate dashboards urls for the apps that has them and check if execute correctly
                $dashboard_urls_script = "./generate_dashboard_urls.ps1"
                if (Test-Path "$dashboard_urls_script") {
                    print_and_log "GREEN" "Executing $dashboard_urls_script script"
                    & "$dashboard_urls_script"
                    if ($LASTEXITCODE -eq 0) {
                        print_and_log "GREEN" "All Apps dashboards URLs generated. Check the generated dashboards file for the URLs."
                    }
                    else {
                        errorprint_and_log "Error: $dashboard_urls_script failed to execute. Error generating Apps dashboards URLs"
                    }
                }
                else {
                    errorprint_and_log "Error: $dashboard_urls_script not found"
                }
                colorprint "Yellow" "If not already done, use the previously generated apps nodes URLs to add your device in any apps dashboard that require node claiming/registration (e.g. Earnapp, ProxyRack, etc.)"
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
Function that will stop all the apps and delete the docker stack previously created using the configured ${ENV_FILENAME} file and the docker compose file.

.DESCRIPTION
This function will stop all the apps and delete the docker stack previously created using the configured ${ENV_FILENAME} file and the docker compose file.

.EXAMPLE
Just call fn_stopStack

.NOTES
This function has been tested until v 2.0.0. The new version has not been tested as its assume that the logic is the same as the previous one just more refined.
#>
function fn_stopStack() {
    Clear-Host
    while ($true) {
        colorprint "YELLOW" "This menu item will stop all the apps and delete the docker stack previously created using the configured ${ENV_FILENAME} file and the $($script:DKCOM_FILENAME) file."
        $yn = Read-Host "Do you wish to proceed Y/N?"

        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            if (docker compose -f $DKCOM_FILENAME down) {
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

# Function that will call the script to seup the multiple proxies instances
function fn_setupmproxies {
    Clear-Host
    toLog_ifDebug -l "[DEBUG]" -m "Starting setupmproxies function"

    # Path to the runmproxies.sh script 
    $runmproxies_script = "./runmproxies.ps1"

    # Execute the  and check the exit status of the script
    if (Test-Path $runmproxies_script) {
        print_and_log "GREEN" "Executing $runmproxies_script script"
        & $runmproxies_script
        if ($LASTEXITCODE -eq 0) {
            colorprint "GREEN" "Multi-proxy setup completed successfully"
        }
        else {
            errorprint_and_log "Error: $runmproxies_script failed to execute"
        }
    }
    else {
        errorprint_and_log "Error: $runmproxies_script not found"
    }
    Write-Output "Returning to mainmenu"
    Start-Sleep -Seconds $SLEEP_TIME
}
<#
.SYNOPSIS
Function that will reset the ${ENV_FILENAME} file

.DESCRIPTION
This function will reset the ${ENV_FILENAME} file to the original version using the ${ENV_TEMPLATE_FILENAME} template file.

.EXAMPLE
Just call fn_resetEnv
#>
function fn_resetEnv() {
    Clear-Host
    toLog_ifDebug -l "[DEBUG]" -m "Starting resetEnv function"
    while ($true) {
        colorprint "YELLOW" "A fresh ${ENV_FILENAME} file will be created from the ${ENV_TEMPLATE_FILENAME} template file"
        $yn = Read-Host "Do you wish to proceed Y/N?"
        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            try {
                if (Test-Path .\${ENV_FILENAME}) {
                    Remove-Item .\${ENV_FILENAME}
                }
                Copy-Item .\${ENV_TEMPLATE_FILENAME} .\${ENV_FILENAME} -Force
                colorprint "GREEN" "${ENV_FILENAME} file resetted, remember to reconfigure it"
            }
            catch {
                colorprint "RED" "Error resetting ${ENV_FILENAME} file."
            }
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        elseif ($yn.ToLower() -eq 'n' -or $yn.ToLower() -eq 'no') {
            colorprint "BLUE" "${ENV_FILENAME} file reset canceled. The file is left as it is"
            Read-Host "Press Enter to go back to mainmenu"
            break
        }
        else {
            colorprint "RED" "Please answer yes or no."
        }
    }
    toLog_ifDebug -l "[DEBUG]" -m "resetEnv function ended"
}


<#
.SYNOPSIS
Function that will reset the docker-compose.yaml file

.DESCRIPTION
This function will reset the docker-compose.yaml file to the original version using the ${DKCOM_TEMPLATE_FILENAME} template file.

.EXAMPLE
Just call fn_resetDockerCompose
#>
function fn_resetDockerCompose() {
    Clear-Host
    toLog_ifDebug -l "[DEBUG]" -m "Starting resetDockerCompose function"
    while ($true) {
        colorprint "YELLOW" "A fresh ${DKCOM_FILENAME} file will be created from the ${DKCOM_TEMPLATE_FILENAME} template file"
        $yn = Read-Host "Do you wish to proceed Y/N?"
        if ($yn.ToLower() -eq 'y' -or $yn.ToLower() -eq 'yes') {
            try {
                if (Test-Path .\${DKCOM_FILENAME}) {
                    Remove-Item .\${DKCOM_FILENAME}
                }
                Copy-Item .\${DKCOM_TEMPLATE_FILENAME} .\${DKCOM_FILENAME} -Force
                colorprint "GREEN" "${DKCOM_FILENAME} file resetted, remember to reconfigure it if needed"
            }
            catch {
                colorprint "RED" "Error resetting ${DKCOM_FILENAME} file."
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
    toLog_ifDebug -l "[DEBUG]" -m "resetDockerCompose function ended"
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
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v$script:SCRIPT_VERSION"
    check_project_updates
    colorprint "GREEN" "---------------------------------------------- "
    colorprint "MAGENTA" "Join our Discord community for updates, help, and discussions: $DS_PROJECT_SERVER_URL"
    colorprint "MAGENTA" "---------------------------------------------- "
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
    colorprint "GREEN" "MONEY4BAND AUTOMATIC GUIDED SETUP v$script:SCRIPT_VERSION"
    check_project_updates
    adaptLimits
    colorprint "GREEN" "---------------------------------------------- "
    colorprint "CYAN" "Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!"
    colorprint "MAGENTA" "Join our Discord community for updates, help, and discussions: $DS_PROJECT_SERVER_URL"
    colorprint "MAGENTA" "---------------------------------------------- "
    colorprint "DEFAULT" "Detected OS type: $($script:OS_TYPE)"
    colorprint "DEFAULT" "Detected architecture: $($script:ARCH)"
    colorprint "DEFAULT" "Docker $($script:DKARCH) image architecture will be used if the app's image permits it"
    colorprint "DEFAULT" "---------------------------------------------- "
    
    toLog_ifDebug -l "[DEBUG]" -m "Loading menu options"
    # Reset the menuItems array
    $menuItems = @()
    # Load the menu items from the JSON file
    $menuItems = Get-Content "$script:CONFIG_DIR\$script:MAINMENU_JSON_FILE" | ConvertFrom-Json
    toLog_ifDebug -l "[DEBUG]" -m "Menu options loaded. Showing menu options, ready to select"

    for ($i = 0; $i -lt $menuItems.Length; $i++) {
        colorprint "DEFAULT" "$($i + 1)) $($menuItems[$i].label)"
    }

    $Select = Read-Host "Select an option and press Enter"
    do {
        if (([int]$Select -gt 0) -and ([int]$Select -le $menuItems.Length)) {
            Clear-Host
            toLog_ifDebug -l "[DEBUG]" -m "User selected option number $Select that corresponds to menu item [$($menuItems[$Select - 1].label)]"
            # Fetch the function name associated with the chosen menu item
            $functionName = $menuItems | Where-Object { $_.label -eq $menuItems[$Select - 1].label } | Select-Object -ExpandProperty function

            if ($functionName) {
                # Invoke the function
                & $functionName
            }
            else {
                colorprint "RED" "Error: Unable to find the function associated with the selected option."
                toLog_ifDebug -l "[DEBUG]" -m "Error in JSON: Missing function for menu item [$($menuItems[$Select - 1].label)]"
            }
            break
        }
        else {
            colorprint "RED" "Invalid input. Please select a number between 1 and $($menuItems.Length)"
            Start-Sleep -Seconds "$SLEEP_TIME"
            break
        }
    } while ($true)
}


### Startup ##
toLog_ifDebug -l "[DEBUG]" -m "Starting $script:SCRIPT_NAME v$script:SCRIPT_VERSION"
Clear-Host

# Detect the operating system
detect_os

# Detect the architecture and set the correct docker image architecture
detect_architecture

# Check dependencies
fn_checkDependencies

# Start the main menu
do {
    mainmenu
} while ($true)