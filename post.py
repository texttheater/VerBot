from datetime import datetime as dt
import hashlib
import urllib.parse


import feedparser
import mechanicalsoup
import sqlite3


import config


def wikiurl(title):
    title = title.replace(' ', '_')
    title = '/'.join(urllib.parse.quote(p) for p in title.split('/'))
    return title


def htmlsafe(html):
    """Escape HTML for use in SMF [html]...[/html] tags"""
    return html.replace('[/html]', '&#91;/html&#93;')


def message(entry):
    author = entry.author
    author_url = f'https://neutsch.org/Benutzer:{wikiurl(author)}'
    title = entry.title
    title_url = f'https://neutsch.org/{wikiurl(title)}'
    change_url = entry.link
    return f'[url={author_url}]{author}[/url] ' \
        f'hat folgende [url={change_url}]Änderung[/url] ' \
        f'an der Seite [url={title_url}]{title}[/url] vorgenommen:\n\n' \
        f'[html]{htmlsafe(entry.description)}[/html]'


def post(b, entry):
    b.open(config.forum_url_post)
    form = b.select_form('#postmodify')
    b['subject'] = entry.title
    b['message'] = message(entry)
    form.choose_submit('post')
    response = b.submit_selected()
    response.raise_for_status()


if __name__ == '__main__':
    # feed parser
    d = feedparser.parse(config.feed_url)
    # forum browser
    b = mechanicalsoup.StatefulBrowser()
    b.open(config.forum_url_login)
    b.select_form('#frmLogin')
    b['user'] = config.forum_user
    b['passwrd'] = config.forum_pass
    b.submit_selected().raise_for_status()
    # database
    con = sqlite3.connect(config.database)
    con.execute(
        'CREATE TABLE IF NOT EXISTS '
        'posted_entries (entry_hash PRIMARY KEY, url, time)',
    )
    # go through entries
    for entry in d.entries[::-1]:
        # compute entry hash
        guid = entry.id
        entry_hash = hashlib.sha256(
            entry.guid.encode('utf-8') + entry.description.encode('utf-8'),
        ).hexdigest()
        # check if entry has already been processed
        res = con.execute('''
            SELECT COUNT(*)
            FROM posted_entries
            WHERE entry_hash = ?''',
            (entry_hash,),
        )
        count = res.fetchall()[0][0]
        # if not, process it
        if not count:
            post(b, entry)
            con.execute(
                'INSERT INTO posted_entries (entry_hash, url, time) '
                'VALUES (?, ?, ?) ',
                (entry_hash, guid, str(dt.now())),
            )
            db.commit()
