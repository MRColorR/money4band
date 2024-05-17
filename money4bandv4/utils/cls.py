import os
import time

def cls():
    """
    Clear the console.
    """
    os.system('cls' if os.name=='nt' else 'clear')

if __name__ == "__main__":
    try:
        # Test the function
        print("Testing cls() function in 3 seconds...")
        time.sleep(3)
        cls()
    except Exception as e:
        print("Error:", e)