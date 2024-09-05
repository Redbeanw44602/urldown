import requests
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

import config

from util.network import get_base_url
from util.network import download as download_file
from util.network import add_query_param
from util.system import get_executable_extension
from util.system import get_redirect_to_null_suffix
from util.internal import __assert__
from util.internal import __check_response__
from util.string import sanitize_filename


class ExtTag(object):
    name = None

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f'<ExtTag> {self.name}'

    @staticmethod
    def parse(line: str):
        if len(line) == 0 or line[0] != '#':
            return None
        max_idx = len(line) - 1
        idx = 0
        buffer = str()
        name = str()
        kv = dict()
        key = str()
        tag_name_begin = False
        content_begin = True
        is_in_quotation_mark = False
        is_base_tag = True
        is_simple_tag = False
        is_kv_tag = False
        while True:
            if idx > max_idx:
                break
            char = line[idx]
            idx += 1
            if char == '"':
                is_in_quotation_mark = not is_in_quotation_mark
                continue  # to forbid mark in final result.
            if not is_in_quotation_mark:
                match char:
                    case '#':
                        __assert__(not tag_name_begin, 'Error when parsing tag.')
                        tag_name_begin = True
                        buffer += '#'
                    case ':':
                        if tag_name_begin:
                            name = buffer
                            buffer = ''
                        is_base_tag = False
                        is_simple_tag = True
                        tag_name_begin = False
                        content_begin = True
                    case '=':
                        __assert__(content_begin, 'Error when parsing tag.')
                        is_simple_tag = False
                        is_kv_tag = True
                        key = buffer
                        buffer = ''
                    case ',':
                        if line.startswith('#EXTINF'):
                            break  # For compatibility with earlier HLS versions.
                        __assert__(is_kv_tag, 'Error when parsing tag.')
                        kv[key] = buffer
                        buffer = ''
                    case _:
                        buffer += char
            else:
                buffer += char
        # handle end of buffer
        if is_base_tag:
            return ExtTag(buffer)
        if is_simple_tag:
            return SimpleExtTag(name, buffer)
        if is_kv_tag:
            kv[key] = buffer
            return KVExtTag(name, kv)


class SimpleExtTag(ExtTag):
    value = None

    def __init__(self, name, value):
        super().__init__(name)
        self.value = value

    def __str__(self):
        return f'<SimpleExtTag> {self.name} --> {self.value}'


class KVExtTag(ExtTag):
    dict = None

    def __init__(self, name, dict):
        super().__init__(name)
        self.dict = dict

    def __str__(self):
        result = f'<KVExtTag> {self.name}'
        for key in self.dict:
            result += f'\n  {key} --> {self.dict[key]}'
        return result


def decrypt_local_ts_file(file_path, key, iv):
    with open(file_path, 'rb') as encrypted_file:
        encrypted_data = encrypted_file.read()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    with open(file_path, 'wb') as decrypted_file:
        decrypted_file.write(decrypted_data)


def download(url: str, video_name: str, token: str = None):  # token is tencent's extension?
    video_name = sanitize_filename(video_name)
    base_url = get_base_url(url)
    m3u8 = requests.get(url, timeout=config.REQUESTS_TIMEOUT)
    m3u8 = m3u8.content.decode().split('\n')
    adaptive_stream_idx = 0
    key = None
    video_urls = []
    idx = 0
    while True:
        if idx > len(m3u8) - 1:  # end
            break
        line = m3u8[idx]
        idx += 1
        if len(line) == 0:
            continue
        line = ExtTag.parse(line)
        match line.name:
            case '#EXTM3U':
                pass
            case '#EXT-X-VERSION':
                pass
            case '#EXT-X-STREAM-INF':
                # TODO: Choose a stream
                print(f'Processing new adaptive stream... ({adaptive_stream_idx})')
                download(
                    base_url + m3u8[idx],
                    f'{video_name}.{adaptive_stream_idx}'
                    if adaptive_stream_idx > 0
                    else f'{video_name}',
                    token,
                )
                adaptive_stream_idx += 1
                idx += 1
            case '#EXT-X-PLAYLIST-TYPE':
                __assert__(line.value == 'VOD', 'Unsupported playlist type.')
            case '#EXT-X-MEDIA-SEQUENCE':
                if int(line.value) != 0:
                    print('Warning! Media sequence is not zero, will be ignored.')
            case '#EXT-X-TARGETDURATION':
                pass
            case '#EXT-X-KEY':
                print('The DRM key is found and the video will be automatically decrypted later.')
                key = line
            case '#EXTINF':
                url = m3u8[idx]
                idx += 1
                video_urls.append(url)
            case '#EXT-X-ENDLIST':
                pass
            case _:
                print(f'Warning! Unhandled line: {line.name}')
    if len(video_urls) == 0:
        return
    # Download
    os.makedirs(f'temp/{video_name}', exist_ok=True)
    idx = 0
    max_idx = len(video_urls) - 1
    saved_files = []
    for url in video_urls:
        print(f'\rDownloading... ({idx}/{max_idx})', end='')
        path = f'temp/{video_name}/{idx}.ts'
        saved_files.append(path)
        if not download_file(base_url + url, path):
            return
        idx += 1

    # Decrypt
    if key:
        method = key.dict['METHOD']
        __assert__(method == 'AES-128', f'Unsupported encrypt method: {method}')
        key_url = key.dict['URI']
        iv = bytes.fromhex(key.dict['IV'].removeprefix('0x'))
        if token:
            key_url = add_query_param(key_url, 'token', token)
        response = requests.get(key_url, timeout=config.REQUESTS_TIMEOUT)
        __check_response__(response)
        key = response.content
        idx = 0
        for path in saved_files:
            print(f'\rDecrypting... ({idx}/{max_idx})', end='')
            decrypt_local_ts_file(path, key, iv)
            idx += 1

    print('\nMerging...')
    os.system(
        f'ffmpeg{get_executable_extension()} -nostdin -i "concat:{'|'.join(_ for _ in saved_files)}" -c copy "{video_name + '.mp4'}" {get_redirect_to_null_suffix()}'
    )

    print('Completed.')
