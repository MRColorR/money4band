#!/bin/pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force

### Links ##
$EARNAPP_LNK = "EARNAPP | https://earnapp.com/i/3zulx7k"
$HONEYGAIN_LNK = "HONEYGAIN | https://r.honeygain.me/MINDL15721"
$IPROYALPAWNS_LNK = "IPROYALPAWNS | https://pawns.app?r=MiNe"
$PACKETSTREAM_LNK = "PACKETSTREAM | https://packetstream.io/?psr=3zSD"
$PEER2PROFIT_LNK = "PEER2PROFIT | https://p2pr.me/165849012262da8d0aa13c8"
$TRAFFMONETIZER_LNK = "TRAFFMONETIZER | https://traffmonetizer.com/?aff=366499"
$BITPING_LNK = "BITPING | https://app.bitping.com?r=qm7mIuX3"

### .env File Prototype Link##
$ENV_SRC = 'https://github.com/MRColorR/money4band/raw/main/.env'

### docker-compose.yml Prototype Link##
$DKCOM_SRC = 'https://github.com/MRColorR/money4band/raw/main/docker-compose.yml'

### Docker installer script for windows source link ##
$DKINST_WIN_SRC = 'https://github.com/MRColorR/money4band/raw/main/install-docker.ps1'

### Proxy config #
$PROXY_CONF='false' ;
$PROXY_CONF_ALL='false' ;
$STACK_HTTP_PROXY='';
$STACK_HTTPS_PROXY='';

### Functions ##
function fn_bye { Write-Output "Bye bye."; exit 0; }
function fn_fail { Write-Output "Wrong option." exit 1; }
function fn_unknown { Write-Output "Unknown choice $REPLY, please choose a valid option"; }

### Sub-menu Functions ##
function fn_showLinks {
    clear;
    Write-Output "Use CTRL+Click to open links or copy them:"
    Write-Output $EARNAPP_LNK
    Write-Output $HONEYGAIN_LNK
    Write-Output $IPROYALPAWNS_LNK
    Write-Output $PACKETSTREAM_LNK
    Write-Output $PEER2PROFIT_LNK
    Write-Output $TRAFFMONETIZER_LNK
    Write-Output $BITPING_LNK
    Read-Host -Prompt "Press enter to go back to mainmenu"
    mainmenu
}

