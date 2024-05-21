import os
import requests
import logging
import argparse
from typing import Any

def download_file(url: str, dest_path: str):
    """
    Download a file from a given URL and save it to the specified destination path.

    Parameters:
    url (str): The URL of the file to download.
    dest_path (str): The local path where the file will be saved.

    Raises:
    requests.RequestException: If there is an issue with the request.
    """
    try:
        logging.info(f"Starting download from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(dest_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        logging.info(f"File downloaded successfully from {url} to {dest_path}")
    except requests.RequestException as e:
        logging.error(f"An error occurred while downloading the file from {url}: {str(e)}")
        raise

if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description=f"Run the {script_name} module standalone.")
    parser.add_argument('--url', type=str, required=True, help='URL of the file to download')
    parser.add_argument('--dest-path', type=str, required=True, help='Destination path where the file will be saved')
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
        # Call the download_file function
        download_file(args.url, args.dest_path)
        logging.info(f"{script_name} script completed successfully")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
