############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
############################################################

import os
import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings

import FlatCAMApp
from GUIElements import log
import gettext

# ISO639-1 codes from here: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
languages_dict = {
    'zh': 'Chinese',
    'de': 'German',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'it': 'Italian',
    'ro': 'Romanian',
    'ru': 'Russian',
}

translations = {}

languages_path_search = ''


def load_languages():
    languages_path_search = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale')

    available_translations = next(os.walk(languages_path_search))[1]

    for lang in available_translations:
        try:
            if lang in languages_dict.keys():
                translations[lang] = languages_dict[lang]
        except KeyError as e:
            log.debug("FlatCAMTranslations.load_languages() --> %s" % str(e))
    return translations


def languages_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale')


def on_language_apply_click(app, restart=False):
    """
    Using instructions from here:
    https://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/

    :return:
    """
    name = app.ui.general_defaults_form.general_app_group.language_cb.currentText()

    # do nothing if trying to apply the language that is the current language (already applied).
    settings = QSettings("Open Source", "FlatCAM")
    if settings.contains("language"):
        current_language = settings.value('language', type=str)
        if current_language == name:
            return

    if restart:
        msgbox = QtWidgets.QMessageBox()
        msgbox.setText("The application will restart.")
        msgbox.setInformativeText("Are you sure do you want to change the current language to %s?" % name.capitalize())
        msgbox.setWindowTitle("Apply Language ...")
        msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
        msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)

        response = msgbox.exec_()

        if response == QtWidgets.QMessageBox.Cancel:
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
            name = settings.value('English')
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
            log.debug("FlatCAMTranslation.apply_language() --> %s" % str(e))

        return name


def restart_program(app):
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function.
    """
    app.save_defaults()
    python = sys.executable
    os.execl(python, python, *sys.argv)


