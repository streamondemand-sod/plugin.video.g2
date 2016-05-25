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


try:
    """
    XBMC/KODI GUI dependent primitives
    """
    import xbmc
    import xbmcgui
    import xbmcplugin
    import xbmcaddon

    _ui = 'xbmc'
except:
    pass

from g2.libraries import platform

if _ui == 'xbmc':
    _homeWindow = xbmcgui.Window(10000)
    _addon = xbmcaddon.Addon()

    Window = xbmcgui.Window
    Dialog = xbmcgui.Dialog
    DialogProgress = xbmcgui.DialogProgress
    DialogProgressBG = xbmcgui.DialogProgressBG
    ListItem = xbmcgui.ListItem
    PlayList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    Keyboard = xbmc.Keyboard
    Monitor = xbmc.Monitor

    infoLabel = xbmc.getInfoLabel
    sleep = xbmc.sleep
    condition = xbmc.getCondVisibility
    execute = xbmc.executebuiltin

    addItem = xbmcplugin.addDirectoryItem
    setContent = xbmcplugin.setContent
    finishDirectory = xbmcplugin.endOfDirectory
    resolvedPlugin = xbmcplugin.setResolvedUrl

    def abortRequested():
        return xbmc.abortRequested

    def infoDialog(message, heading=_addon.getAddonInfo('name'), icon=platform.addonIcon(), time=3000):
        try:
            xbmcgui.Dialog().notification(heading, message, icon, time, sound=False)
        except:
            xbmc.executebuiltin("Notification(%s,%s, %s, %s)"%(heading, message, time, icon))

    def yesnoDialog(line1, line2='', line3='', heading=_addon.getAddonInfo('name'), nolabel='', yeslabel=''):
        return xbmcgui.Dialog().yesno(heading, line1, line2, line3, nolabel, yeslabel)

    def busydialog(stop=False):
        return xbmc.executebuiltin('Dialog.Close(busydialog)' if stop else 'ActivateWindow(busydialog)')

    def idle():
        return busydialog(stop=True)

    def refresh():
        return xbmc.executebuiltin('Container.Refresh')

    try:
        from directory import *
        from sourcesdialog import *
        from player import *
    except:
        pass
else:
    raise Exception('Unknown host platform')
