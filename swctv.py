"""
Kodi Plugin - Swisscom TV (unofficial)

Unofficial Kodi plugin for Swisscom TV customers only.
Allows to watch unencrypted Swisscom TV video streams with Kodi.
"""

import sys
import os
import sqlite3

try:
    from urlparse import parse_qs
    from urllib import urlencode
except ImportError:
    from urllib.parse import parse_qs, urlencode

import xbmcgui
import xbmcplugin
import xbmcaddon

from lang import Lang

_basedir = os.path.dirname(__file__)
_db_path = os.path.join(_basedir, u'swctv.db')

_addon_handle = int(sys.argv[1])
_args = parse_qs(sys.argv[2][1:])

__settings__ = xbmcaddon.Addon(id='plugin.video.swisscom_tv_unofficial')
xbmcplugin.setContent(_addon_handle, 'movies')


def build_url(query):
    """build url by query"""
    return sys.argv[0] + '?' + urlencode(query)


def word_replace(s, replace):
    """word based replace function.

    @param s        string to search in
    @param replace  dictionary (key->value) or a list, tuple (value->'')
    """
    words = s.split(' ')
    for i, part in enumerate(words):
        if part in replace:
            if isinstance(replace, (list, tuple)):
                words[i] = None
            elif isinstance(replace, dict):
                words[i] = replace[part]

    # remove None values
    while words.count(None):
        words.remove(None)

    return ' '.join(words)


def prefered_url(channels):
    """remove double entries. prefere urls which use port 10000"""
    names = []
    for url, name, language, resolution, desc_id, thumb, desc in channels:
        names.append(name)

    ch = []
    for url, name, language, resolution, desc_id, thumb, desc in channels:
        if names.count(name) == 1 or url.endswith(':10000'):
            ch.append((url, name, language, resolution, desc_id, thumb, desc))
    return ch


def resolution_filter(channels):
    """Try to remove not prefered channel resolutions."""
    pref_res = __settings__.getSetting("prefered_resolution")

    names = []
    for url, name, language, resolution, desc_id, thumb, desc in channels:
        names.append(name.lower())

    ch = []
    for url, name, language, resolution, desc_id, thumb, desc in channels:
        if pref_res == 'SD' and resolution != 0:
            found = word_replace(name.lower(), ('hd', 'uhd', '4k', '4k1'))
            if found in names:
                continue
        elif pref_res == 'HD' and resolution != 1:
            found = word_replace(name.lower(), ('uhd', '4k', '4k1')) + ' hd'
            if found in names:
                continue
        elif pref_res == 'UHD' and resolution != 2:
            found = word_replace(name.lower(), ('hd',)) + ' uhd'
            if found in names:
                continue

        ch.append((url, name, language, resolution, desc_id, thumb, desc))
    return ch


def favorites(db, folder, entry):
    if entry is not None:
        dbname = 'swc_fav'
        with db:
            db.execute(
                '''UPDATE OR IGNORE {dbname} SET visits=visits+1 WHERE folder=? AND entry=?'''.format(dbname=dbname),
                (folder, entry));
            db.execute('''INSERT OR IGNORE INTO {dbname} (folder,entry,visits) VALUES(?,?,1)'''.format(dbname=dbname),
                       (folder, entry));


class Cat(object):
    """simple category class"""

    def __init__(self, show, subfolder, subsubfolder):
        """c'tor'
        @param show          boolean, show within root folder
        @param subfolder     list or sql query
        @param subsubfolder  tuple
        """
        self.show = show
        self.subfolder = subfolder
        self.subsubfolder = subsubfolder


