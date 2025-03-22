import os
import argparse
import logging


def cls():
    """
    Clear the console.
    """
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
        logging.info("Console cleared successfully")
    except Exception as e:
        logging.error(f"Error clearing console: {str(e)}")
        raise


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description=f"Run the {script_name} module standalone.")
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

    # Test the function
    logging.info(f"Testing {script_name} function...")
    cls()
    logging.info(f"{script_name} test complete")
