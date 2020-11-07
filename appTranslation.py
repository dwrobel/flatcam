# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

import os
import sys
import logging
from pathlib import Path

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings

import gettext

log = logging.getLogger('base')

# import builtins
#
# if '_' not in builtins.__dict__:
#     _ = gettext.gettext

# ISO639-1 codes from here: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
languages_dict = {
    'zh': 'Chinese',
    'de': 'German',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'it': 'Italian',
    'pt_BR': 'Brazilian Portuguese',
    'ro': 'Romanian',
    'ru': 'Russian',
    'tr': 'Turkish',
}

translations = {}

languages_path_search = ''


def load_languages():
    available_translations = []
    languages_path_search = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale')

    try:
        available_translations = next(os.walk(languages_path_search))[1]
    except StopIteration:
        if not available_translations:
            languages_path_search = os.path.join(str(Path(__file__).parents[1]), 'locale')
            try:
                available_translations = next(os.walk(languages_path_search))[1]
            except StopIteration:
                pass

    for lang in available_translations:
        try:
            if lang in languages_dict.keys():
                translations[lang] = languages_dict[lang]
        except KeyError as e:
            log.debug("FlatCAMTranslations.load_languages() --> %s" % str(e))
    return translations


def languages_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale')


def languages_dir_cx_freeze():
    return os.path.join(Path(__file__).parents[1], 'locale')


def on_language_apply_click(app, restart=False):
    """
    Using instructions from here:
    https://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/

    :return:
    """
    name = app.ui.general_defaults_form.general_app_group.language_cb.currentText()

    theme_settings = QSettings("Open Source", "FlatCAM")
    if theme_settings.contains("theme"):
        theme = theme_settings.value('theme', type=str)
    else:
        theme = 'white'

    if theme == 'white':
        resource_loc = 'assets/resources'
    else:
        resource_loc = 'assets/resources'

    # do nothing if trying to apply the language that is the current language (already applied).
    settings = QSettings("Open Source", "FlatCAM")
    if settings.contains("language"):
        current_language = settings.value('language', type=str)
        if current_language == name:
            return

    if restart:
        msgbox = QtWidgets.QMessageBox()
        msgbox.setText(_("The application will restart."))
        msgbox.setInformativeText('%s %s?' %
                                  (_("Are you sure do you want to change the current language to"), name.capitalize()))
        msgbox.setWindowTitle('%s ...' % _("Apply Language"))
        msgbox.setWindowIcon(QtGui.QIcon(resource_loc + '/language32.png'))
        msgbox.setIcon(QtWidgets.QMessageBox.Question)

        bt_yes = msgbox.addButton(_("Yes"), QtWidgets.QMessageBox.YesRole)
        bt_no = msgbox.addButton(_("No"), QtWidgets.QMessageBox.NoRole)

        msgbox.setDefaultButton(bt_yes)
        msgbox.exec_()
        response = msgbox.clickedButton()

        if response == bt_no:
            return
        else:
            settings = QSettings("Open Source", "FlatCAM")
            saved_language = name
            settings.setValue('language', saved_language)
            # This will write the setting to the platform specific storage.
            del settings

            restart_program(app=app)


def apply_language(domain, lang=None):
    lang_code = ''

    if lang is None:
        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("language"):
            name = settings.value('language')
        else:
            name = 'English'
            # in case the 'language' parameter is not in QSettings add it to QSettings and it's value is
            # the default language, English
            settings.setValue('language', 'English')

            # This will write the setting to the platform specific storage.
            del settings
    else:
        name = str(lang)

    for lang_code, lang_usable in load_languages().items():
        if lang_usable == name:
            # break and then use the current key as language
            break

    if lang_code == '':
        return "no language"
    else:
        try:
            current_lang = gettext.translation(str(domain), localedir=languages_dir(), languages=[lang_code])
            current_lang.install()
        except Exception as e:
            log.debug("FlatCAMTranslation.apply_language() --> %s. Perhaps is Cx_freeze-ed?" % str(e))
            try:
                current_lang = gettext.translation(str(domain),
                                                   localedir=languages_dir_cx_freeze(),
                                                   languages=[lang_code])
                current_lang.install()
            except Exception as e:
                log.debug("FlatCAMTranslation.apply_language() --> %s" % str(e))

        return name


def restart_program(app, ask=None):
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function.
    """
    log.debug("FlatCAMTranslation.restart_program()")

    theme_settings = QSettings("Open Source", "FlatCAM")
    if theme_settings.contains("theme"):
        theme = theme_settings.value('theme', type=str)
    else:
        theme = 'white'

    if theme == 'white':
        resource_loc = 'assets/resources'
    else:
        resource_loc = 'assets/resources'

    # try to quit the Socket opened by ArgsThread class
    try:
        app.new_launch.stop.emit()
        # app.new_launch.thread_exit = True
        # app.new_launch.listener.close()
    except Exception as err:
        log.debug("FlatCAMTranslation.restart_program() --> %s" % str(err))

    # try to quit the QThread that run ArgsThread class
    try:
        app.listen_th.quit()
    except Exception as err:
        log.debug("FlatCAMTranslation.restart_program() --> %s" % str(err))

    if app.should_we_save and app.collection.get_list() or ask is True:
        msgbox = QtWidgets.QMessageBox()
        msgbox.setText(_("There are files/objects modified in FlatCAM. "
                         "\n"
                         "Do you want to Save the project?"))
        msgbox.setWindowTitle(_("Save changes"))
        msgbox.setWindowIcon(QtGui.QIcon(resource_loc + '/save_as.png'))
        msgbox.setIcon(QtWidgets.QMessageBox.Question)

        bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
        bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)

        msgbox.setDefaultButton(bt_yes)
        msgbox.exec_()
        response = msgbox.clickedButton()

        if response == bt_yes:
            app.f_handlers.on_file_saveprojectas(use_thread=True, quit_action=True)

    app.preferencesUiManager.save_defaults()
    python = sys.executable
    os.execl(python, python, *sys.argv)
