FlatCAM BETA (c) 2019 - by Marius Stanciu
Based on FlatCAM: 
2D Computer-Aided PCB Manufacturing by (c) 2014-2016 Juan Pablo Caram
=================================================

CHANGELOG for FlatCAM beta

=================================================

7.11.2020

- fixed a small issue in Excellon Editor that reset the delta coordinates on right mouse button click too, which was incorrect. Only left mouse button click should reset the delta coordinates.
- In Gerber Editor upgraded the UI
- in Gerber Editor made sure that trying to add a Circular Pad array with null radius will fail
- in Gerber Editor when the radius is zero the utility geometry is deleted
- in Excellon Editor made sure that trying to add a Circular Drill/Slot array with null radius will fail
- in Excellon Editor when the radius is zero the utility geometry is deleted
- in Gerber Editor fixed an error in the Eraser tool trying to disconnect the Jump signal
- small UI change in the Isolation Tool for the Reference Object selection
- small UI changes in NCC Tool and in Paint Tool for the Reference Object selection
- language strings recompiled to make sure that the .MO files are well optimized
RELEASE 8.994

6.11.2020

- in Gerber Editor made the selection multithreaded in a bid to get more performance but until Shapely will start working on vectorized geometry this don't yield too much improvement
- in Gerber Editor, for selection now the intersection of the click point and the geometry is determined for chunks of the original geometry, each chunk gets done in a separate process
- updated the French translation (by Olivier Cornet)
- fixed the new InputDialog widget to set its passed values in the constructor
- in Gerber Editor fixed the Add circular array capability
- in Gerber Editor remade the utility geometry generation for Circular Pad Array to show the array updated in real time and also fixed the adding of array in negative quadrants
- in Excellon Editor remade the utility geometry generation for Circular Drill/Slot Array to show the array updated in real time and also fixed the adding of array in negative quadrants
- Turkish language strings updated (by Mehmet Kaya)
- both for Excellon and Gerber editor fixed the direction of slots/pads when adding a circular array
- in Gerber editor added the G key shortcut to toggle the grid snapping
- made some changes in the Region Tool from the Gerber Editor

5.11.2020

- fixed the annotation plotting in the CNCJob object
- created a new InputDialog widget that has the buttons and the context menu translated and replaced the old widget throughout the app
- updated the translation strings
- Turkish language strings updated
- set some policy rules back the way they were for the combo boxes in Geometry Object properties
- updated the Italian translation (by Massimiliano Golfetto)
- finished the Google-translation of the German language strings

4.11.2020

- updated all the translation files
- fixed issue with arrays of items could not be added in the Gerber/Excellon Editor when a translation is used
- fixed issue in the Excellon Editor where the Space key did not toggle the direction of the array of drills
- combed the application strings all over the app and trimmed them up until those starting with letter 'O'
- updated the translation strings
- fixed the UI layout in Excellon Editor and made sure that after changing a value in the Notebook side after the mouse is inside the canvas, the canvas takes the focus allowing the key shortcuts to work
- Turkish language strings updated (by Mehmet Kaya)
- in Gerber Editor added the shortcut key 'Space' to change the direction of the array of pads
- updated all the translation languages. Translated by Google the Spanish, Russian. Romanian translation updated.
- refactored the name of the classes from the Gerber Editor
- added more icons in the Gerber and Excellon Editors for the buttons

3.11.2020

- fixed an issue in Tool Isolation used with tools from the Tools Database: the set offset value was not used
- updated the Tools Database to include all the Geometry keys in the every tool from database
- made sure that the Operation Type values ('Iso', 'Rough' and 'Finish') are not translated as this may create issues all over the application
- fix an older issue that made that only the Custom choice created an effect when changing the Offset in the Geometry Object Tool Table
- trying to optimize Gerber Editor selection with the mouse
- optimized some of the strings
- fixed the project context save functionality to work in the new program configuration
- updated Turkish translation (by Mehmet Kaya)
- in NCC and Isolation Tools, the Validity Checking of the tools is now multithreaded when the Check Validity UI control is checked
- translation strings updated
- fixed an error in Gerber parser, when it encounter a pen-up followed by pen-down move while in a region
- trimmed the application strings
- updated the Italian translation (by Massimiliano Golfetto)
- fixed a series of issues in Gerber Editor tools when the user is trying to use the tools by preselecting a aperture without size (aperture macro)
- moved all the UI stuff out of the Gerber Editor class in its own class
- in the Excellon Editor, added shortcut keys Space and Ctrl+Space for toggling the direction of the Slots, respectively for the Array of Slots
- updated the translation strings to the latest changes in the app strings

2.11.2020

- fixed the Tcl Command AlignDrill
- fixed the Tcl Command AlignDrillGrid
- fixed the Tcl COmmand Panelize, Excellon panelization section
- Fixed an issue in Tool Calibration export_excellon method call
- PEP8 corrections all over the app
- made sure that the object selection will not work while in Editors or in the App Tools
- some minor changes to strings and icons
- in Corner Markers Tool - the new Gerber object will have also follow_geometry
- upgraded the Fiducials Tool to create new objects instead of updating in place the source objects
- upgraded the Copper Thieving Tool to create new objects instead of updating in place the source objects
- in Copper Thieving Tool added a new parameter to filter areas too small to be desired in the copper thieving; added it to Preferences too
- Copper Thieving Tool added a new parameter to select what extra geometry to include in the Pattern Plating Mask; added it to the Preferences
- made a wide change on the spinners GUI ranges: from 9999.9999 all values to 10000.0000
- fixed some late issues in Corner Markers Tool new feature (messages)
- upgraded Calculator Tool and added the new parameter is the Preferences
- updated translation strings
- fixed borderline bug in Gerber editor when the edited Gerber object last aperture is a aperture without size (Aperture Macro)
- improved the loading of a Gerber object in the Gerber Editor
- updated translation strings

1.11.2020

- updated the French Translation (by Olivier Cornet)
- fixed issue in Corner Markers Tool that crashed the app if only one corner was checked
- fixed issue in Isolation Tool where Area Isolation selection was not working 
- added to the translatable strings the category labels in the Project Tab and also updated the translations
- fixed a small issue (messages) in Corner Markers Tool
- in Corners Markers Tool added a new feature: possibility to use cross shape markers
- in Corner Marker Tool add new feature: ability to create an Excellon object with drill holes in the corner markes
- in Corner Marker Tool, will no longer update the current object with the marker geometry but create a new Gerber object
- in Join Excellon functionality made sure that the new Combo Exellon object will have copied the data from source objects and not just references, therefore will survive the delete of its parents
- updated Turkish translation (by Mehmet Kaya)
- updated all the languages except Turkish
- in the Tool PDF fixed the creation of Excellon objects to the current Excellon object data structure

31.10.2020

- adapted HPGL importer to work within the new app
- in Gerber Editor fixed an error when using the Distance Tool with "Snap to center" option active: if clicking not on a pad Distance Tool was not working
- updated the Turkish translation strings (by Mehmet Kaya)
- typo fixed in Copper Thieving Tool (due of recent changes)
- fixed issue #457; wrong reference when saving a project
- fixed issue in Excellon Editor that crashed the app if using the Resize Drill feature by clicking in menu/toolbar
- fixed issue in Excellon Editor when using the menu links to Move or Copy Drills/Slots
- updated the strings 
- updated the Turkish translation strings (by Mehmet Kaya)
- added a parent to some of the FCInputDialog widgets used in the app such that those pop-up windows will b displayed in the center of the app main window as opposed to the center of the screen
- finished the Google-translation of not translated strings in Russian language

30.10.2020

- fixed the Punch Gerber Tool bug that did not allowed the projects to be loaded or to create a new project. Fixed issue #456
- in Tool Subtract added an option to delete the source objects after a successful operation. Fixed issue #455
- when entering into an Editor now the Project tab is disabled and the Properties tab where the Editor is installed change the text to 'Editor' and the color is set in Red. After exiting the Tab text is reverted to previous state.
- fixed and issue where the Tab color that was changed in various states of the app was reverted back to a default color 'black'. Now it reverts to whatever color had before therefore being compatible with an usage of black theme
- fixed bug that did not allow joining of any object to a Geometry object
- working on solving the lost triggered signals for the Editor Toolbars buttons after changing the layout
- fixed issue #454; trigger signals for Editor Toolbars lost after changing the layout
- updated the translation strings
- more bugs that were introduced by recent changes done to solve other bugs and so on: fixed issues with the Editors and Delete shortcut
- fixed an error in the Gerber Editor

29.10.2020

- added icons in most application Tools
- updated Punch Gerber Tool such that the aperture table is updated upon clicking of the checboxes in Processed Pads Type
- updated Punch Gerber Tool: the Excellon method now takes into consideration the pads choice 
- minor change for the FCComboBox UI element by setting its size policy as ignored so it will not expand the notebook when the name of one of its items is very long
- added a protection on opening the tools database UI if the tools DB file is not loaded
- fixed NCC Tool not working with the new changes; the check for not having complete isolation is just a Warning
- fixed the sizePolicy for the FCComboBox widgets in the Preferences that holds the preprocessors
- fixed issue with how the preamble / postamble GCode were inserted into the final GCode
- fixed a small issue in GCode Editor where the signals for the buttons were attached again at each launch of the GCode Editor
- fixed issues in the Tools Database due of recent changes in how the data structure is created
- made sure that the right tools go only to the intended use, in Tools Database otherwise an error status message is created and Tools DB is closed on adding a wrong tool
- fixed the usage for Tools Database in Unix-like OS's; fixed issue #453
- done some modest refactoring
- fixed the Search and Add feature in Geometry Object UI
- fixed issue with preamble not being inserted when used alone
- modified the way that the start GCode is stored such that now the bug in GCode Editor that did not allowed selection of the first tool is now solved
- in Punch Gerber Tool added a column in the apertures table that allow marking of the selected aperture so the user can see what apertures are selected
- improvements in the Punch Gerber Tool aperture markings
- improved the Geometry Object functionality in regards of Tools DB, deleting a tool and adding a tool
- when using the 'T' shortcut key with Properties Tab in focus and populated with the properties of a Geometry Object made the popped up spinner to have the value autoselected
- optimized the UI in Extract Drills Tool
- added some more icons for buttons

28.10.2020

- a series of PEP8 corrections in the FlatCAMGeometry.py
- in Geometry UI finished a very basic way for the Polish feature (this will be upgraded in the future, for now is very rough)
- added some new GUI elements by subclassing some widgets for the dialog pop-ups
- in NCC Tool and Isolation Tool, pressing the shortcut key 'T' will bring the add new tool pop up in which now it is included the button to get the optimal diameter
- in Geometry UI and for Solderpaste Tool replaced the pop up window that is launched when using shortcut key with one that has the context menu translated
- some UI cleanup in the Geometry UI
- updated the translation strings except Russian which could be in the works
- fixed an error that did not allowed for the older preferences to be deleted when installing a different version of the software
- in Legacy Mode fixed a small issue: the status bar icon for the Grid axis was not colored on app start
- added a new string to the translatable strings
- fixed an error that sometime showed in Legacy Mode when moving the mouse outside canvas
- reactivated the shortcut key 'S' in TCL Shell, to close the shell dock when it was open (of course the focus has to be not on the command line)
- brought up-to-date and fixed the Tcl Command Drillcncjob and Cncjob
- fixed Tcl command Isolate to not print messages on message bar in case it is run headless
- fixed Tcl command Copper Clear (NCC)
- fixed Tcl command Paint
- temporary fix for comboboxes not finding the the value in the items when setting themselves with a value by defaulting to the first item in the list
- fix in Tool Subtract where there was a typo
- upgraded the punch Gerber Tool
- updated the Turkish translation strings (by Mehmet Kaya)
- fixed an issue in Isolation Tool when running the app in Basic mode;
- fixed Paint, Isolation and NCC Tools such the translated comboboxes values are now stored as indexes instead of translated words as before
- in Geometry Object made sure that the widgets in the Tool Table gets populated regardless of encountering non-recognizable translated values
- in Paint Tool found a small bug and fixed it
- fixed the Tool Subtractor algorithms

27.10.2020

- created custom classes derived from TextEdit and from LineEdit where I overloaded the context menu and I made all the other classes that were inheriting from them to inherit from those new classes
- minor fix in ToolsDB2UI
- updated the Turkish translation strings (by Mehmet Kaya)
- fixed a bug in conversion of any to Gerber in the section of Excellon conversion
- some PEP8 fixes
- fixed a bug due of recent chagnes in FileMenuHandlers class
- fixed an issue in Tools Database (ToolsDB2 class) that did not made the Tab name in Red color when adding/deleting a tool by using the context menu
- optimized the Tools Database
- small string change

26.10.2020

- added a new menu entry and functionality in the View category: enable all non-selected (shortcut key ALT+3)
- fixed shortcut keys for a number of functionality and in some cases added some new
- fixed the enable/disable all plots functionality
- fixed issue with the app window restored in a shifted position after doing Fullscreen
- fixed issue with coords, delta_coords and status toolbars being disabled when entering fullscreen mode and remaining disabled after restore to normal mode
- changed some of the strings (added a few in the How To section)
- more strings updated
- modified the shortcut strings and the way the shortcuts were listed in the Shortcut keys list such that it will allow a future Shortcuts Manager
- updated all the language strings according to the modifications done above
- fixed a small issue with using the shortcut key for toggling the display of Properties tab
- fixed issue with not updating the model view on the model used in the Project tab when using the shortcut keys 1, 2, 3 which made the color of the tree element not reflect the change in status
- minor string fix; removed the 'Close' menu entry on the context menu for the TCL Shell
- overloaded the context menu in the Tcl Shell and added key shortcuts; the menu entries are now translatable
- overloaded the context menu in several classes from GUI Elements such that the menus are now translated
- fixed a formatting issue in the MainGUI.py file
- updated the translations for the new strings that were added
- another GUI element for which I've overloaded the context menu to make it translatable: _ExpandableTextEdit
- overloaded the context menu for FCSpinner and for FCDoubleSpinner
- added new strings and therefore updated the translation strings
- fixed some minor issues when doing a project save

25.10.2020

- updated the Italian translation (by Massimiliano Golfetto)
- finished the update of the Spanish translation (Google translate)

24.10.2020

- added a new GUI element, an InputDialog made out of FCSliderWithSpinner named FCInputDialogSlider
- replaced the InputDialog in the Opacity pop menu for the objects in the Project Tab with a FCInputDialogSlider
- minor changes
- UI changes in the AppTextEditor and in CNCJob properties tab and in GCoe Editor
- some changes in strings; updated all the translation strings to the latest changes
- finished the Romanian translation
- created two new preprocessors (from 'default' and from 'grbl_11') that will have no toolchange commands regardless of the settings in the software
- updated the Turkish translation (by Mehmet Kaya)
- the methods of the APP class that were the handlers for the File menu are now moved to their own class
- fixed some of the Tcl Commands that depended on the methods refactored above
- reverted the preprocessors with no toolchange commands to the original but removed the M6 toolchange command
- fixed newly introduced issue when doing File -> Print(PDF)
- fixed newly introduced issues with SysTray and Splash
- added ability for the app to detect the current DPI used on the screen; applied this information in the Film Tool when exporting PNG files
- found that Pillow v >= 7.2 breaks Reportlab 3.5.53 (latest version) and creates an error in Film Tool when exporting PNG files. Pillow 7.2 still works.

23.10.2020

- updated Copper Thieving Tool to work with the updated program
- updated Rules Check Tool - Hole Size rule to work with the new data structure for the Excellon objects
- updated Rules Check Tool - added an activity message
- updated some strings, updated the translation strings
- commented the ToolsDB class since it is not used currently
- some minor changes in the AppTextEditor.py file
- removed Hungarian language since it's looking like is no longer being translated
- added a default properties tab which will hold a set of information's about the application
- minor changes in the Properties Tool
- Excellon UI: fixed a small issue with toggling all rows in Tools Table not toggling off and also the milling section in Utilities was not updated
- some refactoring in the keys of the defaults dictionary
- fixed an ambiguity in the Tools Database GUI elements

22.10.2020

- added  a message to show if voronoi_diagram method can be used (require Shapely >= 1.8)
- modified behind the scene the UI for Tool Subtract
- modified some strings and updated the translation strings
- in NCC Tool added a check for the validity of the used tools; its only informative
- in NCC Tool done some refactoring
- in NCC Tool fixed a bug when using Rest Machining; optimizations
- in NCC Tool fixed a UI issue
- updated the Turkish translation (by Mehmet Kaya)
- small change in the CNCJob UI by replacing the AL checkbox with a checkable QButton
- disabled the Autolevelling feature in CNCJob due of being not finished and missing also a not-yet-released package: Shapely v 1.8
- added some new strings for translation and updated the translation strings
- in ToolsDB2UI class made the vertical layouts have a preferred minimum dimension as opposed to the previous fixed one
- in Geometry Object made sure that the Tools Table second column is set to Resize to contents
- fixed a bug in Tool PunchGerber when using an Excellon to punch holes in the Gerber apertures

21.10.2020

- in Geometry Object fixed the issue with not using the End X-Y value and also made some other updates here
- in NCC and Paint Tool fixed some issues with missing keys in the tool data dictionary
- In Excellon Object UI fixed the enable/disable for the Milling section according to the Tools Table row that is selected
- In Excellon Object UI fixed the milling geometry generation
- updated the translations strings to the changes in the source code
- some strings changed
- made the Properties checkbox in the Object UI into a checkable button and added to it an icon
- fixed crash on using shortcut for creating a new Document Object
- fixed Cutout Tool to work with the endxy parameter
- added the exclusion parameters for Drilling Tool to the Preferences area
- cascaded_union() method will be deprecated in Shapely 1.8 in favor of unary_union; replaced the usage of cascaded_union with unary_union in all the app
- added some strings to the translatable strings and updated the translation strings
- merged in the Autolevelling branch and made some PEP8 changes to the bilinearInterpolator.py file
- added a button in Gerber UI that will hide/show the bounding box generation and the non-copper region section
- compacted the UI for the 2Sided Tool
- added a button in Excellon UI that will hide/show the milling section
- optimized a bit the UI for Gerber/Excellon/Geometry objects
- optimized FlatCAMObj.add_properties_items() method
- updated the Turkish translation (by Mehmet Kaya)
- added ability to run a callback function with callback_parameters after a new FlatCAM object is created

20.10.2020

- finished to add the Properties data to the Object Properties (former Selected Tab)

19.10.2020

- added a check (and added to Preferences too) for the verification of tools validity in the Isolation Tool
- fixed QrCode Tool
- updated the Turkish translation (by Mehmet Kaya)

18.10.2020

- fixed issue with calling the inform signal in the FlatCAMDefaults.load method
- fixed macro parsing in Gerber files generated by KiCAD 4.99 (KiCAD 5.0)

17.10.2020

- updated Turkish translation (by Mehmet Kaya)

8.10.2020

- small change in the NCC Tool UI
- some strings are changed and therefore the translation strings source are updated
- Isolation Tool - added a check for having a complete isolation

7.10.2020

- working on adding DPI setting for PNG export in Film Tool - update
- finished updating DPI setting feature for PNG export in Film Tool

5.10.2020

- working on adding DPI setting for PNG export in the Film Tool
- finished working in adding DPI settings for PNG export in Film Tool although there are some limitations due of Reportlab
- small change in TclCommandExportSVG

26.09.2020

- the Selected Tab is now Properties Tab for FlatCAM objects
- modified the Properties Tab for various FlatCAM objects preparing the move of Properties Tool data into the Properties Tab
- if the Properties tab is in focus (selected) when a new object is created then it is automatically selected therefore it's properties will be populated

25.09.2020

- minor GUI change in Isolation Tool

24.09.2020

- fixed a bug where end_xy parameter in Drilling Tool was not used
- fixed an issue in Delete All method in the app_Main.py

23.09.2020

- added support for virtual units in SVG parser; warning: it may require the support for units which is not implemented yet
- fixed canvas selection such that when selecting shape fails to be displayed with rounded corners a square selection shape is used
- fixed canvas selection for the case when the selected object is a single line or a line made from multiple segments

22.09.2020

- fixed an error in importing SVG that has a single line
- updated the POT file and the PO/MO files for Turkish language
- working to add virtual units to SVG parser

20.09.2020

- in CNCJob UI Autolevelling: on manual add of probe points, only voronoi diagram is calculated
- in SVG parser: made sure that the minimum number of steps to approximate an arc/circle/bezier is 10

19.09.2020

- removed some brackets in the GRBL laser preprocessor due of GRBL firmware interpreting the first closing bracket as the comment end

3.09.2020

- in CNCJob UI Autolevelling: changed the UI a bit
- added a bilinear interpolation calculation class from: https://github.com/pmav99/interpolation
- in CNCJob UI Autolevelling: made sure that the grid can't have less than 2 rows and 2 columns when using the bilinear interpolation or 1 row and 1 column when using the Voronoi polygons
- in CNCJob UI Autolevelling: prepared the app for bilinear interpolation
- in CNCJob UI Autolevelling: fixes in the UI

2.09.2020

- in CNCJob UI Autolevelling: solved some small errors: when manual adding probe points dragging the mouse with left button pressed created selection rectangles; detection of click inside the solid geometry was failing
- in CNCJob UI Autolevelling: in manual adding of probe points make sure you always add a first probe point in origin
- in CNCJob UI Autolevelling: first added point when manual adding of probe points is auto added in origin before adding first point
- in CNCJob UI Autolevelling: temp geo for adding points in manual mode is now painted in solid black color and with a smaller diameter
- in CNCJob UI Autolevelling - GRBL controller - added a way to save a GRBL height map
- in CNCJob UI Autolevelling: added the UI for choosing the method used for the interpolation used in autolevelling

31.08.2020

- updated the Italian translation files by Massimiliano Golfetto
- in CNCJob UI Autolevelling: made sure that plotting a Voronoi polygon is done only for non-None polygons
- in CNCJob UI Autolevelling: in manual mode, Points can be chosen only when clicking inside the object to be probed
- in CNCJob UI Autolevelling: made sure that plotting a Voronoi polygon is done only for non-None polygons
- in CNCJob UI Autolevelling: remade the probing points generation so they could allow bilinear interpolation

29.08.2020

- 2Sided Tool - fixed newly introduced issues in the Alignment section
- 2Sided Tool - modified the UI such that some of the fields will allow only numbers and some special characters ([,],(,),/,*,,,+,-,%)
- Cutout Tool - working on adding mouse bites for the Freeform cutout
- updated the translation files to the current state of the app
- Cutout Tool - rectangular and freeform cutouts are done in a threaded way
- Cutout Tool - added the Mouse Bites feature for the Rectangular and Freeform cutouts and right now it fails in case of using a Geometry object and Freeform cutout (weird result)
- some changes in camlib due of warnings for future changes in Shapely 2.0
- Cutout Tool - fixed mouse bites feature in case of using a Geometry object and Freeform cutout
- Cutout Tool - can do cutouts on multigeo Geometry objects: it will automatically select the geometry of first tool
- Geometry Editor - fixed exception raised when trying to move and there is no shape to move
- Cutout Tool - finished adding the Mouse Bites feature by adding mouse bites for manual cutouts

28.08.2020

- Paint Tool - upgraded the UI and added the functionality that now adding a new tool is done by first searching the Tools DB for a suitable tool and if fails then it adds an default tool
- Paint Tool - on start will attempt to search in the Tools DB for the default tools and if found will load them from the DB
- NCC Tool - upgraded the UI and added the functionality that now adding a new tool is done by first searching the Tools DB for a suitable tool and if fails then it adds an default tool
- NCC Tool - on start will attempt to search in the Tools DB for the default tools and if found will load them from the DB
- fixes in NCC, Paint and Isolation Tool due of recent changes
- modified the Tools Database and Preferences with the new parameters from CutOut Tool
- changes in Tool Cutout: now on Cutout Tool start the app will look into Tools Database and search for a tool with same diameter (or within the set tolerance) as the one from Preferences and load it if found or load a default tool if not
- Tool Cutout - this Tool can now load tools from Tools Database through buttons in the Cutout Tool

27.08.2020

- fixed the Tcl commands AddCircle, AddPolygon, AddPolyline and AddRectangle to have stored bounds therefore making them movable/selectable on canvas
- in Tool Cutout, when using the Thin Gaps feature, the resulting geometry loose the extra color by toggling tool plot in Geometry UI Tools Table- fixed
- in Tool Cutout fixed manual adding of gaps with thin gaps and plotting
- in Tool Cutout, when using fix gaps made sure that this feature is not activated if the value is zero
- in Tool Cutout: modified the UI in preparation for adding the Mouse Bites feature
- Turkish translation strings were updated by the translator, Mehmet Kaya
- Film Tool - moved the Tool UI in its own class
- in Tools: Image, InvertGerber, Optimal, PcbWizard - moved the Tool UI in its own class
- Tool Isolation - made sure that the app can load from Tools Database only tools marked for Isolation tool
- Tool Isolation - on Tool start it will attempt to load the Preferences set tools by diameter from Tools Database. If it can't find one there it will add a default tool.
- in Tools: Transform, SUb, RulesCheck, DistanceMin, Distance - moved the Tool UI in its own class
- some small fixes
- fixed a borderline issue in CNCJob UI Autolevelling - Voronoi polygons calculations

26.08.2020

