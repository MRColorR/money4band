#!/bin/bash
echo "First of all make sure that you have already run the runme.sh script and that you have registered to the various apps with the links provided.
 and that you have already run the setup of the env file through the runme.sh script or done it manually."$'\n'
read -n 1 -s -r -p "if you have already performed these actions, press any key to continue"$'\n'
echo "To configure bitping we will need to start an interactive container (so Docker needs to be already installed), then wait and enter your bitping email and password in it when prompted , hit enter and then close it (or CTRL+C it) as we will not need it anymore"$'\n'
read -n 1 -s -r -p "When ready to start, press any key to continue"$'\n'
sudo docker run --rm -it -v ${PWD}/.data/.bitping/:/root/.bitping bitping/bitping-node:latest