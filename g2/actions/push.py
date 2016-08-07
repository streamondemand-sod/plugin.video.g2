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


import re
import json
import urllib
import urlparse

from g2.libraries import ui
from g2.libraries import log
from g2.libraries import addon
from g2.libraries.language import _

from g2 import dbs
from g2 import notifiers

from .lib import uid


_PLAYER = ui.Player()


def new(notifier, iden, title, body, url):
    """Find a movie in the url pushed and schedule the sources dialog or playurl action"""
    log.debug('{m}.{f}: %s: iden=%s, title=%s, body=%s, url=%s', notifier, iden, title, body, url)

    url = url or body
    if not url:
        return

    notifiers.notices([], identifiers={notifier: iden})

    try:
        # (fixme) make the sites list a configuration file or download from a site like the packages...
        sites = {
            'imdb.com': {
                'type': 'db',
                'id_name': 'imdb',
                'id_value': r'/title/(tt[\d]+)',
            },
            'themoviedb.org': {
                'type': 'db',
                'id_name': 'tmdb',
                'id_value': r'/movie/([\d]+)',
            },
            # http://thetvdb.com/?tab=episode&seriesid=79349&seasonid=16279&id=307473&lid=15
            'thetvdb.com': {
                'type': 'db',
                'id_name': 'tvdb',
                'id_value': r'seriesid=(\d+)',
                'ids_episode': r'seasonid=(\d+).*?id=(\d+)',
                'id_name_season': 'tvdb_season_id',
                'id_name_episode': 'tvdb_episode_id',
            },
            # This is a folder plugin, so it cannot be hooked in this way.
            # A specific resolver has to be created.
            # 'ilfattoquotidiano.it': {
            #     'type': 'addon',
            #     'addon': 'plugin.video.fattoquotidianotv',
            #     'addon_query': 'page={url}&id=v',
            # },
        }
        netloc, path, dummy, query = urlparse.urlparse(url)[1:5]
        path += '?' + query
        netloc = '.'.join(netloc.split('.')[-2:])
        if netloc not in sites:
            title = title or body
            title = (title or '').encode('utf-8')
            addon.runplugin('sources.playurl',
                            name=urllib.quote_plus(title),
                            url=urllib.quote_plus(url))

        elif sites[netloc]['type'] == 'addon':
            site = sites[netloc]
            if not addon.condition('System.HasAddon(%s)'%site['addon']):
                raise Exception(_('Addon {addon} is missing').format(addon=site['addon']))
            query = site['addon_query'].format(
                url=urllib.quote_plus(url.encode('utf-8')),
            )
            addon.runplugin(query, plugin='plugin://'+site['addon'])

        elif sites[netloc]['type'] == 'db':
            site = sites[netloc]
            meta = {
                site['id_name']: re.search(site['id_value'], path).group(1),
            }
            dbs.meta([meta], 'movie' if 'ids_episode' not in site else 'tvshow')
            if 'episodes' not in meta:
                content = 'movie'
            else:
                content = 'episode'
                season_id, episode_id = re.search(site['ids_episode'], path).groups()
                meta = [e for e in meta['episodes']
                        if e[site['id_name_season']] == season_id
                        and e[site['id_name_episode']] == episode_id][0]

            name = uid.nameitem(content, meta)

            log.debug('{m}.{f}: %s: %s', name, meta)

            addon.runplugin('sources.dialog',
                            name=urllib.quote_plus(name),
                            content=content,
                            meta=urllib.quote_plus(json.dumps(meta)))
        else:
            raise Exception('unknown site type: %s'%sites[netloc])

    except Exception as ex:
        log.error('{m}.{f}: %s', ex)
        ui.infoDialog(_('URL not supported'))


def delete(notifier, iden):
    identifiers = addon.prop('player.notice.ids')

    log.debug('{m}.{f}: %s, %s: identifiers=%s', notifier, iden, identifiers)

    if identifiers and identifiers.get(notifier) == iden:
        del identifiers[notifier]
        addon.prop('player.notice.ids', identifiers or '')
        if _PLAYER.isPlayingVideo():
            _PLAYER.stop()
            notifiers.notices(_('Forced player stop'))
