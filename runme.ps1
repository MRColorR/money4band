#!/bin/pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force


### Colors ##
# ESC=$(printf '\033') RESET="${ESC}[0m" BLACK="${ESC}[30m" RED="${ESC}[31m"
# $GREEN="${ESC}[32m" YELLOW="${ESC}[33m" BLUE="${ESC}[34m" MAGENTA="${ESC}[35m"
# $CYAN="${ESC}[36m" WHITE="${ESC}[37m" DEFAULT="${ESC}[39m"

### Color Functions ##

# greenprint { printf  "$1"; }
# blueprint { printf  "$1"; }
# redprint { printf  "$1"; }
# yellowprint { printf  "$1"; }
# magentaprint { printf  "$1"; }
# cyanprint { printf  "$1"; }

### Links ##
$EARNAPP_LNK = "Earnapp | https://earnapp.com/i/3zulx7k"
$HONEYGAIN_LNK = "HoneyGain | https://r.honeygain.me/MINDL15721"
$IPROYAL_LNK = "IPROYAL | https://pawns.app?r=MiNe"
$PACKETSTREAM_LNK = "PACKETSTREAM | https://packetstream.io/?psr=3zSD"
$PEER2PROFIT_LNK = "PEER2PROFIT | https://p2pr.me/165849012262da8d0aa13c8"
$TRAFFMONETIZER_LNK = "TRAFFMONETIZER | https://traffmonetizer.com/?aff=366499"
$BITPING_LNK = "BITPING | https://app.bitping.com?r=qm7mIuX3"

### .env File Prototype Link##
$ENV_SRC = 'https://github.com/MRColorR/money4band/raw/main/.env'

### docker-compose.yml Prototype Link##
$DKCOM_SRC = 'https://github.com/MRColorR/money4band/raw/main/docker-compose.yml'

### Functions ##
function fn_bye { echo "Bye bye."; exit 0; }
function fn_fail { echo "Wrong option." exit 1; }
function fn_unknown { echo "Unknown choice $REPLY, please choose a valid option"; }

### Sub-menu Functions ##
function fn_showLinks {
    clear;
    echo "Use CTRL+Click to open links or copy them:"
    echo $EARNAPP_LNK
    echo $HONEYGAIN_LNK
    echo $IPROYAL_LNK
    echo $PACKETSTREAM_LNK
    echo $PEER2PROFIT_LNK
    echo $TRAFFMONETIZER_LNK
    echo $BITPING_LNK
    Read-Host -Prompt "Press enter to go back to mainmenu"
    mainmenu
}

