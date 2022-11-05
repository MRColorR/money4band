#!/bin/pwsh
set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force

### Links ##
$EARNAPP_LNK = "EARNAPP | https://earnapp.com/i/3zulx7k"
$HONEYGAIN_LNK = "HONEYGAIN | https://r.honeygain.me/MINDL15721"
$IPROYALPAWNS_LNK = "IPROYALPAWNS | https://pawns.app?r=MiNe"
$PACKETSTREAM_LNK = "PACKETSTREAM | https://packetstream.io/?psr=3zSD"
$PEER2PROFIT_LNK = "PEER2PROFIT | https://p2pr.me/165849012262da8d0aa13c8"
$TRAFFMONETIZER_LNK = "TRAFFMONETIZER | https://traffmonetizer.com/?aff=366499"
$REPOCKET_LNK = "REPOCKET | https://link.repocket.co/hr8i"
$BITPING_LNK = "BITPING | https://app.bitping.com?r=qm7mIuX3"

### .env File Prototype Link##
$ENV_SRC = 'https://github.com/MRColorR/money4band/raw/main/.env'

### docker-compose.yml Prototype Link##
$DKCOM_SRC = 'https://github.com/MRColorR/money4band/raw/main/docker-compose.yml'

### Docker installer script for windows source link ##
$DKINST_WIN_SRC = 'https://github.com/MRColorR/money4band/raw/main/install-docker.ps1'

### Resources, Scripts and Files folders
$RESOURCES_DIR = "$pwd\.resources"
$SCRIPTS_DIR = "$RESOURCES_DIR\.scripts"
$FILES_DIR = "$RESOURCES_DIR\.files"

### Proxy config #
$script:PROXY_CONF = $false
$script:PROXY_CONF_ALL = $false
$script:STACK_HTTP_PROXY = ''
$script:STACK_HTTPS_PROXY = ''

### Functions ##
function fn_bye { Write-Output "Bye bye."; exit 0; }
function fn_fail { Write-Output "Wrong option." exit 1; }
function fn_unknown { Write-Output "Unknown choice $REPLY, please choose a valid option"; }

### Sub-menu Functions ##
function fn_showLinks {
    Clear-Host
    Write-Output "Use CTRL+Click to open links or copy them:"
    Write-Output $EARNAPP_LNK
    Write-Output $HONEYGAIN_LNK
    Write-Output $IPROYALPAWNS_LNK
    Write-Output $PACKETSTREAM_LNK
    Write-Output $PEER2PROFIT_LNK
    Write-Output $TRAFFMONETIZER_LNK
    Write-Output $REPOCKET_LNK
    Write-Output $BITPING_LNK
    Read-Host -Prompt "Press enter to go back to mainmenu"
    mainmenu
}

