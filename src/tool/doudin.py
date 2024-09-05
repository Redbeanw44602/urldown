import re
import os
import shutil

import requests

import config

from util.internal import __check_response__
from util.string import sanitize_filename
from util.network import download

from tool.__base__ import URLHandler


class DoudinURLHandler(URLHandler):
    def __init__(self):
        pass

    def get_name(self) -> str:
        return 'DouDin Preview'

    def get_supported_url_patterns(self) -> list[str]:
        return [r'^https://www\.docin\.com/p-']

    def handle(self, url: str):
        response = requests.get(
            url, headers={'User-Agent': config.REQUESTS_UA}, timeout=config.REQUESTS_TIMEOUT
        )
        __check_response__(response)
        response = response.content.decode()
        book_detail = response[response.find('var readerConfig = {') :]
        page_count = int(re.search(r'(?<=allPage:)(.+)(?=,)', book_detail).group())
        product_id = re.search(r'(?<=productId:)(.+)(?=,)', book_detail).group()
        token = re.search(r'(?<=flash_param_hzq:")(.+)(?=",)', book_detail).group()
        title = sanitize_filename(re.search(r'(?<=productName:")(.+)(?=",)', book_detail).group())
        print(f'Target book: {title} ({product_id})')
        print(f'  Pages: {page_count}')
        if os.path.exists(title):
            shutil.rmtree(title)
        os.mkdir(title)
        for tmp in range(page_count):
            current_page = tmp + 1
            print(f'\rDownloading... ({current_page}/{page_count})', end='')
            if not download(
                f'https://docimg1.docin.com/docinpic.jsp?file={product_id}&width=1600&pageno={current_page}&sid={token}',
                f'{title}/{current_page}.png',
            ):
                return
        print('\nCompleted.')
