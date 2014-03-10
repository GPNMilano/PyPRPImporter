#
# $Id: alc_LogicClasses.py 843 2007-09-13 01:19:29Z Trylon $
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
from alcurutypes import *
from alcdxtconv import *
from alchexdump import *
from alc_GeomClasses import *
from alc_Functions import *
from alcConvexHull import *
from alc_AbsClasses import *
from alc_VolumeIsect import *
from alc_AlcScript import *
from alc_SwimClasses import *
from alc_Messages import *
from alc_Classes import *
from alc_RefParser import *
from alc_ObjClasses import *
from alc_QuickScripts import *
import alc_QuickScripts


class plInterfaceInfoModifier(plSingleModifier):
    def __init__(self,parent,name="unnamed",type=0x00CB):
        plSingleModifier.__init__(self,parent,name,type)
        #format
        self.fKeyList=hsTArray([0x2D],self.getVersion()) # modifiers Type 2D (LogicModifier)
        ####

        self.LogicModIdx = 0

    def _Find(page,name):
        return page.find(0x00CB,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00CB,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plSingleModifier.changePageRaw(self,sid,did,stype,dtype)
        self.fKeyList.changePageRaw(sid,did,stype,dtype)


    def read(self,stream):
        plSingleModifier.read(self,stream)
        self.fKeyList.read(stream)


    def write(self,stream):
        plSingleModifier.write(self,stream)
        self.fKeyList.update(self.Key)
        self.fKeyList.write(stream)



class plLogicModBase(plSingleModifier):                   #Type 0x4F
    Flags = \
    { \
        "kLocalElement"      : 0, \
        "kReset"             : 1, \
        "kTriggered"         : 2, \
        "kOneShot"           : 3, \
        "kRequestingTrigger" : 4, \
        "kTypeActivator"     : 5, \
        "kMultiTrigger"      : 6  \
    }
    def __init__(self,parent,name="unnamed",type=None):
        plSingleModifier.__init__(self,parent,name,type)
        self.MsgCount = 0x00000000
        self.fCommandList = [] # plMessages
        self.fNotify = PrpMessage(0x02E8,self.getVersion())
        self.fFlags = hsBitVector()
        self.fDisabled = False

    def read(self,buf):
        plSingleModifier.read(self,buf)
        count = buf.Read32()
        for i in range(count):
            cmd = PrpMessage.FromStream(buf)
            self.fCommandList.append(cmd)

        self.fNotify = PrpMessage.FromStream(buf)
        self.fFlags.read(buf)
        self.fDisabled = buf.ReadBool()

    def write(self,buf):
        plSingleModifier.write(self,buf)
        buf.Write32(len(self.fCommandList))

        for cmd in self.fCommandList:
            PrpMessage.ToStream(buf,cmd)

        PrpMessage.ToStream(buf,self.fNotify)
        self.fFlags.write(buf)
        buf.WriteBool(self.fDisabled)

class plLogicModifier(plLogicModBase):

    ScriptFlags = \
    { \
        "localelement"      : 0, \
        "reset"             : 1, \
        "triggered"         : 2, \
        "oneshot"           : 3, \
        "requestingtrigger" : 4, \
        "typeactivator"     : 5, \
        "multitrigger"      : 6  \
    }

    Cursors = \
    { \
        "kNoChange"         :  0, \
        "kCursorUp"         :  1, \
        "kCursorLeft"       :  2, \
        "kCursorRight"      :  3, \
        "kCursorDown"       :  4, \
        "kCursorPoised"     :  5, \
        "kCursorClicked"    :  6, \
        "kCursorUnClicked"  :  7, \
        "kCursorHidden"     :  8, \
        "kCursorOpen"       :  9, \
        "kCursorGrab"       : 10, \
        "kCursorArrow"      : 11, \
        "kNullCursor"       : 12  \
    }

    ScriptCursors = \
    { \
        "nochange"   :  0, \
        "up"         :  1, \
        "left"       :  2, \
        "right"      :  3, \
        "down"       :  4, \
        "poised"     :  5, \
        "clicked"    :  6, \
        "unclicked"  :  7, \
        "hidden"     :  8, \
        "open"       :  9, \
        "grab"       : 10, \
        "arrow"      : 11, \
    }


    def __init__(self,parent,name="unnamed",type=0x002D):
        plLogicModBase.__init__(self,parent,name,type)
        #format
        self.fConditionList = hsTArray([0x32,0x37,0x3E,0xA6],self.getVersion(),True)
        self.fMyCursor = 1 #U32 - 1 or 5 defaults to 1

    def _Find(page,name):
        return page.find(0x002D,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x002D,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plLogicModBase.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream):
        plLogicModBase.read(self,stream)
        self.fConditionList.read(stream)
        self.fMyCursor = stream.Read32()

    def write(self,stream):
        plLogicModBase.write(self,stream)
        self.fConditionList.write(stream)
        stream.Write32(self.fMyCursor)



#################
##             ##
##  Detectors  ##
##             ##
#################
class plDetectorModifier(plSingleModifier):                 #Type 0x24
    def __init__(self,parent,name="unnamed",type=None):
        plSingleModifier.__init__(self,parent,name,type)
        #Format
        if (self.getVersion()==6):
            self.fReceivers = hsTArray([],6)
        else:
            self.fReceivers = hsTArray([0x002D],5)
        self.fRemoteMod = UruObjectRef(self.getVersion())
        self.fProxyKey = UruObjectRef(self.getVersion())

    def read(self,buf):
        plSingleModifier.read(self,buf)
        self.fReceivers.ReadVector(buf)
        self.fRemoteMod.read(buf)
        self.fProxyKey.read(buf)

    def write(self,buf):
        plSingleModifier.write(self,buf)
        self.fReceivers.update(self.Key)
        self.fReceivers.WriteVector(buf)
        self.fRemoteMod.write(buf)
        self.fProxyKey.write(buf)


    def changePageRaw(self,sid,did,stype,dtype):
        plSingleModifier.changePageRaw(self,sid,did,stype,dtype)
        self.logic.changePageRaw(sid,did,stype,dtype)
        self.fRemoteMod.changePageRaw(sid,did,stype,dtype)
        self.fProxyKey.changePageRaw(sid,did,stype,dtype)



class plPickingDetector(plDetectorModifier):                    #Type 0x002B
    def __init__(self,parent,name="unnamed",type=0x002B):
        #Gotta figure out how to pass the correct type from M5
        #self.getVersion() & plDectorModifier.getVersion() puke :\
        plDetectorModifier.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x002B,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x002B,name,1)
    FindCreate = staticmethod(_FindCreate)



