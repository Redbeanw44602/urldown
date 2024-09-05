import os
import urllib3
import time

from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
import config


def download(url, save_path):
    # if os.path.exists(save_path):  # for debug use only
    #     return True

    http = urllib3.PoolManager()
    attempt = 0
    max_retries = 3

    while attempt < max_retries:
        try:
            response = http.request(
                'GET', url, preload_content=False, headers={'User-Agent': config.URLLIB_UA}
            )

            if response.status != 200:
                print(f'\nUnable to download: [{response.status}] {url}')
                response.release_conn()
                return False

            with open(save_path, 'wb') as out_file:
                while True:
                    data = response.read(65536)  # or a different chunk size
                    if not data:
                        break
                    out_file.write(data)
            response.release_conn()
            break
        except Exception as e:
            print(f'Download failed: {e}. Retrying in 5 seconds...')
            if os.path.exists(save_path):
                os.remove(save_path)
            if attempt == max_retries:
                raise e
            attempt += 1
            time.sleep(5)
    return True


def get_base_url(url):
    """remove filename and query parameter from url"""

    url = urlparse(url)
    return urlunparse(
        (url.scheme, url.netloc, '/'.join(url.path.split('/')[:-1]) + '/', '', '', '')
    )


def add_query_param(url, param_name, param_value):
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query[param_name] = param_value
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)
