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


import xbmc

from g2.libraries import log
from g2.libraries import cache
from g2.libraries import addon
from .lib.pushbullet import PushBullet


INFO = {
    'methods': ['notices', 'events'],
    'target': 'remote',
}

_PB = PushBullet(addon.setting('pushbullet_apikey'), user_agent=addon.addonInfo('id'))


def notices(notes, playing=None, origin=xbmc.getInfoLabel('System.FriendlyName'), identifier=None, url=None, **kwargs):
    """Push a comulative note to the pushbullet account"""
    body = '\n'.join(notes)
    if body:
        _PB.pushNote(origin, body, iden=identifier, url=url, **kwargs)
    elif identifier:
        _PB.deletePush(identifier[0])


class PushBulletEvents(object):
    def __init__(self, recipient, on_push, on_push_dismissed, on_push_delete):
        self.recipient = recipient
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
                log.debug('{m}.{f}: %s: %s', self.recipient, push)
                if self.recipient and push.get('target_device_iden') != self.recipient:
                    pass # ignore all the pushes but the one addressed to us!
                elif not push['active']:
                    self.on_push_delete(push)
                elif push['dismissed']:
                    self.on_push_dismissed(push)
                else:
                    self.on_push(push)
        else:
            log.notice('{m}.{f}: event %s not filtered: %s', event_type, event_value)


def _nop(dummy):
    pass


def events(start=False, on_push=_nop, on_push_dismissed=_nop, on_push_delete=_nop):
    """Start or stop the reading of the real time events stream"""
    if start:
        def pb_last_modified(dummy_apikey):
            return 0.0
        modified = cache.get(pb_last_modified, -1, _PB.api_key)
        log.debug('{m}.{f}: last modified timestamp: %f (restored from cache)', modified)

        try:
            my_nickname = xbmc.getInfoLabel('System.FriendlyName')
            my_iden = [d.get('iden') for d in _PB.getDevices() if d.get('nickname') == my_nickname]
            if my_iden:
                my_iden = my_iden[0]
                log.notice('{m}.{f}: found device %s with iden %s', my_nickname, my_iden)
            else:
                my_iden = _PB.addDevice(my_nickname)['iden']
                log.notice('{m}.{f}: created new device %s with iden %s', my_nickname, my_iden)
        except Exception as ex:
            my_iden = None
            log.error('{m}.{f}: failed to create a new device: %s', ex)

        return _PB.start_events_handling(PushBulletEvents(my_iden, on_push, on_push_dismissed, on_push_delete).handler,
                                         ['opened', 'pushes', 'closed'], modified=modified)

    try:
        def pb_last_modified(dummy_apikey):
            return _PB.stop_events_handling()
        modified = cache.get(pb_last_modified, 0, _PB.api_key)
        log.debug('{m}.{f}: last modified timestamp: %f (saved to cache)', modified)
    except Exception as ex:
        log.notice('{m}.{f}: %s', ex)
