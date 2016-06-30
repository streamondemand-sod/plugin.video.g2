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


from g2.libraries import ui
from g2.libraries import addon
from g2.libraries.language import _

from . import action


@action
def trakt():
    """Trakt device authorization"""
    from g2.dbs import trakt as trakt_db

    if addon.setting('trakt_enabled') == 'false':
        ui.infoDialog(_('Trakt disabled'))
        return

    try:
        trakt_user = addon.setting('trakt_user')
        if trakt_user:
            if ui.yesnoDialog(_('There is already an authorized account: {trakt_user}').format(
                    trakt_user=trakt_user,
                ), _('Do you wanto to keep it?'), heading='Trakt'):
                ui.refresh()
                return

        dialog_progress = ui.DialogProgress()
        dialog_progress.create('Trakt')
        dialog_progress.update(0)

        def ui_update(code, url, elapsed, expire):
            """Show the device authorization code to the user and allow him to cancel the procedure"""
            minutes, seconds = divmod(int(expire-elapsed), 60)
            dialog_progress.update(int(100 * elapsed) / expire,
                                   _('Provide the code {code} at the site:').format(code=code),
                                   url,
                                   _('You have {minutes:02d}:{seconds:02d} left').format(
                                       minutes=minutes,
                                       seconds=seconds))
            return not ui.abortRequested(1) and not dialog_progress.iscanceled()

        user = trakt_db.authDevice(ui_update=ui_update)

        dialog_progress.close()

        ui.Dialog().ok('Trakt', _('Authorized username: [COLOR orange]{trakt_user}[/COLOR]').format(
            trakt_user=user))

        addon.setSetting('trakt_user', user)

        ui.refresh()

    except Exception as ex:
        dialog_progress.close()
        ui.infoDialog(str(ex), time=5000)


@action
def pushbullet():
    """Pushbullet apikey validation"""
    from g2.notifiers import pushbullet as pb_notifier

    if not addon.setting('pushbullet_apikey'):
        addon.setSetting('pushbullet_email', '')
        ui.infoDialog(_('Pushbullet disabled'))
        # Enabling/disabling the pb events handling requires,
        # for now, a complete restart of service thread.
        addon.prop('service', False)
        return

    pbo = pb_notifier.PushBullet(addon.setting('pushbullet_apikey'))
    try:
        ui.busydialog()
        user = pbo.getUser()
        ui.idle()
        if not user or not user.get('email'):
            raise Exception('Pushbullet authorization failed')
        else:
            ui.Dialog().ok('Pushbullet', _('Authorized account email: [COLOR orange]{pushbullet_email}[/COLOR]').format(
                pushbullet_email=user['email']))
            if not pb_notifier.enabled():
                # Enabling/disabling the pb events handling requires,
                # for now, a complete restart of service thread.
                addon.prop('service', False)
            addon.setSetting('pushbullet_email', user['email'])

    except Exception as ex:
        if pb_notifier.enabled():
            # Enabling/disabling the pb events handling requires,
            # for now, a complete restart of service thread.
            addon.prop('service', False)
        addon.setSetting('pushbullet_email', '')
        ui.infoDialog(str(ex), time=5000)


@action
def imdb():
    """IMdb username validation"""
    from g2.dbs import imdb as imdb_db

    imdb_user = addon.setting('imdb_user')
    if not imdb_user:
        ui.infoDialog(_('IMDb user disabled'))
        addon.setSetting('imdb_nickname', '')
        return

    try:
        ui.busydialog()
        imdb_nickname = imdb_db.nickname(imdb_user)
        ui.idle()
        if not imdb_nickname:
            raise Exception('Invalid IMDb user')
        else:
            ui.Dialog().ok('IMDbt', _('IMDb user nickname: [COLOR orange]{imdb_nickname}[/COLOR]').format(
                imdb_nickname=imdb_nickname))
            addon.setSetting('imdb_nickname', imdb_nickname)
            ui.refresh()

    except Exception as ex:
        addon.setSetting('imdb_nickname', '')
        ui.infoDialog(str(ex), time=5000)
