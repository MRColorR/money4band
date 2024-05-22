import os
import shutil


def main(app_config:dict=None,m4b_config:dict=None) -> None:
    shutil.copyfile('./template/user-config.json', './config/user-config.json')


