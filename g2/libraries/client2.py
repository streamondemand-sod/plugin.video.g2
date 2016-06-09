# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016 J0rdyZ65

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
import HTMLParser

import requests
from requests.packages import urllib3

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

        res = _request(method, url, raise_error=raise_error, debug=debug, **kwargs)

        if _debug(debug, 'adapter'):
            conn = self.get_adapter(url).poolmanager.connection_from_url(url)
            log.debug('{m}.{f}: request.conn: connections:%d, requests:%d', conn.num_connections, conn.num_requests, debug=True)

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
    if _debug(debug, 'request'):
        log.debug('{m}.{f}: request.method: %s', method, debug=True)
        log.debug('{m}.{f}: request.url: %s', url, debug=True)
        if kwargs.get('data'):
            for var, val in kwargs.get('data').iteritems():
                log.debug('{m}.{f}: request.data: %s=%s', var, val, debug=True)
        if type(kwargs.get('headers')) == dict:
            for hdr, val in kwargs.get('headers').iteritems():
                log.debug('{m}.{f}: request.headers: %s=%s', hdr, val, debug=True)

    res = method(url, **kwargs)

    if _debug(debug, 'response'):
        for hdr, val in res.headers.iteritems():
            log.debug('{m}.{f}: response.headers: %s=%s', hdr, val, debug=True)
        for cke, val in res.cookies.iteritems():
            log.debug('{m}.{f}: response.cookies: %s=%s', cke, val, debug=True)
        if res.history:
            log.debug('{m}.{f}: response.history: %s', res.history, debug=True)
        log.debug('{m}.{f}: response.status: %s', res.status_code, debug=True)

    if _debug(debug, 'content'):
        log.debug('{m}.{f}: response.content[%s]: %s', res.encoding, res.content, debug=True)

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


def parseDOM(html, name=u"", attrs=None, ret=False):
    log.debug("{m}.{f}: Name: " + repr(name) + " - Attrs:" + repr(attrs) + " - Ret: " + repr(ret) + " - HTML: " + str(type(html)))

    if not name.strip():
        log.debug("{m}.{f}: Missing tag name")
        return u""

    if isinstance(html, str):
        try:
            html = [html.decode("utf-8")] # Replace with chardet thingy
        except Exception:
            log.debug("{m}.{f}: Couldn't decode html binary string. Data length: " + repr(len(html)))
            html = [html]
    elif isinstance(html, unicode):
        html = [html]
    elif not isinstance(html, list):
        log.debug("{m}.{f}: Input isn't list or string/unicode.")
        return u""

    ret_lst = []
    for item in html:
        temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
        for match in temp_item:
            item = item.replace(match, match.replace("\n", " "))

        lst = _getDOMElements(item, name, attrs)

        rets = []
        for match in lst:
            if isinstance(ret, basestring):
                log.debug("{m}.{f}: Getting attribute %s content for %s"%(ret, match))
                rets += _getDOMAttributes(match, name, ret)
            elif ret:
                log.debug("{m}.{f}: Getting attributes %s content for %s"%(ret, match))
                retdict = {}
                for i in ret:
                    retdict[i] = _getDOMAttributes(match, name, i)
                rets.append(retdict)
            else:
                log.debug("{m}.{f}: Getting element content for %s"%match)
                temp = _getDOMContent(item, name, match).strip()
                item = item[item.find(temp, item.find(match)) + len(temp):]
                rets.append(temp)
        ret_lst += rets

    log.debug("{m}.{f}: Done: " + repr(ret_lst))
    return ret_lst


def _getDOMElements(item, name, attrs):
    log.debug("{m}.{f}:")

    if attrs is None:
        log.debug("{m}.{f}: No attributes specified, matching on name only")
        lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
        if len(lst) == 0:
            lst = re.compile('(<' + name + ' .*?>)', re.M | re.S).findall(item)

    else:
        lst = []
        for key in attrs:
            lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))', re.M | re.S).findall(item)
            if len(lst2) == 0 and attrs[key].find(" ") == -1:  # Try matching without quotation marks
                lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))', re.M | re.S).findall(item)

            if len(lst) == 0:
                log.debug("{m}.{f}: Setting main list " + repr(lst2))
                lst = lst2
                lst2 = []
            else:
                log.debug("{m}.{f}: Setting new list " + repr(lst2))
                test = range(len(lst))
                test.reverse()
                for i in test:  # Delete anything missing from the next list.
                    if not lst[i] in lst2:
                        log.debug("{m}.{f}: Purging mismatch " + str(len(lst)) + " - " + repr(lst[i]))
                        del lst[i]

    log.debug("{m}.{f}: Done: " + str(type(lst)))
    return lst


def _getDOMContent(html, name, match):
    log.debug("{m}.{f}: Match: " + match)

    endstr = u"</" + name  # + ">"

    start = html.find(match)
    end = html.find(endstr, start)
    pos = html.find("<" + name, start + 1)

    log.debug(str(start) + " < " + str(end) + ", pos = " + str(pos) + ", endpos: " + str(end))

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(endstr, end + len(endstr))
        if tend != -1:
            end = tend
        pos = html.find("<" + name, pos + 1)
        log.debug("{m}.{f}: loop: " + str(start) + " < " + str(end) + " pos = " + str(pos))

    log.debug("{m}.{f}: start: %s, len: %s, end: %s" % (start, len(match), end))
    if start == -1 and end == -1:
        result = u""
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]

    log.debug("{m}.{f}: done result length: " + str(len(result)))
    return result


def _getDOMAttributes(match, name, ret):
    log.debug('{m}.{f}')
    lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
    if len(lst) == 0:
        lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
    ret = []
    for tmp in lst:
        cont_char = tmp[0]
        if cont_char in "'\"":
            log.debug("{m}.{f}: Using %s as quotation mark" % cont_char)

            # Limit down to next variable.
            if tmp.find('=' + cont_char, tmp.find(cont_char)) > -1:
                tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char))]

            # Limit to the last quotation mark
            if tmp.rfind(cont_char) > -1:
                tmp = tmp[1:tmp.rfind(cont_char)]
        else:
            log.debug("{m}.{f}: No quotation mark found")
            if tmp.find(" ") > 0:
                tmp = tmp[:tmp.find(" ")]
            elif tmp.find("/") > 0:
                tmp = tmp[:tmp.find("/")]
            elif tmp.find(">") > 0:
                tmp = tmp[:tmp.find(">")]

        ret.append(tmp.strip())

    log.debug("{m}.{f}: done: " + repr(ret))
    return ret
