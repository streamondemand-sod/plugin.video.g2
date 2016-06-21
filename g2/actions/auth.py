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


from g2.libraries import platform
from g2.libraries.language import _

from g2.dbs import trakt as trakt_db
from g2.notifiers import pb as pb_notifier

from .lib import ui
from . import action


@action
def trakt():
    """Trakt device authorization"""
    if platform.setting('trakt_enabled') == 'false':
        ui.infoDialog(_('Trakt functionality disabled'))
        return

    try:
        trakt_user = platform.setting('trakt_user')
        if trakt_user:
            if ui.yesnoDialog(_('There is already an authorized account: ')+trakt_user,
                              _('Do you wanto to keep it?'),
                              heading='Trakt'):
                ui.refresh()
                return

        dialog_progress = ui.DialogProgress()
        dialog_progress.create('Trakt')
        dialog_progress.update(0)

        def ui_update(code, url, elapsed, expire):
            """Show the device authorization code to the user and allow him to cancel the procedure"""
            dialog_progress.update(int(100 * elapsed) / expire,
                                   _('Provide the code')+' %s'%code,
                                   _('at')+' %s'%url,
                                   _('Leftover time')+' %.0f:%02.0f'%divmod(expire-elapsed, 60))
            ui.sleep(1000)
            return not ui.abortRequested() and not dialog_progress.iscanceled()

        user = trakt_db.authDevice(ui_update=ui_update)

        dialog_progress.close()

        # (fixme) add congratulations and other comments about new functionality unlocked
        ui.Dialog().ok('Trakt', _('Authorized username')+' [COLOR orange]%s[/COLOR]'%user)

        platform.setSetting('trakt_user', user)

        ui.refresh()

    except Exception as ex:
        dialog_progress.close()
        ui.infoDialog(str(ex), time=5000)


@action
def pushbullet():
    """Pushbullet apikey validation"""
    if not platform.setting('pushbullet_apikey'):
        ui.infoDialog(_('Pushbullet disabled'))
        return

    # (fixme) if auth fail, clear the pushbullet_email, otherwise set it to the email address
    pbo = pb_notifier.PushBullet(platform.setting('pushbullet_apikey'))
    try:
        user = pbo.getUser()
        if not user:
            raise Exception('Pushbullet authorization failed')
        else:
            ui.Dialog().ok('Pushbullet', _('Authorized account')+' [COLOR orange]%s[/COLOR]'%user['email'])

    except Exception as ex:
        ui.infoDialog(str(ex), time=5000)