function fn_dockerInstall {
    clear;
    echo "This menu item will launch a script that will attempt to install docker"
    echo "Use it only if you do not know how to perform the manual docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some cases and depending on the OS you are using may fail to install docker correctly."
    $yn = Read-Host -Prompt "Do you wish to proceed with the Docker automatic installation Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        clear;
        echo "Which version of Docker do you want to install?"
        echo "1) Install Docker for Linux"
        echo "2) Install Docker for Windows"
        $yn = Read-Host
        Switch ($Select) {
            1 {
                echo "Starting Docker for linux auto installation script"
                curl -fsSL https://get.docker.com -o get-docker.sh;
                sudo sh get-docker.sh;
                echo "Script completed. Docker should be installed"
                Read-Host -Prompt "Press enter to go back to mainmenu"
                mainmenu
            }
            2 {
                echo "Starting Docker for Windows auto installation script"
                
                Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -Command `"cd '$pwd'; & '.\install-docker.ps1';`""
                echo "Script completed. Docker should be installed. Please restart your computer and the proceed to .env file config and stack startup."
                Read-Host -Prompt "Press enter to go back to mainmenu"
                mainmenu
            }
            DEFAULT {
                fn_unknown
            }
        }
    }
    else {
        clear;
        echo "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps.  ";
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

function fn_setupEnv {
    clear;
    $yn = Read-Host -p "Do you wish to proceed with the .env file guided setup Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        clear;
        echo "Beginnning env file guided setup"
        #touch .env
        $DEVICE_NAME = Read-Host -prompt "PLEASE ENTER A NAME FOR YOUR DEVICE:"
        (Get-Content .\.env).replace('yourDeviceName', "$DEVICE_NAME") | Set-Content .\.env

        echo "PLEASE REGISTER ON THE PLATFORMS USING THIS LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
        echo "Use CTRL+Click to open links or copy them:"

        #EarnApp app env setup
        
        echo "Go to $EARNAPP_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        echo "generating an UUID for earnapp"
        $md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
        $utf8 = New-Object -TypeName System.Text.UTF8Encoding
        $UUID = [System.BitConverter]::ToString($md5.ComputeHash($utf8.GetBytes($DEVICE_NAME))).replace("-", "").ToLower()
        (Get-Content .\.env).replace('yourMD5sum', "$UUID") | Set-Content .\.env
        echo "!!SAVE THE FOLLOWING LINK SOMEWHERE TO CLAIM YOUR EARNAPP NODE after completing the setup and after starting the apps stack: https://earnapp.com/r/sdk-node-$UUID"
        Read-Host -prompt "When done, press enter to continue to the next app"

        #HoneyGain app env setup
        clear
        echo "Go to $HONEYGAIN_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        $HG_EMAIL = Read-Host -prompt "Enter your HoneyGain Email"
        (Get-Content .\.env).replace('yourHGMail', "$HG_EMAIL") | Set-Content .\.env
        $HG_PASSWORD = Read-Host -prompt "Now enter your HoneyGain Password"
        (Get-Content .\.env).replace('yourHGPw', "$HG_PASSWORD") | Set-Content .\.env

        #Pawn IPRoyal app env setup
        clear
        echo "Go to $IPROYAL_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        $IR_EMAIL = Read-Host -prompt "Enter your Pawn IPRoyal Email"
        (Get-Content .\.env).replace('yourIRMail', "$IR_EMAIL") | Set-Content .\.env
        $IR_PASSWORD = Read-Host -prompt "Now enter your IPRoyal Password"
        (Get-Content .\.env).replace('yourIRPw', "$IR_PASSWORD") | Set-Content .\.env

        #Peer2Profit app env setup
        clear
        echo "Go to $PEER2PROFIT_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        $P2P_EMAIL = Read-Host -prompt "Enter your Peer2Profit Email"
        (Get-Content .\.env).replace('yourP2PMail', "$P2P_EMAIL") | Set-Content .\.env

        #PacketStream app env setup
        clear
        echo "Go to $PACKETSTREAM_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        echo "Enter your PacketStream CID."
        echo "You can find it going in your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page (you can also use CTRL+F) you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
        $PS_CID = Read-Host PS_CID
        (Get-Content .\.env).replace('yourPSCID', "$PS_CID") | Set-Content .\.env

        # TraffMonetizer app env setup
        clear
        echo "Go to $TRAFFMONETIZER_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        echo "Enter your TraffMonetizer Token."
        echo "You can find it going in your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
        $TM_TOKEN = Read-Host TM_TOKEN
        (Get-Content .\.env).replace('yourTMToken', "$TM_TOKEN") | Set-Content .\.env
    
        # Bitping app env setup
        clear
        echo "Go to $BITPING_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        echo "To configure this app we will need to start an interactive container (so Docker needs to be already installed)."
        echo "Then wait and enter your bitping email and password in it when prompted, hit enter and then close it as we will not need it anymore"
        echo "To do that we will open a new terminal in this same folder and run bitpingSetup.sh for you"
        Read-Host -prompt "When ready to start, press enter to continue"
        Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -Command `"cd '$pwd'; & '.\bitpingSetup.ps1';`""

        echo "env file setup complete."
        Read-Host -prompt "Press enter to go back to the menu";

        mainmenu;

    }
    else {
        echo ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup.";
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
    
}

function fn_startStack {
    echo "This menu item will launch all the apps using the configured .env file and the docker-compose.yml file (Docker must be already installed and running)"
    $yn = Read-Host -prompt "Do you wish to proceed Y/N?"
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        docker compose up -d
        echo "All Apps started. If not already done use the previously generated earnapp node URL to add your device in your earnapp dashboard. Check the README file for more details.";
        mainmenu;
    }
    else {
        echo "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps.  "
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

function fn_resetEnv {
    echo "Now a fresh env file will be downloaded and will need to be reconfigured to be used again"
    $yn = Read-Host -prompt "Do you wish to proceed Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        curl -LJO $ENV_SRC; echo ".env file resetted, remember to reconfigure it";
    }
    else {
        echo ".env file reset canceled. The file is left as it is.  "
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

function fn_resetDockerCompose{
    echo "Now a fresh docker-compose.yml file will be downloaded"
    $yn = Read-Host -prompt "Do you wish to proceed Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        curl -LJO $DKCOM_SRC; echo "docker-compose.yml file resetted, remember to reconfigure it if needed";
    }
    else {
        echo "docker-compose.yml file reset canceled. The file is left as it is. "
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

### Main Menu ##
function mainmenu {
    clear;
    Write-Output "Select an option and press Enter: "
    Write-Output "1) Show apps' links to register or go to dashboard"
    Write-Output "2) Install Docker"
    Write-Output "3) Setup .env file"
    Write-Output "4) Start apps stack"
    Write-Output "5) Reset .env File"
    Write-Output "6) Reset docker-compose.yml file"
    Write-Output "7) Exit"
    Do {
        $Select = Read-Host
        Switch ($Select) {
            1 {
                fn_showLinks
            }
            2 {
                fn_dockerInstall
            }
            3 {
                fn_setupEnv
            }
            4 {
                fn_startStack
            }
            5 {
                fn_resetEnv
            }
            6 {
                fn_resetDockerCompose
            }
            7{
                fn_bye
            }
            DEFAULT {
                fn_unknown
            }
        }
    }
    While ($Select -ne 6)
}

### Startup ##
mainmenu