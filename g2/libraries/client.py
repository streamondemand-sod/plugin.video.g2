# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016-2017 J0rdyZ65

    parseDOM
    Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

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


import re
import time
import HTMLParser

import requests
from requests.packages import urllib3
from requests.structures import CaseInsensitiveDict

from g2.libraries import log


urllib3.disable_warnings()


codes = requests.codes


class Session(requests.Session):
    def __init__(self, debug=False, raise_error=False, headers=None, **kwargs):
        requests.Session.__init__(self, **kwargs)
        if headers:
            self.headers.update(headers)
        self.session_debug = _set_debug(debug)
        self.session_raise_error = raise_error

    def request(self, url, data=None, json=None, **kwargs):
        if not data and not json:
            return self._client_request(self._client_get, url, **kwargs)
        else:
            return self._client_request(self._client_post, url, data=data, json=json, **kwargs)

    def get(self, url, **kwargs):
        return self._client_request(self._client_get, url, **kwargs)

    def post(self, url, **kwargs):
        return self._client_request(self._client_post, url, **kwargs)

    def _client_request(self, method, url, raise_error=False, debug=None, **kwargs):
        debug = self.session_debug | _set_debug(debug)
        raise_error = raise_error or self.session_raise_error

        if _debug(debug, 'cookies') and self.cookies:
            for cke, val in self.cookies.iteritems():
                log.debug('{m}.{f}: session.cookie: %s=%s', cke, val, debug=True)

        res = _request(method, url, raise_error=raise_error, debug=debug, **kwargs)

        if _debug(debug, 'adapter'):
            conn = self.get_adapter(url).poolmanager.connection_from_url(url)
            log.debug('{m}.{f}: session.adapter: connections:%d, requests:%d',
                      conn.num_connections, conn.num_requests, debug=True)

        return res

    def _client_get(self, url, **kwargs):
        return requests.Session.request(self, 'GET', url, **kwargs)

    def _client_post(self, url, **kwargs):
        return requests.Session.request(self, 'POST', url, **kwargs)


def request(url, debug=None, data=None, json=None, **kwargs):
    if not data and not json:
        return _request(requests.get, url, debug=_set_debug(debug), **kwargs)
    else:
        return _request(requests.post, url, debug=_set_debug(debug), data=data, json=json, **kwargs)


def get(url, debug=None, **kwargs):
    return _request(requests.get, url, debug=_set_debug(debug), **kwargs)


def post(url, debug=None, **kwargs):
    return _request(requests.post, url, debug=_set_debug(debug), **kwargs)


def _request(method, url, raise_error=None, debug=None, **kwargs):
    logperf = log.perfactive()
    if logperf:
        started = time.time()

    if _debug(debug, 'request'):
        log.debug('{m}.{f}: request.method: %s', method, debug=True)
        log.debug('{m}.{f}: request.url: %s', url, debug=True)
        if kwargs.get('data'):
            for var, val in kwargs.get('data').iteritems():
                log.debug('{m}.{f}: request.data: %s=%s', var, val, debug=True)
        if kwargs.get('json'):
            log.debug('{m}.{f}: request.json: %s', kwargs.get('json'), debug=True)
        headers = CaseInsensitiveDict(kwargs.get('headers', {}))
        if hasattr(method, 'im_self') and isinstance(method.im_self, Session):
            for hdr, val in method.im_self.headers.iteritems():
                if hdr not in headers:
                    log.debug('{m}.{f}: session.headers: %s=%s', hdr, val, debug=True)
        if headers == dict:
            for hdr, val in headers.iteritems():
                log.debug('{m}.{f}: request.headers: %s=%s', hdr, val, debug=True)

    res = method(url, **kwargs)

    if _debug(debug, 'response'):
        for hdr, val in res.headers.iteritems():
            log.debug('{m}.{f}: response.headers: %s=%s', hdr, val, debug=True)
        if res.cookies:
            for cke, val in res.cookies.iteritems():
                log.debug('{m}.{f}: response.cookies: %s=%s', cke, val, debug=True)
        if res.history:
            log.debug('{m}.{f}: response.history: %s', res.history, debug=True)
        log.debug('{m}.{f}: response.status: %s', res.status_code, debug=True)

    if _debug(debug, 'content'):
        if kwargs.get('stream'):
            log.debug('{m}.{f}: response.content[%s]: not logged because of stream mode', res.encoding, debug=True)
        else:
            log.debug('{m}.{f}: response.content[%s]: %s', res.encoding, res.content, debug=True)

    if logperf:
        log.debug('{m}.{f}: {cf}.{m}.{f}: %s: completed in %.2f seconds', url, time.time()-started, debug=True)

    if raise_error:
        res.raise_for_status()

    return res


def _set_debug(debug):
    return set() if not debug else set(debug) if type(debug) in [list, set, tuple] else set([debug])


def _debug(debug, filters):
    return debug and (filters in debug or True in debug)


def agent():
    return 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0'


def replaceHTMLCodes(txt):
    txt = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", txt)
    txt = HTMLParser.HTMLParser().unescape(txt)
    txt = txt.replace("&quot;", "\"")
    txt = txt.replace("&amp;", "&")
    return txt


_DEBUG = None


