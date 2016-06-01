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


import sys

import re
import json
import urllib
import urlparse

import xbmc

from g2.libraries import log
from g2.libraries import platform
from g2.libraries.language import _
from g2 import notifiers

from .lib import ui


_log_debug = True

_PLAYER = xbmc.Player()


def new(push):
    """Find a movie in the push and schedule the sources dialog"""
    try:
        log.debug('{m}.{f}: %s', push)
        url = push.get('url')
        if not url:
            return

        sites = {
            'imdb.com': {
                'type': 'db',
                'id_name': 'imdb_id',
                'id_value': r'/title/(tt[\d]+)',
                'db_query': 'movie_meta{imdb_id}',
            },
            'themoviedb.org': {
                'type': 'db',
                'id_name': 'tmdb_id',
                'id_value': r'/movie/([\d]+)',
                'db_query': 'movie_meta{tmdb_id}',
            },
            # This is a folder plugin, so it cannot be hooked in this way.
            # A specific resolver has to be created.
            # 'ilfattoquotidiano.it': {
            #     'type': 'addon',
            #     'addon': 'plugin.video.fattoquotidianotv',
            #     'query': 'page={url}&id=v',
            # },
        }
        netloc, path = urlparse.urlparse(url)[1:3]
        netloc = '.'.join(netloc.split('.')[-2:])
        if netloc not in sites:
            title = push.get('body', '').encode('utf-8').split('\n')[0]
            platform.execute('RunPlugin(%s?action=sources.url&title=%s&url=%s)'%
                             (sys.argv[0], urllib.quote_plus(title), urllib.quote_plus(url)))

        elif sites[netloc]['type'] == 'addon':
            adn = sites[netloc]
            if not platform.condition('System.HasAddon(%s)'%adn['addon']):
                raise Exception(_('Addon {addon} is missing').format(addon=adn['addon']))
            query = adn['query'].format(
                url=urllib.quote_plus(url.encode('utf-8')),
            )
            plugin = 'RunScript(plugin://%s/?%s)'%(adn['addon'], query)
            log.debug('{m}.{f}: executing %s...', plugin)
            platform.execute(plugin)

        elif sites[netloc]['type'] == 'db':
            dbs = sites[netloc]
            from g2.dbs import tmdb
            kwargs = {
                dbs['id_name']: re.search(dbs['id_value'], path).group(1),
            }
            meta = {'url': tmdb.url(dbs['db_query'], **kwargs)}
            tmdb.metas([meta])
            item = meta['item']

            log.debug('{m}.{f}: meta=%s', item)

            platform.execute('RunPlugin(%s?action=sources.dialog&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s)'%
                             (sys.argv[0], urllib.quote_plus(item['title']), urllib.quote_plus(item['year']),
                              urllib.quote_plus(item['imdb']), '', urllib.quote_plus(json.dumps(item))))

        else:
            raise Exception('unknown site type: %s'%sites[netloc])

    except Exception as ex:
        log.error('{m}.{f}: %s', ex)
        ui.infoDialog(_('URL not supported'))


def delete(push):
    log.debug('{m}.{f}: %s', push)
    if platform.property('player.notice.id') == push['iden']:
        _PLAYER.stop()
        notifiers.notices(_('Forced player stop'))
