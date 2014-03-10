#
# $Id: alc_CamClasses.py 843 2007-11-04 01:19:29Z Trylon $
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
#from alc_LogicClasses import *
from alc_Functions import *
from alcConvexHull import *
from alc_VolumeIsect import *
from alc_AlcScript import *
from alc_RefParser import *
from alc_Messages import *
import alcconfig, alchexdump



################# Rework of the camera classes ###################

class CamTrans:
    def __init__(self,parent):
        self.parent = parent
        self.fTransTo = UruObjectRef()
        self.fCutPos = False # boolean
        self.fCutPOA = False # boolean
        self.fIgnore = False # boolean
        self.fAccel = 60.0
        self.fDecel = 60.0
        self.fVelocity = 60.0
        self.fPOAAccel = 60.0
        self.fPOADecel = 60.0
        self.fPOAVelocity = 60.0

    def read(self,stream):
        print "w"
        self.fTransTo.read(stream)
        print "v"
        self.fCutPos = stream.ReadBool()
        self.fCutPOA = stream.ReadBool()
        self.fIgnore = stream.ReadBool()
        self.fVelocity = stream.ReadFloat()
        self.fAccel = stream.ReadFloat()
        self.fDecel = stream.ReadFloat()
        self.fPOAVelocity = stream.ReadFloat()
        self.fPOAAccel = stream.ReadFloat()
        self.fPOADecel = stream.ReadFloat()

    def write(self,stream):
        self.fTransTo.write(stream)
        stream.WriteBool(self.fCutPos)
        stream.WriteBool(self.fCutPOA)
        stream.WriteBool(self.fIgnore)
        stream.WriteFloat(self.fVelocity)
        stream.WriteFloat(self.fAccel)
        stream.WriteFloat(self.fDecel)
        stream.WriteFloat(self.fPOAVelocity)
        stream.WriteFloat(self.fPOAAccel)
        stream.WriteFloat(self.fPOADecel)

    def import_obj(self,obj,count):
        pass


