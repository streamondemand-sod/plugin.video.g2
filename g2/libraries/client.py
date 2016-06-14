# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2015 lambda

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
import sys
import urllib2
import HTMLParser

from g2.libraries import log


_log_debug = False


class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"


class DeleteRequest(urllib2.Request):
    def get_method(self):
        return "DELETE"


def request(url, method=None, close=True, error=False, proxy=None, post=None, headers=None, mobile=False, safe=False, referer=None, cookie=None, output='', timeout='30', debug=False):
    global _log_debug
    _log_debug = debug
    try:
        requesterr = False
        handlers = []
        if not proxy == None:
            handlers += [urllib2.ProxyHandler({'http':'%s' % (proxy)}), urllib2.HTTPHandler]
            opener = urllib2.build_opener(*handlers)
            opener = urllib2.install_opener(opener)
        if output == 'cookie' or not close == True or type(cookie) == list:
            import cookielib
            cookies = cookielib.LWPCookieJar()
            handlers += [urllib2.HTTPHandler(), urllib2.HTTPSHandler(), urllib2.HTTPCookieProcessor(cookies)]
            opener = urllib2.build_opener(*handlers)
            opener = urllib2.install_opener(opener)
        try:
            if sys.version_info < (2, 7, 9):
                raise Exception()
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            handlers += [urllib2.HTTPSHandler(context=ssl_context)]
            opener = urllib2.build_opener(*handlers)
            opener = urllib2.install_opener(opener)
        except Exception:
            pass

        try:
            headers.update(headers)
        except Exception:
            headers = {}
        if 'User-Agent' in headers:
            pass
        elif not mobile == True:
            headers['User-Agent'] = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0'
        else:
            headers['User-Agent'] = 'Apple-iPhone/701.341'
        if 'referer' in headers:
            pass
        elif referer == None:
            headers['referer'] = url
        else:
            headers['referer'] = referer
        if not 'Accept-Language' in headers:
            headers['Accept-Language'] = 'en-US'
        if 'cookie' in headers:
            pass
        elif not cookie == None:
            headers['cookie'] = cookie

        log.debug("client.request:url: %s"%url)
        log.debug("client.request:post: %s"%post)
        for hdr in headers:
            log.debug("client.request:headers: %s=%s"%(hdr, headers[hdr]))
        
        if method == 'HEAD':
            request = HeadRequest(url, headers=headers)
        elif method == 'DELETE':
            request = DeleteRequest(url, headers=headers)
        else:
            request = urllib2.Request(url, data=post, headers=headers)

        log.debug("client.request: %s"%request)

        requesterr = False
        try:
            response = urllib2.urlopen(request, timeout=int(timeout))
        except urllib2.HTTPError as response:
            requesterr = True
            if error == 'raise':
                raise response

        if response:
            log.debug("client.request:response: %s"%str(response))
            for hdr in response.headers:
                log.debug("client.request:response-headers: %s=%s"%(hdr, response.headers[hdr]))
        if output == 'cookie' or not close == True or type(cookie) == list:
            for cke in cookies:
                log.debug("client.request:response-cookie: %s=%s"%(cke.name, cke.value))

        if requesterr and error == False:
            return None

        if type(cookie) == list:
            for cke in cookies: 
                cookie.append('%s=%s' % (cke.name, cke.value))

        if not close:
            result = response
        elif output == 'cookie':
            result = []
            for cke in cookies:
                result.append('%s=%s' % (cke.name, cke.value))
            result = "; ".join(result)
        elif output == 'response':
            if safe == True:
                result = (str(response), response.read(224 * 1024))
            else:
                result = (str(response), response.read())
        elif output == 'chunk':
            result = (str(response), int(response.headers['Content-Length']))
        elif output == 'geturl':
            result = response.geturl()
        elif output == 'headers':
            result = response.headers
        elif safe == True:
            result = response.read(224 * 1024)
        else:
            result = response.read()
 
        if close:
            response.close()

        log.debug('client.request:result(%s):\n%s'%(output, repr(result)))

        return result
    except Exception:
        if requesterr and error == 'raise':
            raise response
        return None