- fix for issue nr 2 in case of Drilling Tool. Need to check Isolation Tool, Paint Tool, NCC Tool
- Drilling Tool - UI changes
- Geometry object - now plotting color for an individual tool can be specified
- in CutOut Tool - when using  'thin gaps' option then the cut parts are colored differently than the rest of the geometry in the Geometry object
- solved some deprecation warnings (Shapely module)
- Drilling Tool - when replacing Tools if more than one tool for one diameter is found, the application exit the process and display an error in status bar; some minor fixes
- Isolation Tool - remade the UI
- Isolation Tool - modified the add new tool method to search first in Tools Database  for a suitable tool
- Isolation Tool - added ability to find the tool diameter that will guarantee total isolation of the currently selected Gerber object
- NCC Tool - UI change: if the operation is Isolation then some of the tool parameters are disabled
- fixed issue when plotting a CNCJob object with multiple tools and annotations on by plotting annotations after all the tools geometries are plotted
- fixed crash in Properties Tool, when applied on a CNCJob object made out of an Excellon object (fixed issue #444)
- in Properties Tool, for CNCJob objects made out of Excellon objects, added the information's from Tool Data
- in Properties Tool made sure that the set color for the Tree parents depends on the fact if the gray icons set are used (dark theme) or not
- Properties Tool - properties for a Gerber objects has the Tool Data now at the end of the information's
- in Gerber UI done some optimizations

25.08.2020

- in CNCJob UI Autolevelling - made the Voronoi calculations work even in the scenarios that previously did not work; it need a newer version of Shapely, currently I installed the GIT version
- in CNCJob UI Autolevelling - Voronoi polygons are now plotted
- in CNCJob UI Autolevelling - adding manual probe points now show some geometry (circles) for the added points until the adding is finished
- 2Sided Tool - finished the feature that allows picking an Excellon drill hole center as a Point mirror reference
- Tool Align Objects - moved the Tool Ui into its own class
- for Tools: Calculators, Calibration, Copper Thieving, Corners, Fiducials - moved the Tool UI in its own class

24.08.2020

- fixed issues in units conversion
- in CNCJob UI Autolevelling - changed how the probing code is generated and when
- changed some strings in CNCJob UI Autolevelling
- made sure that when doing units conversion keep only the decimals specified in the application decimals setting (should differentiate between values and display?)
- in CNCJob UI Autolevelling - some UI changes
- in CNCJob UI Autolevelling - GRBL controller - added the probing method
- in CNCJob UI Autolevelling - GRBL controller - fixed the send_grbl_command() method

23.08.2020

- in CNCJob UI Autolevelling - autolevelling is made to be not available for cnc code generated with Roland or HPGL preprocessors
- in CNCJob UI Autolevelling - added a save dialog for the probing GCode
- added a new GUI element, a DoubleSlider
- in CNCJob UI Autolevelling - GRBL controller - Control: trying to add DoubleSlider + DoubleSpinner combo controls
- in GUI element FCDoubleSpinner fixed an range issue

21.08.2020

- in CNCJob UI Autolevelling - GRBL controller - Control: added a Origin button; changed the UI to have rounded rectangles 
- in CNCJob UI Autolevelling - GRBL controller - Control: added feedrate and step size controls and added them in Preferences
- in CNCJob UI Autolevelling - GRBL controller - added handlers for the Zeroing and for Homing and for Pause/Resume; some UI optimizations

19.08.2020

- in CNCJob UI Autolevelling - sending GCode/GRBL commands is now threaded
- in CNCJob UI Autolevelling - Grbl Connect tab colors will change with the connection status
- in CNCJob UI Autolevelling - GRBL Control and Sender tabs are disabled when the serial port is disconnected
- in CNCJob UI Autolevelling - GRBL Sender - now only a single command can be sent 
- in CNCJob UI Autolevelling - GRBL controller - changed the UI
- in CNCJob UI Autolevelling - added some VOronoi poly calculations

18.08.2020

- in Doublesided Tool added some UI for Excellon hole snapping
- in Doublesided Tool cleaned up the UI
- in CNCJob UI Autolevelling - in COntrol section added  buttons for Jog an individual axes zeroing
- in CNCJob UI Autolevelling - added handlers for: jogging, reset, sending commands
- in CNCJob UI Autolevelling - added handlers for GRBL report and for getting GRBL parameters

17.08.2020

- in CNCJob UI Autolevelling - GRBL GUI controls are now organized in a tab widget

16.08.2020

- in CNCJob UI Autolevelling - updated the UI with controls for probing GCode parameters and added signals and slots for the UI
- in CNCJob UI Autolevelling - added a mini gcode sender for the GRBL to be able to send the probing GCode and get the height map (I may make a small and light app for that so it does not need to have FlatCAM on the GCode sender PC)
- in CNCJob UI Autolevelling finished the probing GCode generation for MACH/LinuxCNC controllers; this GCode can also be viewed
- in CNCJob UI Autolevelling - Probing GCode has now a header
- in CNCJob UI Autolevelling - Added entries in Preferences
- in CNCJob UI Autolevelling - finished the Import Height Map method
- in CNCJob UI Autolevelling - made autolevelling checkbox state persistent between app restarts

14.08.2020

- in CNCJob UI worked on the UI for the Autolevelling
- in CNCJob UI finished working on adding test points in Grid mode
- in CNCJob UI finished working on adding test points in Manual mode

13.08.2020

- in CNCJob UI added GUI for an eventual Autolevelling feature 
- in CNCJob UI updated the GUI for Autolevelling
- Cutout Tool - finished handler for gaps thickness control for the manual gaps
- CNCJob object - working in generating Voronoi diagram for autolevelling

11.08.2020

- CutOut Tool - finished handler for gaps thickness control for the free form cutout

9.08.2020

- small fix so the cx_freeze 6.2 module will work in building a frozen version of FlatCAM

7.08.2020

- all Geometry objects resulted from Isolation Tool are now of type multi-geo
- fixed minor glitch in the Isolation Tool UI
- added an extra check when doing selection on canvas
- fixed an UI problem in Gerber Editor

5.08.2020

- Tool Cutout - more work in gaps thickness control feature
- Tool Cutout - added some icons to buttons
- Tool Cutout - done handling the gaps thickness control for the rectangular cutout; TODO: check all app for the usage of geometry_spindledir and geometry_optimization_type defaults in tools and in options
- Tool Cutout - some work in gaps thickness control for the free form cutout

4.08.2020

- removed the Toolchange Macro feature (in the future it will be replaced by full preprocessor customization)
- modified GUI in Preferences
- Tool Cutout - working in adding gaps thickness control feature; added the UI in the Tool

3.08.2020

- GCode Editor - GCode tool selection when clicking on tool in Tools table is working. The only issue is that the first tool gcode includes the start gcode which confuse the algorithm
- GCode Editor - can not delete objects while in the Editor; can not close the Code Editor Tab except on Editor exit; activated the shortcut keys (for now only CTRL+S is working)
- added a way to remember the old state of Tools toolbar before and after entering an Editor
- GCode Editor - modified the UI

2.08.2020

- GCode Editor - closing the Editor will close also the Code Editor Tab
- cleanup of the CNCJob UI; added a checkbox to signal if any append/prepend gcode was set in Preferences (unchecking it will override and disable the usage of the append/prepend GCode)
- the start Gcode is now stored in the CNCJob object attribute gc_start
- GCode Editor - finished adding the ability to select a row in the Tools table and select the related GCode
- GCode Editor - working on GCode tool selection - not OK

1.08.2020

- Tools Database: added a Cutout Tool Parameters section
- GCode Editor - work in the UI

31.07.2020

- minor work in GCode Editor

29.07.2020

- fixed an exception that was raised in Geometry object when using an Offset

27.07.2020

- Gerber parser - a single move with pen up D2 followed by a pen down D1 at the same location is now treated as a Flash; fixed issue #441

25.07.2020

- Tools Tab is hidden when entering into a Editor and showed on exit (this needs to be remade such that the toolbars state should be restored to whatever it was before entering in the Editor)

22.07.2020

- working on a proper GCode Editor
- wip in the GCode Editor
- added a Laser preprocessor named 'Z_laser' which will change the Z to the Travel Z on each ToolChange event allowing therefore control of the dot size
- by default now a new blank Geometry object created by FlatCAM is of type multigeo
- made sure that optimizations of lines when importing SVG or DXF as lines will not encounter polygons but only LinesStrings or LinearRings, otherwise having crashes
- fixed the import SVG and import DXF, when importing as Geometry to be imported as multigeo tool
- fixed the import SVG and import DXF, the source files will be saved as loaded into the source_file attribute of the resulting object (be it Geometry or Gerber)
- in import SVG and import DXF methods made sure that any polygons that are imported as polygons will survive and only the lines are optimized (changed the behavior of the above made modification)

21.07.2020

- updated the FCRadio class with a method that allow disabling certain options
- the Path optimization options for Excellon and Geometry objects are now available depending on the OS platform used (32bit vs 64bit)
- fixed MultiColor checkbox in Excellon Object to work in Legacy Mode (2D)
- modified the visibility change in Excellon UI to no longer do plot() when doing visibility toggle for one of the tools but only a visibility change in the shapes properties
- Excellon UI in Legacy Mode (2D): fixed the Solid checkbox functionality
- Excellon UI: fixed plot checkbox performing an extra plot function which was not required
- Excellon UI: added a column which will color each row/tool of that column in the color used when checking Multicolor checkbox
- Excellon UI: made sure that when the Multicolor checkbox is unchecked, the color is updated in the Color column of the tools table
- made sure that the Preferences files are deleted on new version install, while the application is in Beta status
- fixed issues with detecting older Preferences files
- fixed some issues in Excellon Editor due of recent changes
- moved the Gerber colors fill in the AppObject.on_object_created() slot and fixed some minor issues here
- made sure there are no issues when plotting the Excellon object in one thread and trying to build the UI in another by using a signal

20.07.2020

- fixed a bug in the FlatCAMGerber.on_mark_cb_click_table() method when moving a Gerber object
- added a way to remember the colors set for the Gerber objects; it will remember the order that they were loaded and set a color previously given
- added a control in Preferences -> Gerber Tab for Gerber colors storage usage
- made sure that the defaults on first install will set the number of workers to half the number of CPU's on the system but no less than 2

18.07.2020

- added some icons in the Code Editor
- replaced some icons in the app
- in Code Editor, when changing text, the Save Code button will change color (text and icon) to red and after save it will revert the color to the default one
- in Code Editor some methods rework

16.07.2020

- added a new method for GCode generation for Geometry objects
- added multiple algorithms for path optimization when generating GCode from an Geometry object beside the original Rtree algorithm: TSA, OR-Tools Basic, OR-Tools metaheuristics
- added controls for Geometry object path optimization in Preferences

15.07.2020

- added icons to some of the push buttons
- Tool Drilling - automatically switch to the Selected Tab after job finished
- added Editor Push buttons in Geometry and CNCJob UI's
- Tool Drilling - brushing through code and solved the report on estimation of execution time
- Tool Drilling - more optimizations regarding of using Toolchange as opposed to not using it
- modified the preprocessors to work with the new properties for Excellon objects
- added to preprocessors information regarding the X,Y position at the end of the job
- Tool Drilling made sure that on Toolchange event after toolchange event the tool feedrate is set
- added some icons to more push buttons inside the app
- a change of layout in Tools Database
- a new icon for Search in DB

14.07.2020

- Drilling Tool - now there is an Excellon preference that control the autoload of tools from the Tools Database
- Tools Database - remade the UI
- made sure that the serializable attributes are added correctly and only once (self.ser_attrs)
- Tools Database - some fixes in the UI (some of the widgets had duplicated names)
- Tools Database - made sure the on save the tools are saved only with the properties that relate to their targeted area of the app
- Tools Database - changes can be done only for one tool at a time
- Tool Database - more changes to the UI

13.07.2020

- fixed a bug in Tools Database: due of not disconnecting the signals it created a race that was concluded into a RuntimeError exception (an dict changed size during iteration)
- Drilling Tool - working in adding tools auto-load from Tools DB
- some updates to the Excellon Object options
- Drilling Tool - manual add from Tools DB is working
- Drilling Tool - now slots are converted to drills if the checkbox is ON for the tool investigated
- Drilling Tool - fixes due of changes in properties (preferences)
- fixed the Drillcncjob TCL command
- Multiple Tools fix - fixed issue with converting slots to drills selection being cleared when toggling all rows by clicking on the header
- Multiple Tools fix - fixes for when having multiple tools selected which created issues in tool tables for many tools

12.07.2020

- when creating a new FlatCAM object, the options will be updated with FlatCAM tools properties that relate to them
- updated the Tools DB class by separating the Tools DB UI into it's own class
- Tools DB - added the parameters for Drilling Tool

11.07.2020

- moved all Excellon Advanced Preferences to Drilling Tool Preferences
- updated Drilling Tool to use the new settings
- updated the Excellon Editor: the default_data dict is populated now on Editor entry
- Excellon Editor: added a new functionality: conversion of slots to drills
- Excellon UI: added a new feature that is grouped in Advanced Settings: a toggle tools table visibility checkbox 
- Drilling Tool - minor fixes
- Drilling Tool - changes in UI
- Isolation Tool - modified the UI; preparing to add new feature of polishing at the end of the milling job
- Tool Paint - fixed an issue when launching the tool and an object other than Geometry or Excellon is selected
- Geometry UI - moved the UI for polishing from Isolation Tool to Geometry UI (actually in the future Milling Tool) where it belongs
- Gerber UI - optimized the mark shapes to use only one ShapeCollection

10.07.2020

- Tool Drilling - moved some of the Excellon Preferences related to drilling operation to it's own group Drilling Tool Options
- optimized the CNCJob UI to look like other parts of the app 
- in Gerber and Excellon UI added buttons to start the Editor
- in all Editors Selected Tab added a button to Exit the Editor
- Tool Drilling - fixed incorrect annotations in CNCJob objects generated; one drawback is that now each tool (when Toolchange is ON) has it's own annotation order which lead to overlapping in the start point of one tool and the end of previous tool
- Tool Drilling - refactoring methods and optimizations

9.07.2020

- Tool Drilling - remade the methods used to generate GCode from Excellon, to parse the GCode. Now the GCode and GCode_parsed are stored individually for each tool and also they are plotted individually
- Tool Drilling now works - I still need to add the method for converting slots to drill holes
- CNCJob object - now it is possible for CNCJob objects originated from Excellon objects, to toggle the plot for a selection of tools
- working in cleaning up the Excellon UI (Selected Tab)
- finished the clean-up in Excellon UI
- Tool Drilling - added new feature to drill the slots

8.07.2020

- Tool Drilling - working on the UI
- Tool Drilling - added more tool parameters; laying the ground for adding "Drilling Slots" feature
- added as ToolTip for the the Preprocessor combobox items, the actual name of the items
- working on Tool Drilling - remaking the way that the GCode is stored, each tool will store it's own GCode
- working on Tool Drilling

7.07.2020

- updated the Panelize Tool to save the source code for the panelized Excellon objects so it can be saved from the Save project tab context menu entry
- updated the Panelize Tool to save the source code for the panelized Geometry objects as DXF file
- fixed the Panelize Tool so the box object stay as selected on new objects are loaded; any selection shape on canvas is deleted when clicking Panelize

6.07.2020

- Convert Any to Excellon. Finished Gerber object conversion to Excellon. Flash's are converted to drills. Traces in the form of a linear LineString (no changes in direction) are converted to slots.
- Turkish translation updated by Mehmet Kaya for the 8.993 version of strings

2.07.2020

- trying to optimize the resulting geometry in DXF import (and in SVG import) by merging contiguous lines; reduced the lines to about one third of the original
- fixed importing DXF file as Gerber method such that now the resulting Gerber object is correctly created having the geometry attributes like self.apertures and self.follow_geometry
- added Turkish translation - courtesy of Mehmet Kaya
- modified the Gerber export method to take care of the situation where the exported Gerber file is a SVG/DXF file imported as Gerber
- working in making a new functionality: Convert Any to Excellon. Finished Geometry object conversion to Excellon.

30.06.2020

- fixed the SVG parser so the SVG files with no information regarding the 'height' can be opened in FlatCAM; fixed issue #433

29.06.2020

- fixed the DXF parser to work with the latest version of ezdxf module (issues for the ellipse entity and modified attribute name for the knots_values to knots)
- fixed the DXF parser to parse correctly the b-splines by not adding automatically a knot value 0f (0, 0) when the spline is not closed

27.06.2020

- Drilling Tool - UI is working as expected; I will have to propagate the changes to other tools too, to increase likeness between different parts of the app

25.06.2020

- made sure that when trying to view the source but no object is selected, the messages are correct
- wip for Tool Drilling

23.06.2020

- working on Tool Drilling

21.06.2020

- wip

18.06.2020

- fixed bug in the Cutout Tool that did not allowed the manual cutous to be added on a Geometry created in the Tool
- fixed bug in Cutout Tool that made the selection box show in the stage of adding manual gaps
- updated Cutout Tool UI
- Cutout Tool - in manual gap adding there is now an option to automatically turn on the big cursor which could help
- Cutout Tool - fixed errors when trying to add a manual gap without having a geometry object selected in the combobox
- Cutout Tool - made sure that all the paths generated by this tool are contiguous which means that two lines that meet at one end will become only one line therefore reducing unnecessary Z moves
- Panelize Tool - added a new option for the panels of type Geometry named Path Optimization. If the checkbox is checked then all the LineStrings that are overlapped in the resulting multigeo Geometry panel object will keep only one of the paths thus minimizing the tool cuts.
- Panelize Tool - fixed to work for panelizing Excellon objects with the new data structure storing drills and tools in the obj.tools dictionary
- put the bases for a new Tool: Milling Holes Tool

17.06.2020

- added the multi-save capability if multiple CNCJob objects are selected in Project tab but only if all are of type CNCJob
- added fuse tools control in Preferences UI for the Excellon objects: if checked the app will try to see if there are tools with same diameter and merge the drills for those tools; if not the tools will just be added to the new combined Excellon
- modified generate_from_excellon_by_tool() method in camlib.CNCJob() such that when Toolchange option is False, since the drills will be drilled with one tool only, all tools will be optimized together

16.06.2020

- changed the data structure for the Excellon object; modified the Excellon parser and the Excellon object class
- fixed partially the Excellon Editor to work with the new data structure
- fixed Excellon export to work with the new data structure
- fixed all transformations in the Excellon object attributes; still need to fix the App Tools that creates or use Excellon objects
- fixed some problems (typos, missing data) generated by latest changes
- more typos fixed in Excellon parser, slots processing
- fixed Extract Drills Tool to work with the new Excellon data format
- minor fix in App Tools that were updated to have UI in a separate class
- Tool Punch Gerber - updated the UI
- Tool Panelize - updated the UI
- Tool Extract Drills - updated the UI
- Tool QRcode - updated the UI
- Tool SolderPaste - updated the UI
- Tool DblSided - updated the UI

15.06.2020

- in Paint Tool and NCC Tool updated the way the selected tools were processed and made sure that the Tools Table rows are counted only once in the processing
- modified the UI in Paint Tool such that in case of using rest machining the offset will apply for all tools
- Paint Tool - made the rest machining function for the paint single polygon method
- Paint Tool - refurbished the 'rest machining' for the entire tool
- Isolation Tool - fixed to work with selection of tools in the Tool Table (previously it always used all the tools in the Tool Table)
- Tools Database - added a context menu action to Save the changes to the database even if it's not in the Administration mode
- Tool Isolation - fixed a UI minor issue: 'forced rest' checkbox state at startup was always enabled
- started working in moving the Excellon drilling in its own Application Tool
- created a new App Tool named Drilling Tool where I will move the drilling out of the Excellon UI
- working on the Drilling Tool - started to create a new data structure that will hold the Excellon object data

14.06.2020

- made sure that clicking the icons in the status bar works only for the left mouse click
- if clicking the activity icon in the status bar and there is no object selected then the effect will be a plot_all with fit_view
- modified the FCLabel GUI element
- NCC Tool - remade and optimized the copper clearing with rest machining: now it works as expected with a reasonable performance
- fixed issue #428 - Cutout Tool -> Freeform geometry was not generated due of trying to get the bounds of the solid_geometry before it was available
- NCC Tool - now the tools can be reordered (if the order UI radio is set to 'no')
- remade the UI in Paint Tool and the tools in tools table ca now be reordered (if the order UI radio is set to 'no')
- some updates in NCC Tool using code from Paint Tool
- in Paint and NCC Tools made sure that using the key ESCAPE to cancel the tool will not create mouse events issues
- some updates in Tcl commands Paint and CopperClear data dicts
- modified the Isolation Tool UI: now the tools can be reordered (if the order UI radio is set to 'no')
- modified the Paint, NCC and Isolation Tools that when no tools is selected in the Tools Table, a message will show that no Tool is selected and the Geometry generation button is disabled

13.06.2020

- modified the Tools Database such that there is now a way to mark a tool as meant to be used in a certain part of the application; it will disable or enable parts of the parameters of the tool
- updated the FCTable GUI element to work correctly when doing drag&drop for the rows
- updated the Geometry UI to work with the new FCTable
- made the coordinates / delta coordinates / grid toolbar / actions toolbar visibility an option, controlled from the infobar (Status bar) context menu. How it's at app shutdown it's restored at the next application start
- moved the init of activity view in the MainGUI file from the APP.__init__()
- added a new string in the tooltip for the button that adds tool from database specifying the tools database administration is done in the menu
- when opening a new tab in the PlotTabArea the coordinates toolbars will be hidden and shown after the tab is closed

12.06.2020

- NCC Tool optimization - moved the UI in its own class
- NCC Tool optimization - optimized the Tool edit method
- NCC Tool - allow no tool at NCC Tool start (the Preferences have no tool)
- NCC Tool - optimized tool reset code
- NCC Tool - fixed the non-rest copper clearing to work as expected: each tool in the tool table will make it's own copper clearing without interference from the rest of the tools 
- Geometry UI - made again the header clickable and first click selects all rows, second click will deselect all rows.
- Geometry UI - minor updates in the layout; moved the warning text to the tooltip of the generate_cncjob button
- Geometry UI - working in making the modification of tool parameters such that if there is a selection of tools the modification in the Tool parameters will be applied to all selected

11.06.2020

- finished tool reordering in Geometry UI

10.06.2020

- fixed bug in the Isolation Tool that in certain cases an empty geometry was present in the solid_geometry which mae the CNCJob object generation to fail. It happen for Gerber objects created in the Gerber Editor
- working on the tool reordering in the Geometry UI
- continue - work in tool reordering in Geometry UI

9.06.2020

- fixed a possible problem in generating bounds value for a solid_geometry that have empty geo elements
- added ability to merge tools when merging Geometry objects if they share the same attributes like: diameter, tool_type or type
- added a control in Edit -> Preferences -> Geometry to control if to merge/fuse tools during Geometry merging

8.06.2020

- minor changes in the way that the tools are installed and connected
- renamed the GeoEditor class/file to AppGeoEditor from FlatCAMGeoEditor making it easier to see in the IDE tree structure
- some refactoring that lead to a working solution when using the Python 3.8 + PyQt 5.15
- more refactoring in the app Editors
- added a protection when trying to edit a Geometry object that have multiple tools but no tool is selected

7.06.2020

- refactoring in camlib.py. Made sure that some conditions are met, if some of the parameters are None then return failure. Modifications in generate_from_geometry_2 and generate_from_multitool_geometry methods
- fixed issue with trying to access GUI from different threads by adding a new signal for printing to shell messages
- fixed a small issue in Gerber file opener filter that did not see the *.TOP extension or *.outline extension
- in Excellon parser added a way to "guestimate" the units if no units are detected in the header. I may need to make it optional in Preferences
- changed the Excellon defaults for zeros suppression to TZ (assumed that most Excellon without units in header will come out of older Eagle) and the Excellon export default is now with coordinates in decimal
- made sure that the message that exclusion areas are deleted is displayed only if there are shapes in the exclusion areas storage
- fixed bug: on first ever usage of FlatCAM beta the last loaded language (alphabetically) is used instead of English (in current state is Russian)
- made sure the the GUI settings are cleared on each new install
- added a new signal that is triggered by change in visibility for the Shell Dock and will change the status of the shell label in the status bar. In this way the label will really be changed each time the shell is toggled
- optimized the GUI in Film Tool
- optimized GUI in Alignment Tool

6.06.2020

- NCC Tool - added a message to warn the user that he needs at least one tool with clearing operation
- added a GUI element in the Preferences to control the possibility to edit with mouse cursor objects in the Project Tab. It is named: "Allow Edit"

5.06.2020

- fixed a small issue in the Panelization Tool that blocked the usage of a Geometry object as panelization reference
- in Tool Calculators fixed an application crash if the user typed letters instead of numbers in the boxes. Now the boxes accept only numbers, dots, comma, spaces and arithmetic operators
- NumericalEvalEntry allow the input of commas now
- Tool Calculators: allowed comma to be used as decimal separator
- changed how the import of svg.path module is done in the ParseSVG.py file
- Tool Isolation - new feature that allow to isolate interiors of polygons (holes in polygons). It is possible that the isolation to be reported as successful (internal limitations) but some interiors to not be isolated. This way the user get to fix the isolation by doing an extra isolation.
- added mouse events disconnect in the quit_application() method
- remade the ReadMe tab
- Tool Isolation - added a GUI element to control if the isolation of a polygon, when done with rest, should be done with the current tool even if its interiors (holes in it) could not be isolated or to be left for the next tool
- updated all the translation strings to the latest changes
- small fix
- fixed the color set for the application objects
- made some reverts regarding the mods in the quit_application() method - problems when freezed
RELEASE 8.993

4.06.2020

- improved the Isolation Tool - rest machining: test if the isolated polygon has interiors (holes) and if those can't be isolated too then mark the polygon as a rest geometry to be isolated with the next tool and so on
- updated the French translation strings - from @micmac (Michel Maciejewski)

3.06.2020

- updated Transform Tool to have a selection of possible references for the transformations that are now selectable in the GUI
- Transform Tool - compacted the UI
- minor issue in Paint Tool
- added a new feature for Gerber parsing: if the NO buffering is chosen in the Gerber Advanced Preferences there is now a checkbox to activate delayed buffering which will do the buffering in background allowing the user to work in between. I hope that this can be useful in case of large Gerber files.
- made the delayed Gerber buffering to use multiprocessing but I see not much performance increase
- made sure that the status bar label for preferences is updated also when the Preferences Tab is opened from the Edit -> Preferences
- remade file names in the app
- fixed the issue with factory_defaults being saved every time the app start
- fixed the preferences not being saved to a file when the Save button is pressed in Edit -> Preferences
- fixed and updated the Transform Tools in the Editors
- updated the language translation strings (and Google_Translated some of them)
- made sure that if the user closes the app with an editor open, before the exit the editor is closed and signals disconnected
- updated the Italian translation - contribution by Golfetto Massimiliano
- made the timing for the object creation to be displayed in the shell

2.06.2020

- Tcl Shell - added a button to delete the content of the active line
- Tcl Command Isolate - fixed to work in the new configuration
- Tcl Command Follow - fixed to work in the new configuration
- Etch Compensation Tool - added a new etchant: alkaline baths
- fixed spacing in the status toolbar icons
- updated the translation files to the latest changes
- modified behavior of object comboboxes in Paint, NCC and CutOut Tools: now if an object is selected in Project Tab and is of the supported kind in the Tool, it will be auto-selected
- fixed some more strings
- updated the Google-translations for the German, Spanish, French
- updated the Romanian translation
- replaced the icon for the Editor in Toolbar (both for the normal icons and for icons in dark theme)

1.06.2020

- made the Distance Tool display the angle in values between 0 and 359.9999 degrees
- changed some strings
- fixed the warning that old preferences found even for new installation
- in Paint Tool fixed the message to select a polygon when using the Selection: Single Polygon being overwritten by the "Grid disabled" message
- more changes in strings throughout the app
- made some minor changes in the GUI of the FlatCAM Tools
- in Tools Database made sure that each new tool added has a unique name
- in AppTool made some methods to be class methods
- reverted the class methods in AppTool
- added a button for Transformations Tool in the lower side (common) of the Object UI
- some other UI changes
- after using Isolation Tool it will switch automatically to the Geometry UI
- in Preferences replaced some widgets with a new one that combine a Slider with a Spinner (from David Robertson)
- in Preferences replaced the widgets that sets colors with a compound one (from David Robertson)
- made Progressive plotting work in Isolation Tool
- fix an issue with progressive plotted shapes not being deleted on the end of the job
- some fixed due of recent changes and some strings changed
- added a validator for the FCColorEntry GUI element such that only the valid chars are accepted
- changed the status bar label to have an icon instead of text
- added a label in status bar that will toggle the Preferences tab
- made some changes such that that the label in status bar for toggling the Preferences Tab will be updated in various cases of closing the tab
- changed colors for the status bar labels and added some of the new icons in the gray version
- remade visibility as threaded - it seems that I can't really squeeze more performance from this

31.05.2020

- structural changes in Preferences from David Robertson
- made last filter selected for open file to be used next time when opening files (for Excellon, GCode and Gerber files, for now)

30.05.2020

- made confirmation messages for the values that are modified not to be printed in the Shell
- Isolation Tool: working on the Rest machining: almost there, perhaps I will use multiprocessing
- Isolation Tool: removed the tools that have empty geometry in case of rest machining
- Isolation Tool: solved some naming issues
- Isolation Tool: updated the tools dict with the common parameters value on isolating
- Fixed a recent change that made the edited Geometry objects in the Geometry Editor not to be plotted after saving changes
- modified the Tool Database such that when a tool shape is selected as 'V' any change in the Vdia or Vangle or CutZ parameters will update the tool diameter value
- In Tool Isolation made sure that the use of ESC key while some processes are active will disconnect the mouse events that may be connected, correctly
- optimized the Gerber UI
- added a Multi-color checkbox for the Geometry UI (will color differently tool geometry when the geometry is multitool)
- added a Multi-color checkbox for the Excellon UI (this way colors for each tool are easier to differentiate especially when the diameter is close)
- made the Shell Dock always show docked
- fixed NCC Tool behavior when selecting tools for Isolation operation

29.05.2020

- fixed the Tool Isolation when using the 'follow' parameter
- in Isolation Tool when the Rest machining is checked the combine parameter is set True automatically because the rest machining concept make sense only when all tools are used together
- some changes in the UI; added in the status bar an icon to control the Shell Dock
- clicking on the activity icon will replot all objects
- optimized UI in Tool Isolation
- overloaded the App inform signal to allow not printing to shell if a second bool parameter is given; modified some GUI messages to use this feature
- fixed the shell status label status on shell dock close from close button
- refactored some methods from App class and moved them to plotcanvas (plotcanvaslegacy) class
- added an label with icon in the status bar, clicking it will toggle (show status) of the X-Y axis on cavnas
- optimized the UI, added to status bar an icon to toggle the axis 
- updated the Etch Compensation Tool by adding a new possibility to compensate the lateral etch (manual value)
- updated the Etch Compensation Tool such that the resulting Gerber object will have the apertures attributes ('size', 'width', 'height') updated to the changes

28.05.2020

- made the visibility change (when using the Spacebar key in Project Tab) to be not threaded and to use the enabled property of the ShapesCollection which should be faster
- updated the Tool Database class to have the Isolation Tool data
- Isolation Tool - made to work the adding of tools from database
- fixed some issues related to using the new Numerical... GUI elements
- fixed issues in the Tool Subtract
- remade Tool Subtract to use multiprocessing when processing geometry
- the resulting Gerber file from Tool Subtract has now the attribute source_file populated

27.05.2020

- working on Isolation Tool: made to work the Isolation with multiple tools without rest machining

26.05.2020

- working on Isolation Tool: made to work the tool parameters data to GUI and GUI to data
- Isolation Tool: reworked the GUI
- if there is a Gerber object selected then in Isolation Tool the Gerber object combobox will show that object name as current
- made the Project Tree items not editable by clicking on selected Tree items (the object rename can still be done in the Selected tab)
- working on Isolation Tool: added a Preferences section in Edit -> Preferences and updated their usage within the Isolation tool
- fixed milling drills not plotting the resulting Geometry object
- all tuple entries in the Preferences UI are now protected against letter entry
- all entries in the Preferences UI that have numerical entry are protected now against letters
- cleaned the Preferences UI in the Gerber area
- minor UI changes

25.05.2020

- updated the GUI fields for the Scale and Offset in the Object UI to allow only numeric values and operators in the list [/,*,+,-], spaces, dots and comma
- modified the Etch Compensation Tool and added conversion utilities from Oz thickenss and mils to microns
- added a Toggle All checkbox to Corner Markers Tool
- added an Icon to the MessageBox that asks for saving if the user try to close the app and there is some unsaved work 
- changed and added some icons
- fixed the Shortcuts Tab to reflect the actual current shortcut keys
- started to work on moving the Isolation Routing from the Gerber Object UI to it's own tool
- created a new tool: Isolation Routing Tool: work in progress
- some fixes in NCC Tool
- added a dialog in Menu -> Help -> ReadMe?

24.05.2020

- changes some icons
- added a new GUI element which is a evaluated LineEdit that accepts only float numbers and /,*,+,-,% chars
- finished the Etch Compensation Tool
- fixed unreliable work of Gerber Editor and optimized the App.editor2object() method
- updated the Gerber parser such that it will parse correctly Gerber files that have only one solid polygon inside with multiple clear polygons (like those generated by the Invert Tool)
- fixed a small bug in the Geometry UI that made updating the storage from GUI not to work
- some small changes in Gerber Editor

23.05.2020

- fixed a issue when testing for Exclusion areas overlap over the Geometry object solid_geometry

22.05.2020

- fixed the algorithm for calculating closest points in the Exclusion areas
- added the Exclusion zones processing to Geometry GCode generation

21.05.2020

- added the Exclusion zones processing to Excellon GCode generation
- fixed a non frequent plotting problem for CNCJob objects made out of Excellon objects

19.05.2020

- updated the Italian language (translation incomplete)
- updated all the language strings to the latest changes; updated the POT file
- fixed a possible malfunction in Tool Punch Gerber

18.05.2020

- fixed the PDF Tool when importing as Gerber objects
- moved all the parsing out of the PDF Tool to a new file ParsePDF in the flatcamParsers folder
- trying to fix the pixmap load crash when running a FlatCAMScript
- made the workspace label in the status bar clickable and also added a status bar message on status toggle for workspace
- modified the GUI for Film and Panelize Tools
- moved some of the GUI related methods from FlatCAMApp.App to the flatcamGUI.MainGUI class
- moved Shortcuts Tab creation in it's own class
- renamed classes to have shorter names and grouped
- removed reference to postprocessors and replaced it with preprocessors
- more refactoring class names
- moved some of the methods from the App class to the ObjectCollection class
- moved all the new_object related methods in their own class AppObjects.AppObject
- more refactoring; solved some issues introduced by the refactoring
- solved a circular import
- updated the language translation files to the latest changes (no translation)
- working on a new Tool: Etch Compensation Tool -> installed the tool and created the GUI and class template
- moved more methods out of App_Main class
- added confirmation messages for toggle of HUD, Grid, Grid Snap, Axis
- added icon in status bar for HUD; clicking on it will toggle the HUD (heads up display)
- fixes due of recent changes
- fixed issue #417

17.05.2020

- added new FlatCAM Tool: Corner Markers Tool which will add line markers in the selected corners of the bounding box of the targeted Gerber object
- added a menu entry in Menu -> View for Toggle HUD
- solved the issue with the GUI in the Notebook being expanded too much in width due of the FCDoubleSpinner and FCSpinner sizeHint by setting the sizePolicy to Ignored value
- fixed the workspace being always A4
- added a label in the status bar to show if the workplace is active and what size it is
- now the Edit command (either from Menu Edit ->Edit Object) or through the shortcut key (E key) or project tab context menu works also for the CNCJob objects (will open a text Editor with the GCode)
- fixed the object collection methods that return a list of objects or names of objects such that they have a parameter now to allow adding to those lists (or not) for the objects of type Script or Document. Thus fixing some of the Tcl commands such Set Origin
- reverted the previous changes to object collection; it is better to create empty methods in FlatCAMScript and FlatCAMDocument objects

16.05.2020

- worked on the NCC Tool; added a new clear method named 'Combo' which will go through all methods until the clear is done
- added a Preferences parameter for font size used in HUD

13.05.2020

- updated the French translation strings, made by @micmac (Michel)

12.05.2020

- fixed recent issues introduced in Tcl command Drillcncjob
- updated the Cncjob to use the 'endxy' parameter which dictates the x,y position at the end of the job
- now the Tcl commands Drillcncjob and Cncjob can use the toolchangexy and endxy parameters with or without parenthesis (but no spaces allowed)
- modified the Tcl command Paint "single" parameter. Now it's value is a tuple with the x,y coordinates of the single polygon to be painted.
- the HUD display state is now persistent between app restarts
- updated the Distance Tool such that the right click of the mouse will cancel the tool unless it was a panning move
- modified the PlotCanvasLegacy to decide if there is a mouse drag based on the distance between the press event position and the release event position. If the distance is smaller than a delta distance then it is not a drag move.

11.05.2020

- removed the labels in status bar that display X,Y positions and replaced it with a HUD display on canvas (combo key SHIFT+H) will toggle the display of the HUD
- made the HUD work in Legacy2D mode
- fixed situation when the mouse cursor is outside of the canvas and no therefore returning None values
- remade the Snap Toolbar presence; now it is always active and situated in the Status Bar
- Snap Toolbar is now visible in Fullscreen
- in Fullscreen now the Notebook is available but it will be hidden on Fullscreen launch
- fixed some minor issues (in the HUD added a separating line, missing an icon in toolbars on first launch)
- made sure that the corner snap buttons are shown only in Editors
- changed the HUD color when using Dark theme 
- fix issue in Legacy2D graphic mode where the snap function was not accessible when the PlotCanvasLegacy class was created
- modified the HUD in Legacy2D when using Dark Theme to use different colors
- modified how the graphic engine change act in Preferences: now only by clicking Apply(or Save) the change will happen. And there is also a message asking for confirmation
- re-added the position labels in the status bar; they will be useful if HUD is Off (Altium does the same :) so learn from the best)
- fixed the Tcl command Cncjob: there was a problem reported as issue #416. The command did not work due of the dpp parameter
- modified the Tcl command Cncjob such that if some of the parameters are not used then the default values will be used (set with set_sys)
- modified the Tcl command Drillcncjob to use the defaults when some of the parameters are not used

10.05.2020

- fixed the problem with using comma as decimal separator in Grid Snap fields

9.05.2020

- modified the GUI for Exclusion areas; now the shapes are displayed in a Table where they can be selected and deleted. Modification applied for Geometry Objects only (for now).
- fixed an error when converting units, error that acted when in those fields that accept lists of tools only one tool was added
- finished the GUI for exclusion areas both in the Excellon and Geometry Objects. Need to think if to make it visible only in Advanced Mode

8.05.2020

- added a parameter to the FlatCAMDefaults class, whenever a value in the self.defaults dict change it will call a callback function and send to it the modified key
- optimized and fixed some issues in the self.on_toggle_units() method
- the Exclusion areas will have all the orange color but the color of the outline will differ according to the type of the object from where it was added (cosmetic use only as the Exclusion areas will be applied globally)
- removed the Apply theme button in the Preferences; it is now replaced by the more general buttons (either Save or Apply)
- added a confirmation/warning message when applying a new theme

7.05.2020

- added a fix so the app close is now clean, with exit code 0 as set
- added the ability to add exclusion areas from the Excellon object too. Now there is a difference in color to differentiate from which type of object the exclusion areas were added but they all serve the same purpose

6.05.2020

- wip in adding Exclusion areas in Geometry object; each Geometry object has now a storage for shapes (exclusion shapes, should I make them more general?)
- changed the above: too many shapes collections and the performance will go down. Created a class ExclusionAreas that holds all the require properties and the Object UI elements will connect to it's methods. This way I can apply this feature to Excellon object too (who is a special type of Geometry Object)
- handled the New project event and the object deletion (when all objects are deleted then the exclusion areas will be deleted too)
- solved issue with new parameter end_xy when it is None
- solved issue with applying theme and not making the change in the Preferences UI. In Preferences UI the theme radio is always Light (white)
- now the annotations will invert the selected color in the Preferences, when selecting Dark theme 

5.05.2020

- fixed an issue that made the preprocessors combo boxes in Preferences not to load and display the saved value fro the file
- some PEP8 corrections

4.05.2020

- in detachable tabs, Linux loose the reference of the detached tab and on close of the detachable tabs will gave a 'segmentation fault' error. Solved it by not deleting the reference in case of Unix-like systems
- some strings added to translation strings

3.05.2020

- small changes to allow making the x86 installer that is made from a Python 3.5 run FlatCAM beta 
- fixed multiple parameter 'outname' in the Tcl commands OpenGerber and OpenGcode 
- added more examples in the scripts Examples: isolate and cutout examples
- updated the Italian translation
- updated the translation files
- changed the line endings for Makefile and setup_ubuntu.sh files
- protected a dict in VispyVisuals from issuing errors of keys changed while iterating through it

2.05.2020

- working on a new feature: adding interdiction area for Gcode generation. They will be added in the Geometry Object

2.05.2020

- changed the icons for the grid snap in the status bar
- moved some of the methods from FlatCAMApp.App to flatcamGUI.MainGUI class
- fixed bug in Gerber Editor in which the units conversion wasn't calculated correct
- fixed bug in Gerber Editor in which the QThread that is started on object edit was not stopped at clean up stage
- fixed bug in Gerber Editor that kept all the apertures (including the geometry) of a previously edited object that was not saved after edit
- modified the Cutout Tool to generate multi-geo objects therefore the set geometry parameters will populate the Geometry Object UI
- modified the Panelize Tool to optimize the output from Cutout Tool such that there are no longer overlapping cuts
- some string corrections
- updated the Italian translation done by user @pcb-hobbyst (Golfetto Massimiliano)
- RELEASE 8.992

01.05.2020

- added some ToolTips (strings needed to be translated too) for the Cut Z entry in Geometry Object UI that explain why is sometime disabled and reason for it's value (sometime is zero)
- solve parenting issues when trying to load a FlatScript from Menu -> File -> Scripting
- added a first new example script and added some files to work with
- added a new parameter that will store the home folder of the FlatCAM installation so we can access the example folder
- added in Gerber editor a method for zoom fit that takes into consideration the current geometry of the edited object

30.04.2020 

- made some corrections - due of recent refactoring PyCharm reported errors all over (not correct but it made programming difficult)
- modified the requirements.txt file to force svg.path module to be at least version 4.0
- fixed bug in Tools DB that crashed when a tool is copied
- in Tools Database added a Save Button whose color is changed in Red if the DB was modified and back to default when the DB is saved.
- fixed bug in Tool DB that crashed the app when the Tool Name was modified but there was no tree item (a tool in the list) selected in the Tree widget (list of tools)
- now on tool add and tool copy, the last item (tool, which is the one added) is autoselected; o tool delete always the first item (tool) is selected
- fixed issue #409; problem was due of an assert I used in the handler of the Menu ->Options -> Flip X(Y) menu entry
- activated and updated the editing in the Aperture Table in the Gerber Editor; not all parameters can be edited for every type of aperture
- some strings updated
- fixed a small issue in loading the Projects

29.04.2020

- added a try-except clause in the FlatCAMTranslation.restart_program() when closing the Listener and the thread that runs it to adjust to MacOS usage
- more PEP8 changes
- in PreferencesUI.PreferencesUIManager class I removed the need to pass reference to the App class since it this was available through the 'ui' parameter
- some fixes due to recent refactoring
- minor bugs fixed (not so visible)
- promoted some methods to be static
- set the default layout on first run to the 'minimal' value
- modified the method that detects which tab was closed in the Plot Area so it will no longer depend on it's translated text but on it's objectName set on the QTab creation
- fixed the merge methods for all FlatCAM objects
- fixed a SyntaxError Exception when checking for types of found old preferences
- updated the French, German and Spanish Google translations
- updated the Romanian translation
- fixed units conversion issue
- updated the units conversion method to convert all the convertible parameters in the Preferences
- solved the problem with not closing all the tabs in Plot Area when creating a New Project; the issue was that once a tab was removed the indexes are remade (when tab 0 is removed then tab 1 becomes tab 0 and so on)
- some more strings changed -> updated the translations
- replaced some FormLayouts with Gridlayouts in Tool Cutout.

28.04.2020

- handled a possible situation in App.load_defaults() method
- fixed some issues in FlatCAMDB that may appear in certain scenarios
- some minor changes in the Python version detection
- added a new Tcl Command named SetPath which will set a path to be used by the Tcl commands. Once set will serve as a fallback path in case that the files fail to be opened first time. It will be persistent, saved in preferences.
- added the GUI for the new Open Example in the FIle -> Scripting menu.
- I am modifying all the open ... handlers to add a parameter that will flag if the method was launched from Tcl Shell. This way if the method will fail to open the filename (which include the path) it will try to open from a set fallback path.
- fixed issue #406, bug introduced recently (leftover changes).
- modified the ImportSVG Tcl command name to OpenSVG (open_svg alias)
- added a new Tcl command named OpenDXF (open_dxf alias)
- fixed some errors in Scripting features
- added a new Tcl command named GetPath as a convenient way to get the current default path stored in App.defaults['global_tcl_path']
- added a new package to be installed in Linux to make available the black theme for FlatCAM beta
- moved all the 'share' resources (icons) to the 'assets/resources' folder
- some more fixes to problems generated by latest changes in the open handlers
- modified the make_freezed.py script for the new location of the icons
- added a fix for the ConnectionRefusedError in Linux that is issued when first running after a FlatCAM crash
- in SVG parser modified some imports to be one on each line
- fixed the Tcl Command BBox (leftovers from recent global changes)
- fixed some typos in strings reported by @pcb-hobbyst on FlatCAM forum
- disabled a skip_quotes method in ToolShell.FCShell class so I can now use quotes to enclose file paths with spaces inside

27.04.2020

- finished the moving of all Tcl Shell stuff out of the FlatCAAMApp class to flatcamTools.ToolShell class
- updated the requirements.txt file to request that the Shapely package needs to be at least version 1.7.0 as it is needed in the latest versions of FlatCAM beta
- some TOOD cleanups
- minor changes
- replaced the testing if instance of FlatCAMObj with testing the obj.kind attribute
- removed the import of the whole FlatCAMApp file only for the usage of GracefulException
- remove the import of FlatCAMApp and used alternate ways
- optimized the imports in some files
- moved the Bookmarksmanager and ToolDB classes into their own files
- solved some bugs that were not so visible in the Editors and HPGL parser
- split the FlatCAMObj file into multiple files located in the flatcamObjects folder and renamed the contained classes with names more suggestive
- updated the Google Translation for the German language
- added support for Hungarian language - no translation for now
- minor changes
- moved the ObjectCollection class to the flatcamObjects folder where it belongs
- Linux Makefile 

25.04.2020

- ensured that on Graceful Exit (CTRL+ALT+X key combo) if using Progressive Plotting, the eventual residual plotted lines are deleted. This apply for Tool NCC and Tool Paint
- fixed links in Attributions tab in Help -> About FlatCAM to be able to open external links.
- updated Google Translations for French and Spanish languages
- added some '\n' chars in the Help Tcl command to make the help more readable

24.04.2020

- some PEP changes, some method descriptions updated
- added a placeholder text to 2Sided Tool
- added a new menu entry in the context menu of the Tcl Shell: 'Save Log' which will save the content of the Tcl Shell browser window to a file
- the status bar messages that are echoed in the Tcl Shell will no longer have all text colored but only the identifier
- some message strings cleanup
- added possibility to save as text file the content in Tcl Shell browser window when clicking the Save log context menu entry
- fixed an issue regarding the statusbar pixmap selection
- update the language template strings.pot and updated the Romanian translation
- updated the Readme file with the steps for installation for MacOS
- updated the requirements.txt file
- updated some of the icons in the dark_resources folder (some added, some modified)
- updated Paint Tool for the new Tool DB
- updated the Tcl commands CopperClear and Paint

23.04.2020 

- fixed the Tcl Command Help to work as expected; made the text of the commands to be colored in Red color and bold
- added a 'Close' menu entry in the Tcl Shell context menu that will close (hide) the Tcl Shell Dock widget
- on launching the Tcl Shell the Edit line will take focus immediately 
- in App.on_mouse_move_over_plot() method no longer will be done a setFocus() on every move, only when it is needed
- added an extra check if old preferences files are detected, a check if the type of the values is the same with the type in the current preferences file. If the type is not the same then the current type is preferred.
- aligned the Tcl commands display when the Help Tcl command is run without parameters
- fixed the Tcl command Plot_All that malfunctioned if there were any FlatCAM scripts (or FlatCAM documents) open
- updated the shortcuts list

22.04.2020 

- added a new feature, project auto-saving controlled from Edit -> Preferences -> General -> APP. Preferences -> Enable Auto Save checkbox
- fixed some bugs in the Tcl Commands
- modified the Tcl Commands to be able to use as boolean values keywords with lower case like 'false' instead of expected 'False'
- refactored some of the code in the App class and created a new Tcl Command named Help

20.04.2020

- made the Grid icon in the status bar clickable and it will toggle the snap to grid function
- some mods in the Distance Tool
- added ability to use line width when adding shapes for both Legacy and OpenGL graphic engines
- added the linewidth=2 parameter for the Tool Distance utility geometry
- fixed a selection issue in Legacy graphic mode for single click
- added a CHANGELOG file and changed the README file to contain the installation instructions
- updated the README file
- in Project Tab added tooltips for the loaded objects
- fixed a bug in loading objects by drag&drop into the Project Tab where only one object in the selection was loaded

19.04.2020 

- fixed a bug that did not allow to edit GUI elements of type FCDoubleSpinner if it contained the percent symbol
- some small optimizations in the GUI of Cutout Tool
- fixed more issues (new) in NCC Tool
- added a new layout named 'minimal'
- some PEP8 changes in Geometry Editor

15.04.2020 

- made sure that the Tcl commands descriptions listed on help command are aligned

14.04.2020 

- lightened the hue of the color for 'success' messages printed in the Tcl Shell browser
- modified the extensions all over such the names include also the extension name. For Linux who does not display the extensions in the native FileDialog.
- added descriptions for some of the methods in the app.
- added lightened icons for the dark theme from Leandro Heck 

13.04.2020 

- added the outname parameter for the geocutout Tcl command
- multiple fixes in the Tcl commands (especially regarding the interchange between True/false and 1/0 values)
- updated the help for all Tcl Commands
- in Tcl Shell, the 'help' command will add also a brief description for each command in the list
- updated the App.plot_all() method giving it the possibility to be run as threaded or not
- updated the Tcl command PlotAll to be able to run threaded or not
- updated the Tcl commands PlotAll and PlotObjects to have a parameter that control if the objects are to be plotted or not on canvas; it serve as a disable/enable
- minor update to the autocomplete dictionary
- the Show Shell in Edit -> Preferences will now toggle the Tcl shell based on the current status of the Tcl Shell
- updated the Tcl command Isolate help for follow parameter 
- updated DrillCncJob Tcl Command with new parameters and fixed it to work in the new format of the Excellon methods
- fixed issue #399
- changed CncJob Tcl Command parameter 'depthperpass' to a shorter 'dpp'

11.04.2020 

- fixed issue #394 - the saveDialog in Linux did not added the selected extension
- when the Save button is clicked in the Edit -> Preferences the Preferences tab is closed.

10.04.2020 

- made sure that the timeout parameter used by some Tcl Commands is seen as an integer in all cases - fixed issue #389
- minor changes in Paint Tool
- minor changes in GUI (Save locations in Menu -> File) and the key shortcuts - fixed issue #391


9.04.2020 