# the predefined folders
media_folders = dict((
    ('Language', Cat(True,
                     """WITH RECURSIVE split(lang_text, lang_key, rest) AS (
                             SELECT iso639_1.{lang}, '', swc_tv.language || ',' FROM swc_tv LEFT JOIN iso639_1 ON swc_tv.language=iso639_1.key
                               UNION ALL
                             SELECT lang_text,
                                    substr(rest, 0, instr(rest, ',')),
                                    substr(rest, instr(rest, ',')+1)
                               FROM split
                               WHERE rest <> '')
                         SELECT DISTINCT lang_key, lang_text
                           FROM split
                           WHERE lang_key <> '' AND lang_text NOTNULL
                           ORDER BY lang_key='{lang}' DESC, lang_text ASC""",
                     ("""SELECT swc_tv.*, swc_desc.{lang}
                FROM swc_tv LEFT JOIN swc_desc ON swc_tv.desc_id = swc_desc.id
                WHERE instr(language, ?)
                ORDER BY name COLLATE NOCASE ASC""",
                      lambda a: a,
                      resolution_filter,
                      favorites)
                     )
     ),
    ('Resolution', Cat(True,
                       (('SD', 'SD: 720 x 576'), ('HD', 'HD: 1280 x 720 / 1920 x 1080'), ('UHD', 'UHD: 3840 x 2160')),
                       ("""SELECT swc_tv.*, swc_desc.{lang}
                FROM swc_tv LEFT JOIN swc_desc ON swc_tv.desc_id = swc_desc.id
                WHERE resolution=?
                ORDER BY name COLLATE NOCASE ASC""",
                        ('SD', 'HD', 'UHD').index,
                        lambda a: a,
                        favorites)
                       )
     ),
    ('Favorites', Cat(False,
                      None,
                      ('''SELECT swc_tv.*, swc_desc.{lang}
                FROM swc_tv LEFT JOIN swc_desc
                ON swc_tv.desc_id = swc_desc.id
                WHERE language IN (
                    SELECT lower(entry) FROM swc_fav WHERE folder=? ORDER BY visits DESC LIMIT 1
                )
                ORDER BY name COLLATE NOCASE ASC''',
                       lambda a: 'Language',
                       resolution_filter,
                       None)
                      )
     ),

))

folder = _args.get('folder', [None])[0]
entry = _args.get('entry', [None])[0]

# get interface language
lang = Lang(__settings__)


def iso639_1(value):
    global lang

    cur = db.cursor()
    cur.execute("SELECT {lang} FROM iso639_1 WHERE key=?".format(lang=lang), (value,))
    try:
        return cur.fetchone()[0]
    except:
        return value.upper()


if folder is None:
    # root folder
    for elem in media_folders:
        if media_folders[elem].show:
            kodi_url = build_url({'folder': 'root', 'entry': elem})
            kodi_li = xbmcgui.ListItem(lang.translate(elem))
            kodi_li.setArt(dict(icon='DefaultFolder.png'))
            xbmcplugin.addDirectoryItem(handle=_addon_handle, url=kodi_url, listitem=kodi_li, isFolder=True)

    # append favorite language section
    folder = 'Favorites'
    entry = None
    # ~ xbmcplugin.endOfDirectory(_addon_handle)

if folder == 'root':
    # sub folder
    subfolder = media_folders[entry].subfolder

    if isinstance(subfolder, str):
        db = sqlite3.connect(_db_path)
        subfolder = [d for d in db.execute(subfolder.format(lang=lang))]
        db.close()

    for elem, text in subfolder:
        kodi_url = build_url({'folder': entry, 'entry': elem})
        kodi_li = xbmcgui.ListItem(text)
        kodi_li.setArt(dict(icon='DefaultFolder.png'))
        xbmcplugin.addDirectoryItem(handle=_addon_handle, url=kodi_url, listitem=kodi_li, isFolder=True)
    xbmcplugin.endOfDirectory(_addon_handle)

if folder in media_folders:
    query, post_action, post_filter, favorites = media_folders[folder].subsubfolder

    db = sqlite3.connect(_db_path)

    # update favorites
    if favorites:
        favorites(db, folder, entry)

    cur = db.cursor()
    cur.execute(query.format(lang=lang), (post_action(entry),))
    for values in post_filter(prefered_url(cur.fetchall())):
        stream_url, name, language, resolution, desc_id, thumb, desc = values

        if thumb:
            thumb_path = os.path.join(_basedir, 'resources', 'media', thumb)
            if not os.path.exists(thumb_path):
                # kodi can't handle "memory" images, so create a folder and extract the image from DB into the filesystem
                if not os.path.exists(os.path.dirname(thumb_path)):
                    os.makedirs(os.path.dirname(thumb_path))
                cur = db.cursor()
                cur.execute("SELECT data FROM swc_img where name=?", (thumb,))
                with open(thumb_path, 'wb') as f:
                    f.write(cur.fetchone()[0])

            kodi_li = xbmcgui.ListItem(name)
            kodi_li.setArt(dict(icon=thumb_path, thumb=thumb_path))
        else:
            kodi_li = xbmcgui.ListItem(name)
            kodi_li.setArt(dict(icon='DefaultVideo.png'))

        kodi_li.setInfo(type="Video", infoLabels={"Title": name, 'plot': desc})
        xbmcplugin.addDirectoryItem(handle=_addon_handle, url=stream_url, listitem=kodi_li)

    xbmcplugin.endOfDirectory(_addon_handle)
    db.close()
