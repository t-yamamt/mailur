import json
import logging
import logging.config
import os
import socket
import time
from contextlib import ContextDecorator
from functools import wraps

log = logging.getLogger(__name__)
app_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(app_dir, '..'))


class _Conf:
    def __init__(self):
        filename = os.environ.get('MAILUR_CONF', 'conf.json')
        self.path = os.path.join(base_dir, filename)

        with open(self.path, 'br') as f:
            conf = json.loads(f.read().decode())

        defaults = {
            'attachments_dir': 'attachments',
            'cache_type': 'werkzeug.contrib.cache.NullCache',
            'imap_body_maxsize': 50 * 1024 * 1024,
            'imap_batch_size': 2000,
            'ui_ga_id': '',
            'ui_is_public': False,
            'ui_use_names': True,
        }
        self.data = dict(defaults, **conf)
        self.setup_logging()

    def update(self, *args, **kwargs):
        self.data.update(*args, **kwargs)
        content = json.dumps(
            self.data, sort_keys=True, indent=4, separators=(',', ': ')
        )
        with open(self.path, 'bw') as f:
            f.write(content.encode())

    def __call__(self, key, default=None):
        return self.data.get(key, default)

    @property
    def theme_dir(self):
        return os.path.join(app_dir, 'theme')

    @property
    def attachments_dir(self):
        dir_ = self('attachments_dir')
        return os.path.join(base_dir, dir_)

    def setup_logging(self):
        conf = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '%(levelname)s %(asctime)s  %(message)s',
                    'datefmt': '%H:%M:%S'
                },
                'detail': {
                    'format': (
                        '%(asctime)s[%(threadName)-12.12s][%(levelname)-5.5s] '
                        '%(name)s %(message)s'
                    )
                }
            },
            'handlers': {
                'console_simple': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'simple',
                    'stream': 'ext://sys.stdout'
                },
                'console_detail': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'detail',
                    'stream': 'ext://sys.stdout'
                },
            },
            'loggers': {
                '': {
                    'handlers': self('log_enabled', ['console_detail']),
                    'level': self('log_level', 'INFO'),
                    'propagate': True
                }
            }
        }
        log_file = self('log_file')
        if log_file:
            conf['handlers'].update(file={
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detail',
                'filename': log_file,
                'maxBytes': 10485760,
                'backupCount': 20,
                'encoding': 'utf8'
            })
            conf['loggers']['']['handlers'].append('file')
        logging.config.dictConfig(conf)

conf = _Conf()


def with_lock(func):
    target = ':'.join([func.__module__, func.__name__, conf.path])

    @wraps(func)
    def inner(*a, **kw):
        lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        lock_socket.bind('\0' + target)
        return func(*a, **kw)
    return inner


class Timer(ContextDecorator):
    __slots__ = ('start', 'finish', 'label')

    def __init__(self, label=None):
        self.reset()
        self.label = label

    def __enter__(self):
        self.reset()

    def __exit__(self, *a, **kw):
        duration = self.duration
        if self.label:
            log.info('%s for %.2fs', self.label, duration)

    def reset(self):
        self.start = time.time()

    @property
    def duration(self):
        self.finish = time.time()
        return self.finish - self.start

    def time(self, reset=True):
        duration = self.duration
        if reset:
            self.reset()
        return duration
