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

import os
import re
import sys
import urllib
import pkgutil
import urlparse

import g2

from g2.libraries import log
from g2.libraries import client
from .lib import metastream


# Streams shorter than this are not considered valid
_MIN_STREAM_SIZE = 1024 * 1024


class ResolverError(Exception):
    pass


class ResolvedURL(unicode):
    def enrich(self, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val)
        return self


def info():
    def resolver_info(package, dummy_module, mod, paths):
        if not hasattr(mod, 'info'):
            nfo = []
        elif callable(mod.info):
            nfo = mod.info(paths)
        else:
            nfo = mod.info
        if type(nfo) != list:
            nfo = [nfo]
        for i in nfo:
            i.update({
                # User configurable priority at the package level 
                'priority': g2.setting('resolvers', package, name='priority'),
            })
        return nfo

    return g2.info('resolvers', resolver_info)


def _top_domain(url):
    elements = urlparse.urlparse(url)
    domain = elements.netloc or elements.path
    domain = domain.split('@')[-1].split(':')[0]
    try:
        domain = re.search(r'(\w{2,}\.\w{2,3}\.\w{2}|\w{2,}\.\w{2,})$', domain).group(1)
    except Exception:
        pass
    return domain.lower()


def _netloc_match(resolver, url):
    if _top_domain(url) in resolver.get('domains', []):
        return True

    if 'url_patterns' in resolver:
        for pat in resolver['url_patterns']:
            try:
                if re.search(pat, url):
                    return True
            except Exception:
                pass
    
    return False


def resolve(url, checkonly=False):
    if not url:
        return [ResolverError('No resolver for the empty url')]
    resolvers = [r for r in info().itervalues() if _netloc_match(r, url)]
    if not resolvers:
        return [ResolverError('No resolver for %s'%_top_domain(url))]
    if checkonly:
        return url

    errors = []
    for resolver in sorted(resolvers, key=lambda r: r['priority']):
        def collect_resolver_error(resolver, err):
            if isinstance(err, basestring) or err is None or not str(err).startswith(resolver['name']):
                errors.append(ResolverError('%s: %s'%(resolver['name'], str(err))))
            else:
                errors.append(err)

        with g2.Context('resolvers', resolver['package'], [resolver['module']], resolver['search_paths']) as mod:
            res = None if not mod else mod[0].resolve(resolver['name'].split('.'), url)

        # On error, go to the next resolver for the same domain
        if not isinstance(res, basestring):
            collect_resolver_error(resolver, res)
            continue

        if not res:
            collect_resolver_error(resolver, 'empty url')
            continue

        # For non http(s) urls, do not check anything more
        if not res.startswith('http'):
            return ResolvedURL(res).enrich(resolver=resolver['name'])

        # Otherwise, check if the URL doesn't return errors
        try:
            headers = dict(urlparse.parse_qsl(res.rsplit('|', 1)[1]))
        except Exception:
            headers = dict('')

        if not 'User-Agent' in headers:
            headers['User-Agent'] = client.agent()
        if not 'Referer' in headers:
            headers['Referer'] = url

        try:
            response = client.request(res.split('|')[0], headers=headers, close=False, error=True, timeout='20')
        except Exception as ex:
            collect_resolver_error(resolver, str(ex))
            continue

        if not response or 'HTTP Error' in str(response):
            collect_resolver_error(resolver, str(response))
            continue

        if int(response.headers['Content-Length']) < _MIN_STREAM_SIZE:
            collect_resolver_error(resolver, 'Stream too short')
            continue

        meta = metastream.video(response)

        url = res.split('|')[0]
        return ResolvedURL('%s%s%s' % (url, '&' if '?' in url else '?', urllib.urlencode(headers))).enrich(
            resolver=resolver['name'],
            meta=meta,
            size=int(response.headers['Content-Length']),
            acceptbyteranges='bytes' in response.headers.get('Accept-Ranges', '').lower())

    return errors
