import time
import sys
import os
import shutil
import json
import re
from urllib.parse import urlparse

import requests

QUERY_REPLAY_INFO_API = 'https://meeting.tencent.com/wemeet-tapi/liveportal/v2/query_meeting_room_live_replay_info?c_os=web&c_os_version=Mozilla/5.0%%20(Windows%%20NT%%2010.0;%%20Win64;%%20x64)%%20AppleWebKit/537.36%%20(KHTML,%%20like%%20Gecko)%%20Chrome/119.0.0.0%%20Safari/537.36%%20Edg/119.0.0.0&c_os_model=web&c_timestamp=%s&c_instance_id=5&c_nonce=iHnReNN58&c_app_uid=null&c_app_id=null&c_app_version=&c_token=null&c_platform=0'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'

REQUESTS_TIMEOUT = 15


def _do_assert(cond: bool, msg: str = None):
    if cond:
        return
    if msg:
        print(msg)
    sys.exit(-1)


def handle_filename(name):
    return (
        name.replace('\\', '')
        .replace('/', '')
        .replace('*', '')
        .replace('?', '')
        .replace(':', '')
        .replace('<', '')
        .replace('>', '')
        .replace('|', '')
    )


def get_query_replay_info_url():
    return QUERY_REPLAY_INFO_API % int(round(time.time() * 1000))


def query_replay_info(live_id: str, room_id: str | None, password: str | None) -> dict:
    resp = requests.post(
        get_query_replay_info_url(),
        timeout=REQUESTS_TIMEOUT,
        json={
            'live_password': password if password else '',
            'media_room_id': room_id if room_id else '',
            'meeting_id': live_id,
        },
    )
    _do_assert(resp.status_code == 200, f'request failed, code={resp.status_code}')
    info = None
    try:
        info = json.loads(resp.content)
    except Exception:
        pass
    _do_assert(info and info['code'] == 0, f'query replay info failed: {info['msg']}')
    return info


def download_replay(url: str, password: str):
    live_url = urlparse(url)
    live_id = live_url.path.removeprefix('/live/')
    room_ids = set()
    _do_assert(live_id.isnumeric(), 'not a valid live id, invalid meeting?')
    for i in live_url.query.split('&'):
        d = i.split('=')
        if d[0] == 'room_id':
            room_ids.add(d[1])
    print(f'got live id: {live_id}')
    if len(room_ids) == 0:
        print('live room id is not specified, getting...')
        info = query_replay_info(live_id, None, password)
        for i in info['live_replay_info']:
            room_ids.add(i['room_id'])
        _do_assert(len(room_ids) > 0, 'no meeting room founded!')
    for i in room_ids:
        print(f'got room id: {i}')
        info = query_replay_info(live_id, i, password)
        count = 0
        for j in info['live_replay_info']:
            count += 1
            print(f'--> paragraph {count}: {'<file_state_error>' if (
                j['replay_file_state'] != 0 or j['replay_url_long'] == '-') else j['replay_url_long']}')


def download_yumpu(url: str):
    matched = re.match(r'https://www\.yumpu\.com/[^/]+/document/read/(\d+)(/.*)?', url)
    _do_assert(matched, "invalid url style, can't get bookid")
    book_id = matched.group(1)
    print(f'got book id: {book_id}')
    resp = requests.get(
        'https://www.yumpu.com/en/document/json/' + book_id, timeout=REQUESTS_TIMEOUT
    )
    _do_assert(resp.status_code == 200, f'request failed, code={resp.status_code}')
    meta: dict = json.loads(resp.content)
    _do_assert('document' in meta, 'failed to get book information.')
    book_name = handle_filename(meta['document']['title'])
    _do_assert(book_name, 'invalid book name')
    print(f'book: {book_name}')
    print(f'{len(meta['document']['pages'])} page(s) founded.')
    image_base = meta['document']['base_path']
    image_title = meta['document']['images']['title']
    image_dimension = meta['document']['images']['dimensions']['big']
    image_quality = meta['document']['images']['quality']
    _do_assert(image_base, 'invalid image base')
    _do_assert(image_title, 'invalid image title')
    _do_assert(image_dimension, 'invalid image dimension')
    _do_assert(image_quality, 'invalid image quality')
    file_format = image_title[image_title.find('.') :]
    if os.path.exists(book_name):
        shutil.rmtree(book_name)
    os.mkdir(book_name)
    for t in meta['document']['pages']:
        page = t['nr']
        print(f'\rplease wait...{page}', end='')
        resp = requests.get(
            f'{image_base}{page}/{image_dimension}/{image_title}?quality={image_quality}',
            timeout=REQUESTS_TIMEOUT,
        )
        with open(f'{book_name}/{page}{file_format}', 'wb') as file:
            file.write(resp.content)
    print('\ncompleted.')


