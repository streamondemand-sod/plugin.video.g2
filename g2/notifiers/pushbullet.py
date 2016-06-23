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
from g2.libraries import cache
from g2.libraries import addon
from .lib.pb import PushBullet

from g2.actions.lib import ui

INFO = {
    'methods': ['notices', 'events'],
    'targets': ['remote'],
}

_PB = PushBullet(addon.setting('pushbullet_apikey'), user_agent=addon.addonInfo('id'))
_MYNAME = __name__.split('@')[-1].split('.')[-1]


def enabled():
    return addon.setting('pushbullet_apikey') and addon.setting('pushbullet_email')


def notices(notes, playing=None, origin=ui.infoLabel('System.FriendlyName'), identifiers=None, url=None, **kwargs):
    """Push a comulative note to the pushbullet account"""

    if not enabled():
        return

    body = '\n'.join(notes)
    if body:
        push = _PB.pushNote(origin, body, url=url, **kwargs)
        if type(identifiers) is dict:
            identifiers[_MYNAME] = push['iden']
    elif identifiers and _MYNAME in identifiers: # Delete push
        _PB.deletePush(identifiers[_MYNAME])


class PushBulletEvents(object):
    def __init__(self, recipient, on_push, on_push_dismiss, on_push_delete):
        self.recipient = recipient
        self.on_push = on_push
        self.on_push_dismiss = on_push_dismiss
        self.on_push_delete = on_push_delete

    def handler(self, event_value, event_type):
        log.debug('{m}.{f}: %s: %s, %s', self.recipient, event_type, event_value)

        if event_type == 'opened':
            log.notice('{m}.{f}: connected to the pushbullet websocket for real time events (%s)', repr(event_value))

        elif event_type == 'closed':
            code, reason = event_value
            log.notice('{m}.{f}: pushbullet websocket closed [code:%s, reason:%s]', code, reason)

        elif event_type == 'pushes':
            for push in event_value:
                iden = push.get('iden')
                if not iden:
                    pass
                elif not push['active']:
                    self.on_push_delete(_MYNAME, iden)
                elif push['dismissed']:
                    self.on_push_dismiss(_MYNAME, iden)
                elif not self.recipient or push.get('target_device_iden') == self.recipient:
                    self.on_push(_MYNAME, iden, push.get('title'), push.get('body'), push.get('url'))
        else:
            log.notice('{m}.{f}: event %s not filtered: %s', event_type, event_value)


def _nop(*dummy_args):
    pass


def events(start=False, on_push=_nop, on_push_dismiss=_nop, on_push_delete=_nop):
    """Start or stop the reading of the real time events stream"""

    if start:
        if not enabled():
            return None

        def pb_last_modified(dummy_apikey):
            return 0.0
        modified = cache.get(pb_last_modified, -1, _PB.api_key)
        log.debug('{m}.{f}: last modified timestamp: %f (restored from cache)', modified)

        try:
            my_nickname = ui.infoLabel('System.FriendlyName')
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

        return _PB.start_events_handling(PushBulletEvents(my_iden, on_push, on_push_dismiss, on_push_delete).handler,
                                         ['opened', 'pushes', 'closed'], modified=modified)

    try:
        if not _PB.events_handling():
            return None

        def pb_last_modified(dummy_apikey):
            return _PB.stop_events_handling()
        modified = cache.get(pb_last_modified, 0, _PB.api_key)
        log.debug('{m}.{f}: last modified timestamp: %f (saved to cache)', modified)
    except Exception as ex:
        log.notice('{m}.{f}: %s', ex)

    return None
