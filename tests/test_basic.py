from mailur import imap, parse


def test_binary_msg():
    assert parse.binary_msg('Ответ: 42').as_bytes() == '\r\n'.join([
        'MIME-Version: 1.0',
        'Content-Transfer-Encoding: binary',
        'Content-Type: text/plain; charset="utf-8"',
        '',
        'Ответ: 42'
    ]).encode()

    assert parse.binary_msg('Ответ: 42').as_string() == '\r\n'.join([
        'MIME-Version: 1.0',
        'Content-Transfer-Encoding: base64',
        'Content-Type: text/plain; charset="utf-8"',
        '',
        '0J7RgtCy0LXRgjogNDI=\r\n'
    ])


def test_basic_gmail():
    gm = imap.Gmail()
    assert gm.current_folder == 'All'

    gm = imap.Gmail('\\Junk')
    assert gm.current_folder == 'V/Spam'

    gm = imap.Gmail('\\Trash')
    assert gm.current_folder == 'V/Trash'


def test_fetch_and_parse(clean_users, gmail, some):
    gm = imap.Gmail()
    lm = imap.Local()
    parse.fetch_folder()
    parse.parse_folder()

    def gmail_uidnext():
        res = lm.getmetadata('gmail/uidnext/all')
        assert res == [(b'All (/private/gmail/uidnext/all {12}', some), b')']
        return some.value

    def mlr_uidnext():
        res = lm.getmetadata('mlr/uidnext')
        assert res == [(b'All (/private/mlr/uidnext {1}', some), b')']
        return some.value

    def add_msgs(items=None):
        if items is None:
            items = [(1042, 42, '42')]
        gmail.fetch = [('OK', [])]
        for gid, uid, txt in items:
            msg = parse.binary_msg(txt).as_bytes()
            gm.append('All', None, None, msg)
            gmail.fetch[0][1].extend([
                (
                    b'1 (X-GM-MSGID %d X-GM-LABELS ("\\\\Inbox") UID %d '
                    b'INTERNALDATE "08-Jul-2017 09:08:30 +0000" FLAGS () '
                    b'BODY[] {%d}' % (gid, uid, len(msg)),
                    msg
                ),
                b')'
            ])

    assert gmail_uidnext().endswith(b',1')
    assert lm.getmetadata('mlr/uidnext') == [b'All (/private/mlr/uidnext NIL)']

    add_msgs()
    parse.fetch_folder()
    parse.parse_folder()
    assert gmail_uidnext().endswith(b',2')
    assert mlr_uidnext() == b'2'
    assert lm.select(lm.ALL) == [b'1']
    assert lm.select(lm.PARSED) == [b'1']

    add_msgs([(10001, 101, '1'), (10002, 102, '2')])
    parse.fetch_folder()
    parse.parse_folder()
    assert gmail_uidnext().endswith(b',4')
    assert mlr_uidnext() == b'4'
    assert lm.select(lm.ALL) == [b'3']
    assert lm.select(lm.PARSED) == [b'3']

    parse.fetch_folder()
    parse.parse_folder('all')
    assert gmail_uidnext().endswith(b',4')
    assert mlr_uidnext() == b'4'
    assert lm.select(lm.ALL) == [b'3']
    assert lm.select(lm.PARSED) == [b'3']
    assert lm.status(lm.PARSED, '(UIDNEXT)') == [b'Parsed (UIDNEXT 7)']
