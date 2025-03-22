import os
import argparse
import logging
import json
from typing import Dict, Any


def write_json(data: Dict[str, Any], filename: str) -> None:
    """
    Write data to a JSON file.

    Arguments:
    data -- the data to write
    filename -- the file to write the data to
    """
    try:
        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        logging.info(f"Data written to {filename} successfully!")
    except Exception as e:
        logging.error(f"Error writing to {filename}: {e}")
        raise


if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Write data to a JSON file.')
    parser.add_argument('--data', type=str, required=True,
                        help='The data to write in JSON format')
    parser.add_argument('--filename', type=str, required=True,
                        help='The filename to write the data to')
    parser.add_argument('--log-dir', default=os.path.join(script_dir,
                        'logs'), help='Set the logging directory')
    parser.add_argument(
        '--log-file', default=f"{script_name}.log", help='Set the logging file name')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING',
                        'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
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
        # Load the data from the command-line argument
        data = json.loads(args.data)

        # Write data to the specified filename
        write_json(data, args.filename)

        logging.info(f"{script_name} script completed successfully")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
