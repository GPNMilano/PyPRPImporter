#
# $Id: alc_Classes.py 876 2007-12-15 22:15:11Z Paradox $
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

try:
    import Blender
    try:
        from Blender import Mesh
        from Blender import Lamp
    except Exception, detail:
        print detail
except ImportError:
    pass

import md5, random, binascii, cStringIO, copy, Image, math, struct, StringIO, os, os.path, pickle
from alc_AbsClasses import *
import alcconfig, alchexdump
from alc_RefParser import *


import alcconfig, alchexdump
def stripIllegalChars(name):
    name=name.replace("*","_")
    name=name.replace("?","_")
    name=name.replace("\\","_")
    name=name.replace("/","_")
    name=name.replace("<","_")
    name=name.replace(">","_")
    name=name.replace(":","_")
    name=name.replace("\"","_")
    name=name.replace("|","_")
    name=name.replace("#","_")
    name=name.strip()
    return name


########
## Material and layer classes are in alc_MatClasses.py
#########

class plSpawnModifier(plMultiModifier):
    def __init__(self,parent,name="unnamed",type=0x003D):
        plMultiModifier.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x003D,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x003D,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plMultiModifier.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream):
        plMultiModifier.read(self,stream)

    def write(self,stream):
        plMultiModifier.write(self,stream)

    def import_obj(self,obj):
        obj.addProperty("type","swpoint")
        obj.layers = [2,]
        try:
            obj.setDrawMode(9)
        except:
            obj.setDrawMode(10)
        obj.setDrawType(2)



