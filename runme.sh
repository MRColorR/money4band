#!/usr/bin/env bash

mainmenu() {
    echo -ne "
MAIN MENU
1) Setup .env file
0) Exit
Choose an option:  "
    read -r ans
    case $ans in
    #Go to .env file setup
    1)
        submenu
        mainmenu
        ;;
    #exit from the script
    0)
        echo "Bye bye."
        exit 0
        ;;
    #Default if no case match 
    *)
        echo "Wrong option."
        exit 1
        ;;
    esac
}

submenu() {
    echo -ne "
ENV FILE SETUP MENU
1) SUBCMD1
2) Go Back to Main Menu
0) Exit
Choose an option:  "
    read -r ans
    case $ans in
    1)
        sub-submenu
        submenu
        ;;
    2)
        menu
        ;;
    0)
        echo "Bye bye."
        exit 0
        ;;
    *)
        echo "Wrong option."
        exit 1
        ;;
    esac
}


mainmenu