# -*- coding: utf-8 -*-
"""
Kodi Plugin - Swisscom TV (unofficial)

Unofficial Kodi plugin for Swisscom TV customers only.
Allows to watch unencrypted Swisscom TV video streams with Kodi.
"""

import sys
import os
import urllib
import urlparse
import sqlite3

import xbmcgui
import xbmcplugin
import xbmcaddon

from iso639 import iso639_1

_basedir = os.path.dirname(__file__)
_db_path = os.path.join(_basedir, u'swctv.db')

_addon_handle = int(sys.argv[1])
_args = urlparse.parse_qs(sys.argv[2][1:])

__settings__ = xbmcaddon.Addon(id='plugin.video.swisscom_tv_unofficial')
xbmcplugin.setContent(_addon_handle, 'movies')


def build_url(query):
    """build url by query"""
    return sys.argv[0] + '?' + urllib.urlencode(query)


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
    for url, name, language, resolution, thumb, desc in channels:
        names.append(name)

    ch = []
    for url, name, language, resolution, thumb, desc in channels:
        if names.count(name) == 1 or url.endswith(':10000'):
            ch.append((url, name, language, resolution, thumb, desc))
    return ch


def resolution_filter(channels):
    """Try to remove not prefered channel resolutions."""
    pref_res = __settings__.getSetting("prefered_resolution")

    names = []
    for url, name, language, resolution, thumb, desc in channels:
        names.append(name.lower())

    ch = []
    for url, name, language, resolution, thumb, desc in channels:
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

        ch.append((url, name, language, resolution, thumb, desc))
    return ch


def favorites(db, folder, entry):
    if entry is not None:
        dbname = 'swc_fav'
        with db:
            db.execute('''UPDATE OR IGNORE {dbname} SET visits=visits+1 WHERE folder=? AND entry=?'''.format(dbname=dbname), (folder,entry));
            db.execute('''INSERT OR IGNORE INTO {dbname} (folder,entry,visits) VALUES(?,?,1)'''.format(dbname=dbname), (folder,entry));


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
media_folders = dict()
#~ media_folders = collections.OrderedDict()
media_folders.update((
    ('Language', Cat(True,
        """WITH RECURSIVE split(lang_name, rest) AS (
                SELECT '', language || ',' FROM swc_tv
                  UNION ALL
                SELECT substr(rest, 0, instr(rest, ',')),
                       substr(rest, instr(rest, ',')+1)
                  FROM split
                  WHERE rest <> '')
            SELECT DISTINCT lang_name
              FROM split
              WHERE lang_name <> ''
              ORDER BY lang_name ASC""",
        ('SELECT swc_tv.*, swc_desc.{lang} FROM swc_tv LEFT JOIN swc_desc ON swc_tv.name = swc_desc.name WHERE instr(language, ?) ORDER BY name COLLATE NOCASE ASC',
            lambda a: a,
            resolution_filter,
            favorites)
        )
    ),
    ('Resolution', Cat(True,
        ('SD', 'HD', 'UHD'),
        ('SELECT swc_tv.*, swc_desc.{lang} FROM swc_tv LEFT JOIN swc_desc ON swc_tv.name = swc_desc.name WHERE resolution=? ORDER BY name COLLATE NOCASE ASC',
            ('SD', 'HD', 'UHD').index,
            lambda a: a,
            favorites)
        )
    ),
    ('Favorites', Cat(False,
        None,
        ('''SELECT swc_tv.*, swc_desc.{lang} FROM swc_tv LEFT JOIN swc_desc ON swc_tv.name = swc_desc.name WHERE language IN (
                SELECT lower(entry) FROM swc_fav WHERE folder=? ORDER BY visits DESC LIMIT 1
            ) ORDER BY name COLLATE NOCASE ASC''',
            lambda a: 'Language',
            resolution_filter,
            None)
        )
    ),

))


folder = _args.get('folder', [None])[0]
entry = _args.get('entry', [None])[0]

if folder is None:
    # root folder
    for elem in media_folders:
        if media_folders[elem].show:
            kodi_url = build_url({'folder': 'root', 'entry': elem})
            kodi_li = xbmcgui.ListItem(elem)
            kodi_li.setArt(dict(icon='DefaultFolder.png'))
            xbmcplugin.addDirectoryItem(handle=_addon_handle, url=kodi_url,
                                        listitem=kodi_li, isFolder=True)

    # append favorite language section
    folder = 'Favorites'
    entry = None
    #~ xbmcplugin.endOfDirectory(_addon_handle)

if folder == 'root':
    # sub folder
    subfolder = media_folders[entry].subfolder

    if isinstance(subfolder, str):
        db = sqlite3.connect(_db_path)
        subfolder = [d[0] for d in db.execute(subfolder)]
        db.close()

    for elem in subfolder:
        kodi_url = build_url({'folder': entry, 'entry': elem})
        kodi_li = xbmcgui.ListItem(iso639_1.get(elem, elem.upper()))
        kodi_li.setArt(dict(icon='DefaultFolder.png'))
        xbmcplugin.addDirectoryItem(handle=_addon_handle, url=kodi_url,
                                        listitem=kodi_li, isFolder=True)
    xbmcplugin.endOfDirectory(_addon_handle)


if folder in media_folders:
    query, post_action, post_filter, favorites = media_folders[folder].subsubfolder

    db = sqlite3.connect(_db_path)

    # update favorites
    if favorites:
        favorites(db, folder, entry)

    # get interface language
    supported_lang = ('en', 'de', 'fr', 'it')
    # local override is possible
    desc_lang = __settings__.getSetting("channel_description_language").lower()
    if desc_lang not in supported_lang:
        # use 'default' interface language
        desc_lang = xbmc.getLanguage(xbmc.ISO_639_1)
        if desc_lang not in supported_lang:
            desc_lang = 'en'

    cur = db.cursor()
    cur.execute(query.format(lang=desc_lang), (post_action(entry),))
    for values in post_filter(prefered_url(cur.fetchall())):
        stream_url, name, language, resolution, thumb, desc = values
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