class plCameraModifier1(plSingleModifier):    # actually descends from plSingleModifer, but doesn't use those read/write functions


    def __init__(self,parent,name="unnamed",type=0x009B):
        plSingleModifier.__init__(self,parent,name,type)
        #format
        self.fBrain=UruObjectRef()

        self.fTrans = [] #CamTrans Fields

        #Ending is almost always like this:
        self.fFOVw = 45.0 # Field of View
        self.fFOVh = 33.75 #

        self.fMessageQueue = []
        self.fFOVInstructions = []

        self.fAnimated = False
        self.fStartAnimOnPush = False
        self.fStopAnimOnPop = False
        self.fResetAnimOnPop = False

    def _Find(page,name):
        return page.find(0x009B,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x009B,name,1)
    FindCreate = staticmethod(_FindCreate)


    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream,size):
        start = stream.tell()
        hsKeyedObject.read(self,stream)

        self.fBrain.read(stream)

        count = stream.Read32()
        for i in range(count):
            cam = CamTrans(self)
            cam.read(stream) # not like this in Plasma, but makes it easier here :)
            self.fTrans.append(cam)

        self.fFOVw = stream.ReadFloat()
        self.fFOVh = stream.ReadFloat()

        count = stream.Read32()
        # we now should read in a message queue, which is hard because of incomplete message implementations


        try:
            print "Y"

            for i in range(count):
                Msg = PrpMessage.FromStream(stream)
                self.fMessageQueue.add(Msg.data)

            print "Z"

            for msg in self.fMessageQueue:
                msg.fSender.read(stream)

            # read in queue of plCameraMSgs
            self.fFOVInstructions = []
            count = stream.Read32()
            for i in range(count):
                Msg = PrpMessage.FromStream(stream)
                self.fFOVInstructions.append(FovMsg.data)

        except ValueError, detail:
            print "/---------------------------------------------------------"
            print "|  WARNING:"
            print "|   Got Value Error:" , detail, ":"
            print "|   Skipping message arrays of plCameraModifier1..."
            print "|   -> Skipping %i bytes ahead " % ( (start + size -4) - stream.tell())
            print "|   -> Total object size: %i bytes"% (size)
            print "\---------------------------------------------------------\n"

            stream.seek(start + size - 4) #reposition the stream to read in the last 4 bytes

        self.fAnimated = stream.ReadBool()
        self.fStartAnimOnPush = stream.ReadBool()
        self.fStopAnimOnPop = stream.ReadBool()
        self.fResetAnimOnPop = stream.ReadBool()

    def write(self,stream):
        hsKeyedObject.write(self,stream)

        self.fBrain.write(stream)

        stream.Write32(len(self.fTrans))
        for cam in self.fTrans:
            cam.write(stream)

        stream.WriteFloat(self.fFOVw)
        stream.WriteFloat(self.fFOVh)


        stream.Write32(len(self.fMessageQueue))
        for msg in self.fMessageQueue:
            PrpMessage.ToStream(stream,msg)

        for msg in self.fMessageQueue:
            msg.fSender.write(stream)

        stream.Write32(len(self.fFOVInstructions))
        for msg in self.fFOVInstructions:
            PrpMessage.ToStream(stream,msg)

        stream.WriteBool(self.fAnimated)
        stream.WriteBool(self.fStartAnimOnPush)
        stream.WriteBool(self.fStopAnimOnPop)
        stream.WriteBool(self.fResetAnimOnPop)



    def import_obj(self,obj):
        root = self.getRoot()

        # calculate the camera lens (blender has 32 mm camera)
        radian_fFOVh = self.fFOVh / (360/(2*math.pi))

        lens = 32/(2*math.tan(radian_fFOVh/2))

        # now set the blender lens property
        obj.data.setLens(lens)

        c = 0
        for cam in self.fTrans:
            cam.import_obj(obj,c)
            c = c+1

        cbrain = root.findref(self.fBrain)
        cbrain.data.import_obj(obj)

        pass

    def _Import(scnobj,prp,obj):
        # Lights
        for c_ref in  scnobj.data1.vector:
            if c_ref.Key.object_type in [0x009B,]:
                cam=prp.findref(c_ref)
                cam.data.import_obj(obj)
                obj.layers=[5,]
                break

    Import = staticmethod(_Import)


