from appGUI.GUIElements import *

import gettext
import appTranslation as fcTranslate
import builtins


fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext
