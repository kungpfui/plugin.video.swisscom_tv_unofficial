import sys
import os
import urllib, urlparse
import xbmcgui
import xbmcplugin
import collections
import sqlite3

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')

def build_url(query):
    return base_url + '?' + urllib.urlencode(query)

def prefered_url_filter(channels):
    """remove double entries. prefere urls which use port 10000"""
    names = []
    for url, name, language, desc, resolution, thumb in channels:
        names.append(name)

    ch = []
    for url, name, language, desc, resolution, thumb in channels:
        if names.count(name) >= 1 and not url.endswith(':10000'):
            pass
        else:
            ch.append((url, name, language, desc, resolution, thumb))
    return ch


res_folders = ('SD', 'HD', 'UHD')
root_folders = collections.OrderedDict(
    Language=('SELECT * FROM swc_tv WHERE language=?', lambda a: a),
    Resolution=('SELECT * FROM swc_tv WHERE resolution=?', res_folders.index)
)


db = sqlite3.connect(os.path.join(os.path.dirname(__file__),u'swctv.db'))

folder = args.get('folder', [None])[0]
entry = args.get('entry', [None])[0]
if folder is None:
    # root folder
    for elem in root_folders:
        url = build_url({'folder': 'root', 'entry': elem})
        li = xbmcgui.ListItem(elem, iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
            listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)


elif folder == 'root':
    # sub folder
    if entry == 'Resolution':
        for elem in res_folders:
            url = build_url({'folder': entry, 'entry': elem})
            li = xbmcgui.ListItem(elem, iconImage='DefaultFolder.png')
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

    elif entry == 'Language':
        cur = db.cursor()
        cur.execute("SELECT distinct language FROM swc_tv where language <> '' ORDER BY language ASC")

        for lang in cur.fetchall():
            url = build_url({'folder': entry, 'entry': lang[0]})
            li = xbmcgui.ListItem(lang[0].upper(), iconImage='DefaultFolder.png')
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)

elif folder in root_folders:
    query = root_folders[folder][0]
    filter = root_folders[folder][1](entry)


    cur = db.cursor()
    cur.execute(query, (filter,))
    for url, name, language, desc, resolution, thumb in prefered_url_filter(cur.fetchall()):
        if thumb:
            thumb = os.path.join(os.path.dirname(__file__), 'images', thumb)
            li = xbmcgui.ListItem(name, iconImage=thumb, thumbnailImage=thumb)
        else:
            li = xbmcgui.ListItem(name, iconImage='DefaultVideo.png')
        li.setInfo( type="Video", infoLabels={ "Title": name, 'Description': desc, 'Language':language })
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)

    xbmcplugin.endOfDirectory(addon_handle)

db.close()
