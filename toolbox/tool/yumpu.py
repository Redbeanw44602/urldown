import re
import json
import os
import shutil

import requests

import config

from util.internal import __assert__
from util.internal import __check_response__
from util.string import sanitize_filename
from util.network import download

from tool.__base__ import URLHandler


class YumPuURLHandler(URLHandler):
    def __init__(self):
        pass

    def get_name(self) -> str:
        return 'YumPu Preview'

    def get_supported_url_patterns(self) -> list[str]:
        return [r'https://www\.yumpu\.com/[^/]+/document/read/']

    def handle(self, url: str):
        matched = re.match(r'https://www\.yumpu\.com/[^/]+/document/read/(\d+)(/.*)?', url)
        __assert__(matched, 'Unable to get book id.')
        book_id = matched.group(1)
        response = requests.get(
            'https://www.yumpu.com/en/document/json/' + book_id,
            timeout=config.REQUESTS_TIMEOUT,
        )
        __check_response__(response)
        meta_info = json.loads(response.content)
        __assert__('document' in meta_info, 'failed to get book information.')
        book_name = sanitize_filename(meta_info['document']['title'])
        page_count = len(meta_info['document']['pages'])
        __assert__(book_name, 'invalid book name')
        print(f'Target book: {book_name} ({book_id})')
        print(f'  Pages: {page_count}')
        image_base = meta_info['document']['base_path']
        image_title = meta_info['document']['images']['title']
        image_dimension = meta_info['document']['images']['dimensions']['big']
        image_quality = meta_info['document']['images']['quality']
        __assert__(image_base, 'Invalid image base.')
        __assert__(image_title, 'Invalid image title.')
        __assert__(image_dimension, 'Invalid image dimension.')
        __assert__(image_quality, 'Invalid image quality.')
        file_format = image_title[image_title.find('.') :]
        if os.path.exists(book_name):
            shutil.rmtree(book_name)
        os.mkdir(book_name)
        for tmp in meta_info['document']['pages']:
            page = tmp['nr']
            print(f'\rDownloading... ({page}/{page_count})', end='')
            if not download(
                f'{image_base}{page}/{image_dimension}/{image_title}?quality={image_quality}',
                f'{book_name}/{page}{file_format}',
            ):
                return
        print('\nCompleted.')
