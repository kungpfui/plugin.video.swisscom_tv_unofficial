"""
Kodi Plugin - Swisscom TV (unofficial)

Unofficial Kodi plugin for Swisscom TV customers only.
Allows to watch unencrypted Swisscom TV video streams with Kodi.
"""

import sys
import os
import urllib, urlparse
import sqlite3
#~ import collections

import xbmcgui
import xbmcplugin

_basedir = os.path.dirname(__file__)
_addon_handle = int(sys.argv[1])
_args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(_addon_handle, 'movies')

def build_url(query):
    return sys.argv[0] + '?' + urllib.urlencode(query)

def prefered_url(channels):
    """remove double entries. prefere urls which use port 10000"""
    names = []
    for url, name, language, desc, resolution, thumb in channels:
        names.append(name)

    ch = []
    for url, name, language, desc, resolution, thumb in channels:
        if names.count(name) == 1 or url.endswith(':10000'):
            ch.append((url, name, language, desc, resolution, thumb))
    return ch


# the predefined folders
media_folders = dict()
#~ media_folders = collections.OrderedDict()
media_folders.update((
    ('Language', ("SELECT distinct upper(language) FROM swc_tv where language <> '' ORDER BY language ASC",
                 ('SELECT * FROM swc_tv WHERE language=lower(?)', lambda a: a)
                 )
    ),
    ('Resolution', (('SD', 'HD', 'UHD'),
                   ('SELECT * FROM swc_tv WHERE resolution=?', ('SD', 'HD', 'UHD').index)
                   )
    ),
))

db = sqlite3.connect(os.path.join(_basedir, u'swctv.db'))

folder = _args.get('folder', [None])[0]
entry = _args.get('entry', [None])[0]
if folder is None:
    # root folder
    for elem in media_folders:
        kodi_url = build_url({'folder': 'root', 'entry': elem})
        kodi_li = xbmcgui.ListItem(elem, iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=_addon_handle, url=kodi_url,
                                    listitem=kodi_li, isFolder=True)
    xbmcplugin.endOfDirectory(_addon_handle)


elif folder == 'root':
    # sub folder
    subfolder = media_folders[entry][0]
    if isinstance(subfolder, str):
        cur = db.cursor()
        cur.execute(subfolder)
        subfolder = [d[0] for d in cur.fetchall()]

    for elem in subfolder:
        kodi_url = build_url({'folder': entry, 'entry': elem})
        kodi_li = xbmcgui.ListItem(elem, iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=_addon_handle, url=kodi_url,
                                        listitem=kodi_li, isFolder=True)
    xbmcplugin.endOfDirectory(_addon_handle)


elif folder in media_folders:
    query, post_action = media_folders[folder][-1]
    param = post_action(entry)

    cur = db.cursor()
    cur.execute(query, (param,))
    for stream_url, name, language, desc, resolution, thumb in prefered_url(cur.fetchall()):
        if thumb:
            thumb_path = os.path.join(_basedir, 'resources', 'media', thumb)
            if not os.path.exists(thumb_path):
                # kodi can't handle "memory" images, so create a folder and extract the image from DB into the filesystem
                if not os.path.exists(os.path.dirname(thumb_path)):
                    os.makedirs(os.path.dirname(thumb_path))
                cur = db.cursor()
                cur.execute("SELECT imagedata FROM swc_img where imagename=?", (thumb,))
                with open(thumb_path, 'wb') as f:
                    f.write(cur.fetchone()[0])

            kodi_li = xbmcgui.ListItem(name, iconImage=thumb_path, thumbnailImage=thumb_path)
        else:
            kodi_li = xbmcgui.ListItem(name, iconImage='DefaultVideo.png')

        kodi_li.setInfo(type="Video", infoLabels={"Title": name, 'plot': desc})
        xbmcplugin.addDirectoryItem(handle=_addon_handle, url=stream_url, listitem=kodi_li)

    xbmcplugin.endOfDirectory(_addon_handle)

db.close()
