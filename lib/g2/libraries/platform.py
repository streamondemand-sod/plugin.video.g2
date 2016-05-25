# -*- coding: utf-8 -*-

"""
    Genesi2 Add-on
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
import json

try:
    """
    XBMC/KODI non-GUI dependent primitives
    """
    import xbmc
    import xbmcaddon
    import xbmcvfs

    _platform = 'xbmc'
except:
    pass

if _platform == 'xbmc':

    # Local data
    _addon = xbmcaddon.Addon()

    # Function aliases

    # TODO[code]:
    # move addon* into resources.lib.addon
    # rename:
    #   addonInfo -> info
    #   addonInfo2 -> addonInfo
    #   setSetting -> setting(s, v)
    #   setting -> setting(s)
    addonInfo = _addon.getAddonInfo
    setting = _addon.getSetting
    def freshsetting(setid):
        return xbmcaddon.Addon().getSetting(setid)
    setSetting = _addon.setSetting

    # TODO[code]:
    # move all file related functions & data to resources.lib.files
    translatePath = xbmc.translatePath
    Stat = xbmcvfs.Stat
    makeDir = xbmcvfs.mkdirs
    listDir = xbmcvfs.listdir
    removeDir = xbmcvfs.rmdir
    removeFile = xbmcvfs.delete

    condition = xbmc.getCondVisibility
    execute = xbmc.executebuiltin

    def addonSetting(addon, setting):
        addon = xbmcaddon.Addon(addon)
        return addon.getSetting(setting)

    def addonInfo2(addon, info):
        addon = xbmcaddon.Addon(addon)
        return addon.getAddonInfo(info)

    def addonIcon():
        return _media('icon.png', addonInfo('icon'))

    def addonPoster():
        return _media('poster.png', 'DefaultVideo.png')

    def addonBanner():
        return _media('banner.png', 'DefaultVideo.png')

    def addonThumb():
        return _media('icon.png', 'DefaultFolder.png', addonInfo('icon'))

    def addonFanart():
        return _media('fanart.png', None, addonInfo('fanart'))

    def addonNext():
        return _media('next.jpg', 'DefaultFolderBack.png', 'DefaultFolderBack.png')

    def artPath():
        return _media('', None, None)

    def _media(icon, icon_default, icon_default2=None):
        appearance = setting('appearance').lower()
        if appearance == '-':
            return icon_default
        elif appearance == '':
            return icon_default2
        else:
            # TODO[func]: check that the icon actually exists, otherwise returns the icon_default
            return os.path.join(addonPath, 'resources', 'media', appearance, icon)

    def property(module='', value=None, name='status', addon=addonInfo('id')):
        property_name = addon
        if module: property_name += '.' + module
        if name: property_name += '.' + name
        try:
            import xbmcgui
            _homeWin = xbmcgui.Window(10000)

            if value is None:
                value = _homeWin.getProperty(property_name)
            elif value == '':
                _homeWin.clearProperty(property_name)
                return
            else:
                _homeWin.setProperty(property_name, repr(value))
                return
        except:
            if not hasattr(property, 'properties'):
                property.properties = {}

            if value is None:
                value = property.properties.get(name)
            elif value == '':
                del property.properties[name]
                return
            else:
                property.properties[name] = repr(value)
                return
        try:
            return ast.literal_eval(value) if value else None
        except Exception:
            return None

    # def executeJSONRPC(method, params):
    #     result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}'%(method, params))
    #     result = unicode(result, 'utf-8', errors='ignore')
    #     return json.loads(result)

    # Data
    addonPath = xbmc.translatePath(addonInfo('path')).decode('utf-8')
    dataPath = xbmc.translatePath(addonInfo('profile')).decode('utf-8')

else:
    raise Exception('Unknown host platform')

metacacheFile = os.path.join(dataPath, 'meta.db')
sourcescacheFile = os.path.join(dataPath, 'sources.db')
cacheFile = os.path.join(dataPath, 'cache.db')
databaseFile = os.path.join(dataPath, 'settings.db')
