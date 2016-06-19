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

from g2 import pkg
from g2.libraries import log

from .lib import ui


def busyaction():
    def wrap(func):
        def busyaction_func(*args, **kwargs):
            ui.busydialog()
            func(*args, **kwargs)
            ui.busydialog(stop=True)
        busyaction_func.is_action = True
        return busyaction_func
    return wrap


def action(func):
    func.is_action = True
    return func


def execute(action, kwargs=None):
    """Execute the plugin actions"""
    if '.' not in action:
        log.error('{m}.{f}(%s, ...): malformed action identifier (it should be module.action)', action)
        return

    if kwargs is None:
        kwargs = {}

    log.debug('{m}.{f}: tID:%s, ACTION:%s, ARGS:%.80s...', sys.argv[1], action, repr(kwargs))

    module, action = action.split('.')

    try:
        mod = __import__(module, globals(), locals(), [], -1)
        if not hasattr(mod, action):
            raise Exception('missing action function')
        function = getattr(mod, action)
        if not hasattr(function, 'is_action'):
            raise Exception('action function is not decorated')
        function(**kwargs)
    except Exception as ex:
        log.error('{m}.{f}: %s.%s: %s', module, action, ex, trace=True)
