import logging
import re


class RedactAccessLinks(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r'/confirm/[^/\s?]+/?', '/confirm/[redacted]/', record.getMessage())
        record.msg = re.sub(r'([?&]invite=)[^\s&]+', r'\1[redacted]', record.msg)
        record.args = ()
        return True
