import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def listFilesUrl(url, username, password, ext=''):
    page = requests.get(url, auth=(username, password)).text
    soup = BeautifulSoup(page, 'html.parser')
    return [url + '/' + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]


def fetchUrl(url_file, username, password, filename=None):

    downloaded = False

    if filename is None:
        filename = os.path.basename(urlparse(url_file).path)
    print(f'\tProcessing {filename} ...')

    # writing the file locally
    r = requests.get(url_file, auth=(username, password))
    if r.status_code == 200:
        with open(filename, 'wb') as out:
            for bits in r.iter_content():
                out.write(bits)
        downloaded = not(downloaded)
    else:
        print(f'\t\t\033[91mCouldnt download {url_file}\033[0m')

    return downloaded