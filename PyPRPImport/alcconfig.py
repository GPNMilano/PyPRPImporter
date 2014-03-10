#!BPY
#
# $Id: alcconfig.py 865 2007-11-30 21:40:10Z trylon $
#
#    Copyright (C) 2005-2006  Alcugs pyprp Project Team
#    See the file AUTHORS for more info about the team
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#    Please see the file COPYING for the full license.
#    Please see the file DISCLAIMER for more details, before doing nothing.
#

#Set your settings here.
#These can now be set in PRPExplorer.

path = []
# Set path to additional modules (If you mix modules from different versions, the result will be a nice kaboum!!!)
#Uncomment if Blender cannot find the Python Imaging library. (Pointing to the correct place where is installed)
#path = ["C:\\Python23\\lib\\site-packages\\PIL",]
#path = ["/usr/lib/python2.3/site-packages/PIL",]

#Set the game version, allowed values are: "uu","tpots","m5"
# uu    -> version 5 63.11 (Prime,Live,UU,To D'ni)
# tpots -> version 5 63.12
# m5    -> version 6
game_version = "tpots"

#Set debug level
debug_level = 3

#refresh?
refresh = 1

#enable import?
I_agree_that_I_am_NOT_going_to_use_CYAN_material_on_other_games_or_projects_without_written_permission_from_CYAN = 1

# import texture type for tex
import_texture_type = ".png"

# import all textures from all prps loaded when importing
# this can be annoying when importing a small geometry file, as it slows down even when they are already extracted.
extractAllTextures = False

### You don't need to edit below this line ###
#--------------------------------------------#

ver0=5
ver2=11

if game_version.lower() in ["uu","live"]:
    ver0=5
    ver2=11
elif game_version.lower() in ["m5",]:
    ver0=6
else: #tpots
    ver0=5
    ver2=12

try:
    from alcmyconfig import *
except ImportError:
    pass

import sys
import os.path

def startup():
    global path
    for p in path:
        sys.path.append(p)

def alcGetDBGLevel():
    global debug_level
    return debug_level
