from appGUI.GUIElements import *
from PyQt5.QtCore import QSettings
import gettext
import appTranslation as fcTranslate
import builtins


fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0
