import re
import shutil
import os

import pyperclip

import config
import util.system

from util.internal import __assert__

from tool.__base__ import URLHandler

from tool.book118 import Book118URLHandler
from tool.doudin import DoudinURLHandler
from tool.imac_cast import IMacCastURLHandler
from tool.tencent_meeting import TencentMeetingURLHandler
from tool.yumpu import YumPuURLHandler

REGISTERED_TOOLS = [
    Book118URLHandler(),
    DoudinURLHandler(),
    IMacCastURLHandler(),
    TencentMeetingURLHandler(),
    YumPuURLHandler(),
]


def print_welcome():
    print(f'ToolBox Version: {config.VERSION}')


def print_tools_available():
    print(f'There is currently {len(REGISTERED_TOOLS)} tool available:')
    for tool in REGISTERED_TOOLS:
        print(f' * {tool.get_name()}')


def select_tool_by_url(url: str) -> URLHandler | None:
    for handler in REGISTERED_TOOLS:
        for pattern in handler.get_supported_url_patterns():
            if re.match(pattern, url):
                return handler
    return None


def clear_tmps():
    shutil.rmtree('temp', ignore_errors=True)


def init_dirs():
    clear_tmps()
    os.makedirs('temp', exist_ok=True)


def main():
    init_dirs()
    print_welcome()

    url = pyperclip.paste()
    tool_selected = select_tool_by_url(url)

    if tool_selected:
        print('A valid URL was found in your clipboard.')
        print(f' * {tool_selected.get_name()} --> {url}')
        print('Do you want to use it directly? [y/N]')
        match input('> ').lower():
            case 'y':
                tool_selected.handle(url)
                return
            case 'n' | '':
                pass
            case _:
                __assert__(False, 'Invalid input.')

    print_tools_available()
    print('Enter the URL directly: ')

    url = input('> ')
    tool_selected = select_tool_by_url(url)

    __assert__(tool_selected, 'Unsupported url!')
    tool_selected.handle(url)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    util.system.pause()
    clear_tmps()