class plCameraBrain1(hsKeyedObject):

    Flags = {
        "kCutPos"                   : 0,
        "kCutPosOnce"               : 1,
        "kCutPOA"                   : 2,
        "kCutPOAOnce"               : 3,
        "kAnimateFOV"               : 4,
        "kFollowLocalAvatar"        : 5,
        "kPanicVelocity"            : 6,
        "kRailComponent"            : 7,
        "kSubject"                  : 8,
        "kCircleTarget"             : 9,
        "kMaintainLOS"              : 10,
        "kZoomEnabled"              : 11,
        "kIsTransitionCamera"       : 12,
        "kWorldspacePOA"            : 13,
        "kWorldspacePos"            : 14,
        "kCutPosWhilePan"           : 15,
        "kCutPOAWhilePan"           : 16,
        "kNonPhys"                  : 17,
        "kNeverAnimateFOV"          : 18,
        "kIgnoreSubworldMovement"   : 19,
        "kFalling"                  : 20,
        "kRunning"                  : 21,
        "kVerticalWhenFalling"      : 22,
        "kSpeedUpWhenRunning"       : 23,
        "kFallingStopped"           : 24,
        "kBeginFalling"             : 25
    }

    ScriptFlags = {
        "cutpos"                   : 0,
        "cutposonce"               : 1,
        "cutpoa"                   : 2,
        "cutpoaonce"               : 3,
        "animatefov"               : 4,
        "followlocalavatar"        : 5,
        "panicvelocity"            : 6,
        "railcomponent"            : 7,
        "subject"                  : 8,
        "circletarget"             : 9,
        "maintainlos"              : 10,
        "zoomenabled"              : 11,
        "istransitioncamera"       : 12,
        "worldspacepoa"            : 13,
        "worldspacepos"            : 14,
        "cutposwhilepan"           : 15,
        "cutpoawhilepan"           : 16,
        "nonphys"                  : 17,
        "neveranimatefov"          : 18,
        "ignoresubworldmovement"   : 19,
        "falling"                  : 20,
        "running"                  : 21,
        "verticalwhenfalling"      : 22,
        "speedupwhenrunning"       : 23,
        "fallingstopped"           : 24,
        "beginfalling"             : 25
    }



    def __init__(self,parent,name="unnamed",type=0x0099):
        hsKeyedObject.__init__(self,parent,name,type)
        #format
        self.fFlags=hsBitVector()

        # -------- Initialize default settings
        self.fFlags.SetBit(plCameraBrain1.Flags["kFollowLocalAvatar"])

        self.fPOAOffset = Vertex(0.0,0.0,6.0)

        self.fSubjectKey=UruObjectRef()
        self.fRail=UruObjectRef()

        self.fAccel = 30
        self.fDecel = 30
        self.fVelocity = 30
        self.fPOAAccel = 30
        self.fPOADecel = 30
        self.fPOAVelocity = 30
        self.fXPanLimit = 0
        self.fZPanLimit = 0
        self.fZoomRate = 0
        self.fZoomMin = 0
        self.fZoomMax = 0

    def _Find(page,name):
        return page.find(0x0099,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0099,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)
        self.fSubjectKey.changePageRaw(sid,did,stype,dtype)
        self.fRail.changePageRaw(sid,did,stype,dtype)


    def read(self,stream):
        hsKeyedObject.read(self,stream)

        self.fPOAOffset.read(stream)
        self.fSubjectKey.read(stream)
        self.fRail.read(stream)
        self.fFlags.read(stream)

        self.fAccel = stream.ReadFloat()
        self.fDecel = stream.ReadFloat()
        self.fVelocity = stream.ReadFloat()
        self.fPOAAccel = stream.ReadFloat()
        self.fPOADecel = stream.ReadFloat()
        self.fPOAVelocity = stream.ReadFloat()
        self.fXPanLimit = stream.ReadFloat()
        self.fZPanLimit = stream.ReadFloat()
        self.fZoomRate = stream.ReadFloat()
        self.fZoomMin = stream.ReadFloat()
        self.fZoomMax = stream.ReadFloat()

    def write(self,stream):
        hsKeyedObject.write(self,stream)

        self.fPOAOffset.write(stream)
        self.fSubjectKey.write(stream)
        self.fRail.write(stream)
        self.fFlags.write(stream)

        stream.WriteFloat(self.fAccel)
        stream.WriteFloat(self.fDecel)
        stream.WriteFloat(self.fVelocity)
        stream.WriteFloat(self.fPOAAccel)
        stream.WriteFloat(self.fPOADecel)
        stream.WriteFloat(self.fPOAVelocity)
        stream.WriteFloat(self.fXPanLimit)
        stream.WriteFloat(self.fZPanLimit)
        stream.WriteFloat(self.fZoomRate)
        stream.WriteFloat(self.fZoomMin)
        stream.WriteFloat(self.fZoomMax)


    def import_obj(self,obj):
        objscript = AlcScript.objects.FindCreate(obj.name)
        StoreInDict(objscript,"camera.brain.type","simple")

        StoreInDict(objscript,"camera.brain.poa","%f,%f,%f"%(float(self.fPOAOffset.x),float(self.fOAOffset.y),float(self.fPOAOffset.z)))
        StoreInDict(objscript,"camera.brain.accel",self.fAccel)
        StoreInDict(objscript,"camera.brain.decel",self.fDecel)
        StoreInDict(objscript,"camera.brain.velocity",self.fVelocity)
        StoreInDict(objscript,"camera.brain.poaaccel",self.fPOAAccel)
        StoreInDict(objscript,"camera.brain.poadecel",self.fPOADecel)
        StoreInDict(objscript,"camera.brain.poavelocity",self.fPOAVelocity)
        StoreInDict(objscript,"camera.brain.xpanlimit",self.fXPanLimit)
        StoreInDict(objscript,"camera.brain.zpanlimit",self.fZPanLimit)
        StoreInDict(objscript,"camera.brain.zoomrate",self.fZoomRate)
        StoreInDict(objscript,"camera.brain.zoommin",self.fZoomMin)
        StoreInDict(objscript,"camera.brain.zoommax",self.fZoomMax)

        if not self.fRail.isNull():
            StoreInDict(objscript,"camera.brain.rail","%0x%X:%s"%(int(self.fSubjectKey.object_type),str(self.fSubjectKey.Key.Name)))

        if not self.fSubjectKey.isNull():
            StoreInDict(objscript,"camera.brain.subjectkey","%0x%X:%s"%(int(self.fSubjectKey.object_type),str(self.fSubjectKey.Key.Name)))




