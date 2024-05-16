import os
import json
import time
import logging
import argparse
from typing import Dict, Any
import locale

# Get the script absolute path or use current directory 
script_dir = os.path.dirname(os.path.realpath(__file__))

# Get the default directories
default_log_dir = os.path.join(script_dir, 'logs')
default_config_dir = os.path.join(script_dir, 'config')
default_apps_dir = os.path.join(script_dir, 'apps')
default_utils_dir = os.path.join(script_dir, 'utils')
default_requirements_path = os.path.join(script_dir, 'requirements.toml')

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Run the script.')
parser.add_argument('--config-dir', default=default_config_dir, help='Set the config directory')
parser.add_argument('--config-m4b-file', default='m4b-config.json', help='Set the m4b  config file name')
parser.add_argument('--config-usr-file', default='usr-config.json', help='Set  the user config file name')
parser.add_argument('--config-app-file', default='app-config.json', help='Set the apps config file name')
parser.add_argument('--apps-dir', default=default_apps_dir, help='Set the apps directory')
parser.add_argument('--utils-dir', default=default_utils_dir, help='Set the utils directory')
parser.add_argument('--requirements-path', default=default_requirements_path, help='Set the requirements path')
parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
parser.add_argument('--log-dir', default=default_log_dir, help='Set the logging directory')
parser.add_argument('--log-file', default='m4b.log', help='Set the logging file name')
args = parser.parse_args()

# Address possible locale issues that uses different notations for decimal numbers and so on
locale.setlocale(locale.LC_ALL, 'C')

# Set logging level based on command-line arguments
log_level = getattr(logging, args.log_level.upper(), None)
if not isinstance(log_level, int):
    raise ValueError(f'Invalid log level: {args.log_level}')

# Setup logging reporting date time, error level and message
os.makedirs(args.log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(args.log_dir, args.log_file), format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=log_level)

# Load config variables from the config file
def load_config(config_file_path: str) -> Dict[str, Any]:
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
        logging.info(f"Successfully loaded config from {config_file_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Config file {config_file_path} not found.")
        raise
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {config_file_path}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred when loading {config_file_path}: {str(e)}")
        raise


def main():
    
    m4b_config = load_config(os.path.join(args.config_dir, args.config_m4b_file))
    # Add code here to use the config...

if __name__ == '__main__':
    main()