- if FlatCAM is not run with Python version >= 3.5 it will exit.
- modified all CTRL+ with Ctrl+ and all ALT+ with Alt+ and all SHIFT+ with Shift+. Fixed issue #387.
- removed some packages from setup_ubuntu.sh as they are not needed in FlatCAM beta

8.4.2020 

- fixed the Tcl Command Delete to have an argument -f that will force deletion evading the popup (if the popup is enabled). The sme command without a name now will delete all objects
- fixed the Tcl Command JoinExcellons
- fixed the Tcl Command JoinGeometry
- fixed the Tcl Command Mirror
- updated the Tcl Command Mirror to use a (X,Y) origin parameter. Works if the -box parameter is not used.
- updated the Tcl Command Offset. Now it can use only -x or -y parameter no longer is mandatory to have both. The one that is not present will be assumed 0.0
- updated the Tcl Command Panelize. The -rows and -columns parameters are no longer both required. If one is not present then it is assumed to be zero.
- updated the Tcl Command Scale. THe -origin parameter can now be a tuple of (x,y) coordinates.
- updated the Tcl Command Skew. Now it can use only -x or -y parameter no longer is mandatory to have both. The one that is not present will be assumed 0.0
- updated the help for all the Tcl Commands

6.04.2020 

- added key shortcuts (arrow up/down) that will select the objects in the Project tab if the focus is in that tab
- added a minor change to the ListSys Tcl command
- fixed an crash generated when running the Tool Database from the Menu -> Options menu entry
- fixed a bug in handling the UP/DOWN key shortcuts that caused a crash when no object was selected in the Project Tab; also made sure that the said keys are handled only for the Project Tab
- some PEP8 changes and other minor changes
- updated the requirements file
- updated the 2Sided Tool by not allowing the Gerber file to be mirrored without a valid reference and added some placeholder texts

5.04.2020 

- made sure that the HDPI scaling attribute is set before the QApplication is started
- made sure that when saving a project, the app will try to update the active object from UI form only if there is an active object
- fix for contextual menus on canvas when using PyQt versions > 5.12.1
- decision on which mouse button to use for panning is done now once when setting the plotcanvas
- fix to work with Python 3.8 (closing the application)
- fixed bug in Gerber parser that allowed loading as Gerber of a file that is not a Gerber
- fixed a bug in extension detection for Gerber files that allowed in the filtered list files that extension *.gb*
- added a processEvents method in the Gerber parser parse_lines() method
- fixed issue #386 - multiple Cut operation on a edited object created a crash due of the bounds() method
- some changes in the Geometry UI

4.04.2020 

- fixed the Repeated code parsing in Excellon Parse

1.04.2020 

- updated the SVG parser to take into consideration the 'Close' svg element and paths that are made from a single line (we may need to switch to svgpathtools module)
- minor changes to increase compatibility with Python 3.8
- PEP8 changes

30.03.2020

- working to update the Paint Tool
- fixed some issues in Paint Tool

29.03.2020

- modified the new database to accept data from NCC and Paint Tools
- fixed issues in the new database when adding the tool in a Geometry object
- fixed a bug in Geometry object that generated a change of dictionary while iterating over it
- started to add the new database links in the NCC and Paint Tools
- in the new Tools DB added ability to double click on the ID in the tree widget to execute adding a tool from DB
- working in updating NCC Tool

28.03.2020

- finished the new database based on a QTreeWidget

21.03.2020

- fixed Cutout Tool to work with negative values for Margin parameter

20.03.2020

- updated the "re-cut" feature in Geometry object; now if the re-cut parameter is non zero it will cut half of the entered distance before the isolation end and half of it after the isolation end
- added to Paint and NCC Tool a feature that allow polygon area selection when the reference is selected as Area Selection
- in Paint Tool and NCC Tool added ability to use Escape Tool to cancel Area Selection and for Paint Tool to cancel Polygon Selection
- fixed issue in "re-cut" feature when combined with multi-depth feature
- fixed bugs in cncjob TclCommand

13.03.2020

- fixed a bug in CNCJob generation out of a Excellon object; the plot failed in case some of the geometry of the CNCJob was invalid
- fixed Properties Tool due of recent changes to the FCTree widget

12.03.2020

- working on the new database
- fix a bug in the TextInputTool in FlatCAM Geometry Editor that crashed the sw when some fonts are not loaded correctly

4.03.2020

- updated all the FlatCAM Tools and the Gerber UI FCComboBoxes to update the box value with the latest object loaded in the App
- some fixes in the NCC Tool
- modified some strings

02.03.2020

- added property that allow the FCComboBox to update the view with the last item loaded; updated the app to use this property

01.03.2020

- updated the CutOut Tool such that while adding manual gaps, the cutting geometry is updated on-the-fly if the gap size or tool diameter parameters are adjusted
- updated the UI in Geometry Editor

29.02.2020

- compacted the NCC Tool UI by replacing some Radio buttons with Combo boxes due of too many elements
- fixed error in CutOut Tool when trying to create a FreeFrom Cutout out of a Gerber object with the Convex Shape checked
- working on a new type of database

28.02.2020

- some small changes in preprocessors
- solved issue #381 where there was an error when trying to generate CNCJob out of an Excellon file that have a tool with only slots and no drills
- solved some issues in the preprocessors regarding the newly introduced feature that allow control of the final move X,Y positions

25.02.2020

- fixed bug in Gerber parser: it tried to calculate a len() for a single element and not a list - a Gerber generated by Eagle exhibited this
- added a new parameter named 'End Move X,Y' for the Geometry and Excellon objects. Adding a tuple of coordinates in this field will control the X,Y position of the final move; not entering a value there will cause not to make an end move

20.02.2020

- in Paint Tool replaced the Selection radio with a combobox GUI element that is more compact
- in NCC Tool modified the UI

19.02.2020

- fixed some issues in the Geometry Editor; the jump signal disconnect was failing for repeated Editor tool operation
- fixed an issue in Gerber Editor where the multiprocessing pool was reported as closed and an ValueError exception was raised in a certain scneraio
- on Set Origin, Move to Origin and Move actions for Gerber and Excellon objects the source file will be also updated (the export functions will export an updated object)
- in FlatCAMObj.export_gerber() method took into account the possibility of polygons of type 'clear' (the ones found in the Gerber files under the LPC command)

17.02.2020

- updated the Excellon UI to hold data for each tool
- in Excellon UI removed the tools table column for Offset Z and used the UI form parameter
- updated the Excellon Editor to add for each tool a 'data' dictionary
- updated all FlatCAM tools to use the new confirmation message that show if the entered value is within range or outside
- updated all FlatCAM tools to use the new confirmation message for QSpinBoxes, too
- in Excellon UI protected the values that are common parameters from change on tool selection change
- fixed some issues related to the usage of the new confirmation message in FlatCAM Tools
- made sure that the FlatCAM Tools UI initialization is done only in set_tool_ui() method and not in the constructor
- adapted the GCode generation from Excellon to work with multiple tools data and modified the preprocessors header
- when multiple tools are selected in Excellon UI and parameters are modified it will applied to all selected
- in Excellon UI, Paint Tool and NCC Tool finished the "Apply parameters to all tools" functionality
- updated Paint Tool and NCC Tool in the UI functionality
- fixed the Offset spinbox not being controller by offset checkbox in NCC Tool

16.02.2020

- small update to NCC Tool UI

15.02.2020

- in Paint Tool added a new method of painting named Combo who will pass through all the methods until the polygon is cleared
- in Paint Tool attempting to add a new mode suitable for Laser usage
- more work in the new Laser Mode in the Paint Tool
- modified the Paint Tool UI

14.02.2020

- adjusted the UI for Excellon and Geometry objects
- added a new FlatCAM Tool: Gerber Invert Tool. It will invert the copper features in a Gerber file: where is copper there will be empty and where is empty it will be copper
- added the Preferences entries for the Gerber Invert Tool

13.02.2020

- finished Punch Gerber Tool
- minor changes in the Tool Transform and Tool Calculators UI to bring them up2date with the other tools

12.02.2020

- working on fixing a bug in GeometryObject.merge() - FIXED issue #380
- fixed bug: when deleting a FlatCAMCNCJob with annotations enabled, the annotations are not deleted from canvas; fixed issue #379
- fixed bug: creating a new project while a project is open and it contain CNCJob annotations and/or Gerber mark shapes, did not delete them from canvas

11.02.2020

- working on Tool Punch; finished the geometry update with the clear geometry for the case of Excellon method
- working on Tool Punch; finished the geometry update with the clear geometry for the case of Fixed Diameter method

10.02.2020

- optimized the Paint and NCC Tools. When the Lines type of painting/clearing is used, the lines will try to arrange themselves on the direction that the lines length clearing the polygon are bigger
- solved bug that made drilling with Marlin preprocessor very slow
- applied the fix for above bug to the TclCommand Drillcncjob too
- started a new way to clear the Gerber polygons based on the 'follow' lines
- some cleanup and bug fixes for the Paint Tool


8.02.2020

- added a new preprocessor for using laser on a Marlin 3D printer named 'Marlin_laser_use_Spindle_pin'
- modified the Geometry UI when using laser preprocessors
- added a new preprocessor file for using laser on a Marlin motion controller but with the laser connected to one of the FAN pins, named 'Marlin_laser_use_FAN_pin'
- modified the Excellon GCode generation so now it can use multi depth drilling; modified the preprocessors to show the number of passes

5.02.2020

- Modified the Distance Tool such that the Measure button can't be clicked while measuring is in progress
- optimized selection of drills in the Excellon Editor
- fixed bugs in multiple selection in Excellon Editor
- fixed selection problems in Gerber Editor
- in Distance Tool, when run in the Excellon or Gerber Editor, added a new option to snap to center of the geometry (drill for Excellon, pad for Gerber)

3.02.2020

- modified Spinbox and DoubleSpinbox Custom UI elements such that they issue a warning status message when the typed value is out of range
- fixed the preprocessors with 'laser' in the name to use the spindle direction set in the Preferences
- increased the upper limit for feedrates by an order of magnitude

2.02.2020

- fixed issue #376 where the V-Shape parameters from Gerber UI are not transferred to the resulting Geometry object if the 'combine' checkbox is not checked in the Gerber UI
- in Excellon UI, if Basic application mode is selected in Preferences, the Plot column 'P' is hidden now because some inexperienced users mistake this column checkboxes for tool selection
- fixed an error in Gerber Parser; the initial values for current_x, current_y were None but should have been 0.0
- limited the lower limit of angle of V-tip to a value of 1 because 0 makes no sense 
- small changes in Gerber UI
- in Geometry Editor make sure that after an edit is finished (correctly or forced) the QTree in the Editor UI is cleared of items

31.01.2020

- added a new functionality, a variation of Set Origin named Move to Origin. It will move a selection of objects to origin such as the bottom left corner of the bounding box that fit them all is in origin.
- fixed some bugs
- fixed a division by zero error: fixed #377

30.01.2020

- remade GUI in Tool Cutout, Tool Align Objects, Tool Panelize
- some changed in the Excellon UI
- some UI changes in the common object UI

29.01.2020

- changes in how the Editor exit is handled
- small fix in some pywin32 imports
- remade the GUI + small fixes in 2Sided Tool
- updated 2Sided Tool

28.01.2020

- some changes in Excellon Editor

27.01.2020

- in Geometry Editor made sure that on final save, for MultiLineString geometry all the connected lines are merged into one LineString to minimize the number of vertical movements in GCode
- more work in Punch Gerber Tool
- the Jump To popup window will now autoselect the LineEdit therefore no more need for an extra click after launching the function
- made some structural changes in Properties Tool
- started to make some changes in Geometry Editor
- finished adding in Geometry Editor a TreeWidget with the geometry shapes found in the edited object

24.02.2020

- small changes to the Toolchange manual preprocessor
- fix for plotting Excellon objects if the color is changed and then the object is moved
- laying the GUI for a new Tool: Punch Gerber Tool which will add holes in the Gerber apertures
- fixed bugs in Minimum Distance Tool
- update in the GUI for the Punch Gerber Tool

22.01.2020

- fixed a bug in the bounding box generation

19.01.2020

- fixed some bugs that are visible in Linux regarding the ArgsThread class: on app close we need to quit the QThread running the ArgsThread class and also close the opened Socket
- make sure that the fixes above apply when rebooting app for theme change or for language change
- fixed and issue that made setting colors for the Gerber file not possible if using a translation
- made possible to set the colors for Excellon objects too
- added to the possible colors the fundamentals: black and white
- in the project context menu for setting colors added the option to set the transparency and also a default option which revert the color to the default value set in the Preferences

17.01.2020

- more changes to Excellon UI
- changes to Geometry UI
- more work in NCC Tool upgrade; each tool now work with it's own set of parameters
- some updates in NCC Tool
- optimized the object envelope generation in the redesigned NCC Tool

16.01.2020

- updated/optimized the GUI in Preferences for Paint Tool and for NCC Tool
- work in Paint Tool to bring it up to date with NCC Tool
- updated the GUI in preferences for Calculator Tool
- a small change in the Excellon UI
- updated the Excellon and Geometry UI to be similar
- put bases for future changes to Excellon Object UI such that each tool will hold it's own parameters
- in ParseExcellon.Excellon the self.tools dict has now a key 'data' which holds a dict with all the default values for Excellon and Geometry
- Excellon and Geometry objects, when started with multiple tools selected, the parameters tool name reflect this situation
- moved default_data data update from Excellon parser to the Excellon object constructor

15.01.2020

- added key shortcuts and toolbar icons for the new tools: Align Object Tool (Alt+A) and Extract Drills (Alt+I)
- added new functionality (key shortcut Shift+J) to locate the corners of the bounding box (and center) in a selected object
- modified the NCC Tool GUI to prepare for accepting a tool from a tool database
- started to modify the Paint Tool to be similar to NCC Tool and to accept a tool from a database
- work in Paint Tool GUI functionality

14.01.2020

- in Extract Drill Tool added a new method of drills extraction. The methods are: fixed diameter, fixed annular ring and proportional
- in Align Objects Tool finished the Single Point method of alignment
- working on the Dual Point option in Align Objects Tool - angle has to be recalculated
- finished Dual Point option in Align Objects Tool

13.01.2020

- fixed a small GUI issue in Excellon UI when Basic mode is active
- started the add of a new Tool: Align Objects Tool which will align (sync) objects of Gerber or Excellon type
- fixed an issue in Gerber parser introduced recently due of changes made to make Gerber files produced by Sprint Layout
- working on the Align Objects Tool

12.01.2020

- improved the circle approximation resolution
- fixed an issue in Gerber parser with detecting old kind of units
- if CTRL key is pressed during app startup the app will start in the Legacy(2D) graphic engine compatibility mode

11.01.2020

- fixed an issue in the Distance Tool
- expanded the Extract Drills Tool to use a particular annular ring for each type of aperture flash (pad)
- Extract Drills Tool: fixed issue with oblong pads and with pads made from aperture macros
- Extract Drills Tool: added controls in Edit -> Preferences

10.02.2020

- working on a new tool: Extract Drills Tool who will create a Excellon object out of the apertures of a Gerber object
- finished the GUI in the Extract Drills Tool
- fixed issue in Film Tool where some parameters names in calls of method export_positive() were not matching the actual parameters name
- finished the Extract Drills Tool
- fixed a small issue in the DoubleSided Tool

8.01.2020

- working in NCC Tool
- selected rows in the Tools Tables will stay colored in blue after loosing focus instead of the default gray
- in NCC Tool the Tool name in the Parameters section will be the Tool ID in the Tool Table
- added an exception catch in case the plotcanvas init failed for the OpenGL graphic engine and warn user about what happened

7.01.2020

- solved issue #368 - when using the Enable/Disable prj context menu entries the plotted status is not updated in the object properties
- updates in NCC Tool

6.01.2020

- working on new NCC Tool

2.01.2020

- started to rework the NCC Tool GUI in preparation for adding a Tool DB feature
- for auto-completer, now clicking an entry in the completer popup will select that entry and insert it
- made available only for Linux and Windows (not OSX) the starting of the thread that checks if another instance of FlatCAM is already running at the launch of FLatCAM
- modified Toggle Workspace function to work in the new Preferences UI configuration
- cleaned the app from progress signal usage since it is not used anymore

1.01.2020

- fixed bug in NCC Tool: after trying to add a tool already in the Tool Table when trying to change the Tool Type the GUI does not change
- final fix for app not quiting when running a script as argument, script that has the quit_flatcam Tcl command; fixed issue #360
- fixed issue #363. The Tcl command drillcncjob does not create tool cut, does not allow creation of gcode, it forces the usage of dwell and dwelltime parameters
- in NCC Tool I've added a warning so the user is warned that the NCC margin has to have a value of at least the tool diameter that is doing an iso_op job in the Tool Table
- modified the Drillcncjob and Cncjob Tcl commands to be allowed to work without the 'dwell' and 'toolchange' arguments. If 'dwelltime' argument is present it will be assumed that the 'dwell' is True and the same for 'toolchangez' parameter, if present then 'toolchange' will be assumed to be True, else False
- modified the extracut and multidepth parameters in Cncjob Tcl command like for dwell and toolchange
- added ability for Tcl commands to have optional arguments with None value (meaning missing value). This case should be treated for each Tcl command in execute() method
- fixed the Drillcncjob Tcl command by adding an custom self.options key "Tools_in_use" and build it's value, in case it does not exist, to make the toolchange command work
- middle mouse click on closable tabs will close them

30.12.2019

- Buffer sub-tool in Transform Tool: added the possibility to apply a factor effectively scaling the aperture size thus the copper features sizes
- in Transform Tool adjusted the GUI
- fixed some decimals issues in NCC Tool, Paint Tool and Excellon Editor (they were still using the hardcoded values)
- some small updates in the NCC Tool
- changes in the Preferences UI for NCC and Paint Tool in Tool Dia entry field
- fixed Tcl commands that use the overlap parameter to switch from fraction to percentage
- in Transform Tool made sure that the buffer sub-tool parameters are better explained in tooltips
- attempt to make TclCommand quit_flatcam work under Linux
- some fixes in the NCC Tcl command (using the bool() method on some params)
- another attempt to make TclCommand quit_flatcam work under Linux
- another attempt to make TclCommand quit_flatcam work under Linux - use signal to call a hard exit when in Linux
- TclCommand quit_flatcam work under Linux

29.12.2019

- the Apply button text in Preferences is now made red when changes were made and require to be applied
- the Gerber UI is built only once now so the process is lighter on CPU
- the Gerber apertures marking shapes storage is now built only once because the more are built the more sluggish is the interface
- added a new function called by shortcut key combo Ctrl+G when the current widget in Plot Area is an Code Editor. It will jump to the specified line in the text.
- fixed a small bug where the app tried to hide a label that I've removed previously
- in Paint Tool Preferences is allowed to add a list of initial tools separated by comma
- in Geometry Paint Tool fixed the Overlap rate to work between 0 and 99.9999%

28.12.2019

- more updates to the Preferences window and in some other parts of the GUI
- updated the translations (less Russian)
- fixed a minor issue that when saving a project with CNCJob objects, the variable that holds the origin of the CNCJob object was not saved in the project. Added to the serializable objects also the exc_cnc_tools dictionary 
- some changes in the File menu

28.12.2019

- updated all the translations files
- fixed the big mouse cursor in OpenGL(3D) graphic mode to get the set color
- fixed the cursor to have the set color and set cursor width in the Legacy(2D) graphic engine
- in Legacy(2D) graphic mode fixed the cursor toggle when the big cursor is activated
- in Legacy(2D) fixed big mouse cursor to snap to the grid
- RELEASE 8.991

27.12.2019

- updated the POT file and the translation files for German, Spanish and French languages
- fixed some typos

26.12.2019

- modified the ToolDB class and changed some strings
- Preferences classes now have access to the App attributes through app.setup_obj_classes() method
- moved app.setup_obj_classes() upper in the App.__init__()
- added a new Preferences setting allowing to modify the mouse cursor color
- remade the GUI in Preferences -> General grouping the settings in a more clear way
- made available the Jump To function in Excellon Editor
- added a clean_up() method in all the Editor Tools that need it, to be run when aborting using the ESC key
- fixed an error in the Gerber parser; it did not took into consideration the aperture size declared before the beginning of a Gerber region. Detected for Gerber files generated by KiCAD 5.x
- in Panelize Tool made sure that for Gerber objects if one of the apertures is without geometry then it is ignored
- further modifications in Preferences -> General GUI
- further modifications in Preferences -> General GUI - extended the changes
- in Legacy(2D) graphic engine made to work the mouse color change
- theme changing is no longer auto-reboot upon change; it require now to press a button
- cleaned the Preferences classes and added the signals and signal slots in those classes, removing them from the main app class
- each FlatCAM object found in Preferences has it's own set of controls for changing the colors
- added a set of gray icons to be used when the theme is complete dark (for now it is useful only for MacOS with dark theme because at the moment the app is not styled to dark UI except the plot area)

25.12.2019

- fixed an issue in old default file detection and in saving the factory defaults file
- in Preferences window removed the Import/Export Preferences buttons because they are redundant with the entries in the File -> Menu -> Backup. and added a button to Restore Defaults
- when in Basic mode the Tool type of the tool in the Geometry UI Tool Table after isolating a Gerber object is automatically selected as 'C1'
- let the multiprocessing Pool have as many processes as needed
- added a new Preferences setting allowing a custom mouse line width (to make it thicker or thinner)
- changed the extension of the Tool Database file to FlatDB for easy recognition (in the future double clicking such a file might import the new tools in the FC database)

24.12.2019

- edited some icons so they don't contain white background
- fixed an incorrect usage of object in the app.select_objects() method
- fixed a typo in ToolDB.on_tool_add()

23.12.2019

- some fixes in the Legacy(2D) graphic mode regarding the possibility of changing the color of the Gerber objects
- added a method to darken the outline color for Gerber objects when they have the color set
- when Printing as PDF Gerber objects now the rendered color is the print color
- speed up the plotting in OpenGL(3D) graphic mode
- speed up the color setting for Gerber object when using the OpenGL(3D) graphic mode
- setting color for Gerber objects work on a selection of Gerber objects
- ~~when the selection is changed in the Project Tree the selection shape on canvas is deleted~~
- if an object is selected on Project Tree and it does not have the selection shape drawn, first click on canvas over it will draw the selection shape 
- in Tool Transform added a new feature named 'Buffer'. For Geometry and Gerber objects will create (and replace) a geometry at a distance from the original geometry and for Excellon will adjust the Tool diameters
- solved issue #355 - when the tool diameter field in the Edit → Preferences → Geometry → Geometry General → Tools → Tool dia is only one the app failed to read it
- solved issue #356 - in Tools DB can not be added more than one tool if a translation is active 
- some changes related to the fact that the geometry default tool diameter value can be comma separated string of tool diameters

22.12.2019

- added a new option for the Gerber objects: on the project context menu now can be chosen a color for the selected Gerber object
- fixed issue in Gerber UI where a label was not hidden when in Basic mode
- added the color parameters of the objects to the serializable attributes
- fixed Gerber object color set for Legacy(2D) graphic engine; glitch on the OpenGL(3D) graphic engine
- fixed the above mentioned glitch in the OpenGL(3D) graphic engine when an Gerber object has been set with a color

21.12.2019

- fixed a typo in Distance Tool

20.12.2019

- fixed a rare issue in the generation of non-copper-region geometry started from the Gerber Object UI (selected tab)
- Print function is now printing a PDF file for a selection of objects in the colors from canvas 
- added an icon in the infobar that will show more clearly the status of the grid snapping
- in Geometry Object UI (selected tab) when a tool type is changed from no matter what to V-shape, the cut_z value is saved and when the tool type is changed back to something different than V-shape, this saved cut-z value is restored
- fixed re-cut length entry not staying disabled when the re-cut cb is not checked

19.12.2019

- in 2-Sided Tool added a way to calculate the bounding box values for a selection of objects, and also the centroid
- in 2-Sided Tool fixed the Reset Tool button handler to reset the bounds value too; changed a string
- added Preferences values for PDF margins when saving text in Code Editor as PDF
- when clicking Cancel in Preferences now the values are reverted to what they used to be before opening Preferences tab and start changing values
- starting to work to a general Print function; for now it will generate PDF files; currently it works only for one object not for a selection
- added shortcut key Ctrl+P for printing to PDF method

18.12.2019

- added new parameters to improve Gerber parsing
- small optimizations in the Preferences UI
- the Jump To function reference is now saving it's last used value
- added the ability to use the Jump To method in the Gerber Editor
- improved the loading of Config File by using the advanced code editor
- fixed a bug in the new feature 'extra buffering'
- fixed the creation of CNCJob objects out of multigeo Geometry objects (objects with multiple tools)
- optimized the NCC Tool

17.12.2019

- more optimizations in NCC Tool
- optimizations in Paint Tool
- maximum range for Cut Z is now zero to deal with the situation when using V-shape with tip-dia same value with cut width
- modified QValidator in FCDoubleSpinner() GUI element to allow entering the minus sign when the range maximum is set as 0.0; also for positive numbers allowed entering the symbol plus
- made sure that if in Gerber UI the isolation is made with a V-Shape tool then the tool type is automatically updated on the generated Geometry Object
- added ability to save the Source File as PDF (still have to adjust the page size)
- fixed the generate_from_geometry_2() method to use the default values in case the parameters are None
- added ability to save the Source File as PDF - fixed page size and added line breaks
- more mods to generate_from_geometry_2() method
- fixed bug saving the FlatCAM project saying the file is used by another application
- fixed issue #347 - a Gerber generated by Sprint Layout with copper pour ON will not have rendered the copper pour

16.12.2019

- in Geometry Editor added support for Jump To function such as that it works within the Editor Tools themselves. For now it works only in absolute jumps
- modified the Jump To method such that now allows relative jump from the current mouse location
- fixed the Defaults upgrade overwriting the new version number with the old one
- fixed issue with clear_polygon3() - the one who makes 'lines' and fixed the NCC Tool
- some small changes in the GeometryObject.on_tool_add() method
- made sure that in Geometry Editor the self.app.mouse attribute is updated with the current mouse position (x, y)
- updated the preprocessor files
- fixed the HPGL preprocessor
- fixed the CNCJob geometry created with HPGL preprocessor
- fixed GCode generated with HPGL preprocessor to output only integer coordinates
- fixed the HPGL2 import parsing for absolute linear movements
- fixed the line endings for setup_ubuntu.sh

15.12.2019

- fixed a bug that created a crash in special conditions; it's related to the QSettings in FlatCAMGui.py
- added a script to remove the bad profiles from resource pictures. From here: https://stackoverflow.com/questions/22745076/libpng-warning-iccp-known-incorrect-srgb-profile/43415650, link mentioned by @camellan (Andrey Kultyapov)
- prepared the application for usage of dark icons in case of using the dark theme
- updated the languages
- fixed a typo
- fixed layout on first launch of the app
- fixed some issues with the recent preparation for dark icons resource usage
- added a new preprocessor file contributed by Daniel Friderich and added fixes for it
- modified the export_gcode() method and the preprocessors such that the preprocessors now have the information if to include the gcode header
- updated all the translation PO files and the POT file
- RELEASE 8.99

14.12.2019

- finished the strings update in the Google-translated Spanish
- finished the strings update in the Google-translated French

13.12.2019

- HPGL2 import: added support for circles, arcs and 3-point arcs. Everything works only for absolute coordinates.
- removed the .plt extension from Gcode extensions
- some strings updated; update on the Romanian translate
- more strings updated; finished the Romanian translation update
- some work in updating the Spanish Google-translation
- small updates (Google Translate) in Russian and Brazilian-PT languages

12.12.2019

- finished the Calibration Tool
- changed the Scale Entry in Object UI to FCEntry() GUI element in order to allow expressions to be entered. E.g: 1/25.4
- some small changes in the Scale button handler in FlatCAMObj() class
- added option to save objects as PDF files in File -> Save menu
- optimized the GerberObject.clear_plot_apertures() method
- some changes in the ObjectUI and for the Geometry UI
- finished a very rough and limited HPGL2 file import 

11.12.2019

- started work in HPGL2 parser
- some more work in Calibration Tool

10.12.2019

- small changes in the Geometry UI
- now extracut option in the Geometry Object will recut as many points as many they are within the specified re-cut length
- if extracut_length is zero then the extracut will cut up until the first point in path no matter what the distance is
- in Gerber isolation, when selection mode is checked, now area selection works too
- in CNCJob UI, now the CNCJob objects made out of Excellon objects will display their CNC tools (drill bits)
- fixed a cumulative error when using the Tool Offset for Excellon objects
- added the display of the real depth of cut (cut z + offset_z) for CNC tools made out of an Excellon object
- for OpenGL graphic mode added a fit_view() execution on canvas initialization
- fixed Excellon scaling the UI values
- replaced the SpindleSpeed entry with a FCSpinner() GUI element; if speed is set to 0 it will amount to None

9.12.2019 

- updated the border for fit view on OpenGL graphic mode
- Calibration Tool - added preferences values
- Calibration Tool - more work on it
- reverted this change: "selected object in Project used to ask twice for UI build" because it will not build the UI when a tab is closed for Document object and the object is selected
- fixed issue after Geometry object edit; the GCode made from an edited object did not reflect the changes in the object
- in Object UI, the Scale FCDoubleSpinner will no longer work for Return key press due of issues of unwanted scaling on focusOut event
- in GeometryObject fixed the scale and offset methods to always process the self.solid_geometry
- Calibration Tool - finished the calibrated object creation method
- updated the POT file
- fixed an error in the German PO file
- updated the languages PO files
- some fixes on the app.jump_to() method
- made sure that the ToolFilm will not start saving a file if there are no objects loaded
- some fixes on the app.jump_to() method for the Legacy(2D) graphic mode

8.12.2019

- Calibrate Tool - rearranged the GUI
- in Geometry UI made sure that the Label that points to the Tool parameters show clearly that those parameters apply only for the selected tool
- fixed an small issue in Object UI
- small fixes: selected object in Project used to ask twice for UI build; if scale factor in Object UI is 1 do nothing as there is no point in scaling with a factor of 1
- in Geometry UI added a button that allow updating all the tools in the Tool Table with the current values in the UI form
- updated Tcl commands to make use of either 0 or False for False value or 1 or True for True in case of a parameter with type Bool

7.12.2019 

- renamed Calibrate Excellon Tool to a simpler Calibrate Tool
- Calibrate Tool - when generating verification GCode it will always load into an Editor from which it can be edited and/or saved. On save the editor will close.
- updated the CNCJob and Drillcncjob Tcl Commands to use 0 and 1 as values for the parameters that are stated as of bool type, beside the normal keywords of False and True
- Calibrate Tool - working on it

6.12.2019

- fixed the toggle_units() method so now the grid values are accurate to the decimal
- cleaned up the Excellon parser and fixed some bugs (old and new); Excellon parser has it's own convert_units() method no longer inheriting from Geometry
- in Excellon UI fixed bug that did not allow editing of the Offset Z parameter from the Tool table
- in Properties Tool added new information's for the tools in the CNCjob objects
- few bugs solved regarding the newly created empty objects
- changed everywhere the name "preprocessor" with "preprocessor"
- updated the preprocessor files in the toolchange section in order to avoid a graphical representation of travel lines glitch
- fixed a GUI glitch in the Excellon tool table
- added units to some of the parameters in the Properties Tool

5.12.2019 

- in NCC Tool, the new Geometry object that is created on copper clear now has the solid_geometry attribute where the geometry is stored not only in the obj.tools attribute
- Copper Thieving Tool - added units label for the pattern plated area
- Properties Tool - added a new parameter, the copper area which show the area of the copper features for the Gerber objects
- Copper Thieving Tool - added a default value for the mask clearance when generating pattern plating mask
- application wide change: introduced the precision parameters in Edit -> Preferences who will control how many decimals to use in the app parameters
- changed the FCDoubleSpinner, FCSpinner and FCEntry GUI elements to allow passing an alignment value: left, right or center (not yet available in the app)
- fixed the GUI of the Geometry Editor Tool Transform and adapted it to use the precision setting
- updated Gerber Editor to use the precision setting and the Gerber Editor Transform Tool to use the FCDoubleSpinner GUI element
- in Properties Tool added more information's regarding the Excellon tools, about travelled distance and job time; fixed issues when doing Properties on the CNCjob objects
- TODO: I need to solve the mess in units conversion: it's too convoluted 

4.12.2019 

- made sure that if an older preferences file is detected then there are no errors and only the parameters that are currently active are loaded; the factory defaults file is deleted and recreated in the new format
- in Preferences added a new button: 'Close' to close the Preferences window without saving
- fixed bug in FCSpinner and FCDoubleSpinner GUI elements, that are now the main GUI element in FlatCAM, that made partial selection difficult
- updated the Paint Tool in Geometry Editor to use the FCDoubleSpinner
- added the possibility for suffix presence on the FCSpinner and FCDoubleSpinner GUI Elements
- added the '%' symbol for overlap fields; I still need to divide the content by 100 to get the original (0 ... 1) value
- fixed the overlap parameter all over the app to reflect the change to percentage
- in Copper Thieving Tool added the display of the patterned plated area (approximate area) 
- Copper Thieving Tool - updated the way plated area is calculated making it a bit more precise but still it is a bit bigger than the actual area
- fixed the Copy Object function to copy also the source_file content
- Copper Thieving Tool - when the clearance value for the pattern plating mask is negative it will be applied to the origin soldermask too
- modified the GUI in all tools making the text of the buttons bold and adding a new button named Reset Tool which have to reset the tool GUI and variables (need to check all tools to see if happen)
- when the Tool tab is in focus, clicking on canvas will no longer change the focus to Project tab
- Copper Thieving Tool - when creating the pattern platting mask will make a new Gerber object with it
- small fix in the GUI layout in Gerber Editor

3.12.2019

- in Preferences added an Apply button which apply the modified preferences but does not save to a file, minimizing the file IO operations; Ctrl+S key combo does the Apply now.
- updated some of the default values to metric, values that were missed previously
- remade the Gerber Editor way to import an Gerber object into the editor in such a way to use the multiprocessing
- various small fixes
- fix for toggle grid lines updating canvas only after moving the mouse (hack, actually)
- some changes in the UI layout in Cutout Tool
- added some geometry parameters in Cutout Tool as a convenience, to be passed to the generated Geometry objects

2.12.2019

- fixed issue #343; updated the Image Tool
- improvements in Importing SVG as Gerber - added an automatic source generation (it is not infallible)
- a hack to import correctly the QRCode exported as SVG from FlatCAM
- added 3 new tcl commands: export dxf, export excellon and export gerber
- added a Cancel button in Tools DB when requesting to add a tool in the Geometry Tool Table
- modified the default values for the METRIC system; the app now starts in the METRIC units since the majority of the world use the METRIC units system
- small changes, updated the estimated release date
- Tool Copper Thieving - added pattern plating mask generation feature

28.11.2019

- small fixes in NCC Tool and in the GeometryObject class

27.11.2019

- in Tool Film added the page size and page orientation in case of saving the film as PDF file
- the application workspace has now a lot more options selectable in the Edit -> Preferences -> General -> GUI Preferences
- updated the drawing of the workspace such that the application overall start time is improved and after first turn on of the workspace, toggling it will have no performance penalty
- updated the workspace functions to work in Legacy(2D) graphic mode
- adjusted the selection color transparency for the Legacy(2D) graphic mode because it was too transparent for the fill

26.11.2019

- updated the Film Tool to allow exporting PDF and PNG file (besides the SVG file)

25.11.2019

- In Gerber isolation changed the UI
- in Gerber isolation added the option to selectively isolate only certain polygons
- made some optimizations in GerberObject.isolate() method
- updated the 'single' isolation of Gerber polygons to remove the polygon if clicked on it and it is already in the list of single polygons to be isolated
- clicking to add a polygon when doing Single type isolation will add a blue shape marking the selected polygon, second click will remove that shape
- fixed bugs in Paint Tool when painting single polygon
- in Gerber isolation added the option to selectively isolate only certain polygons - made it to work for Legacy(2D) graphic mode
- remade the Paint Tool - single polygon painting; now it can single paint a list of polygons that are clicked onto (right click will start the actual painting)

23.11.2019

- in Tool Fiducials added a new fiducial type: chess pattern
- work in Calibrate Excellon Tool
- fixed the line numbers in the TextPlainEdit to fit all digits of the line number; activated the line numbers for ScriptObject objects too
- line numbers in the TextPlainEdit for the selected line are bold
- made sure that the self.defaults dictionary is deepcopy-ed in the self.options dictionary
- made sure that the units are read from the self.defaults and not from the GUI
- added Robber Bar option to Copper Thieving Tool

22.11.2019

- Tool Fiducials - added GUI in Preferences and entries in self.defaults dict
- Tool Fiducials - updated the source_file object for the modified Gerber files
- working on adding line numbers to the TextPlainEdit
- GCode view now has line numbers
- solved a bug that made selection of objects on canvas impossible if there is an object of type ScriptObject or DocumentObject opened

21.11.2019

- Tool Fiducials - finished the part with adding copper fiducials: manual and auto
- Tool Fiducials - added choice of shapes: circular or non-standard cross
- Tool Fiducials - finished the work on adding soldermask openings
- Tool Fiducials - finished the tool
- updated requirements.txt and setup_ubuntu.sh files

20.11.2019

- Tool Fiducials - added the GUI and the shortcut key
- Tool Fiducials - updated the icon

19.11.2019

- removed the f-strings replacing them with the traditional string formatting due of not being supported by older versions of Python 3
- fixed some TclCommands: MillDrills and OpenGerber
- fixed bug in Tool Subtract that did not allow subtracting Gerber objects
- starting to work on Tool Fiducials - created the file

18.11.2019

- finished the Dots and Squares options in the Copper Thieving Tool
- working on the Lines option in Copper Thieving Tool
- finished the Lines option in the Copper Thieving Tool; still have to add threading to maximize performance
- finished Copper Thieving Tool improvements
- working on the Calibrate Excellon Tool - remade the UI

17.11.2019

- optimized the storage of the Gerber mark shapes by making them one layer only
- optimized the Distance Tool such that the distance utility geometry will be shown even when the mark shapes are plotted.
- updated the make_freezed.py file to make sure that all the required files are included
- updated the setup_ubuntu.sh to include the sudo command (courtesy of Krishna Torque on bitbucket)

16.11.2019

- fixed issue #341 that affected both preprocessors that have inlined feedrate: marlin and repetier. The used feedrate was the Feedrate X-Y and instead had to be Feedrate Z.

15.11.2019

