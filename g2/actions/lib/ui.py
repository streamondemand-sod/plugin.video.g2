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
import xbmcaddon

from g2.libraries import log
from g2.libraries import addon
from g2.libraries.language import _


_ADDON = xbmcaddon.Addon()
_MONITOR = xbmc.Monitor()

Window = xbmcgui.Window
Dialog = xbmcgui.Dialog
DialogProgress = xbmcgui.DialogProgress
DialogProgressBG = xbmcgui.DialogProgressBG
ListItem = xbmcgui.ListItem
PlayList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
Keyboard = xbmc.Keyboard
Monitor = xbmc.Monitor
Player = xbmc.Player

infoLabel = xbmc.getInfoLabel
sleep = xbmc.sleep
condition = xbmc.getCondVisibility
execute = xbmc.executebuiltin

setContent = xbmcplugin.setContent
finishDirectory = xbmcplugin.endOfDirectory


def addon_icon():
    return _media('icon.png', addon.addonInfo('icon'))


def addon_poster():
    return _media('poster.png', 'DefaultVideo.png')


def addon_banner():
    return _media('banner.png', 'DefaultVideo.png')


def addon_thumb():
    return _media('icon.png', 'DefaultFolder.png', addon.addonInfo('icon'))


def addon_fanart():
    return _media('fanart.jpg', None, addon.addonInfo('fanart'))


def addon_next():
    return _media('next.jpg', 'DefaultFolderBack.png', 'DefaultFolderBack.png')


def artpath():
    return _media('', None, None)


def _media(icon, icon_default, icon_default2=None):
    appearance = addon.setting('appearance').lower()
    if appearance == '-':
        return icon_default
    elif appearance == '':
        return icon_default2
    else:
        return os.path.join(addon.PATH, 'resources', 'media', appearance, icon)

def isfolderaction():
    try:
        thread = int(sys.argv[1])
        return thread > 0
    except Exception:
        return False


def resolvedPlugin():
    try:
        thread = int(sys.argv[1])
        if thread > 0:
            xbmcplugin.setResolvedUrl(thread, True, xbmcgui.ListItem(path=''))
    except Exception:
        pass


def abortRequested(timeout=None):
    return _MONITOR.waitForAbort(timeout) if timeout else _MONITOR.abortRequested()


def keyboard(heading):
    k = xbmc.Keyboard('', heading)
    k.doModal()
    return k.getText() if k.isConfirmed() else None


def infoDialog(message, heading=_ADDON.getAddonInfo('name'), icon=addon_icon(), time=3000):
    try:
        xbmcgui.Dialog().notification(heading, message, icon, time, sound=False)
    except Exception:
        xbmc.executebuiltin("Notification(%s,%s, %s, %s)"%(heading, message, time, icon))


def yesnoDialog(line1, line2='', line3='', heading=_ADDON.getAddonInfo('name'), nolabel='', yeslabel=''):
    return xbmcgui.Dialog().yesno(heading, line1, line2, line3, nolabel=nolabel, yeslabel=yeslabel)


def busydialog(stop=False):
    return xbmc.executebuiltin('Dialog.Close(busydialog)' if stop else 'ActivateWindow(busydialog)')


def idle():
    return busydialog(stop=True)


def refresh(action=None, **kwargs):
    if not action:
        return xbmc.executebuiltin('Container.Refresh')
    else:
        return xbmc.executebuiltin('Container.Update(%s)'%addon.itemaction(action, **kwargs))


def addItem(url, listitem, isFolder=False, totalItems=None):
    try:
        thread = int(sys.argv[1])
    except Exception:
        raise
    if totalItems is None:
        xbmcplugin.addDirectoryItem(thread, url, listitem, isFolder=isFolder)
    else:
        xbmcplugin.addDirectoryItem(thread, url, listitem, isFolder=isFolder, totalItems=totalItems)


def addDirectoryItem(name, query, thumb, icon, context=None, isAction=True, isFolder=True):
    try:
        name = _(name)
    except Exception:
        pass
    url = addon.itemaction(query) if isAction else query
    thumb = thumb if thumb.startswith('http://') else os.path.join(artpath(), thumb) if artpath() is not None else icon
    cmds = []
    if context:
        cmds.append((context[0] if isinstance(context[0], basestring) else _(context[0]),
                     context[1][1:] if context[1][0] == ':' else addon.pluginaction(context[1])))
    item = xbmcgui.ListItem(label=name, iconImage=thumb, thumbnailImage=thumb)
    item.addContextMenuItems(cmds, replaceItems=False)
    fanart = addon_fanart()
    if fanart:
        item.setProperty('Fanart_Image', fanart)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isFolder)


def endDirectory(next_item=None, content=None):
    viewmode = None
    if type(next_item) == dict and next_item.get('next_action') and next_item.get('next_url'):
        log.debug('{m}.{f}: next_action:%s, next_url:%s, next_page:%s, max_pages:%s',
                  next_item.get('next_action'), next_item.get('next_url'), next_item.get('next_page'), next_item.get('max_pages'))

        url = addon.itemaction(next_item['next_action'], url=urllib.quote_plus(next_item['next_url']))

        if next_item.get('max_pages') and next_item.get('next_page'):
            # Label for the "Next Page" item when the max number of pages is known
            next_page_label = _('[I]Next Page[/I]  [{page_of} of {max_pages}]').format(
                page_of=next_item['next_page'],
                max_pages=next_item['max_pages']
            )
        elif next_item.get('next_page'):
            # Label for the "Next Page" item when only the current page number is known
            next_page_label = _('[I]Next Page[/I]  [{page_of}}]').format(
                page_of=next_item['next_page'],
            )
        else:
            next_page_label = _('[I]Next Page[/I]')

        item = xbmcgui.ListItem(label=next_page_label, iconImage=addon_next(), thumbnailImage=addon_next())
        item.addContextMenuItems([], replaceItems=False)
        fanart = addon_fanart()
        if fanart:
            item.setProperty('Fanart_Image', fanart)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
        # On paged directories, replicate the current viewmode when displaying the pages after the first
        if next_item.get('next_page') > 2:
            viewmode = repr(xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId())

    if content:
        xbmcplugin.setContent(int(sys.argv[1]), content)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))

    if viewmode:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % viewmode)


try:
    from .sourcesdialog import *
    from .packagesdialog import *
    from .playerdialog import *
except Exception as ex:
    log.error('{m}: %s', repr(ex), trace=True)
