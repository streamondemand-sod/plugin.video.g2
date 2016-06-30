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


from g2.libraries import ui
from g2.libraries import cache
from g2.libraries import addon
from g2.libraries.language import _

from . import action


@action
def menu():
    ui.addDirectoryItem(_('[B]SETTINGS[/B]'), 'tools.settings&category=0',
                        'settings.jpg', 'DefaultAddonProgram.png', isFolder=False)
    ui.addDirectoryItem(_('[B]SETTINGS[/B] : Providers'), 'tools.settings&category=3',
                        'settings.jpg', 'DefaultAddonProgram.png', isFolder=False)
    ui.addDirectoryItem(_('[B]SETTINGS[/B] : Resolvers'), 'tools.settings&category=4',
                        'settings.jpg', 'DefaultAddonProgram.png', isFolder=False)
    ui.addDirectoryItem(_('[B]G2[/B] : Packages'), 'packages.dialog',
                        'tools.jpg', 'DefaultAddonProgram.png', isFolder=False)
    ui.addDirectoryItem(_('[B]G2[/B] : Clear cache...'), 'tools.clearcache',
                        'cache.jpg', 'DefaultAddonProgram.png', isFolder=False)
    ui.endDirectory()


@action
def settings(category='0'):
    ui.idle()
    ui.execute('Addon.OpenSettings(%s)'%addon.addonInfo('id'))
    ui.execute('SetFocus(%i)' % (int(category) + 100))


@action
def clearcache():
    ui.idle()
    yes = ui.yesnoDialog(_('Are you sure?'), '', '')
    if yes and cache.clear():
        ui.infoDialog(_('Process Complete'))
