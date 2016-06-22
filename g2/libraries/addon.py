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


import ast
import sys

import xbmc
import xbmcaddon
import xbmcvfs


_addon = xbmcaddon.Addon()

addonInfo = _addon.getAddonInfo
setting = _addon.getSetting

setSetting = _addon.setSetting

condition = xbmc.getCondVisibility
execute = xbmc.executebuiltin


def freshsetting(setid):
    return xbmcaddon.Addon().getSetting(setid)


def addonSetting(addon, setid):
    addon = xbmcaddon.Addon(addon)
    return addon.getSetting(setid)


def addonInfo2(addon, info):
    addon = xbmcaddon.Addon(addon)
    return addon.getAddonInfo(info)


def prop(module='', value=None, name='status', addon=addonInfo('id')):
    prop_name = addon
    if module:
        prop_name += '.' + module
    if name:
        prop_name += '.' + name
    try:
        import xbmcgui
        home_win = xbmcgui.Window(10000)

        if value is None:
            value = home_win.getProperty(prop_name)
        elif value == '':
            home_win.clearProperty(prop_name)
            return
        else:
            home_win.setProperty(prop_name, repr(value))
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


def pluginaction(action_name, **kwargs):
    return 'RunPlugin(%s)'%itemaction(action_name, **kwargs)


def itemaction(action_name, **kwargs):
    return _action('%s?action=%s'%(sys.argv[0] or 'plugin://%s/'%addonInfo('id'), action_name), **kwargs)


def scriptaction(action_name, **kwargs):
    return 'RunScript(%s)'%_action(action_name, args_sep=',', **kwargs)


def _action(action_name, args_sep='&', **kwargs):
    return action_name + ('' if not len(kwargs) else
                          args_sep.join(['']+['%s=%s'%(k, v) for k, v in kwargs.iteritems()]))


# def executeJSONRPC(method, params):
#     result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}'%(method, params))
#     result = unicode(result, 'utf-8', errors='ignore')
#     return json.loads(result)


addonPath = xbmc.translatePath(addonInfo('path')).decode('utf-8')
