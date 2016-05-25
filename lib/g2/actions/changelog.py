# -*- coding: utf-8 -*-

"""
    Genesi2 Add-on
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


from g2.libraries import log
from g2.libraries import cache
from g2.libraries import platform
from g2.libraries.language import _

from lib import ui


def show(action, **kwargs):
    cache.get(changelog, -1, platform.addonInfo('version'), table='changelog')


def changelog(version):
    with open(platform.addonInfo('changelog')) as f:
        text = f.read()

    label = '%s - %s' % (_(24054), platform.addonInfo('name'))

    ui.execute('ActivateWindow(10147)')
    ui.sleep(300)
    win = ui.Window(10147)

    for retry in range(50):
        try:
            ui.sleep(10)
            win.getControl(1).setLabel(label)
            win.getControl(5).setText(text)
            break
        except:
            pass

    return True
