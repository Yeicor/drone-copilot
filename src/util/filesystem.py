import os

import requests
from kivy import Logger


def source_dir() -> str:
    """Returns the path to the project's './src/' directory.

    This directory should be readable and writable on any deployment platform.

    Only the non-python files inside this directory are available in production.

    :return: The absolute path to the project's './src/' directory."""
    return os.path.dirname(os.path.dirname(__file__))  # __file__ is already an absolute path


def source(*rel_name_parts: str) -> str:
    """Finds a file path relative to the project's './src/' directory.
    The file does not need to exist already.

    :param rel_name_parts: The relative path to the file, as a string or a list of strings.
    :return: The absolute path to the file."""
    return os.path.join(source_dir(), *rel_name_parts)


def cache(*rel_name_parts: str) -> str:
    """Returns the path to the project's './src/.cache/' directory.

    This directory should be readable and writable on any deployment platform.

    :return: The absolute path to the project's './src/.cache/' directory.

    :param rel_name_parts: The relative path to the file inside the cache, as a string or a list of strings.
    :return: The absolute path to the file."""
    return source('.cache', *rel_name_parts)


def download_or_cache(url: str, cache_dir: str = cache()) -> str:
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


def download(url, filepath, ):
    """Downloads a file from a URL to a file path (asynchronous callbacks)."""
    Logger.info(f'download: Downloading {url} to {filepath}...')
    with open(filepath, 'wb') as f:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        # Write response data to file
        for block in response.iter_content(4096):
            f.write(block)
    Logger.info(f'download: File downloaded to: {filepath}')
