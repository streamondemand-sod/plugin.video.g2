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

from g2.libraries import addon

from g2 import actions

def main():
    params = dict(urlparse.parse_qsl(sys.argv[2].replace('?', '')))

    if 'action' not in params:
        actions.execute('changelog.show')
        action = None
    else:
        action = params['action']
        del params['action']

    if not action:
        action = 'main.menu'

    if action == 'service.thread':
        service_monitor_setup()

    actions.execute(action, params)

    return 0


def service_monitor_setup():
    from g2.actions import service
    service.monitor('trakt_enabled', 'setting', addon.execute, 'RunPlugin(%s?action=auth.trakt)'%sys.argv[0])

    service.monitor('pushbullet_apikey', 'setting', addon.execute, 'RunPlugin(%s?action=auth.pushbullet)'%sys.argv[0])

    from g2.libraries import workers
    from g2.actions.lib import downloader
    service.monitor('downloader', 'property', workers.Thread, downloader.worker)

    service.monitor('playing', 'player', addon.execute, 'RunPlugin(%s?action=player.notify)'%sys.argv[0])

    from g2 import notifiers
    from g2.actions import push
    service.monitor('notifiers.events', 'service', notifiers.events,
                    init_arg_name='start', on_push=push.new, on_push_delete=push.delete)


if __name__ == '__main__':
    main()
