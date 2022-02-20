from appGUI.GUIElements import FCCheckBox, FCLabel, FCFrame, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

class ToolsSubPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):

        super(ToolsSubPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Substractor Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.sublabel = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.sublabel.setToolTip(
            _("A tool to substract one Gerber or Geometry object\n"
              "from another of the same type.")
        )
        self.layout.addWidget(self.sublabel)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        self.close_paths_cb = FCCheckBox(_("Close paths"))
        self.close_paths_cb.setToolTip(_("Checking this will close the paths cut by the subtractor object."))
        param_grid.addWidget(self.close_paths_cb, 0, 0, 1, 2)

        self.delete_sources_cb = FCCheckBox(_("Delete source"))
        self.delete_sources_cb.setToolTip(
            _("When checked will delete the source objects\n"
              "after a successful operation.")
        )
        param_grid.addWidget(self.delete_sources_cb, 2, 0, 1, 2)
        self.layout.addStretch()
