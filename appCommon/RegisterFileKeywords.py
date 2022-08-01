
from PyQt6.QtCore import pyqtSignal
from PyQt6 import QtCore

from dataclasses import dataclass
import ctypes
from copy import deepcopy
import os
import sys
import typing

if sys.platform == 'win32':
    import winreg

if typing.TYPE_CHECKING:
    import appMain


@dataclass
class KeyWords:
    """
    Holds the keywords recognized by the application
    """

    tcl_commands = [
        'add_aperture', 'add_circle', 'add_drill', 'add_poly', 'add_polygon', 'add_polyline',
        'add_rectangle', 'add_rect', 'add_slot',
        'aligndrill', 'aligndrillgrid', 'bbox', 'buffer', 'clear', 'cncjob', 'cutout',
        'del', 'drillcncjob', 'export_dxf', 'edxf', 'export_excellon',
        'export_exc',
        'export_gcode', 'export_gerber', 'export_svg', 'ext', 'exteriors', 'follow',
        'geo_union', 'geocutout', 'get_active', 'get_bounds', 'get_names', 'get_path',
        'get_sys', 'help',
        'interiors', 'isolate', 'join_excellon',
        'join_geometry', 'list_sys', 'list_pp', 'milld', 'mills', 'milldrills', 'millslots',
        'mirror', 'ncc',
        'ncr', 'new', 'new_geometry', 'new_gerber', 'new_excellon', 'non_copper_regions',
        'offset',
        'open_dxf', 'open_excellon', 'open_gcode', 'open_gerber', 'open_project', 'open_svg',
        'options', 'origin',
        'paint', 'panelize', 'plot_all', 'plot_objects', 'plot_status', 'quit_app',
        'save', 'save_project',
        'save_sys', 'scale', 'set_active', 'set_origin', 'set_path', 'set_sys',
        'skew', 'subtract_poly', 'subtract_rectangle',
        'version', 'write_gcode'
    ]

    # those need to be duplicated in self.options["util_autocomplete_keywords"] but within a string
    default_keywords = [
        'Berta_CNC', 'Default_no_M6', 'Desktop', 'Documents', 'FlatConfig', 'FlatPrj',
        'False', 'GRBL_11', 'GRL_11_no_M6', 'GRBL_laser', 'grbl_laser_eleks_drd',
        'GRBL_laser_z', 'ISEL_CNC', 'ISEL_ICP_CNC',
        'Line_xyz', 'Marlin',
        'Marlin_laser_FAN_pin', 'Marlin_laser_Spindle_pin', 'NCCAD9', 'Marius', 'My Documents',
        'Paste_1', 'Repetier', 'Roland_MDX_20', 'Roland_MDX_540',
        'Toolchange_Manual', 'Toolchange_Probe_MACH3',
        'True', 'Users',
        'all', 'auto', 'axis',
        'axisoffset', 'box', 'center_x', 'center_y', 'center', 'columns', 'combine', 'connect',
        'contour', 'default',
        'depthperpass', 'dia', 'diatol', 'dist', 'drilled_dias', 'drillz', 'dpp',
        'dwelltime', 'extracut_length', 'endxy', 'endz', 'f', 'factor', 'feedrate',
        'feedrate_z', 'gridoffsety', 'gridx', 'gridy',
        'has_offset', 'holes', 'hpgl', 'iso_type', 'join', 'keep_scripts',
        'las_min_pwr', 'las_power', 'margin', 'marlin', 'method',
        'milled_dias', 'minoffset', 'min_bounds', 'name', 'offset', 'opt_type', 'order',
        'outname', 'overlap', 'obj_name',
        'p_coords', 'passes', 'postamble', 'pp', 'ppname_e', 'ppname_g',
        'preamble', 'radius', 'ref', 'rest', 'rows', 'shellvar_', 'scale_factor',
        'spacing_columns',
        'spacing_rows', 'spindlespeed', 'startz', 'startxy',
        'toolchange_xy', 'toolchangez', 'travelz',
        'tooldia', 'use_threads', 'value',
        'x', 'x0', 'x1', 'x_dist', 'y', 'y0', 'y1', 'y_dist', 'z_cut', 'z_move'
    ]

    tcl_keywords = [
        'after', 'append', 'apply', 'argc', 'argv', 'argv0', 'array', 'attemptckalloc', 'attemptckrealloc',
        'auto_execok', 'auto_import', 'auto_load', 'auto_mkindex', 'auto_path', 'auto_qualify', 'auto_reset',
        'bgerror', 'binary', 'break', 'case', 'catch', 'cd', 'chan', 'ckalloc', 'ckfree', 'ckrealloc', 'clock',
        'close', 'concat', 'continue', 'coroutine', 'dde', 'dict', 'encoding', 'env', 'eof', 'error', 'errorCode',
        'errorInfo', 'eval', 'exec', 'exit', 'expr', 'fblocked', 'fconfigure', 'fcopy', 'file', 'fileevent',
        'filename', 'flush', 'for', 'foreach', 'format', 'gets', 'glob', 'global', 'history', 'http', 'if', 'incr',
        'info', 'interp', 'join', 'lappend', 'lassign', 'lindex', 'linsert', 'list', 'llength', 'load', 'lrange',
        'lrepeat', 'lreplace', 'lreverse', 'lsearch', 'lset', 'lsort', 'mathfunc', 'mathop', 'memory', 'msgcat',
        'my', 'namespace', 'next', 'nextto', 'open', 'package', 'parray', 'pid', 'pkg_mkIndex', 'platform',
        'proc', 'puts', 'pwd', 're_syntax', 'read', 'refchan', 'regexp', 'registry', 'regsub', 'rename', 'return',
        'safe', 'scan', 'seek', 'self', 'set', 'socket', 'source', 'split', 'string', 'subst', 'switch',
        'tailcall', 'Tcl', 'Tcl_Access', 'Tcl_AddErrorInfo', 'Tcl_AddObjErrorInfo', 'Tcl_AlertNotifier',
        'Tcl_Alloc', 'Tcl_AllocHashEntryProc', 'Tcl_AllocStatBuf', 'Tcl_AllowExceptions', 'Tcl_AppendAllObjTypes',
        'Tcl_AppendElement', 'Tcl_AppendExportList', 'Tcl_AppendFormatToObj', 'Tcl_AppendLimitedToObj',
        'Tcl_AppendObjToErrorInfo', 'Tcl_AppendObjToObj', 'Tcl_AppendPrintfToObj', 'Tcl_AppendResult',
        'Tcl_AppendResultVA', 'Tcl_AppendStringsToObj', 'Tcl_AppendStringsToObjVA', 'Tcl_AppendToObj',
        'Tcl_AppendUnicodeToObj', 'Tcl_AppInit', 'Tcl_AppInitProc', 'Tcl_ArgvInfo', 'Tcl_AsyncCreate',
        'Tcl_AsyncDelete', 'Tcl_AsyncInvoke', 'Tcl_AsyncMark', 'Tcl_AsyncProc', 'Tcl_AsyncReady',
        'Tcl_AttemptAlloc', 'Tcl_AttemptRealloc', 'Tcl_AttemptSetObjLength', 'Tcl_BackgroundError',
        'Tcl_BackgroundException', 'Tcl_Backslash', 'Tcl_BadChannelOption', 'Tcl_CallWhenDeleted', 'Tcl_Canceled',
        'Tcl_CancelEval', 'Tcl_CancelIdleCall', 'Tcl_ChannelBlockModeProc', 'Tcl_ChannelBuffered',
        'Tcl_ChannelClose2Proc', 'Tcl_ChannelCloseProc', 'Tcl_ChannelFlushProc', 'Tcl_ChannelGetHandleProc',
        'Tcl_ChannelGetOptionProc', 'Tcl_ChannelHandlerProc', 'Tcl_ChannelInputProc', 'Tcl_ChannelName',
        'Tcl_ChannelOutputProc', 'Tcl_ChannelProc', 'Tcl_ChannelSeekProc', 'Tcl_ChannelSetOptionProc',
        'Tcl_ChannelThreadActionProc', 'Tcl_ChannelTruncateProc', 'Tcl_ChannelType', 'Tcl_ChannelVersion',
        'Tcl_ChannelWatchProc', 'Tcl_ChannelWideSeekProc', 'Tcl_Chdir', 'Tcl_ClassGetMetadata',
        'Tcl_ClassSetConstructor', 'Tcl_ClassSetDestructor', 'Tcl_ClassSetMetadata', 'Tcl_ClearChannelHandlers',
        'Tcl_CloneProc', 'Tcl_Close', 'Tcl_CloseProc', 'Tcl_CmdDeleteProc', 'Tcl_CmdInfo',
        'Tcl_CmdObjTraceDeleteProc', 'Tcl_CmdObjTraceProc', 'Tcl_CmdProc', 'Tcl_CmdTraceProc',
        'Tcl_CommandComplete', 'Tcl_CommandTraceInfo', 'Tcl_CommandTraceProc', 'Tcl_CompareHashKeysProc',
        'Tcl_Concat', 'Tcl_ConcatObj', 'Tcl_ConditionFinalize', 'Tcl_ConditionNotify', 'Tcl_ConditionWait',
        'Tcl_Config', 'Tcl_ConvertCountedElement', 'Tcl_ConvertElement', 'Tcl_ConvertToType',
        'Tcl_CopyObjectInstance', 'Tcl_CreateAlias', 'Tcl_CreateAliasObj', 'Tcl_CreateChannel',
        'Tcl_CreateChannelHandler', 'Tcl_CreateCloseHandler', 'Tcl_CreateCommand', 'Tcl_CreateEncoding',
        'Tcl_CreateEnsemble', 'Tcl_CreateEventSource', 'Tcl_CreateExitHandler', 'Tcl_CreateFileHandler',
        'Tcl_CreateHashEntry', 'Tcl_CreateInterp', 'Tcl_CreateMathFunc', 'Tcl_CreateNamespace',
        'Tcl_CreateObjCommand', 'Tcl_CreateObjTrace', 'Tcl_CreateSlave', 'Tcl_CreateThread',
        'Tcl_CreateThreadExitHandler', 'Tcl_CreateTimerHandler', 'Tcl_CreateTrace',
        'Tcl_CutChannel', 'Tcl_DecrRefCount', 'Tcl_DeleteAssocData', 'Tcl_DeleteChannelHandler',
        'Tcl_DeleteCloseHandler', 'Tcl_DeleteCommand', 'Tcl_DeleteCommandFromToken', 'Tcl_DeleteEvents',
        'Tcl_DeleteEventSource', 'Tcl_DeleteExitHandler', 'Tcl_DeleteFileHandler', 'Tcl_DeleteHashEntry',
        'Tcl_DeleteHashTable', 'Tcl_DeleteInterp', 'Tcl_DeleteNamespace', 'Tcl_DeleteThreadExitHandler',
        'Tcl_DeleteTimerHandler', 'Tcl_DeleteTrace', 'Tcl_DetachChannel', 'Tcl_DetachPids', 'Tcl_DictObjDone',
        'Tcl_DictObjFirst', 'Tcl_DictObjGet', 'Tcl_DictObjNext', 'Tcl_DictObjPut', 'Tcl_DictObjPutKeyList',
        'Tcl_DictObjRemove', 'Tcl_DictObjRemoveKeyList', 'Tcl_DictObjSize', 'Tcl_DiscardInterpState',
        'Tcl_DiscardResult', 'Tcl_DontCallWhenDeleted', 'Tcl_DoOneEvent', 'Tcl_DoWhenIdle',
        'Tcl_DriverBlockModeProc', 'Tcl_DriverClose2Proc', 'Tcl_DriverCloseProc', 'Tcl_DriverFlushProc',
        'Tcl_DriverGetHandleProc', 'Tcl_DriverGetOptionProc', 'Tcl_DriverHandlerProc', 'Tcl_DriverInputProc',
        'Tcl_DriverOutputProc', 'Tcl_DriverSeekProc', 'Tcl_DriverSetOptionProc', 'Tcl_DriverThreadActionProc',
        'Tcl_DriverTruncateProc', 'Tcl_DriverWatchProc', 'Tcl_DriverWideSeekProc', 'Tcl_DStringAppend',
        'Tcl_DStringAppendElement', 'Tcl_DStringEndSublist', 'Tcl_DStringFree', 'Tcl_DStringGetResult',
        'Tcl_DStringInit', 'Tcl_DStringLength', 'Tcl_DStringResult', 'Tcl_DStringSetLength',
        'Tcl_DStringStartSublist', 'Tcl_DStringTrunc', 'Tcl_DStringValue', 'Tcl_DumpActiveMemory',
        'Tcl_DupInternalRepProc', 'Tcl_DuplicateObj', 'Tcl_EncodingConvertProc', 'Tcl_EncodingFreeProc',
        'Tcl_EncodingType', 'tcl_endOfWord', 'Tcl_Eof', 'Tcl_ErrnoId', 'Tcl_ErrnoMsg', 'Tcl_Eval', 'Tcl_EvalEx',
        'Tcl_EvalFile', 'Tcl_EvalObjEx', 'Tcl_EvalObjv', 'Tcl_EvalTokens', 'Tcl_EvalTokensStandard', 'Tcl_Event',
        'Tcl_EventCheckProc', 'Tcl_EventDeleteProc', 'Tcl_EventProc', 'Tcl_EventSetupProc', 'Tcl_EventuallyFree',
        'Tcl_Exit', 'Tcl_ExitProc', 'Tcl_ExitThread', 'Tcl_Export', 'Tcl_ExposeCommand', 'Tcl_ExprBoolean',
        'Tcl_ExprBooleanObj', 'Tcl_ExprDouble', 'Tcl_ExprDoubleObj', 'Tcl_ExprLong', 'Tcl_ExprLongObj',
        'Tcl_ExprObj', 'Tcl_ExprString', 'Tcl_ExternalToUtf', 'Tcl_ExternalToUtfDString', 'Tcl_FileProc',
        'Tcl_Filesystem', 'Tcl_Finalize', 'Tcl_FinalizeNotifier', 'Tcl_FinalizeThread', 'Tcl_FindCommand',
        'Tcl_FindEnsemble', 'Tcl_FindExecutable', 'Tcl_FindHashEntry', 'tcl_findLibrary', 'Tcl_FindNamespace',
        'Tcl_FirstHashEntry', 'Tcl_Flush', 'Tcl_ForgetImport', 'Tcl_Format', 'Tcl_FreeHashEntryProc',
        'Tcl_FreeInternalRepProc', 'Tcl_FreeParse', 'Tcl_FreeProc', 'Tcl_FreeResult',
        'Tcl_Free·\xa0Tcl_FreeEncoding', 'Tcl_FSAccess', 'Tcl_FSAccessProc', 'Tcl_FSChdir',
        'Tcl_FSChdirProc', 'Tcl_FSConvertToPathType', 'Tcl_FSCopyDirectory', 'Tcl_FSCopyDirectoryProc',
        'Tcl_FSCopyFile', 'Tcl_FSCopyFileProc', 'Tcl_FSCreateDirectory', 'Tcl_FSCreateDirectoryProc',
        'Tcl_FSCreateInternalRepProc', 'Tcl_FSData', 'Tcl_FSDeleteFile', 'Tcl_FSDeleteFileProc',
        'Tcl_FSDupInternalRepProc', 'Tcl_FSEqualPaths', 'Tcl_FSEvalFile', 'Tcl_FSEvalFileEx',
        'Tcl_FSFileAttrsGet', 'Tcl_FSFileAttrsGetProc', 'Tcl_FSFileAttrsSet', 'Tcl_FSFileAttrsSetProc',
        'Tcl_FSFileAttrStrings', 'Tcl_FSFileSystemInfo', 'Tcl_FSFilesystemPathTypeProc',
        'Tcl_FSFilesystemSeparatorProc', 'Tcl_FSFreeInternalRepProc', 'Tcl_FSGetCwd', 'Tcl_FSGetCwdProc',
        'Tcl_FSGetFileSystemForPath', 'Tcl_FSGetInternalRep', 'Tcl_FSGetNativePath', 'Tcl_FSGetNormalizedPath',
        'Tcl_FSGetPathType', 'Tcl_FSGetTranslatedPath', 'Tcl_FSGetTranslatedStringPath',
        'Tcl_FSInternalToNormalizedProc', 'Tcl_FSJoinPath', 'Tcl_FSJoinToPath', 'Tcl_FSLinkProc',
        'Tcl_FSLink·\xa0Tcl_FSListVolumes', 'Tcl_FSListVolumesProc', 'Tcl_FSLoadFile', 'Tcl_FSLoadFileProc',
        'Tcl_FSLstat', 'Tcl_FSLstatProc', 'Tcl_FSMatchInDirectory', 'Tcl_FSMatchInDirectoryProc',
        'Tcl_FSMountsChanged', 'Tcl_FSNewNativePath', 'Tcl_FSNormalizePathProc', 'Tcl_FSOpenFileChannel',
        'Tcl_FSOpenFileChannelProc', 'Tcl_FSPathInFilesystemProc', 'Tcl_FSPathSeparator', 'Tcl_FSRegister',
        'Tcl_FSRemoveDirectory', 'Tcl_FSRemoveDirectoryProc', 'Tcl_FSRenameFile', 'Tcl_FSRenameFileProc',
        'Tcl_FSSplitPath', 'Tcl_FSStat', 'Tcl_FSStatProc', 'Tcl_FSUnloadFile', 'Tcl_FSUnloadFileProc',
        'Tcl_FSUnregister', 'Tcl_FSUtime', 'Tcl_FSUtimeProc', 'Tcl_GetAccessTimeFromStat', 'Tcl_GetAlias',
        'Tcl_GetAliasObj', 'Tcl_GetAssocData', 'Tcl_GetBignumFromObj', 'Tcl_GetBlocksFromStat',
        'Tcl_GetBlockSizeFromStat', 'Tcl_GetBoolean', 'Tcl_GetBooleanFromObj', 'Tcl_GetByteArrayFromObj',
        'Tcl_GetChangeTimeFromStat', 'Tcl_GetChannel', 'Tcl_GetChannelBufferSize', 'Tcl_GetChannelError',
        'Tcl_GetChannelErrorInterp', 'Tcl_GetChannelHandle', 'Tcl_GetChannelInstanceData', 'Tcl_GetChannelMode',
        'Tcl_GetChannelName', 'Tcl_GetChannelNames', 'Tcl_GetChannelNamesEx', 'Tcl_GetChannelOption',
        'Tcl_GetChannelThread', 'Tcl_GetChannelType', 'Tcl_GetCharLength', 'Tcl_GetClassAsObject',
        'Tcl_GetCommandFromObj', 'Tcl_GetCommandFullName', 'Tcl_GetCommandInfo', 'Tcl_GetCommandInfoFromToken',
        'Tcl_GetCommandName', 'Tcl_GetCurrentNamespace', 'Tcl_GetCurrentThread', 'Tcl_GetCwd',
        'Tcl_GetDefaultEncodingDir', 'Tcl_GetDeviceTypeFromStat', 'Tcl_GetDouble', 'Tcl_GetDoubleFromObj',
        'Tcl_GetEncoding', 'Tcl_GetEncodingFromObj', 'Tcl_GetEncodingName', 'Tcl_GetEncodingNameFromEnvironment',
        'Tcl_GetEncodingNames', 'Tcl_GetEncodingSearchPath', 'Tcl_GetEnsembleFlags', 'Tcl_GetEnsembleMappingDict',
        'Tcl_GetEnsembleNamespace', 'Tcl_GetEnsembleParameterList', 'Tcl_GetEnsembleSubcommandList',
        'Tcl_GetEnsembleUnknownHandler', 'Tcl_GetErrno', 'Tcl_GetErrorLine', 'Tcl_GetFSDeviceFromStat',
        'Tcl_GetFSInodeFromStat', 'Tcl_GetGlobalNamespace', 'Tcl_GetGroupIdFromStat', 'Tcl_GetHashKey',
        'Tcl_GetHashValue', 'Tcl_GetHostName', 'Tcl_GetIndexFromObj', 'Tcl_GetIndexFromObjStruct', 'Tcl_GetInt',
        'Tcl_GetInterpPath', 'Tcl_GetIntFromObj', 'Tcl_GetLinkCountFromStat', 'Tcl_GetLongFromObj',
        'Tcl_GetMaster', 'Tcl_GetMathFuncInfo', 'Tcl_GetModeFromStat', 'Tcl_GetModificationTimeFromStat',
        'Tcl_GetNameOfExecutable', 'Tcl_GetNamespaceUnknownHandler', 'Tcl_GetObjectAsClass', 'Tcl_GetObjectCommand',
        'Tcl_GetObjectFromObj', 'Tcl_GetObjectName', 'Tcl_GetObjectNamespace', 'Tcl_GetObjResult', 'Tcl_GetObjType',
        'Tcl_GetOpenFile', 'Tcl_GetPathType', 'Tcl_GetRange', 'Tcl_GetRegExpFromObj', 'Tcl_GetReturnOptions',
        'Tcl_Gets', 'Tcl_GetServiceMode', 'Tcl_GetSizeFromStat', 'Tcl_GetSlave', 'Tcl_GetsObj',
        'Tcl_GetStackedChannel', 'Tcl_GetStartupScript', 'Tcl_GetStdChannel', 'Tcl_GetString',
        'Tcl_GetStringFromObj', 'Tcl_GetStringResult', 'Tcl_GetThreadData', 'Tcl_GetTime', 'Tcl_GetTopChannel',
        'Tcl_GetUniChar', 'Tcl_GetUnicode', 'Tcl_GetUnicodeFromObj', 'Tcl_GetUserIdFromStat', 'Tcl_GetVar',
        'Tcl_GetVar2', 'Tcl_GetVar2Ex', 'Tcl_GetVersion', 'Tcl_GetWideIntFromObj', 'Tcl_GlobalEval',
        'Tcl_GlobalEvalObj', 'Tcl_GlobTypeData', 'Tcl_HashKeyType', 'Tcl_HashStats', 'Tcl_HideCommand',
        'Tcl_IdleProc', 'Tcl_Import', 'Tcl_IncrRefCount', 'Tcl_Init', 'Tcl_InitCustomHashTable',
        'Tcl_InitHashTable', 'Tcl_InitMemory', 'Tcl_InitNotifier', 'Tcl_InitObjHashTable', 'Tcl_InitStubs',
        'Tcl_InputBlocked', 'Tcl_InputBuffered', 'tcl_interactive', 'Tcl_Interp', 'Tcl_InterpActive',
        'Tcl_InterpDeleted', 'Tcl_InterpDeleteProc', 'Tcl_InvalidateStringRep', 'Tcl_IsChannelExisting',
        'Tcl_IsChannelRegistered', 'Tcl_IsChannelShared', 'Tcl_IsEnsemble', 'Tcl_IsSafe', 'Tcl_IsShared',
        'Tcl_IsStandardChannel', 'Tcl_JoinPath', 'Tcl_JoinThread', 'tcl_library', 'Tcl_LimitAddHandler',
        'Tcl_LimitCheck', 'Tcl_LimitExceeded', 'Tcl_LimitGetCommands', 'Tcl_LimitGetGranularity',
        'Tcl_LimitGetTime', 'Tcl_LimitHandlerDeleteProc', 'Tcl_LimitHandlerProc', 'Tcl_LimitReady',
        'Tcl_LimitRemoveHandler', 'Tcl_LimitSetCommands', 'Tcl_LimitSetGranularity', 'Tcl_LimitSetTime',
        'Tcl_LimitTypeEnabled', 'Tcl_LimitTypeExceeded', 'Tcl_LimitTypeReset', 'Tcl_LimitTypeSet',
        'Tcl_LinkVar', 'Tcl_ListMathFuncs', 'Tcl_ListObjAppendElement', 'Tcl_ListObjAppendList',
        'Tcl_ListObjGetElements', 'Tcl_ListObjIndex', 'Tcl_ListObjLength', 'Tcl_ListObjReplace',
        'Tcl_LogCommandInfo', 'Tcl_Main', 'Tcl_MainLoopProc', 'Tcl_MakeFileChannel', 'Tcl_MakeSafe',
        'Tcl_MakeTcpClientChannel', 'Tcl_MathProc', 'TCL_MEM_DEBUG', 'Tcl_Merge', 'Tcl_MethodCallProc',
        'Tcl_MethodDeclarerClass', 'Tcl_MethodDeclarerObject', 'Tcl_MethodDeleteProc', 'Tcl_MethodIsPublic',
        'Tcl_MethodIsType', 'Tcl_MethodName', 'Tcl_MethodType', 'Tcl_MutexFinalize', 'Tcl_MutexLock',
        'Tcl_MutexUnlock', 'Tcl_NamespaceDeleteProc', 'Tcl_NewBignumObj', 'Tcl_NewBooleanObj',
        'Tcl_NewByteArrayObj', 'Tcl_NewDictObj', 'Tcl_NewDoubleObj', 'Tcl_NewInstanceMethod', 'Tcl_NewIntObj',
        'Tcl_NewListObj', 'Tcl_NewLongObj', 'Tcl_NewMethod', 'Tcl_NewObj', 'Tcl_NewObjectInstance',
        'Tcl_NewStringObj', 'Tcl_NewUnicodeObj', 'Tcl_NewWideIntObj', 'Tcl_NextHashEntry', 'tcl_nonwordchars',
        'Tcl_NotifierProcs', 'Tcl_NotifyChannel', 'Tcl_NRAddCallback', 'Tcl_NRCallObjProc', 'Tcl_NRCmdSwap',
        'Tcl_NRCreateCommand', 'Tcl_NREvalObj', 'Tcl_NREvalObjv', 'Tcl_NumUtfChars', 'Tcl_Obj', 'Tcl_ObjCmdProc',
        'Tcl_ObjectContextInvokeNext', 'Tcl_ObjectContextIsFiltering', 'Tcl_ObjectContextMethod',
        'Tcl_ObjectContextObject', 'Tcl_ObjectContextSkippedArgs', 'Tcl_ObjectDeleted', 'Tcl_ObjectGetMetadata',
        'Tcl_ObjectGetMethodNameMapper', 'Tcl_ObjectMapMethodNameProc', 'Tcl_ObjectMetadataDeleteProc',
        'Tcl_ObjectSetMetadata', 'Tcl_ObjectSetMethodNameMapper', 'Tcl_ObjGetVar2', 'Tcl_ObjPrintf',
        'Tcl_ObjSetVar2', 'Tcl_ObjType', 'Tcl_OpenCommandChannel', 'Tcl_OpenFileChannel', 'Tcl_OpenTcpClient',
        'Tcl_OpenTcpServer', 'Tcl_OutputBuffered', 'Tcl_PackageInitProc', 'Tcl_PackageUnloadProc', 'Tcl_Panic',
        'Tcl_PanicProc', 'Tcl_PanicVA', 'Tcl_ParseArgsObjv', 'Tcl_ParseBraces', 'Tcl_ParseCommand', 'Tcl_ParseExpr',
        'Tcl_ParseQuotedString', 'Tcl_ParseVar', 'Tcl_ParseVarName', 'tcl_patchLevel', 'tcl_pkgPath',
        'Tcl_PkgPresent', 'Tcl_PkgPresentEx', 'Tcl_PkgProvide', 'Tcl_PkgProvideEx', 'Tcl_PkgRequire',
        'Tcl_PkgRequireEx', 'Tcl_PkgRequireProc', 'tcl_platform', 'Tcl_PosixError', 'tcl_precision',
        'Tcl_Preserve', 'Tcl_PrintDouble', 'Tcl_PutEnv', 'Tcl_QueryTimeProc', 'Tcl_QueueEvent', 'tcl_rcFileName',
        'Tcl_Read', 'Tcl_ReadChars', 'Tcl_ReadRaw', 'Tcl_Realloc', 'Tcl_ReapDetachedProcs', 'Tcl_RecordAndEval',
        'Tcl_RecordAndEvalObj', 'Tcl_RegExpCompile', 'Tcl_RegExpExec', 'Tcl_RegExpExecObj', 'Tcl_RegExpGetInfo',
        'Tcl_RegExpIndices', 'Tcl_RegExpInfo', 'Tcl_RegExpMatch', 'Tcl_RegExpMatchObj', 'Tcl_RegExpRange',
        'Tcl_RegisterChannel', 'Tcl_RegisterConfig', 'Tcl_RegisterObjType', 'Tcl_Release', 'Tcl_ResetResult',
        'Tcl_RestoreInterpState', 'Tcl_RestoreResult', 'Tcl_SaveInterpState', 'Tcl_SaveResult', 'Tcl_ScaleTimeProc',
        'Tcl_ScanCountedElement', 'Tcl_ScanElement', 'Tcl_Seek', 'Tcl_ServiceAll', 'Tcl_ServiceEvent',
        'Tcl_ServiceModeHook', 'Tcl_SetAssocData', 'Tcl_SetBignumObj', 'Tcl_SetBooleanObj',
        'Tcl_SetByteArrayLength', 'Tcl_SetByteArrayObj', 'Tcl_SetChannelBufferSize', 'Tcl_SetChannelError',
        'Tcl_SetChannelErrorInterp', 'Tcl_SetChannelOption', 'Tcl_SetCommandInfo', 'Tcl_SetCommandInfoFromToken',
        'Tcl_SetDefaultEncodingDir', 'Tcl_SetDoubleObj', 'Tcl_SetEncodingSearchPath', 'Tcl_SetEnsembleFlags',
        'Tcl_SetEnsembleMappingDict', 'Tcl_SetEnsembleParameterList', 'Tcl_SetEnsembleSubcommandList',
        'Tcl_SetEnsembleUnknownHandler', 'Tcl_SetErrno', 'Tcl_SetErrorCode', 'Tcl_SetErrorCodeVA',
        'Tcl_SetErrorLine', 'Tcl_SetExitProc', 'Tcl_SetFromAnyProc', 'Tcl_SetHashValue', 'Tcl_SetIntObj',
        'Tcl_SetListObj', 'Tcl_SetLongObj', 'Tcl_SetMainLoop', 'Tcl_SetMaxBlockTime',
        'Tcl_SetNamespaceUnknownHandler', 'Tcl_SetNotifier', 'Tcl_SetObjErrorCode', 'Tcl_SetObjLength',
        'Tcl_SetObjResult', 'Tcl_SetPanicProc', 'Tcl_SetRecursionLimit', 'Tcl_SetResult', 'Tcl_SetReturnOptions',
        'Tcl_SetServiceMode', 'Tcl_SetStartupScript', 'Tcl_SetStdChannel', 'Tcl_SetStringObj',
        'Tcl_SetSystemEncoding', 'Tcl_SetTimeProc', 'Tcl_SetTimer', 'Tcl_SetUnicodeObj', 'Tcl_SetVar',
        'Tcl_SetVar2', 'Tcl_SetVar2Ex', 'Tcl_SetWideIntObj', 'Tcl_SignalId', 'Tcl_SignalMsg', 'Tcl_Sleep',
        'Tcl_SourceRCFile', 'Tcl_SpliceChannel', 'Tcl_SplitList', 'Tcl_SplitPath', 'Tcl_StackChannel',
        'Tcl_StandardChannels', 'tcl_startOfNextWord', 'tcl_startOfPreviousWord', 'Tcl_Stat', 'Tcl_StaticPackage',
        'Tcl_StringCaseMatch', 'Tcl_StringMatch', 'Tcl_SubstObj', 'Tcl_TakeBignumFromObj', 'Tcl_TcpAcceptProc',
        'Tcl_Tell', 'Tcl_ThreadAlert', 'Tcl_ThreadQueueEvent', 'Tcl_Time', 'Tcl_TimerProc', 'Tcl_Token',
        'Tcl_TraceCommand', 'tcl_traceCompile', 'tcl_traceEval', 'Tcl_TraceVar', 'Tcl_TraceVar2',
        'Tcl_TransferResult', 'Tcl_TranslateFileName', 'Tcl_TruncateChannel', 'Tcl_Ungets', 'Tcl_UniChar',
        'Tcl_UniCharAtIndex', 'Tcl_UniCharCaseMatch', 'Tcl_UniCharIsAlnum', 'Tcl_UniCharIsAlpha',
        'Tcl_UniCharIsControl', 'Tcl_UniCharIsDigit', 'Tcl_UniCharIsGraph', 'Tcl_UniCharIsLower',
        'Tcl_UniCharIsPrint', 'Tcl_UniCharIsPunct', 'Tcl_UniCharIsSpace', 'Tcl_UniCharIsUpper',
        'Tcl_UniCharIsWordChar', 'Tcl_UniCharLen', 'Tcl_UniCharNcasecmp', 'Tcl_UniCharNcmp', 'Tcl_UniCharToLower',
        'Tcl_UniCharToTitle', 'Tcl_UniCharToUpper', 'Tcl_UniCharToUtf', 'Tcl_UniCharToUtfDString', 'Tcl_UnlinkVar',
        'Tcl_UnregisterChannel', 'Tcl_UnsetVar', 'Tcl_UnsetVar2', 'Tcl_UnstackChannel', 'Tcl_UntraceCommand',
        'Tcl_UntraceVar', 'Tcl_UntraceVar2', 'Tcl_UpdateLinkedVar', 'Tcl_UpdateStringProc', 'Tcl_UpVar',
        'Tcl_UpVar2', 'Tcl_UtfAtIndex', 'Tcl_UtfBackslash', 'Tcl_UtfCharComplete', 'Tcl_UtfFindFirst',
        'Tcl_UtfFindLast', 'Tcl_UtfNext', 'Tcl_UtfPrev', 'Tcl_UtfToExternal', 'Tcl_UtfToExternalDString',
        'Tcl_UtfToLower', 'Tcl_UtfToTitle', 'Tcl_UtfToUniChar', 'Tcl_UtfToUniCharDString', 'Tcl_UtfToUpper',
        'Tcl_ValidateAllMemory', 'Tcl_Value', 'Tcl_VarEval', 'Tcl_VarEvalVA', 'Tcl_VarTraceInfo',
        'Tcl_VarTraceInfo2', 'Tcl_VarTraceProc', 'tcl_version', 'Tcl_WaitForEvent', 'Tcl_WaitPid',
        'Tcl_WinTCharToUtf', 'Tcl_WinUtfToTChar', 'tcl_wordBreakAfter', 'tcl_wordBreakBefore', 'tcl_wordchars',
        'Tcl_Write', 'Tcl_WriteChars', 'Tcl_WriteObj', 'Tcl_WriteRaw', 'Tcl_WrongNumArgs', 'Tcl_ZlibAdler32',
        'Tcl_ZlibCRC32', 'Tcl_ZlibDeflate', 'Tcl_ZlibInflate', 'Tcl_ZlibStreamChecksum', 'Tcl_ZlibStreamClose',
        'Tcl_ZlibStreamEof', 'Tcl_ZlibStreamGet', 'Tcl_ZlibStreamGetCommandName', 'Tcl_ZlibStreamInit',
        'Tcl_ZlibStreamPut', 'tcltest', 'tell', 'throw', 'time', 'tm', 'trace', 'transchan', 'try', 'unknown',
        'unload', 'unset', 'update', 'uplevel', 'upvar', 'variable', 'vwait', 'while', 'yield', 'yieldto', 'zlib'
    ]