def parseDOM(html, name=u"", attrs={}, ret=False, noattrs=True, debug=False):
    # Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen
    global _log_debug
    _log_debug = debug

    if isinstance(html, str):
        try:
            html = [html.decode("utf-8")] # Replace with chardet thingy
        except Exception:
            html = [html]
    elif isinstance(html, unicode):
        html = [html]
    elif not isinstance(html, list):
        return u""

    log.debug('client.parseDOM: name=%s'%name)
    for key in attrs:
        log.debug('client.parseDOM:attrs: %s=%s'%(key, attrs[key]))
    log.debug('client.parseDOM: ret=%s, noattrs=%s'%(ret, noattrs))

    if not name.strip():
        return u""

    ret_lst = []
    for item in html:
        temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
        for match in temp_item:
            item = item.replace(match, match.replace("\n", " "))

        lst = []
        for key in attrs:
            try:
                lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))', re.M | re.S).findall(item)
            except Exception:
                pass
            if len(lst2) == 0 and attrs[key].find(" ") == -1:  # Try matching without quotation marks
                try:
                    lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))', re.M | re.S).findall(item)
                except Exception:
                    pass

            if len(lst) == 0:
                lst = lst2
                lst2 = []
            else:
                test = range(len(lst))
                test.reverse()
                for i in test:  # Delete anything missing from the next list.
                    if not lst[i] in lst2:
                        del lst[i]

        if len(lst) == 0 and attrs == {}:
            if noattrs:
                lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
            if len(lst) == 0:
                lst = re.compile('(<' + name + ' .*?>|<' + name + '>)', re.M | re.S).findall(item)

        if isinstance(ret, str):
            lst2 = []
            for match in lst:
                attr_lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
                if len(attr_lst) == 0:
                    attr_lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
                for tmp in attr_lst:
                    cont_char = tmp[0]
                    if cont_char in "'\"":
                        # Limit down to next variable.
                        if tmp.find('=' + cont_char, tmp.find(cont_char, 1)) > -1:
                            tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char, 1))]

                        # Limit to the last quotation mark
                        if tmp.rfind(cont_char, 1) > -1:
                            tmp = tmp[1:tmp.rfind(cont_char)]
                    else:
                        if tmp.find(" ") > 0:
                            tmp = tmp[:tmp.find(" ")]
                        elif tmp.find("/") > 0:
                            tmp = tmp[:tmp.find("/")]
                        elif tmp.find(">") > 0:
                            tmp = tmp[:tmp.find(">")]

                    lst2.append(tmp.strip())
            lst = lst2
        else:
            lst2 = []
            for match in lst:
                endstr = u"</" + name

                start = item.find(match)
                end = item.find(endstr, start)
                pos = item.find("<" + name, start + 1)

                while pos < end and pos != -1:
                    tend = item.find(endstr, end + len(endstr))
                    if tend != -1:
                        end = tend
                    pos = item.find("<" + name, pos + 1)

                if start == -1 and end == -1:
                    temp = u""
                elif start > -1 and end > -1:
                    temp = item[start + len(match):end]
                elif end > -1:
                    temp = item[:end]
                elif start > -1:
                    temp = item[start + len(match):]

                if ret:
                    endstr = item[end:item.find(">", item.find(endstr)) + 1]
                    temp = match + temp + endstr

                item = item[item.find(temp, item.find(match)) + len(temp):]
                lst2.append(temp)
            lst = lst2
        ret_lst += lst

    if len(ret_lst):
        for i in ret_lst:
            log.debug('client.parseDOM:result: %s'%repr(i.encode('utf-8')))
    else:
        log.debug('client.parseDOM:result: None')

    return ret_lst


def replaceHTMLCodes(txt):
    txt = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", txt)
    txt = HTMLParser.HTMLParser().unescape(txt)
    txt = txt.replace("&quot;", "\"")
    txt = txt.replace("&amp;", "&")
    return txt


def agent():
    return 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0'
