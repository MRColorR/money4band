import os
import sys
import argparse
import logging
import hashlib
import uuid
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

def generate_md5_uuid(device_name: str, length: int) -> str:
    """
    Generate a MD5 UUID of the specified length.

    Arguments:
    device_name -- the device name to include in the UUID generation
    length -- the length of the UUID to generate
    """
    if length <= 0:
        raise ValueError("Length must be a positive integer")
    
    hash_input = (device_name + uuid.uuid4().hex).encode('utf-8')
    md5_hash = hashlib.md5(hash_input).hexdigest()
    while len(md5_hash) < length:
        hash_input = (md5_hash + uuid.uuid4().hex).encode('utf-8')
        md5_hash += hashlib.md5(hash_input).hexdigest()
    return md5_hash[:length]

def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function to generate and display a UUID.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    """
    # Example usage for generating a UUID
    device_name = "example_device"
    uuid_length = 32  # Change as needed
    generated_uuid = generate_md5_uuid(device_name, uuid_length)
    print(f"Generated UUID: {generated_uuid}")

if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the UUID generator module standalone.')
    parser.add_argument('--app-config', type=str, required=True, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=False, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=False, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default=f"{script_name}.log", help='Set the logging file name')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=log_level
    )

    logging.info(f"Starting {script_name} script...")

    try:
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config)
        logging.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