function fn_dockerInstall {
    Clear-Host
    Write-Output "This menu item will launch a script that will attempt to install docker"
    Write-Output "Use it if you do not know how to perform the manual docker installation described at https://docs.docker.com/get-docker/ as the automatic script in some cases and depending on the OS you are using may fail to install docker correctly."
    $yn = Read-Host -Prompt "Do you wish to proceed with the Docker automatic installation Y/N?  "
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        Clear-Host
        Write-Output "Which version of Docker do you want to install?"
        Write-Output "1) Install Docker for Linux"
        Write-Output "2) Install Docker for Windows"
        $yn = Read-Host
        Switch ($Select) {
            1 {
                Write-Output "Starting Docker for linux auto installation script"
                Invoke-WebRequest https://get.docker.com -o "$SCRIPTS_DIR/get-docker.sh"  ;
                sudo sh get-docker.sh;
                Write-Output "Script completed. Docker should be installed"
                Read-Host -Prompt "Press enter to go back to mainmenu"
                mainmenu
            }
            2 {
                Write-Output "Starting Docker for Windows auto installation script"
                Invoke-WebRequest $DKINST_WIN_SRC -o "$SCRIPTS_DIR\install-docker.ps1"
                Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -Command `"cd '$SCRIPTS_DIR'; & '.\install-docker.ps1';`"" -Wait
                
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
        Clear-Host
        Write-Output "Docker unattended installation canceled. Make sure you have docker installed before proceeding with the other steps.  ";
        Read-Host -prompt "Press enter to go back to the menu";
        mainmenu;
    }
}

function fn_setupNotifications() {
    Clear-Host
    Write-Output "This step will setup notifications about containers updates using shoutrrr"
    Write-Output "Now we will configure a SHOUTRRR_URL that should looks like this <app>://<token>@<webhook> . Where <app> is one of the supported messaging apps supported by shoutrrr (We will use a private discord server as example)."
    Write-Output "For more apps and details visit https://containrrr.dev/shoutrrr/, select your desider app (service) and paste the required SHOUTRRR_URL in this script when prompted "
    Read-Host -p "Press enter to proceed and show the discord notification setup example (Remember: you can also use a different supported app, just enter the link correctly)"
    Clear-Host
    Write-Output "CREATE A NEW DISCORD SERVER, GO TO SERVER SETTINGS>INTEGRATIONS AND CREATE A WEBHOOK"
    Write-Output "Your Discord Webhook-URL will look like this: https://discordapp.com/api/webhooks/YourWebhookid/YourToken to obtain the SHOUTRRR_URL you should rearrange it to look like this: discord://yourToken@yourWebhookid"
    Read-Host -p "Press enter to continue"
    Clear-Host
    Write-Output "NOW INSERT BELOW THE LINK FOR NOTIFICATIONS using THE SAME FORMAT WRITTEN ABOVE e.g.: discord://yourToken@yourWebhookid"
    $SHOUTRRR_URL = Read-Host
    (Get-Content .\.env).replace('# SHOUTRRR_URL=yourApp:yourToken@yourWebHook', "SHOUTRRR_URL=$SHOUTRRR_URL") | Set-Content .\.env
    (Get-Content .\docker-compose.yml).replace('# - WATCHTOWER_NOTIFICATIONS=shoutrrr', "- WATCHTOWER_NOTIFICATIONS=shoutrrr") | Set-Content .\docker-compose.yml
    (Get-Content .\docker-compose.yml).replace('# - WATCHTOWER_NOTIFICATION_URL', "- WATCHTOWER_NOTIFICATION_URL") | Set-Content .\docker-compose.yml
    (Get-Content .\docker-compose.yml).replace('# - WATCHTOWER_NOTIFICATIONS_HOSTNAME', "- WATCHTOWER_NOTIFICATIONS_HOSTNAME") | Set-Content .\docker-compose.yml
    Read-Host -p "Notifications setup complete. If the link is correct, you will receive a notification for each update made on the app container images. Now press enter to continue"
    Clear-Host
}

function fn_setupApp() {
    param ($CURRENT_APP, $TYPE , $SUBTYPE
    )
    if ( "$TYPE" -eq "email" ) {
        Write-Output "Enter your $CURRENT_APP Email"
        $APP_EMAIL = Read-Host 
        (Get-Content .\.env).replace("your${CURRENT_APP}Mail", "$APP_EMAIL") | Set-Content .\.env
    
        if ("$SUBTYPE" -eq "password" ) { 
            Write-Output "Now enter your $CURRENT_APP Password"
            $APP_PASSWORD = Read-Host  
        (Get-Content .\.env).replace("your${CURRENT_APP}Pw", "$APP_PASSWORD") | Set-Content .\.env
        }
    }
    elseif ( "$TYPE" -eq "uuid" ) {
        Write-Output "generating an UUID for $CURRENT_APP"
        $SALT = "$SUBTYPE$(Get-Random)"
        $md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
        $utf8 = New-Object -TypeName System.Text.UTF8Encoding
        $UUID = [System.BitConverter]::ToString($md5.ComputeHash($utf8.GetBytes($SALT))).replace("-", "").ToLower()
        (Get-Content .\.env).replace("your${CURRENT_APP}MD5sum", "$UUID") | Set-Content .\.env
        Write-Output "Save the following link somewhere to claim your earnapp node after completing the setup and after starting the apps stack: https://earnapp.com/r/sdk-node-$UUID. A new file containing this link has been created for you"
        Write-Output "https://earnapp.com/r/sdk-node-$UUID" > ClaimEarnappNode.txt 
    }

    elseif ("$TYPE" -eq "cid" ) {
        Write-Output "Enter your $CURRENT_APP CID."
        Write-Output "You can find it going in your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
        $APP_CID = Read-Host 
        (Get-Content .\.env).replace("your${CURRENT_APP}CID", "$APP_CID") | Set-Content .\.env
    }

    elseif ("$TYPE" -eq "token") {
        Write-Output "Enter your $CURRENT_APP Token."
        Write-Output "You can find it going in your dashboard https://app.traffmonetizer.com/dashboard then -> Look for Your application token -> just insert it here (you can also copy and then paste it)"
        $APP_TOKEN = Read-Host 
        (Get-Content .\.env).replace("your${CURRENT_APP}Token", "$APP_TOKEN") | Set-Content .\.env
    }
    elseif ("$TYPE" -eq "customScript") {
        Start-Process PowerShell -Verb RunAs "-noprofile -executionpolicy bypass -Command `"cd '$pwd'; & '$SUBTYPE';`"" -wait
    }
    
    if ( $script:PROXY_CONF ) {
        if ( $script:PROXY_CONF_ALL ) {
            (Get-Content .\.env).replace("# ${CURRENT_APP}_HTTP_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "${CURRENT_APP}_HTTP_PROXY=$script:STACK_HTTP_PROXY") | Set-Content .\.env
            (Get-Content .\.env).replace("# ${CURRENT_APP}_HTTPS_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "${CURRENT_APP}_HTTPS_PROXY=$script:STACK_HTTPS_PROXY") | Set-Content .\.env
        }
        else {
            Write-Output "Insert the designed HTTP proxy to use with $CURRENT_APP (also socks5h is supported)."
            $APP_HTTP_PROXY = Read-Host 
            Write-Output "Insert the designed HTTPS proxy to use with $CURRENT_APP (you can also use the same of the HTTP proxy and also socks5h is supported)."
            $APP_HTTPS_PROXY = Read-Host 
            (Get-Content .\.env).replace("# ${CURRENT_APP}_HTTP_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "${CURRENT_APP}_HTTP_PROXY=$APP_HTTP_PROXY") | Set-Content .\.env
            (Get-Content .\.env).replace("# ${CURRENT_APP}_HTTPS_PROXY=http://proxyUsername:proxyPassword@proxy_url:proxy_port", "${CURRENT_APP}_HTTPS_PROXY=$APP_HTTPS_PROXY") | Set-Content .\.env
        }

        (Get-Content .\docker-compose.yml).replace("#- ${CURRENT_APP}_HTTP_PROXY", "- HTTP_PROXY") | Set-Content .\docker-compose.yml
        (Get-Content .\docker-compose.yml).replace("#- ${CURRENT_APP}_HTTPS_PROXY", "- HTTPS_PROXY") | Set-Content .\docker-compose.yml
        (Get-Content .\docker-compose.yml).replace("#- ${CURRENT_APP}_NO_PROXY", "- NO_PROXY") | Set-Content .\docker-compose.yml
    }
    Read-Host -p "${CURRENT_APP} configuration complete, press enter to continue to the next app"
}

function fn_setupProxy() {
    $yn = Read-Host -p "Do you wish to use a proxy? Y/N? Note that if you want to run multiple instances of the same app you will need to configure different env files each in different project folders (copy the project to multiple different folders and configure them using different proxies)"
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        Clear-Host
        Write-Output "Proxy setup started.";
        $yn = Read-Host -p "Do you wish to use the same proxy for all the apps in this stack? Y/N?"
        if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
            Write-Output "Insert the designed HTTP proxy to use. Eg: http://proxyUsername:proxyPassword@proxy_url:proxy_port or just http://proxy_url:proxy_port if auth is not needed, also socks5h is supported.";
            $script:STACK_HTTP_PROXY = Read-Host 
            Write-Output "Ok, $script:STACK_HTTP_PROXY will be used as proxy for all apps in this stack"
            Read-Host -p "Press enter to continue"
            Clear-Host
            Write-Output "Insert the designed HTTPS proxy to use (you can also use the same of the HTTP proxy), also socks5h is supported."
            $script:STACK_HTTPS_PROXY = Read-Host
            Write-Output "Ok, $script:STACK_HTTPS_PROXY will be used as secure proxy for all apps in this stack"
            Read-Host -p "Press enter to continue"
            $script:PROXY_CONF_ALL = $true
            $script:PROXY_CONF = $true
        }
        elseif ($yn -eq 'N' -or $yn -eq 'n' -or $yn -eq 'No' -or $yn -eq 'no') {
            $script:PROXY_CONF_ALL = $false
            $script:PROXY_CONF = $true
            Write-Output "Ok, later you will be asked for a proxy for each application"
            Read-Host -p "Press enter to continue"
        }
        else {
            Clear-Host
            Write-Output "Please answer yes or no."
            fn_setupProxy
        }
        # An unique name for the stack is chosen so that even if multiple stacks are started with different proxies the names do not conflict
            (Get-Content .\.env).replace("COMPOSE_PROJECT_NAME=Money4Band", "COMPOSE_PROJECT_NAME=Money4Band_$(Get-Random)") | Set-Content .\.env
    }
    elseif ($yn -eq 'N' -or $yn -eq 'n' -or $yn -eq 'No' -or $yn -eq 'no') {
        Write-Output "Ok, no proxy added to configuration."
    }
    else {
        Clear-Host
        Write-Output "Please answer yes or no."
        fn_setupProxy
    }
    
}

function fn_setupEnv {
    Clear-Host
    $yn = Read-Host -p "Do you wish to proceed with the .env file guided setup Y/N? (This will also adapt the docker-compose.yml file accordingly)"
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        Clear-Host
        if ( -Not (Select-String -Path .\.env -Pattern "DEVICE_NAME=yourDeviceName" -Quiet) ) {
            Write-Output "The current .env file appears to have already been modified. A fresh version will be downloaded and used."
            Invoke-WebRequest -OutFile '.env' $ENV_SRC;
            Invoke-WebRequest -OutFile 'docker-compose.yml' $DKCOM_SRC;
        }
        Write-Output "Beginnning env file guided setup"
        $CURRENT_APP = '';
        $DEVICE_NAME = Read-Host -prompt "PLEASE ENTER A NAME FOR YOUR DEVICE"
        (Get-Content .\.env).replace('yourDeviceName', "$DEVICE_NAME") | Set-Content .\.env

        Clear-Host
        fn_setupProxy
        Clear-Host

        Write-Output "PLEASE REGISTER ON THE PLATFORMS USING THIS LINKS, YOU'LL NEED TO ENTER SOME DATA BELOW:"
        Write-Output "Use CTRL+Click to open links or copy them:"

        #EarnApp app env setup
        $CURRENT_APP = 'EARNAPP';
        Write-Output "Go to $EARNAPP_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "uuid" "$DEVICE_NAME"


        #HoneyGain app env setup
        Clear-Host
        $CURRENT_APP = 'HONEYGAIN';
        Write-Output "Go to $HONEYGAIN_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "email" "password"

        #IPROYALPAWNS app env setup
        Clear-Host
        $CURRENT_APP = 'IPROYALPAWNS';
        Write-Output "Go to $IPROYALPAWNS_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "email" "password"


        #Peer2Profit app env setup
        Clear-Host
        $CURRENT_APP = 'PEER2PROFIT';
        Write-Output "Go to $PEER2PROFIT_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "email"

        #PacketStream app env setup
        Clear-Host
        $CURRENT_APP = 'PACKETSTREAM';
        Write-Output "Go to $PACKETSTREAM_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "cid"

        # TraffMonetizer app env setup
        Clear-Host
        $CURRENT_APP = 'TRAFFMONETIZER';
        Write-Output "Go to $TRAFFMONETIZER_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "token"

        # Repocket app env setup
        Clear-Host
        $CURRENT_APP = 'REPOCKET';
        Write-Output "Go to $REPOCKET_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "email" "password"
    
        # Bitping app env setup
        Clear-Host
        $CURRENT_APP = 'BITPING';
        Write-Output "Go to $BITPING_LNK and register"
        Read-Host -prompt "When done, press enter to continue"
        fn_setupApp "$CURRENT_APP" "customScript" "$SCRIPTS_DIR\bitpingSetup.ps1"
        

        # Notifications setup
        Clear-Host
        $yn = Read-Host -p "Do you wish to setup notifications about apps images updates (Yes to recieve notifications and apply updates, No to just silently apply updates) Y/N?  "
        if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
            fn_setupNotifications 
        }
        elseif ($yn -eq 'N' -or $yn -eq 'n' -or $yn -eq 'No' -or $yn -eq 'no') {
            Write-Output "Noted: all updates will be applied automatically and silently"
        }
        else {
            Write-Output "Please answer yes or no."
            fn_setupNotifications 
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
    Clear-Host
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

function fn_stopStack() {
    Clear-Host
    Write-Output "This menu item will stop all the apps and delete the docker stack previously created using the configured .env file and the docker-compose.yml file."
    Write-Output "You don't need to use this command to temporarily pause apps or to update the stack. Use it only in case of uninstallation!"
    $yn = Read-Host -prompt "Do you wish to proceed Y/N?"
    if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ) {
        docker compose down
        Write-Output "All Apps stopped and stack deleted.";
        Read-Host "Now press enter to go back to the menu";
        mainmenu;
    }
    else {
        Write-Output "Docker stack removal canceled.";
        Read-Host -prompt "Press Enter to go back to mainmenu";
        mainmenu; ;
    }

}

function fn_resetEnv {
    Write-Output "Now a fresh env file will be downloaded and will need to be configured to be used again"
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

function fn_resetDockerCompose {
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
    Clear-Host
    Write-Output "Select an option and press Enter: "
    Write-Output "1) Show apps' links to register or go to dashboard"
    Write-Output "2) Install Docker"
    Write-Output "3) Setup .env file"
    Write-Output "4) Start apps stack"
    Write-Output "5) Stop apps stack"
    Write-Output "6) Reset .env File"
    Write-Output "7) Reset docker-compose.yml file"
    Write-Output "8) Exit"
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
                fn_stopStack
            }
            6 {
                fn_resetEnv
            }
            7 {
                fn_resetDockerCompose
            }
            8 {
                fn_bye
            }
            DEFAULT {
                fn_unknown
            }
        }
    }
    While ($Select -ne 8)
}

### Startup ##
mainmenu