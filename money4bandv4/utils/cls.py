import os
import argparse
import logging
import time

def cls():
    """
    Clear the console.
    """
    os.system('cls' if os.name=='nt' else 'clear')

if __name__ == "__main__":
        # Get the script absolute path and name
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_name = os.path.basename(__file__)

        # Parse command-line arguments
        parser = argparse.ArgumentParser(description=f"Run the {script_name} module standalone.")
        parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
        parser.add_argument('--log-file', default=f"{script_name}.log", help='Set the logging file name')
        args = parser.parse_args()

        # Start logging
        os.makedirs(args.log_dir, exist_ok=True)
        logging.basicConfig(filename=os.path.join(args.log_dir, args.log_file),  format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level="DEBUG")

        # Test the function
        msg = f"Testing {script_name} function in 3 seconds..."
        print(msg)
        logging.info(msg)
        
        time.sleep(3)
        cls()

        msg = f"{script_name} test complete"
        print(msg)
        logging.info(msg)