from util.internal import __purecall__


class URLHandler(object):
    def __init__(self):
        pass

    def get_name(self) -> str:
        __purecall__()

    def get_supported_url_patterns(self, url: str) -> list[str]:
        __purecall__()

    def handle(self, url: str):
        __purecall__()
