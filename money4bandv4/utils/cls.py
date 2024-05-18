import os
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

        # Start logging
        logging.basicConfig(filename=f"{script_name}.log",  format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level="DEBUG")


        # Test the function
        msg = f"Testing {script_name} function in 3 seconds..."
        print(msg)
        logging.info(msg)
        time.sleep(3)
        cls()
        msg = "{script_name} test complete"
        print(msg)
        logging.info(msg)