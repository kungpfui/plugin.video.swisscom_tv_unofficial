

import re
import sqlite3
import json
import os
import codecs

from iso639 import iso639_1
from channel_translate import channels

db = sqlite3.connect(u'swctv.db')
db.executescript(u'''
CREATE TABLE IF NOT EXISTS swc_img
(
	name TEXT PRIMARY KEY,
	data BLOB
);

CREATE TABLE IF NOT EXISTS swc_desc
(
	id INTEGER PRIMARY KEY,
	en TEXT,
	de TEXT,
	fr TEXT,
	it TEXT
);

CREATE TABLE IF NOT EXISTS iso639_1
(
	key TEXT PRIMARY KEY,
	en TEXT,
	de TEXT,
	fr TEXT,
	it TEXT
);

CREATE TABLE IF NOT EXISTS swc_tv
(
	stream TEXT PRIMARY KEY,
	name TEXT,
	language TEXT,
	resolution INTEGER,
	desc_id INTEGER,
	image TEXT,
	FOREIGN KEY(language) REFERENCES iso639_1(key),
	FOREIGN KEY(desc_id) REFERENCES swc_desc(id),
	FOREIGN KEY(image) REFERENCES swc_img(name)
);

CREATE TABLE IF NOT EXISTS swc_fav
(
	folder TEXT,
	entry TEXT,
	visits INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fav ON swc_fav (folder, entry);

''')
db.commit()


def sql_qlist(iter):
	return ','.join(['?'] * len(iter))


def replace_n(s, old, new):
	for o in old:
		s = s.replace(o, new)
	return s

packages = dict()
for lang in ('de', 'en', 'fr', 'it'):
	packages[lang] = json.load(open(f'./tmp/channel_list_{lang}.json', 'rb'))

for key, value in iso639_1.items():
	if isinstance(value, tuple):
		row4 = (key, *value)
	else:
		row4 = (key, value, value, value, value)
	db.execute(u"INSERT OR IGNORE INTO iso639_1 VALUES({0})".format(sql_qlist(row4)), row4)


def insert_into(swc, url, name, res: int, key):
	global packages

	try:
		image_path = swc['title'].lower().replace('/', '_').replace(':', '_').encode('ascii', 'ignore').decode() + '.png'
		desc = swc['description']
		row = (url, name, ','.join(swc.get('lang')), res, key, image_path)
		db.execute(u"INSERT INTO swc_tv VALUES({0})".format(sql_qlist(row)), row)

		row3 = (key, *[packages[lang]['channels'][key]['description'] for lang in ('en', 'de', 'fr', 'it')])
		db.execute(u"INSERT OR IGNORE INTO swc_desc VALUES({0})".format(sql_qlist(row3)), row3)

		row2 = (image_path, open(os.path.join('./tmp/logos', image_path), 'rb').read())
		db.execute(u"INSERT OR IGNORE INTO swc_img VALUES({0})".format(sql_qlist(row2)), row2)
		return
	except sqlite3.IntegrityError:
		pass


def find_named_channel(name, url, residx: int):

	for lang in ('de', ): #'en', 'fr', 'it'):
		for key, a in packages['de']['channels'].items():
			#~ print (name, a['name'])
			# try with 'HD' extension
			if a['title'].lower() == name.lower():
				insert_into(a, url, name, residx, key)
			elif a['title'].lower() == name.lower() + ' hd' or a['title'].lower() + ' hd' == name.lower():
				insert_into(a, url, name, residx, key)
			elif a['title'].lower() == name.lower() + ' uhd' or a['title'].lower() + ' uhd' == name.lower():
				insert_into(a, url, name, residx, key)
			elif a['title'].lower() == name.lower() + ' 4k' or a['title'].lower() + ' 4k' == name.lower():
				insert_into(a, url, name, residx, key)

		else:
			row = (url, name, '', residx, -1, None)
			try:
				db.execute("INSERT INTO swc_tv VALUES({0})".format(sql_qlist(row)), row)
				row3 = (-1, '', '', '', '')
				db.execute(u"INSERT OR IGNORE INTO swc_desc VALUES({0})".format(sql_qlist(row3)), row3)
			except sqlite3.IntegrityError:
				pass


re_info = re.compile(r'#EXTINF:-1\s*.*?,(.+)')
info = None

resolutions = ('sd', 'hd', 'uhd')
for residx, resolution in enumerate(resolutions):
	filepath = f'./tmp/swisscom-{resolution}.m3u'
	for line in open(filepath, 'r', encoding='utf-8'):
		mobj = re_info.match(line)
		if mobj:
			info = mobj.group(1).strip()
			# get rid of some strange "iptv-ch.github.io" string parts
			info = info.replace(' CH', '')
			info = info.replace(' (alb)', '')
			info = info.replace(' (bos)', '')
			info = info.replace(' (rus)', '')
			info = info.replace(' (ara)', '')
			info = info.replace(' (spa)', '')

			if info.endswith(' HD'):
				info = info[:-3]
				info = channels.get(info, info)
				info += ' HD'
			elif info.endswith(' UHD'):
				info = info[:-4]
				info = channels.get(info, info)
				info += ' UHD'
			else:
				info = channels.get(info, info)

		if line.startswith((u'rtp', u'udp')) and info:
			find_named_channel(info, line.strip(), residx)
			info = None
db.commit()
db.close()