class plViewFaceModifier(plSingleModifier):
    plVFFlags = \
    { \
        "kPivotFace"    :  0, \
        "kPivotFavorY"  :  1, \
        "kPivotY"       :  2, \
        "kPivotTumble"  :  3, \
        "kScale"        :  4, \
        "kFaceCam"      :  5, \
        "kFaceList"     :  6, \
        "kFacePlay"     :  7, \
        "kFaceObj"      :  8, \
        "kOffset"       :  9, \
        "kOffsetLocal"  : 10, \
        "kMaxBounds"    : 11  \
    }


    def __init__(self, parent, name="unnamed", type=0x0040):
        plSingleModifier.__init__(self, parent, name, type)
        self.fScale = Vertex()
        self.fOrigLocalToParent = hsMatrix44()
        self.fOrigParentToLocal = hsMatrix44()
        self.fOffset = Vertex()
        self.fMaxBounds = hsBounds3Ext()
        self.fFaceObj = UruObjectRef(self.getVersion())

    def _Find(page,name):
        return page.find(0x0040,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0040,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self, stream):
        plSingleModifier.read(self,stream)
        self.fScale.read(stream)
        self.fOrigLocalToParent.read(stream)
        self.fOrigParentToLocal.read(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kFaceObj"]]):
            self.fFaceObj.read(stream)
        self.fOffset.read(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kMaxBounds"]]):
            self.fMaxBounds.read(stream)

    def write(self, stream):
        plSingleModifier.write(self,stream)
        self.fScale.write(stream)
        self.fOrigLocalToParent.write(stream)
        self.fOrigParentToLocal.write(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kFaceObj"]]):
            self.fFaceObj.write(stream)
        self.fOffset.write(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kMaxBounds"]]):
            self.fMaxBounds.write(stream) # only write this if needed


    def import_obj(self,obj):
        if(self.bitVector.Count > 0):
            obj.addProperty("sprite_flags",str(alcHex2Ascii(self.bitVector.Data[0],4)))
        else:
            obj.addProperty("sprite_flags",str(alcHex2Ascii(0x00,4)))


#list2
class plAGModifier(plSingleModifier):
    def __init__(self,parent,name="unnamed",type=0x006C):
        plSingleModifier.__init__(self,parent,name,type)
        #format
        #U32 0
        #U32 0
        self.string = ""

    def _Find(page,name):
        return page.find(0x006C,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x006C,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plSingleModifier.read(self,stream)
        self.string = stream.ReadSafeString(self.getVersion())


    def write(self,stream):
        plSingleModifier.write(self,stream)
        stream.WriteSafeString(self.string,self.getVersion())



class plAGMasterMod(hsKeyedObject):
    def __init__(self,parent,name="unnamed",type=0x006D):
        hsKeyedObject.__init__(self,parent,name,type)
        #format
        #U32 0
        self.str=str32(type=1)
        self.anims=[] #armature anims


    def _Find(page,name):
        return page.find(0x006D,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x006D,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)
        for i in self.anims:
            i.changePageRaw(sid,did,stype,dtype)


    def read(self,stream):
        hsKeyedObject.read(self,stream)
        unk1, = struct.unpack("I",stream.read(4))
        ##myst5 unk1: 0x04
        if unk1 not in [0x00,0x04]:
            raise "unk1 %08X" %unk1
        #On tpots always "", on old versions there is something here
        self.str.read(stream)
        if self.getVersion()==6:
            count1, = struct.unpack("H",stream.read(2))
        else:
            count1, = struct.unpack("I",stream.read(4))
        self.anims=[]
        for i in range(count1):
            ref = UruObjectRef(self.getVersion())
            ref.read(stream)
            #print ref, self.Key
            assert(ref.verify(self.Key))
            if ref.Key.object_type not in [0xF1,0xF2]:
                raise "armature anim %08X" %ref.Key.object_type
            self.anims.append(ref)


    def write(self,stream):
        hsKeyedObject.write(self,stream)
        stream.write(struct.pack("I",0))
        self.str.write(stream)
        stream.write(struct.pack("I",len(self.anims)))
        for ref in self.anims:
            ref.update(self.Key)
            ref.write(stream)


class plExcludeRegionModifier(plSingleModifier):
    Flags = \
    { \
        "kBlockCameras" : 0 \
    }

    def __init__(self,parent,name="unnamed",type=0x00A4):
        plSingleModifier.__init__(self,parent,name,type)

        self.fSafePoints = []
        self.fSeek = True
        self.fSeekTime = 10

    def _Find(page,name):
        return page.find(0x00A4,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00A4,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plSingleModifier.read(self,stream)

        count = stream.Read32()
        for i in range(count):
            safepoint = UruObjectRef()
            safepoint.read(stream)
            self.fSafePoints.append(safepoint)

        self.fSeek = stream.ReadBool()
        self.fSeekTime = stream.ReadFloat()

    def write(self,stream):
        plSingleModifier.write(self,stream)

        stream.Write32(len(fSafePoints))
        for safepoint in self.fSafePoints:
            safepoint.write(stream)

        stream.WriteBool(self.fSeek)
        stream.WriteFloat(self.fSeekTime)

class plSoftVolume(plRegionBase):               #Type 0x0087 (Uru)
    Flags = \
    { \
        "kListenNone"       : 0x0, \
        "kListenCheck"      : 0x1, \
        "kListenPosSet"     : 0x2, \
        "kListenDirty"      : 0x4, \
        "kListenRegistered" : 0x8 \
    }

    def __init__(self,parent,name="unnamed",type=0x0087):
        plRegionBase.__init__(self,parent,name,type)
        #Format
        self.fListenState = 13
        self.fInsideStrength = 1.0
        self.fOutsideStrength = 0

    def _Find(page,name):
        return page.find(0x0087,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0087,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plRegionBase.read(self,stream)
        self.fListenState = stream.Read32()
        self.fInsideStrength = stream.ReadFloat()
        self.fOutsideStrength = stream.ReadFloat()


    def write(self,stream):
        plRegionBase.write(self,stream)
        stream.Write32(self.fListenState)
        stream.WriteFloat(self.fInsideStrength)
        stream.WriteFloat(self.fOutsideStrength)


class plSoftVolumeSimple(plSoftVolume):
    def __init__(self,parent,name="unnamed",type=0x0088):
        plSoftVolume.__init__(self,parent,name,type)
        #Format
        self.fSoftDist = 5
        self.fVolume = None #plVolumeIsect instance


    def _Find(page,name):
        return page.find(0x0088,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0088,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream,size):
        st=stream.tell()
        plSoftVolume.read(self,stream)
        self.fSoftDist = stream.ReadFloat()
        vitype = stream.Read16()
        if (vitype != 0x0000):
            self.fVolume = PrpVolumeIsect(vitype,self.getVersion())
            if self.fVolume.data == None:
                size=size-(stream.tell()-st)
                self.rawdata=cStringIO.StringIO()
                self.rawdata.write(stream.read(size))
                self.rawdata.seek(0)
            else:
                self.fVolume.read(stream)

    def write(self,stream):
        plSoftVolume.write(self,stream)
        stream.WriteFloat(self.fSoftDist)
        if self.fVolume == None:
            stream.Write16(0x8000)
        else:
            stream.Write16(self.fVolume.vitype)
            self.fVolume.write(stream)


    def getPropertyString(self):
        return str(self.Key.name)


    def import_all(self):
        name = str(self.Key.name)
        if self.fVolume.data != None:
            self.fVolume.data.createObject(name,self.getPageNum())



class plSoftVolumeComplex(plSoftVolume):
    def __init__(self,parent,name="unnamed",type=0x0089):
        plSoftVolume.__init__(self,parent,name,type)
        #Format
        self.vSV7C = hsTArray([0x88,0x8A,0x8B,0x8C],self.getVersion(),True)

    def _Find(page,name):
        return page.find(0x0089,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0089,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plSoftVolume.read(self,stream)
        self.vSV7C.read(stream)

    def write(self,stream):
        plSoftVolume.write(self,stream)
        self.vSV7C.write(stream)

    def getPropertyString(self):
        count = self.vSV7C.size
        if count > 0:
            propertyString = self.getPropertySymbol()
            propertyString += "("
            for i in range(count):
                if i > 0:
                    propertyString += ","
                svRef = self.vSV7C[i]
                softVolume = self.getRoot().findref(svRef)
                if softVolume != None:
                    propertyString += softVolume.data.getPropertyString()
                else:
                    raise RuntimeError, "Could not find soft volume object %s" % str(svRef.Key.name)
            propertyString += ")"
            return propertyString
        return None



class plSoftVolumeUnion(plSoftVolumeComplex):
    def __init__(self,parent,name="unnamed",type=0x008A):
        plSoftVolumeComplex.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x008A,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x008A,name,1)
    FindCreate = staticmethod(_FindCreate)

    def getPropertySymbol(self):
        return "U"


class plSoftVolumeIntersect(plSoftVolumeComplex):
    def __init__(self,parent,name="unnamed",type=0x008B):
        plSoftVolumeComplex.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x008B,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x008B,name,1)
    FindCreate = staticmethod(_FindCreate)

    def getPropertySymbol(self):
        return "I"


class plSoftVolumeInvert(plSoftVolumeComplex):
    def __init__(self,parent,name="unnamed",type=0x008C):
        plSoftVolumeComplex.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x008C,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x008C,name,1)
    FindCreate = staticmethod(_FindCreate)

    def getPropertySymbol(self):
        return "!"


class plMsgForwarder(hsKeyedObject):
    def __init__(self,parent,name="unnamed",type=0x00A8):
        hsKeyedObject.__init__(self,parent,name,type)
        #format
        self.mods=[] #modifiers

    def _Find(page,name):
        return page.find(0x00A8,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00A8,name,1)
    FindCreate = staticmethod(_FindCreate)


    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)
        for i in self.mods:
            i.changePageRaw(sid,did,stype,dtype)


    def read(self,stream):
        hsKeyedObject.read(self,stream)
        count1, = struct.unpack("I",stream.read(4))
        self.mods=[]
        for i in range(count1):
            ref = UruObjectRef(self.getVersion())
            ref.read(stream)
            ##assert(ref.verify(self.Key))
            if ref.Key.object_type not in [0x6D,]:
                raise "modifier %08X" %ref.Key.object_type
            self.mods.append(ref)


    def write(self,stream):
        hsKeyedObject.write(self,stream)
        stream.write(struct.pack("I",len(self.mods)))
        for ref in self.mods:
            ##ref.update(self.Key)
            ref.write(stream)


class plArmatureEffectsMgr(hsKeyedObject):
    Sounds = \
    { \
        "kFootDirt"             :  0, \
        "kFootPuddle"           :  1, \
        "kFootWater"            :  2, \
        "kFootTile"             :  3, \
        "kFootMetal"            :  4, \
        "kFootWoodBridge"       :  5, \
        "kFootRopeLadder"       :  6, \
        "kFootGrass"            :  7, \
        "kFootBrush"            :  8, \
        "kFootHardWood"         :  9, \
        "kFootRug"              : 10, \
        "kFootStone"            : 11, \
        "kFootMud"              : 12, \
        "kFootMetalLadder"      : 13, \
        "kFootWoodLadder"       : 14, \
        "kFootDeepWater"        : 15, \
        "kFootMaintainerGlass"  : 16, \
        "kFootMaintainerStone"  : 17, \
        "kFootSwimming"         : 18, \
        "kMaxSurface"           : 19, \
        "kFootNoSurface"        : 19  \
    }

    SurfaceStrings = \
    [ \
        "Dirt", \
        "Puddle", \
        "Water", \
        "Tile", \
        "Metal", \
        "WoodBridge", \
        "RopeLadder", \
        "Grass", \
        "Brush", \
        "HardWood", \
        "Rug", \
        "Stone", \
        "Mud", \
        "MetalLadder", \
        "WoodLadder", \
        "DeepWater", \
        "Maintainer(Glass)", \
        "Maintainer(Stone)", \
        "Swimming", \
        "(none)"  \
    ]

    def __init__(self,parent,name="unnamed",type=0x00CD):
        hsKeyedObject.__init__(self,parent,name,type)

        self.fEffects = []

    def _Find(page,name):
        return page.find(0x00CD,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00CD,name,1)
    FindCreate = staticmethod(_FindCreate)


    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream):
        hsKeyedObject.read(self,stream)

        count = stream.Read32()
        for i in range(count):
            ref = UruObjectRef(self.getVersion())
            ref.read(stream)
            self.fEffects.append(ref)

    def write(self,stream):
        hsKeyedObject.write(self,stream)

        stream.Write32(len(self.fEffects))
        for ref in self.fEffects:
            ref.write(stream)



class plHardRegionPlanes(plRegionBase):
    def __init__(self,parent,name="unnamed",type=0x0111):
        plRegionBase.__init__(self,parent,name,type)
        self.vM70 = [] #hsMatrix34

    def _Find(page,name):
        return page.find(0x0111,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0111,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plRegionBase.read(self,stream)
        count = stream.Read32()
        for i in range(count):
            self.vM70[i] = hsMatrix34()
            self.vM70.read(stream)

    def write(self,stream):
        plRegionBase.write(self,stream)
        count = len(self.vM70)
        stream.Write32(count)
        for i in range(count):
            self.vM70.write(stream)


class plHardRegionComplex(plRegionBase):
    def __init__(self,parent,name="unnamed",type=0x0112):
        plRegionBase.__init__(self,parent,name,type)
        self.vHR70 = hsTArray([],self.getVersion())

    def _Find(page,name):
        return page.find(0x0112,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0112,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plRegionBase.read(self,stream)
        self.vHR70.read(self,stream)

    def write(self,stream):
        plRegionBase.write(self,stream)
        self.vHR70.write(stream)

    def changePageRaw(self,sid,did,stype,dtype):
        plRegionBase.changePageRaw(self,sid,did,stype,dtype)
        self.vHR70.changePageRaw(sid,did,stype,dtype)

class plVisRegion(plObjInterface):
    Flags = \
    { \
        "kRefRegion" : 0, \
        "kRefVisMgr" : 1  \
    }

    VecFlags = \
    { \
        "kDisable"       : 0, \
        "kIsNot"         : 1, \
        "kReplaceNormal" : 2, \
        "kDisableNormal" : 3  \
    }

    def __init__(self,parent,name="unnamed",type=0x0116):
        plObjInterface.__init__(self,parent,name,type)
        self.fRegion = UruObjectRef(self.getVersion())
        self.fMgr = UruObjectRef(self.getVersion())

    def _Find(page,name):
        return page.find(0x0116,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0116,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plObjInterface.changePageRaw(self,sid,did,stype,dtype)
        self.fRegion.changePageRaw(sid,did,stype,dtype)
        self.fMgr.changePageRaw(sid,dad,stype,dtype)

    def read(self,stream):
        plObjInterface.read(self,stream)
        self.fRegion.read(stream)
        self.fMgr.read(stream)

    def write(self,stream):
        plObjInterface.write(self,stream)
        self.fRegion.write(stream)
        self.fMgr.write(stream)

class plRelevanceRegion(plObjInterface):
    def __init__(self,parent,name="unnamed",type=0x011E):
        plObjInterface.__init__(self,parent,name,type)
        self.fRegion = UruObjectRef(self.getVersion())

    def _Find(page,name):
        return page.find(0x011E,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x011E,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plObjInterface.changePageRaw(self,sid,did,stype,dtype)
        self.fRegion.changePageRaw(sid,did,stype,dtype)

    def read(self,stream):
        plObjInterface.read(self,stream)
        self.fRegion.read(stream)

    def write(self,stream):
        plObjInterface.write(self,stream)
        self.fRegion.write(stream)

from alcurutypes import *
from alcdxtconv import *
from alchexdump import *
from alc_GeomClasses import *
from alc_Functions import *
from alcConvexHull import *
from alc_VolumeIsect import *
from alc_AlcScript import *
