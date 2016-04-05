"""
Kodi Plugin - Swisscom TV (unofficial)

Unofficial Kodi plugin for Swisscom TV customers only.
Allows to watch unencrypted Swisscom TV video streams with Kodi.
"""

import sys
import os
import urllib, urlparse
#~ import collections
import sqlite3

import xbmcgui
import xbmcplugin

addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')

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
res_folders = ('SD', 'HD', 'UHD')
root_folders = dict()
#~ root_folders = collections.OrderedDict()
root_folders.update((
    ('Language', ('SELECT * FROM swc_tv WHERE language=?', lambda a: a)),
    ('Resolution', ('SELECT * FROM swc_tv WHERE resolution=?', res_folders.index)),
#~ ('Favorites', ('SELECT * FROM swc_fav ORDER BY count DESC LIMIT 1,10',)),
#~ ('Last Seen', ('SELECT * FROM swc_fav ORDER BY date DESC LIMIT 1,10',)),
))

db = sqlite3.connect(os.path.join(os.path.dirname(__file__), u'swctv.db'))

folder = args.get('folder', [None])[0]
entry = args.get('entry', [None])[0]
if folder is None:
    # root folder
    for elem in root_folders:
        kodi_url = build_url({'folder': 'root', 'entry': elem})
        kodi_li = xbmcgui.ListItem(elem, iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=kodi_url,
                                    listitem=kodi_li, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)


elif folder == 'root':
    # sub folder
    if entry == 'Resolution':
        for elem in res_folders:
            kodi_url = build_url({'folder': entry, 'entry': elem})
            kodi_li = xbmcgui.ListItem(elem, iconImage='DefaultFolder.png')
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=kodi_url,
                                        listitem=kodi_li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    elif entry == 'Language':
        cur = db.cursor()
        cur.execute("SELECT distinct language FROM swc_tv where language <> '' ORDER BY language ASC")

        for lang in cur.fetchall():
            kodi_url = build_url({'folder': entry, 'entry': lang[0]})
            kodi_li = xbmcgui.ListItem(lang[0].upper(), iconImage='DefaultFolder.png')
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=kodi_url,
                                        listitem=kodi_li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)


elif folder in root_folders:
    query = root_folders[folder][0]
    param = root_folders[folder][1](entry)

    cur = db.cursor()
    cur.execute(query, (param,))
    for stream_url, name, language, desc, resolution, thumb in prefered_url(cur.fetchall()):
        if thumb:
            thumb_path = os.path.join(os.path.dirname(__file__), 'resources', 'media', thumb)
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
        kodi_li.setInfo(type="Video", infoLabels={"Title": name, 'Description': desc, 'Language':language})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=stream_url, listitem=kodi_li)

    xbmcplugin.endOfDirectory(addon_handle)

db.close()
