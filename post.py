import hashlib
import urllib.parse


import feedparser
import mechanicalsoup
import mysql.connector


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
    b.select_form('#postmodify')
    b['subject'] = entry.title
    b['message'] = message(entry)
    b['preview'] = None
    b.submit_selected().raise_for_status()


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
    db = mysql.connector.connect(
        user=config.db_user,
        password=config.db_pass,
        host=config.db_host,
        database=config.db_name,
    )
    cursor = db.cursor()
    for entry in d.entries[::-1]:
        guid = entry.id
        id_hash = hashlib.sha256(guid.encode('utf-8')).hexdigest()
        entry_hash = hashlib.sha256(
            entry.guid.encode('utf-8') + entry.description.encode('utf-8'),
        ).hexdigest()
        cursor.execute('''
            SELECT COUNT(*)
            FROM posted_entries
            WHERE id = %s OR entry_hash = %s''',
            (id_hash, entry_hash)
        )
        count = cursor.fetchall()[0][0]
        if not count:
            post(b, entry)
            cursor.execute('''
                INSERT INTO posted_entries (id, entry_hash, url)
                VALUES (%s, %s, %s)''',
                (id_hash, entry_hash, guid)
            )
            db.commit()
