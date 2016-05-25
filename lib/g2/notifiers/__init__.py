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


import importer

import g2

from g2.libraries import log
from g2.libraries import platform


# _log_debug = True
# _log_trace_on_error = True


def info():
    def notifiers_info(package, module, m, paths):
        if not hasattr(m, 'INFO'):
            return []
        if callable(m.INFO):
            nfo = m.INFO(paths)
        else:
            nfo = m.INFO
        return [dict(nfo)]

    return g2.info('notifiers', notifiers_info)


def notices(notes, targets=None, **kwargs):
    if isinstance(notes, basestring):
        notes = [notes]
    # (fixme) [func] review the targets semantic
    for notifier in [no for no in info().itervalues() if not targets or no['target'] in targets]:
        try:
            if 'package' in notifier:
                with g2.Context('notifiers', notifier['package'], [notifier['module']], notifier['search_paths']) as mod:
                    mod[0].notices(notes, **kwargs)
            else:
                with g2.Context('notifiers', notifier['module'], [], []) as mod:
                    mod.notices(notes, **kwargs)
        except Exception as ex:
            log.error('notifiers.%s.notices(): %s'%(notifier['name'], ex))