class plCollisionDetector(plDetectorModifier):              #Type 0x2C
    Type = \
    { \
        "kTypeEnter"    :  0x1, \
        "kTypeExit"     :  0x2, \
        "kTypeAny"      :  0x4, \
        "kTypeUnEnter"  :  0x8, \
        "kTypeUnExit"   : 0x10, \
        "kTypeBump"     : 0x20  \
    }

    ScriptType = \
    { \
        "enter"    :  0x1, \
        "exit"     :  0x2, \
        "any"      :  0x4, \
        "unenter"  :  0x8, \
        "unexit"   : 0x10, \
        "bump"     : 0x20  \
    }

    def __init__(self,parent,name="unnamed",type=None):
        plDetectorModifier.__init__(self,parent,name,type)
        self.fType = 0

    def read(self,buf):
        plDetectorModifier.read(self,buf)
        self.fType = buf.ReadByte()

    def write(self,buf):
        plDetectorModifier.write(self,buf)
        buf.WriteByte(self.fType)


class plObjectInVolumeDetector(plCollisionDetector):
    def __init__(self,parent,name="unnamed",type=0x007B):
        plCollisionDetector.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x007B,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x007B,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plCollisionDetector.read(self,stream)

    def write(self,stream):
        plCollisionDetector.write(self,stream)

    def import_obj(self,obj):
        pass



