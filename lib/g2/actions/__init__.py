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


import g2

from g2.libraries import log
from .lib import ui


_log_trace_on_error = True


def info():
    def action_info(dummy_package, dummy_module, mod, paths):
        if not hasattr(mod, 'info'):
            return []
        if callable(mod.info):
            nfo = mod.info(paths)
        else:
            nfo = mod.info
        return [dict(nfo)]

    return g2.info(__name__, action_info)


def execute(action, args=None):
    """Execute the plugin actions"""
    if '.' not in action:
        log.error('{m}.{f}(%s, ...): malformed action identifier (it should be module.action)', action)
        return

    if not args:
        args = {}
    if 'action' not in args:
        args['action'] = action

    module, action = action.split('.')
    action_ext = [a for a in info().itervalues()
                  if 'package' in a and a.get('module') == module and action in a.get('methods', [])]
    try:
        if action_ext:
            # if multiple modules redefine the same actions, use the first one without a particular order
            action_ext = action_ext[0]
            with g2.Context(__name__, action_ext['package'], [action_ext['module']], action_ext['search_paths']) as mod:
                getattr(mod[0], action)(**args)
        else:
            mod = __import__(module, globals(), locals(), [], -1)
            getattr(mod, action)(**args)
    except Exception as ex:
        log.error('{m}.{f}(%s.%s, ...): %s', module, action, ex)
