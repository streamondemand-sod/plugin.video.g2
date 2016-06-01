# -*- coding: utf-8 -*-

"""
    Thanks to Azelphur@GitHub (irc.azelphur.com #azelphur)

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


_log_debug = True


_HOST = "https://api.pushbullet.com/v2/"
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

        url = urlparse.urljoin(_HOST, path)

        log.debug('{m}.{f}: %s %s post=%s, params=%s', method, url, post, params)
        res = requests.request(method, url, json=post, params=params, headers=headers)

        try:
            res.raise_for_status()
            return res.json()
        except Exception as ex:
            log.error('{m}.{f}: %s', ex)
            return None


    def addDevice(self, device_name):
        """ Push a note
            https://docs.pushbullet.com/v2/pushes

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

    def _push(self, data, iden=None, guid=None, recipient=None, recipient_type='device_iden', url=None):
        log.debug('{m}.{f}: %s iden=%s, guid=%s', data, iden, guid)
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
            if type(iden) == list:
                iden[0:] = [push['iden']]
        return push

    # def pushFile(self, recipient, file_name, body, file, file_type=None, recipient_type="device_iden"):
    #     """ Push a file
    #         https://docs.pushbullet.com/v2/pushes
    #         https://docs.pushbullet.com/v2/upload-request

    #         Arguments:
    #         recipient -- a recipient
    #         file_name -- name of the file
    #         file -- a file object
    #         file_type -- file mimetype, if not set, python-magic will be used
    #         recipient_type -- a type of recipient (device, email, channel or client)
    #     """

    #     if not file_type:
    #         try:
    #             import magic
    #         except ImportError:
    #             raise Exception("No file_type given and python-magic isn't installed")

    #         # Unfortunately there's two libraries called magic, both of which do
    #         # the exact same thing but have different conventions for doing so
    #         if hasattr(magic, "from_buffer"):
    #             file_type = magic.from_buffer(file.read(1024))
    #         else:
    #             _magic = magic.open(magic.MIME_TYPE)
    #             _magic.compile(None)

    #             file_type = _magic.file(file_name)

    #             _magic.close()

    #         file.seek(0)

    #     data = {"file_name": file_name,
    #             "file_type": file_type}

    #     upload_request = self._request("GET",
    #                                    "upload-request",
    #                                    None,
    #                                    data)

    #     upload = requests.post(upload_request["upload_url"],
    #                            data=upload_request["data"],
    #                            files={"file": file},
    #                            headers={"User-Agent": "pyPushBullet"})

    #     upload.raise_for_status()

    #     data = {"type": "file",
    #             "file_name": file_name,
    #             "file_type": file_type,
    #             "file_url": upload_request["file_url"],
    #             "body": body}
				
    #     data[recipient_type] = recipient

    #     return self._request("POST", "pushes", data)

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

    def getContacts(self):
        """ Gets your contacts
            https://docs.pushbullet.com/v2/contacts

            returns a list of contacts
        """
        return self._request("GET", "contacts")["contacts"]

    def deleteContact(self, contact_iden):
        """ Delete a contact
            https://docs.pushbullet.com/v2/contacts

            Arguments:
            contact_iden -- the iden of the contact to delete
        """
        return self._request("DELETE", "contacts/" + contact_iden)

    def getUser(self):
        """ Get this users information
            https://docs.pushbullet.com/v2/users
        """
        return self._request("GET", "users/me")

    def events(self, callback=None, evfilter=None, modified=0):
        if callback is None:
            if self.wss:
                log.debug('{m}.{f}: closing web socket %s...', self.wss.bind_addr)
                self.wss.close(immediate=True)
                self.wss = None
            return self.modified
        else:
            self.callback = callback
            self.evfilter = set() if not evfilter else set(evfilter)
            self.modified = modified
            self.wss = PushBulletEvents(self._event_handler, _WSS_REALTIME_EVENTS_STREAM + self.api_key)
            self.wss.connect()
            return self.wss._th

    def __del__(self):
        self.events(None)

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
                # NOTE: this is not perfectly compliant to the API since other active pushes
                # might be returned in the following pages, but it optimize the pull in case
                # no older push is left around. Need to be double checked with pushbullet!!!
                # BTW, wondering when they purge the db of deleted/dismissed pushes?!?
                # if not len(pushes['pushes']):
                #     break
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
