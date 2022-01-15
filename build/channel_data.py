#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get public channel list files
"""

import os
import re
import sys
import subprocess
import time
import json
import multiprocessing
from urllib.request import urlopen


def download_iptv_lists(dir=os.curdir):
	for resolution in ('sd', 'hd', 'uhd'):
		iptv_file = f"https://github.com/iptv-ch/iptv-ch.github.io/raw/master/swisscom-{resolution}.m3u"

		f = urlopen(iptv_file)
		open(os.path.join(dir, f'swisscom-{resolution}.m3u'), 'wb').write(f.read())

def download_channel_lists(dir=os.curdir):
	if not os.path.exists(dir):
		os.makedirs(dir)

	for lang in ('de', 'en', 'it', 'fr'):
		channel_list = f"https://www.swisscom.ch/portal-services/portal-integration/ws/channellist/channel-list/{lang}"

		f = urlopen(channel_list)
		open(os.path.join(dir, f'channel_list_{lang}.json'), 'wb').write(f.read())

def download_logos(channel_list, dir=os.curdir, resolution=256):
	if not os.path.exists(dir):
		os.makedirs(dir)

	js = json.load(open(channel_list, 'rb'))

	channels = js['channels']
	for key in channels:
		imageurl = "{logo}".format(**channels[key]).format(resolution=f'W{resolution}', fileType='png')
		filename = channels[key]['title'].lower().replace('/', '_').replace(':', '_').encode('ascii', 'ignore').decode() + '.png'

		imagepath = os.path.join(dir, filename)
		if not os.path.exists(imagepath):
			f = urlopen(imageurl)
			open(imagepath, 'wb').write(f.read())


def optimize_png(semaphore, filepath):
	optipng = 'optipng.exe' if sys.platform == 'win32' else 'optipng'
	subprocess.call([optipng, '-o9', filepath])
	semaphore.get()


def optimize_logos(dir):
	fileexts = ('.png',)

	opti_queue = multiprocessing.Queue(multiprocessing.cpu_count())
	for root, dirs, files in os.walk(dir):
		for name in files:
			if name.endswith(fileexts):
				filepath = os.path.join(root, name)
				opti_queue.put(filepath)
				p = multiprocessing.Process(target=optimize_png, args=(
					opti_queue,
					filepath
					))
				p.start()

	# wait until all task are finished
	while not opti_queue.empty():
		time.sleep(1.0)


def main():
	logo_dir = './tmp/logos'
	list_dir = './tmp'

	download_iptv_lists(list_dir)
	download_channel_lists(list_dir)
	download_logos('./tmp/channel_list_de.json', logo_dir)
	optimize_logos(logo_dir)


if __name__ == '__main__':
	main()
