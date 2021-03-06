# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016-2017 J0rdyZ65

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


from g2.libraries import log
from g2.libraries import addon

from g2 import pkg


def info(force_refresh=False):
    def notifiers_info(dummy_package, dummy_module, mod, paths):
        if not hasattr(mod, 'info'):
            return []
        if callable(mod.info):
            nfo = mod.info(paths)
        else:
            nfo = mod.info
        return [dict(nfo)]

    return pkg.info('notifiers', notifiers_info, force_refresh)


def notices(notes, targets=None, **kwargs):
    if isinstance(notes, basestring):
        notes = [notes]
    if not targets:
        targets = []
    elif isinstance(targets, basestring):
        targets = [targets]

    _all_modules_method('notices', targets, notes, **kwargs)


def events(start, targets=None, **kwargs):
    if start is None:
        start = False
    return _all_modules_method('events', targets, start, **kwargs)


def _all_modules_method(method, targets, *args, **kwargs):
    res = None
    for module in [m for m in info().itervalues()
                   if method in m['methods'] and
                   (not targets or set([m['name']] + m['targets']) & set(targets))]:
        try:
            if 'package' in module:
                with pkg.Context('notifiers', module['package'], [module['module']], module['search_paths']) as mod:
                    res = getattr(mod[0], method)(*args, **kwargs)
            else:
                with pkg.Context('notifiers', module['module'], [], []) as mod:
                    res = getattr(mod, method)(*args, **kwargs)
        except Exception as ex:
            log.error('notifiers.%s.%s: %s', module['name'], method, ex)

    return res
