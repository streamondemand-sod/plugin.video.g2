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


from g2.libraries import log
from g2.libraries import platform
from g2.notifiers.lib.pushbullet import PushBullet


_log_debug = True


INFO = {
    'target': 'remote',
}

_PB = PushBullet(platform.setting('pushbullet_apikey'))


def notices(notes, origin=platform.addonInfo('id'), identifier=None, **kwargs):
    """Push a comulative note to the pushbullet account"""
    # (fixme) do not call if apikey is none or invalid
    # (fixme) add pushbullet_email as non configurable setting and clear it if auth fails
    # (fixme) add a 'device' identifier to the origin, such as Kodi@Home, to be configured in settings
    body = '\n'.join(notes)
    if body:
        _PB.pushNote(origin, body, iden=identifier, **kwargs)
    elif identifier:
        _PB.deletePush(identifier[0])


class PushBulletEvents(object):
    def __init__(self, on_push, on_push_dismissed, on_push_delete):
        self.on_push = on_push
        self.on_push_dismissed = on_push_dismissed
        self.on_push_delete = on_push_delete

    def handler(self, event_value, event_type):
        if event_type == 'opened':
            log.notice('{m}.{f}: connected to the pushbullet websocket for real time events (%s)', repr(event_value))

        elif event_type == 'closed':
            code, reason = event_value
            log.notice('{m}.{f}: pushbullet websocket closed [code:%s, reason:%s]', code, reason)

        elif event_type == 'pushes':
            for push in event_value:
                log.debug('{m}.{f}: new/upd push: %s', push)
                if not push['active']:
                    self.on_push_delete(push)
                elif push['dismissed']:
                    self.on_push_dismissed(push)
                else:
                    self.on_push(push)

        else:
            log.notice('{m}.{f}: event %s not filtered: %s', event_type, event_value)


def events(start=False, on_push=lambda p: True, on_push_dismissed=lambda p: True, on_push_delete=lambda p: True):
    """Start or stop the reading of the real time events stream"""
    if not start:
        _PB.events(None)
    else:
        return _PB.events(PushBulletEvents(on_push, on_push_dismissed, on_push_delete).handler,
                          ['opened', 'pushes', 'closed'])
