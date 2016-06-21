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


from g2.libraries import addon
from g2.actions.lib import ui


INFO = {
    'methods': ['notices'],
    'target': 'ui',
}


def notices(notes, playing=None, origin=addon.addonInfo('id'), **dummy_kwargs):
    """Show a Kodi infodialog for each note"""
    if playing != 'video':
        for note in notes:
            ui.infoDialog(note, time=5000, heading=origin)
            ui.sleep(5000)           