def get_preview_detail(book_id: str, view_token: str, page: int) -> dict:
    resp = requests.get(
        f'https://openapi.book118.com/getPreview.html?&project_id=1&aid={book_id}&view_token={view_token}&page={page}',
        timeout=REQUESTS_TIMEOUT,
    )
    _do_assert(resp.status_code == 200, f'request failed, code={resp.status_code}')
    resp = resp.content.decode()
    resp = resp.removeprefix('jsonpReturn(')
    resp = resp.removesuffix(');')
    resp = json.loads(resp)
    # print(resp)
    _do_assert(resp and resp['status'] == 200, 'failed to get preview.')
    for i in resp['data']:
        resp['data'][i] = 'https' + resp['data'][i]
    return resp['data']


def download_book118(url: str):
    resp = requests.get(url, timeout=REQUESTS_TIMEOUT)
    _do_assert(resp.status_code == 200, f'request failed, code={resp.status_code}')
    resp = resp.content.decode()
    detail = resp[resp.find('base.detail = {') :]
    book_id = re.search('(?<=aid: )(.+)(?=, //解密后的id)', detail).group()
    title = handle_filename(re.search("(?<=title: ')(.+)(?=',)", detail).group())
    view_token = re.search("(?<=view_token: ')(.+)(?=')", detail).group()
    real_pages = int(re.search('(?<=actual_page: )(.+)(?=,)', detail).group())
    prev_pages = int(re.search('(?<=preview_page: )(.+)(?=,)', detail).group())
    print(f'got book: {title} ({book_id})')
    print(f'previewable pages: {prev_pages}/{real_pages}')
    current_page = 1
    if os.path.exists(title):
        shutil.rmtree(title)
    os.mkdir(title)
    while current_page <= prev_pages:
        dl = get_preview_detail(book_id, view_token, current_page)
        for page in dl:
            print(f'\rplease wait...{page}', end='')
            resp = requests.get(dl[page], timeout=REQUESTS_TIMEOUT)
            with open(f'{title}/{page}.png', 'wb') as file:
                file.write(resp.content)
            current_page = int(page) + 1
    print('\ncompleted.')


def download_doudin(url: str):
    resp = requests.get(url, headers={'User-Agent': UA}, timeout=REQUESTS_TIMEOUT)
    _do_assert(resp.status_code == 200, f'request failed, code={resp.status_code}')
    resp = resp.content.decode()
    detail = resp[resp.find('var readerConfig = {') :]
    pages = int(re.search('(?<=allPage:)(.+)(?=,)', detail).group())
    product_id = re.search('(?<=productId:)(.+)(?=,)', detail).group()
    token = re.search('(?<=flash_param_hzq:")(.+)(?=",)', detail).group()
    title = handle_filename(re.search('(?<=productName:")(.+)(?=",)', detail).group())
    print(f'got book: {title} ({product_id})')
    print(f'pages: {pages}')
    if os.path.exists(title):
        shutil.rmtree(title)
    os.mkdir(title)
    for p in range(pages):
        page = p + 1
        print(f'\rplease wait...{page}', end='')
        resp = requests.get(
            f'https://docimg1.docin.com/docinpic.jsp?file={product_id}&width=1600&pageno={
                            page}&sid={token}',
            headers={'User-Agent': UA},
            timeout=REQUESTS_TIMEOUT,
        )
        _do_assert(
            resp.status_code == 200,
            '\nthe server refused to serve more content, stopped.',
        )
        with open(f'{title}/{page}.png', 'wb') as file:
            file.write(resp.content)
    print('\ncompleted.')


def main():
    print('Tools available:')
    print('[1] TenMeeting Replay Downloader')
    print('[2] Yumpu Downloader')
    print('[3] Book118 Downloader')
    print('[4] Doudin Downloader')
    opt = int(input('(1-4) > '))
    match opt:
        case 1:
            print('# please enter the shared meeting link:')
            shared_link = input('> ')
            print('# please enter the meeting password: ')
            meeting_password = input('(optional) > ')
            resp = requests.get(shared_link, timeout=REQUESTS_TIMEOUT)
            _do_assert(
                resp.status_code == 200, f'request failed, code={resp.status_code}'
            )
            _do_assert(
                resp.url.startswith('https://meeting.tencent.com/live/'),
                'unexpected link style, invalid meeting?',
            )
            download_replay(resp.url, meeting_password)
        case 2:
            print('# please enter the yumpu link:')
            link = input('> ')
            download_yumpu(link)
        case 3:
            print('# please enter the book118 link:')
            link = input('> ')
            download_book118(link)
        case 4:
            print('# please enter the doudin link:')
            link = input('> ')
            download_doudin(link)
        case _:
            _do_assert(False, 'invalid tool.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    os.system('pause')
