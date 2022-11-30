# if a flag is provided it will install Docker for mac with intelCPU
param(
    [Parameter(Mandatory)][string]$filesPath,
    [switch]$IntelCPU
    )
$cpu = ""
Write-Host "Downloading Docker setup files, please wait... "
if ($IntelCPU) {
    $cpu = "Intel"
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest https://desktop.docker.com/mac/main/amd64/Docker.dmg -o "$filesPath/Docker.dmg";
    $ProgressPreference = 'Continue'
}else {
    $cpu = "Apple silicon arm"
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest https://desktop.docker.com/mac/main/arm64/Docker.dmg -o "$filesPath/Docker.dmg";
    $ProgressPreference = 'Continue'
}
Write-Output "Installing Docker for $cpu CPU, please wait..."
sudo hdiutil attach "$filesPath/Docker.dmg"
sudo /Volumes/Docker/Docker.app/Contents/MacOS/install --accept-license
sudo hdiutil detach /Volumes/Docker
open /Applications/Docker.app