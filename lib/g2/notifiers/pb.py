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


from g2.libraries import platform
from g2.notifiers.lib.pushbullet import PushBullet


INFO = {
    'target': 'remote',
}

_PB = PushBullet(platform.setting('pushbullet_apikey'))


def notices(notes, origin=platform.addonInfo('id'), **dummy_kwargs):
    """Push a comulative note to the pushbullet account"""
    # (fixme) do not call if apikey is none or invalid
    # (fixme) add pushbullet_email as non configurable setting and clear it if auth fails
    _PB.pushNote(None, origin, '\n'.join(notes))
