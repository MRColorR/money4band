set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force

# Check if brew is installed and install it if it's not 
$BrewInstall=`which brew`
if ($BrewInstall -ne 0) {
    Write-Output "It seems brew is not installed. Intalling it now"
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

brew install --cask docker
open /Applications/Docker.app