function fn_dockerInstall {
    clear;
    Write-Output "This menu item will launch a script that will attempt to install docker"
    Write-Output "Use it only if you do not know how to perform the manual docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some cases and depending on the OS you are using may fail to install docker correctly."
    $yn = Read-Host -Prompt "Do you wish to proceed with the Docker automatic installation Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        clear;
        Write-Output "Which version of Docker do you want to install?"
        Write-Output "1) Install Docker for Linux"
        Write-Output "2) Install Docker for Windows"
        $yn = Read-Host
        Switch ($Select) {
            1 {
                Write-Output "Starting Docker for linux auto installation script"
                curl  -o 'get-docker.sh' https://get.docker.com ;
                sudo sh get-docker.sh;
                Write-Output "Script completed. Docker should be installed"
                Read-Host -Prompt "Press enter to go back to mainmenu"
                mainmenu
            }
            2 {
                Write-Output "Starting Docker for Windows auto installation script"
                Invoke-WebRequest $DKINST_WIN_SRC -o install-docker.ps1
                Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -Command `"cd '$pwd'; & '.\install-docker.ps1';`"" -Wait
                
                Write-Output "Script completed. Docker should be installed. Please restart your computer and the proceed to .env file config and stack startup."
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
        Write-Output "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps.  ";
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

function fn_setupNotifications(){
    clear;
    Write-Output "This step will setup notifications about containers updates using shoutrrr"
    Write-Output "Now we will configure a SHOUTRRR_URL that should looks like this <app>://<token>@<webhook> . Where <app> is one of the supported messaging apps supported by shoutrrr (We will use a private discord server as example)."
    Write-Output "For more apps and details visit https://containrrr.dev/shoutrrr/, select your desider app (service) and paste the required SHOUTRRR_URL in this script when prompted "
    Read-Host -p "Press enter to proceed and show the discord notification setup example (Remember: you can also use a different supported app, just enter the link correctly)"
    clear;
    Write-Output "CREATE A NEW DISCORD SERVER, GO TO SERVER SETTINGS>INTEGRATIONS AND CREATE A WEBHOOK"
    Write-Output "Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken to obtain the SHOUTRRR_URL you should rearrange it to look like this: discord://yourToken@yourWebhookid"
    Read-Host -p "Press enter to continue"
    clear;
    Write-Output "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"
    Read-Host -r SHOUTRRR_URL
    (Get-Content .\.env).replace('# SHOUTRRR_URL=yourApp:yourToken@yourWebHook', "SHOUTRRR_URL=$SHOUTRRR_URL") | Set-Content .\.env
    (Get-Content .\docker-compose.yml).replace('# - WATCHTOWER_NOTIFICATIONS=shoutrrr', "- WATCHTOWER_NOTIFICATIONS=shoutrrr") | Set-Content .\docker-compose.yml
    (Get-Content .\docker-compose.yml).replace('# - WATCHTOWER_NOTIFICATION_URL', "- WATCHTOWER_NOTIFICATION_URL") | Set-Content .\docker-compose.yml
    (Get-Content .\docker-compose.yml).replace('# - WATCHTOWER_NOTIFICATIONS_HOSTNAME', "- WATCHTOWER_NOTIFICATIONS_HOSTNAME") | Set-Content .\docker-compose.yml
    Read-Host -p "Notifications setup complete. If the link is correct, you will receive a notification for each update made on the app container images. Now press enter to continue"
    clear;
}

function fn_setupApp(){
    if ( "$2" -eq "email" ){
        Write-Output "Enter your $1 Email"
        $APP_EMAIL = Read-Host 
        (Get-Content .\.env).replace("your$1Mail", "$APP_EMAIL") | Set-Content .\.env
    
        if ("$3" -eq "password" ){ 
        Write-Output "Now enter your $1 Password"
        $APP_PASSWORD = Read-Host  
        (Get-Content .\.env).replace("your$1Pw", "$APP_PASSWORD") | Set-Content .\.env
        }
    }
    elseif ( "$2" -eq "uuid" ){
        Write-Output "generating an UUID for $1"
        $SALT="$3$(Get-Random)"
        $md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
        $utf8 = New-Object -TypeName System.Text.UTF8Encoding
        $UUID = [System.BitConverter]::ToString($md5.ComputeHash($utf8.GetBytes($SALT))).replace("-", "").ToLower()
        (Get-Content .\.env).replace("your$1""MD5sum", "$UUID") | Set-Content .\.env
        Write-Output "Save the following link somewhere to claim your earnapp node after completing the setup and after starting the apps stack: https://earnapp.com/r/sdk-node-$UUID. A new file containing this link has been created for you"
        Write-Output "https://earnapp.com/r/sdk-node-$UUID" > ClaimEarnappNode.txt 
    }

    elseif ("$2" -eq "cid" ){
        Write-Output "Enter your $1 CID."
        Write-Output "You can find it going in your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
        $APP_CID = Read-Host 
        (Get-Content .\.env).replace("your$1""CID", "$APP_CID") | Set-Content .\.env
    }

    elseif  ("$2" -eq "token"){
        Write-Output "Enter your $1 Token."
        Write-Output "You can find it going in your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
        $APP_TOKEN = Read-Host 
        (Get-Content .\.env).replace("your$1""Token", "$APP_TOKEN") | Set-Content .\.env
    }
    
    if  ("$PROXY_CONF" -eq 'true') {
        if ( "$PROXY_CONF_ALL" -eq 'true'){
            (Get-Content .\.env).replace("# $1""_HTTP_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "$1""_HTTP_PROXY=$STACK_HTTP_PROXY") | Set-Content .\.env
            (Get-Content .\.env).replace("# $1""_HTTPS_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "$1""_HTTPS_PROXY=$STACK_HTTPS_PROXY") | Set-Content .\.env
        }
        else{
            Write-Output "Insert the designed HTTP proxy to use with $1 (also socks5h is supported)."
            $APP_HTTP_PROXY = Read-Host 
            Write-Output "Insert the designed HTTPS proxy to use with $1 (you can also use the same of the HTTP proxy and also socks5h is supported)."
            $APP_HTTPS_PROXY = Read-Host 
            (Get-Content .\.env).replace("# $1""_HTTP_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "$1""_HTTP_PROXY=$APP_HTTP_PROXY") | Set-Content .\.env
            (Get-Content .\.env).replace("# $1""_HTTPS_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "$1""_HTTPS_PROXY=$APP_HTTPS_PROXY") | Set-Content .\.env
        }

        
        sed -i "s^^^" docker-compose.yml ;
        (Get-Content .\docker-compose.yml).replace("#- $1""_HTTP_PROXY", "- HTTP_PROXY") | Set-Content .\docker-compose.yml
        (Get-Content .\docker-compose.yml).replace("#- $1""_HTTPS_PROXY", "- HTTPS_PROXY") | Set-Content .\docker-compose.yml
        (Get-Content .\docker-compose.yml).replace("#- $1""_NO_PROXY", "- NO_PROXY") | Set-Content .\docker-compose.yml
    }
}

function fn_setupProxy(){
    if ( "$PROXY_CONF" -eq 'false' ){
        $yn = Read-Host -p "Do you wish to use a proxy? Y/N? Note that if you want to run multiple instances of the same app you will need to configure different env files each in different project folders (copy the project to multiple different folders and configure them using different proxies)"
        if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ){
            clear;
                Write-Output "Proxy setup started.";
                $yn = Read-Host -p "Do you wish to use the same proxy for all the apps in this stack? Y/N?"
                if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ){
                        Write-Output "Insert the designed HTTP proxy to use. Eg: http://proxyUsername:proxyPassword@proxy_url:proxy_port or just http://proxy_url:proxy_port if auth is not needed, also socks5h is supported.";
                        $STACK_HTTP_PROXY = Read-Host 
                        Write-Output "Ok, $STACK_HTTP_PROXY will be used as proxy for all apps in this stack"
                        Read-Host -p "Press enter to continue"
                        clear
                        Write-Output "Insert the designed HTTPS proxy to use (you can also use the same of the HTTP proxy), also socks5h is supported."
                        $STACK_HTTPS_PROXY = Read-Host
                        Write-Output "Ok, $STACK_HTTPS_PROXY will be used as secure proxy for all apps in this stack"
                        Read-Host -p "Press enter to continue"
                        PROXY_CONF_ALL='true' ;
                        PROXY_CONF='true' ;
                    }
        } elseif ($yn -eq 'N' -or $yn -eq 'n' -or $yn -eq 'No' -or $yn -eq 'no') {
            $PROXY_CONF_ALL='false' ;
                    $PROXY_CONF='true' ;
                    Write-Output "Ok, later you will be asked for a proxy for each application"
        }else {
            clear;
            Write-Output "Please answer yes or no."
            fn_setupProxy ;

        }
                # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
                (Get-Content .\.env).replace("COMPOSE_PROJECT_NAME= Money4Band", "COMPOSE_PROJECT_NAME= Money4Band_$(Get-Random)") | Set-Content .\.env
    }elseif ($yn -eq 'N' -or $yn -eq 'n' -or $yn -eq 'No' -or $yn -eq 'no') {
                Write-Output "Ok, no proxy added to configuration."
    }else {
        clear;
        Write-Output "Please answer yes or no."
        fn_setupProxy ;

    }
}

function fn_setupEnv {
    clear;
    $yn = Read-Host -p "Do you wish to proceed with the .env file guided setup Y/N? (This will also adapt the docker-compose.yml file accordingly)"
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        clear;
        Write-Output "Beginnning env file guided setup"
        $CURRENT_APP='';
        $DEVICE_NAME = Read-Host -prompt "PLEASE ENTER A NAME FOR YOUR DEVICE:"
        (Get-Content .\.env).replace('yourDeviceName', "$DEVICE_NAME") | Set-Content .\.env

        clear ;
        fn_setupProxy ;
        clear ;

        Write-Output "PLEASE REGISTER ON THE PLATFORMS USING THIS LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
        Write-Output "Use CTRL+Click to open links or copy them:"

        #EarnApp app env setup
        $CURRENT_APP='EARNAPP';
        Write-Output "Go to $EARNAPP_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp $CURRENT_APP uuid "$DEVICE_NAME";
        Read-Host -p "$CURRENT_APP configuration complete, press enter to continue to the next app"


        #HoneyGain app env setup
        clear
        $CURRENT_APP='HONEYGAIN';
        Write-Output "Go to $HONEYGAIN_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp $CURRENT_APP email password ;
        Read-Host -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

        #IPROYALPAWNS app env setup
        clear
        $CURRENT_APP='IPROYALPAWNS';
        Write-Output "Go to $IPROYALPAWNS_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp $CURRENT_APP email password ;
        Read-Host -p "$CURRENT_APP configuration complete, press enter to continue to the next app"


        #Peer2Profit app env setup
        clear
        $CURRENT_APP='PEER2PROFIT';
        Write-Output "Go to $PEER2PROFIT_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp $CURRENT_APP email ;
        Read-Host -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

        #PacketStream app env setup
        clear
        $CURRENT_APP='PACKETSTREAM';
        Write-Output "Go to $PACKETSTREAM_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp $CURRENT_APP cid ;
        Read-Host -p "$CURRENT_APP configuration complete, press enter to continue to the next app"

        # TraffMonetizer app env setup
        clear
        $CURRENT_APP='TRAFFMONETIZER';
        Write-Output "Go to $TRAFFMONETIZER_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp $CURRENT_APP token ;
        Read-Host -p "$CURRENT_APP configuration complete, press enter to continue to the next app"
    
        # Bitping app env setup
        clear
        Write-Output "Go to $BITPING_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        Write-Output "To configure this app we will need to start an interactive container (so Docker needs to be already installed)."
        Write-Output "To do that now we will open a new terminal in this same folder and run bitpingSetup for you."
        Read-Host -prompt "When ready to start, press enter to continue"
        Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -Command `"cd '$pwd'; & '.\bitpingSetup.ps1';`"" -wait

        # Notifications setup
        clear;
        $yn = Read-Host -p "Do you wish to setup notifications about apps images updates (Yes to recieve notifications and apply updates, No to just silently apply updates) Y/N?  "
        if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
          fn_setupNotifications ;
        } elseif ($yn -eq 'N' -or $yn -eq 'n' -or $yn -eq 'No' -or $yn -eq 'no') {
            Write-Output "Noted: all updates will be applied automatically and silently"
        }else{
            Write-Output "Please answer yes or no."
        }

        Write-Output "env file setup complete."
        Read-Host -prompt "Press enter to go back to the menu";

        mainmenu;

    }
    else {
        Write-Output ".env file setup canceled. Make sure you have a valid .env file before proceeding with the stack startup.";
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
    
}

function fn_startStack {
    Write-Output "This menu item will launch all the apps using the configured .env file and the docker-compose.yml file (Docker must be already installed and running)"
    $yn = Read-Host -prompt "Do you wish to proceed Y/N?"
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        docker compose up -d
        Write-Output 'All Apps started you can visit the web dashboard on http://localhost:8081/ . If not already done use the previously generated earnapp node URL to add your device in your earnapp dashboard.'
        Read-Host "Check the README file for more details. Now press enter to go back to the menu";
        mainmenu;
    }
    else {
        Write-Output "Docker stack startup canceled. After configuring the .env you have to start the stack to be able to earn. Proceed when you feel ready."
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

function fn_resetEnv {
    Write-Output "Now a fresh env file will be downloaded and will need to be reconfigured to be used again"
    $yn = Read-Host -prompt "Do you wish to proceed Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        Invoke-WebRequest -OutFile '.env' $ENV_SRC; Write-Output ".env file resetted, remember to reconfigure it";
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
    else {
        Write-Output ".env file reset canceled. The file is left as it is.  "
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

function fn_resetDockerCompose{
    Write-Output "Now a fresh docker-compose.yml file will be downloaded"
    $yn = Read-Host -prompt "Do you wish to proceed Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        Invoke-WebRequest -OutFile 'docker-compose.yml' $DKCOM_SRC; Write-Output "docker-compose.yml file resetted, remember to reconfigure it if needed";
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
    else {
        Write-Output "docker-compose.yml file reset canceled. The file is left as it is. "
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