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

try:
    """
    XBMC/KODI non-GUI dependent primitives
    """
    import xbmc
    import xbmcaddon
    import xbmcvfs

    _platform = 'xbmc'
except Exception:
    pass

if _platform == 'xbmc':
    _addon = xbmcaddon.Addon()

    # (fixme)[code]: put all addons related methods in g2.libraries.addon
    addonInfo = _addon.getAddonInfo
    setting = _addon.getSetting
    def freshsetting(setid):
        return xbmcaddon.Addon().getSetting(setid)
    setSetting = _addon.setSetting

    condition = xbmc.getCondVisibility
    execute = xbmc.executebuiltin

    def addonSetting(addon, setid):
        addon = xbmcaddon.Addon(addon)
        return addon.getSetting(setid)

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
            return os.path.join(addonPath, 'resources', 'media', appearance, icon)

    def property(module='', value=None, name='status', addon=addonInfo('id')):
        property_name = addon
        if module:
            property_name += '.' + module
        if name:
            property_name += '.' + name
        try:
            import xbmcgui
            home_win = xbmcgui.Window(10000)

            if value is None:
                value = home_win.getProperty(property_name)
            elif value == '':
                home_win.clearProperty(property_name)
                return
            else:
                home_win.setProperty(property_name, repr(value))
                return
        except Exception:
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

    # (fixme) addon.runplugin(action, **kwargs)
    # build the RunPlugin command using sys.argv[0] as plugin id, action=action and
    # kwargs as key=value
    # replace all the 'RunPlugin...' strings

    # def executeJSONRPC(method, params):
    #     result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}'%(method, params))
    #     result = unicode(result, 'utf-8', errors='ignore')
    #     return json.loads(result)

    addonPath = xbmc.translatePath(addonInfo('path')).decode('utf-8')

else:
    raise Exception('Unknown host platform')
