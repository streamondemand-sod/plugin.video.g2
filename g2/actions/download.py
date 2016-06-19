# -*- coding: utf-8 -*-

"""
    G2 Add-on
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


import urllib

from g2.libraries import platform
from g2.libraries.language import _

from .lib import ui
from .lib import downloader
from . import action, busyaction


@action
def menu():
    items = downloader.listDownloads()

    cmd = (_('Refresh'), ':Container.Refresh')
    if not items:
        pass
    elif downloader.status():
        ui.addDirectoryItem('[COLOR red]Stop Downloads[/COLOR]', 'download.stop',
                            'movies.jpg', None, context=cmd, isFolder=False)
    else:
        ui.addDirectoryItem('[COLOR FF00b8ff]Start Downloads[/COLOR]', 'download.start',
                            'movies.jpg', None, context=cmd, isFolder=False)

    for i in items:
        percentage, completition_time = downloader.statusItem(i)
        status = ''
        if percentage is not None:
            status = '%d%%'%percentage
            if completition_time:
                status += ' '+completition_time
            status = '[COLOR FF00b8ff][%s][/COLOR] ' % status
        ui.addDirectoryItem(status+i['name'], i['url'], i['image'], None,
                            context=(_('Remove from queue'), 'download.remove&url=%s'%urllib.quote_plus(i['url'])),
                            isAction=False, isFolder=False)
    ui.endDirectory()


@busyaction()
def start():
    platform.property('downloader', True)
    ui.sleep(3000)
    ui.refresh()


@busyaction()
def stop():
    platform.property('downloader', False)
    ui.sleep(3000)
    ui.refresh()


@busyaction()
def remove(url):
    downloader.removeDownload(url)
    ui.sleep(500)
    ui.refresh()
