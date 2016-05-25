# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2015 Blazetamer
    Copyright (C) 2015 lambda
    Copyright (C) 2015 spoyser
    Copyright (C) 2015 crzen
    Copyright (C) 2016 J0rdyZ65

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import sys
import urllib

from g2.libraries import platform
from g2.libraries.language import _

from .lib import ui
from .lib import downloader


_THREAD = int(sys.argv[1])


def menu(action, **kwargs):
    # (fixme) [int]
    items = downloader.listDownloads()

    cmd = (_('Refresh'), ':Container.Refresh')
    if not items:
        pass

    elif downloader.status():
        ui.addDirectoryItem('[COLOR red]Stop Downloads[/COLOR]', 'download.stop', 'movies.jpg', None, context=cmd)

    else:
        ui.addDirectoryItem('[COLOR FF00b8ff]Start Downloads[/COLOR]', 'download.start', 'movies.jpg', None, context=cmd)

    for i in items:
        percentage, completition_time = downloader.statusItem(i)
        status = ''
        if percentage is not None:
            status = '%d%%'%percentage
            if completition_time:
                status += ' '+completition_time
            status = '[COLOR FF00b8ff][%s][/COLOR] ' % status
        ui.addDirectoryItem(status+i['name'], i['url'], i['image'], None,
            context=(_('Remove from Queue'), 'download.remove&url=%s' % urllib.quote_plus(i['url'])))

    ui.endDirectory()


def start(action, **kwargs):
    ui.execute('Action(Back,10025)')
    if _THREAD > 0:
        ui.resolvedPlugin(_THREAD, True, ui.ListItem(path=''))
    platform.property('downloader', True)
    ui.sleep(3000)
    ui.idle()
    ui.refresh()


def stop(action, **kwargs):
    ui.execute('Action(Back,10025)')
    if _THREAD > 0:
        ui.resolvedPlugin(_THREAD, True, ui.ListItem(path=''))
    platform.property('downloader', False)
    ui.sleep(3000)
    ui.idle()
    ui.refresh()


def remove(action, url, **kwargs):
    downloader.removeDownload(url)
    ui.sleep(500)
    ui.idle()
    ui.refresh()
