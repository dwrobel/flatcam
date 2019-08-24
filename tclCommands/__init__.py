import pkgutil
import sys

# Todo: I think these imports are not needed.
# allowed command modules (please append them alphabetically ordered)
import tclCommands.TclCommandAddCircle
import tclCommands.TclCommandAddPolygon
import tclCommands.TclCommandAddPolyline
import tclCommands.TclCommandAddRectangle
import tclCommands.TclCommandAlignDrill
import tclCommands.TclCommandAlignDrillGrid
import tclCommands.TclCommandClearShell
import tclCommands.TclCommandCncjob
import tclCommands.TclCommandCutout
import tclCommands.TclCommandDelete
import tclCommands.TclCommandDrillcncjob
import tclCommands.TclCommandExportGcode
import tclCommands.TclCommandExportSVG
import tclCommands.TclCommandExteriors
import tclCommands.TclCommandGeoCutout
import tclCommands.TclCommandGeoUnion
import tclCommands.TclCommandGetNames
import tclCommands.TclCommandGetSys
import tclCommands.TclCommandImportSvg
import tclCommands.TclCommandInteriors
import tclCommands.TclCommandIsolate
import tclCommands.TclCommandFollow
import tclCommands.TclCommandJoinExcellon
import tclCommands.TclCommandJoinGeometry
import tclCommands.TclCommandListSys
import tclCommands.TclCommandMillHoles
import tclCommands.TclCommandMirror
import tclCommands.TclCommandNew
import tclCommands.TcLCommandNregions
import tclCommands.TclCommandNewGeometry
import tclCommands.TclCommandOffset
import tclCommands.TclCommandOpenExcellon
import tclCommands.TclCommandOpenGCode
import tclCommands.TclCommandOpenGerber
import tclCommands.TclCommandOpenProject
import tclCommands.TclCommandOptions
import tclCommands.TclCommandPaint
import tclCommands.TclCommandPanelize
import tclCommands.TclCommandPlot
import tclCommands.TclCommandSaveProject
import tclCommands.TclCommandSaveSys
import tclCommands.TclCommandScale
import tclCommands.TclCommandSetActive
import tclCommands.TclCommandSetSys
import tclCommands.TclCommandSkew
import tclCommands.TclCommandSubtractPoly
import tclCommands.TclCommandSubtractRectangle
import tclCommands.TclCommandVersion
import tclCommands.TclCommandWriteGCode


__all__ = []

for loader, name, is_pkg in pkgutil.walk_packages(__path__):
    module = loader.find_module(name).load_module(name)
    __all__.append(name)


def register_all_commands(app, commands):
    """
    Static method which registers all known commands.

    Command should  be for now in directory tclCommands and module should start with TCLCommand
    Class  have to follow same  name as module.

    we need import all  modules  in top section:
    import tclCommands.TclCommandExteriors
    at this stage we can include only wanted  commands  with this, auto loading may be implemented in future
    I have no enough knowledge about python's anatomy. Would be nice to include all classes which are descendant etc.

    :param app: FlatCAMApp
    :param commands: List of commands being updated
    :return: None
    """

    tcl_modules = {k: v for k, v in list(sys.modules.items()) if k.startswith('tclCommands.TclCommand')}

    for key, mod in list(tcl_modules.items()):
        if key != 'tclCommands.TclCommand':
            class_name = key.split('.')[1]
            class_type = getattr(mod, class_name)
            command_instance = class_type(app)

            for alias in command_instance.aliases:
                commands[alias] = {
                    'fcn': command_instance.execute_wrapper,
                    'help': command_instance.get_decorated_help()
                }