@dataclass
class Extensions:
    """
    Holds the file extensions recognized by the application
    """

    grb_list = [
        'art', 'bot', 'bsm', 'cmp', 'crc', 'crs', 'dim', 'g4', 'gb0', 'gb1', 'gb2', 'gb3', 'gb5',
        'gb6', 'gb7', 'gb8', 'gb9', 'gbd', 'gbl', 'gbo', 'gbp', 'gbr', 'gbs', 'gdo', 'ger', 'gko',
        'gml', 'gm1', 'gm2', 'gm3', 'grb', 'gtl', 'gto', 'gtp', 'gts', 'ly15', 'ly2', 'mil', 'outline',
        'pho', 'plc', 'pls', 'smb', 'smt', 'sol', 'spb', 'spt', 'ssb', 'sst', 'stc', 'sts', 'top',
        'tsm'
    ]

    exc_list = ['drd', 'drl', 'drill', 'exc', 'ncd', 'tap', 'txt', 'xln']

    gcode_list = [
        'cnc', 'din', 'dnc', 'ecs', 'eia', 'fan', 'fgc', 'fnc', 'gc', 'gcd', 'gcode', 'h', 'hnc',
        'i', 'min', 'mpf', 'mpr', 'nc', 'ncc', 'ncg', 'ngc', 'ncp', 'out', 'ply', 'rol',
        'sbp', 'tap', 'xpi'
    ]
    svg_list = ['svg']
    dxf_list = ['dxf']
    pdf_list = ['pdf']
    prj_list = ['flatprj']
    conf_list = ['flatconfig']


