# Define paths and default file names
$proxiesFile = if ($args.Count -gt 0) { $args[0] } else { "proxies.txt" }
$dockerComposeTemplate = "docker-compose.yaml"
$envTemplate = ".env"
$rootDir = Get-Location
$instancesDir = Join-Path -Path $rootDir -ChildPath "m4b_proxy_instances"
$logFile = Join-Path -Path $rootDir -ChildPath "multiproxies.log"

# Ensure the instances directory exists
if (-not (Test-Path -Path $instancesDir)) {
    New-Item -Path $instancesDir -ItemType Directory | Out-Null
}

# Read proxies from file
$proxies = Get-Content -Path $proxiesFile

# Load COMPOSE_PROJECT_NAME and DEVICE_NAME from the .env file
$envContent = Get-Content -Path $envTemplate
$composeProjectName = ($envContent | Where-Object { $_ -match "^COMPOSE_PROJECT_NAME=" }) -split '=', 2 | Select-Object -Last 1
$deviceName = ($envContent | Where-Object { $_ -match "^DEVICE_NAME=" }) -split '=', 2 | Select-Object -Last 1

# Function to log messages
function Log-Message {
    Param (
        [string]$Message,
        [string]$Type = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp [$Type] $Message" | Out-File -FilePath $logFile -Append
    if ($Type -eq "ERROR") {
        Write-Host -ForegroundColor Red $Message
    } else {
        Write-Host $Message
    }
}

foreach ($proxy in $proxies) {
    $uniqueSuffix = Get-Random -Maximum 9999
    $instanceDirName = "m4b_${composeProjectName}_${deviceName}_$uniqueSuffix"
    $instanceDir = Join-Path -Path $instancesDir -ChildPath $instanceDirName

    # Create instance directory
    New-Item -Path $instanceDir -ItemType Directory | Out-Null

    # Copy all relevant files from the root directory to the instance directory
    Get-ChildItem -Path $rootDir -Exclude ".git", "m4b_proxy_instances", "*.log" | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $instanceDir -Recurse -Force
    }

    # Update .env with unique COMPOSE_PROJECT_NAME and DEVICE_NAME, and set the proxy
    $instanceEnvFile = Join-Path -Path $instanceDir -ChildPath ".env"
    (Get-Content -Path $instanceEnvFile) -replace "COMPOSE_PROJECT_NAME=.*", "COMPOSE_PROJECT_NAME=${composeProjectName}_$uniqueSuffix" -replace "DEVICE_NAME=.*", "DEVICE_NAME=${deviceName}_$uniqueSuffix" -replace "STACK_PROXY=.*", "STACK_PROXY=$proxy" | Set-Content -Path $instanceEnvFile

    # Start the docker-compose in the instance directory
    Push-Location -Path $instanceDir
    try {
        docker-compose up -d | Out-Null
        Log-Message -Message "Docker compose up succeeded for $instanceDirName"
    } catch {
        Log-Message -Message "Failed to start docker-compose for $instanceDirName" -Type "ERROR"
    }
    Pop-Location
}

# Final message indicating completion
Log-Message -Message "Created and ran $($proxies.Count) instances with unique proxies."
