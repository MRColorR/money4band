set-executionpolicy -scope CurrentUser -executionPolicy Bypass -Force
If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
{
  # Relaunch as an elevated process:
  Start-Process powershell.exe "-File",('"{0}"' -f $MyInvocation.MyCommand.Path) -Verb RunAs
  exit
}
$RESOURCES_DIR = (get-item $PWD ).parent.FullName
$SCRIPTS_DIR = "$RESOURCES_DIR\.scripts"
$FILES_DIR = "$RESOURCES_DIR\.files"
function installDoker {
    Write-Output "Downloading the Docker exe"
            Invoke-WebRequest -Uri https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe -OutFile DockerInstaller.exe -UseBasicParsing
            Write-Output "Download Completed"

            Write-Output "Installing Docker please wait..."
            start-process .\DockerInstaller.exe -Wait -NoNewWindow -ArgumentList "install --accept-license --quiet"
            Copy-Item "$FILES_DIR\docker-default-settings.json" -Destination "$env:AppData\Docker\settings.json"
            Write-Output "Docker Installed successfully"
            Read-Host "You must reboot the sytem to continue. After reboot re-run the script and proceed with the next steps"
            Restart-Computer -Confirm 
}

$ProgressPreference = 'Continue'

    $wsl = Get-WindowsOptionalFeature -FeatureName Microsoft-Windows-Subsystem-Linux -Online

    if($wsl.State -eq "Enabled") {
       
        Write-Output "WSL is enabled."

        if ([Environment]::Is64BitOperatingSystem)
        {
            Write-Output "System is x64. Need to update Linux kernel..."
            if (-not (Test-Path wsl_update_x64.msi))
            {
                Write-Output "Downloading Linux kernel update package..."
                Invoke-WebRequest -OutFile wsl_update_x64.msi https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
            }
            Write-Output "Installing Linux kernel update package..."
            Start-Process msiexec.exe -Wait -ArgumentList '/I wsl_update_x64.msi /quiet'
            Write-Output "Linux kernel update package installed."
        }

        Write-Output "WSL is enabled. Setting it to WSL2"
        wsl --set-default-version 2
        
        if(Test-Path 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -PathType Leaf){
            $yn=Read-Host -Prompt 'It seems Docker is already installed in your system. Do you want to reinstall/repair it Y/N?'
            if ($yn -eq 'Y' -or $yn -eq 'y' -or $yn -eq 'Yes' -or $yn -eq 'yes' ){
                installDoker
            } else {
                Write-Output 'Docker installation/repair  canceled.'
                Write-Output 'If docker was already correctly installed on your system you should be able to proceed with the next steps anyway'
            }
        } else {
            Write-Output 'It seems that Docker is not installed on the system, the installation is starting'
            installDoker
        }
        
            
        
    
        
    } 
    else {
        Write-Output "WSL is disabled."
        Write-Output "Enabling WSL2 feature now. You will then restart your machine and execute the install docker option again to complete the docker installation"
    
        & cmd /c 'dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart'
        & cmd /c 'dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart'
        Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
        Start-Sleep 30
        Write-Output "WSL is enabled now reboot the system and re-run the script to continue the docker installation."
    }