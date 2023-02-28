#!/bin/pwsh
Write-Output "First of all make sure that you have already run the runme.ps1 script and that you have registered to the various apps with the links provided."
Read-Host -prompt "if you have already performed these actions, press enter to continue"
Write-Output "To configure this app we will need to start an interactive container in a new terminal (so Docker needs to be already installed)."
Write-Output "Then when prompted enter your bitping email and password in it. Hit enter and then close it (or CTRL+C it) as we will not need it anymore"
Read-Host -prompt "When ready to start, press enter to continue"
docker run --rm -it -v ${PWD}/.data/.bitping/:/root/.bitping bitping/bitping-node:latest ;
if ($LASTEXITCODE -eq 0) {
    Write-Output "ok"
  }
Write-Output "Bitping interactive container closed. Bitping config should be complete now."
Start-Sleep -Seconds 3