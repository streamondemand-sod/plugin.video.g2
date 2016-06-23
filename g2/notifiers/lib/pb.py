# -*- coding: utf-8 -*-

"""
    Thanks to Azelphur@GitHub (irc.azelphur.com #azelphur) for the original code

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


import json
import urlparse

import requests
from requests.packages import urllib3

from g2.libraries import log
from .ws4py.client.threadedclient import WebSocketClient


_BASE_URL = "https://api.pushbullet.com/v2/"
_WSS_REALTIME_EVENTS_STREAM = "wss://stream.pushbullet.com/websocket/"


urllib3.disable_warnings()


class PushBulletEvents(WebSocketClient):
    def __init__(self, callback, *args, **kwargs):
        WebSocketClient.__init__(self, *args, **kwargs)
        self.callback = callback

    def opened(self):
        self.callback(self.bind_addr, 'opened')

    def closed(self, code, reason=None):
        self.callback((code, reason), 'closed')

    def received_message(self, message):
        try:
            self.callback(json.loads(str(message)), 'message')
        except Exception:
            self.callback(message, 'error')


class PushBullet:
    def __init__(self, api_key, user_agent=None):
        self.api_key = api_key
        self.user_agent = user_agent
        self.wss = None
        self.modified = 0
        self.evfilter = []
        self.callback = None
        self.reqsess = None

    def _request(self, method, path, post=None):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Access-Token": self.api_key,
        }
        if self.user_agent:
            headers.update({
                "User-Agent": self.user_agent,
            })

        if method != 'GET':
            params = None
        else:
            params = post
            post = None

        url = urlparse.urljoin(_BASE_URL, path)

        log.debug('{m}.{f}: %s%s %s post=%s, params=%s', '(session) ' if self.reqsess else '', method, url, post, params)
        reqobj = self.reqsess if self.reqsess else requests
        res = reqobj.request(method, url, json=post, params=params, headers=headers)

        try:
            res.raise_for_status()
            return res.json()
        except Exception as ex:
            log.error('{m}.{f}: %s', ex)
            return None


    def addDevice(self, device_name):
        """ Add a device
            https://docs.pushbullet.com/v2/devices

            Arguments:
            device_name -- Human readable name for device
            type -- stream, thats all there is currently

        """
        data = {
            "nickname": device_name,
            "type": "stream",
        }
        return self._request("POST", "devices", data)

    def getDevices(self):
        """ Get devices
            https://docs.pushbullet.com/v2/devices

            Get a list of devices, and data about them.
        """
        return self._request("GET", "devices")["devices"]

    def deleteDevice(self, device_iden):
        """ Delete a device
            https://docs.pushbullet.com/v2/devices

            Arguments:
            device_iden -- iden of device to push to
        """
        return self._request("DELETE", "devices/"+device_iden)

    def pushNote(self, title, body, **kwargs):
        """ Push a note
            https://docs.pushbullet.com/v2/pushes

            Arguments:
            recipient -- a recipient
            title -- a title for the note
            body -- the body of the note
            recipient_type -- a type of recipient (device, email, channel or client)
        """
        data = {
            "type": "note",
            "title": title,
            "body": body,
        }
        return self._push(data, **kwargs)

    def pushAddress(self, name, address, **kwargs):
        """ Push an address
            https://docs.pushbullet.com/v2/pushes

            Arguments:
            recipient -- a recipient
            name -- name for the address, eg "Bobs house"
            address -- address of the address
            recipient_type -- a type of recipient (device, email, channel or client)
        """
        data = {
            "type": "address",
            "name": name,
            "address": address,
        }
        return self._push(data, **kwargs)

    def pushList(self, title, items, **kwargs):
        """ Push a list
            https://docs.pushbullet.com/v2/pushes

            Arguments:
            recipient -- a recipient
            title -- a title for the list
            items -- a list of items
            recipient_type -- a type of recipient (device, email, channel or client)
        """
        data = {
            "type": "list",
            "title": title,
            "items": items,
        }
        return self._push(data, **kwargs)

    def pushLink(self, title, url, **kwargs):
        """ Push a link
            https://docs.pushbullet.com/v2/pushes

            Arguments:
            recipient -- a recipient
            title -- link title
            url -- link url
            recipient_type -- a type of recipient (device, email, channel or client)
        """
        data = {
            "type": "link",
            "title": title,
            "url": url,
        }
        return self._push(data, **kwargs)

    def _push(self, data, guid=None, recipient=None, recipient_type='device_iden', url=None):
        log.debug('{m}.{f}: %s: guid=%s', data, guid)
        if guid:
            data.update({
                'guid': guid,
            })
        if recipient:
            data.update({
                recipient_type: recipient,
            })
        if url:
            data.update({
                'url': url,
            })

        push = self._request("POST", "pushes", data)
        if push:
            self._update_modified([push])
        return push

    def getPushHistory(self, modified_after=0, cursor=None, active=True):
        """ Get Push History
            https://docs.pushbullet.com/v2/pushes

            Returns a list of pushes

            Arguments:
            modified_after -- Request pushes modified after this timestamp
            cursor -- Request another page of pushes (if necessary)
        """
        data = {
            # NOTE: used repr as otherwise the float str() method limits
            # the precision to 12 decimal digits only (vs. 16)
            "modified_after": repr(modified_after),
            'active': repr(active).lower(),
        }
        if cursor:
            data.update({
                "cursor": cursor,
            })

        pushes = self._request("GET", "pushes", data)
        self._update_modified(pushes['pushes'])
        return pushes

    def _update_modified(self, pushes):
        self.modified = max([self.modified] + [p['modified'] for p in pushes])
        log.debug('{m}.{f}: modified time updated to %s', self.modified)

    def deletePush(self, push_iden):
        """ Delete push
            https://docs.pushbullet.com/v2/pushes

            Arguments:
            push_iden -- the iden of the push to delete
        """
        return self._request("DELETE", "pushes/" + push_iden)

    def getUser(self):
        """ Get this users information
            https://docs.pushbullet.com/v2/users
        """
        return self._request("GET", "users/me")

    def start_events_handling(self, callback, evfilter=None, modified=0):
        """ Start the thread for handling the pb events
            - Monitor the websocket real time events
            - Pull the push history and give the new events to the callback
        """
        self.callback = callback
        self.evfilter = set() if not evfilter else set(evfilter)
        self.modified = modified
        if not self.wss:
            self.wss = PushBulletEvents(self._event_handler, _WSS_REALTIME_EVENTS_STREAM + self.api_key)
            self.wss.connect()
        if not self.reqsess:
            self.reqsess = requests.Session()
        return self.wss._th

    def events_handling(self):
        return self.wss is not None
        
    def stop_events_handling(self):
        if self.wss:
            log.debug('{m}.{f}: closing web socket %s...', self.wss.bind_addr)
            self.wss.close(immediate=True)
            self.wss = None
        if self.reqsess:
            self.reqsess.close()
            self.reqsess = None
        return self.modified

    def __del__(self):
        self.stop_events_handling()

    def _event_handler(self, event_value, event_type):
        log.debug('{m}.{f}: %s: %s', event_value, event_type)

        if event_type != 'message':
            if self._event_filter([event_type]):
                self.callback(event_value, event_type)
            if event_type == 'closed':
                self.wss = None
                return
            if event_type != 'opened':
                return
            event_value = {
                'type': 'tickle',
                'subtype': 'push',
            }

        message_type = event_value.get('type')
        if message_type == 'tickle' and event_value.get('subtype') == 'push':
            if not self._event_filter(['pushes']):
                return

            cursor = None
            modified = self.modified
            while True:
                log.debug('{m}.{f}: fetching pushes since %s [%s]', modified, cursor)
                pushes = self.getPushHistory(modified, cursor, active=False)
                if pushes is None:
                    break
                log.debug('{m}.{f}: got %d pushes', len(pushes['pushes']))
                self.callback(pushes['pushes'], 'pushes')
                if 'cursor' in pushes:
                    cursor = pushes['cursor']
                else:
                    break
            return

        if message_type == 'nop':
            if self._event_filter(['nop']):
                self.callback(event_value, 'nop')
            return

    def _event_filter(self, events):
        return '*' in self.evfilter or set(events) & self.evfilter
