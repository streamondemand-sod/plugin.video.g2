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
import sys
import urlparse

import xbmc

import importer
ADDONS_PATH = os.path.join(xbmc.translatePath('special://home'), 'addons')
for addon_dir in os.listdir(ADDONS_PATH):
    importer.add_path(os.path.join(ADDONS_PATH, addon_dir))
sys.path_hooks.append(importer.ImpImporterSandbox)

from g2.libraries import log
from g2.libraries import platform
from g2 import actions

PARAMS = dict(urlparse.parse_qsl(sys.argv[2].replace('?', '')))
ARGS_DEFAULT = {
    'action': platform.setting('main_menu'),
    'name': None,
    'title': None,
    'year': None,
    'imdb': '0',
    'tmdb': '0',
    'tvdb': '0',
    'url': None,
    'image': None,
    'meta': None,
    'query': None,
    'source': None,
}

if 'action' not in PARAMS:
    actions.execute('changelog.show')

elif PARAMS['action'] == 'service.thread':
    # (fixme) [code] plugin.run(action, **kwargs) -> plugin.run('auth.trakt')
    from g2.actions import service
    service.monitor('trakt_enabled', 'setting', platform.execute, 'RunPlugin(%s?action=auth.trakt)'%sys.argv[0])

    service.monitor('pushbullet_apikey', 'setting', platform.execute, 'RunPlugin(%s?action=auth.pushbullet)'%sys.argv[0])

    from g2.libraries import workers
    from g2.actions.lib import downloader
    service.monitor('downloader', 'property', workers.Thread, downloader.worker)

    service.monitor('playing', 'player', platform.execute, 'RunPlugin(%s?action=player.notify)'%sys.argv[0])

    from g2 import notifiers
    from g2.actions import push
    service.monitor('notifiers.events', 'service', notifiers.events,
                    init_arg_name='start', on_push=push.new, on_push_delete=push.delete)

for arg, defvalue in ARGS_DEFAULT.iteritems():
    if arg not in PARAMS:
        PARAMS[arg] = defvalue

if not PARAMS['action']:
    PARAMS['action'] = 'main.menu'

log.notice('Thread ID:%s, ACTION:%s, QUERY:%s, IMDB:%s, URL:%s',
           sys.argv[1], PARAMS['action'], PARAMS['query'], PARAMS['imdb'], PARAMS['url'])

actions.execute(PARAMS['action'], PARAMS)