def parseDOM(html, name=u"", attrs=None, ret=False):
    global _DEBUG
    _DEBUG = log.debugactive()

    if _DEBUG:
        log.debug("{m}.{f}: Name: "+repr(name)+" - Attrs:"+repr(attrs)+" - Ret: "+repr(ret)+" - HTML: "+str(type(html)))

    if not name.strip():
        if _DEBUG:
            log.debug("{m}.{f}: Missing tag name")
        return u""

    if isinstance(html, str):
        try:
            html = [html.decode("utf-8")] # Replace with chardet thingy
        except Exception:
            if _DEBUG:
                log.debug("{m}.{f}: Couldn't decode html binary string. Data length: " + repr(len(html)))
            html = [html]
    elif isinstance(html, unicode):
        html = [html]
    elif not isinstance(html, list):
        if _DEBUG:
            log.debug("{m}.{f}: Input isn't list or string/unicode.")
        return u""

    ret_lst = []
    for item in html:
        temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
        for match in temp_item:
            item = item.replace(match, match.replace("\n", " "))

        lst = _getDOMElements(item, name, attrs)

        rets = []
        item_offset = 0
        for match in lst:
            if ret:
                match_string = match if isinstance(match, basestring) else match.group()
                if _DEBUG:
                    log.debug("{m}.{f}: Getting attribute(s) %s content for %s", ret, match_string)
                if isinstance(ret, basestring):
                    rets += _getDOMAttributes(match_string, name, ret)
                else:
                    retdict = {}
                    for i in ret:
                        retdict[i] = _getDOMAttributes(match_string, name, i)
                    rets.append(retdict)

            elif match.start() < item_offset:
                if _DEBUG:
                    log.debug("{m}.{f}: Skipping %s@%d as included in the previous element", match.group(), match.start())

            else:
                if _DEBUG:
                    log.debug("{m}.{f}: Getting element content for %s@%d", match.group(), match.start())
                temp = _getDOMContent(item, item_offset, name, match.group()).strip()
                item_offset = item.find(temp, item_offset) + len(temp)
                rets.append(temp)

        ret_lst += rets

    if _DEBUG:
        log.debug("{m}.{f}: Done: " + repr(ret_lst))
    return ret_lst


def _getDOMElements(item, name, attrs):
    if _DEBUG:
        log.debug("{m}.{f}:")

    if not attrs:
        if _DEBUG:
            log.debug("{m}.{f}: No attributes specified, matching on name only")
        lst = [m for m in re.compile('(<' + name + '(?:>| .*?>))', re.M|re.S).finditer(item)]

    else:
        lst = []
        for key in attrs:
            # (fixme): collapse the two re.compile in a single one where the opening quote, if present,
            #   must match the closing quote, otherwise in scenario where there is a mix of the two
            #   format only the elements with the quotes are returned!
            lst2 = [m for m in re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))',
                                          re.M|re.S).finditer(item)]
            if len(lst2) == 0 and attrs[key].find(" ") == -1:  # Try matching without quotation marks
                lst2 = [m for m in re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))',
                                              re.M|re.S).finditer(item)]
            if len(lst) == 0:
                if _DEBUG:
                    log.debug("{m}.{f}: Setting main list " + repr(lst2))
                lst = lst2
                lst2 = []
            else:
                if _DEBUG:
                    log.debug("{m}.{f}: Setting new list " + repr(lst2))
                test = range(len(lst))
                test.reverse()
                for i in test:  # Delete anything missing from the next list.
                    if lst[i].group() not in lst2.group():
                        if _DEBUG:
                            log.debug("{m}.{f}: Purging mismatch " + str(len(lst)) + " - " + repr(lst[i].group()))
                        del lst[i]

    if _DEBUG:
        log.debug("{m}.{f}: Done: " + str(type(lst)))
    return lst


def _getDOMContent(html, offset, name, match):
    if _DEBUG:
        log.debug("{m}.{f}: Match: " + match)

    endstr = u"</" + name  # + ">"

    start = html.find(match, offset)
    end = html.find(endstr, start)
    pos = html.find("<" + name, start + 1)

    if _DEBUG:
        log.debug(str(start) + " < " + str(end) + ", pos = " + str(pos) + ", endpos: " + str(end))

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(endstr, end + len(endstr))
        if tend != -1:
            end = tend
        pos = html.find("<" + name, pos + 1)
        if _DEBUG:
            log.debug("{m}.{f}: loop: " + str(start) + " < " + str(end) + " pos = " + str(pos))

    if _DEBUG:
        log.debug("{m}.{f}: start: %s, len: %s, end: %s" % (start, len(match), end))

    if start == -1 and end == -1:
        result = u""
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]

    if _DEBUG:
        log.debug("{m}.{f}: done result length: " + str(len(result)))
    return result


def _getDOMAttributes(match, name, ret):
    if _DEBUG:
        log.debug('{m}.{f}')

    # (fixme): collapse the two re.compile in a single one where the opening quote, if present,
    #   must match the closing quote, otherwise in scenario where there is a mix of the two
    #   format only the elements with the quotes are returned!
    lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
    if len(lst) == 0:
        lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
    ret = []
    for tmp in lst:
        cont_char = tmp[0]
        if cont_char in "'\"":
            if _DEBUG:
                log.debug("{m}.{f}: Using %s as quotation mark" % cont_char)

            # Limit down to next variable.
            if tmp.find('=' + cont_char, tmp.find(cont_char)) > -1:
                tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char))]

            # Limit to the last quotation mark
            if tmp.rfind(cont_char) > -1:
                tmp = tmp[1:tmp.rfind(cont_char)]
        else:
            if _DEBUG:
                log.debug("{m}.{f}: No quotation mark found")

            if tmp.find(" ") > 0:
                tmp = tmp[:tmp.find(" ")]
            elif tmp.find("/") > 0:
                tmp = tmp[:tmp.find("/")]
            elif tmp.find(">") > 0:
                tmp = tmp[:tmp.find(">")]

        ret.append(tmp.strip())

    if _DEBUG:
        log.debug("{m}.{f}: done: " + repr(ret))

    return ret
