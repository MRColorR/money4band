import argparse
import json
import logging
import os
import shutil


def reset_config(src_path: str, dest_path: str) -> None:
    """
    Resets a configuration file by copying from the source path to the destination path.

    Arguments:
    src_path -- the source file path
    dest_path -- the destination file path
    """
    try:
        # Configure logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Starting the process of resetting {os.path.basename(dest_path)}..."
        )

        # Check if source file exists
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source file {src_path} does not exist.")

        # Create destination directory if it does not exist
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)

        # Copy the file
        shutil.copyfile(src_path, dest_path)
        logger.info(f"Successfully copied {src_path} to {dest_path}.")

    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except PermissionError as e:
        logger.error(f"Permission denied: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise


def main(
    app_config_path: str,
    m4b_config_path: str,
    user_config_path: str,
    src_path: str = "./template/user-config.json",
    dest_path: str = "./config/user-config.json",
) -> None:
    """
    Main function to call the reset_config function.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    src_path -- the source file path
    dest_path -- the destination file path
    """
    reset_config(src_path=src_path, dest_path=dest_path)


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the module standalone.")
    parser.add_argument(
        "--app-config", type=str, required=False, help="Path to app_config JSON file"
    )
    parser.add_argument(
        "--m4b-config", type=str, required=False, help="Path to m4b_config JSON file"
    )
    parser.add_argument(
        "--user-config", type=str, required=False, help="Path to user_config JSON file"
    )
    parser.add_argument(
        "--log-dir",
        default=os.path.join(script_dir, "logs"),
        help="Set the logging directory",
    )
    parser.add_argument(
        "--log-file", default=f"{script_name}.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--src-path",
        type=str,
        default="./template/user-config.json",
        help="Set the source file path",
    )
    parser.add_argument(
        "--dest-path",
        type=str,
        default="./config/user-config.json",
        help="Set the destination file path",
    )
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    logging.info(f"Starting {script_name} script...")

    try:
        main(
            app_config_path=args.app_config,
            m4b_config_path=args.m4b_config,
            user_config_path=args.user_config,
            src_path=args.src_path,
            dest_path=args.dest_path,
        )
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
