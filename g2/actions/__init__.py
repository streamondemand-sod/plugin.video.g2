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


import sys

from g2.libraries import ui
from g2.libraries import log

from g2 import pkg


def action(func):
    func.is_action = True
    return func


def busyaction(func):
    def func_wrapper(*args, **kwargs):
        ui.busydialog()
        func(*args, **kwargs)
        ui.busydialog(stop=True)
    func_wrapper.is_action = True
    return func_wrapper


def execute(act, kwargs=None):
    """Execute the plugin actions"""
    if kwargs is None:
        kwargs = {}

    log.debug('{m}.{f}: tID:%s, ACTION:%s, ARGS:%.80s...', sys.argv[1], act, repr(kwargs))

    try:
        module, act = act.split('.')
        mod = __import__(module, globals(), locals(), [], -1)
        if not hasattr(mod, act):
            raise Exception('missing action function')
        function = getattr(mod, act)
        if not hasattr(function, 'is_action'):
            raise Exception('action function is not decorated')
        function(**kwargs)
    except Exception as ex:
        log.error('{m}.{f}: %s.%s: %s', module, act, ex, trace=True)
