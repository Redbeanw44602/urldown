import time
import json

from urllib.parse import urlparse

import requests

import config

from util.internal import __assert__
from util.internal import __check_response__
from util.internal import __check_object__

from tool.__base__ import URLHandler


class TencentMeetingURLHandler(URLHandler):
    def __init__(self):
        pass

    def get_name(self) -> str:
        return 'TencentMeeting Replay (direct-link only)'

    def get_supported_url_patterns(self) -> list[str]:
        return [r'^https://meeting\.tencent\.com/live/']

    def get_query_replay_info_url(self):
        return (
            r'https://meeting.tencent.com/wemeet-tapi/liveportal/v2/query_meeting_room_live_replay_info'
            r'?c_os=web&c_os_version=Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/'
            r'537.36%20(KHTML,%20like%20Gecko)%20Chrome/119.0.0.0%20Safari/537.36%20Edg/119.0.0.0&c_os_'
            r'model=web&c_timestamp=<TimeStamp>&c_instance_id=5&c_nonce=iHnReNN58&c_app_uid=null&c_app_'
            r'id=null&c_app_version=&c_token=null&c_platform=0'
        ).replace('<TimeStamp>', str(round(time.time() * 1000)))

    def get_replay_info(self, live_id: str, room_id: str | None, password: str | None) -> dict:
        response = requests.post(
            self.get_query_replay_info_url(),
            timeout=config.REQUESTS_TIMEOUT,
            json={
                'live_password': password if password else '',
                'media_room_id': room_id if room_id else '',
                'meeting_id': live_id,
            },
        )
        __check_response__(response)
        info = None
        try:
            info = json.loads(response.content)
        except Exception:
            pass
        __check_object__(info)
        __assert__(info['code'] == 0, f'Query replay info failed: {info['msg']}')
        return info

    def handle(self, url: str):
        print('Is this meeting password protected? If yes please enter:')
        password = input('(optional) > ')
        live_url = urlparse(url)
        live_id = live_url.path.removeprefix('/live/')
        room_ids = set()
        __assert__(live_id.isnumeric(), 'Not a valid live id.')
        for i in live_url.query.split('&'):
            d = i.split('=')
            if d[0] == 'room_id':
                room_ids.add(d[1])
        print(f'Target live id: {live_id}')
        if len(room_ids) == 0:
            print('Live room id is not specified, try to get...')
            info = self.get_replay_info(live_id, None, password)
            for i in info['live_replay_info']:
                room_ids.add(i['room_id'])
            __assert__(len(room_ids) > 0, 'No meeting room founded!')
        for i in room_ids:
            print(f'Live room id: {i}')
            info = self.get_replay_info(live_id, i, password)
            count = 0
            for j in info['live_replay_info']:
                count += 1
                print(f'--> paragraph {count}: {'<file_state_error>' if (
                    j['replay_file_state'] != 0 or j['replay_url_long'] == '-') else j['replay_url_long']}')
        print('Completed.')