- added all the recognized extensions to the save dialog filters; latest extension used will be preselected next time a save operation occur
- fixed issue #335. The FCDoubleSPinBox (and FCSpinBox) value was not used when the user entered data but just hovered away the mouse expecting the data to be already confirmed
- converted setup_ubuntu.sh to Linux line endings

14.11.2019

- made sure that the 'default' preprocessor file is always loaded first such that this name is always first in the GUI comboboxes
- added a class in GUIElements for a TextEdit box with line numbers and highlight

13.11.2019

- trying to improve the performance of View CNC Code command by using QPlainTextEdit; made the mods for it
- when using the Find function in the AppTextEditor and the result reach the bottom of the document, the next find will be the first in the document (before it defaulted to the beginning of the document)
- finished improving the show of text files in FlatCAM (CNC Code, Source files)
- fixed an issue in the FlatCAMObj.GerberObject.convert_units() which needed to be updated after changes elsewhere

12.11.2019

- added two new preprocessor files for ISEL CNC and for BERTA CNC
- clicking on a FCTable GUI element empty space will also clear the focus now

11.11.2019

- in Tools Database added a contextual menu to add/copy/delete tool; Ctrl+C, DEL keys work too; key T for adding a tool is now only partially working
- in Tools Database made the status bar messages show when adding/copying/deleting tools in DB
- changed all Except statements that were single to except Exception as recommended in some PEP
- renamed the Copper Fill Tool to Copper Thieving Tool as this is a more appropriate name; started to add ability for more types of copper thieving besides solid
- fixed some issues recently introduced in ParseSVG
- updated POT file
- fixed GUI in 2Sided Tool
- extending the Copper Thieving Tool - wip

9.11.2019

- fixed a new bug that did not allow to open the FlatCAM Preferences files by doubleclick in Windows
- added a new feature: Tools Database for Geometry objects; resolved issue #308
- added tooltips for the Tools Database table headers and buttons

8.11.2019

- updated the make file for frozen executable

7.11.2019

- added the '.ngc' file extension to the GCode Save file dialog filter
- made the 'M2' Gcode command footer optional, default is False (can be set using the TclCommand: set_sys cncjob_footer True)
- added a setting in Preferences to force the GCode output to have the Windows line-endings even for non-Windows OS's

6.11.2019

- the "CRTL+S" key combo when the Preferences Tab is in focus will save the Preferences instead of saving the Project
- fixed bug in the Paint Tool that did not allow choosing a Paint Method that was not Standard
- made sure that in the GeometryObject.merge() all the source data is deepcopy-ed in the final object
- the font color of the Preferences tab will change to red if settings are not saved and it will revert to default when saved
- fixed issue #333. The Geometry Editor Paint tool was not working and using it resulted in an error

5.11.2019

- added a new setting named 'Allow Machinist Unsafe Settings' that will allow the Travel Z and Cut Z to take both positive and negative values
- fixed some issues when editing a multigeo geometry

4.11.2019

- wip
- getting rid of all the Options GUI and related functions as it is no longer supported
- updated the UI in Geometry UI
- optimized the order of the defaults storage declaration and the update of the Preferences GUI from the defaults
- started to add a Tool Database

3.11.2019

- fixed the V-shape tool diameter calculation in NCC Tool
- in NCC Tool made the new tool dia (circular type) a parameter in Preferences
- fixed a small issue with clicking in a disabled FCDoubleSpinner or FCSpinner still doing a selection

30.10.2019

- converted SolderPaste Tool to usage of SpinBoxes; changed the SolderPaste Tool UI in Preferences too
- fixed a bug in SolderPaste Tool that did not allow to view the GCode

29.10.2019

- a bug fix in Geometry Object
- fixed some missing properties in Tool Calculators

28.10.2019

- in Tools: Paint, NCC and Copper Fill, when using the Area Selection, now the selected areas will stay drawn as markers until the user click RMB
- in legacy2D graphic engine, adding an utility geometry no longer draw the older ones, overwriting them
- fixed some issues in the Gerber Editor (Aperture add was double adding an aperture)
- converted Gerber Editor to usage of SpinBoxes
- working on the Calibrate Excellon Tool
- converted Excellon Editor to usage of SpinBoxes
- Calibrate Excellon Tool: working on self.calculate_factors() method

27.10.2019

- Copper Fill Tool: some PEP8 corrections

26.10.2019

- fixed an error in the FCDoubleSpinner class when FlatCAM is run on system with locale that use the comma as decimal separator

25.10.2019

- QRCode Tool: added ability to add negative QRCodes (perhaps they can be isolated on copper?); added a clear area surrounding the QRCode in case it is dropped on a copper pour (region); fixed the Gerber export
- QRCode Tool: all parameters are hard-coded for now
- small update
- fixed imports in all TclCommands
- fixed the requirements.txt and setup_ubuntu.sh files
- QRCode Tool: change the plot method parameter
- QRCode Tool: added ability to save the generated QRCode as SVG file or PNG file
- QRCode Tool: added the feature to save the PNG file with transparent background
- QRCode Tool: added GUI category in Preferences window
- QRCode Tool: shortcut key for this tool is now Alt+Q while PDF import Tool was relegated to Ctrl+Q combo key shortcut
- added a new FlatCAM Tool: Copper Fill Tool. It will pour copper into a Gerber filling all empty space with copper, at a clearance distance of the Gerber features
- Copper Fill Tool: added possibility to select between a bounding box rectangular or convex hull when the reference is the geometry of the source Gerber object
- Copper Fill Tool: cleanup on not regular tool exit
- Copper Fill Tool: added GUI category in Edit -> Preferences window
- QRCode Tool: added a selection limit parameter to control the selection shape vs utility geo

24.10.2019

- added some placeholder texts in the TextBoxes.
- working on QRCode Tool; added the utility geometry and initial functional layout
- working on QRCode Tool; finished adding the QRCode geometry to the selected Gerber object and also finished adding the 'follow' geometry needed when exporting the Gerber object as a Gerber file in addition to the 'solid' geometry in the obj.apertures
- working on QRCode Tool; finished offsetting the geometry both in apertures and in solid_geometry; updated the source_file of the source object

23.10.2019

- QRCode Tool - a SVG object is generated and plotted on screen having the QRCode data
- fixed an import error in Distance Tool
- fixed the Toggle Grid Lines functionality

22.10.2019

- working on the Calibrate Excellon Tool
- finished the GUI layout for the Calibrate Excellon Tool
- start working on QRCode Tool - not working yet
- start working on QRCode Tool - searching for alternatives

21.10.2019

- the context menu for the Tabs in notebook and PlotTabArea is launched now on right mouse click on tabs themselves
- fixed an error when trying to view the source file and there is no object selected
- updated the Objects menu signals so whenever an object is (de)selected in the Project Tab, it's state will reflect the (un)checked state of the actions in the Object menu
- fixed issue in Gerber Object UI of not updating the value of CutZ entry on TipDia or TipAngle entries change. Fixed issue #324

18.10.2019

- fixed a small bug in BETA status change
- updated the About FlatCAM window
- reverted change in tool dia being able to take only positive values in Gerber Object UI
- started to work to a new tool: Calibrate Excellon Tool
- solved the issue #329

18.10.2019

- finished the update on the Google translated Spanish translation.
- updated the new objects icons for Gerber, Geometry and Excellon
- small import problem fixed
- RELEASE 8.98

17.10.2019

- fixed a bug in milling holes due of a message wrongly formatted
- added an translator email address
- finished the update on German Google translation. Part of it was corrected by Jens Karstedt
- finished the update of the Romanian translation.
- finished the Objects menu by adding the ability of actions to be checked so they will show the selected status of the objects and by adding to actions to (de)select all objects
- fixed and optimized the click selection on canvas
- fixed Gerber parsing for very simple Gerber files that have only one Polygon but many LPC zones
- fixed SVG export; fix bug #327
- finished the update on French Google translation.

16.10.2019

- small update to Romanian translation files

15.10.2019

- adjusted the layout in NCC Tool
- fixed bug in Panelization Tool for which in case of Excellon objects, the panel kept a reference to the source object which created issues when moving or disabling/enabling the plots
- cleaned up the module imports throughout the app (the TclCommands are not yet verified)
- removed the styling on the comboboxes cellWidget's in the Tool Tables
- replaced some of the icons that did not looked Ok on the dark theme
- added a new toolbar button for the Copy object functionality
- changed the Panelize tool icon
- corrected some strings

14.10.2019

- modified the result highlight color in Check Rules Tool
- added the Check Rules Tool parameters to the unit conversion list
- converted more of the Preferences entries to FCDoubleSpinner and FCSpinner
- converted all ObjectUI entries to FCDoubleSpinner and FCSpinner
- updated the translation files (~ 89% translation level)
- changed the splash screen as it seems that FlatCAM beta will never be more than beta
- changed some of the signals from returnPressed to editingFinished due of now using the SpinBoxes
- fixed an issue that caused the impossibility to load a GCode file that contained the % symbol even when was loaded in a regular way from the File menu
- re-added the CNC tool diameter entry for the CNCjob object in Selected tab.FCSpinner
- since the CNCjob geometry creation is only useful for graphical purposes and have no impact on the GCode creation I have removed the cascaded union on the GCode geometry therefore speeding up the Gcode display by many factors (perhaps hundreds of times faster)
- added a secondary link in the bookmark manager
- fixed the bookmark manager order of bookmark links; first two links are always protected from deletion or drag-and-drop to other positions
- fixed a whole load of PyQT signal problems generated by recent changes to the usage of SpinBoxes; added a signal returnPressed for the FCSpinner and for FCDoubleSpinner
- fixed issue in Paint Tool where the first added tool was expected to have a float diameter but it was a string
- updated the translation files to the latest state in the app

13.10.2019

- fixed a bug in the Merge functions
- fixed the Export PNG function when using the 2D legacy graphic engine
- added a new capability to toggle the grid lines for both graphic engines: menu link in View and key shortcut combo Alt+G
- changed the grid colors for 3D graphic engine when in Dark mode
- enhanced the Tool Film adding the Film adjustments and added the GUI in Preferences
- set the GUI layout in Preferences for a new category named Tools 2
- added the Preferences for Check Rules Tool and for Optimal Tool and also updated the Film Tool to use the default settings in Preferences

12.10.2019

- fixed the Gerber Parser convert units unnecessary usage. The only units conversion should be done when creating the new object, after the parsing
- more fixes in Rules Check Tool
- optimized the Move Tool
- added support for key-based panning in 3D graphic engine. Moving the mouse wheel while pressing the CTRL key will pan up-down and while pressing SHIFT key will pan left-right
- fixed a bug in NCC Tool and start trying to make the App responsive while the NCC tool is run in a non-threaded way
- fixed a GUI bug with the QMenuBar recently introduced

11.10.2019

- added a Bookmark Manager and a Bookmark menu in the Help Menu
- added an initial support for rows drag and drop in FCTable in GUIElements; it crashes for CellWidgets for now, if CellWidgetsare in the table rows
- fixed some issues in the Bookmark Manager
- modified the Bookmark manager to be installed as a widget tab in Plot Area; fixed the drag & drop function for the table rows that have CellWidgets inside
- marked in gray color the rows in the Bookmark Manager table that will populate the BookMark menu
- made sure that only one instance of the BookmarkManager class is active at one time

10.10.2019

- fixed Tool Move to work only for objects that are selected but also plotted, therefore disabled objects will not be moved even if selected

9.10.2019

- updated the Rules Check Tool - solved some issues
- made FCDoubleSpinner to use either comma or dot as a decimal separator
- fixed the FCDoubleSpinner to only allow the amount of decimals already set with set_precision()
- fixed ToolPanelize to use FCDoubleSpinner in some places

8.10.2019

- modified the FCSpinner and FCDoubleSpinner GUI elements such that the wheel event will not change the values inside unless there is a focus in the lineedit of the SpinBox
- in Preferences General, Gerber, Geometry, Excellon, CNCJob sections made all the input fields of type SpinBox (where possible)
- updated the Distance Tool utility geometry color to adapt to the dark theme canvas
- Toggle Code Editor now works as expected even when the user is closing the Editor tab and not using the command Toggle Code Editor
- more changes in Preferences GUI, replacing the FCEntries with Spinners
- some small fixes in toggle units conversion
- small GUI changes

7.10.2019

- fixed an conflict in a signal usage that was triggered by Tool SolderPaste when a new project was created
- updated Optimal Tool to display both points coordinates that made a distance (and the minimum) not only the middle point (which is still the place where the jump happen)
- added a dark theme to FlatCAM (only for canvas). The selection is done in Edit -> Preferences -> General -> GUI Settings
- updated the .POT file and worked a bit in the romanian translation
- small changes: reduced the thickness of the axis in 3D mode from 3 pixels to 1 pixel
- made sure that is the text in the source file of a DocumentObject is HTML is loaded as such
- added inverted icons

6.10.2019

- remade the Mark area Tool in Gerber Editor to be able to clear the markings and also to delete the marked polygons (Gerber apertures)
- working in adding to the Optimal Tool the rest of the distances found in the Gerber and the locations associated; added GUI
- added display of the results for the Rules Check Tool in a formatted way
- made the Rules Check Tool document window Read Only
- made Excellon and Gerber classes from camlib into their own files in the flatcamParser folder
- moved the ApertureMacro class from camlib to ParseGerber file
- moved back the ApertureMacro class to camlib for now and made some import changes in the new ParseGerber and ParseExcellon classes
- some changes to the tests - perhaps I will try adding a few tests in the future
- changed the Jump To icon and reverted some changes to the parseGerber and ParseExcellon classes
- updated Tool Optimal with display of all distances (and locations of the middle point between where they happen) found in the Gerber Object

5.10.2019

- remade the Tool Calculators to use the QSpinBox in order to simplify the user interaction and remove possible errors
- remade: Tool Cutout, Tool 2Sided, Tool Image, Panelize Tool, NCC Tool, Paint Tool  to use the QSpinBox GUI elements
- optimized the Transformation Tool both in GUI and in functionality and replaced the entries with QSpinBox
- fixed an issue with the tool table context menu in Paint Tool
- made some changes in the GUI in Paint Tool, NCC Tool and SolderPaste Tool
- changed some of the icons; added attributions for icons source in the About FlatCAM window
- added a new tool in the Geometry Editor named Explode which is the opposite of Union Tool: it will explode the polygons into lines

4.10.2019

- updated the Film Tool and added the ability to generate Punched Positive films (holes in the pads) when a Gerber file is the film's source. The punch holes source can be either an Excellon file or the pads center
- optimized Rules Check Tool so it runs faster when doing Copper 2 Copper rule
- small GUI changes in Optimal Tool and in Film Tool
- some PEP8 corrections
- some code annotations to make it easier to navigate in the MainGUI.py
- fixed exit FullScreen with Escape key
- added a new menu category in the MenuBar named 'Objects'. It will hold the objects found in the Project tab. Useful when working in FullScreen
- disabled a log.debug in ObjectColection.get_by_name()
- added a Toggle Notebook button named 'NB' in the QMenBar which toggle the notebook
- in Gerber isolation section, the tool dia value is updated when changing from Circular to V-shape and reverse
- in Tool Film, when punching holes in a positive film, if the resulting object geometry is the same as the source object geometry, the film will not ge generated
- fixed a bug that when a Gerber object is edited and it has as solid_geometry a single Polygon, saving the result was failing due of len() function not working on a single Polygon
- added the Distance Tool, Distance Min Tool, Jump To and Set Origin functions to the Edit Toolbar

3.10.2019

- previously I've added the initial layout for the DocumentObject object
- added more editing features in the Selected Tab for the DocumentObject object

2.10.2019

- fixed bug in Geometry Editor that did not allow the copy of geometric elements
- created a new class that holds all the Code Editor functionality and integrated as a Editor in FlatCAM, the location is in flatcamEditors folder
- remade all the functions for view_source, scripts and view_code to use the new AppTextEditor class; now all the Code Editor tabs are being kept alive, before only one could be in an open state
- changed the name of the new object FlatCAMNotes to a more general one DocumentObject
- changed the way a new ScriptObject object is made, the method that is processing the Tcl commands when the Run button is clicked is moved to the FlatCAMObj.ScriptObject() class
- reused the Multiprocessing Pool declared in the App for the ToolRulesCheck() class
- adapted the Project context menu for the new types of FLatCAM objects
- modified the setup_recent_files to accommodate the new FlatCAM objects
- made sure that when an ScriptObject object is deleted, it's associated Tab is closed
- fixed the FlatCMAScript object saving when project is saved (loading a project with this script object is not working yet)
- fixed the FlatCMAScript object when loading it from a project

1.10.2019

- fixed the FCSpinner and FCDoubleSpinner GUI elements to select all on first click and deselect on second click in the Spinbox LineEdit
- for Gerber object in Selected Tab added ability to chose a V-Shape tool and therefore control the isolation better by adjusting the cut width of the isolation in function of the cut depth, tip width of the tool and the tip angle of the tool
- when in Gerber UI is selected the V-Shape tool, all those parameters (tip dia, tip angle, tool_type = 'V' and cut Z) are transferred to the generated Geometry and prefilled in the Geoemtry UI
- added a fix in the Gerber parser to work even when there is no information about zero suppression in the Gerber file
- added new settings in Edit -> Preferences -> Gerber for Gerber Units and Gerber Zeros to be used as defaults in case that those informations are missing from the Gerber file
- added new settings for the Gerber newly introduced feature to isolate with the V-Shape tools (tip dia, tip angle, tool_type and cut Z) in Edit -> Preferences -> Gerber Advanced
- made those settings just added for Gerber, to be updated on object creation
- added the Geo Tolerance parameter to those that are converted from MM to INCH
- added two new FlatCAM objects: ScriptObject and FlatCAMNotes

30.09.2019

- modified the Distance Tool such that the number of decimals all over the tool is set in one place by the self.decimals
- added a new tool named Minimum Distance Tool who will calculate the minimum distance between two objects; key shortcut: SHIFT + M
- finished the Minimum Distance Tool in case of using it at the object level (not in Editors)
- completed the Minimum Distance Tool by adding the usage in Editors
- made the Minimum Distance Tool more precise for the Excellon Editor since in the Excellon Editor the holes shape are represented as a cross line but in reality they should be evaluated as circles
- small change in the UI layout for Check Rules Tool by adding a new rule (Check trace size)
- changed a tooltip in Optimal Tool
- in Optimal Tool added display of how frequent that minimum distance is found
- in Tool Distance and Tool Minimal Distance made the entry fields read-only
- in Optimal Tool added the display of the locations where the minimum distance was detected
- added support to use Multi Processing (multi core usage, not simple threading) in Rules Check Tool
- in Rules Check Tool added the functionality for the following rules: Hole Size, Trace Size, Hole to Hole Clearance
- in Rules Check Tool added the functionality for Copper to Copper Clearance
- in Rules Check Tool added the functionality for Copper to Outline Clearance, Silk to Silk Clearance, Silk to Solder Mask Clearance, Silk to Outline Clearance, Minimum Solder Mask Sliver, Minimum Annular Ring
- fixes to cover all possible situations for the Minimum Annular Ring Rule in Rules Check Tool
- some fixes in Rules Check Tool and added a QSignal that is fired at the end of the job

29.09.2019

- work done for the GUI layout of the Rule Check Tool
- setup signals in the Rules Check Tool GUI
- changed the name of the Measurement Tool to Distance Tool. Moved it's location to the Edit Menu
- added Angle parameter which is continuously updated to the Distance Tool

28.09.2019

- changed the icon for Open Script and reused it for the Check Rules Tool
- added a new tool named "Optimal Tool" which will determine the minimum distance between the copper features for a Gerber object, in fact determining the maximum diameter for a isolation tool that can be used for a complete isolation
- fixed the ToolMeasurement geometry not being displayed
- fixed a bug in Excellon Editor that crashed the app when editing the first tool added automatically into a new black Excellon file
- made sure that if the big mouse cursor is selected, the utility geometry in Excellon Editor has a thicker line width (2 pixels now) so it is visible over the geometry of the mouse cursor
- fixed issue #319 where generating a CNCJob from a geometry made with NCC Tool made the app crash; also #328 which is the same
- replaced in FlatCAM Tools and in FLatCAMObj.py  and in Editors all references to hardcoded decimals in string formats for tools with a variable declared in the __init__()
- fixed a small bug that made app crash when the splash screen is disabled: it was trying to close it without being open

27.09.2019

- optimized the toggle axis command
- added possibility of using a big mouse cursor or a small mouse cursor. The big mouse cursor is made from 2 infinite lines. This was implemented for both graphic engines
- added ability to change the cursor size when the small mouse cursor is selected in Preferences -> General
- removed the line that remove the spaces from the path parameter in the Tcl commands that open something (Gerber, Gcode, Excellon)
- fixed issue with the old SysTray icon not hidden when the application is restarted programmatically
- if an object is edited but the result is not saved, the app will reload the edited object UI and set the Selected tab as active
- made the mouse cursor (big, small) change in real time for both graphic engines
- started to work on a new FlatCAM tool: Rules Check
- created the GUI for the Rule Check Tool
- if there are (x, y) coordinates in the clipboard, when launching the "Jump to" function, those coordinates will be preloaded in the Dialog box.
- when the combo SHIFT + LMB is executed there is no longer a deselection of objects
- when the "Jump to" function is called, the mouse cursor (if active) will be moved to the new position and the screen position labels will be updated accordingly


27.09.2019

- RELEASE FlatCAM 8.97

26.09.2019

- added a Copy All button in the Code Editor, clicking this button will copy all text in the editor to the clipboard
- added a 'Milling Type' radio button in Geometry Editor Preferences to contorl the type of geometry will be generated in the Geo Editor (for conventional milling or for the climb milling)
- added the functionality to allow climb/conventional milling selection for the geometry created in the Geometry Editor
- now any Geometry that is edited in Geometry editor will have coordinates ordered such that the resulting Gcode will allow the selected milling type in the 'Milling Type' radio button in Geometry Editor Preferences (which depends also of the spindle direction)
- some strings update
- French Google-translation at 100%
- German Google-translation update to 100%
- updated the other languages and the .POT file
- changed some strings (that should not have been included for translation) and updated language files and the .POT file
- fixed issue when rebooting from within in cx_freezed state (it issued a startup arg with the path to FlatCAM.exe but that triggered the last sys.exit(2) that I had in the App.args_at_startup())
- modified the make_win script for the presence of MatPlotLib

25.09.2019

- French translation at 33%
- fixed the 'Jump To' function to work in legacy graphic engine
- in legacy graphic engine fixed the mouse cursor shape when grid snapping is ON, such that it fits with the shape from the OpenGL graphic engine
- in legacy graphic engine fixed the axis toggle
- French Google-translation at 48%

24.09.2019

- fixed the fullscreen method to show the application window in fullscreen wherever the mouse pointer it is therefore on the screen we are working on; before it was showing always on the primary screen
- fixed setup_ubuntu.sh to include the matplotlib package required by the Legacy (2D) graphic engine
- in legacy graphic engine, fixed issue where immediately after changing the mouse cursor snapping the mouse cursor shape was not updated
- in legacy graphic engine, fixed issue where while zooming the mouse cursor shape was not updated
- in legacy graphic engine, fixed issue where immediately after panning finished the mouse cursor shape was not updated
- unfortunately the fix for issue where while zooming the mouse cursor shape was not updated braked something in way that Matplotlib work with PyQt5, therefore I removed it
- fixed a bug in legacy graphic engine: when doing the self.app.collection.delete_all() in new_project an app crash occurred
- implemented the Annotation change in CNCJob Selected Tab for the legacy graphic engine

23.09.2019

- in legacy graphic engine, fixed bug that made the old object disappear when a new object was loaded
- in legacy graphic engine, fixed bug that crashed the app when creating a new project
- in legacy graphic engine, fixed a bug that when deleting an object all objects where deleted
- added a new TclCommand named "set_origin" which will set the origin for all loaded objects to zero if the -auto True argument is used and to a certain x,y location if the format is: set_origin 5,7
- added a new TclCommand named "bounds" which will return a list of bounds values from a supplied list of objects names. For use in Tcl Scripts
- updated strings in the translations and the .POT file
- added the new keywords to the default keywords list
- fixed the FullScreen option not working for the 3D graphic engine (due bug of Qt5 when OpenGL window is fullscreen) by creating a sort of fullscreen
- added a final fix that allow full coverage of the screen in FullScreen in Windows and still the menus are working
- optimized the Gerber mark shapes display
- fixed a color format bug in Tool Move for 3D engine
- made sure that when the Tool Move is used on a Gerber file with mark shapes active, those mark shapes are deleted before the actual move
- in legacy graphic engine, fixed issue with Delete shortcut key trying to delete twice
- 26% in Google-translated French translation and updated some strings too

22.09.2019

- fixed zoom directions legacy graphic engine (previous commit)
- fixed display of MultiGeo geometries in legacy graphic engine
- fixed Paint tool to work in legacy graphic engine
- fixed CutOut Tool to work in legacy graphic engine
- fixed display of distance labels and code optimizations in ToolPaint and NCC Tool
- adjusted axis at startup for legacy graphic engine plotcanvas
- when the graphic engine is changed in Edit -> Preferences -> General -> App Preferences, the application will restart
- made hover shapes work in legacy graphic engine
- fixed bug in display of the apertures marked in the Aperture table found in the Gerber Selected tab and through this made it to also work with the legacy graphic engine
- fixed annotation in Mark Area Tool in Gerber Editor to work in legacy graphic engine
- fixed the MultiColor plot option Gerber selected tab to work in legacy graphic engine
- documented some methods in the ShapeCollectionLegacy class
- updated the files: setup_ubuntu.sh and requirements.txt
- some strings changed to be easier for translation
- updated the .POT file and the translation files
- updated and corrected the Romanian and Spanish translations
- updated the .PO files for the rest of the translations, they need to be filled in.
- fixed crash when trying to set a workspace in FlatCAM in the Legacy engine 2D mode by disabling this function for the case of 2D mode
- fixed exception when trying to Fit View (shortcut key 'V') with no object loaded, in legacy graphic engine

21.09.2019

- fixed Measuring Tool in legacy graphic engine
- fixed Gerber plotting in legacy graphic engine
- fixed Geometry plotting in legacy graphic engine
- fixed CNCJob and Excellon plotting in legacy graphic engine
- in legacy graphic engine fixed the travel vs cut lines in CNCJob objects
- final fix for key shortcuts with modifier in legacy graphic engine
- refactored some of the code in the legacy graphic engine
- fixed drawing of selection box when dragging mouse on screen and the selection shape drawing on the selected objects
- fixed the moving drawing shape in Tool Move in legacy graphic engine
- fixed moving geometry in Tool Measurement in legacy graphic engine
- fixed Geometry Editor to work in legacy graphic engine
- fixed Excellon Editor to work in legacy graphic engine
- fixed Gerber Editor to work in legacy graphic engine
- fixed NCC tool to work in legacy graphic engine

20.09.2019

- final fix for the --shellvar having spaces within the assigned value; now they are retained
- legacy graphic engine - made the mouse events work (click, release, doubleclick, dragging)
- legacy graphic engine - made the key events work (simple or with modifiers)
- legacy graphic engine - made the mouse cursor work (enabled/disabled, position report); snapping is not moving the cursor yet
- made the mouse cursor snap to the grid when grid snapping is active
- changed the axis color to the one used in the OpenGL graphic engine
- work on ShapeCollectionLegacy
- fixed mouse cursor to work for all objects
- fixed event signals to work in both graphic engines: 2D and 3D

19.09.2019

- made sure that if FlatCAM is registered with a file extension that it does not recognize it will exit
- added some fixes in the the file extension detection
- added some status messages for the Tcl script related methods
- made sure that optionally, when a script is run then it is also loaded into the code editor
- added control over the display of Sys Tray Icon in Edit -> Preferences -> General -> GUI Settings -> Sys Tray Icon checkbox
- updated some of the default values to more reasonable ones
- FlatCAM can be run in HEADLESS mode now. This mode can be selected by using the --headless=1 command line argument or by changing the line headless=False to True in config/configuration.txt file. In this mod the Sys Tray Icon menu will hold only the Run Scrip menu entry and Exit entry.
- added a new TclCommand named quit_flatcam which will ... quit FlatCAM from Tcl Shell or from a script
- fixed the command line argument --shellvar to work when there are spaces in the argument value
- fixed bug in Gerber editor that did not allow to display all shapes after it encountered one shape without 'solid' geometry
- fixed bug in Gerber Editor -> selection area handler where if some of the selected shapes did not had the 'solid' geometry will silently abort selection of further shapes
- added new control in Edit -> Preferences -> General -> Gui Preferences -> Activity Icon. Will select a GIF from a selection, the one used to show that FlatCAM is working.
- changed the script icon to a smaller one in the sys tray menu
- fixed bug with losing the visibility of toolbars if at first startup the user tries to change something in the Preferences before doing a first save of Preferences
- changed a bit the splash PNG file
- moved all the GUI Preferences classes into it's own file flatcamGUI.PreferencesUI.py
- changed the default method for Paint Tool to 'all'

18.09.2019

- added more functionality to the Extension registration with FLatCAM and added to the GUI in Edit -> Preferences -> Utilities
- fixed the parsing of the Manufacturing files when double clicking them and they are registered with FlatCAM
- fixed showing the GUI when some settings (maximized_GUI) are missing from QSettings
- added sys tray menu
- added possibility to edit the custom keywords used by the autocompleter (in Tcl Shell and in the Code Editor). It is done in the Edit -> Preferences -> Utilities
- added a new setting in Edit -> Preferences -> General -> GUI Settings -> Textbox Font which control the font on the Textbox GUI elements
- fixed issue with the sys tray icon not hiding after application close
- added option to run a script from the context menu of the sys tray icon. Changed the color of the sys tray icon to a green one so it will be visible on light and dark themes

17.09.2019

- added more programmers that contributed to FlatCAM over the years, in the "About FlatCAM" -> Programmers window
- fixed issue #315 where a script run with the --shellfile argument crashed the program if it contained a TclCommand New
- added messages in the Splash Screen when running FlatCAM with arguments at startup
- fixed issue #313 where TclCommand drillcncjob is spitting errors in Tcl Shell which should be ignored
- fixed an bug where the pywrapcp name from Google OR-Tools is not defined; fix issue #316
- if FlatCAM is started with the 'quit' or 'exit' as argument it will close immediately and it will close also another instance of FlatCAM that may be running
- added a new command line parameter for FlatCAM named '--shellvars' which can load a text file with variables for Tcl Shell in the format: one variable assignment per line and looking like: 'a=3' without quotes
- made --shellvars into --shellvar and make it only one list of commands passed to the Tcl. The list is separated by comma but without spaces. The variables are accessed in Tcl with the names shellvar_x where x is the index in the list of command comma separated values
- fixed an issue in the TclShell that generated an exception IndexError which crashed the software
- fixed the --shellvar and --shellfile FlatCAM arguments to work together but the --shellvar has precedence over --shellfile as it is most likely that whatever variable set by --shellvar will be used in the script file run by --shellfile

16.09.2019

- modified the TclCommand New so it will no longer close all tabs when called (it closed the Code Editor tab which may have been holding the code that run)
- fixed the App.on_view_source() method for CNCJob objects: the Gcode will now contain the Prepend and Append code from the Edit -> Preferences -> CNCJob -> CNCJob Options
- added a new parameter named 'muted' for the TclCommands: cncjob, drillcncjob and write_gcode. Setting it as -muted 1 will disable the error reporting in TCL Shell
- some GUI optimizations
- more GUI optimizations related to being part of the Advanced category or not
- added possibility to change the positive SVG exported file color in Tool Film
- fixed some issues recently introduced in the TclCommands CNCJob, DrillCNCJob and write_gcode; changed some parameters names
- fixed issue in the Laser preprocessor where the laser was turned on as soon as the GCode started creating an unwanted cut up until the job start
- added new links in Menu -> Help (Excellon, Gerber specifications and a Report Bug)
- made the splashscreen to be showed on the current monitor on systems with multiple monitors
- added a new entry in Menu -> View -> Redraw All which is doing what the name says: redraw all loaded objects
- fixed issue where in TCl Shell the Windows paths were not understood due of backslash symbol understood as escape symbol instead of path separator
- made sure that in for the TclCommand cncjob and for the drillcncjob if one of the args is stated but no value then the value used will be the default one
- made available the TSA algorithm for drill path optimization when the used OS is 64bit. When used OS is 32bit the only available algorithm is TSA

15.09.2019

- refactored GeometryObject.mtool_gen_cncjob() method
- fixed the TclCommandCncjob to work for multigeometry Geometry objects; still I had to fix the list of tools parameter, right now I am setting it to an empty list
- update the Tcl Command isolate to be able to isolate exteriors, interiors besides the full isolation, using the iso_type parameter
- fixed issue in ToolPaint that could not allow area painting of a geometry that was a list and not a Geometric element (polygon or MultiPolygon)
- fixed UI showing before the initialization of FlatCAM is finished when the last state of GUI was maximized
- finished updating the TclCommand cncjob to work for multi-geo Geometry objects with the parameters from the args
- fixed the TclCommand cncjob to use the -outname parameter
- added some more keywords in the data_model for auto-completer
- fixed isolate TclCommand to use correctly the -outname parameter
- added possibility to see the GCode when right clicking on the Project tab on a CNCJob object and then clicking View Source
- added a new TclCommand named PlotObjects which will plot a list of FlatCAM objects
- made that after opening an object in FlatCAM it is not automatically plotted. If the user wants to plot it can use the TclCommands PlotAll or PlotObjects
- modified the TclCommands so that open files do not plot the opened files automatically
- made all TclCommands not to be plotted automatically
- made sure that all TclCommands are not threaded
- added new TclCommands: NewExcellon, NewGerber
- fixed the TclCommand open_project
- added the outname parameter (and established an default name when outname not used) for the AlignDrillGrid and AlignDrill TclCommands
- fixed Scripts repeating multiple time when the Code Editor is used. This repetition was correlated with multiple openings of the Code Editor window (especially after an error)
- added the autocomplete keywords that can be changed to the defaults dictionary

14.09.2019

- more string changes
- updated translation files
- fixed a small bug
- minor changes in the Code Editor GUI
- minor changes in the 'FlatCAM About' GUI
- added a new shortcut key F5 for doing the 'Plot All'
- updated the google-translated Spanish translation strings
- fixed the layouts to include toolbars breaks where it was needed
- whenever the user changes the Excellon format values for loading files, the Export Excellon Format values will be updated
- made optional the behavior of Excellon Export values following the values in the Excellon Loading section
- updated the translations (except RU) and the POT file
- added to the NonCopperClear.clear_copper() a parameter to be able to run it non-threaded

13.09.2019

- added control for simplification when loading a Gerber file in Preferences -> Gerber -> Gerber General -> Simplify
- added some messages for the Edit -> Conversions -> Join methods() to make sure that there are at least 2 objects selected for join
- added a grid layout in on_about()
- upgraded the Script Editor to be able to run Tcl commands in batches
- added some ToolTips for the buttons in the Code Editor
- converted the big strings that hold the shortcut keys descriptions to smaller string to make translations easier
- fixed some of the strings that were left in the old way
- updated the POT file
- updated Romanian language partially
- added a new way to handle scripts with repeating Tcl commands
- added new buttons in the Tools toolbar for running, opening and adding new scripts
- finished the Romanian translation update and updated the POT file

12.09.2019

- small changes in the TclCommands: MillDrills, MillSlots, DrillCNCJob: the new parameter for tolerance is now named: diatol
- cleaned up the 'About FlatCAM' window, started to give credits for the translation team
- started to add an application splash screen
- now, Excellon and Gerber edited objects will have the source_code updated and ready to be saved
- the edited Gerber (or Excellon) object now is kept in the app after editing and the edited object is a new object
- added a message to the splash screen
- remade the splash screen to show multiple messages on app initialization
- added a new splash image
- added a control in Preferences -> General -> GUI Settings -> Splash Screen that control if the splash screen is shown at startup

11.09.2019

- added the Gerber code as source for the panelized object in Panelize Tool
- whenever a Gerber file is deleted, the mark_shapes objects are deleted also
- made faster the Gerber parser for the case of having a not valid geometry when loading a Gerber file without buffering
- updated code in self.on_view_source() to make it more responsive
- fixed the TclCommand MillHoles
- changed the name of TclCommand MillHoles to MillDrills and added a new TclCommand named MillSlots
- modified the MillDrills and MillSlots TclCommands to accept as parameter a list of tool diameters to be milled instead of tool indexes
- fixed issue #302 where a copied object lost all the tools
- modified the TclCommand DrillCncJob to have as parameter a list of tool diameters to be drilled instead of tool indexes
- updated the Spanish translation (Google-translation)
- added a new parameter in the TclCommands: DrillCNCJob, MillDrills, MillSlots named tol (from tolerance). If the diameters of the milled (drilled) dias are within the tolerance specified of the diameters in the Excellon object than those diameters will be processed. This is to help account for rounding errors when having units conversion

10.09.2019

- made isolation threaded
- fixed a small typo in TclCommandCopperCLear
- made changing the Plot kind in CNCJob selected tab, threaded
- fixed an object used before declaring it in NCC Tool - Area option
- added progress for the generation of Isolation geometry
- added progress and possibility of graceful exit in Panel Tool
- added graceful exit possibility when creating Isolation
- changed the workers thread priority back to Normal
- when disabling plots, if the selection shape is visible, it will be deleted
- small changes in Tool Panel (eliminating some deepcopy() calls)
- made sure that all the progress counters count to 100%

9.09.2019

- changed the triangulation type in VisPyVisuals for ShapeCollectionVisual class
- added a setting in Preferences -> Gerber -> Gerber General named Buffering. If set to 'no' the Gerber objects load a lot more faster (perhaps 10 times faster than when set to 'full') but the visual look is not so great as all the aperture polygons can be seen
- added for NCC Tool and Paint Tool a setting in the Preferences -> Tools --> (NCC Tool/ Paint Tool) that can set a progressive plotting (plot shapes as they are processed)
- some fixes in Paint Tool when done over the Gerber objects in case that the progressive plotting is selected
- some fixes in Gerber isolation in case that the progressive plotting is selected; added a 'Buffer solid geometry' button shown only when progressive plotting for Gerber object is selected. It will buffer the entire geometry of the object and plot it, in a threaded way.
- modified FlatCAMObj.py file to the new string format that will allow easier translations
- modified camlib.py, FlatCAMAPp.py and ObjectCollection.py files to the new string format that will allow easier translations
- updated the POT file and the German language
- fixed issue when loading unbuffered a Gerber file that has negative regions
- fixed Panelize Tool to save the aperture geometries into the panel apertures. Also made the tool faster by removing the buffering at the end of the job
- modified FlatCAMEditor's files to the new string format that will allow easier translations
- updated POT file and the Romanian translation

