# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2015 lambda
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


from g2.libraries import cache
from g2.libraries import addon

from .lib import ui
from . import action


@action
def show():
    cache.get(_changelog, -1, addon.addonInfo('version'), table='changelog')


def _changelog(version):
    with open(addon.addonInfo('changelog')) as fil:
        text = fil.read()

    label = '%s - %s'%(addon.addonInfo('name'), version)

    ui.execute('ActivateWindow(10147)')
    ui.sleep(300)
    win = ui.Window(10147)

    for dummy in range(50):
        try:
            ui.sleep(10)
            win.getControl(1).setLabel(label)
            win.getControl(5).setText(text)
            break
        except Exception:
            pass

    return version
