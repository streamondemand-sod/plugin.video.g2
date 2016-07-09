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
import ast
import sys
import errno

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from g2.libraries import log
from g2.libraries import addon


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


def addon_icon():
    return media('icon', addon.addonInfo('icon'))


def addon_poster():
    return media('poster', 'DefaultVideo.png')


def addon_banner():
    return media('banner', 'DefaultVideo.png')


def addon_thumb():
    return media('icon', addon.addonInfo('icon'))


def addon_fanart():
    return media('fanart', addon.addonInfo('fanart'))


def addon_next():
    return media('next', 'DefaultFolderBack.png')


def resource_themes():
    media_desc = {}
    for media_filepath in [os.path.join(addon.PATH, 'resources', 'media.py'),
                           os.path.join(addon.PROFILE_PATH, 'media.py')]:
        try:
            with open(media_filepath) as fil:
                media_desc.update(ast.literal_eval(fil.read()))
        except IOError as ex:
            if ex.errno != errno.ENOENT:
                raise Exception(ex)
        except Exception as ex:
            log.notice('{m}.{f}: %s: %s', media_filepath, repr(ex))

    if '' not in media_desc:
        # default entry for the g2 resources/media folder
        media_desc[''] = {
            'themes': 'folder',
        }

    themes = {'-': None}
    default_media_path = ['resources', 'media']
    for res, med in media_desc.iteritems():
        if res == '':
            media_path = os.path.join(addon.PATH, *default_media_path)
        else:
            try:
                addon_id = med['addon_id']
                if not addon.condition('System.HasAddon(%s)'%addon_id):
                    continue
                media_path = os.path.join(addon.addonInfo2(addon_id, 'path'), *med.get('media_path', default_media_path))
            except Exception as ex:
                log.notice('{m}.{f}: %s %s: %s', res, med, repr(ex))
                continue

        if med.get('themes') != 'folder':
            # Single theme
            theme_name = res.lower()
            themes[theme_name] = {
                'path': media_path,
                'mappings': med.get('mappings', {}),
            }
            log.debug('{m}.{f}: %s: %s: %s', res, theme_name, themes[res])
        else:
            # Multiple themes
            for theme in os.listdir(media_path):
                theme_path = os.path.join(media_path, theme)
                if os.path.isdir(theme_path):
                    theme_name = theme if res == '' else '%s:%s'%(res, theme)
                    theme_name = theme_name.lower()
                    themes[theme_name] = {
                        'path': theme_path,
                        'mappings': med.get('mappings', {}),
                    }
                    log.debug('{m}.{f}: %s: %s, %s', res, theme_name, themes[theme_name])

    return themes


_RESOURCE_THEMES = resource_themes()


def media(icon, icon_default=None):
    if not icon:
        return icon_default or 'DefaultFolder.png'

    if '://' in icon:
        return icon

    appearance = addon.setting('appearance').lower()
    if appearance in ['-', ''] or appearance not in _RESOURCE_THEMES:
        return icon_default or 'DefaultFolder.png'

    theme = _RESOURCE_THEMES[appearance]
    theme_path = theme['path']
    icon = theme['mappings'].get(icon, icon)

    icon_path = os.path.join(theme_path, icon)
    icon, ext = os.path.splitext(icon)
    if ext and os.path.isfile(icon_path):
        return icon_path

    for ext in ['.png', '.jpg']:
        icon_path = os.path.join(theme_path, icon+ext)
        if os.path.isfile(icon_path):
            return icon_path

    return icon_default or 'DefaultFolder.png'


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
    default = addon.prop('ui', name=heading)
    k = xbmc.Keyboard(default or '', heading)
    k.doModal()
    if not k.isConfirmed():
        return None
    default = k.getText()
    addon.prop('ui', default, name=heading)
    return default


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


def viewmode():
    return repr(xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId())


def setcontent(content):
    if content:
        xbmcplugin.setContent(int(sys.argv[1]), content)


def addsortmethods(methods):
    if methods:
        for method in methods:
            # (fixme) map methods name to numbers
            xbmcplugin.addSortMethod(int(sys.argv[1]), method)


def finish():
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def additem(url, item, isFolder=False, totalItems=None):
    if totalItems is None:
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isFolder)
    else:
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isFolder, totalItems=totalItems)