8.09.2019

- added some documentation strings for methods in FlatCAMApp.App class
- removed some @pyqtSlot() decorators as they interfere with the current way the program works

7.09.2019

- added a method to gracefully exit from threaded tasks and implemented it for the NCC Tool and for the Paint Tool
- modified the on_about() function to reflect the reality in 2019 - FlatCAM it is an Open Source contributed software
- remade the handlers for the Enable/Disable Project Tree context menu so they are threaded and activity is shown in the lower right corner of the main window
- added to GUI new options for the Gerber object related to area subtraction
- added new feature in the Gerber object isolation allowing for the isolation to avoid an area defined by another object (Gerber or Geometry)
- all transformation functions show now the progress (rotate, mirror, scale, offset, skew)
- made threaded the Offset and Scale operations found in the Selected tab of the object
- corrected some issues and made Move Tool to show correctly when it is plotting and when it is offsetting the objects position
- made Set Origin feature, threaded
- updated German language translation files
- separated the Plotting thread from the transformations threads

6.09.2019

- remade visibility threaded
- reimplemented the thread listening for new FlatCAM process starting with args so it is no longer subclassed but using the moveToThread function
- added percentage display for work done in NCC Tool
- added percentage display for work done in Paint Tool
- some fixes and prepared the activity monitor area to receive updated texts
- added progress display in status bar for generating CNCJob from Excellon objects
- added progress display in status bar for generating CNCJob from Geometry objects
- modified all the FlatCAM tools strings to the new format in which the status is no longer included in the translated strings to make it easier for the future translations
- more customization for the progress display in case of NCC Tool, Paint Tool and for the Gcode generation
- updated POT file with the new strings
- made the objects offset (therefore the Move Tool) show progress display

5.09.2019

- fixed issue with loading files at start-up
- fixed issue with generating bounding box geometry for CNCJob objects
- added some more infobar messages and log.debug
- increased the priority for the worker tasks
- hidden the configuration for G91 coordinates due of deciding to leave this development for another time; it require too much refactoring
- added some messages for the G-code generation so the user know in which stage the process is

4.09.2019

- started to work on support for G91 in Gcode (relative coordinates)
- added support for G91 coordinates
- working in plotting the CNCjob generated with G91 coordinates

3.09.2019

- in NCC tool there is now a depth of cut parameter named 'Cut Z' which will dictate how deep the tool will enter into the PCB material
- in NCC tool added possibility to choose between the type of tools to be used and when V-shape is used then the tool diameter is calculated from the desired depth of cut and from the V-tip parameters
- small changes in NCC tool regarding the usage of the V-shape tool
- fixed the isolation distance in NCC Tool for the tools with iso_op type
- in NCC Tool now the Area adding is continuous until RMB is clicked (no key modifier is needed anymore)
- fixed German language translation
- in NCC Tool added a warning in case there are isolation tools and if those isolation's are interrupted by an area or a box
- in Paint Tool made that the area selection is repeated until RMB click
- in Paint Tool and NCC Tool fixed the RMB click detection when Area selection is used
- finished the work on file extensions registration with FlatCAM. If the file extensions are deleted in the Preferences -> File Associations then those extensions are unregistered with FlatCAM
- fixed bug in NCC Tools and in SolderPaste Tool if in Edit -> Preferences only one tool is entered
- fixed bug in camblib.clear_polygon3() which caused that some copper clearing / paintings were not complete (some polygons were not processed) when the Straight Lines method was used
- some changes in NCC Tools regarding of the clearing itself

2.09.2019

- fixed issue in NCC Tool when using area option
- added formatting for some strings in the app strings, making the future translations easier
- made changes in the Excellon Tools Table to make it more clear that the tools are selected in the # column and not in the Plot column
- in Excellon and Gerber Selected tab made the Plot (mark) columns not selectable
- some ToolTips were modified
- in Properties Tool made threaded the calculation of convex_hull area and also made it to work for multi-geo objects
- in NCC tool the type of tool that is used is transferred to the Geometry object
- in NCC tool the type of isolation done with the tools selected as isolation tools can now be selected and it has also an Edit -> Preferences entry
- in Properties Tool fixed the dimensions calculations (length, width, area) to work for multi-geo objects

1.09.2019

- fixed open handlers
- fixed issue in NCC Tool where the tool table context menu could be installed multiple times
- added new ability to create simple isolation's in the NCC Tool
- fixed an issue when multi depth step is larger than the depth of cut

27.08.2019

- made FlatCAM so that whenever an associated file is double clicked, if there is an opened instance of FlatCAM, the file will be opened in the first instance without launching a new instance of FlatCAM. If FlatCAM is launched again it will spawn a new process (hopefully it will work when freezed).

26.08.2019

- added support for file associations with FlatCAM, for Windows

25.08.2019

- initial add of a new Tcl Command named CopperClear
- remade the NCC Tool in preparation for the newly added TclCommand CopperClear
- finished adding the TclCommandCopperClear that can be called with alias: 'ncc'
- added new capability in NCC Tool when the reference object is of Gerber type and fixed some newly introduced errors
- fixed issue #298. The changes in preprocessors done in Preferences dis not update the object UI layout as it was supposed to. The selection of Marlin postproc. did not unhidden the Feedrate Rapids entry.
- fixed minor issues
- fixed Tcl Command AddPolygon, AddPolyline
- fixed Tcl Command CncJob
- fixed crash due of Properties Tool trying to have a convex hull area on FlatCAMCNCJob objects which is not possible due of their nature
- modified Tcl Command SubtractRectangle
- fixed and modernized the Tcl Command Scale to be able to scale on X axis or on Y axis or on both and having as scale reference either the (0, 0) point or the minimum point of the bounding box or the center of the bounding box.
- fixed and modernized the Tcl Command Skew

24.08.2019

- modified CutOut Tool so now the manual gaps adding will continue until the user is clicking the RMB
- added ability to turn on/off the grid snapping and to jump to a location while in CutOut Tool manual gap adding action
- made PlotCanvas class inherit from VisPy Canvas instead of creating an instance of it (work of JP)
- fixed selection by dragging a selection shape in Geometry Editor
- modified the Paint Tool. Now the Single Polygon and Area/Reference Object painting works with multiple tools too. The tools have to be selected in the Tool Table.
- remade the TclCommand Paint to work in the new configuration of the the app (the painting functions are now in their own tool, Paint Tool)
- fixed a bug in the Properties Tool
- added a new TcL Command named Nregions who generate non-copper regions
- added a new TclCommand named Bbox who generate a bounding box.

23.08.2019

- in Tool Cutout for the manual gaps, right mouse button click will exit from the action of adding gaps
- in Tool Cutout tool I've added the possibility to create a cutout without bridge gaps; added the 'None' option in the Gaps combobox
- in NCC Tool added ability to add multiple zones to clear when Area option is checked and the modifier key is pressed (either CTRL or SHIFT as set in Preferences). Right click of the mouse is an additional way to finish the job.
- fixed a bug in Excellon Editor that made that the selection of drills is always cumulative
- in Paint Tool added ability to add multiple zones to paint when Area option is checked and the modifier key is pressed (either CTRL or SHIFT as set in Preferences). Right click of the mouse is an additional way to finish the job.
- in Paint Tool and NCC Tool, for the Area option, now mouse panning is allowed while adding areas to process
- for all the FlatCAM tools launched from toolbar the behavior is modified: first click it will launch the tool; second click: if the Tool tab has focus it will close the tool but if another tab is selected, the tool will have focus
- modified the NCC Tool and Paint Tool to work multiple times after first launch
- fixed the issue with GUI entries content being deselected on right click in the box in order to copy the value
- some changes in GUI tooltips
- modified the way key modifiers are detected in Gerber Editor Selection class and in Excellon Editor Selection class
- updated the translations
- fixed aperture move in Gerber Editor
- fixed drills/slots move in Excellon Editor
- RELEASE 8.96

22.08.2019

- added ability to turn ON/OFF the detachable capability of the tabs in Notebook through a context menu activated by right mouse button click on the Notebook header
- added ability to turn ON/OFF the detachable capability of the tabs in Plot Tab Area through a context menu activated by right mouse button click on the Notebook header
- added possibility to turn application portable from the Edit -> Preferences -> General -> App. Preferences -> Portable checkbox
- moved the canvas setup into it's own function and called it in the init() function
- fixed the Buffer Tool in Geometry Editor; made the Buffer entry field a QDoubleSpinner and set the lower limit to zero.
- fixed Tool Cutout so when the target Gerber is a single Polygon then the created manual geometry will follow the shape if shape is freeform
- fixed TclCommandFollow command; an older function name was used who yielded wrong results
- in Tool Cutout for the manual gaps, now the moving geometry that cuts gaps will orient itself to fit the angle of the cutout geometry

21.08.2019

- added feature in Paint Tool allowing the painting to be done on Gerber objects
- added feature in Paint Tool to set how (and if) the tools are sorted
- added Edit -> Preferences GUI entries for the above just added features
- added new entry in Properties Tool which is the calculated Convex Hull Area (should give a more precise area for the irregular shapes than the box area)
- added some more strings in Properties Tool for the translation
- in NCC Tool added area selection feature
- fixed bug in Excellon parser for the Excellon files that do not put the type of zero suppression they use in the file (like DipTrace eCAD)
- fixed some issues introduced in NCC Tool

20.08.2019

- added ability to do copper clearing through NCC Tool on Geometry objects
- replaced the layout from Grid to Form for the Reference objects comboboxes in Paint Tool and in NCC Tool

19.08.2019

- updated the Edit -> Preferences to include also the Gerber Editor complete Preferences
- started to update the app strings to make it easier for future translations
- fixed the POT file and the German translation
- some mods in the Tool Sub
- fixed bug in Tool Sub that created issues when toggling visibility of the plots
- fixed the Spanish, Brazilian Portuguese and Romanian translations

18.08.2019

- made the exported preferences formatted therefore more easily read
- projects at startup don't work in another thread so there is no multithreading if I want to double click an project and to load it
- added messages in the application window title which show the progress in loading a project (which is not thread-safe therefore keeping the app from fully initialize until finished)
- in NCC Tool added a new parameter (radio button) that offer the choice on the order of the tools both in tools table and in execution of engraving; added as a parameter also in Edit -> Preferences -> Tools -> NCC Tool
- added possibility to drag & drop FlatCAM config files (*.FlatConfig) into the canvas to be opened into the application
- added GUI in Paint tool in beginning to add Paint by external reference object 
- finished adding in Paint Tool the usage of an external object to set the extent of th area painted. For simple shapes (single Polygon) the shape can be anything, for the rest will be a convex hull of the reference object
- modified NCC tool so for simple objects (single Polygon) the external object used as reference can have any shape, for the other types of objects the copper cleared area will be the convex hull of the reference object
- modified the strings of the app wherever they contained the char seq <b> </b> so it is not included in the translated string
- updated the translation files for the modified strings (and for the newly added strings)
- added ability to lock toolbars within the context menu that is popped up on any toolbars right mouse click. The value is saved in QSettings and it is persistent between application startup's.

17.08.2019

- added estimated time of routing for the CNCJob and added travelled distance parameter for geometry, too
- fixed error when creating CNCJob due of having the annotations disabled from preferences but the plot2() function from camlib.CNCJob class still performed operations who yielded TypeError exceptions
- coded a more accurate way to estimate the job time in CNCJob, taking into consideration if there is a usage of multi depth which generate more passes
- another fix (final one) for the Exception generated by the annotations set not to show in Preferences
- updated translations and changed version
- fixed installer issue for the x64 version due of the used CX_FREEZE python package which was in unofficial version (obviously not ready to be used)
- fixed bug in Geometry Editor, in disconnect_canvas_event_handlers() where I left some part of code without adding a try - except block which was required
- moved the initialization of the FlatCAM editors after a read of the default values. If I don't do this then only at the first start of the application the Editors are not functional as the Editor objects are most likely destroyed
- fixed bug in FlatCAM editors that caused the shapes to be drawn without resolution when the app units where INCH
- modified the transformation functions in all classes in camlib.py and FlatCAMObj.py to work with empty geometries
- RELEASE 8.95

17.08.2019

- updated the translations for the new strings
- RELEASE 8.94

16.08.2019

- working in Excellon Editor to Tool Resize to consider the slots, too
- fixed a weird error that created a crash in the following scenario: create a new excellon, edit it, add some drills/slots, delete it without saving, create a new excellon, try to edit and a crash is issued due of a wrapped C++ error
- fixed bug selection in Excellon editor that caused not to select the corresponding row (tool dia) in the tool table when a selection rectangle selected an even number of geometric elements
- updated the default values to more convenient ones
- remade the enable/disable plots functions to work only where it needs to (no sense in disabling a plot already disabled)
- made sure that if multi depth is choosed when creating GCode then if the multidepth is more than the depth of cut only one cut is made (to the depth of cut)
- each CNCJob object has now it's own text_collection for the annotations which allow for the individual enabling and disabling of the annotations
- added new menu category in File -> Backup with two menu entries that duplicate the functions of the export/import preferences buttons from the bottom of the Preferences window
- in Excellon Editor fixed the display of the number of slots in the Tool Table after the resize done with the Resize tool
- in Excellon Editor -> Resize tool, made sure that when the slot is resized, it's length remain the same, because the tool should influence only the 'thickness' of the slot. Since I don't know anything but the geometry and tool diameters (old and new), this is only an approximation and computationally intensive
- in Excellon Editor -> remade the Tool edit made by editing the diameter values in the Tools Table to work for slots too
- In Excellon Editor -> fixed bug that caused incorrect display of the relative coordinates in the status bar

15.08.2019

- added Edit -> Preferences GUI and storage for the Excellon Editor Add Slots
- added a confirmation message for objects delete and a setting to activate it in Edit -> Preferences -> Global
- merged pull request from Mike Smith which fix an application crash when attempting to open a not-a-FlatCAM-project file as project
- merged pull request from Mike Smith that add support for a new SVG element: <use>
- stored inside FlatCAM app the VisPy data files and at the first start the application will try to copy those files to the APPDATA (roaming) folder in case of running under Windows OS
- created a configuration file in the root/config/configuration.txt with a configuration line for portability. Set portable to True to run the app as portable
- working on the Slots Array in Excellon Editor - building the GUI
- added a failsafe path to the source folder from which to copy the VisPy data
- fixed the GUI for Slot Arrays in Excellon Editor
- finished the Slot Array tool in Excellon Editor
- added the key shortcut handlers for Add Slot and Add Slot Array tools in Excellon Editor
- started to work on the Resize tool for the case of Excellon slots in Excellon Editor
- final fix for the VisPy data files; the defaults files are saved to the Config folder when the app is set to be portable
- added the Slot Type parameter for exporting Excellon in Edit -> Preferences -> Excellon -> Export Excellon. Now the Excellon object can be exported also with drilled slot command G85
- fixed bug in Excellon export when there are no zero suppression (coordinates with decimals)

14.08.2019

- fixed the loading of Excellon with slots and the saving of edited Excellon object in regard of slots, in Excellon Editor
- fixed the Delete tool, Select tool in Excellon Editor to work for Slots too
- changes in the way the edited Excellon with added slots is saved
- added more icons and cursor in Excellon Editor for Slots related functions
- in Excellon Editor fixed the selection issue which in a certain step created a failure in the Copy and Move tools.
- in Excellon Editor fixed the selection with key modifier pressed
- edited the mouse cursors and saved them without included thumbnail in a bid to remove some CRC warnings made by libpng

13.08.2019

- added new option in ToolSub: the ability to close (or not) the resulting paths when using tool on Geometry objects. Added also a new category in the Edit -> Preferences -> Tools, the Substractor Tool Options
- some PEP8 changes in FlatCAMApp.py
- added new settings in Edit -> Preferences -> General for Notebook Font size (set font size for the items in Project Tree and for text in Selected Tab) and for canvas Axis font size. The values are stored in QSettings.
- updated translations
- fixed a bug in FCDoubleSpinner GUI element
- added a new parameter in NCC tool named offset. If the offset is used then the copper clearing will finish to a set distance of the copper features
- fixed bugs in Geometry Editor
- added protection's against the 'bowtie' geometries for Subtract Tool in Geometry Editor
- added all the tools from Geometry Editor to the the contextual menu
- fixed bug in Add Text Tool in Geometry Editor that gave error when clicking to place text without having text in the box
- added all the tools from Gerber Editor to the the contextual menu
- added the menu entry "Edit" in the Project contextual menu for Gerber objects
- started to work in adding slots and slots array in Excellon Editor
- in SlotAdd finished the utility geometry and the GUI for it

12.08.2019

- done regression to solve the bug with multiple passes cutting from the copper features (I should remember not to make mods here)
- if 'combine' is checked in Gerber isolation but there is only one pass, the resulting geometry will still be single geo
- the 'passes' entry was changed to a IntSpinner so it will allow passes to be entered only in range (1, 999) - it will not allow entry of 0 which may create some issues
- improved the GerberObject.isolate() function to work for geometry in the form of list and also in case that the elements of the list are LinearRings (like when doing the Exterior Isolation)
- in NCC Tool made sure that at each run the old objects are deleted
- fixed bug in camlib.Gerber.parse_lines() Gerber parser where for Allegro Gerber files the Gerber units were incorrectly detected
- improved Mark Area Tool in Gerber Editor such that at each launch the previous markings are deleted

11.08.2019

- small changes regarding the Project Title
- trying to fix reported bugs
- made sure that the annotations are deleted when the object that contain them is deleted
- fixed issue where the annotations for all the CNCJob objects are toggled together whenever the ones for an single object are toggled
- optimizations in GeoEditor
- updated translations

10.08.2019

- added new feature in NCC Tool: now another object can be used as reference for the area extent to be cleared of copper
- fixed issue in the latest feature in NCC Tool: now it works also with reference objects made out of LineStrings (tool 'Path' in Geometry Editor)
- translation files updated for the new strings (Google Translate)
- RELEASE 8.93

9.08.2019

- added Exception handing for the case when the user is trying to save & overwrite a file already opened in another file
- finished added 'Area' type of Paint in Paint Tool
- fixed bug that created a choppy geometry for CNCJob when working in INCH
- fixed bug that did not asked the user to save the preferences after importing a new set of preferences, after the user is trying to close the Preferences tab window

7.08.2019

- replaced setFixedWidth calls with setMinimumWidth
- recoded the camlib.Geometry.isolation_geometry() function
- started to work on Paint Area in Paint Tool

6.08.2019

- fixed bug that crashed the app after creating a new geometry, if a new object is loaded and the new geometry is deleted and then trying to select the just loaded new object
- made some GUI elements in Edit -> Preferences to have a minimum width as opposed to the previous fixed one
- fixed issue in the isolation function, if the isolation can't be done there will be generated no Geometry object 
- some minor UI changes
- strings added and translations updated

5.08.2019

- made sure that if using an negative Gerber isolation diameter, the resulting Geometry object will use a tool with positive diameter
- fixed bug that when isolating a Gerber file made out of a single polygon, an RecursionException was issued together with inability to create tbe isolation
- when applying a new language if there are any changes in the current project, the app will offer to save the project before the reboot

3.08.2019

- added project name to the window title
- fulfilled request: When saving a CNC file, if the file name is changed in the OS window, the new name does appear in the “Selected” (in name) and “Project” tabs (in cnc_job)
- solved bug such that the app is not crashing when some apertures in the Gerber file have no geometry. More than that, now the apertures that have geometry elements are bolded as opposed to the ones without geometry for which the text is unbolded
- merged a pull request with language changes for Russian translate
- updated the other translations

31.07.2019

- changed the order of the menu entries in the FIle -> Open ...
- organized the list of recent files so the Project entries are to the top and separated from the other types of file
- work on identification of changes in Preferences tab
- added categories names for the recent files
- added a detection if any values are changed in the Edit -> Preferences window and on close it will ask the user if he wants to save the changes or not
- created a new menu entry in the File menu named Recent projects that will hold the recent projects and the previous "Recent files" will hold only the previous loaded files
- updated all translations for the new strings
- fixed bug recently introduced that when changing the units in the Edit -> Preferences it did not converted the values
- fixed another bug that when selecting an Excellon object after disabling it it crashed the app
- RELEASE 8.92

30.07.2019

- fixed bug that crashed the software when trying to edit a GUI value in Geometry selected tab without having a tool in the Tools Table
- fixed bug that crashed the app when trying to add a tool without a tool diameter value
- Spanish Google translation at 77%
- changed the Disable plots menu entry in the context menu, into a Toggle Visibility menu entry
- Spanish Google translation 100% but two strings (big ones) - needs review
- added two more strings to translation strings (due of German language)
- completed the Russian translation using the Google and Yandex translation engines (minus two big strings) - needs review

28.07.2019

- fixed issue with not using the current units in the tool tables after unit conversion
- after unit conversion from Preferences, the default values are automatically saved by the app
- in Basic mode, the tool type column is no longer hidden as it may create issues when using an painted geometry
- some PEP8 clean-up in FlatCAMGui.py
- fixed Panelize Tool to do panelization for multiple passes type of geometry that comes out of the isolation done with multiple passes

20.07.2019

- updated the CutOut tool so it will work on single PCB Gerbers or on PCB panel Gerbers
- updated languages
- 70% progress in Spanish Google translation

19.07.2019

- fixed bug in FlatCAMObj.GeometryObject.ui_disconnect(); the widgets signals were not disconnected from handlers when required therefore the signals were connected in an exponential way
- some changes in the widgets used in the Selected tab for Geometry object
- some PEP8 cleanup in FlatCAMObj.py
- updated languages
- 60% progress in Spanish Google translation

17.07.2019

- added some more strings to the translatable ones, especially the radio button labels
- updated the .POT file and the available translations
- 51% progress in Spanish Google translation
- version date change

16.07.2019

- PEP8 correction in flatcamTools
- merged the Brazilian-portuguese language from a pull request made by Carlos Stein
- more PEP8 corrections

15.07.2019

- some PEP8 corrections

13.07.2019

- fixed a possible issue in Gerber Object class
- added a new tool in Gerber Editor: Mark Area Tool. It will mark the polygons in a edited Gerber object with areas within a defined range, allowing to delete some of the not necessary  copper features
- added new menu links in the Gerber Editor menu for Eraser Tool and Mark Area Tool
- added key shortcuts for Eraser Tool (Ctrl+E) and Mark Area Tool (Alt+A) and updated the shortcuts list

9.07.2019

- some changes in the app.on_togle_units() to make sure we don't try to convert empty parameters which may cause crashes on FlatCAM units change
- updated setup_ubuntu.sh file
- made sure to import certain libraries in some of the FlatCAM files and not to rely on chained imports

8.07.2019

- fixed bug that allowed empty tool in the tools generated in Geometry object
- fixed bug in Tool Cutout that did not allow the transfer of used cutout tool diameter to the cutout geometry object

5.07.2019

- fixed bug in CutOut Tool
- some other bug in CutOut tool fixed

1.07.2019

- Spanish translation at 36%

28.06.2019

- Spanish translation (Google Translate) at 21%

27.06.2019

- added new translation: Spanish. Finished 10%

23.06.2019

- fixes issues with units conversion when the tool diameters are a list of comma separated values (NCC Tool, SolderPaste Tool and Geometry Object)
- fixed a "typo" kind of bug in SolderPaste Tool
- RELEASE 8.919

22.06.2019

- some GUI layout optimizations in Edit -> Preferences
- added the possibility for multiple tool diameters in the Edit -> Preferences -> Geometry -> Geometry General -> Tool dia separated by comma
- fixed scaling for the multiple tool diameters in Edit -> Preferences -> Geometry -> Geometry General -> Tool dia, for NCC tools more than 2 and for Solderpaste nozzles more than 2
- fixed bug in CNCJob where the CNC Tools table will show always only 2 decimals for Tool diameters regardless of the current measuring units
- made the tools diameters decimals in case of INCH FlatCAM units to be 4 instead of 3
- fixed bug in updating Grid values whenever toggling the FlatCAM units and the X, Y Grid values are linked, bugs which caused the Y value to be scaled incorrectly
- set the decimals for Grid values to be set to 6 if the units of FlatCAM is INCH and to set to 4 if FlatCAM units are METRIC
- updated translations
- updated the Russian translation from 51% complete to 69% complete using the Yandex translation engine
- fixed recently introduced bug in milling drills/slots functions
- moved Substract Tool from Menu -> Edit -> Conversions to Menu -> Tool
- fixed bug in Gerber isolation (Geometry expects now a value in string format and not float)
- fixed bug in Paint tool: now it is possible to paint geometry generated by External Isolation (or Internal isolation)
- fixed bug in editing a multigeo Geometry object if previously a tool was deleted
- optimized the toggle of annotations; now there is no need to replot the entire CNCJob object too on toggling of the annotations
- on toggling off the plot visibility the annotations are turned off too
- updated translations; Russian translation at 76% (using Yandex translator engine - needs verification by a native speaker of Russian)

20.06.2019

- fixed Scale and Buffer Tool in Gerber Editor
- fixed Editor Transform Tool in Gerber Editor
- added a message in the status bar when copying coordinates to clipboard with SHIFT + LMB click combo
- languages update

19.06.2019

- milling an Excellon file (holes and/or slots) will now transfer the chosen milling bit diameter to the resulting Geometry object

17.06.2019

- fixed bug where for Geometry objects after a successful object rename done in the Object collection view (Project tab), deselect the object and reselect it and then in the Selected tab the name is not the new one but the old one
- for Geometry objects, adding a new tool to the Tools table after a successful rename will now store the new name in the tool data

15.06.2019

- fixed bug in Gerber parser that made the Gerber files generated by Altium Designer 18 not to be loaded
- fixed bug in Gerber editor - on multiple edits on the same object, the aperture size and dims were continuously multiplied due of the file units not being updated
- restored the FlatCAMObj.visible() to a non-threaded default

11.06.2019

- fixed the Edit -> Conversion -> Join ... functions (merge() functions)
- updated translations
- Russian translate by @camellan is not finished yet
- some PEP8 cleanup in camlib.py
- RELEASE 8.918

9.06.2019

- updated translations
- fixed the the labels for shortcut keys for zoom in and zoom out both in the Menu links and in the Shortcut list
- made sure the zoom functions use the global_zoom_ratio parameter from App.self.defaults dictionary.
- some PEP8 cleanup

8.06.2019

- make sure that the annotation shapes are deleted on creation of a new project
- added folder for the Russian translation
- made sure that visibility for TextGroup is set only if index is not None in VisPyVisuals.TextGroup.visible() setter

7.06.2019

- fixed bug in ToolCutout where creating a cutout object geometry from another external isolation geometry failed
- fixed bug in cncjob TclCommand where the gcode could not be correctly generated due of missing bounds params in obj.options dict
- fixed a hardcoded tolerance in GeometryObject.generatecncjob() and in GeometryObject.mtool_gen_cncjob() to use the parameter from Preferences
- updated translations

5.06.2019

- updated translations
- some layout changes in Edit -> Preferences such that the German translation (longer words than English) to fit correctly
- after editing an parameter the focus is lost so the user knows that something happened

4.06.2019

- PEP8 updates in AppExcEditor.py
- added the Excellon Editor parameters to the Edit -> Preferences -> Excellon GUI
- fixed a small bug in Excellon Editor
- PEP8 cleanup in FlatCAMGui
- finished adding the Excellon Editor parameters into the app logic and added a selection limit within Excellon Editor just like in the other editors

3.06.2019

- TclCommand Geocutout is now creating a new geometry object when working on a geometry, preserving also the origin object
- added a new parameter in Edit -> Preferences -> CNCJob named Annotation Color; it controls the color of the font used for annotations
- added a new parameter in Edit -> Preferences -> CNCJob named Annotation Size; it controls the size of the font used for annotations
- made visibility change threaded in FlatCAMObj()

2.06.2019

- fixed issue with geometry name not being updated immediately after change while doing geocutout TclCommand
- some changes to enable/disable project context menu entry handlers

1.06.2019

- fixed text annotation for CNC job so there are no overlapping numbers when 2 lines meet on the same point
- fixed issue in CNC job plotting where some of the isolation polygons are painted incorrectly
- fixed issue in CNCJob where the set circle steps is not used 

31.05.2019

- added the possibility to display text annotation for the CNC travel lines. The setting is both in Preferences and in the CNC object properties

30.05.2019

- editing a multi geometry will no longer pop-up a Tcl window
- solved issue #292 where a new geometry renamed with many underscores failed to store the name in a saved project
- the name for the saved projects are updated to the current time and not to the time of the app startup
- some PEP8 changes related to comments starting with only one '#' symbol
- more PEP8 cleanup
- solved issue where after the opening of an object the file path is not saved for further open operations

24.05.2019

- added a toggle Grid button to the canvas context menu in the Grids submenu
- added a toggle left panel button to the canvas context menu

23.05.2019

- fixed bug in Gerber editor FCDisk and DiscSemiEditorGrb that the resulting geometry was not stored into the '0' aperture where all the solids are stored
- fixed minor issue in Gerber Editor where apertures were included in the saved object even if there was no geometric data for that aperture
- some PEP8 cleanup in FlatCAMApp.py

22.05.2019

- Geo Editor - added a new editor tool, Eraser
- some PEP8 cleanup of the Geo Editor
- fixed some selection issues in the new tool Eraser in Geometry Editor
- updated the translation files
- RELEASE 8.917

21.05.2019

- added the file extension .ncd to the Excellon file extension list
- solved parsing issue for Excellon files generated by older Eagle versions (v6.x)
- Gerber Editor: finished a new tool: Eraser. It will erase certain parts of Gerber geometries having the shape of a selected shape.

20.05.2019

- more PEP8 changes in Gerber editor
- Gerber Editor - started to work on a new editor tool: Eraser

19.05.2019

- fixed the Circle Steps parameter for both Gerber and Geometry objects not being applied and instead the app internal defaults were used.
- fixed the Tcl command Geocutout issue that gave an error when using the 4 or 8 value for gaps parameter
- made wider the '#' column for Apertures Table for Gerber Object and for Gerber Editor; in this way numbers with 3 digits can be seen
- PEP8 corrections in AppGerberEditor.py
- added a selection limit parameter for Geometry Editor
- added entries in Edit -> Preferences for the new parameter Selection limit for both the Gerber and Geometry Editors.
- set the buttons in the lower part of the Preferences Window to have a preferred minimum width instead of fixed width
- updated the translation files

18.05.2019

- added a new toggle option in Edit -> Preferences -> General Tab -> App Preferences -> "Open" Behavior. It controls which path is used when opening a new file. If checked the last saved path is used when saving files and the last opened path is used when opening files. If unchecked then the path for the last action (either open or save) is used.
- fixed App.convert_any2gerber to work with the new Gerber apertures data structure
- fixed Tool Sub to work with the new Gerber apertures data structure
- fixed Tool PDF to work with the new Gerber apertures data structure

17.05.2019

- remade the Tool Cutout to work on panels
- remade the Tool Cutout such that on multiple applications on the same object it will yield the same result
- fixed an issue in the remade Cutout Tool where when applied on a single Gerber object, the Freeform Cutout produced no cutout Geometry object
- remade the Properties Tool such that it works with the new Gerber data structure in the obj.apertures. Also changed the view for the Gerber object in Properties
- fixed issue with false warning that the Gerber object has no geometry after an empty Gerber was edited and added geometry elements

16.05.2019

- Gerber Export: made sure that if some of the coordinates in a Gerber object geometry are repeating then the resulting Gerber code include only one copy
- added a new parameter/feature: now the spindle can work in clockwise mode (CW) or counter clockwise mode (CCW)

15.05.2019

- rewrited the Gerber Parser in camlib - success
- moved the self.apertures[aperture]['geometry'] processing for clear_geometry (geometry made with Gerber LPC command) in Gerber Editor
- Gerber Editor: fixed the Poligonize Tool to work with new geometric structure and took care of a special case
- Gerber Export is fixed to work with the new Gerber object data structure and it now works also for Gerber objects edited in Gerber Editor
- Gerber Editor: fixed units conversion for obj.apertures keys that require it
- camlib Gerber parser - made sure that we don't loose goemetry in regions
- Gerber Editor - made sure that for some tools the added geometry is clean (the coordinates are non repeating)
- covered some possible issues in Gerber Export

12.05.2019

- some modifications to ToolCutout

11.05.2019

- fixed issue in camlib.CNCjob.generate_from_excellon_by_tool() in the drill path optimization algorithm selection when selecting the MH algorithm. The new API's for Google OR-tools required some changes and also the time parameter can be now just an integer therefore I modified the GUI
- made the Feedrate Rapids parameter to depend on the type of preprocessor choosed. It will be showed only for a preprocessor which the name contain 'marlin' and for any preprocessor's that have 'custom' in the name
- fixed the camlib.Gerber functions of mirror, scale, offset, skew and rotate to work with the new data structure for apertures geometry
- fixed Gerber Editor selection to work with the new Gerber data structure in self.apertures
- fixed Gerber Editor PadEditorGrb class to work with the new Gerber data structure in self.apertures
- fixed camlib.Gerber issues related to what happen after parsing rectangular apertures 
- wip in camblib.Gerber
- completely converted the Gerber editor to the new data structure
- Gerber Editor: added a threshold limit for how many elements a move selection can have. If above the threshold only a bounding box Poly will be painted on canvas as utility geometry.

10.05.2019

- Gerber Editor - working in conversion to the new data format
- made sure that only units toggle done in Edit -> Preferences will toggle the data in Preferences. The menu entry Edit -> Toggle Units and the shortcut key 'Q' will change only the display units in the app
- optimized Transform tool
- RELEASE 8.916

9.05.2019

- reworked the Gerber parser

8.05.2019

- added zoom fit for Set Origin command
- added move action for solid_geometry stored in the gerber_obj.apertures
- fixed camlib.Gerber skew, rotate, offset, mirror functions to work for geometry stored in the Gerber apertures
- fixed Gerber Editor follow_geometry reconstruction
- Geometry Editor: made the tool to be able to continuously move until the tool is exited either by ESC key or by right mouse button click
- Geometry Editor Move Tool: if no shape is selected when triggering this tool, now it is possible to make the selection inside the tool
- Gerber editor Move Tool: fixed a bug that repeated the plotting function unnecessarily 
- Gerber editor Move Tool: if no shape is selected the tool will exit

7.05.2019

- remade the Tool Panelize GUI
- work in Gerber Export: finished the header export
- fixed the Gerber Object and Gerber Editor Apertures Table to not show extra rows when there are aperture macros in the object
- work in Gerber Export: finished the body export but have some errors with clear geometry (LPC)
- Gerber Export - finished

6.05.2019

- made units change from shortcut key 'Q' not to affect the preferences
- made units change from Edit -> Toggle Units not to affect the preferences
- remade the way the aperture marks are plotted in Gerber Object
- fixed some bugs related to moving an Gerber object with the aperture table in view
- added a new parameter in the Edit -> Preferences -> App Preferences named Geo Tolerance. This parameter control the level of geometric detail throughout FlatCAM. It directly influence the effect of Circle Steps parameter.
- solved a bug in Excellon Editor that caused app crash when trying to edit a tool in Tool Table due of missing a tool offset
- updated the ToolPanelize tool so the Gerber panel of type GerberObject can be isolated like any other GerberObject object
- updated the ToolPanelize tool so it can be edited
- modified the default values for toolchangez and endz parameters so they are now safe in all cases

5.05.2019

- another fix for bug in clear geometry processing for Gerber apertures
- added a protection for the case that the aperture table is part of a deleted object
- in Script Editor added support for auto-add closing parenthesis, brace and bracket
- in Script Editor added support for "CTRL + / " key combo to comment/uncomment line

4.05.2019

- fixed bug in camlib.parse_lines() in the clear_geometry processing section for self.apertures
- fixed bug in parsing Gerber regions (a point was added unnecessary)
- renamed the menu entry Edit -> Copy as Geo to Convert Any to Geo and moved it in the Edit -> Conversion
- created a new function named Convert Any to Gerber and installed it in Edit -> Conversion. It's doing what the name say: it will convert an Geometry or Excellon FlatCAM object to a Gerber object.

01.05.2019

- the project items color is now controlled from Foreground Role in ObjectCollection.data()
- made again plot functions threaded but moved the dataChanged signal (update_view() ) to the main thread by using an already existing signal (plots_updated signal) to avoid the errors with register QVector
- Enable/Disable Object toggle key ("Space" key) will trigger also the datChanged signal for the Project MVC
- added a new setting for the color of the Project items, the color when they are disabled.
- fixed a crash when triggering 'Jump To' menu action (shortcut key 'J' worked ok)
- made some mods to what can be translated as some of the translations interfered with the correct functioning of FlatCAM
- updated the translations
- fixed bugs in Excellon Editor
- Excellon Editor:  made Add Pad tool to work until right click
- Excellon Editor: fixed mouse right click was always doing popup context menu
- GUIElements.FCEntry2(): added a try-except clause
- made sure that the Tools Tab is cleared on Editors exit
- Geometry Editor: restored the old behavior: a tool is active until it is voluntarily exited: either by using the 'ESC' key, or selecting the Select tool or new: right click on canvas
- RELEASE 8.915

30.04.2019

