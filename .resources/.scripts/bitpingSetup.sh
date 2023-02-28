#!/bin/bash
echo "First of all make sure that you have already run the runme.sh script and that you have registered to the various apps with the links provided."
read -n 1 -s -r -p "if you have already performed these actions, press any key to continue"$'\n'
echo "To configure this app we will need to start an interactive container in a new terminal (so Docker needs to be already installed)."
echo "Then when prompted enter your bitping email and password in it. Hit enter and then close it (or CTRL+C it) as we will not need it anymore"$'\n'
read -n 1 -s -r -p "When ready to start, press any key to continue"$'\n'
BITPING_DATA_PATH="${PWD}/.data/.bitping/"
echo $BITPING_DATA_PATH
sudo docker run --rm -it -v "$BITPING_DATA_PATH":/root/.bitping bitping/bitping-node:latest
echo "Bitping interactive container closed. Bitping config should be complete now."