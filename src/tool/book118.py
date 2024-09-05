import re
import os
import shutil
import json
import time

import requests

import config

from util.internal import __assert__
from util.internal import __check_response__
from util.internal import __check_object__
from util.string import sanitize_filename
from util.network import download

from tool.__base__ import URLHandler


class Book118URLHandler(URLHandler):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return 'Book118 Preview (ppt/xls is not supported)'

    def get_supported_url_patterns(self) -> list[str]:
        return [r'^https://max\.book118\.com/html/']

    def get_preview_download_urls(
        self, book_id: str, view_token: str, start_page: int
    ) -> dict:  # page_id <-> url, kv
        response = requests.get(
            f'https://openapi.book118.com/getPreview.html?&project_id=1&aid={book_id}&view_token={view_token}&page={start_page}',
            timeout=config.REQUESTS_TIMEOUT,
        )
        time.sleep(3)  # openapi has throttle
        __check_response__(response)
        response = response.content.decode()
        response = response.removeprefix('jsonpReturn(').removesuffix(');')
        response = json.loads(response)
        # print(response)
        __check_object__(response)
        __assert__(
            response['status'] == 200,
            f'Failed to get preview, server response: \n{json.dumps(response)}',
        )
        for i in response['data']:
            response['data'][i] = 'https:' + response['data'][i]
        return response['data']

    def handle(self, url: str):
        response = requests.get(url, timeout=config.REQUESTS_TIMEOUT)
        __check_response__(response)
        response = response.content.decode()
        book_detail = response[response.find('base.detail = {') :]
        book_id = re.search('(?<=aid: )(.+)(?=, //解密后的id)', book_detail).group()
        title = sanitize_filename(re.search("(?<=title: ')(.+)(?=',)", book_detail).group())
        view_token = re.search("(?<=view_token: ')(.+)(?=')", book_detail).group()
        real_page_count = int(re.search('(?<=actual_page: )(.+)(?=,)', book_detail).group())
        prevable_page_count = int(re.search('(?<=preview_page: )(.+)(?=,)', book_detail).group())
        print(f'Target book: {title} ({book_id})')
        print(f'  Previewable pages: {prevable_page_count}/{real_page_count}')
        current_page_id = 1
        if os.path.exists(title):
            shutil.rmtree(title)
        os.mkdir(title)
        while current_page_id <= prevable_page_count:
            time.sleep
            page_id_to_url = self.get_preview_download_urls(book_id, view_token, current_page_id)
            for page_id in page_id_to_url:
                print(
                    f'\rDownloading... ({current_page_id}/{prevable_page_count})',
                    end='',
                )
                if not download(page_id_to_url[page_id], f'{title}/{page_id}.png'):
                    return
                current_page_id = int(page_id) + 1
        print('\nCompleted.')
