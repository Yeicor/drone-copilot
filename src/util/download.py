import os

import requests
from kivy import Logger


def download_or_cache(url: str, cache_dir: str = os.path.join(os.path.dirname(__file__), '.cache')):
    """Downloads a file from a URL to a directory. If the file already exists, it will be skipped.
    :return: The path to the downloaded file."""
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    filename = url.split('/')[-1]
    filepath = os.path.join(cache_dir, filename)
    if os.path.exists(filepath):
        Logger.info(f'download_or_cache: File already exists: {filepath}')
        return filepath

    download(url, filepath)

    return filepath


def download(url, filepath):
    """Downloads a file from a URL to a file path."""
    Logger.info(f'download: Downloading {url} to {filepath}...')
    with open(filepath, 'wb') as f:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        # Write response data to file
        for block in response.iter_content(4096):
            f.write(block)
    Logger.info(f'download: File downloaded to: {filepath}')