- in ObjectCollection class, made sure that renaming an object in Project View does not result in an empty name. If new name is blank the rename is cancelled.
- made ObjectCollection.TreeItem() inherit KeySensitiveListVIew and implicitly QTreeView (in the hope that the theme applied on app will be applied on the tree items, too (for MacOs new DarkUI theme)
- renamed SilkScreen Tool to Substract Tool and move it's menu location in Edit -> Conversion
- started to modify the Substract Tool to work on Geometry objects too
- progress in the new Substract Tool for Geometry Objects
- finished the new Substract Tool
- added new setting for the color of the Project Tree items; it helps in providing contrast when using dark theme like the one in MacOS

29.04.2019

- solved bug in Gerber Editor: the '0' aperture (the region aperture) had no size which created errors. Made the size to be zero.
- solved bug in editors: the canvas selection shape was not deleted on mouse release if the grid snap was OFF
- solved bug in Excellon Editor: when selecting a drill hole on canvas the selected row in the Tools Table was not the correct one but the next highest row
- finished the Silkscreen Tool but there are some limitations (some wires fragments from silkscreen are lost)
- solved the issue in Silkscreen Tool with losing some fragments of wires from silkscreen

26.04.2019

- small changes in GUI; optimized contextual menu display
- made sure that the Project Tab is disabled while one of the Editors is active and it is restored after returning to app
- fixed some bugs recently introduced in Editors due of the changes done to the way mouse panning is detected 
- cleaned up the context menu's when in Editors; made some structural changes
- updated the code in camlib.CNCJob.generate_from_excellon_by_tools() to work with the new API from Google OR-Tools
- all Gerber regions (G36 G37) are stored in the '0' aperture
- fixed a bug that added geometry with clear polarity in the apertures where was not supposed to be

25.04.2019

- Geometry Editor: modified the intersection (if the selected shapes don't intersects preserve them) and substract functions (delete all shapes that were used in the process)
- work in the ToolSub
- for all objects, if in Selected the object name is changed to the same name, the rename is not done (because there is nothing changed)
- fixed Edit -> Copy as Geom function handler to work for Excellon objects, too
- made sure that the mouse pointer is restored to default on Editor exit
- added a toggle button in Preferences to toggle on/off the display of the selection box on canvas when the user is clicking an object or selecting it by mouse dragging.

24.04.2019

- PDF import tool: working in making the PDF layer rendering multithreaded in itself (one layer rendered on each worker)
- PDF import tool: solved a bug in parsing the rectangle subpath (an extra point was added to the subpath creating nonexisting geometry)
- PDF import tool: finished layer rendering multithreading
- New tool: Silkscreen Tool: I am trying to remove the overlapped geo with the soldermask layer from overlay layer; layed out the class and functions - not working yet

23.04.2019

- Gerber Editor: added two new tools: Add Disc and Add SemiDisc (porting of Circle and Arc from Geometry Editor)
- Gerber Editor: made Add Pad repeat until user exits the Add Pad through either mouse right click, or ESC key or deselecting the Add Pad menu item
- Gerber and Geometry Editors: fixed some issues with the Add Arc/Add Semidisc; in mode 132, the norm() function was not the one from numpy but from a FlatCAM Class. Also fixed some of the texts and made sure that when changing the mode, the current points are reset to prepare for the newly selected mode.
- Fixed Measurement Tool to show the mouse coordinates on the status bar (it was broken at some point)
- updated the translation files
- added more custom mouse cursors in Geometry and Gerber Editors
- RELEASE 8.914

22.04.2019

- added PDF file as type in the Recent File list and capability to load it from there
- PDF's can be drag & dropped on the GUI to be loaded
- PDF import tool: added support for save/restore Graphics stack. Only for scale and offset transformations and for the linewidth. This is the final fix for Microsoft PDF printer who saves in PDF format 1.7
- PDF Import tool: added support for PDF files that embed multiple Gerber layers (top, bottom, outline, silkscreen etc). Each will be opened in it's own Gerber file. The requirement is that each one is drawn in a different color
- PDF Import tool: fixed bugs when drag & dropping PDF files on canvas the files geometry previously opened was added to the new one. Also scaling issues. Solved.
- PDF Import tool: added support for detection of circular geometry drawn with white color which means actually invisible color. When detected, FlatCAM will build an Excellon file out of those geoms.
- PDF Import tool: fixed storing geometries in apertures with the right size (before they were all stored in aperture D10)

21.04.2019

- fixed the PDF import tool to work with files generated by the Microsoft PDF printer (chained subpaths)
- in PDF import tool added support for paths filled and at the same time stroked ('B' and 'B*'commands)
- added a shortcut key for PDF Import Tool (Alt+Q) and updated the Shortcut list (also with the 'T' and 'R' keys for Gerber Editor where they control the bend in Track and Region tool and the 'M' and 'D' keys for Add Arc tool in Geometry Editor)

20.04.2019

- finished adding the PDF import tool although it does not support all kinds of outputs from PDF printers. Microsoft PDF printer is not supported.

19.04.2019

- started to work on PDF import tool


18.04.2019

- Gerber Editor: added custom mouse cursors for each mode in Add Track Tool
- Gerber Editor: Poligonize Tool will first fuse polygons that touch each other and at a second try will create a polygon. The polygon will be automatically moved to Aperture '0' (regions).
- Gerber Editor: Region Tool will add regions only in '0' aperture
- Gerber Editor: the bending mode will now survive until the tool is exited
- Gerber Editor: solved some bugs related with deleting an aperture and updating the last_selected_aperture

17.04.2019

- Gerber Editor: added some messages to warn user if no selection exists when trying to do aperture deletion or aperture geometry deletion
- fixed version check
- added custom mouse cursors for some tools in Gerber Editor
- Gerber Editor: added multiple modes to lay a Region: 45-degrees, reverse 45-degrees, 90-degrees, reverse 90-degrees and free-angle. Added also key shortcuts 'T' and 'R' to cycle forward, respectively in reverse through the modes.
- Excellon Editor: fixed issue not remembering last tool after adding a new tool
- added custom mouse cursors for Excellon and Geometry Editors in some of their tools

16.04.2019

- added ability to use ENTER key to finish tool adding in Editors, NCC Tool, Paint Tool and SolderPaste Tool.
- Gerber Editor: started to add modes of laying a track
- Gerber Editor: Add Track Tool: added 5 modes for laying a track: 45-degrees, reverse-45 degrees, 90-degrees, reverse 90-degrees and free angle. Key 'T' will cycle forward through the modes and key 'R' will cycle in reverse through the track laying modes.
- Gerber Editor: Add Track Tool: first right click will finish the track. Second right click will exit the Track Tool and return to Select Tool.
- Gerber Editor: added protections for the Pad Array and Pad Tool for the case when the aperture size is zero (the aperture where to store the regions)

15.04.2019

- working on a new tool to process automatically PcbWizard Excellon files which are generated in 2 files
- finished ToolPcbWizard; it will autodetect the Excellon format, units from the INF file
- Gerber Editor: reduced the delay to show UI when editing an empty Gerber object
- update the order of event handlers connection in Editors to first connect new handlers then disconnect old handlers. It seems that if nothing is connected some VispY functions like canvas panning no longer works if there is at least once nothing connected to the 'mouse_move' event
- Excellon Editor: update so always there is a tool selected even after the Excellon object was just edited; before it always required a click inside of the tool table, not you do it only if needed.
- fixed the menu File -> Edit -> Edit/Close Editor entry to reflect the status of the app (Editor active or not)
- added support in Excellon parser for autodetection of Excellon file format for the Excellon files generated by the following ECAD sw: DipTrace, Eagle, Altium, Sprint Layout
- Gerber Editor: finished a new tool: Poligonize Tool (Alt+N in Editor). It will fuse a selection of tracks into a polygon. It will fill a selection of polygons if they are apart and it will make a single polygon if the selection is overlapped. All the newly created filled polygons will be stored in aperture '0' (if it does not exist it will be automatically created)
- fixed a bug in Move command in context menu who crashed the app when triggered
- Gerber Editor: when adding a new aperture it will be store as the last selected and it will be used for any tools that are triggered until a new aperture is selected.

14.04.2019

- Gerber Editor: Remade the processing of 'clear_geometry' (geometry generated by polygons made with Gerber LPC command) to work if more than one such polygon exists
- Gerber Editor: a disabled/enabled sequence for the VisPy cursor on Gerber edit make the graphics better
- Editors: activated an old function that was no longer active: each tool can have it's own set of shortcut keys, the Editor general shortcut keys that are letters are overridden
- Gerber and Geometry editors, when using the Backspace keys for certain tools, they will backtrack one point but now the utility geometry is immediately updated
- In Geometry Editor I fixed bug in Arc modes. Arc mode shortcut key is now key 'M' and arc direction change shortcut key is 'D'
- moved the key handler out of the Measurement tool to flatcamGUI.FlatCAMGui.keyPressEvent()
- Gerber Editor: started to add new function of poligonize which should make a filled polygon out of a shape
- cleaned up Measuring Tool
- solved bug in Gerber apertures size and dimensions values conversion when file units are different than app units

13.04.2019

- updating the German translation
- Gerber Editor: added ability to change on the fly the aperture after one of the tools: Add Pad or Add Pad Array is activated
- Gerber Editor: if a tool is cancelled via key shortcut ESCAPE, the selection is now deleted and any other action require a new selection
- finished German translation (Google translated with some adjustments)
- final fix for issue #277. Previous fix was applied only for one case out of three.
- RELEASE 8.913

12.04.2019

- Gerber Editor: added support for Oblong type of aperture
- fixed an issue with automatically filled in aperture code when the edited Gerber file has no apertures; established an default with value 10 (according to Gerber specifications)
- fixed a bug in editing a blank Gerber object
- added handlers for the Gerber Editor context menu
- updated the translation template POT file and the EN PO/MO files
- Gerber Editor: added toggle effect to the Transform Tool
- Gerber Editor: added shortcut for Transform Tool and also toggle effect here, too
- updated the shortcut list with the Gerber Editor shortcut keys
- Gerber Editor: fixed error when adding an aperture with code value lower than the ones that already exists
- when adding an aperture with code '0' (zero) it will automatically be set with size zero and type: 'REG' (from region); here we store all the regions from a Gerber file, the ones without a declared aperture
- Gerber Editor: added support for Gerber polarity change commands (LPD, LPC)
- moved the polarity change processing from AppGerberEditor() class to camlib.Gerber().parse_lines()
- made optional the saving of an edited object. Now the user can cancel the changes to the object.
- replaced the standard buttons in the QMessageBox's used in the app with custom ones that can have text translated
- updated the POT translation file and the MO/PO files for English and Romanian language

11.04.2019

- changed the color of the marked apertures to the global_selection_color
- Gerber Editor: added Transformation Tool and Rotation key shortcut
- in all Editors, manually deactivating a button in the editor toolbar will automatically select the 'Select' button
- fixed Excellon Editor selection: when a tool is selected in Tools Table, all the drills belonging to that tool are selected. When a drill is selected on canvas, the associated tool will be selected without automatically selecting all other drills with same tool
- Gerber Editor: added Add Pad Array tool
- Gerber Editor: in Add Pad Array tool, if the pad is not circular type, for circular array the pad will be rotated to match the array angle
- Gerber Editor: fixed multiple selection with key modifier such that first click selects, second deselects

10.04.2019

- Gerber Editor: added Add Track and Add Region functions
- Gerber Editor: fixed key shortcuts
- fixed setting the Layout combobox in Preferences according to the current layout
- created menu links and shortcut keys for adding a new empty Gerber objects; on update of the edited Gerber, if the source object was an empty one (new blank one) this source obj will be deleted
- removed the old apertures editing from Gerber Obj selected tab
- Gerber Editor: added Add Pad (circular or rectangular type only)
- Gerber Editor: autoincrement aperture code when adding new apertures
- Gerber Editor: automatically calculate the size of the rectangular aperture

9.04.2019

- Gerber Editor: added buffer and scale tools
- Gerber Editor: working on aperture selection to show on Aperture Table
- Gerber Editor: finished the selection on canvas; should be used as an template for the other Editors
- Gerber Editor: finished the Copy, Aperture Add, Buffer, Scale, Move including the Utility geometry
- Trying to fix bug in Measurement Tool: the mouse events don't disconnect
- fixed above bug in Measurement Tool (but there is a TODO there)

7.04.2019

- default values for Jump To function is jumping to origin (0, 0)

6.04.2019

- fixed bug in Geometry Editor in buffer_int() function that created an Circular Reference Error when applying buffer interior on a geometry.
- fixed issue with not possible to close the app after a project save.
- preliminary Gerber Editor.on_aperture_delete() 
- fixed 'circular reference' error when creating the new Gerber file in Gerber Editor
- preliminary Gerber Editor.on_aperture_add()

5.04.2019

- Gerber Editor: made geometry transfer (which is slow) to Editor to be multithreaded
- Gerber Editor: plotting process is showed in the status bar
- increased the number of workers in FlatCAM and made the number of workers customizable from Preferences
- WIP in Gerber Editor: geometry is no longer stored in a Rtree storage as it is not needed
- changed the way delayed plot is working in Gerber Editor to use a Qtimer instead of python threading module
- WIP in Gerber Editor
- fixed bug in saving the maximized state
- fixed bug in applying default language on first start
~~- on activating 'V' key shortcut (zoom fit) the mouse cursor is now jumping to origin (0, 0)~~
- fixed bug in saving toolbars state; the file was saved before setting the self.defaults['global_toolbar_view]

4.04.2019

- added support for Gerber format specification D (no zero suppression) - PCBWizard Gerber files support
- added support for Excellon file with no info about tool diameters - PCB Wizard Excellon file support
- modified the bogus diameters series for Excellon objects that do not have tool diameter info
- made Excellon Editor aware of the fact that the Excellon object that is edited has fake (bogus) tool diameters and therefore it will not sort the tools based on diameter but based on tool number
- fixed bug on Excellon Editor: when diameter is edited in Tools Table and the target diameter is already in the tool table, the drills from current tool are moved to the new tool (with new dia) - before it crashed
- fixed offset after editing drill diameters in Excellon Editor.

3.04.2019

- fixed plotting in Gerber Editor
- working on GUI in Gerber Editor
- added a Gcode end_command: default is M02
- modified the calling of the editor2object() slot function to fix an issue with updating geometry imported from SVG file, after edit
- working on Gerber Editor - added the key shortcuts: wip
- made saving of the project file non-blocking and also while saving the project file, if the user tries again to close the app while project file is being saved, the app will close only after saving is complete (the project file size is non zero)
- fixed the camlib.Geometry.import_svg() and camlib.Gerber.bounds() to work when importing SVG files as Gerber

31.03.2019

- fixed issue #281 by making generation of a convex shape for the freeform cutout in Tool Cutout a choice rather than the default
- fixed bug in Tool Cutout, now in manual cutout mode the gap size reflect the value set
- changed Measuring Tool to use the mouse click release instead of mouse click press; also fixed a bug when using the ESC key.
- fixed errors when the File -> New Project is initiated while an Editor is still active.
- the File->Exit action handler is now self.final_save() 
- wip in Gerber editor

29.03.2019

- update the TCL keyword list
- fix on the Gerber parser that makes searching for '%%' char optional when doing regex search for mode, units or image polarity. This allow loading Gerber files generated by the ECAD software TCl4.4
- fix error in plotting Excellon when toggling units
- FlatCAM editors now are separated each in it's own file
- fixed TextTool in Geometry Editor so it will open the notebook on activation and close it after finishing text adding
- started to work on a Gerber Editor
- added a fix in the Excellon parser by allowing a comma in the tool definitions between the diameter and the rest

28.03.2019

- About 45% progress in German translation
- new feature: added ability to edit MultiGeo geometry (geometry from Paint Tool)
- changed all the info messages that are of type warning, error or success so they have a space added after the keyword
- changed the Romanian translation by adding more diacritics  
- modified Gerber parser to copy the follow_geometry in the self.apertures
- modified the Properties Tool to show the number of elements in the follow_geometry for each aperture
- modified the copy functions to copy the follow_geometry and also the apertures if it's possible (only for Gerber objects)

27.03.2019

- added new feature: user can delete apertures in Advanced mode and then create a new FlatCAM Gerber object
- progress in German translation. About 27% done.
- fixed issue #278. Crash on name change in the Name field in the Selected Tab.

26.03.2019

- fixed an issue where the Geometry plot function protested that it does not have an parameter that is used by the CNCJob plot function. But both inherit from FaltCAMObj plot function which does not have that parameter so something may need to be changed. Until then I provided a phony keyboard parameter to make that function 'shut up'
- fixed bug: after using Paint Tool shortcut keys are disabled
- added CNCJob geometry for the holes created by the drills from Excellon objects

25.03.2019

- in the TCL completer if the word is already complete don't add it again but add a space
- added all the TCL keywords in the completer keyword list
- work in progress in German translation ~7%
- after any autocomplete in TCL completer, a space is added
- fixed an module import issue in NCC Tool
- minor change (optimization) of the CNCJob UI
- work in progress in German translation ~20%

22.03.2019

- fixed an error that created a situation that when saving a project with some of the CNCJob objects disabled, on project reload the CNCJob objects are no longer loaded
- fixed the Gerber.merge() function. When some of the Gerber files have apertures with same id, create a new aperture id for the object that is fused because each aperture id may hold different geometries.
- changed the autoname for saving Preferences, Project and PNG file

20.03.2019

- added autocomplete finish with ENTER key for the TCL Shell
- made sure that the autocomplete function works only for FlatCAM Scripts
- ESC key will trigger normal view if in full screen and the ESC key is pressed
- added an icon and title text for the Toggle Units QMessageBox

19.03.2019

- added autocomplete for Code editor;
- autocomplete in Code Editor is finished by hitting either TAB key or ENTER key
- fixed the Gerber.merge() to work for the case when one of the merged Gerber objects solid_geometry type is Polygon and not a list

18.03.2019

- added ability to create new scripts and open scripts in FlatCAM Script Editor
- the Code Editor tab name is changed according to the task; 'save' and 'open' buttons will have filters installed for the QOpenDialog fit to the task
- added ability to run a FlatCAM Tcl script by double-clicking on the file
- in Code Editor added shortcut combo key Ctrl+Shift+V to function as a Special Paste that will replace the '\' char with '/' so the Windows paths will be pasted correctly for TCL Shell. Also doing SHIFT + LMB on the Paste in contextual menu is doing the same.

17.03.2019

- remade the layout in 2Sided Tool
- work in progress for translation in Romanian - 91%
- changed some of the app strings formatting to work better with Poedit translation software
- fixed bug in Drillcncjob TclCommand
- finished translation in Romanian
- made the translations work when the app is frozen with CX_freeze
- some formatting changes for the application strings
- some changes on how the first layout is applied
- minor bug fixes (typos from copy/paste from another part of the program)

16.03.2019

- fixed bug in Paint Tool - Single Poly: no geometry was generated
- work in progress for translation in Romanian - 70%

13.03.2019

- made the layout combobox current item from Preferences -> General window to reflect the current layout
- remade the POT translate file
- work in progress in translation for Romanian language 44%
- fix for showing tools by activating them from the Menu - final fix.

11.03.2019

- changed some icons here and there
- fixed the Properties Project menu entry to work on the new way
- in Properties tool now the Gerber apertures show the number of polygons in 'solid_geometry' instead of listing the objects
- added a visual cue in Menu -> Edit about the entries to enter the Editor and to Save & Exit Editor. When one is enabled the other is disabled.
- grouped all the UI files in flatcamGUI folder
- grouped all parser files in flatcamParsers folder
- another changes to the final_save() function
- some strings were left outside the translation formatting - fixed
- finished the replacement of '_' symbols throughout the app which conflicted with the _() function used by the i18n
- reverted changes in Tools regarding the toggle effect - now they work as expected

10.03.2019

- added a fix in the Gerber parser when adding the geometry in the self.apertures dict for the case that the current aperture is None (Allegro does that)
- finished support for internationalization by adding a set of .po/.mo files for the English language. Unfortunately the final action can be done only when Beta will be out of Beta (no more changes) or when I will decide to stop working on this app.
- changed the tooltip for 'feedrate_rapids' parameter to point out that this parameter is useful only for the Marlin preprocessor
- fix app crash for the case that there are no translation files
- fixed some forgotten strings to be prepared for internationalization in ToolCalculators
- fixed Tools menu no longer working due of changes
- added some test translation for the ToolCalculators (in Romanian)
- fixed bug in ToolCutOut where for each tool invocation the signals were reconnected
- fixed some issues with ToolMeasurement due of above changes
- updated the App.final_save() function
- fixed an issue created by the fact that I used the '_' char inside the app to designate unused info and that conflicted with the _() function used by gettext
- made impossible to try to reapply current language that it's already applied (un-necessary)

8.03.2019

- fixed issue when doing th CTRL (or SHIFT) + LMB, the focus is automatically moved to Project Tab
- further work in internationalization, added a fallback to English language in case there is no translation for a string
- fix for issue #262: when doing Edit-> Save & Close Editor on a Geometry that is not generated through first entering into an Editor, the geometry disappear
- finished preparing for internationalization for the files: camlib and objectCollection
- fixed tools shortcuts not working anymore due of the new toggle parameter for the .run().
- finished preparing for internationalization for the files: FlatCAMEditor, MainGUI
- finished preparing for internationalization for the files: FlatCAMObj, ObjectUI
- sorted the languages in the Preferences combobox

7.03.2019

- made showing a shape when hovering over objects, optional, by adding a Preferences -> General parameter
- starting to work in internationalization using gettext()
- Finished adding _() in FlatCAM Tools
- fixed Measuring Tool - after doing a measurement the Notebook was switching to Project Tab without letting the user see the results
- more work on the translation engine; the app now restarts after a language is applied
- added protection against using Travel Z parameter with negative or zero value (in Geometry).
- made sure that when the Measuring Tools is active after last click the Status bar is no longer deleted

6.03.2019

- modified the way the FlatCAM Tools are run from toolbar as opposed of running them from other sources
- some Gerber UI changes

5.03.2019

- modified the grbl-laser preprocessor lift_code()
- treated an error created by Z_Cut parameter being None
- changed the hover and selection box transparency

4.03.2019

- finished work on object hovering
- fixed Excellon object move and all the other transformations
- starting to work on Manual Cutout Tool
- remade the CutOut Tool
- finished Manual Cutout Tool by adding utility geometry to the cutting geometry
- added CTRL + click behavior for adding manual bridge gaps in Cutout Tool
- in Tool Cutout added shortcut key 'Escape' to cancel the current adding of bridge gaps

3.03.2019

- minor UI changes for Gerber UI
- ~~after an object move, the apertures plotted shapes are deleted from canvas and the 'mark all' button is deselected~~
- after move tool action or any other transform (rotate, skew, scale, mirror, offset), the plotted apertures are kept plotted.
- changing units now will convert all the default values from one unit type to another
- prettified the selection shape and the moving shape
- initial work in object hovering shape

02.03.2019

- fixed offset, rotate, scale, skew for follow_geometry. Fixed the move tool also.
- fixed offset, rotate, scale, skew for 'solid_geometry' inside the self.apertures.

28.02.2019

- added a change that when a double click is performed in a object on canvas resulting in a selection, if the notebook is hidden then it will be displayed
- progress in ToolChange Custom commands replacement and rename

27.02.2019

- made the Custom ToolChange Text area in CNCJob Selected Tab depend on the status of the ToolChange Enable Checkbox even in the init stage.
- added some parameters throughout camlib gcode generation functions; handled some possible errors (e.g like when attempting to use an empty Custom GCode Toolchange)
- added toggle effect for the tools in the toolbar.
- enhanced the toggle effect for the tools in the Tools Toolbar and also for Notebook Tab selection: if the current tool is activated it will toggle the notebook side but only if the installed widget is itself. If coming from another tool, the notebook will stay visible
- upgraded the Tool Cutout when done from Gerber file to create a convex_hull around the Gerber file rather than trying to isolate it
- added some protections for the FlatCAM Tools run after an object was loaded

26.02.2019

- added a function to read the parameters from ToolChange macro Text Box (I need to move it from CNCJob to Excellon and Geometry)
- fixed the geometry adding to the self.apertures in the case when regions are done without declaring any aperture first (Allegro does that). Now, that geometry will be stored in the '0' aperture with type REG
- work in progress to Toolchange_Custom code replacement -> finished the parse and replace function
- fixed mouse selection on canvas, mouse drag, mouse click and mouse double click
- fixed Gerber Aperture Table dimensions
- added a Mark All button in the Gerber aperture table.
- because adding shapes to the shapes collection (when doing Mark or Mark All) is time consuming I made the plot_aperture() threaded.
- made the polygon fusing in modified Gerber creation, a list comprehension in an attempt for optimization
- when right clicking the files in Project tab, the Save option for Excellon no longer export it but really save the original. 
- in ToolChange Custom Code replacement, the Text Box in the CNCJob Selected tab will be active only if there is a 'toolchange_custom' in the name of the preprocessor file. This assume that it is, or was created having as template the Toolchange Custom preprocessor file.


25.02.2019

- fixed the Gerber object UI layout
- added ability to mark individual apertures in Gerber file using the Gerber Aperture Table
- more modifications for the Gerber UI layout; made 'follow' an advanced Gerber option
- added in Preferences a new Category: Gerber Advanced Options. For now it controls the display of Gerber Aperture Table and the "follow" attribute4
- fixed GerberObject.merge() to merge the self.apertures[ap]['solid_geometry'] too
- started to work on a new feature that allow adding a ToolChange GCode macro - GUI added both in CNCJob Selected tab and in CNCJob Preferences
- added a limited 'sort-of' Gerber Editor: it allows buffering and scaling of apertures

24.02.2019

- fixed a small bug in the Tool Solder Paste: the App don't take into consideration pads already filled with solder paste.
- prettified the defaults files and the recent file. Now they are ordered and human readable
- added a Toggle Code Editor Menu and key shortcut
- added the ability to open FlatConfig configuration files in Code Editor, Modify them and then save them.
- added ability to double click the FlatConfig files and open them in the FlatCAM Code Editor (to be verified)
- when saving a file from Code Editor and there is no object active then the OpenFileDialog filters are reset to FlatConfig files.
- reverted a change in GCode that might affect Gerber polarity change in Gerber parser
- ability to double click the FlatConfig files and open them in the FlatCAM Code Editor - fixed and verified
- fixed the Set To Origin function when Escape was clicked
- added all the Tools in a new ToolBar
- fixed bug that after changing the layout all the toolbar actions are no longer working
- fixed bug in Set Origin function
- fixed a typo in Toolchange_Probe_MACH3 preprocessor

23.02.2019

- remade the SolderPaste geometry generation function in ToolSoderPaste to work in certain scenarios where the Gerber pads in the SolderPaste mask Gerber may be just pads outlines
- updated the Properties Tool to include more information's, also details if a Geometry is of type MultiGeo or SingleGeo
- remade the Preferences GUI to include the Advanced Options in a separate way so it is obvious which are displayed when App Level is Advanced.
- added protection, not allowing the user to make a Paint job on a MultiGeo geometry (one that is converted in the Edit -> Conversion menu)) because it is not supported

22.02.2019

- added Repetier preprocessor file
- removed "added ability to regenerate objects (it's actually deletion followed by recreation)" because of the way Python pass parameters to functions by reference instead of copy
- added ability to toggle globally the display of ToolTips. Edit -> Preferences -> General -> Enable ToolTips checkbox.
- added true fullscreen support (for Windows OS)
- added the ability of context menu inside the GuiElements.FCCombobox() object.
- remade the UI for ToolSolderPaste. The object comboboxes now have context menu's that allow object deletion. Also the last object created is set as current item in comboboxes.
- some GUI elements changes

21.02.2019

- added protection against creating CNCJob from an empty Geometry object (with no geometry inside)
- changed the shortcut key for YouTube channel from F2 to key F4
- changed the way APP LEVEL is showed both in Edit -> Preferences -> General tab and in each Selected Tab. Changed the ToolTips content for this.
- added the functions for GCode View and GCode Save in Tool SolderPaste
- some work in the Gcode generation function in Tool SolderPaste
- added protection against trying to create a CNCJob from a solder_paste dispenser geometry. This one is different than the default Geometry and can be handled only by SolderPaste Tool.
- ToolSolderPaste tools (nozzles) now have each it's own settings
- creating the camlib functions for the ToolSolderPaste gcode generation functions
- finished work in ToolSolderPaste
- fixed issue with not updating correctly the plot kind (all, cut, travel) when clicking in the CNC Tools Table plot buttons
- made the GCode Editor for ToolSolderPaste clear the text before updating the Code Editor tab
- all the Tabs in Plot Area are closed (except Plot Area itself) on New Project creation
- added ability to regenerate objects (it's actually deletion followed by recreation)

20.02.2019

- finished added a Tool Table for Tool SolderPaste
- working on multi tool solder paste dispensing
- finished the Edit -> Preferences defaults section
- finished the UI, created the preprocessor file template
- finished the multi-tool solder paste dispensing: it will start using the biggest nozzle, fill the pads it can, and then go to the next smaller nozzle until there are no pads without solder.

19.02.2019

- added the ability to compress the FlatCAM project on save with LZMA compression. There is a setting in Edit -> Preferences -> Compression Level between 0 and 9. 9 level yields best compression at the price of RAM usage and time spent.
- made FlatCAM able to load old type (uncompressed) FlatCAM projects
- fixed issue with not loading old projects that do not have certain information's required by the new versions of FlatCAM
- compacted a bit more the GUI for Gerber Object
- removed the Open Gerber with 'follow' menu entry and also the open_gerber Tcl Command attribute 'follow'. This is no longer required because now the follow_geometry is stored by default in a Gerber object attribute gerber_obj.follow_geometry
- added a new parameter for the Tcl CommandIsolate, named: 'follow'. When follow = 1 (True) the resulting geometry will follow the Gerber paths.
- added a new setting in Edit -> Preferences -> General that allow to select the type of saving for the FlatCAM project: either compressed or uncompressed. Compression introduce an time overhead to the saving/restoring of a FlatCAM project.
- started to work on Solder Paste Dispensing Tool
- fixed a bug in rotate from shortcut function
- finished generating the solder paste dispense geometry

18.02.2019

- added protections again wrong values for the Buffer and Paint Tool in Geometry Editor
- the Paint Tool in Geometry Editor will load the default values from Tool Paint in Preferences
- when the Tools in Geometry Editor are activated, the notebook with the Tool Tab will be unhidden. After execution the notebook will hide again for the Buffer Tool.
- changed the font in Tool names
- added in Geometry Editor a new Tool: Transformation Tool.
- in Geometry Editor by selecting a shape with a selection shape, that object was added multiple times (one per each selection) to the selected list, which is not intended. Bug fixed.
- finished adding Transform Tool in Geometry Editor - everything is working as intended
- fixed a bug in Tool Transform that made the user to not be able to capture the click coordinates with SHIFT + LMB click combo
- added the ability to choose an App QStyle out of the offered choices (different for each OS) to be applied at the next app start (Preferences -> General -> Gui Pref -> Style Combobox)
- added support for FlatCAM usage with High DPI monitors (4k). It is applied on the next app startup after change in Preferences -> General -> Gui Settings -> HDPI Support Checkbox
- made the app not remember the window size if the app is maximized and remember in QSettings if it was maximized. This way we can restore the maximized state but restore the windows size unmaximized
- added a button to clear the GUI preferences in Preferences -> General -> Gui Settings -> Clear GUI Settings
- added key shortcuts for the shape transformations within Geometry Editor: X, Y keys for Flip(mirror), Shift+X, Shift+Y combo keys for Skew and Alt+X, Alt+Y combo keys for Offset
- adjusted the plotcanvas.zomm_fit() function so the objects are better fit into view (with a border around) 
- modified the GUI in Objects Selected Tab to accommodate 2 different modes: basic and Advanced. In Basic mode, some of the functionality's are hidden from the user.
- added Tool Transform preferences in Edit -> Preferences and used them through out the app
- made the output of Panelization Tool a choice out of Gerber and Geometry type of objects. Useful for those who want to engrave multiple copies of the same design.

17.02.2019

- changed some status bar messages
- New feature: added the capability to view the source code of the Gerber/Excellon file that was loaded into the app. The file is also stored as an object attribute for later use. The view option is in the project context menu and in Menu -> Options -> View Source
- Serialized the source_file of the Objects so it is saved in the FlatCAM project and restored.
- if there is a single tool in the tool list (Geometry , Excellon) and the user click the Generate GCode, use that tool even if it is not selected
- fixed issue where after loading a project, if the default kind of CNCjob view is only 'cuts' the plot will revert to the 'all' type
- in Editors, if the modifier key set in Preferences (CTRL or SHIFT key) is pressed at the end of one tool operation it will automatically continue to that action until the modifier is no longer pressed when Select tool will be automatically selected.
- in Geometry Editor, on entry the notebook is automatically hidden and restored on Geometry Editor exit.
- when pressing Escape in Geometry Editor it will automatically deselect any shape not only the currently selected tool.
- when deselecting an object in Project menu the status bar selection message is deleted
- added ability to save the Gerber file content that is stored in FlatCAM on Gerber file loading. It's useful to recover from saved FlatCAM projects when the source files are no longer available.
- fixed an issue where the function handler that changed the layout had a parameter changed accidentally by an index value passed by the 'activate' signal to which was connected
- fixed bug in paint function in Geometry Editor that didn't allow painting due of overlap value

16.02.2019

- added the 'Save' menu entry to the Project context menu, for CNCJob: it will export the GCode.
- added messages in info bar when selecting objects in the Project View list
- fixed DblSided Tool so it correctly creates the Alignment Drills Excellon file using the new structure
- fixed DblSided Tool so it will not crash the app if the user tries to make a mirror using no coordinates
- added some relevant status bar messages in DblSided Tool
- fixed DblSided Tool to correctly use the Box object (until now it used as reference only Gerber object in spite of Excellon or Geometry objects being available)
- fixed DblSided Tool crash when trying to create Alignment Drills object without a Tool diameter specified
- fixed DblSided Tool issue when entering Tool diameter values with comma decimal separator instead of decimal dot separator
- fixed Cutout Tool Freeform to generate cutouts with options: LR, TB. 2LR, 2TB which didn't worked previously
- fixed Excellon parser to detect correctly the units and zeros for Excellon's generated by Eagle 9.3.0
- modified the initial size of the canvas on startup
- modified the build file (make_win.py) to solve the issue with suddenly not accepting the version as Beta
- changed the initial layout to 'compact'
- updated the install scripts to uninstall a previously installed FlatCAM Beta (that has the same GUID)

15.02.2019

- rearranged the File and Edit menu's and added some explanatory tooltips on certain menu items that could be seen as cryptic
- added Excellon Export Options in Edit -> Preferences
- started to work in using the Excellon Export parameters
- remade the Excellon export function to work with parameters entered in Edit -> Preferences -> Excellon Export
- added a new entry in the Project Context Menu named 'Save'. It will actually work for Geometry and it will do Export DXF and for Excellon and it will do Export Excellon
- reworked the offer to save a project so it is done only if there are objects in the project but those objects are new and/or are modified since last project load (if an old project was loaded.)
- updated the Excellon plot function so it can plot the Excellon's from old projects
- removed the message boxes that popup on Excellon Export errors and replaced them with status bar messages
- small change in tab width so the tabs looks good in Linux, too.

14.02.2019

- added total travel distance for CNCJob object created from Excellon Object in the CNCJob Selected tab
- added 'FlatCAM ' prefix to any detached tab, for easy identification
- remade the Grids context menu (right mouse button click on canvas). Now it has values linked to the units type (inch or mm). Added ability to add or delete grid values and they are persistent.
- updated the function for the project context menu 'Generate CNC' menu entry (Action) to use the modernized function FlatCAMObj.GeometryObject.on_generatecnc_button_click()
- when linked, the grid snap on Y will copy the value in grid snap on X in real time
- in Gerber aperture table now the values are displayed in the current units set in FlatCAM
- added shortcut key 'J' (jump to location) in Editors and added an icon to the dialog popup window
- the notebook is automatically collapsed when there are no objects in the collection and it is showed when adding an object
- added new options in Edit -> Preferences -> General -> App Preferences to control if the Notebook is showed at startup and if the notebook is closed when there are no objects in the collection and showed when the collection has objects.

13.02.2019

- added new parameter for Excellon Object in Preferences: Fast Retract. If the checkbox is checked then after reaching the drill depth, the drill bit will be raised out of the hole asap.
- started to work on GUI forms simplification
- changed the Preferences GUI for Geometry and Excellon Objects to make a difference between parameters that are changed often and those that are not.
- changed the layout in the Selected Tab UI
- started to add apertures table support
- finished Gerber aperture table display
- made the Gerber aperture table not visible as default and added a checkbox that can toggle the visibility
- fixed issue with plotting in CNCJob; with Plot kind set to something else than 'all' when toggling Plot, it was defaulting to kind = 'all'
- added (and commented) an experimental FlatCAMObj.GerberObject.plot_aperture()

12.02.2019

- whenever a FlatCAM tool is activated, if the notebook side is hidden it will be unhidden
- reactivated the Voronoi classes
- added a new parameter named Offset in the Excellon tool table - work in progress
- finished work on Offset parameter in Excellon Object (Excellon Editor, camlib, FlatCAMObj updated to take this param in consideration)
- fixed a bug where in Excellon editor when editing a file, a tool was automatically added. That is supposed to happen only for empty newly created Excellon Objects.
- starting to work on storing the solid_geometry for each tool in part in Excellon Object
- stored solid_geometry of Excellon object in the self.tools dictionary
- finished the solid_geometry restore after edit in Excellon Editor
- finished plotting selection for each tool in the Excellon Tool Table
- fixed the camlib.Excellon.bounds() function for the new type of Excellon geometry therefore fixed the canvas selection, too


10.02.2019

- the SELECTED type of messages are no longer printed to shell from 2 reasons: first, too much spam and second, issue with displaying html
- on set_zero function and creation of new geometry or new excellon there is no longer a zoom fit 
- repurposed shortcut key 'Delete' to delete tools in tooltable when the mouse is over the Seleted tab (with Geometry inside) or in Tools tab (when NCC Tool or Paint Tool is inside). Or in Excellon Editor when mouse is hovering the Selected tab selecting a tool, 'Delete' key will delete that tool, if on canvas 'Delete' key will delete a selected shape (drill). In rest, will delete selected objects.
- adjusted the preprocessor files so the Spindle Off command (M5) is done before the move to Toolchange Z
- adjusted the Toolchange Manual preprocessor file to have more descriptive messages on the toolchange event
- added a strong focus to the object_name entry in the Selected tab
- the keypad keyPressed are now detected correctly
- added a pause and message/warning to do a rough zero for the Z axis, in case of Toolchange_Probe_MACH3 preprocessor file
- changes in Toolchange_Probe_MACH3 preprocessor file

9.02.2019

- added a protection for when saving a file first time, it require a saved path and if none then it use the current working directory
- added into Preferences the Calculator Tools
- made the Preferences window scrollable on the horizontal side (it was only vertically scrollable before)
- fixed an error in Excellon Editor -> add drill array that could appear by starting the function to add a drill array by shortcut before any mouse move is registered while in Editor
- changed the messages from status bar on new object creation/selection
- in Geometry Editor fixed the handler for the Rotate shortcut key ('R')

8.02.2019

- when shortcut keys 1, 2, 3 (tab selection) are activated, if the splitter left side (the notebook) is hidden it will be made visible
- changed the menu entry Toggle Grid name to Toggle Grid Snap
- fixed errors in Toggle Axis
- fixed error with shortcut key triggering twice the keyPressEvent when in the Project List View
- moved all shortcut keys handlers from Editors to the keyPressEvent() handler from FLatCAMGUI
- in Excellon Editor added a protection for Tool_dia field in case numbers using comma as decimal separator are used. Also added a QDoubleValidator forcing a number with max 4 decimals and from 0.0000 to 9.9999
- in Excellon Editor added a shortcut key 'T' that popup a window allowing to enter a new Tool with the set diameter
- in App added a shortcut key 'T' that popup a windows allowing to enter a new Tool with set diameter only when the Selected tab is on focus and only if a Geometry object is selected
- changed the shortcut key for Transform Tool from 'T' to 'Alt+T'
- fixed bug in Geometry Selected tab that generated error when used tool offset was less than half of either total length or half of total width. Now the app signal the issue with a status bar message
- added Double Validator for the Offset value so only float numbers can be entered.
- in App added a shortcut key 'T' that popup a windows allowing to enter a new Tool with set diameter only when the Tool tab is on focus and only if a NCC Tool or Paint Area Tool object is installed in the Tool Tab
- if trying to add a tool using shortcut key 'T' with value zero the app will react with a message telling to use a non-zero value.

7.02.2019

- in Paint Tool, when painting single polygon, when clicking on canvas for the polygon there is no longer a selection of the entire object
- commented some debug messages
- imported speedups for shapely
- added a disable menu entry in the canvas contextual menu
- small changes in Tools layout
- added some new icons in the help menu and reorganized this menu
- added a new function and the shortcut 'leftquote' (left of Key 1) for toggle of the notebook section
- changed the Shortcut list shortcut key to F3
- moved some graphical classes out of Tool Shell to GUIElements.py where they belong
- when selecting an object on canvas by single click, it's name is displayed in status bar. When nothing is selected a blank message (nothing) it's displayed
- in Move Tool I've added the type of object that was moved in the status bar message
- color coded the status bar bullet to blue for selection
- the name of the selected objects are displayed in the status bar color coded: green for Gerber objects, Brown for Excellon, Red for Geometry and Blue for CNCJobs.

6.02.2019

- fixed the units calculators crash FlatCAM when using comma as decimal separator
- done a regression on Tool Tab default text. It somehow delete Tools in certain scenarios so I got rid of it
- fixed bug in multigeometry geometry not having the bounds in self.options and crashing the GCode generation
- fixed bug that crashed whole application in case that the GCode editor is activated on a Tool gcode that is defective. 
- fixed bug in Excellon Slots milling: a value of a dict key was a string instead to be an int. A cast to integer solved it.
- fixed the name self-insert in save dialog file for GCode; added protection in case the save path is None
- fixed FlatCAM crash when trying to make drills GCode out of a file that have only slots.
- changed the messages for Units Conversion
- all key shortcuts work across the entire application; moved all the shortcuts definitions in MainGUI.keyPressEvent()
- renamed the theme to layout because it is really a layout change
- added plot kind for CNC Job in the App Preferences
- combined the geocutout and cutout_any TCL commands - work in progress
- added a new function (and shortcut key Escape) that when triggered it deselects all selected objects and delete the selection box(es) 
- fixed bug in Excellon Gcode generation that made the toolchange X,Y always none regardless of the value in Preferences
- fixed the Tcl Command Geocutout to work with Gerber objects too (besides Geometry objects)

5.02.3019

- added a text in the Selected Tab which is showed whenever the Selected Tab is selected but without having an object selected to display it's properties
- added an initial text in the Tools tab
- added possibility to use the shortcut key for shortcut list in the Notebook tabs
- added a way to set the Probe depth if Toolchange_Probe preprocessors are selected
- finished the preprocessor file for MACH3 tool probing on toolchange event
- added a new parameter to set the feedrate of the probing in case the used preprocessor does probing (has toolchange_probe in it's name)
- fixed bug in Marlin preprocessor for the Excellon files; the header and toolchange event always used the parenthesis witch is not compatible with GCode for Marlin
- fixed a issue with a move to Z_move before any toolchange

4.02.2019

- modified the Toolchange_Probe_general preprocessor file to remove any Z moves before the actual toolchange event
- created a prototype preprocessor file for usage with tool probing in MACH3
- added the default values for Tool Film and Tool Panelize to the Edit -> Preferences
- added a new parameter in the Tool Film which control the thickness of the stroke width in the resulting SVG. It's a scale parameter.
- whatever was the visibility of the corresponding toolbar when we enter in the Editor, it will be set after exit from the Editor (either Geometry Editor or Excellon Editor).
- added ability to be detached for the tabs in the Notebook section (Project, Selected and Tool)
- added ability for all detachable tabs to be restored to the same position from where they were detached.
- changed the shortcut keys for Zoom In, Zoom Out and Zoom Fit from 1, 2, 3 to '-', '=' respectively 'V'. Added new shortcut keys '1', '2', '3' for Select Project Tab, Select Selected Tab and Select Tool Tab.
- formatted the Shortcut List Tab into a HTML table

3.3.2019

- updated the new shortcut list with the shortcuts added lately
- now the special messages in the Shell are color coded according to the level. Before they all were RED. Now the WARNINGS are yellow, ERRORS are red and SUCCESS is a dark green. Also the level is in CAPS LOCK to make them more obvious
- some more changes to GUI interface (solved issues)
- added some status bar messages in the Geometry Editor to guide the user when using the Geometry Tools
- now the '`' shortcut key that shows the 'shortcut key list' in Editors points to the same window which is created in a tab no longer as a pop-up window. This tab can be detached if needed.
- added a remove_tools() function before install_tools() in the init_tools() that is called when creating a new project. Should solve the issue with having double menu entry's in the TOOLS menu
- fixed remove_tools() so the Tcl Shell action is readded to the Tools menu and reconnected to it's slot function
- added an automatic name on each save operation based on the object name and/or the current date
- added more information's for the statistics

2.2.2019

- code cleanup in Tools
- some GUI structure optimization's
- added protection against entering float numbers with comma separator instead of decimal dot separator in key points of FlatCAM (not everywhere)
- added a choice of plotting the kind of geometry for the CNC plot (all, travel and cut kind of geometries) in CNCJob Selected Tab
- added a new preprocessor file named: 'probe_from_zmove' which allow probing to be done from z_move position on toolchange event 
- fixed the snap magnet button in Geometry Editor, restored the checkable property to True
- some more changes in the Editors GUI in deactivate() function
- a fix for saving as empty an edited new and empty Excellon Object

1.02.2019

- fixed preprocessor files so now the bounds values are right aligned (assuming max string length of 9 chars which means 4 digits and 4 decimals)
- corrected small type in list_sys Tcl command; added a protection of the Plot Area Tab after a successful edit.
- remade the way FlatCAM saves the GUI position data from a file (previously) to use PyQt QSettings
- added a 'theme' combo selection in Edit -> Preferences. Two themes are available: standard and compact.
- some code cleanup
- fixed a source of possible errors in DetachableTab Widget.
- fixed gcode conversion/scale (on units change) when multiple values are found on each line
- replaced the pop-up window for the shortcut list with a new detachable tab
- removed the pop-up messages from the rotate, skew, flip commands

31.01.2019

- added a parameter ('Fast plunge' in Edit -> Preferences -> Geometry Options and Excellon Options) to control if the fast move to Z_move is done or not
- added new function to toggle fullscreen status in Menu -> View -> Toggle Full Screen. Shortcut key: Alt+F10
- added key shortcuts for Enable Plots, Disable Plots and Disable other plots functions (Alt+1, Alt+2, Alt+3)
- hidden the snap magnet entry and snap magnet toggle from the main view; they are now active only in Editor Mode
- updated the camlib.CNCJob.scale() function so now the GCode is scaled also (quite a HACK :( it will need to be replaced at some point)). Units change work now on the GCODE also.
- added the bounds coordinates to the GCODE header
- FlatCAM saves now to a file in self.data_path the toolbar positions and the position of TCL Shell
- Plot Area Tab view can now be toggled, added entry in View Menu and shortcut key Ctrl+F10
- All the tabs in the GUI right side are (Plot Are, Preferences etc) are now detachable to a separate windows which when closed it returns in the previous location in the toolbar. Those detached tabs can be also reattached by drag and drop.

30.01.2019

- added a space before Y coordinate in end_code() function in some of the preprocessor files
- added in Calculators Tool an Electroplating Calculator.
- remade the App Menu for Editors: now they will be showed only when the respective Editor is active and hidden when the Editor is closed.
- added a traceback report in the TCL Shell for the errors that don't allow creation of an object; useful to trace exceptions/errors
- in case that the Toolchange X,Y parameter in Selected (or in Preferences) are deleted then the app will still do the job using the current coordinates for toolchange
- fixed an issue in camlib.CNCJob where tha variable self.toolchange_xy was used for 2 different purposes which created loss of information.
- fixed unit conversion functions in case the toolchange_xy parameter is None
- more fixes in camlib.CNCJob regarding usage of toolchange (in case it is None)
- fixed preprocessor files to work with toolchange_xy parameter value = None (no values in Edit - Preferences fields)
- fixed Tcl commands CncJob and DrillCncJob to work with toolchange
- added to the preprocessor files the command after toolchange to go with G00 (fastest) to "Z Move" value of Z pozition.

29.01.2019

- fixed issue in Tool Calculators when a float value was entered starting only with the dot.
- added protection for entering incorrect values in Offset and Scale fields for Gerber and Geometry objects (in Selected Tab)
- added more shortcut keys in the Geometry Editor and in Excellon Editor; activated also the zoom (fit, in, out) shortcut keys ('1' , '2', '3') for the editors
- disabled the context menu in tools table on Paint Tool in case that the painting method is single.
- added protection when trying to do Intersection in Geometry Editor without having selected Geometry items.
- fixed the scale, mirror, rotate, skew functions to work with Geometry Objects of multi-geometry type.
- added a GUI for Excellon Search time for OR-TOOLS path optimization in Edit -> Preferences -> Excellon General -> Optimization Time
- more changes in Edit -> Preferences -> Geometry, Gerber and in CNCJob
- added new option for Cutout Tool Freeform Gaps in Edit -> Preferences -> Tools
- fixed Freeform Cutout gaps issue (it was double than the value set)
- added protection so the Cutout (either Freeform or Rectangular) cannot be done on a multigeo Geometry
- added 2Sided Tool default values in Edit -> Preferences -> Tools
- optimized the FlatCAMCNCJob.on_plot_cb_click_table() plot function and solved a bug regarding having tools numbers not in sync with the cnc tool table

28.01.2018

- fixed the GerberObject.merge() function
- added a new menu entry for the Gerber Join function: Edit -> Conversions -> "Join Gerber(s) to Gerber" allowing joining Gerber objects into a final Gerber object
- moved Paint Tool defaults from Geometry section to the Tools section in Edit -> Preferences
- added key shortcuts for Open Manual = F1 and for Open Online VideoHelp = F2

27.01.2018

- added more key shortcuts into the application; they are now displayed in the GUI menu's
- reorganized the Edit -> Preferences -> Global
- redesigned the messagebox that is showed when quiting ot creating a New Project: now it has an option ('Cancel') to abort the process returning to the app
- added options for trace segmentation that can be useful for auto-levelling (code snippet from Lei Zheng from a rejected pull request on FlatCAM https://bitbucket.org/realthunder/ )
- added shortcut key 'L' for creating 'New Excellon' 
- added shortcut key combo 'Shift+S' for Running a Script.
- modified GRBL_laser preprocessor file so it includes a Sxxxx command on the line with M03 (laser active) whenever a value is enter in the Spindlespeed entry field
- remade the EDIT -> PREFERENCES window, the Excellon and Gerber sections. Created a new section named TOOLS

26.01.2019

- fixed grbl_11 preprocessor in linear_code() function
- added icons to the Project Tab context menu
- added new entries to the Canvas context menu (Copy, Delete, Edit/Save, Move, New Excellon, New Geometry, New Project)
- fixed GRBL_laser preprocessor file
- updated function for copy of an Excellon object for the case when the object has slots
- updated ExcellonObject.merge() function to work in case some (or all) of the merged objects have slots  

25.01.2019

- deleted junk folders
- remade the Panelize Tool: now it is much faster, it is multi-threaded, it works with multitool geometries and it works with multigeo geometries too.
- made sure to copy the options attribute to the final object in the case of: GeometryObject.merge(), GerberObject.merge() and for the Panelize Tool
- modified the panelize TclCommand to take advantage of the new panelize() function; added a 'threaded' parameter (default value is 1) which controls the execution of the panelize TclCommand: threaded or non-threaded
- fixed TclCommand Cutout
- added a new TclCommand named CutoutAny. Keyword: cutout_any

24.01.2019

- trying to fix painting single when the actual painted object it's a MultiPolygon
- fixed the Copy Object function when the object is Gerber
- added the Copy entry to the Project context menu
- made the functions behind Disable and Enable project context menu entries, non-threaded to fix a possible issue
- added multiple object selection on Open ... and Import ... (idea and code snippet came from Travers Carter, BitBucket user https://bitbucket.org/travc/)
- fixed 'GRBL_laser' preprocessor bugs (missing functions)
- fixed display geometry for 'GRBL_laser' preprocessor
- Excellon Editor - added possibility to create an linear drill array rotated at an custom angle
- added the Edit and Properties entries to the Project context menu

23.01.2019

- added a new preprocessor file named 'line_xyz' which have x, y, z values on the same GCode line
- fixed calculation of total path for Excellon Gcode file
- modified the way FlatCAM preferences are saved. Now they can be saved as new files with .FlatConfig extension by the user and shared.
- added possibility to open the folder where FlatCAM is saving the preferences files

21.01.2019

- changed some tooltips
- added tooltips in Excellon tool table headers
- in Excellon Tool Table the columns are now only selectable by clicking on the header (sorting is done automatically)
- if CNCJob from Excellon then hide the CNC tools table in CNCJob Object

 
20.01.2019

- fixed the HPGL code geometry rendering when travel
- fixed the message box layout when asking to save the current work
- made sure that whenever the HPGL preprocessor is selected the Toolchange is always ON and the MultiDepth is OFF
- the HPGL preprocessor entry is not allowed in Excellon Object preprocessor selection combobox as it is only applicable for Geometry
- when saving HPGL code it will be saved as a file with extension .plt
- the units mentioned in HPGL format are only METRIC therefore if FlatCAM units are in INCH they will be transform to METRIC
- the minimum unit in HPGL is 0.025mm therefore the coordinates are rounded to a multiple of 0.025mm
- removed the raise statement in do_worker_task() function as this is fatal in conjunction with PyQt5
- added a try - except clause for the situations when for a font can't be determined the family and name
- moved font parsing to the Geometry Editor: it is done everytime the Text tool is invoked
- made sure that the HPGL preprocessor is not populated in the Excellon preprocessors in Preferences as it make no sense (HPGL is useful only for Geometries)

19.01.2019

- added initial implementation of HPGL preprocessor
- fixed display HPGL code geometry on canvas

11.01.2019

- added a status message for font parsing

9.01.2019

- added a fix to allow creating of Excellon geometry even when there are points with no tools by skipping those points and warning the user about this in a Tcl message
- added a message box asking users if they want to save the project in case that either New Project menu entry is clicked or if Exit menu entry is clicked or if the app is closed from the close button. The message box will be showed only if there are objects in the collection.
- modified the first line in the Gcode header to show the FlatCAM version and version_date

8.01.2019

- added checkboxes in Preferences -> General -> Global Preferences to switch on/off version check at application startup and also to control if the app will send anonymous statistics about FlatCAM usage to help improve FlatCAM

7.01.2019

- added tooltips in Edit->Convert menu
- fixed cutting from copper features when doing Gerber isolation with multiple passes

6.01.2019

- fixed the Marlin preprocessor detection in GCode header
- the version date in GCode header is now the one set in FlatCAMApp.App.version_date
- fixed bug in preprocessor files: number of drills is now calculated only for the Excellon objects in toolchange function (only Excellon objects have drills) 

5.01.2019

- fixed cncjob TclCommand - it used the default values for parameters
- fixed the layout in ToolTransform
- fixed the initial text in the ToolShell
- reactivated the version check in case the release is not BETA; FlatCAMApp.App has now a beta object that when set True the application will show in the Title and help-> About that is Beta (and it disable version checking)
- added a new name (mine: for good and/or bad) to the contributors list
- fixed the Join function to work on Gerber and Excellon, Gerber and Gerber, Excellon and Excelon combination of objects. The merged property is the solid_geometry and the result is a GeometryObject object.

3.01.2019

- initial merge into FlatCAM regular

28.12.2018

- changed the workspace drawing from 'gl' to 'agg'. 'gl' has better performance but it messes with the overlapping graphics
- removed the initial obj.build_ui() in App.editor2object()

25.12.2018

- fixed bugs in Excellon Editor due of PyQt5 port
- fixed bug when loading Gerber with follow
- fixed bug that when a Gerber was loaded with -follow parameter it could not be isolated external and full
- changed multiple status bar messages
- changed some assertions to (status error message + return) combo
- fixed issues in 32bit installers
- added protection against using Excellon joining on different kind of objects
- fixed bug in ToolCutout where the Rectangular Cutout used the Type of Gaps from Freeform Cutout
- fixed bug that didn't allowed saving SVG file from a Gerber file
- modified setup_ubuntu.sh file for PyQt5 packages

23.12.2018

- added move (as in Tool Move) capability for CNCJob object and the GCode is updated on each move --> finished both for Gcode loaded and for CNCJob generated in the app
- fixed some errors related to DialogOpen widget that I've missed in PyQt5 porting
- added a bounds() method for CNCJob class in camlib (perhaps overdone as it worked well with the one inherited)
- small changes in Paint Tool - the rest machining is working only partially
- added more columns in CNCjob Tool Table showing more info about the present tools
- make the columns in CNCJob Tool Table not editable as it has no sense

22.12.2018

- fixed issues in Transform Tool regarding the message boxes
- fixed more error in Double Sided Tool and added some more information's in ToolTips
- added more information's in CutOut Tool ToolTips
- updated the tooltips in amost all FlatCAM tools; in Tool Tables added column header ToolTips
- fixed NCC rest machining in NCC Tool; added status message and stop object creation if there is no geometry on any tool
- fixed version number: now it will made of a number in format main_version.secondary_version/working_version
- modified the makefile for windows builds to accommodate both 32bit and 64bit executable generation

21.12.2018

- added shortcut "SHIFT + W" for workspace toggle
- updated the list of shortcuts
- forbid editing for the MultiGeo type of Geometry because the Geometry Editor is not prepared for this
- finished a "sort" of rest-machining for Non Copper Clearing Tool but it's time consuming operation
- reworked the NCC Tool as it was fundamental wrong - still has issues on the rest machining
- added a parameter reset for each run of Paint Tool and NCC Tool

20.12.2018

- porting application to PyQt5
- adjusted the level of many status bar messages
- created new bounds() methods for Excellon and Gerber objects as the one inherited from Geometry failed in conjunction with PyQt5
- fixed some small bugs where a string was divided by a float finally casting the result to an integer
- removed the 'raise' conditions everywhere I could and make protections against loading files in the wrong place
- fixed a "PyCharm stupid paste on the previous tab level even after one free line " in Excellon.bounds()
- in Geometry object fixed error in tool_delete regarding deletion while iterating a dict
- started to rework the NCC Tool to generate one file only
- in Geometry Tool Table added checkboxes for individual plot of tools in case of MultiGeo Geometry
- rework of NCC Tool UI
- added a automatic selector: if the system is 32bit the OR-tools imports are not done and the OR-tools drill path optimizations are replaced by a default Travelling Salesman drill path optimization
- created a Win32 make file to generate a Win32 executable
- disabled the Plot column in Geometry Tool Table when the geometry is SingleGeo as it is not needed
- solved a issue when doing isolation, if the solid_geometry is not a list will make it a list
- added tooltips in the Geometry Tool Table headers explaining each column
- added a new Tcl Command: clear. It clears the Tcl Shell of all text and restore it to the original state
- fixed Properties Tool area calculation; added status bar messages if there is no object selected show an error and successful showing properties is confirmed in status bar
- when Preferences are saved, now the default values are instantly propagated within the application
- when a geometry is MultiGeo and all the tools are deleted, it will have no geometry at all therefore all that it's plotted on canvas that used to belong to it has to be deleted and because now it is an empty object we demote it to SingleGeo so it can be edited

19.12.2018

- fixed SVG_export for MultiGeo Geometries
- fixed DXF_export for MultiGeo Geometries
- fixed SingleGeo to MultiGeo conversion plotting bug

18.12.2018

- small changes in GeometryObject.plot()
- updated the GeometryObject.merge() function and the Join Geometry feature to accommodate the different types of geometries: singlegeo and multigeo type
- added Conversion submenu in Edit where I moved the Join features and added the Convert from MultiGeo to SingleGeo type and the reverse
- added Copy Tool (on a selection of tools) feature in Geometry Object UI 
- fixed the bounds() method for the MultiGeo geometry object so the canvas selection is working and also the Properties Tool
- fixed Move Tool to support MultiGeo geometry objects moving
- added tool edit in Geometry Object Tool Table
- added Tool Table context menu in Geometry Object and in Paint Tool
- modified some Status Bar messages in Geometry Object

17.12.2018

- added support for multiple solid_geometry in a geometry object; each tool can now have it's own geometry. Plot, project save/load are OK.
- added support for single GCode file generation from multi-tool PaintTool job
- added protection for results of Paint Tool job that do not have geometry at all. An Error will be issued. It can happen if the combination of Paint parameters is not good enough
- solved a small bug that didn't allow the Paint Job to be done with lines when the results were geometries not iterable 
- added protection for the case when trying to run the cncjob Tcl Command on a Geometry object that do not have solid geometry or one that is multi-tool
- Paint Tool Table: now it is possible to edit a tool to a new diameter and then edit another tool to the former diameter of the first edited tool
- added a new type of warning, [WARNING_NOTCL]
- fixed conflict with "space" keyboard shortcut for CNC job

16.12.2018

- redone the Options menu; removed the Transfer Options as they were not used
- deleted some folders in the project structure that were never used
- Paint polygon Single works only for left mouse click allowing mouse panning
- added ability to print errors in status bar without raising Tcl Shell
- fixed small bug: when doing interiors isolation on a Gerber that don't allow it, no object is created now and an error in the status bar is issued
- fixed bug in Paint All for Geometry made from exteriors Gerber isolation
- fixed the join geometry: when the geometries has different tools the join will fail with a status bar message (as it should). Allow joining of geometries that have no tool. // Reverted on 18.12.2018
- changed the error messages that are simple to the kind that do not open the TCl shell
- fixed some issues in Geometry Object
- Paint Tool - reworked the UI and made it compatible with the Geometry Object UI
- Paint Tool - tool edit functional
- added Clear action in the Context menu of the TCl Shell

14.12.2018

- fixed typo in setup_ubuntu.sh
- minor changes in Excellon Object UI
- added Tool Table in Paint Tool
- now in Paint Tool and Non Copper Clearing Tool a selection of tools can be deleted (not only one by one)
- minor GUI changes (added/corrected tooltips)
- optimized vispy startup time from about >6 sec to ~3 seconds
- removed vispy text collection starting in plotcanvas as it did nothing // RESTORED 18.12.2018 as it messed the graphical presentation
- fixed cncjob TclCommand for the new type of Geometry
- make sure that when using the TclCommands, the object names are case insensitive
- updated the TCL Shell auto-complete function; now it will index also the names of objects created or loaded in the application
- on object removal the name is removed from the Shell auto-complete model

13.12.2018

NEW Geometry Object and CNC Object architecture (3rd attempt) which allow multiple tools for one geometry

- fixed issue with cumulative G-code after successive delete/create of a CNCJob on the same geometry (some references were kept after deletion of CNCJob object which kept the deleted tools data and added it to a new one)
- fixed plot and export G-code in new format
- fixed project save/load in the new format for geometry
- added new feature in CNCJob Object UI: since we may have multiple tools per CNCJob object due of having multiple tool in Geometry Object,
now there is a Tool Table in CNC Object UI and each tool GCode can be enabled or disabled

12.12.2018

- Geometry Tool Table: when the Offset type is 'custom' each tool it's storing the value and it is updated on UI when that tool is selected in UI table
- Geometry Tool Table: fixed tool offset conversion when the Offset in Tool Table UI is set to Custom

11.12.2018

- cleaned up the generatecncjob() function in FlatCAMObj
- created a new function for generating cncjob out of multitool geometry, mtool_generate_cncjob()
- cleaned up the generate_from_geometry_2() method in camlib
- Geometry Tool Table: new tool added copy all the form fields (data) from the last tool
- finished work on generation of a single CNC Job file (therefore a single GCODE file) even for multiple tools in Geo Tool Table
- GCode header is added only on saving the file therefore the time generation will be reflected in the file
- modified preprocessors to accommodate the new CNC Job file with multiple tools
- modified preprocessors so the last X,Y move will be to the toolchange X,Y pos (set in Preferences)
- save_project and load_project now work with the new type of multitool geometry and cncjob objects

10.12.2018

- added new feature in Geometry Tool Table: if the Offset type in tool table is 'Offset' then a new entry is unhidden and the user can use custom offset
- Geometry Tool Table: fixed add new tool with diameter with many decimals
- Geometry Tool Table: when editing the tip dia or tip angle for the V Shape tool, the CutZ is automatically calculated

9.12.2018

- new Geometry Tool Table has functional unit conversion
- when entering a float number in Spindle Speed now there is no error and only the integer part is used, the decimals are discarded
- finished the Geometry Tool Table in the form that generates only multiple files
- if tool type is V-Shape ('V') then the Cut Z entry is disabled and new 'Tip Dia' and 'Tip Angle' fields are showed. The values entered will calculate the Cut Z parameter

5.12.2018

- remade the Geometry Tool Table, before this change each tool could not store it's own set of data in case of multiple tools with same diameter
- added a new column in Geo Tool Table where to specify which type of tool to use: C for circular, B for Ball and V for V-shape

4.12.2018

- new geometry/excellon object name is now only "new_g"/"new_e" as the type is clear from the category is into (and the associated icon)
- always autoselect the first tool in the Geometry Tool table
- issue error message if the user is trying to generate CNCJob without a tool selected in Geometry Tool Table
- add the whole data from Geometry Object GUI as dict in the geometry tool dict so each tool (file) will have it's own set of data

3.12.2018

- Geometry Tool table: delete multiple tools with same diameter = DONE
- Geometry Tool table: possibility to cut a path inside or outside or on path = DONE
- Geometry Tool table: fixed situation when user tries to add a tool but there is no tool diameter entered
- if a geometry is a closed shape then create a Polygon out of it
- some fixes in Non Copper Clearing Tool
- Geometry Tool table: added option to delete_tool function for delete_all
- Geometry Tool table: added ability to delete even the last tool in tool_table and added an warning if the user try to generate a CNC Job without a tool in tool table
- if a geometry is painted inside the Geometry Editor then it will store the tool diameter used for this painting. Only one tool cn be stored (the last one) so if multiple paintings are done with different tools in the same geometry it will store only the last used tool.
- if multiple geometries have different tool diameters associated (contain a paint geometry) they aren't allowed to be joined and a message is displayed letting the user know

2.12.2018

- started to work on a geometry Tool Table
- renamed FlatCAMShell as ToolShell and moved it (and termwidget) to flatcamTools folder
- cleaned up the ToolShell by removing the termwidget separate file and added those classes to ToolShell
- added autocomplete for TCL Shell - the autocomplete key is 'TAB'
- covered some possible exceptions in rotate/skew/mirror functions
- Geometry Tool table: add/delete tools = DONE
- Geometry Tool table: add multiple tools with same diameter = DONE

1.12.2018

- fixed Gerber parser so now the Gerber regions that have D02 operation code just before the end of the region will be processed correctly. Autotrax Dex Gerbers are now loaded
- fixed an issue with temporary geo storage "geo" being referenced before assignment
- moved all FlatCAM Tools into a single directory

30.11.2018

- remade the CutOut Tool. I've put together the former Freeform Cutout tool and the Cutout Object fount in Gerber Object GUI and left only a link in the Gerber Object GUI. This tidy the GUI a bit.
- created a Paint Tool and replaced the Paint Area section in Geometry Object GUI with a link to this tool.
- fixed bug in former Paint Area and in the new Paint Tool that made the paint method not to be saved in App preferences
- solved a bug in Gerber parser: in case that an operation code D? was encountered alone it was not remembered - fixed
- fixed bug related to the newly entered toolchange feature for Geometry: it was trying to evaluate toolchange_z as a comma separated value like for toolchange x,y
- fixed bug in scaling units in CNC Job which made the unit change between INCH and MM not possible if a CNC Job was present in the project objects

29.11.2018

- added checks for using a Z Cut with positive value. The Z Cut parameter has to be negative so if the app will detect a positive value it will automatically convert it to negative
- started to implement rest-machining for Non Copper clearing Tool - for now the results are not great
- added Toolchange X,Y position parameters and modified the default and manual_toolchange preprocessor file to use them
For now they are used only for Excellon objects who do have toolchange events
- added Toolchange event selection for Geometry objects; for now it is as before, single tool on each file
- remade the GUI for objects and in Preferences to have uniformity
- fixed bug: after editing a newly created excellon/geometry object the object UI used to not keep the original settings
- fixed some bugs in Tool Add feature of the new Non Copper Clear Tool
- added some messages in the Non Copper Clear Tool
- added parameters for coordinates no of decimals and for feedrate no of decimals used in the resulting GCODE. They are in EDIT -> Preferences -> CNC Job Options
- modified the preprocessors to use the "decimals" parameters

28.11.2018

- added different methods of copper clearing (standard, seed, line_based) and "connect", "contour" options found in Paint function
- remake of the non-copper clearing tool as a separate tool
- modified the "About" menu entry to mention the main contributors to FlatCAM 3000 
- modified Marlin preprocessor according to modifications made by @redbull0174 user from FlatCAM.org forum
- modified Move Tool so it will detect if there is no object to move and issue a message

27.11.2018

- fixed bug in isolation with multiple passes
- cosmetic changes in Buffer and Paint tool from Geometry Editor
- changed the way selection box is working in Geometry Editor; now cumulative selection is done with modifier key (SHIFT or CONTROL) - before it was done by default
- changed the default value for CNCJob tooldia to 1mm

25.11.2018

- each Tool change the name of the Tools tab to it's name
- all open objects are no longer autoselected upon creation. Only on new Geometry/Excellon object creation it will be autoselected

24.11.2018

- restored the selection method in Geometry Editor to the original one found in FlatCAM 8.5
- minor changes in Clear Copper function
- minor changes in some preprocessors
- change Join Geometry menu entry to Join Geo/Gerber
- added menu entry for Toggle Axis in Menu -> View
- added menu entry for Toggle Workspace in Menu -> View
- added Bounding box area to the Properties (when metric units, in cm2)
- non-copper clearing function optimization
- fixed Z_toolchange value in the GCODE header

21.11.2018

- not very precise jump to location function
- added shortcut key for jump to coordinates (J) and for Tool Transform (T)
- some work in shortcut key

19.11.2018

- fixed issue with nested comment in preprocessors
- fixed issue in Paint All; reverted changes

18.11.2018

- renamed FlatCAM 2018 to FlatCAM 3000
- added new entries in the Help menu; one will show shortcut list and the other will start a YouTube webpage with a playlist where I will publish future training videos for this version of FlatCAM
- if a Gerber region has issues the file will be loaded bypassing the error but there will be a TCL message letting the user know that there are parser errors. 

17.11.2018

- added Excellon parser support for units defined outside header


12.11.2018

- fixed bug in Paint Single Polygon
- added spindle speed in laser preprocessor
- added Z start move parameter. It controls the height at which the tool travel on the fist move in the job. Leave it blank if you don't need it.

9.11.2018

- fixed a reported bug generated by a typo for feedrate_z object in camlib.py. Because of that, the project could not be saved.
- fixed a G01 usage (should be G1) in Marlin preprocessor.
- changed the position of the Tool Dia entry in the Object UI and in MainGUI
- fixed issues in the installer

30.10.2018

- fixed a bug in Freeform Cutout Tool - it was missing a change in the name of an object

29.10.2018

- added Excellon export menu entry and functionality that can export in fixed format 2:4 LZ INCH (format that Altium can load and it is a more generic format).
It will be usefull for those who need FlatCAM to only convert the Excellon to a more useful format and visualize Gerbers.
The other Excellon Export menu entry is exporting in units either Metric or INCH depending on the current units in FlatCAM, but it will always use the decimal format which may not be loaded in all cases.
- disabled the Selected Tab while in Geometry Editor; the user is not supposed to have access to those functions while in Geometry Editor
- added an menu entry in Menu -> File -> Recent Files named Clear Recent files which does exactly that
- fixed issue: when a New Project is created but there is a Geometry still in Geometry Editor (or Excellon Editor) not saved, now that geometry is deleted
- fixed problem when doing Clear Copper with Cut over 1st point option active. When the shape is not closed then it may cut over copper features. Originally the feature was meant to be used only with isolation geometry which is closed. Fixed

28.10.2018

- fixed Excellon Editor shortcut messages; also fixed differences in messages between usage by shortcuts and usage by menu toolbar actions
- fixed Excellon Editor bug: it was triggering exceptions when the user selected a tool in tooltable and then tried to add a drill (or array) by clicking on canvas
Clicking on canvas by default clear all the used tools, therefore the action could not be done. Fixed.
- fixed bug Excellon Editor: when all the drills from a tool are resized, after resize they can't be selected.
- Excellon Editor: added ability to delete multiple tools at once by doing multiple selection on the tooltable
- Excellon Editor: if there are no more drills to a tool after doing drills resize then delete that tool from the tooltable
- Excellon Editor: always select the last tool added to the tooltable
- Excellon Editor: added a small canvas context menu for Excellon Editor

27.10.2018

- added a Paint tool toolbar icon and added shortcut key 'I' for Paint Tool
- fixed unreliable multiple selection in Geometry Editor; some clicks were not registered
- added utility geometry for Add Drill Array in Excellon Editor
- fixed bug Excellon Editor: drills in drill array start now from the array start point (x, y); previously array start point was used only for calculating the radius
- fixed bug Excellon Editor: Measurement Tool was not acting correctly in Exc Editor regarding connect/disconnect of events
- in Excellon Editor every time a tool is clicked (except Select which is the default) the focus will return to Selected tab
- added protection in Excellon Editor: if there is no tool/drill selected no operation over drills can be performed and a status bar message will be displayed
- Excellon Editor: added relevant messages for all actions
- fixed bug Excellon Editor: multiple selection with key modifier pressed (CTRL/SHIFT) either by simple click or through selection box is now working
- fixed dwell parameter for Excellon in Preferences to be default Off

26.10.2018

- when objects are disabled they can't be selected
- added Feedrate_z (Plunge) parameter for Geometry Object
- fixed bug in units convert for Geometry Tab; added some missing parameters to the conversion list
- fixed bug in isolation Geometry when the isolated Gerber was a single Polygon
- updated the Paint function in Geometry Editor

25.10.2018

- added a verification on project saving to make sure that the project was saved successfully. If not, a message will be displayed in the status bar saying so.

20.10.2018

- fixed the SVG import as Gerber. But unfortunately, when there is a ground pour in a imported PCB SVG, the ground pour will be isolated inside
instead to be isolated outside like every other feature. That's no way around this. The end result will be thinner features
for the ground pour and if one is relying on those thin connections as GND links then it will not work as intended ,they may be broken.
Of course one can edit the isolation geometry and delete the isolation for the ground pour.
- delete selection shapes on double clicking on object as we may not want to have selection shape while Selected tab is active

19.10.2018

- solved some value update bugs in tool_table in Excellon Editor when editing tools followed by deleting another tool,
and then re-adding the just-deleted tool.
- added support for chaining blocks in DXF Import
- fixed the DXF arc import
- added support for a type of Gerber files generated by OrCAD where the Number format is combined with G74 on the same line
- in Geometry Editor added the possibility for buffer to use different kinds of corners
- added protection against loading an GCODE file as Excellon through drag & drop on canvas or file open dialog
- added shortcut key 'B' for buffer operation inside Geometry Editor
- added shell message in case the Font used in Text Tool in Geometry editor is not supported. Only Regular, Bold, Italic adn BoldItalic are supported as of yet.
- added shortcut key 'T' for Text Tool inside Geometry Editor
- added possibility for Drag & Drop on FlatCAM GUI with multiple files at once 

18.10.2018

- fixed DXF arc import in case of extrusion enabled
- added on Geo Editor Toolbar the button for Buffer Geometry; added the possibility to create exterior and interior buffer
- fixed a numpy import error

17.10.2018

- added Spline support and Ellipse (chord) support in DXF Import: chord might have issues
(borrowed from the work of Vasilis Vlachoudis, https://github.com/vlachoudis/bCNC)
- added Block support in DXF Import - no support yet for chained blocks (INSERT in block)
- support for repasted block insertions

16.10.2018

- added persistent toolbar view: the enabled toolbars will be active at the next app startup while those that are not enabled will not be
enabled at the next app startup. To enable/disable toolbars right click on the toolbar.

15.10.2018

- DXF Export works now also for Exteriors only and Interiors only geometry generated from Gerber Object
- when a Geometry is edited, now the interiors and exterior of a Polygon that is part of the Geometry can be selected individually. In practice, if
doing full isolation geometry, now both external and internal trace can be selected individually.

13.10.2018

- solved issue in CNC Code Editor: it appended text to the previous one even if the CNC Code Editor was closed
- added .GBD Gerber extension to the lists
- added support for closed polylines/lwpolylines in Import DXF; now PCB patterns found in PDF format can be imported in INKSCAPE
and saved as DXF. FlatCAM can import DXF as Gerber and the user now can do isolation on it.

12.10.2018

- added zoom in, zoom out and zoom fit buttons on the View toolbar
- fixed bug that on Double Sided Tool when a Excellon Alignment is created does not reset the list of Alignment drills
- added a message warning the user to add Point coordinates in case the reference used in Double Sided Tool is Point
- added new feature: DXF Export for Geometry

10.10.2018

- fixed a small bug in Setup Recent Files
- small fix in Freeform Cutout Tool regarding objects populating the combo boxes
- Excellon object name will reflect the number of edits performed on it

9.10.2018

- In Geometry Editor, now Path and Polygon draw mode can be finished not only with shortcut key Enter but also with right click on canvas
- fixes regarding of circle linear approximation - final touch
- fix for interference between Geo Editor and Excellon Editor
- fixed Cut action in Geometry Editor so it can now be done multiple times on the target geometry without need for saving in between.
- initial work on DXF import; made the GUI interface and functional structure
- added import functions for DXF import
- finished DXF Import (no blocks support, no SPLINE support for now)

8.10.2018

- completed toggle canvas selection when there is only one object under click position for the case when clicking the object is done
while other object is already selected.
- added static utility geometry just upon activating an Editor function
- changed the way the canvas is showed on FlatCAM startup

7.10.2018

- solved mouse click not setting relative measurement origin to zero
- solved bug that always added one drill when copying a selection of drills in the EXCELLON EDITOR
- solved bug that the number of copied drills in Excellon Editor was not updated in the tool table
- work in the Excellon Editor: found useful to change the diameter of one tool to another already in the list;
could help for all those tools that are a fraction difference that comes from imperial to mm (or reverse) conversion,
to reduce the tool changes - Done
- in Excellon Editor, always auto-select the last tool added
- in Excellon Editor fixed shortcuts for drill add and drill_array add: they were reversed. Now key 'A' is for array add
and key 'D' is for drill add
- solved a small bug in Excellon export: even when there were no slots in the file, it always added the tools list that
acted as unnecessary toolchanges
- after Move action, all objects are deselected


6.10.2018

- Added basic support for SVG text in SVG import. Will not work if some letters in a word have different style (italic bold or both)
- added toggle selection to the canvas selection if there is only one object under the click position
- added support for "repeat" command in Excellon file
- added support for Allegro Gerber and Excellon files
- Python 3.7 is used again; solved bug where the activity icon was not playing when FlatCAM active

5.10.2018

- fixed undesired setting focus to Project Tab when doing the SHIFT + LMB combo (to capture the click coordinates)

4.10.2018

- Excellon Editor: finished Add Drill Array - Linear type action
- Excellon Editor: finished Add Drill Array - Circular type action
- detected bug in shortcuts: Fixed
- Excellon Editor: added constrain for adding circular array, if the number of drills multiplied by angle is more than 360
the app will return with an message
- solved sorting bug in the Excellon Editor tool table
- solved bug in Menu -> Edit -> Sort Origin ; the selection box was not updated after offset
- added Excellon Export in Menu -> File -> Export -> Export Excellon
- added support to save the slots in the Excellon file in case there were some in the original file
- fixed Double Sided Tool for the case of using the box as mirroring reference.

2.10.2018

- made slots persistent after edit
- bug detected: in Excellon Editor if new tool added diameter is bigger than 10 it mess things up: SOLVED
- Excellon Editor: finished Drill Resize action
- after an object is deleted from the Project list, if the current tab in notebook is not Project,
always focus in the Project Tab (deletion can be done by shortcut key also)
- changed the initial view to include the possible enabled workspace guides

1.10.2018

- added GUI for Excellon Editor in the Tool Tab
- Excellon Editor: created and populated the tool list
- Excellon Editor: added possibility to add new tools in the list
- Excellon Editor: added possibility to delete a tool (and the drills that it contain) by selecting a row in the tool table and 
clicking the Delete Tool button
- Excellon Editor: added possibility to change the tool diameter in the tool list for existing tool diameters.
- Excellon Editor: when selecting a drill, it will highlight the tool in the Tool table
- Excellon Editor: optimized single click selection
- Excellon Editor: added selection for all drills with same diameter upon tool selection in tool table; fix in tool_edit
- Excellon Editor: added constrain to selection by single click, it will select if within a certain area around the drill
- Excellon Editor: finished Add Drill action
- Excellon Editor: finished Move Drill action
- Excellon Editor: finished Copy Drill action

- fixed issue: when an object is selected before entering the Editor mode, now the selecting shape is deleted before entry 
in the Editor (be it Geometry or Excellon).
- fixed a few glitches regarding the units change
- when an object is deselected on the Plot Area, the notebook will switch to Project Tab
- changed the selection behavior for the dragging rectangle selection box in Editor (Geometry, Excellon): by dragging a
selection box and selecting is cumulative: it just adds. To remove from selection press key Ctrl (or Shift depending of 
the setting in the Preferences) and drag the rectangle across the objects you want to deselect.

29.09.2018

- optimized the combobox item population in Panelization Tool and in Film Tool
- FlatCAM now remember the last path for saving files not only for opening
- small fix in GUI
- work on Excellon Editor. Excellon editor working functions are: loading an Excellon object into Editor, 
saving an Excellon object from editor to FlatCAM, selecting drills by left click, selection of drills by dragging rectangle, deletion of drills.
- fixed Excellon merge
- added more Gcode details (depthperpass parameter in Gcode header) in preprocessors
- deleted the Tool informations from header in preprocessors due to Mach3 not liking the lot of square brackets
- more corrections in preprocessors


28.09.2018

- added a save_defaults() call on App exit from action on Menu -> File -> Exit
- solved a small bug in Measurement Tool
- disabled right mouse click functions when Measurement Tools is active so the user can do panning and find the destination point easily
- added a new button named "Measure" in Measurement Tool that allow easy access to Measurement Tool from within the tool
- fixed a bug in Gerber parser that when there was a rectangular aperture used within a region, some artifacts were generated.
- some more work on Excellon Editor

27.09.2018

- fixed bug when creating a new project, if a previous object was selected on screen, the selection shape survived the creation of a new project
- added compatibility with old type of FlatCAM projects
- reverted modifications to the way that Excellon geometry was stored to the old way.
- added exceptions for Paint functions so the user can know if something failed.
- modified confirmation messages to use the color coded messages (error = red, success = green, warning = yellow)
- restored activity icon

26.09.2018

- disabled selection of objects in Project Tab when in Editor
- the Editor Toolbar is hidden in normal mode and it is showed when Editor is activated. I may change this behaviour back.
- changed names in classes, functions to prepare for the Excellon editor

- fixed bugs in Paint All function
- fixed a bug in ParseSVG module in parse_svg_transform(), related to 'scale'

- moved all the Editor menu/toolbar creation to FlatCAMUI where they belong
- fixed a Gerber parse number issue when Gerber zeros are TZ (keep trailing zeros)

- changed the way of how the solid_geometry for Excellon files is stored and plotted. Before everything was put in the same "container". Now, the geometries of drills and slots are organized into dictionaries having as keys the tool diameters and as values list of Shapely objects (polygons)
- fix for Excellon plotting for newly created empty Excellon Object
- fixed geometry.bounds() in camlib to work with the new format of the Excellon geometry (list of dicts)

24.09.2018

- added packages in the Requirements and setup_ubuntu.sh. Tested in Ubuntu and it's OK
- added Replace (All) feature in the CNC Code Editor
- made CNC Code generation for Excellon to show progress
- added information about transforms in the object properties (like skew and how much, if it was mirrored and so on)
- made all the transforms threaded and make them show progress in the progress bar
- made FlatCAM project saving, threaded.
 
23.09.2018

- added support for "header-less" Excellon files. It seems that Mentor PADS does generate such non-standard Excellon files. The user will have to guess: units (IN/MM), type of zero suppression LZ/TZ  (leading zeros or trailing zeros are kept) and Excellon number format(digits and decimals).  All of those can be adjusted in Menu -> Edit -> Preferences -> Excellon Object -> Excellon format
- fixed svgparse for Path. Now PCB rasted images can traced in Inkscape or PDF's can be converted and then saved as SVG files which can be imported into FlatCAM. This is a convolute way to convert a PDF to Gerber file.

22.09.2018

- added Drag & Drop capability. Now the user can drag and drop to FlatCAM GUI interface a file (with the right extension) that can be a FlatCAM project file (.FlatPrj) a Gerber file, an Excellon file, a G-Code file or a SVG file.
- made the Move Tool command threaded
- added Image import into FlatCAM

21.09.2018

- added new information's in the object properties: all used Tool-Table items are included in a new entry in self.options dictionary
- modified the preprocessor files so they now include information's about how many drills (or slots) are for each tool. The Gcode will have this information displayed on the message from ToolChange.
- removed some log.debug and add new log.debug especially for moments when some process is finished
- fixed the utility geometry for Font geometry in Geometry Editor
- work on selection in Geometry Editor
- added multiple selection key as a Preference in Menu -> Edit -> Preferences It can be either Shift or Ctrl.
- fixed bug in Gerber Object -> Copper Clearing.
- added more comprehensive tooltips in Non-copper Clearing as advice on how to proceed.
- adjusted make_win32.py file so it will work with Python 3.7 (cx_freeze can't copy OpenGL files, so it has to be done manually)

19.09.2018

- optimized loading FlatCAM project by double clicking on project file; there is no need to clean up everything by using the function not Thread Safe: on_file_new() because there is nothing to clean since FlatCAM just started.

- added a workspace delimitation with sizes A3, A4 and landscape or portrait format
- The Workspace checkbox in Preferences GUI is doing toggle on the workspace
- made the workspace app default state = False
- made the workspace to resize when units are changed
- disabled automatic defaults save (might create SSD wear)
- added an automatic defaults save on FlatCAM application close
- made the draw method for the Workspace lines 'agg' so the quality of the FC objects will not be affected

- added Area constrain to the Panelization Tool: if the resulting area is too big to fit within constrains, the number of columns and/or rows will be reduced to the maximum that still fits is.
- removed the Flip command from Panelization Tools because Flipping (Mirroring) should be done properly with the Transform Tool or using the provided shortcut keys.

- made Font parsing threaded so the application will not wait for the font parsing to complete therefore the app start is faster


17.09.2018

- fixed Measuring Tool not working when grid is turned OFF
- fixed Roland MDX20 preprocessor
- added a .GBR extension in the open_gerber filter
- added ability to Scale and Offset (for all types of objects) to just press Enter after entering a value in the Entry just like in Tool Transform
- added capability in Tool Transform to mirror(flip) around a certain Point. The point coordinates can either be entered by hand or they can be captured by left clicking while pressing key "SHIFT" and then clicking the Add button
- added the .ROL extension when saving Machine Code
- replaced strings that reference to G-Code from G-Code to CNC Code
- added capability to open a project by serving the path/project_name.FlatPrj as a parameter to FlatCAM.py

15.09.2018

- removed dwell line generator and included dwell generation in the preprocessor files
- added a proposed RML1 Roland_MDX20 preprocessor file.
- added a limit of 15mm/sec (900mm/min) to the feedrate and to the feedrate_rapid. Anything faster than this will be capped to 900mm/min regardless what is entered in the program GUI. This is because Roland MDX-20 has a mechanical limit of the speed to 15mm/sec (900mm/min in GUI)

14.09.2018
- remade the Double Sided Tool so it now include mirroring of Excellon and Geometry Objects along Gerber. Made adding points easier by adding buttons to GUI that allow adding the coordinates captured by left mouse click + SHIFT key
- added a few fixes in code to the other FlatCAM tools regarding reset_fields() function. The issue was present when clicking New Project entry in Menu -> File.
- FIXED: fix adding/updating bounding box coords for the mirrored objects in Double side Tool.
- FIXED: fix the bounding box values from within FlatCAM objects, upon units change.
- fixed issue with running again the constructor of the drawing tools after the tool action was complete, in Geometry Editor
- fixed issue with Tool tab not closed after Text Input tool is finished.
- fixed issue with TEXT to GEOMETRY tool, the resulting geometry was not scaled depending of current units
- fixed case when user is clicking on the canvas to place a Font Geometry without clicking apply button first or the Font Geometry is empty, in Geometry Editor - > Text Input tool
- reworked Measuring Tool by adding more information's (START, STOP point coordinates) and remade the strings
- added to Double Sided Tool the ability to use as reference box Excellon and Geometry Objects

12.09.2018

- fixed Excellon Object class such that Excellon files that have both drills and slots are supported
- remade the GUI interface for the Excellon Object in a more compact way; added a column with slots numbers (if any) along the drills numbers so now there is only one tool table for drills and slots.
- remade the GUI in Preferences and removed unwanted stretch that was broken the layout.
- if for a certain tool, the slots number is zero it will not be displayed
- reworked Text to Geometry feature to work in Linux and MacOS
- remade the Text to Geometry so font collection process is done once at app start-up improving the performance


09.09.2018

- added TEXT ENTRY SUPPORT in Geometry Editor. It will convert strings of True Type Fonts to geometry. The actual dimensions are approximations because font size is in points and not in metric or inch units. For now full support is limited to Windows. In Linux/MacOS only the fonts for which the font name is the same as the font filename are supported. Italic and Bold functions may not work in Linux/MacOS.
- solved bug: some Drawing menu entries not having connected functions

28.08.2018

- fixed Gerber parser so now G01 "moving" rectangular aperture is supported.
- fixed import_svg function; it can import SVG as geometry (solved bug)
- fixed import_svg function; it can import SVG as Gerber (it did not work previously)
- added menu entry's for SVG import as Gerber and separated import as Geometry

27.08.2018

- fixed Gerber parser so now FlatCAM can load Gerber files generated by Mentor Graphics EDA programs.

26.08.2018

- added awareness for missing coordinates in Gerber parsing. It will try to use the previous coordinates but if there are not any those lines will be ignored and an Warning will be printed in Tcl Shell.
- fixed TCL commands AlignDrillGrid and DrilCncJob
- added TCL script file load_and_run support in GUI
- made the tool_table in Excellon to automatically adjust the table height depending on the number of rows such that all the rows will be displayed.
- structural changes in the Excellon build_ui()
- icon changes and menu compress

23.08.2018

- added Excellon routing support
- solved a small bug that crippled Excellon slot G85 support when the coordinates are with period.
- changed the way selection is done in Geometry Editor; now it should work in all cases (although the method used may be computationally intensive, because sometimes you have to click twice to make selection if you do it too fast)

21.08.2018

- added Excellon slots support when using G85 command for generation of the slots file. Inspired from the work of @mgix. Thanks. Routing format support for slots will follow. 
- minor bug solved: option "Cut over 1st pt" now has same name both in Preferences -> Geometry Options and in Selected tab -> Geomety Object. Solves #3
- added option to select Climb or Conventional Milling in Gerber Object options Solves #4
- made "Combine passes" option to be saved as an app preference
- added Generate Exteriors Geo and Generate Interiors Geo buttons in the Gerber Object properties
- added configuration for the number of steps used for Gerber circular aperture linear approximation. The option is in Preferences -> Gerber Options
- added configuration for the number of steps used for Gcode circular aperture linear approximation. The option is in Preferences -> CNCjob Options
- added configuration for the number of steps used for Geometry circular aperture linear approximation. The option is in Preferences -> Geometry Options. It is used on circles/arcs made in Geometry Editor and for other types of geometries generated in the app.

17.07.2018

- added the required packages in Requirements.txt file
- added required packages in setup_ubuntu.sh file
- added color control over almost all the colors in the application; those settings are in Menu -> Edit -> Preferences -> General Tab
- added configuration of which mouse button to be used when panning (MMB or RMB)
- fixed bug with missing 'drillz' parameter in function generate_from_excellon_by_tool() (credits for finding it goes to Stefan Smith https://bitbucket.org/stefan064/)
- load Factory defaults in Preferences will load the defaults that are used just after first install. Load Defaults option in Preferences will load the User saved Defaults.

03.07.2018

- fixed bug in rotate function that didn't update the bounding box of the modified object (rotated) due of not emitting the right signal parameter.
- removed the Options tab from the Notebook (the left area where is located also the Project tab). Replaced it with the Preferences Tab launched with Menu -> Edit -> Preferences
- when FlatCAM is used under MacOS, multiple selection of shapes in Editor mode is done using SHIFT key instead of CTRL key due of MacOS interpreting Ctrl+LMB_click as a RMB click
- when in Editor, clicking not on a shape, reset the index of selected shapes to zero
- added a new Tab in the Plot Area named Gcode Editor. It allow the user to edit the Gcode and then Save it or Print it.
- added a fix so the 'preamble' Gcode is correctly inserted between the comments header and the actual GCODE
- added Find function in G-Code Editor

27.06.2018

- the Plot Area tab is changing name to "Editor Area" when the Editor is activated and returns to the "Plot Area" name upon exiting the Editor
- made the labels shorter in Transform Tool in anticipation of Options Tab removal from Notebook and replacing it with Preferences
- the Excellon Editor is not finished (not even started yet) so the Plot Area title should stay "Plot Area" not change to "Editor Area" when attempting to edit an Excellon file. Solved.
- added a header comment block in the generated Gcode with useful information's
- fixed issue that did not allow the Nightly's to be run in Windows 7 x64. The reason was an outdated DLL file (freetype.dll) used by Vispy python module.

25.06.2018

- "New" menu entry in Menu -> File is renamed to "New Project"
- on "New Project" action, all the Tools are reinitialized so the Tools tab will work as expected
- fixed issue in Film Tool when generating black film
- fixed Measurement Tool acquiring and releasing the mouse/key events
- fixed cursor shape is updated on grid_toggle
- added some infobar messages to show the user when the Editor was activated and when it was closed (control returned to App).
- added thread usage for Film tool; now the App is no longer blocked on film generation and there is a visual clue that the App is working

22.06.2018

- added export PNG image functionality and menu entry in Menu -> File -> Export PNG ...
- added a command to set focus on canvas inside the mouve move event handler; once the mouse is moved the focus is moved to canvas so the shortcuts work immediatly.
- solved a small bug when using the 'C' key to copy name of the selected object to clipboard
- fixed millholes() function and isolate() so now it works even when the tool diameter is the same as the hole diameter.

Actually if the passed value to  the buffer() function is zero, I
artificially add a value of 0.0000001 (FlatCAM has a precision of
6 decimals so I use a tenth of that value as a pseudo "zero")
because the value has to be positive. This may have solved for some use
cases the user complaints that on clearing the areas of copper there is
still copper leftovers.

- added shortcut "Shift+G" to toggle the axis presence. Useful when one wants to save a PNG file.
- changed color of the grid from 'gray' to 'dimgray'
- the selection shape is deleted when the object is deleted
- the plot area is now in a TAB.
- solved bug that allowed middle button click to create selection
- fixed issue with main window geometry restore (hopefully).
- made view toolbar to be hidden by default as it is not really needed (we have the functions in menu, zoom is done with mouse wheel, and there is also the canvas context menu that holds the functionality)
- remade the GUIElements.FCInput() and made a GUIElements.FCTab()
- on visibility plot toogle the selection shape is deleted
- made sure that on panning in Geometry editor, the context menu is not displayed
- disabled App shortcut keys on entry in Geometry Editor so only the local shortcut keys are working
- deleted metric units in canvas context menu
- added protection so object deletion can't be done until Geometry Editor session is finished. Solved bug when the shapes on Geometry Editor were not transferred to the New_geometry object yet and the New_Geometry object is deleted. In this case the drawn shapes are left in a intermediary state on canvas.
- added selection shape drawing in Geometry Editor preserving the current behavior: click to select, click on canvas clear selection, Ctrl+click add to selection new shape but remove from selection if already selected. Drag LMB from left to right select enclosed shapes, drag LMB from right to left select touching shapes. Now the selection is made based on
- added info message to be displayed in infobar, when a object is renamed

20.06.2018

- there are two types of mouse drag selection (rectangle selection). If there is a rectangle selection from left to right, the color of the selection rectangle is blue and the selection is "enclosing" - this means that the object to be selected has to be enclosed by the selecting blue rectangle shape. If there is a rectangle selection fro right to left, the color of the selection rectangle is green and the selection is "touching" - this means that it's enough to touch with the selecting green rectangle the object(s) to be selected so they become selected
- changed the modifier key required to be pressed when LMB is ckicked over canvas in order to copy to clipboard the coordinates of the click, from CTRL to SHIFT. CTRL will be used for multiple selection.
- change the entry names in the canvas context menu
- disconnected the app mouse event functions while in geometry editor since the geometry editor has it's own mouse event functions and there was interference between object and geometry items. Exception for the mouse release event so the canvas context menu still work.
- solved a bug that did not update the obj.options after a geometry object was edited in geometry editor
- solved a bug in the signal that saved the position and dimensions of the application window.
- solved a bug in app.on_preferences() that created an error when run in Linux

18.06.2018 Update 1

- reverted the 'units' parameter change to 'global_units' due of a bug that did not allow saving of the project
- modified the camlib transform (rotate, mirror, scale etc) functions so now they work with Gerber file loaded with 'follow' parameter

18.06.2018

- reworked the Properties context menu option to a Tool that displays more informations on the selected object(s)
- remade the FlatCAM project extension as .FlatPrj
- rearranged the toolbar menu entries to a more properly order
- objects can now be selected on canvas, a blue polygon is drawn around when selected
- reworked the Tool Move so it will work with the new canvas selection
- reworked the Measurement Tool so it will work with the new canvas selection
- canvas selection can now be done by dragging left mouse boutton and creating a selection box over the objects
- when the objects are overlapped on canvas, the mouse click selection works in a circular way, selecting the first, then the second, then ..., then the last and then again the first and so on.
- double click on a object on canvas will open the Selected Tab
- each object store the bounding box coordinates in the options dict
- the bbox coordinates are updated on the obj options when the object is modified by a transform function (rotate, scale etc)


15.06.2018

- the selection marker when moving is now a semitransparent Polygon with a blue border
- rectified a small typo in the ToolTip for Excellon Format for Diptrace excellon format; from 4:2 to 5:2
- corrected an error that cause no Gcode could be saved

14.06.2018

- more work on the contextual menu
- added Draw context menu
- added a new tool that bring together all the transformations, named Transformation Tool (Rotate, Skew, Scale, Offset, Flip)
- added shorcut key 'Q' which toggle the units between IN and MM
- remade the Move tool, there is now a selection box to show where the move is done
- remade the Measurement tool, there is now a line between the start point of measurement and the end point of the measurement.
- renamed most of the system variables that have a global app effect to global_name where name is the parameter (variable)

9.06.2018

- reverted to PyQt4. PyQt5 require too much software rewrite
- added calculators: units_calculator and V-shape Tool calculator
- solved bug in Join Excellon
- added right click menu over canvas

6.06.2018 Update

- fixed bug: G-Code could not be saved
- fixed bug: double clicking a category in Project Tab made the app to crash
- remade the bounds() function to work with nested lists of objects as per advice from JP which made the operation less performance taxing.
- added shortcut Shift+R that is complement to 'R'
- shorcuts 'R' and 'Shift+R' are working now in steps of 90 degrees instead of previous 45 degrees.
- added filters in the open ... FlatCAM projects are saved automatically as *.flat, the Gerber files have few categories. So the Excellons and G-Code and SVG.

6.06.2018

- remade the transform functions (rotate, flip, skew) so they are now working for joined objects, too
- modified the Skew and Rotate comamands: if they are applied over a selection of objects than the origin point will be the center of the biggest bounding box. That allow for perfect sync between the selected objects
- started to modify the program so the exceptions are handled correctly
- solved bug where a crash occur when ObjCollection.setData didn't return a bool value
- work in progress for handling situations when a different file is loaded as another (like loading a Gerber file using Open Excellon commands.
- added filters on open_gerber and open_excellon Dialogs. There is still the ability to select All Files but this should reduce the cases when the user is trying to oprn a file from a wrong place.

4.06.2018

- finished PyQt4 to PyQt4 port on the Vispy variant (there were some changes compared with the Matplotlib version for which the port was finished some time ago)
- added Ctrl+S shortcut for the Geometry Editor. When is activated it will save de geometry ("update") and return to the main App.
- modified the Mirror command for the case when multiple objects are selected and we want to mirror all together. In this case they should mirror around a bounding box to fill all.

3.06.2018

- removed the current drill path optimizations as they are inefficient
- implemented Google OR-tools drill path optimization in 2 flavors; Basic OR-tools TSP algorithm and OR-Tools Metaheuristics Guided Local Path
- Move tool is moved to Menu -> Edit under the name Move Object

- solved some internal bugs (info command was creating an non-fatal error in PyQt, regarding using QPixMaps outside GUI thread
- reworked camlib number parsing (still had some bugs)
- working in porting the application from usage of PyQt4 to PyQt4
- added TclCommands save_sys and list_sys. save_sys is saving all the system default parameters and list_sys is listing them by the first letters. listsys with no arguments will list all the system parameters.

29.05.2018

- modified the labels for the X,Y and Dx,Dy coordinates
- modified the menu entries, added more icons
- added initial work on a Excellon Editor
- modified the behavior of when clicking on canvas the coordinates were copied to cliboard: now it is required to press CTRL key for this to happen, and it will only happen just for left mouse button click
- removed the autocopy of the object name on new object creation
- remade the Tcl commands drillcncjob and cncjob
- added fix so the canvas is focused on the start of the program, therefore the shortcuts work without the need for doing first a click on canvas.

28.05.2018

- added total drill count column in Excellon Tool Table which displays the total number of drills
- added aliases in panelize Tool (pan and panel should work)
- modified generate_milling method which had issues from the Python3 port (it could not sort the tools due of dict to dict comparison no longer possible).
- modified the 'default' preprocessor in order to include a space between the value of Xcoord and the following Y
- made optional the using of threads for the milling command; by default it is OFF (False) because in the current configuration it creates issues when it is using threads
- modified the Panelize function and Tcl command Panelize. It was having issues due to multithreading (kept trying to modify a dictionary in redraw() method)and automatically selecting the last created object (feature introduced by me). I've added a parameter to the app_obj.new_object method, named autoselected (by default it is True) and in the panelize method I initialized it with False.
By initializing the plot parameter with False for the temporary objects, I have increased dramatically the  generation speed of the panel because now the temporary object are no longer ploted which consumed time.
- replaced log.warn() with log.warning() in camlib.py. Reason: deprecated
- fixed the issue that the "Defaults" button was having no effect when clicked and Options Combo was in Project Options
- fixed issue with Tcl Shell loosing focus after each command, therefore needing to click in the edit line before we type a new command (borrowed from @brainstorm
- added a header in the preprocessor files mentioning that the GCODE files were generated by FlatCAM.
- modified the number of decimals in some of the line entries to 4.
- added an alias for the millholes Tcl Command: 'mill'

27.04.2018

- modified the Gerber.scale() function from camlib.py in order to allow loading Gerber files with 'follow' parameter in other units than the current ones
- snap_max_entry is disabled when the DRAW toolbar is disabled (previous fix didn't work)
- added drill count column in Excellon Tool Table which displays the total number of drills for each tool
- added a new menu entry in Menu -> EDIT named "Join Excellon". It will merge a selection of Excellon files into a new Excellon file
- added menu stubs for other Excellon based actions
- solved bug that was not possible to generate film from joined geometry
- improved toggle active/inactive of the object through SPACE key. Now the command works not only for one object but also for a selection

26.05.2018

- made conversion to Python3
- added Rtree Indexing drill path optimization
- added a checkbox in Options Tab -> App Defaults -> Excellon Group named Excellon Optim. Type from which it can be selected the default optimization type: TS stands for Travelling Salesman algorithm and Rtree stands for Rtree Indexing
- added a checkbox on the Grid Toolbar that when checked (default status is checked) whatever value entered in the GridX entry will be used instead of the now disabled GridY entry
- modified the default behavior on when a line_entry is clicked. Now, on each click on a line_entry, the content is automatically selected.
- snap_max_entry is disabled when the DRAW toolbar is disabled

24.05.2015

- in Geometry Editor added a initial form of Rotate Geometry command in toolbar
- changed the way the geometry is finished if it requires a key: before it was using key 'Space' now it uses 'Enter'
- added Shortcut for Rotate Geometry to key 'Space'
- after using a tool in Geometry Editor it automatically defaults to 'Select Tool'

23.05.2018

Added key shortcut's in FlatCAMApp and in Geometry Editor.

FlatCAMApp shortcut list:
1      Zoom Fit
2      Zoom Out
3      Zoom In
C      Copy Obj_Name
E      Edit Geometry (if selected)
G      Grid On/Off
M      Move Obj

N      New Geometry
R      Rotate
S      Shell Toggle
V      View Fit
X      Flip on X_axis
Y      Flip on Y_axis
~      Show Shortcut List

Space:   En(Dis)able Obj Plot
Ctrl+A   Select All
Ctrl+C   Copy Obj
Ctrl+E   Open Excellon File
Ctrl+G   Open Gerber File
Ctrl+M   Measurement Tool
Ctrl+O   Open Project
Ctrl+S   Save Project As
Delete   Delete Obj'''


Geometry Editor Key shortcut list:
A       Add an 'Arc'
C       Copy Geo Item
G       Grid Snap On/Off
K       Corner Snap On/Off
M       Move Geo Item

N       Add an 'Polygon'
O       Add a 'Circle'
P       Add a 'Path'
R       Add an 'Rectangle'
S       Select Tool Active


~        Show Shortcut List
Space:   Rotate Geometry
Enter:   Finish Current Action
Escape:  Abort Current Action
Delete:  Delete Obj

22.05.2018

- Added Marlin preprocessor
- Added a new entry into the Geometry and Excellon Object's UI: Feedrate rapid: the purpose is to set a feedrate for the G0 command that some firmwares like Marlin don't intepret as 'move with highest speed'
- FlatCAM was not making the conversion from one type of units to another for a lot of parameters. Corrected that.
- Modified the Marlin preprocessor so it will generate the required GCODE.

21.05.2018

- added new icons for menu entries
- added shortcuts that work on the Project tab but also over Plot. Shorcut list is accesed with shortcut key '~' sau '`'
- small GUI modification: on each "New File" command it will switch to the Project Tab regardless on which tab we were.
- removed the global shear entries and checkbox as they can be damaging and it will build effect upon effect, which is not good
- solved bug in that the Edit -> Shear on X (Y)axis could adjust only in integers. Now the angle can be adjusted in float with 3 decimals.
- changed the tile of QInputDialog to a more general one
- changed the "follow" Tcl command to the new format
- added a new entry in the Menu -> File, to open a Gerber with the follow parameter = True
- added a new checkbox in the Gerber Object Selection Tab that when checked it will create a "follow" geometry
- added a few lines in Mill Holes Tcl command to check if there are promises and raise an Tcl error if there are any.
- started to modify the Export_Svg Tcl command

20.05.2018

- changed the interpretation of the axis for the rotate and skew commands. Actually I reversed them to reflect reality.
- for the rotate command a positive angle now rotates CW. It was reversed.
- added shortcuts (for outside CANVAS; the CANVAS has it's own set of shortcuts) Ctrl+C will copy to clipboard the name of the selected object Ctrl+A will Select All objects
"X" key will flip the selected objects on X axis
"Y" key will flip the selected objects on Y axis
"R" key will rotate CW with a 45 degrees step

- changed the layout for the top of th Options page. Added a checkbox and entries for parameters for skew command. When the checkbox is checked it will save (and load at the next startup of the program) the option that at each CNCJob generation (be it from Excellon or Geometry) it will perform the Skew command with the parametrs set in the nearby field boxes (Skew X and Skey Y angles). It is useful in case the CNC router is not perfectly alligned between the X and Y axis
- added some protection in case the skew command receive a None parameter
- BUG solved: made an UGLY (really UGLY) HACK so now, when there is a panel geometry generated from GUI, the project WILL save. I had to create a copy of the generated panel geometry and delete the original panel geometry. This way there is no complain from JSON module about circular reference.
- removed the Save buttons previously added on each Group in Application Defaults. Replaced them with a single Save button that stays always on top of the Options TAB
- added settings for defaults for the Grid that are persistent
- changed the default view at FlatCAM startup: now the origin is in the center of the screen

19.05.2018

- last object that is opened (created) is always automatically selected and the name of the object is automatically copied to clipboard; useful when using the TCL command :)
- added new commands in MENU -> EDIT named: "Copy Object" and "Copy Obj as Geom". The first command will duplicate any object (Geometry, Gerber, Excellon). The second command will duplicate the object as a geometry. For example, holes in Excello now are just circles that can be "painted" if one wants it.
- added new Tool named ToolFreeformCutout. It does what it says, it will make a board cutout from a "any shape" Gerber or Geometry file
- solved bug in the TCL command "drillcncjob" that always used the endz parameter value as the toolchangez parameter value and for the endz value used a default value = 1
- added preprocessor name into the TCL command "drillcncjob" parameters
- when adding a new geometry the default name is now: "New_Geometry" instead of "New Geometry". TCL commands don't handle the spaces inside the name and require adding quotes.
- solved bug in "cncjob" TCL command in which it used multidepth parameter as always True regardless of the argument provided
- added a checkbox for Multidepth in the Options Tab -> Application Defaults

18.05.2018

- added an "Defaults" button in Excellon Defaults Group; it loads the following configuration (Excellon_format_in 2:4, Excellon_format_mm 3:3, Excellon_zeros LZ)
- added Save buttons for each Defaults Group; in the future more parameters will be propagated in the app, for now they are a few
- added functions for Skew on X axis and for Skew on Y menu stubs. Now, clicking on those Menu -> Options -> Transform Object menu entries will trigger those functions
- added a CheckBox button in the Options Tab -> Application Defaults that control the behaviour of the TCL shell: checking it will make the TCL shell window visible at each start-up, unchecking it the TCL shell window will be hidden until needed
- Depth/pass parameter from Geometry Object CNC Job is now in the defaults and it will keep it's value until changed in the Application Defaults.

17.05.2018

- added messages box for the Flip commands to show error in case there is no object selected when the command is executed
- added field entries in the Options TAB - > Application Defaults for the following newly introduced parameters: 
excellon_format_upper_in
excellon_format_lower_in
excellon_format_upper_mm
excellon_format_lower_mm

The ones with upper indicate how many digits are allocated for the units and the ones with lower indicate how many digits from coordinates are alocated for the decimals.

[  Eg: Excellon format 2:4 in INCH
   excellon_format_upper_in = 2
   excellon_format_lower_in = 4
where the first 2 digits are for units and the last 4 digits are
decimals so from a number like 235589 we will get a coordinate 23.5589
]

- added Radio button in the Options TAB - > Application Defaults for the Excellon_zeros parameter
After each change of those parameters the user will have to press "Save defaults" from File menu in order to propagate the new values, or wait for the autosave to kick in (each 20sec).
Those parameters can be set in the set_sys TCL command.

15.05.2018
- modified SetSys TCL command: now it can change units
- modified SetSys TCL command: now it can set new parameters: excellon_format_mm and excellon_format_in. the first one is when the excellon units are MM and the second is for when the excellon units are in INCH. Those parameters can be set with a number between 1 and 5 and it signify how many digits are before coma.
- added new GUI command in EDIT -> Select All. It will select all objects on the first mouse click and on the second will deselect all (toggle action)
- added new GUI commands in Options -> Transform object. Added Rotate selection, Flip on X axis of the selection and Flip on Y axis of the selection For the Rotate selection command, negative numbers means rotation CCW and positive numbers means rotation CW.
- cleaned up a bit the module imports
- worked on the excellon parsing for the case of trailing zeros. If there are more than 6digits in the coordinates, in case that there is no period, now the software will identify the issue and attempt to correct it by dividing the coordinate  further by 10 for each additional digit over 6. If the number of digits is less than 6 then the software will multiply by 10 the coordinates

14.05.2018

- fixed bug in Geometry CNCJob generation that prevented generating the object
- added GRBL 1.1 preprocessor and Laser preprocessor (adapted from the work of MARCO A QUEZADA)

13.05.2018

- added postprocessing in correct form
- added the possibility to select an preprocessor for Excellon Object
- added a new preprocessor, manual_toolchange.py. It allows to change the tools and adjust the drill tip to touch the surface manually, always in the X=0, Y=0, Z = toolchangeZ coordinates.
- fixed drillcncjob TCL command by adding toolchangeZ parameter
- fixed the preprocessor file template 'default.py' in the toolchange command section
- after I created a feature that the message in infobar is cleared by moving mouse on canvas, it generated a bug in TCL shell: everytime  mouse was moved it will add a space into the TCL read only section. Now this bug is fixed.
- added an EndZ parameter for the drillcncjob and cncjob TCL commands: it will specify at what Z value to park the CNC when job ends
- the spindle will be turned on after the toolchange and it will be turned off just before the final end move.

Previously:
- added GRID based working of FLATCAM
- added Set Origin command
- added FilmTool, PanelizeTool GUI, MoveTool
- and others

24.04.2018

- Remade the Measurement Tool: it now ask for the Start point of the measurement and then for the Stop point. After it will display the measurement until we left click again on the canvas and so on. Previously you clicked the start point and reset the X and Y coords displayed and then you moved the mouse pointer wherever you wanted to measure, but moving the mouse from there you lost the measurement.
- Added Relative measurement on the main plot
- Now both the measuring tool and the relative measurement will work only with the left click of the mouse button because middle mouse click and right mouse click are used for panning
- Renamed the tools files starting with Tool so they are grouped (in the future they may have their own folder like for TCL Commands)

- Commented some shortcut keys and functions for features that are not present anymore or they are planned to be in the future but unfinished (like buffer tool, paint tool)
- minor corrections regarding PEP8 (Pycharm complains about the m)
- solved bug in TclCommandsSetSys.py Everytime that the command was executed it complain about the parameter not being in the list (something like this). There was a missing “else:”
- when using the command “set_sys excellon_zeros” with parameter in lower case (either ‘l’ or ‘t’) now it is always written in the defaults file as capital letter

- solved a bug introduced by me: when apertures macros were detected in Excellon file, FlatCam will complain about missing dictionary key “size”. Now it first check if the aperture is a macro and perform the check for zero value only for apertures with “size” key
- solved a bug that didn't allowed FC to detect if Excellon file has leading zeros or trailing zeros
- solved a bug that FC was searching for char ‘%’ that signal end of Excellon header even in commented lines (latest versions of Eagle end the commented line with a ‘%’)


============================================
This fork features:

- Added buttons in the menu bar for opening of Gerber and Excellon files;
- Reduced number of decimals for drill bits to two decimals;
- Updated make_win32.py so it will work with cx_freeze 5.0.1 
- Added capability so FlatCAM can now read Gerber files with traces having zero value (aperture size is zero);
- Added Paint All / Seed based Paint functions from the JP's FlatCAM;
- Added Excellon move optimization (travelling salesman algorithm) cherry-picked from David Kahler: https://bitbucket.org/dakahler/flatcam
- Updated make_win32.py so it will work with cx_freeze 5.0.1
- Corrected small typo in DblSidedTool.py
- Added the TCL commands in the new format. Picked from FLATCAM master.
- Hack to fix the issue with geometry not being updated after a TCL command was executed. Now after each TCL command the plot_all() function is executed and the canvas is refreshed.
- Added GUI for panelization TCL command
- Added GUI tool for the panelization TCL command: Changed some ToolTips.
============================================

Previously added features by Dennis

- "Clear non-copper" feature, supporting multi-tool work.
- Groups in Project view.
- Pan view by dragging in visualizer window with pressed MMB.
- OpenGL-based visualizer.

