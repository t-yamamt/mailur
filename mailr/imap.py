import re
from collections import OrderedDict

from . import Timer, log
from .db import session

re_noesc = r'[^\\](?:\\\\)*'


def list_(im):
    _, data = im.list()

    re_line = r'^[(]([^)]+)[)] "([^"]+)" "(.*%s)"$' % re_noesc
    lexer_line = re.compile(re_line)
    rows = []
    for line in data:
        matches = lexer_line.match(line.decode())
        row = matches.groups()
        row = tuple(row[0].split()), row[1], row[2]
        rows.append(row)
    return rows


def status(im, name, readonly=True):
    name = '"%s"' % name
    im.select(name, readonly=readonly)

    uid_next = 'UIDNEXT'
    _, data = im.status(name, '(%s)' % uid_next)
    lexer_uid = re.compile(r'[(]%s (\d+)[)]' % uid_next)
    matches = lexer_uid.search(data[0].decode())
    uid = int(matches.groups()[0])
    return uid


def search(im, name):
    uid_next = status(im, name)
    uids, step = [], 5000
    for i in range(1, uid_next, step):
        _, data = im.uid('SEARCH', None, '(UID %d:%d)' % (i, i + step - 1))
        if data[0]:
            uids += data[0].decode().split(' ')
    return uids


def fetch(im, uids, query, batch_size=500, callback=None, quiet=False):
    if not isinstance(query, str):
        query = ' '.join(query)

    steps = range(0, len(uids), batch_size)
    log_ = (lambda *a, **kw: None) if quiet else log.info
    log_('  * Fetch "%s" for (%d) %d ones...', query, len(steps),  len(uids))

    timer, data = Timer(), OrderedDict()
    for num, i in enumerate(steps, 1):
        uids_ = uids[i: i + batch_size]
        if not uids_:
            continue
        data_ = _fetch(im, uids_, query)
        data.update(data_)
        log_('  - (%d) %d ones for %.2fs', num, len(uids_), timer.time())
        if callback:
            with session.begin():
                callback(data_)
            log_('  - %s for %.2fs', callback.__name__, timer.time())
    return data


def _fetch(im, ids, query):
    status, data = im.uid('fetch', ','.join(ids), '(%s)' % query)

    data = iter(data)
    keys = query.split()
    if 'UID' not in keys:
        keys.append('UID')

    re_keys = r'|'.join([re.escape(k) for k in keys])
    re_list = r'("(.+?%s)"|[^ ]+)' % re_noesc
    lexer_list = re.compile(re_list)
    lexer_line = re.compile(
        r'(%s) ((\d+)|({\d+})|"([^"]+)"|([(].*%s[)]))' % (re_keys, re_noesc)
    )

    def parse(item, row):
        if isinstance(item, tuple):
            line = item[0]
        else:
            line = item

        matches = lexer_line.findall(line.decode())
        if matches:
            for match in matches:
                key, value = match[0:2]
                if match[2]:
                    row[key] = int(value)
                elif match[3]:
                    row[key] = item[1]
                    row = parse(next(data), row)
                elif match[4]:
                    row[key] = value
                elif match[5]:
                    unesc = lambda v: re.sub(r'\\(.)', r'\1', v)
                    value_ = value[1:-1]
                    value_ = lexer_list.findall(value_)
                    value_ = [unesc(v[1]) if v[1] else v[0] for v in value_]
                    row[key] = value_
        return row

    rows = OrderedDict()
    for i in range(len(ids)):
        row = parse(next(data), {})
        rows[str(row['UID'])] = row
    return rows