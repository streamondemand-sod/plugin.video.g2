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
import urlparse

from contextlib import closing

from g2 import pkg

from g2.libraries import log
from g2.libraries import client2

from .lib import metastream


_log_debug = True


# Streams shorter than this are not considered valid
_MIN_STREAM_SIZE = 1024 * 1024


class ResolverError(Exception):
    pass


class ResolvedURL(unicode):
    def enrich(self, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val)
        return self


def info(force=False):
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
                'priority': pkg.setting('resolvers', package, name='priority'),
            })
        return nfo

    return pkg.info('resolvers', resolver_info, force)


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

        log.debug('{m}.{f}: %s: resolving %s...', resolver['name'], url)

        res = None
        with pkg.Context('resolvers', resolver['package'], [resolver['module']], resolver['search_paths']) as mod:
            res = None if not mod else mod[0].resolve(resolver['name'].split('.'), url)

        log.debug('{m}.{f}: %s: %s', resolver['name'], repr(res))

        # On error, go to the next resolver for the same domain
        if not isinstance(res, basestring):
            collect_resolver_error(resolver, res)
            continue

        if not res:
            collect_resolver_error(resolver, 'empty url')
            continue

        # For non http(s) urls, do not check anything more
        if not res.lstrip().startswith('http'):
            return ResolvedURL(res).enrich(resolver=resolver['name'])

        # Otherwise, check if the URL doesn't return errors
        try:
            headers = res.split('|')[1]
            if ' ' in headers:
                headers = urllib.quote_plus(headers, '=&')
            headers = dict(urlparse.parse_qsl(headers))
        except Exception:
            headers = dict('')

        if not 'User-Agent' in headers:
            headers['User-Agent'] = client2.agent()
        if not 'Referer' in headers:
            headers['Referer'] = url

        with closing(client2.get(res.split('|')[0], headers=headers, stream=True, timeout=20, debug=True)) as resp:
            try:
                resp.raise_for_status()
            except Exception as ex:
                collect_resolver_error(resolver, str(ex))
                continue

            content_lenght = resp.headers.get('Content-Length', 0)
            if content_lenght < _MIN_STREAM_SIZE:
                collect_resolver_error(resolver, 'Stream too short')
                continue

            meta = metastream.video(resp.raw)

            url = res.split('|')[0]
            return ResolvedURL('%s%s%s' % (url, '&' if '?' in url else '?', urllib.urlencode(headers))).enrich(
                resolver=resolver['name'],
                meta=meta,
                size=content_lenght,
                acceptbyteranges='bytes' in resp.headers.get('Accept-Ranges', '').lower()
            )

    return errors
