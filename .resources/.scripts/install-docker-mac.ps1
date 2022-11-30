# if a flag is provided it will install Docker for mac with intelCPU
param(
    [string(Mandatory)]$filePath,
    [switch]$IntelCPU
    )
$cpu = ""
if ($IntelCPU) {
    $cpu = "Intel"
    #Invoke-WebRequest https://desktop.docker.com/mac/main/amd64/Docker.dmg -o "$filePath/Docker.dmg";
}else {
    $cpu = "Apple silicon arm"
    #Invoke-WebRequest https://desktop.docker.com/mac/main/arm64/Docker.dmg -o "$filePath/Docker.dmg";
}
Read-Host -Prompt "Ready. Press enter to install Docker for Mac with $cpu CPU"
sudo hdiutil attach "$filePath/Docker.dmg"
sudo /Volumes/Docker/Docker.app/Contents/MacOS/install --accept-license
sudo hdiutil detach /Volumes/Docker
open /Applications/Docker.app

