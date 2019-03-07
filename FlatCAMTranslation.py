import os
from datetime import datetime

import FlatCAMApp
from FlatCAMApp import log

# ISO639-1 codes from here: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
languages_dict = {
    'de': 'German',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'it': 'Italian',
    'ro': 'Romanian',
    'ru': 'Russian',
    'zh': 'Chinese',
}

translations = {}

languages_path_search = ''


def load_languages(app):
    languages_path_search = os.path.join('locale')

    available_translations = next(os.walk(languages_path_search))[1]

    for lang in available_translations:
        try:
            if lang in languages_dict.keys():
                translations[lang] = languages_dict[lang]
        except KeyError as e:
            log.debug("FlatCAMTranslations.load_languages() --> %s" % str(e))
    return translations


def languages_dir(app):
    return os.path.join('locale')
