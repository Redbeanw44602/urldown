import os
import re
import json

import requests

import config

from util.internal import __assert__
from util.internal import __check_response__
from util.internal import __check_object__
from util.m3u8 import download as download_m3u8

from tool.__base__ import URLHandler


class TCPlayDetail:
    file_id: str = None
    app_id: str = None
    p_sign: str = None

    video_name: str = None

    def is_valid(self) -> bool:
        return self.file_id and self.app_id and self.p_sign and self.video_name

    def build_play_info_url(self) -> str:
        return f'http://playvideo.qcloud.com/getplayinfo/v4/{self.app_id}/{self.file_id}?psign={self.p_sign}'

    def get_play_info(self) -> dict:
        response = requests.get(self.build_play_info_url(), timeout=config.REQUESTS_TIMEOUT)
        __check_response__(response)
        result = json.loads(response.content)
        __check_object__(result)
        __assert__(result['code'] == 0, f'Unable to get play info, message = "{result['message']}"')
        return result


class IMacCastURLHandler(URLHandler):
    def __init__(self):
        pass

    def get_name(self) -> str:
        return 'IMAC-CAST CloudClass'

    def get_supported_url_patterns(self) -> list[str]:
        return [r'^http://www\.imac-cast\.org\.cn/View/CloudResource/CloudClassDetail\.aspx\?id=']

    def get_play_detail(self, url: str) -> TCPlayDetail:
        __assert__(
            os.path.exists('imac-cast.cookie'),
            'Please provide cookies (imac-cast.cookie), otherwise the download cannot be processed.',
        )
        cookie = None
        with open('imac-cast.cookie', 'r') as storaged_cookies:
            cookie = storaged_cookies.read()
        response = requests.get(url, headers={'Cookie': cookie}, timeout=config.REQUESTS_TIMEOUT)
        __check_response__(response)
        response = response.content.decode()
        script_raw = None
        title_raw = None
        for line in response.split('\n'):
            if line.find('var videoid = TCPlayer') != -1:
                script_raw = line
            if line.find('vip_ico_vd') != -1:
                title_raw = line
            if script_raw and title_raw:
                break
        __assert__(script_raw, 'Resource information not found, login has expired.')
        __assert__(title_raw, 'Unable to get resource name.')
        result = TCPlayDetail()
        result.file_id = re.search(r'(?<=fileID: ")(.+)(?=", appID)', script_raw).group()
        result.app_id = re.search(r'(?<=appID: ")(.+)(?=",  psign)', script_raw).group()
        result.p_sign = re.search(r'(?<=psign: ")(.+)(?="\})', script_raw).group()
        result.video_name = re.search(r'(?<=</span>)(.+)(?=</h1>)', title_raw).group()
        __assert__(result.is_valid(), 'Unable to get resource information.')
        return result

    def handle(self, url: str):
        play_detail = self.get_play_detail(url)
        print(f'Target file: {play_detail.video_name} ({play_detail.file_id})')
        play_info = play_detail.get_play_info()
        streaming_info = play_info['media']['streamingInfo']
        __check_object__(streaming_info)
        drm_output = streaming_info['drmOutput']
        __check_object__(drm_output)
        __assert__(
            len(drm_output) == 1, 'More than one drm output, maybe we need to make a choice.'
        )
        print('Successfully obtained the m3u8 file link.')

        download_m3u8(drm_output[0]['url'], play_detail.video_name, streaming_info['drmToken'])
