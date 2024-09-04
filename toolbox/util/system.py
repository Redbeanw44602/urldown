import sys
import os


def is_windows():
    return sys.platform.startswith('win')


def pause():
    if is_windows():
        os.system('pause')
