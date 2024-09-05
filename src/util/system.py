import sys
import os


def is_windows():
    return sys.platform.startswith('win')


def pause():
    if is_windows():
        os.system('pause')


def get_executable_extension():
    return '.exe' if is_windows() else ''


def get_redirect_to_null_suffix():
    return '> NUL 2>&1' if is_windows() else '> /dev/null 2>&1'
