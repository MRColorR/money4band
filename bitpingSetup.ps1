#!/bin/pwsh
echo "First of all make sure that you have already run the runme.ps1 script and that you have registered to the various apps with the links provided."
Read-Host -prompt "if you have already performed these actions, press any key to continue"
echo "To configure bitping we will need to start an interactive container (so Docker needs to be already installed)."
echo "Then when prompted enter your bitping email and password in it. Hit enter and then close it (or CTRL+C it) as we will not need it anymore"
Read-Host -prompt "When ready to start, press any key to continue"
docker run --rm -it -v ${PWD}/.data/.bitping/:/root/.bitping bitping/bitping-node:latest
echo "Bitping interactive container closed. Bitping config should be complete now."