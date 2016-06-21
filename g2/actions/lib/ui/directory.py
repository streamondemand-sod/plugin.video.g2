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


import os
import sys
import urllib

import xbmc
import xbmcgui
import xbmcplugin

from g2.libraries import log
from g2.libraries import addon
from g2.libraries.language import _


# (fixem)[code]: pylint-fy, so rename all these methods
__all__ = [
   'doQuery',
   'addDirectoryItem',
   'endDirectory',
]


try:
    _thread_id = int(sys.argv[1])
except:
    _thread_id = -1

_artPath = addon.artPath()
_addonFanart = addon.addonFanart()


def doQuery(title):
    k = xbmc.Keyboard('', title)
    k.doModal()
    return k.getText() if k.isConfirmed() else None


def addDirectoryItem(name, query, thumb, icon, context=None, isAction=True, isFolder=True):
    try:
        name = _(name)
    except Exception:
        pass
    url = '%s?action=%s'%(sys.argv[0], query) if isAction else query
    thumb = thumb if thumb.startswith('http://') else os.path.join(_artPath, thumb) if _artPath is not None else icon
    cmds = []
    if context:
        cmds.append((context[0] if isinstance(context[0], basestring) else
                     _(context[0]), context[1][1:] if context[1][0] == ':' else
                     'RunPlugin(%s?action=%s)'%(sys.argv[0], context[1])))
    item = xbmcgui.ListItem(label=name, iconImage=thumb, thumbnailImage=thumb)
    item.addContextMenuItems(cmds, replaceItems=False)
    if _addonFanart:
        item.setProperty('Fanart_Image', _addonFanart)
    xbmcplugin.addDirectoryItem(handle=_thread_id, url=url, listitem=item, isFolder=isFolder)


def endDirectory(next_item=None, content=None, updateListing=False, cacheToDisc=True):
    viewmode = None
    if type(next_item) == dict and next_item.get('next_action') and next_item.get('next_url'):
        log.debug('{m}.{f}: next_action:%s, next_url:%s, next_page:%s, max_pages:%s',
                  next_item.get('next_action'), next_item.get('next_url'), next_item.get('next_page'), next_item.get('max_pages'))

        url = '%s?action=%s&url=%s' % (sys.argv[0], next_item['next_action'], urllib.quote_plus(next_item['next_url']))
        addon_next = addon.addonNext()

        pages = '' if not next_item.get('max_pages') or not next_item.get('next_page') else \
                _('[{page_of} of {max_pages}]').format(page_of=next_item['next_page'], max_pages=next_item['max_pages'])
        item = xbmcgui.ListItem(label=_('[I]Next Page[/I]')+' '+pages, iconImage=addon_next, thumbnailImage=addon_next)
        item.addContextMenuItems([], replaceItems=False)
        if _addonFanart:
            item.setProperty('Fanart_Image', _addonFanart)
        xbmcplugin.addDirectoryItem(handle=_thread_id, url=url, listitem=item, isFolder=True)
        # On paged directories, replicate the current viewmode when displaying the pages after the first
        if next_item.get('next_page') > 2:
            viewmode = repr(xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId())

    if content:
        xbmcplugin.setContent(_thread_id, content)

    xbmcplugin.endOfDirectory(_thread_id, updateListing=updateListing, cacheToDisc=cacheToDisc)

    if viewmode:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % viewmode)
