# if a flag is provided it will install Docker for mac with intelCPU
param(
    [string(Mandatory)]$filePath,
    [switch]$IntelCPU
    )

if ($IntelCPU) {
    Write-Output "Selected Intel CPU"
    #Invoke-WebRequest https://desktop.docker.com/mac/main/amd64/Docker.dmg -o "$filePath/Docker.dmg";
}else {
    Write-Output "Selected Appla silicon arm CPU"
    #Invoke-WebRequest https://desktop.docker.com/mac/main/arm64/Docker.dmg -o "$filePath/Docker.dmg";
}
sudo hdiutil attach "$filePath"
sudo /Volumes/Docker/Docker.app/Contents/MacOS/install --accept-license
sudo hdiutil detach /Volumes/Docker
open /Applications/Docker.app