class plObjectInVolumeAndFacingDetector(plObjectInVolumeDetector): # type 0x00E7
    def __init__(self,parent,name="unnamed",type=0x00E7):
        plObjectInVolumeDetector.__init__(self,parent,name,type)
        self.fFacingTolerance = 0.1 # probably in radians, so give a bit of an edge
        self.fNeedWalkingForward = False # let's default to no walking forward needed

    def _Find(page,name):
        return page.find(0x00E7,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00E7,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plObjectInVolumeDetector.read(self,stream)
        self.fFacingTolerance = stream.ReadFloat()
        self.fNeedWalkingForward = stream.ReadBool()


    def write(self,stream):
        plObjectInVolumeDetector.write(self,stream)
        stream.WriteFloat(self.fFacingTolerance)
        stream.WriteBool(self.fNeedWalkingForward)



class plPanicLinkRegion(plCollisionDetector):
    def __init__(self,parent,name="unnamed",type=0x00FC):
        plCollisionDetector.__init__(self,parent,name,type)
        self.fPlayLinkOutAnim = True

    def _Find(page,name):
        return page.find(0x00FC,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00FC,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plCollisionDetector.changePageRaw(self,sid,did,stype,dtype)


    def read(self,stream):
        plCollisionDetector.read(self,stream)
        self.fPlayLinkOutAnim = stream.ReadBool()

    def write(self,stream):
        plCollisionDetector.write(self,stream)
        stream.WriteBool(self.fPlayLinkOutAnim)

    def import_obj(self,obj):
        # The only thing this thing does is set the regiontype property
        try:
            obj.removeProperty("regiontype")
        except:
            pass

        obj.addProperty("regiontype","paniclink")
        pass




class plCameraRegionDetector(plDetectorModifier):
    def __init__(self,parent,name="unnamed",type=0x006F):
        plDetectorModifier.__init__(self,parent,name,type)

        self.fMessages = []

    def _Find(page,name):
        return page.find(0x006F,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x006F,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plDetectorModifier.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream):
        plDetectorModifier.read(self,stream)

        count = stream.Read32()
        self.fMessages = []
        for i in range(count):
            msg = PrpMessage.FromStream(stream,self.getVersion())
            self.fMessages.append(msg)

    def write(self,stream):
        plDetectorModifier.write(self,stream)

        stream.Write32(len(self.fMessages))
        for msg in self.fMessages:
            PrpMessage.ToStream(stream,msg)



    def import_obj(self,obj):
        try:
            obj.removeProperty("regiontype")
        except:
            pass
        obj.addProperty("regiontype","camera")

        objscript = AlcScript.objects.FindOrCreate(obj.name)

        msgscripts = []
        for msg in self.fMessages:
            msgscript = {}
            StoreInDict(msgscript,"camera",str(msg.data.fNewCam.Key.name))

            if self.fMessages[0].data.fCmd[plCameraMsg.ModCmds["kSetAsPrimary"]] == 1:
                StoreInDict(msgscript,"setprimary",True)
            else:
                StoreInDict(msgscript,"setprimary",False)

            msgscripts.append(msgscript)

        StoreInDict(objscript,"region.camera.cameras",msgscripts)



###########################
##                       ##
##  Conditional Objects  ##
##                       ##
###########################

class plConditionalObject(hsKeyedObject):                   #Type 0x2E

    Flags = \
    { \
        "kLocalElement" : 0, \
        "kNOT"          : 1  \
    }

    def __init__(self,parent,name="unnamed",type=0x002E):
        hsKeyedObject.__init__(self,parent,name,type)
        self.bSatisfied = False
        self.fToggle = False

    def _Find(page,name):
        return page.find(0x002E,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x002E,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,buf):
        hsKeyedObject.read(self,buf)
        self.bSatisfied = buf.ReadBool()
        self.fToggle = buf.ReadBool()

    def write(self,buf):
        hsKeyedObject.write(self,buf)
        buf.WriteBool(self.bSatisfied)
        buf.WriteBool(self.fToggle)


class plObjectInBoxConditionalObject(plConditionalObject):
    def __init__(self,parent,name="unnamed",type=0x0037):
        plConditionalObject.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x0037,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0037,name,1)
    FindCreate = staticmethod(_FindCreate)


class plVolumeSensorConditionalObject(plConditionalObject):
    Type = \
    { \
        "kTypeEnter" : 0x1,\
        "kTypeExit"  : 0x2 \
    }

    def __init__(self,parent,name="unnamed",type=0x00A6):
        plConditionalObject.__init__(self,parent,name,type)
        #format
        self.fTrigNum=-1 #
        self.fType=1 #
        self.fFirst = False

    def _Find(page,name):
        return page.find(0x00A6,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00A6,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plConditionalObject.changePageRaw(self,sid,did,stype,dtype)


    def read(self,stream):
        plConditionalObject.read(self,stream)

        self.fTrigNum = stream.ReadSigned32()
        self.fType = stream.Read32() # Was "direction"
        self.fFirst = stream.ReadBool()


    def write(self,stream):
        plConditionalObject.write(self,stream)
        stream.WriteSigned32(self.fTrigNum)
        stream.Write32(self.fType)
        stream.WriteBool(self.fFirst)

    def import_obj(self,obj):
        pass


    def _FindCreate(page,name):
        plobj = page.find(0x00A6,name,1)
        return plobj
    FindCreate = staticmethod(_FindCreate)


class plActivatorConditionalObject(plConditionalObject):
    def __init__(self,parent,name="unnamed",type=0x0032):
        plConditionalObject.__init__(self,parent,name,type)
        #format
        self.fActivators = hsTArray()

    def _Find(page,name):
        return page.find(0x0032,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0032,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plConditionalObject.changePageRaw(self,sid,did,stype,dtype)
        self.fActivators.changePageRaw(sid,did,stype,dtype)

    def read(self,stream):
        plConditionalObject.read(self,stream)
        self.fActivators.ReadVector(stream)

    def write(self,stream):
        plConditionalObject.write(self,stream)
        self.fActivators.update(self.Key)
        self.fActivators.WriteVector(stream)



class plFacingConditionalObject(plConditionalObject):
    def __init__(self,parent,name = "unnamed"):
        plConditionalObject.__init__(self,parent,name,0x3E)
        self.fTolerance = -1.0
        self.fDirectional = False

    def _Find(page,name):
        return page.find(0x003E,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x003E,name,1)
    FindCreate = staticmethod(_FindCreate)


    def read(self,stream):
        plConditionalObject.read(self,stream)
        self.fTolerance = stream.ReadFloat()
        self.fDirectional = stream.ReadBool()


    def write(self,stream):
        plConditionalObject.write(self,stream)
        stream.WriteFloat(self.fTolerance)
        stream.WriteBool(self.fDirectional)



#################
##             ##
##  Modifiers  ##
##             ##
#################
class plMultistageBehMod(plSingleModifier):
    def __init__(self,parent,name="unnamed",type=0x00C1):
        plSingleModifier.__init__(self,parent,name,type)

        self.fStages = []
        self.fFreezePhys = True #this+0x70
        self.fSmartSeek = True #this+0x71
        self.fReverseFBControlsOnRelease = False #this+0x72
        self.fReceivers = hsTArray()


    def read(self, s):
        plSingleModifier.read(self, s)

        self.fFreezePhys = s.ReadBool()
        self.fSmartSeek = s.ReadBool()
        self.fReverseFBControlsOnRelease = s.ReadBool()

        count = s.Read32()
        for i in range(count):
            self.fStages[i] = plAnimStage()
            self.fStages[i].read(s)

        self.fReceivers.ReadVector(s)


    def write(self, s):
        plSingleModifier.write(self, s)

        s.WriteBool(self.fFreezePhys)
        s.WriteBool(self.fSmartSeek)
        s.WriteBool(self.fReverseFBControlsOnRelease)

        s.Write32(len(self.fStages))
        for stage in self.fStages:
            stage.write(s)

        self.fReceivers.WriteVector(s)

class plSittingModifier(plSingleModifier):
    Flags = \
    { \
        "kApproachFront"  :  0x1, \
        "kApproachLeft"   :  0x2, \
        "kApproachRight"  :  0x4, \
        "kApproachRear"   :  0x8, \
        "kApproachMask"   :  0xF, \
        "kDisableForward" : 0x10  \
    }

    def __init__(self,parent,name = "unnamed"):
        plSingleModifier.__init__(self,parent,name,0x00AE)

        self.fMiscFlags = 0
        self.fNotifyKeys = []

    def _Find(page,name):
        return page.find(0x00AE,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00AE,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plSingleModifier.read(self,stream)

        self.fMiscFlags = stream.ReadByte()
        count = stream.Read32()
        for i in range(count):
            key = UruObjectRef()
            key.read(stream)
            self.fNotifyKeys.append(key)

    def write(self,stream):
        plSingleModifier.write(self,stream)

        self.WriteByte(self.fMiscFlags)
        self.Write32(len(self.fNotifyKeys))
        for key in self.fNotifyKeys:
            key.write(stream)


class plOneShotMod(plMultiModifier):
    def __init__(self,parent,name="unnamed",type=0x0077):
        plMultiModifier.__init__(self,parent,name,type)
        self.fAnimName = ""
        self.fSeekDuration = 2.0
        self.fDrivable = False
        self.fReversable = False
        self.fSmartSeek = True
        self.fNoSeek = False

    def _Find(page,name):
        return page.find(0x0077,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0077,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plMultiModifier.read(self,stream)
        self.fAnimName = stream.ReadSafeString()
        self.fSeekDuration = stream.ReadFloat()
        self.fDrivable = stream.ReadBool()
        self.fReversable = stream.ReadBool()
        self.fSmartSeek = stream.ReadBool()
        self.fNoSeek = stream.ReadBool()

    def write(self,stream):
        plMultiModifier.write(self,stream)
        stream.WriteSafeString(self.fAnimName)
        stream.WriteFloat(self.fSeekDuration)
        stream.WriteBool(self.fDrivable)
        stream.WriteBool(self.fReversable)
        stream.WriteBool(self.fSmartSeek)
        stream.WriteBool(self.fNoSeek)



class plPythonFileMod(plMultiModifier):

    def __init__(self,parent,name="unnamed",type=0x00A2):
        plMultiModifier.__init__(self,parent,name,type)

        self.fPythonFile = ""
        self.fReceivers = [] # array of plKey
        self.fParameters = []

    def _Find(page,name):
        return page.find(0x00A2,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00A2,name,1)
    FindCreate = staticmethod(_FindCreate)


    def read(self,stream):
        plMultiModifier.read(self,stream)

        self.fPythonFile = stream.ReadSafeString()

        self.fReceivers = []
        count = stream.Read32()
        for i in range(count):
            key = UruObjectRef()
            key.read(stream)
            self.fReceivers.append(key)

        count = stream.Read32()
        self.fParameters = []
        for i in range(count):
            parm = plPythonParameter(self.parent)
            parm.read(stream)
            self.fParameters.append(parm)

    def write(self,stream):
        plMultiModifier.write(self,stream)

        stream.WriteSafeString(self.fPythonFile)

        stream.Write32(len(self.fReceivers))
        for key in self.fReceivers:
            key.write(stream)

        stream.Write32(len(self.fParameters))
        for parm in self.fParameters:
            parm.write(stream)

    def addParameter(self,pyparam):
        self.fParameters.append(pyparam)


class plPythonParameter :
    #version Uru
    ValueType = \
    { \
        "kInt"                  :  1, \
        "kFloat"                :  2, \
        "kBoolean"              :  3, \
        "kString"               :  4, \
        "kSceneObject"          :  5, \
        "kSceneObjectList"      :  6, \
        "kActivatorList"        :  7, \
        "kResponderList"        :  8, \
        "kDynamicText"          :  9, \
        "kGUIDialog"            : 10, \
        "kExcludeRegion"        : 11, \
        "kAnimation"            : 12, \
        "kAnimationName"        : 13, \
        "kBehavior"             : 14, \
        "kMaterial"             : 15, \
        "kGUIPopUpMenu"         : 16, \
        "kGUISkin"              : 17, \
        "kWaterComponent"       : 18, \
        "kSwimCurrentInterface" : 19, \
        "kClusterComponentList" : 20, \
        "kMaterialAnimation"    : 21, \
        "kGrassShaderComponent" : 22, \
        "kNone"                 : 23  \
    }

# Type Table - for use in the read/write functions
    ValueTypeTable = \
    { \
         1: "int", \
         2: "float", \
         3: "bool", \
         4: "str", \
         5: "key", \
         6: "key", \
         7: "key", \
         8: "key", \
         9: "key", \
        10: "key", \
        11: "key", \
        12: "key", \
        13: "str", \
        14: "key", \
        15: "key", \
        16: "key", \
        17: "key", \
        18: "key", \
        19: "key", \
        20: "key", \
        21: "key", \
        22: "key", \
        23: "None" \
    }

 # From the cobbs wiki:
 #   Type  6 refs a type 0x0001-SceneObject
 #   Type  7 refs a type 0x002D-LogicModifier,
 #                  type 0x00A2-PythonFileMod,
 #                  type 0x00AE-SittingModifier,
 #                  type 0x00C4-AnimEventModifier, or
 #                  type 0x00F5-NPCSpawnMod
 #   Type  8 refs a type 0x007C-ResponderModifier
 #   Type  9 refs a type 0x00AD-DynamicTextMap
 #   Type 10 refs a type 0x0098-GUIDialogMod
 #   Type 11 refs a type 0x00A4-ExcludeRegionModifier
 #   Type 12 refs a type 0x006D-AGMasterMod, or
 #                  type 0x00A8-MessageForwarder
 #   Type 14 refs a type 0x0077-OneShotMod, or
 #                  type 0x00C1-MultiStageBehMod
 #   Type 15 refs a type 0x0004-MipMap (HSM)
 #   Type 18 refs a type 0x00FB-WaveSet7
 #   Type 19 refs a type 0x0134-SwimCircularCurrentRegion, or
 #                  type 0x0136-SwimStraightCurrentRegion
 #   Type 20 refs a type 0x012B-ClusterGroup
 #   Type 21 refs a type 0x0043-LayerAnimation

# This list is used to determine which object types are related to what kinds of value:


    # next list translates script names (lowercase)  to blocks of type-specific information
    ScriptValueType = \
    { \
        "int"                   : {"typenum":  1, "type": "int"     }, \
        "float"                 : {"typenum":  2, "type": "float"   }, \
        "bool"                  : {"typenum":  3, "type": "bool"    }, \
        "string"                : {"typenum":  4, "type": "str"     }, \
        "sceneobject"           : {"typenum":  5, "type": "key",     "defaultkeytype": 0x0001, "allowlist": [0x0001,] }, \
        "sceneobjectlist"       : {"typenum":  6, "type": "keylist", "defaultkeytype": 0x0001, "allowlist": [0x0001,] }, \
        "activator"             : {"typenum":  7, "type": "key",     "defaultkeytype": 0x002D,  "allowlist": [0x002D,0x00A2,0x00AE,] }, \
        "activatorlist"         : {"typenum":  7, "type": "keylist", "defaultkeytype": 0x002D,  "allowlist": [0x002D,0x00A2,0x00AE,] }, \
        "responder"             : {"typenum":  8, "type": "key",     "defaultkeytype": 0x007C, "allowlist": [0x007C,] }, \
        "responderlist"         : {"typenum":  8, "type": "keylist", "defaultkeytype": 0x007C, "allowlist": [0x007C,] }, \
#       "dynamictext"           : {"typenum":  9, "type": "key",     "defaultkeytype": 0x00AD, "allowlist": [0x00AD,] }, \
#       "guidialog"             : {"typenum": 10, "type": "key",     "defaultkeytype": 0x0098, "allowlist": [0x0098,] }, \
#       "excluderegion"         : {"typenum": 11, "type": "key",     "defaultkeytype": 0x00A4, "allowlist": [0x00A4,] }, \
#       "animation"             : {"typenum": 12, "type": "key",     "defaultkeytype": None,   "allowlist": [0x006D,0x00A8,] }, \
        "animationname"         : {"typenum": 13, "type": "str"}, \
# Duplicate is to allow for english spelling:
        "behaviour"             : {"typenum": 14, "type": "key",     "defaultkeytype": 0x0077,  "allowlist": [0x0077,] }, \
        "behavior"              : {"typenum": 14, "type": "key",     "defaultkeytype": 0x0077,  "allowlist": [0x0077,] }, \
        "material"              : {"typenum": 15, "type": "key",     "defaultkeytype": 0x0004, "allowlist": [0x0004,], "tag": "texture",  }, \
#       "guipopupmenu"          : {"typenum": 16, "type": "key",     "defaultkeytype": None,   "allowlist": [0x0119,] }, \
#       "guiskin"               : {"typenum": 17, "type": "key",     "defaultkeytype": None,   "allowlist": [0xFFFF,] }, \
#       "watercomponent"        : {"typenum": 18, "type": "key",     "defaultkeytype": 0x00FB, "allowlist": [0x00FB,] }, \
        "swimcurrentinterface"  : {"typenum": 19, "type": "key",     "defaultkeytype": None,   "allowlist": [0x0136,0x0134,] }, \
#       "clustercomponentlist"  : {"typenum": 20, "type": "keylist", "defaultkeytype": 0x012B, "allowlist": [0x012B,] }, \
#       "materialanimation"     : {"typenum": 21, "type": "key",     "defaultkeytype": 0x0043, "allowlist": [0x0043,] }, \
#       "grassshadercomponent"  : {"typenum": 22, "type": "key",     "defaultkeytype": None,   "allowlist": [0xFFFF] }, \
        "none"                  : {"typenum": 23, "type": "none" } \
    }

    def __init__(self,parent):
        self.parent = parent
        self.fID = 0
        self.fValueType = plPythonParameter.ValueType["kNone"]
        self.fObjectKey = UruObjectRef(self.parent.data.getVersion())

        self.fValue = None

    def read(self,stream):

        self.fValueType = plPythonParameter.ValueType["kNone"]
        self.fID = stream.Read32()
        self.fValueType = stream.Read32()

        if plPythonParameter.ValueTypeTable[self.fValueType] == "int":
            self.fValue = stream.Read32()

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "bool":
            self.fValue = bool(stream.Read32())

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "float":
            self.fValue = stream.ReadFloat()

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "str":
            size = stream.Read32()
            self.fValue = stream.read(size)

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "key":
            self.fObjectKey.read(stream)

    def write(self,stream):

        stream.Write32(self.fID)
        stream.Write32(self.fValueType)

        if plPythonParameter.ValueTypeTable[self.fValueType] == "int":
            stream.Write32(self.fValue)

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "bool":
            stream.Write32(int(self.fValue))

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "float":
            stream.WriteFloat(self.fValue)

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "str":
            stream.Write32(len(str(self.fValue))+1)
            stream.write(str(self.fValue))
            stream.WriteByte(00) # Add terminator character

        elif plPythonParameter.ValueTypeTable[self.fValueType] == "key":
            self.fObjectKey.write(stream)



class plResponderModifier(plSingleModifier):

    Flags = \
    { \
        "kDetectTrigger"    : 0x1, \
        "kDetectUnTrigger"  : 0x2, \
        "kSkipFFSound"      : 0x4  \
    }

    ScriptFlags = \
    {
        "detecttrigger"    : 0x1, \
        "detectuntrigger"  : 0x2, \
        "skipffsound"      : 0x4  \
    }

    def __init__(self,parent,name="unnamed",type=0x007C):
        plSingleModifier.__init__(self,parent,name,type)

        self.fSDLExcludeList.append("Responder")

        self.fStates = []
        self.fCurState = 0
        self.fEnabled = True
        self.fFlags = plResponderModifier.Flags["kDetectTrigger"] # default to this, since that's what we'll b using it for

    def _Find(page,name):
        return page.find(0x007C,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x007C,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream,size):
        start = stream.tell() # Keep start offset in case of trouble...
        plSingleModifier.read(self,stream)

        count = stream.ReadByte()
        self.fStates = []

        # The try block is to ensure proper reading when we encounter an unknown message type
        # Which ofcourse should happen pretty often until we sort out all neccesary messages....

        try:

            for i in range(count):
                state = plResponderState(self)
                state.read(stream)
                self.fStates.append(state)

        except ValueError, detail:
            print "/---------------------------------------------------------"
            print "|  WARNING:"
            print "|   Got Value Error:" , detail, ":"
            print "|   Skipping state array of plResponderModifier"
            print "|   -> Skipping %i bytes ahead " % ( (start + size - 3) - stream.tell())
            print "|   -> Total object size: %i bytes"% (size)
            print "\---------------------------------------------------------\n"

            stream.seek(start + size - 3) #reposition the stream to read in the last 3 bytes

        state = stream.ReadByte()

        if state >= 0 and state < len(self.fStates):
            self.fCurState = state
        else:
            #Invalid state %d specified, will default to current state", state);
            pass

        self.fEnabled = stream.ReadBool()
        self.fFlags = stream.ReadByte()

    def write(self,stream):
        plSingleModifier.write(self,stream)

        stream.WriteByte(len(self.fStates))

        for state in self.fStates:
            state.write(stream)

        # Check if the current state is actually valid - else, we make it state "0"
        if self.fCurState >= 0 and self.fCurState < len(self.fStates):
            stream.WriteByte(self.fCurState)
        else:
            stream.WriteByte(0)

        stream.WriteBool(self.fEnabled)
        stream.WriteByte(self.fFlags)




class plResponderState:
    def __init__(self,parent):
        self.parent = parent
        self.fCmds = [] # hsTArray<plResponderCmd> fCmds;
        self.fNumCallbacks = 0
        self.fSwitchToState = 0
        self.fWaitToCmd = {}


    def read(self,stream):
        self.fNumCallbacks = stream.ReadByte()
        self.fSwitchToState = stream.ReadByte()

        self.fCmds = []
        count = stream.ReadByte()
        for i in range(count):
            cmd = plResponderCmd(self)
            cmd.read(stream)
            self.fCmds.append(cmd)

        self.fWaitToCmd.clear()
        count = stream.ReadByte()
        for i in range(count):
            wait = stream.ReadByte()
            value = stream.ReadByte()
            self.fWaitToCmd[wait] = value

    def write(self,stream):
        stream.WriteByte(self.fNumCallbacks)
        stream.WriteByte(self.fSwitchToState)
        stream.WriteByte(len(self.fCmds))

        for cmd in self.fCmds:
            cmd.write(stream)

        stream.WriteByte(len(self.fWaitToCmd.keys()))
        for key in self.fWaitToCmd.keys():
            stream.WriteByte(key)
            stream.WriteByte(self.fWaitToCmd[key])


class plResponderCmd:
    ScriptMsgTypes = \
    { \
        "armatureeffectmsg" : 0x038E, \
        "oneshotmsg"        : 0x0302, \
        "cameramsg"         : 0x020A, \
        "enablemsg"         : 0x024F, \
        "soundmsg"          : 0x0255, \
    }

    def __init__(self,parent):
        self.parent = parent
        self.fMsg = None
        self.fWaitOn = -1

    def read(self,stream):
        self.fMsg = PrpMessage.FromStream(stream)
        self.fWaitOn = stream.ReadSignedByte()

    def write(self,stream):
        PrpMessage.ToStream(stream,self.fMsg)
        stream.WriteSignedByte(self.fWaitOn)


class plAvLadderMod(plSingleModifier):
    #Rewritten at Oct/11/2006
    fTypeField = \
    { \
        "kBig": 0, \
        "kFourFeet": 1, \
        "kTwoFeet":2, \
        "kNumOfTypeFields":3 \
    }

    def __init__(self,parent,name="unnamed",type=0x00B2):
        plSingleModifier.__init__(self,parent,name,type)
        #format
        self.fType = 0
        self.fLoops = 1
        self.fGoingUp = False
        self.fEnabled = True
        self.fLadderView = Vertex()

    def _Find(page,name):
        return page.find(0x00B2,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00B2,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plSingleModifier.changePageRaw(self,sid,did,stype,dtype)


    def read(self,stream):
        plSingleModifier.read(self,stream)
        self.fType = stream.Read32()
        self.fLoops = stream.Read32()
        self.fGoingUp = stream.ReadBool()
        self.fEnabled = stream.ReadBool()
        self.fLadderView.read(stream)


    def write(self,stream):
        plSingleModifier.write(self,stream)
        stream.Write32(self.fType)
        stream.Write32(self.fLoops)
        stream.WriteBool(self.fGoingUp)
        stream.WriteBool(self.fEnabled)
        self.fLadderView.write(stream)

        # print "*writing ladder mod*"
        # print "Type: %d" % self.fType
        # print "Loops: %d" % self.fLoops
        # print "GoingUp: %s" % self.fGoingUp
        # print "Enabled: %s" % self.fEnabled
        # print "LadderView: "
        # print self.fLadderView

    def import_obj(self,obj):
        try:
            obj.removeProperty("regiontype")
        except:
            pass
        obj.addProperty("regiontype","ladder")

        objscript = AlcScript.objects.FindOrCreate(obj.name)

        if self.fType == plAvLadderMod.fTypeField["kBig"]:
            StoreInDict(objscript,"region.ladder.style","big")
        elif self.fType == plAvLadderMod.fTypeField["kFourFeet"]:
            StoreInDict(objscript,"region.ladder.style","fourfeet")
        elif self.fType == plAvLadderMod.fTypeField["kTwoFeet"]:
            StoreInDict(objscript,"region.ladder.style","twofeet")

        StoreInDict(objscript,"region.ladder.loops",self.fLoops)
        if self.fGoingUp:
            StoreInDict(objscript,"region.ladder.direction","up")
        else:
            StoreInDict(objscript,"region.ladder.direction","down")

        v = Vertex(self.fLadderView.x,self.fLadderView.y,self.fLadderView.z)

        matrix = getMatrix(obj)
        rotMatrix = matrix.rotationPart().resize4x4()
        rotMatrix.invert()
        rotMatrix.transpose()
        m = hsMatrix44()
        m.set(rotMatrix)
        v.transform(m)

        StoreInDict(objscript,"region.ladder.ladderview",str(v))




