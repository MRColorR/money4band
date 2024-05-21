import requests


import logging


def download_file(url: str, dest_path: str):
    """Download a file from a given URL and save it to the specified destination path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(dest_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        logging.info(f"File downloaded successfully from {url}")
    except requests.RequestException as e:
        logging.error(f"An error occurred while downloading the file from {url}: {str(e)}")
        raise