# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

# ######################################################################
# ## Borrowed code from 'https://github.com/gddc/ttfquery/blob/master/ #
# ## and made it work with Python 3                                    #
# ######################################################################

import re
import os
import sys
import glob

from shapely.geometry import Polygon
from shapely.affinity import translate, scale
from shapely.geometry import MultiPolygon

import freetype as ft
from fontTools import ttLib

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base2')


class ParseFont:

    FONT_SPECIFIER_NAME_ID = 4
    FONT_SPECIFIER_FAMILY_ID = 1

    @staticmethod
    def get_win32_font_path():
        """Get User-specific font directory on Win32"""
        try:
            import winreg
        except ImportError:
            return os.path.join(os.environ['WINDIR'], 'Fonts')
        else:
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            try:
                # should check that k is valid? How?
                return winreg.QueryValueEx(k, "Fonts")[0]
            finally:
                winreg.CloseKey(k)

    @staticmethod
    def get_linux_font_paths():
        """Get system font directories on Linux/Unix

        Uses /usr/sbin/chkfontpath to get the list
        of system-font directories, note that many
        of these will *not* be truetype font directories.

        If /usr/sbin/chkfontpath isn't available, uses
        returns a set of common Linux/Unix paths
        """
        executable = '/usr/sbin/chkfontpath'
        if os.path.isfile(executable):
            data = os.popen(executable).readlines()
            match = re.compile('\d+: (.+)')
            set_lst = []
            for line in data:
                result = match.match(line)
                if result:
                    set_lst.append(result.group(1))
            return set_lst
        else:
            directories = [
                # what seems to be the standard installation point
                "/usr/X11R6/lib/X11/fonts/TTF/",
                # common application, not really useful
                "/usr/lib/openoffice/share/fonts/truetype/",
                # documented as a good place to install new fonts...
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                # seems to be where fonts are installed for an individual user?
                "~/.fonts",
            ]

            dir_set = []

            for directory in directories:
                directory = os.path.expanduser(os.path.expandvars(directory))
                try:
                    if os.path.isdir(directory):
                        for path, children, files in os.walk(directory):
                            dir_set.append(path)
                except (IOError, OSError, TypeError, ValueError):
                    pass
            return dir_set

    @staticmethod
    def get_mac_font_paths():
        """Get system font directories on MacOS
        """
        directories = [
            # okay, now the OS X variants...
            "~/Library/Fonts/",
            "/Library/Fonts/",
            "/Network/Library/Fonts/",
            "/System/Library/Fonts/",
            "System Folder:Fonts:",
        ]

        dir_set = []

        for directory in directories:
            directory = os.path.expanduser(os.path.expandvars(directory))
            try:
                if os.path.isdir(directory):
                    for path, children, files in os.walk(directory):
                        dir_set.append(path)
            except (IOError, OSError, TypeError, ValueError):
                pass
        return dir_set

    @staticmethod
    def get_win32_fonts(font_directory=None):
        """Get list of explicitly *installed* font names"""

        import winreg
        if font_directory is None:
            font_directory = ParseFont.get_win32_font_path()
        k = None

        items = {}
        for keyName in (
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Fonts",
        ):
            try:
                k = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    keyName
                )
            except OSError:
                pass

        if not k:
            # couldn't open either WinNT or Win98 key???
            return glob.glob(os.path.join(font_directory, '*.ttf'))

        try:
            # should check that k is valid? How?
            for index in range(winreg.QueryInfoKey(k)[1]):
                key, value, _ = winreg.EnumValue(k, index)
                if not os.path.dirname(value):
                    value = os.path.join(font_directory, value)
                value = os.path.abspath(value).lower()
                if value[-4:] == '.ttf':
                    items[value] = 1
            return list(items.keys())
        finally:
            winreg.CloseKey(k)

    @staticmethod
    def get_font_name(font_path):
        """
        Get the short name from the font's names table
        From 'https://github.com/gddc/ttfquery/blob/master/ttfquery/describe.py'
        and
        http://www.starrhorne.com/2012/01/18/
        how-to-extract-font-names-from-ttf-files-using-python-and-our-old-friend-the-command-line.html
        ported to Python 3 here: https://gist.github.com/pklaus/dce37521579513c574d0
        """
        name = ""
        family = ""

        font = ttLib.TTFont(font_path)

        for record in font['name'].names:
            if b'\x00' in record.string:
                name_str = record.string.decode('utf-16-be')
            else:
                # name_str = record.string.decode('utf-8')
                name_str = record.string.decode('latin-1')

            if record.nameID == ParseFont.FONT_SPECIFIER_NAME_ID and not name:
                name = name_str
            elif record.nameID == ParseFont.FONT_SPECIFIER_FAMILY_ID and not family:
                family = name_str

            if name and family:
                break
        return name, family

    def __init__(self, app):
        super(ParseFont, self).__init__()

        self.app = app

        # regular fonts
        self.regular_f = {}
        # bold fonts
        self.bold_f = {}
        # italic fonts
        self.italic_f = {}
        # bold and italic fonts
        self.bold_italic_f = {}

    def get_fonts(self, paths=None):
        """
        Find fonts in paths, or the system paths if not given
        """
        files = {}
        if paths is None:
            if sys.platform == 'win32':
                font_directory = ParseFont.get_win32_font_path()
                paths = [font_directory, ]

                # now get all installed fonts directly...
                for f in self.get_win32_fonts(font_directory):
                    files[f] = 1
            elif sys.platform == 'linux':
                paths = ParseFont.get_linux_font_paths()
            else:
                paths = ParseFont.get_mac_font_paths()
        elif isinstance(paths, str):
            paths = [paths]

        for path in paths:
            for file in glob.glob(os.path.join(path, '*.ttf')):
                files[os.path.abspath(file)] = 1

        return list(files.keys())

    def get_fonts_by_types(self):

        system_fonts = self.get_fonts()

        # split the installed fonts by type: regular, bold, italic (oblique), bold-italic and
        # store them in separate dictionaries {name: file_path/filename.ttf}
        for font in system_fonts:
            try:
                name, family = ParseFont.get_font_name(font)
            except Exception as e:
                log.debug("ParseFont.get_fonts_by_types() --> Could not get the font name. %s" % str(e))
                continue

            if 'Bold' in name and 'Italic' in name:
                name = name.replace(" Bold Italic", '')
                self.bold_italic_f.update({name: font})
            elif 'Bold' in name and 'Oblique' in name:
                name = name.replace(" Bold Oblique", '')
                self.bold_italic_f.update({name: font})
            elif 'Bold' in name:
                name = name.replace(" Bold", '')
                self.bold_f.update({name: font})
            elif 'SemiBold' in name:
                name = name.replace(" SemiBold", '')
                self.bold_f.update({name: font})
            elif 'DemiBold' in name:
                name = name.replace(" DemiBold", '')
                self.bold_f.update({name: font})
            elif 'Demi' in name:
                name = name.replace(" Demi", '')
                self.bold_f.update({name: font})
            elif 'Italic' in name:
                name = name.replace(" Italic", '')
                self.italic_f.update({name: font})
            elif 'Oblique' in name:
                name = name.replace(" Italic", '')
                self.italic_f.update({name: font})
            else:
                try:
                    name = name.replace(" Regular", '')
                except Exception:
                    pass
                self.regular_f.update({name: font})
        log.debug("Font parsing is finished.")

    def font_to_geometry(self, char_string, font_name, font_type, font_size, units='MM', coordx=0, coordy=0):
        path = []
        scaled_path = []
        path_filename = ""

        regular_dict = self.regular_f
        bold_dict = self.bold_f
        italic_dict = self.italic_f
        bold_italic_dict = self.bold_italic_f

        try:
            if font_type == 'bi':
                path_filename = bold_italic_dict[font_name]
            elif font_type == 'bold':
                path_filename = bold_dict[font_name]
            elif font_type == 'italic':
                path_filename = italic_dict[font_name]
            elif font_type == 'regular':
                path_filename = regular_dict[font_name]
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Font not supported, try another one."))
            log.debug("[ERROR_NOTCL] Font Loading: %s" % str(e))
            return "flatcam font parse failed"

        face = ft.Face(path_filename)
        face.set_char_size(int(font_size) * 64)

        pen_x = coordx
        previous = 0

        # done as here: https://www.freetype.org/freetype2/docs/tutorial/step2.html
        for char in char_string:
            glyph_index = face.get_char_index(char)

            try:
                if previous > 0 and glyph_index > 0:
                    delta = face.get_kerning(previous, glyph_index)
                    pen_x += delta.x
            except Exception:
                pass

            face.load_glyph(glyph_index)
            # face.load_char(char, flags=8)

            slot = face.glyph
            outline = slot.outline

            start, end = 0, 0
            for i in range(len(outline.contours)):
                end = outline.contours[i]
                points = outline.points[start:end + 1]
                points.append(points[0])

                char_geo = Polygon(points)
                char_geo = translate(char_geo, xoff=pen_x, yoff=coordy)

                path.append(char_geo)

                start = end + 1

            pen_x += slot.advance.x
            previous = glyph_index

        for item in path:
            if units == 'MM':
                scaled_path.append(scale(item, 0.0080187969924812, 0.0080187969924812, origin=(coordx, coordy)))
            else:
                scaled_path.append(scale(item, 0.00031570066, 0.00031570066, origin=(coordx, coordy)))

        return MultiPolygon(scaled_path)