class plCameraBrain1_Fixed(plCameraBrain1):
    def __init__(self,parent,name="unnamed",type=0x009F):
        plCameraBrain1.__init__(self,parent,name,type)

        # set the Camerabrain1 floats to match defaults for this brain type
        self.fAccel = 30
        self.fDecel = 30
        self.fVelocity = 30
        self.fPOAAccel = 30
        self.fPOADecel = 30
        self.fPOAVelocity = 30
        self.fXPanLimit = 0
        self.fZPanLimit = 0
        self.fZoomRate = 0
        self.fZoomMin = 0
        self.fZoomMax = 0

        #format
        self.fTargetPoint=UruObjectRef()

    def _Find(page,name):
        return page.find(0x009F,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x009F,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plCameraBrain1.changePageRaw(self,sid,did,stype,dtype)
        self.fTargetPoint.changePageRaw(sid,did,stype,dtype)

    def read(self,stream):
        plCameraBrain1.read(self,stream)
        self.fTargetPoint.read(stream)

    def write(self,stream):
        plCameraBrain1.write(self,stream)
        self.fTargetPoint.write(stream)

    def import_obj(self,obj):
        plCameraBrain1.import_obj(self,obj)
        objscript = AlcScript.objects.FindCreate(obj.name)
        StoreInDict(objscript,"camera.brain.type","fixed")
        if not self.fTargetPoint.isNull():
            StoreInDict(objscript,"camera.brain.target","%0x%X:%s"%(int(self.fSubjectKey.object_type),str(self.fSubjectKey.Key.Name)))



class plCameraBrain1_Circle(plCameraBrain1_Fixed):
    CircleFlags = {
        "kLagged"               :  0x1,
        "kAbsoluteLag"          :  0x3,
        "kFarthest"             :  0x4,
        "kTargetted"            :  0x8,
        "kHasCenterObject"      : 0x10,
        "kPOAObject"            : 0x20,
        "kCircleLocalAvatar"    : 0x40
    }

    ScriptCircleFlags = {
        "lagged"               :  0x1,
        "absolutelag"          :  0x3,
        "farthest"             :  0x4,
        "targetted"            :  0x8,
        "hascenterobject"      : 0x10,
        "poaobject"            : 0x20,
        "circlelocalavatar"    : 0x40
    }


    def __init__(self,parent,name="unnamed",type=0x00C2):
        plCameraBrain1_Fixed.__init__(self,parent,name,type)

        # set the Camerabrain1 floats to match defaults for this brain type
        self.fAccel = 10
        self.fDecel = 10
        self.fVelocity = 15
        self.fPOAAccel = 10
        self.fPOADecel = 10
        self.fPOAVelocity = 15
        self.fXPanLimit = 0
        self.fZPanLimit = 0
        self.fZoomRate = 0
        self.fZoomMin = 0
        self.fZoomMax = 0

        #format
        self.fCircleFlags = 0
        self.fCircleFlags |= plCameraBrain1_Circle.CircleFlags['kCircleLocalAvatar'] | \
                             plCameraBrain1_Circle.CircleFlags['kFarthest']

        self.fCenter = Vertex(0.0,0.0,0.0)

        self.fRadius = 0


        self.fCenterObject = UruObjectRef()
        self.fPOAObj = UruObjectRef()

        self.fCirPerSec = 0.10 # virtually always 0.10

    def _Find(page,name):
        return page.find(0x00C2,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00C2,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plCameraBrain1.changePageRaw(self,sid,did,stype,dtype)
        self.fCenterObject.changePageRaw(sid,did,stype,dtype)
        self.fPOAObj.changePageRaw(sid,did,stype,dtype)

    def read(self,stream):
        plCameraBrain1.read(self,stream) # yes, this is correct, it uses the plCameraBrain1 read/write functions

        self.fCircleFlags = stream.Read32()

        self.fCenter.read(stream)

        self.fRadius = stream.ReadFloat()

        self.fCenterObject.read(stream)
        self.fPOAObj.read(stream)

        self.fCirPerSec = stream.ReadFloat()

    def write(self,stream):
        plCameraBrain1.write(self,stream) # yes, this is correct, it uses the plCameraBrain1 read/write functions

        stream.Write32(self.fCircleFlags)
        self.fCenter.write(stream)
        stream.WriteFloat(self.fRadius)
        self.fCenterObject.write(stream)
        self.fPOAObj.write(stream)

        stream.WriteFloat(self.fCirPerSec)



    def import_obj(self,obj):
        plCameraBrain1.import_obj(self,obj)
        objscript = AlcScript.objects.FindCreate(obj.name)
        StoreInDict(objscript,"camera.brain.type","circle")

        obj.data.setClipEnd(self.fRadius)
        obj.data.setMode("showLimits")


        flaglist = []

        for flag in plCameraBrain1_Circle.ScriptCircleFlags.keys():
            if self.fCicleFlags & plCameraBrain1_Circle.ScriptCircleFlags[flag] > 0:
                flaglist.append(flag)


        StoreInDict(objscript,"camera.brain.cicleflags",flaglist)





class plCameraBrain1_Avatar(plCameraBrain1):
    def __init__(self,parent,name="unnamed",type=0x009E):
        plCameraBrain1.__init__(self,parent,name,type)
        # Set default flag...
        self.fFlags.SetBit(plCameraBrain1.Flags["kMaintainLOS"])

        # set the Camerabrain1 floats to match defaults for this brain type
        self.fAccel = 10
        self.fDecel = 10
        self.fVelocity = 50
        self.fPOAAccel = 10
        self.fPOADecel = 10
        self.fPOAVelocity = 50
        self.fXPanLimit = 0
        self.fZPanLimit = 0
        self.fZoomRate = 0
        self.fZoomMin = 0
        self.fZoomMax = 0

        #format
        self.fOffset = Vertex(0,0,0)


    def _Find(page,name):
        return page.find(0x009E,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x009E,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plCameraBrain1.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream):
        plCameraBrain1.read(self,stream)
        self.fOffset.read(stream)

    def write(self,stream):
        plCameraBrain1.write(self,stream)
        self.fOffset.write(stream)


    def import_obj(self,obj):
        plCameraBrain1.import_obj(self,obj)
        objscript = AlcScript.objects.FindCreate(obj.name)
        StoreInDict(objscript,"camera.brain.type","avatar")

        StoreInDict(objscript,"camera.brain.fpoffset","%f,%f,%f"%(float(self.fOffset.x),float(self.fOffset.y),float(self.fOffset.z)))



class plCameraBrain1_FirstPerson(plCameraBrain1_Avatar):
    def __init__(self,parent,name="unnamed",type=0x00B3):
        plCameraBrain1_Avatar.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x00B3,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00B3,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plCameraBrain1_Avatar.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream):
        plCameraBrain1_Avatar.read(self,stream)

    def write(self,stream):
        plCameraBrain1_Avatar.write(self,stream)


    def import_obj(self,obj):
        plCameraBrain1_Avatar.import_obj(self,obj)
        StoreInDict(objscript,"camera.brain.type","firstperson")

