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
import time

import xbmc

from g2.libraries import log
from g2.libraries import addon


def main():
    """(Re)schedule the g2 service thread"""
    service_thread_id = 0
    next_restart_after = time.time()
    start_service_thread = True
    addon.property('service', '')
    while not xbmc.abortRequested:
        # The current thread terminated
        if service_thread_id and addon.property('service', name=str(service_thread_id)) is None:
            log.notice('service manager: service thread with id %d terminated', service_thread_id)
            start_service_thread = True

        # User/system asked to terminate the current thread
        if addon.property('service') is False:
            addon.property('service', '')
            if service_thread_id and addon.property('service', name=str(service_thread_id)) is True:
                log.notice('service manager: terminating the service thread with id %d...', service_thread_id)
                addon.property('service', False, name=str(service_thread_id))

        # User/system asked to start the service thread
        if start_service_thread and time.time() >= next_restart_after:
            service_thread_id += 1
            log.notice('service manager: scheduling the service thread with id %d...', service_thread_id)
            addon.property('service', True, name=str(service_thread_id))
            addon.execute(addon.pluginaction('service.thread', name=service_thread_id))
            next_restart_after = time.time() + 15
            start_service_thread = False

        xbmc.sleep(1000)


if __name__ == '__main__':
    sys.exit(main())