class RegisterFK(QtCore.QObject):
    """
    Will associate the application with some files with certain extensions. It will also update the Qt autocompleter.
    """

    def __init__(self,
                 ui: 'appMain.MainGUI',
                 inform_sig: pyqtSignal,
                 options_dict: 'appMain.AppOptions',
                 shell: 'appMain.FCShell',
                 log: ('appMain.AppLogging', 'appMain.logging'),
                 keywords: KeyWords,
                 extensions: Extensions):

        super().__init__()
        self.ui = ui
        self.shell = shell
        self.log = log
        self.inform = inform_sig
        self.options = options_dict
        self.keywords = keywords

        self.tcl_keywords = self.keywords.tcl_keywords
        self.tcl_commands_list = self.keywords.tcl_commands
        self.default_keywords = self.keywords.default_keywords

        self.exc_list = extensions.exc_list
        self.grb_list = extensions.grb_list
        self.gcode_list = extensions.gcode_list
        self.svg_list = extensions.svg_list
        self.dxf_list = extensions.dxf_list
        self.pdf_list = extensions.pdf_list
        self.prj_list = extensions.prj_list
        self.conf_list = extensions.conf_list

        autocomplete_kw_list = self.options['util_autocomplete_keywords'].replace(' ', '').split(',')
        self.myKeywords = self.tcl_commands_list + autocomplete_kw_list + self.tcl_keywords

        # initial register of keywords for the shell
        self.register_keywords(self.myKeywords)

        self.connect_signals()

        # ###########################################################################################################
        # ##################################### Register files with FlatCAM;  #######################################
        # ################################### It works only for Windows for now  ####################################
        # ###########################################################################################################
        if sys.platform == 'win32' and self.options["first_run"] is True:
            self.on_register_files()

    def connect_signals(self):
        # ###########################################################################################################
        # ####################################### FILE ASSOCIATIONS SIGNALS #########################################
        # ###########################################################################################################
        self.ui.util_pref_form.fa_excellon_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='excellon'))
        self.ui.util_pref_form.fa_gcode_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='gcode'))
        self.ui.util_pref_form.fa_gerber_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='gerber'))

        self.ui.util_pref_form.fa_excellon_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='excellon'))
        self.ui.util_pref_form.fa_gcode_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='gcode'))
        self.ui.util_pref_form.fa_gerber_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='gerber'))

        self.ui.util_pref_form.fa_excellon_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='excellon'))
        self.ui.util_pref_form.fa_gcode_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='gcode'))
        self.ui.util_pref_form.fa_gerber_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='gerber'))

        self.ui.util_pref_form.fa_excellon_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='excellon'))
        self.ui.util_pref_form.fa_gcode_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='gcode'))
        self.ui.util_pref_form.fa_gerber_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='gerber'))

        # connect the 'Apply' buttons from the Preferences/File Associations
        self.ui.util_pref_form.fa_excellon_group.exc_list_btn.clicked.connect(
            lambda: self.on_register_files(obj_type='excellon'))
        self.ui.util_pref_form.fa_gcode_group.gco_list_btn.clicked.connect(
            lambda: self.on_register_files(obj_type='gcode'))
        self.ui.util_pref_form.fa_gerber_group.grb_list_btn.clicked.connect(
            lambda: self.on_register_files(obj_type='gerber'))

        # ###########################################################################################################
        # ########################################### KEYWORDS SIGNALS ##############################################
        # ###########################################################################################################
        self.ui.util_pref_form.kw_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='keyword'))
        self.ui.util_pref_form.kw_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='keyword'))
        self.ui.util_pref_form.kw_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='keyword'))
        self.ui.util_pref_form.kw_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='keyword'))

    def register_keywords(self, keywords=None):
        if keywords is None:
            self.shell.command_line().set_model_data(self.myKeywords)
            return
        self.myKeywords = keywords
        self.shell.command_line().set_model_data(self.myKeywords)

    def prepend_keyword(self, kw, update=True):
        self.myKeywords.insert(0, kw)
        if update:
            self.register_keywords(self.myKeywords)

    def append_keyword(self, kw, update=True):
        self.myKeywords.append(kw)
        if update:
            self.register_keywords(self.myKeywords)

    def remove_keyword(self, kw, update=True):
        self.myKeywords.remove(kw)
        if update:
            self.register_keywords(self.myKeywords)

    @staticmethod
    def set_reg(name, root_pth, new_reg_path_par, value):
        # create the keys
        try:
            winreg.CreateKey(root_pth, new_reg_path_par)
            with winreg.OpenKey(root_pth, new_reg_path_par, 0, winreg.KEY_WRITE) as registry_key:
                winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
            return True
        except WindowsError:
            return False

    @staticmethod
    def delete_reg(root_pth, reg_path, key_to_del):
        # delete key in registry
        key_to_del_path = reg_path + key_to_del
        try:
            winreg.DeleteKey(root_pth, key_to_del_path)
            return True
        except WindowsError:
            return False

    def on_register_files(self, obj_type=None):
        """
        Called whenever there is a need to register file extensions with FlatCAM.
        Works only in Windows and should be called only when FlatCAM is run in Windows.

        :param obj_type: the type of object to be register for.
        Can be: 'gerber', 'excellon' or 'gcode'. 'geometry' is not used for the moment.

        :return: None
        """
        self.log.debug("Manufacturing files extensions are registered with FlatCAM.")

        # find if the current user is admin
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() == 1

        if is_admin is True:
            root_path = winreg.HKEY_LOCAL_MACHINE
        else:
            root_path = winreg.HKEY_CURRENT_USER

        if obj_type is None or obj_type == 'excellon':
            self.register_excellon_extension(root_path)

        if obj_type is None or obj_type == 'gcode':
            self.register_gcode_extension(root_path)

        if obj_type is None or obj_type == 'gerber':
            self.register_gerber_extension(root_path)

    def register_excellon_extension(self, root_path):
        new_reg_path = 'Software\\Classes\\'

        exc_list = \
            self.ui.util_pref_form.fa_excellon_group.exc_list_text.get_value().replace(' ', '').split(',')
        exc_list = [x for x in exc_list if x != '']

        # register all keys in the Preferences window
        for ext in exc_list:
            new_k = new_reg_path + '.%s' % ext
            self.set_reg('', root_pth=root_path, new_reg_path_par=new_k, value='FlatCAM')

        # and unregister those that are no longer in the Preferences windows but are in the file
        for ext in self.options["fa_excellon"].replace(' ', '').split(','):
            if ext not in exc_list:
                self.delete_reg(root_pth=root_path, reg_path=new_reg_path, key_to_del='.%s' % ext)

        # now write the updated extensions to the self.options
        # new_ext = ''
        # for ext in exc_list:
        #     new_ext = new_ext + ext + ', '
        # self.options["fa_excellon"] = new_ext
        self.inform.emit('[success] %s' % _("Extensions registered."))  # noqa

    def register_gerber_extension(self, root_path):
        new_reg_path = 'Software\\Classes\\'

        grb_list = self.ui.util_pref_form.fa_gerber_group.grb_list_text.get_value().replace(' ', '').split(',')
        grb_list = [x for x in grb_list if x != '']

        # register all keys in the Preferences window
        for ext in grb_list:
            new_k = new_reg_path + '.%s' % ext
            self.set_reg('', root_pth=root_path, new_reg_path_par=new_k, value='FlatCAM')

        # and unregister those that are no longer in the Preferences windows but are in the file
        for ext in self.options["fa_gerber"].replace(' ', '').split(','):
            if ext not in grb_list:
                self.delete_reg(root_pth=root_path, reg_path=new_reg_path, key_to_del='.%s' % ext)

        self.inform.emit('[success] %s' % _("Extensions registered."))  # noqa

    def register_gcode_extension(self, root_path):
        new_reg_path = 'Software\\Classes\\'

        gco_list = self.ui.util_pref_form.fa_gcode_group.gco_list_text.get_value().replace(' ', '').split(',')
        gco_list = [x for x in gco_list if x != '']

        # register all keys in the Preferences window
        for ext in gco_list:
            new_k = new_reg_path + '.%s' % ext
            self.set_reg('', root_pth=root_path, new_reg_path_par=new_k, value='FlatCAM')

        # and unregister those that are no longer in the Preferences windows but are in the file
        for ext in self.options["fa_gcode"].replace(' ', '').split(','):
            if ext not in gco_list:
                self.delete_reg(root_pth=root_path, reg_path=new_reg_path, key_to_del='.%s' % ext)

        self.inform.emit('[success] %s' % _("Extensions registered."))  # noqa

    def add_extension(self, ext_type):
        """
        Add a file extension to the list for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """

        if ext_type == 'excellon':
            self.add_excellon_extension()
        if ext_type == 'gcode':
            self.add_gcode_extension()
        if ext_type == 'gerber':
            self.add_gerber_extension()
        if ext_type == 'keyword':
            self.add_keyword_in_preferences_gui()

    def add_excellon_extension(self):
        new_ext = self.ui.util_pref_form.fa_excellon_group.ext_entry.get_value()
        if new_ext == '':
            return

        old_val = self.ui.util_pref_form.fa_excellon_group.exc_list_text.get_value().replace(' ', '').split(',')
        if new_ext in old_val:
            return
        old_val.append(new_ext)
        old_val.sort()
        self.ui.util_pref_form.fa_excellon_group.exc_list_text.set_value(', '.join(old_val))

    def add_gerber_extension(self):
        new_ext = self.ui.util_pref_form.fa_gerber_group.ext_entry.get_value()
        if new_ext == '':
            return

        old_val = self.ui.util_pref_form.fa_gerber_group.grb_list_text.get_value().replace(' ', '').split(',')
        if new_ext in old_val:
            return
        old_val.append(new_ext)
        old_val.sort()
        self.ui.util_pref_form.fa_gerber_group.grb_list_text.set_value(', '.join(old_val))

    def add_gcode_extension(self):
        new_ext = self.ui.util_pref_form.fa_gcode_group.ext_entry.get_value()
        if new_ext == '':
            return

        old_val = self.ui.util_pref_form.fa_gcode_group.gco_list_text.get_value().replace(' ', '').split(',')
        if new_ext in old_val:
            return
        old_val.append(new_ext)
        old_val.sort()
        self.ui.util_pref_form.fa_gcode_group.gco_list_text.set_value(', '.join(old_val))

    def add_keyword_in_preferences_gui(self, kw=None):
        new_kw = self.ui.util_pref_form.kw_group.kw_entry.get_value() if kw is None else kw
        if new_kw == '':
            return

        old_val = self.ui.util_pref_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
        if new_kw in old_val:
            return
        old_val.append(new_kw)
        old_val.sort()
        self.ui.util_pref_form.kw_group.kw_list_text.set_value(', '.join(old_val))

        # update the self.myKeywords so the model is updated
        autocomplete_kw_list = self.ui.util_pref_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
        self.myKeywords = self.tcl_commands_list + autocomplete_kw_list + self.tcl_keywords
        self.register_keywords(self.myKeywords)

    def del_extension(self, ext_type):
        """
        Remove a file extension from the list for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """
        if ext_type == 'excellon':
            self.delete_excellon_extension()
        if ext_type == 'gcode':
            self.delete_gcode_extension()
        if ext_type == 'gerber':
            self.delete_gerber_extension()
        if ext_type == 'keyword':
            self.delete_keyword_in_preferences_gui()

    def delete_excellon_extension(self):
        new_ext = self.ui.util_pref_form.fa_excellon_group.ext_entry.get_value()
        if new_ext == '':
            return

        old_val = self.ui.util_pref_form.fa_excellon_group.exc_list_text.get_value().replace(' ', '').split(',')
        if new_ext not in old_val:
            return
        old_val.remove(new_ext)
        old_val.sort()
        self.ui.util_pref_form.fa_excellon_group.exc_list_text.set_value(', '.join(old_val))

    def delete_gerber_extension(self):
        new_ext = self.ui.util_pref_form.fa_gerber_group.ext_entry.get_value()
        if new_ext == '':
            return

        old_val = self.ui.util_pref_form.fa_gerber_group.grb_list_text.get_value().replace(' ', '').split(',')
        if new_ext not in old_val:
            return
        old_val.remove(new_ext)
        old_val.sort()
        self.ui.util_pref_form.fa_gerber_group.grb_list_text.set_value(', '.join(old_val))

    def delete_gcode_extension(self):
        new_ext = self.ui.util_pref_form.fa_gcode_group.ext_entry.get_value()
        if new_ext == '':
            return

        old_val = self.ui.util_pref_form.fa_gcode_group.gco_list_text.get_value().replace(' ', '').split(',')
        if new_ext not in old_val:
            return
        old_val.remove(new_ext)
        old_val.sort()
        self.ui.util_pref_form.fa_gcode_group.gco_list_text.set_value(', '.join(old_val))

    def delete_keyword_in_preferences_gui(self, kw=None):
        new_kw = kw if kw is not None else self.ui.util_pref_form.kw_group.kw_entry.get_value()
        if new_kw == '':
            return

        old_val = self.ui.util_pref_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
        if new_kw not in old_val:
            return
        old_val.remove(new_kw)
        old_val.sort()
        self.ui.util_pref_form.kw_group.kw_list_text.set_value(', '.join(old_val))

        # update the self.myKeywords so the model is updated
        autocomplete_kw_list = self.ui.util_pref_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
        self.myKeywords = self.tcl_commands_list + autocomplete_kw_list + self.tcl_keywords
        self.register_keywords(self.myKeywords)

    def restore_extensions(self, ext_type):
        """
        Restore all file extensions associations with FlatCAM, for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """

        if ext_type == 'excellon':
            # don't add 'txt' to the associations (too many files are .txt and not Excellon) but keep it in the list
            # for the ability to open Excellon files with .txt extension
            new_exc_list = deepcopy(self.exc_list)

            try:
                new_exc_list.remove('txt')
            except ValueError:
                pass
            self.ui.util_pref_form.fa_excellon_group.exc_list_text.set_value(', '.join(new_exc_list))
        if ext_type == 'gcode':
            self.ui.util_pref_form.fa_gcode_group.gco_list_text.set_value(', '.join(self.gcode_list))
        if ext_type == 'gerber':
            self.ui.util_pref_form.fa_gerber_group.grb_list_text.set_value(', '.join(self.grb_list))
        if ext_type == 'keyword':
            self.ui.util_pref_form.kw_group.kw_list_text.set_value(', '.join(self.default_keywords))

            # update the self.myKeywords so the model is updated
            self.myKeywords = self.tcl_commands_list + self.default_keywords + self.tcl_keywords
            self.shell.command_line().set_model_data(self.myKeywords)

    def delete_all_extensions(self, ext_type):
        """
        Delete all file extensions associations with FlatCAM, for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """

        if ext_type == 'excellon':
            self.ui.util_pref_form.fa_excellon_group.exc_list_text.set_value('')
        if ext_type == 'gcode':
            self.ui.util_pref_form.fa_gcode_group.gco_list_text.set_value('')
        if ext_type == 'gerber':
            self.ui.util_pref_form.fa_gerber_group.grb_list_text.set_value('')
        if ext_type == 'keyword':
            self.ui.util_pref_form.kw_group.kw_list_text.set_value('')

            # update the self.myKeywords so the model is updated
            self.myKeywords = self.tcl_commands_list + self.tcl_keywords
            self.register_keywords(self.myKeywords)
