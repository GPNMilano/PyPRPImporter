#
# $Id: alc_MatClasses.py 843 2007-09-13 01:19:29Z Trylon $
#
#    Copyright (C) 2005-2007  Alcugs pyprp Project Team
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
        from Blender import Ipo
        from Blender import BezTriple
    except Exception, detail:
        print detail
except ImportError:
    pass

import md5, random, binascii, cStringIO, copy, Image, math, struct, StringIO, os, os.path, pickle
import alc_AbsClasses
import alc_AnimClasses
from alc_AbsClasses import *
from alcurutypes import *
from alcdxtconv import *
from alchexdump import *
from alc_GeomClasses import *
from alc_Functions import *
from alcConvexHull import *
from alc_VolumeIsect import *
from alc_AlcScript import *
from alc_AnimClasses import *

def stripIllegalChars(name):

    ## Sirius fix for too long texture name BEGIN
    if name[-4] == '.': # filter extension
        name=name[:-4]

    sb = name.find("*")
    if sb != -1 and name.find("#") != -1: # filter useless size info
        #name = name[:sb] # we MUSTN'T remove the *x#y thingy, because sometimes the script will extract the SMALLEST of all textures.
        name = name.replace("#", "x") # However we can make it look a bit less ugly...

    nm = name.find("_LIGHTMAPGEN") # usually, this extension can be removed
    if nm != -1:
        name = name[:nm]
    ## Sirius fix for too long texture name END

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

################# Rework of the main Layer and Material Classes

class hsGMatState:
    StateIdx = \
    { \
        "kBlend" : 0x0, \
        "kClamp" : 0x1, \
        "kShade" : 0x2, \
        "kZ"     : 0x3, \
        "kMisc"  : 0x4  \
    }

    hsGMatBlendFlags =  \
    { \
        "kBlendTest"                :        0x1, \
        "kBlendAlpha"               :        0x2, \
        "kBlendMult"                :        0x4, \
        "kBlendAdd"                 :        0x8, \
        "kBlendAddColorTimesAlpha"  :       0x10, \
        "kBlendAntiAlias"           :       0x20, \
        "kBlendDetail"              :       0x40, \
        "kBlendNoColor"             :       0x80, \
        "kBlendMADD"                :      0x100, \
        "kBlendDot3"                :      0x200, \
        "kBlendAddSigned"           :      0x400, \
        "kBlendAddSigned2X"         :      0x800, \
        "kBlendMask"                :      0xF5E, \
        "kBlendInvertAlpha"         :     0x1000, \
        "kBlendInvertColor"         :     0x2000, \
        "kBlendAlphaMult"           :     0x4000, \
        "kBlendAlphaAdd"            :     0x8000, \
        "kBlendNoVtxAlpha"          :    0x10000, \
        "kBlendNoTexColor"          :    0x20000, \
        "kBlendNoTexAlpha"          :    0x40000, \
        "kBlendInvertVtxAlpha"      :    0x80000, \
        "kBlendAlphaAlways"         :   0x100000, \
        "kBlendInvertFinalColor"    :   0x200000, \
        "kBlendInvertFinalAlpha"    :   0x400000, \
        "kBlendEnvBumpNext"         :   0x800000, \
        "kBlendSubtract"            :  0x1000000, \
        "kBlendRevSubtract"         :  0x2000000, \
        "kBlendAlphaTestHigh"       :  0x4000000  \
    }

    hsGMatClampFlags = \
    { \
        "kClampTextureU"    : 0x1, \
        "kClampTextureV"    : 0x2, \
        "kClampTexture"     : 0x3  \
    }

    hsGMatShadeFlags = \
    { \
        "kShadeSoftShadow"          :        0x1, \
        "kShadeNoProjectors"        :        0x2, \
        "kShadeEnvironMap"          :        0x4, \
        "kShadeVertexShade"         :       0x20, \
        "kShadeNoShade"             :       0x40, \
        "kShadeBlack"               :       0x40, \
        "kShadeSpecular"            :       0x80, \
        "kShadeNoFog"               :      0x100, \
        "kShadeWhite"               :      0x200, \
        "kShadeSpecularAlpha"       :      0x400, \
        "kShadeSpecularColor"       :      0x800, \
        "kShadeSpecularHighlight"   :     0x1000, \
        "kShadeVertColShade"        :     0x2000, \
        "kShadeInherit"             :     0x4000, \
        "kShadeIgnoreVtxIllum"      :     0x8000, \
        "kShadeEmissive"            :    0x10000, \
        "kShadeReallyNoFog"         :    0x20000  \
    }

    hsGMatZFlags = \
    { \
        "kZIncLayer"    :  0x1, \
        "kZClearZ"      :  0x4, \
        "kZNoZRead"     :  0x8, \
        "kZNoZWrite"    : 0x10, \
        "kZMask"        : 0x1C, \
        "kZLODBias"     : 0x20 \
    }

    hsGMatMiscFlags = \
    { \
        "kMiscWireFrame"            :        0x1, \
        "kMiscDrawMeshOutlines"     :        0x2, \
        "kMiscTwoSided"             :        0x4, \
        "kMiscDrawAsSplats"         :        0x8, \
        "kMiscAdjustPlane"          :       0x10, \
        "kMiscAdjustCylinder"       :       0x20, \
        "kMiscAdjustSphere"         :       0x40, \
        "kMiscAdjust"               :       0x70, \
        "kMiscTroubledLoner"        :       0x80, \
        "kMiscBindSkip"             :      0x100, \
        "kMiscBindMask"             :      0x200, \
        "kMiscBindNext"             :      0x400, \
        "kMiscLightMap"             :      0x800, \
        "kMiscUseReflectionXform"   :     0x1000, \
        "kMiscPerspProjection"      :     0x2000, \
        "kMiscOrthoProjection"      :     0x4000, \
        "kMiscProjection"           :     0x6000, \
        "kMiscRestartPassHere"      :     0x8000, \
        "kMiscBumpLayer"            :    0x10000, \
        "kMiscBumpDu"               :    0x20000, \
        "kMiscBumpDv"               :    0x40000, \
        "kMiscBumpDw"               :    0x80000, \
        "kMiscBumpChans"            :    0xE0000, \
        "kMiscNoShadowAlpha"        :   0x100000, \
        "kMiscUseRefractionXform"   :   0x200000, \
        "kMiscCam2Screen"           :   0x400000, \
        "kAllMiscFlags"             :       0xFF  \
    }

    def __init__(self):
        self.fBlendFlags = 0x00
        self.fClampFlags = 0x00
        self.fShadeFlags = 0x00
        self.fZFlags     = 0x00
        self.fMiscFlags  = 0x00

    def read(self,buf):
        self.fBlendFlags = buf.Read32()
        self.fClampFlags = buf.Read32()
        self.fShadeFlags = buf.Read32()
        self.fZFlags     = buf.Read32()
        self.fMiscFlags  = buf.Read32()
        pass

    def write(self,buf):
        buf.Write32(self.fBlendFlags)
        buf.Write32(self.fClampFlags)
        buf.Write32(self.fShadeFlags)
        buf.Write32(self.fZFlags)
        buf.Write32(self.fMiscFlags)
        pass

class hsGMaterial(plSynchedObject):         # Type 0x07

    hsGCompFlags =  \
    { \
        "kCompShaded"            :    0x1, \
        "kCompEnvironMap"        :    0x2, \
        "kCompProjectOnto"       :    0x4, \
        "kCompSoftShadow"        :    0x8, \
        "kCompSpecular"          :   0x10, \
        "kCompTwoSided"          :   0x20, \
        "kCompDrawAsSplats"      :   0x40, \
        "kCompAdjusted"          :   0x80, \
        "kCompNoSoftShadow"      :  0x100, \
        "kCompDynamic"           :  0x200, \
        "kCompDecal"             :  0x400, \
#OBSOLETE        "kCompIsEmissive"        :  0x800, \
        "kCompIsLightMapped"     : 0x1000, \
        "kCompNeedsBlendChannel" : 0x2000  \
    }

    UpdateFlags =  \
    { \
        "kUpdateAgain" : 0x1 \
    }

    def __init__(self,parent,name="unnamed",type=0x0007):
        plSynchedObject.__init__(self,parent,name,type)

        self.fLOD = 0# Int32
        self.fLayersCount = 0
        self.fLayers = []   # hsTArray<plLayerInterface>
        self.fPiggyBacksCount = 0
        self.fPiggyBacks = [] # hsTArray<plLayerInterface>
        self.fCompFlags = 0 # UInt32
        self.fLoadFlags = 0 # UInt32
        #self.fLastUpdateTime# Single
        self.fZOffset = 0
        self.fCriteria = 0
        self.fRenderLevel = plRenderLevel()
        self.blendermaterial = None

    def _Find(page,name):
        return page.find(0x0007,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0007,name,1)
    FindCreate = staticmethod(_FindCreate)



    def write(self,stream):
        plSynchedObject.write(self,stream)

        stream.Write32(self.fLoadFlags);
        stream.Write32(self.fCompFlags);
        stream.Write32(len(self.fLayers));
        stream.Write32(len(self.fPiggyBacks));

        for key in self.fLayers:
            key.update(self.Key)
            key.write(stream)

        for key in self.fPiggyBacks:
            key.update(self.Key)
            key.write(stream)

    def read(self,stream):
        plSynchedObject.read(self,stream)

        self.fLoadFlags = stream.Read32();
        self.fCompFlags = stream.Read32();

        self.fLayersCount = stream.Read32();
        self.fPiggyBacksCount = stream.Read32();

        for i in range(self.fLayersCount):
            key = UruObjectRef(self.getVersion())
            key.read(stream)
            self.fLayers.append(key)

        for i in range(self.fPiggyBacksCount):
            key = UruObjectRef(self.getVersion())
            key.read(stream)
            self.fLayers.append(key)

    ###################################
    ##                               ##
    ##      Interface Functions      ##
    ##                               ##
    ###################################
    def ToBlenderMat(self,obj):
        if self.blendermaterial != None:
            return self.blendermaterial
        print "    [Material %s]"%(str(self.Key.name))


        resmanager=self.getResManager()
        texprp=resmanager.findPrp("Textures")
        root=self.getRoot()

        # create the material to work on:
        name = str(self.Key.name)
        self.blendermaterial=Blender.Material.New(name)
        mat=self.blendermaterial
        matmode=mat.getMode()
        mat.setMode(matmode)

        texid = 0

        for layerref in self.fLayers:
            layer = root.findref(layerref)
            if layer != None and layer.data.Key.object_type != 0x00F0 and layer.data.Key.object_type != 0x008E and layer.data.Key.object_type != 0x0046 and layer.data.Key.object_type != 0x0106: #plLayerSDLAnimation NIE
                # -- Retrieve from layer some info for the blender material
                ambientCol  = layer.data.fPreshadeColor
                diffuseCol  = layer.data.fRuntimeColor
                mirCol     = layer.data.fAmbientColor
                specCol     = layer.data.fSpecularColor
                mat.setAlpha(diffuseCol.a)
                mat.setRGBCol([diffuseCol.r,diffuseCol.g,diffuseCol.b])
                mat.setMirCol([mirCol.r,mirCol.g,mirCol.b])
                mat.setSpecCol([specCol.r,specCol.g,specCol.b])

                try:
                    emitfactor = emitCol.r / diffuseCol.r
                except:
                    emitfactor = 0.0
                mat.setEmit(emitfactor)

                try:
                    ambfactor = ambientCol.r/ diffuseCol.r
                except:
                    ambfactor = 1.0
                mat.setAmb(ambfactor)

                try:
                    specfactor = 0.4
                    mat.setSpec(specfactor)
                    mat.setHardness(layer.data.fSpecularPower)
                except:
                    layer.data.fSpecularPower > 2
                    specfactor = 0.0
                    mat.setSpec(specfactor)


##                if layer.data.fState.fShadeFlags | hsGMatState.hsGMatShadeFlags["kShadeNoFog"]:
##                    mat.mode |= Blender.Material.Modes['NOMIST']

                # -- Retrieve layer specific date into textures
                bitmap = None
                if not layer.data.fTexture.isNull(): # if a texture image is associated Retrieve the layer from that

                    # try to find it on the current page first....
                    bitmap = root.findref(layer.data.fTexture)
                    # and on the texture page if it isn't there..
                    if bitmap is None and not texprp is None:
                        bitmap = texprp.findref(layer.data.fTexture)

                if bitmap != None and bitmap.data.Key.object_type != 0x0106:
                    tex = bitmap.data.ToBlenderTex(str(layer.data.Key.name))
                else:
                    tex = Blender.Texture.New(str(layer.data.Key.name))
                    tex.setType('None')

                if tex != None and texid < 10:
                    mat.setTexture(texid,tex,Blender.Texture.TexCo["UV"],Blender.Texture.MapTo["COL"])
                    mtexlist = mat.getTextures()
                    mtex = mtexlist[texid]

                    if mtex != None:
                        layer.data.ToBlenderMTex(mtex,obj)

                    texid += 1

        return mat


    def layerCount(self):
        return len(self.fLayers)

    def ZBias(self):
        root = self.getRoot()
        UsesAlpha = True
        for layerref in self.fLayers:
            layer = root.findref(layerref)
            if(layer.type == 0x0043):
                UsesAlpha = False
            else:
                UsesAlpha = (UsesAlpha and layer.data.UsesAlpha)

#            if layer.data.UsesAlpha:
#                print "   DEBUG: Layer \"%s\" uses Alpha"%(layer.data.Key.name)
#            else:
#                print "   DEBUG: Layer \"%s\" is Opaque"%(layer.data.Key.name)

#        if UsesAlpha:
#            print "   DEBUG: Result - Material has Alpha"
#        else:
#            print "   DEBUG: Result - Material is Opaque"

        ZBias = int(self.fZOffset)
        if UsesAlpha and ZBias == 0:
            ZBias += 1

        return ZBias

    def Criteria(self):
        return self.fCriteria

    def TexLayerCount(self):
        root=self.getRoot()

        # count the layers that actually have a texture set.
        count = 0
        for layerref in self.fLayers:
            layer = root.findref(layerref)
            if(layer.data.fHasTexture != 0):
                count += 1
        return count

    def getBlenderTextures(self):
        return self.blendertextures



class plLayerInterface(plSynchedObject):     # Type 0x41 (uru)

    plUVWSrcModifiers = \
    { \
        "kUVWPassThru"  :        0x0, \
        "kUVWNormal"    :    0x10000, \
        "kUVWPosition"  :    0x20000, \
        "kUVWReflect"   :    0x30000, \
        "kUVWIdxMask"   : 0x0000FFFF  \
    }

    def __init__(self,parent,name="unnamed",type=None):
        plSynchedObject.__init__(self,parent,name,type)

        self.fUnderlay = UruObjectRef(self.getVersion())
        self.fOverLay = UruObjectRef(self.getVersion())
        self.fOwnedChannels = 0x00
        self.fPassThruChannels = 0x00
        self.fTransform = hsMatrix44()
        self.fPreshadeColor = RGBA(0.5,0.5,0.5,1.0,type=1) # Grey
        self.fRuntimeColor = RGBA(0.5,0.5,0.5,1.0,type=1) # Grey
        self.fAmbientColor = RGBA(0.0,0.0,0.0,0.0,type=1) # Clear
        self.fOpacity = 1.0
        self.fTexture = UruObjectRef(self.getVersion())
        self.fState = hsGMatState()
        self.fUVWSrc = 0
        self.fLODBias =  -1.0
        self.fSpecularColor = RGBA(0.0,0.0,0.0,1.0,type=1) # Black
        self.fSpecularPower = 1.0
        self.fVertexShader = UruObjectRef(self.getVersion())
        self.fPixelShader = UruObjectRef(self.getVersion())
        self.fBumpEnvXfm = hsMatrix44()

    def read(self,buf):
        plSynchedObject.read(self,buf)
        self.fUnderlay.read(buf)

    def write(self,buf):
        plSynchedObject.write(self,buf)
        self.fUnderlay.write(buf)

class plLayer(plLayerInterface):             # Type 0x06

    def __init__(self,parent,name="unnamed",type=0x0006):
        plLayerInterface.__init__(self,parent,name,type)

        self.fOwnedChannels = 0x3FFF;
        self.fPreshadeColor = RGBA(0.5,0.5,0.5,1.0,type=1) # Grey
        self.fRuntimeColor = RGBA(0.5,0.5,0.5,1.0,type=1) # Grey
        self.fAmbientColor = RGBA(0.0,0.0,0.0,0.0,type=1) # Clear
        self.fSpecularColor = RGBA(0.0,0.0,0.0,1.0,type=1) # Black

        self.fTransform = hsMatrix44()
        self.fOpacity = 1.0
        self.fState = hsGMatState()
        self.fUVWSrc = 0
        self.fLODBias = -1.0
        self.fSpecularPower = 1.0
        self.fTexture = UruObjectRef(self.getVersion())
        self.fVertexShader = UruObjectRef(self.getVersion())
        self.fPixelShader = UruObjectRef(self.getVersion())
        self.fBumpEnvXfm = hsMatrix44()

        self.fRenderLevel = plRenderLevel() #used to determine RenderLevel
        self.fZBias = 0

        self.fHasTexture = 0
        self.InitToDefault()

    def _Find(page,name):
        return page.find(0x0006,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0006,name,1)
    FindCreate = staticmethod(_FindCreate)


    def InitToDefault(self):
        fState = hsGMatState();
        self.fTexture = UruObjectRef(self.getVersion())
        self.fRuntimeColor = RGBA(0.5, 0.5, 0.5, 1.0)  # Grey
        self.fPreshadeColor = RGBA(0.5, 0.5, 0.5, 1.0) # Grey
        self.fAmbientColor = RGBA(0.0, 0.0, 0.0, 0.0)        # Clear
        self.fOpacity = 1.0
        self.fTransform = hsMatrix44()
        self.fUVWSrc = 0
        self.fLODBias = -1.0
        self.fSpecularColor = RGBA(0.0, 0.0, 0.0, 1.0)       # Black
        self.fSpecularPower = 1.0
        self.fVertexShader = UruObjectRef(self.getVersion())
        self.fPixelShader = UruObjectRef(self.getVersion())
        self.fBumpEnvXfm = hsMatrix44()

        self.fRenderLevel = plRenderLevel()
        self.UsesAlpha = False

        self.fHasTexture = 0

    def read(self,stream):
        plLayerInterface.read(self,stream)
        self.fState.read(stream)
        self.fTransform.read(stream)
        self.fPreshadeColor.read(stream)    #old: self.ambient
        self.fRuntimeColor.read(stream)     #old: self.diffuse
        self.fAmbientColor.read(stream)     #old: self.emissive
        self.fSpecularColor.read(stream)    #old: self.specular
        self.fUVWSrc = stream.Read32()
        self.fOpacity = stream.ReadFloat()
        self.fLODBias = stream.ReadFloat()
        self.fSpecularPower = stream.ReadFloat()
        self.fTexture.read(stream)
        self.fVertexShader.read(stream)
        self.fPixelShader.read(stream)
        self.fBumpEnvXfm.read(stream)

    def write(self,stream):
        plLayerInterface.write(self,stream)
        self.fState.write(stream)
        self.fTransform.write(stream)
        self.fPreshadeColor.write(stream)   #old: self.ambient
        self.fRuntimeColor.write(stream)    #old: self.diffuse
        self.fAmbientColor.write(stream)    #old: self.emissive
        self.fSpecularColor.write(stream)   #old: self.specular
        stream.Write32(self.fUVWSrc)
        stream.WriteFloat(self.fOpacity)
        stream.WriteFloat(self.fLODBias)
        stream.WriteFloat(self.fSpecularPower)
        self.fTexture.write(stream)
        self.fVertexShader.write(stream)
        self.fPixelShader.write(stream)
        self.fBumpEnvXfm.write(stream)

    ###################################
    ##                               ##
    ##      Interface Functions      ##
    ##                               ##
    ###################################

    def ToBlenderMTex(self,mtex,obj):
        print "     [Layer %s]"%(str(self.Key.name))
        mesh = obj.getData(False,True)
        mtex.colfac = self.fOpacity
        if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendInvertColor"]:
           mtex.neg = True

        # not working in blender 2.45, perhaps will do in a later version
        if self.fState.fMiscFlags & hsGMatState.hsGMatMiscFlags["kMiscTwoSided"]:
            mode = obj.data.getMode()
            mode |= Blender.Mesh.Modes.TWOSIDED
            obj.data.setMode()
        else:
            mode = obj.data.getMode()
            mode &= Blender.Mesh.Modes.TWOSIDED
            obj.data.setMode()

##        UVLayers = {}
        mtex.uvlayer = "UVLayer" + str(self.fUVWSrc)
##        UVLayers = mesh.getUVLayerNames()
##        if len(UVLayers) < bufferGroup.GetUVCount():
##            for i in range(len(UVLayers),bufferGroup.GetUVCount()):
##                mesh.addUVLayer("UVLayer" + str(i))


        # Note: Using matrix allows us to scale up the tex and offset it, but it won't allow us to rotate it.
        if -100 <= self.fTransform.matrix[0][0] and self.fTransform.matrix[0][0] <= 100:
            if -100 <= self.fTransform.matrix[1][1] and self.fTransform.matrix[1][1] <= 100:
                mtex.size = (self.fTransform.matrix[0][0], self.fTransform.matrix[1][1], 1.0)

        if -10 <= self.fTransform.matrix[0][3] and self.fTransform.matrix[0][3] <= 10:
            if -10 <= self.fTransform.matrix[1][3] and self.fTransform.matrix[1][3] <= 10:
                mtex.ofs  = (self.fTransform.matrix[0][3], self.fTransform.matrix[1][3], 0.0)

        if abs(self.fTransform.matrix[0][1]) + abs(self.fTransform.matrix[1][0]) > 0.05: # approximated, sometimes values under .05 will be remaining crap.
            print "       WARNING: can't import rotation for this layer"



        if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendAlpha"]:
            mtex.tex.imageFlags = Blender.Texture.ImageFlags["USEALPHA"]

        if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendMult"]:
            mtex.blendmode = Blender.Texture.BlendModes["MULTIPLY"]

        if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendSubtract"]:
            mtex.blendmode = Blender.Texture.BlendModes["SUBTRACT"]

        if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendAdd"]:
            mtex.blendmode = Blender.Texture.BlendModes["LIGHTEN"]

        #if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendNoTexAlpha"]:
        #    mtex.blendmode = Blender.Texture.BlendModes["SCREEN"]

        if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendAddColorTimesAlpha"]:
            mtex.blendmode = Blender.Texture.BlendModes["ADD"]

        ## Sirius: these are quite useless, the properties set do not match the result in Plasma.

        #if self.fState.fMiscFlags & hsGMatState.hsGMatMiscFlags["kMiscBindNext"]:
        #    mtex.mtHard = True


        #if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendAlphaTestHigh"]:
        #    mtex.mtTranslu = True


        #if self.fState.fMiscFlags & hsGMatState.hsGMatMiscFlags["kMiscRestartPassHere"]:
        #    mtex.mtRayMir =  True

        if self.fState.fMiscFlags  & hsGMatState.hsGMatMiscFlags["kMiscLightMap"]:
            mtex.mtAmb = True

        #if self.fState.fBlendFlags & hsGMatState.hsGMatBlendFlags["kBlendAlphaAdd"]:
        #    mtex.mtCsp = True

        #if self.fState.fZFlags & hsGMatState.hsGMatZFlags["kZNoZWrite"]:
        #    mtex.mtCmir = True

        pass


class blMipMapInfo:

    def __init__(self):
        self.fImageName = ""
        self.fMipMaps = True
        self.fResize = True
        self.fCalcAlpha = False
        self.fGauss = False
        self.fAlphaMult = 1.0
        self.fCompressionType = plBitmap.Compression["kDirectXCompression"]
        self.fBitmapInfo = plBitmap.Info()
        self.fBitmapInfo.fDirectXInfo.fCompressionType = plBitmap.CompressionType["kError"]

    def read(self,stream):
        self.fImageName = stream.ReadSafeString(0)
        self.fMipMaps = stream.ReadBool()
        self.fResize = stream.ReadBool()
        self.fCalcAlpha = stream.ReadBool()
        self.fGauss = stream.ReadBool()
        self.fAlphaMult = stream.ReadFloat()
        self.fCompressionType = stream.ReadByte()

        if (self.fCompressionType != plBitmap.Compression["kUncompressed"]  and  self.fCompressionType != plBitmap.Compression["kJPEGCompression"]):
            self.fBitmapInfo.fDirectXInfo.fBlockSize = stream.ReadByte()
            self.fBitmapInfo.fDirectXInfo.fCompressionType = stream.ReadByte()
        else:
            self.fBitmapInfo.fUncompressedInfo.fType = stream.ReadByte()

    def write(self,stream):
        # Set compression types correctly
        if self.fBitmapInfo.fDirectXInfo.fCompressionType == plBitmap.CompressionType["kDXT1"]:
            self.fBitmapInfo.fDirectXInfo.fBlockSize = 8
        elif self.fBitmapInfo.fDirectXInfo.fCompressionType == plBitmap.CompressionType["kDXT5"]:
            self.fBitmapInfo.fDirectXInfo.fBlockSize = 16

        stream.WriteSafeString(self.fImageName,0)
        stream.WriteBool(self.fMipMaps)
        stream.WriteBool(self.fResize)
        stream.WriteBool(self.fCalcAlpha)
        stream.WriteBool(self.fGauss)
        stream.WriteFloat(self.fAlphaMult)
        stream.WriteByte(self.fCompressionType)

        if (self.fCompressionType != plBitmap.Compression["kUncompressed"]  and  self.fCompressionType != plBitmap.Compression["kJPEGCompression"]):
            stream.WriteByte(self.fBitmapInfo.fDirectXInfo.fBlockSize)
            stream.WriteByte(self.fBitmapInfo.fDirectXInfo.fCompressionType)
        else:
            stream.WriteByte(self.fBitmapInfo.fUncompressedInfo.fType)





class plBitmap(hsKeyedObject):               # Type 0x03

    #region Structures
    class DirectXInfo:
        def __init__(self):
            self.fCompressionType = 0 #CompressionType;
            self.fBlockSize = 0 #ubyte  #Formerly texelSize


    class UncompressedInfo:
        def __init__(self):
            self.fType = 0 #Uncompressed

    class Info:
        def __init__(self):
            self.fDirectXInfo = plBitmap.DirectXInfo() #DirectXInfo
            self.fUncompressedInfo = plBitmap.UncompressedInfo() #UncompressedInfo


    #region Constants
    CompressionType = \
    { \
        "kError" : 0, \
        "kDXT1"  : 1, \
        "kDXT2"  : 2, \
        "kDXT3"  : 3, \
        "kDXT4"  : 4, \
        "kDXT5"  : 5  \
    }

    Uncompressed =  \
    { \
        "kRGB8888"    : 0, \
        "kRGB4444"    : 1, \
        "kRGB1555"    : 2, \
        "kInten8"     : 3, \
        "kAInten88"   : 4  \
    }

    Space = \
    {  \
        "kNoSpace"        : 0, \
        "kDirectSpace"    : 1, \
        "kGraySpace"      : 2, \
        "kIndexSpace"     : 3  \
    }

    Flags = \
    {  \
        "kNoFlag"               :    0x0, \
        "kAlphaChannelFlag"     :    0x1, \
        "kAlphaBitFlag"         :    0x2, \
        "kBumpEnvMap"           :    0x4, \
        "kForce32Bit"           :    0x8, \
        "kDontThrowAwayImage"   :   0x10, \
        "kForceOneMipLevel"     :   0x20, \
        "kNoMaxSize"            :   0x40, \
        "kIntensityMap"         :   0x80, \
        "kHalfSize"             :  0x100, \
        "kUserOwnsBitmap"       :  0x200, \
        "kForceRewrite"         :  0x400, \
        "kForceNonCompressed"   :  0x800, \
        "kIsTexture"            : 0x1000, \
        "kIsOffscreen"          : 0x2000, \
        "kMainScreen"           :    0x0, \
        "kIsProjected"          : 0x4000, \
        "kIsOrtho"              : 0x8000  \
    }

    Compression = \
    { \
        "kUncompressed"         : 0, \
        "kDirectXCompression"   : 1, \
        "kJPEGCompression"      : 2  \
    }

    BITMAPVER = 2;


    def __init__(self,parent,name="unnamed",type=0x0003):
        hsKeyedObject.__init__(self,parent,name,type)
        self.BitmapInfo = plBitmap.Info() # Info

        self.fCompressionType = 1 # Compression

        self.fPixelSize = 1 #ubyte
        self.fSpace = 1     #sbyte
        self.fFlags = 0     #Flags

        self.fLowModifiedTime = 0 #uint #Formerly fInputManager
        self.fHighModifiedTime = 0 #uint #Formerly fPageMgr

        # for internal handling (From old implementation)
        self.isCubEvMapPart = 0
        self.BlenderImage=None

        self.FullAlpha = False
        self.OnOffAlpha = False

        self.MipMapInfo = blMipMapInfo()

        self.texCacheExtension = ".bmap"

    def _Find(page,name):
        return page.find(0x0003,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0003,name,1)
    FindCreate = staticmethod(_FindCreate)


    def read(self,stream, really=1,silent=1):
        hsKeyedObject.read(self,stream, really, silent)

        stream.ReadByte() #Discarded: Version
        self.fPixelSize = stream.ReadByte()
        self.fSpace = stream.ReadByte()
        self.fFlags = stream.Read16()
        self.fCompressionType = stream.ReadByte()


        if (self.fCompressionType != plBitmap.Compression["kUncompressed"]  and  self.fCompressionType != plBitmap.Compression["kJPEGCompression"]):
            self.BitmapInfo.fDirectXInfo.fBlockSize = stream.ReadByte()
            self.BitmapInfo.fDirectXInfo.fCompressionType = stream.ReadByte()
        else:
            self.BitmapInfo.fUncompressedInfo.fType = stream.ReadByte()

        self.fLowModifiedTime = stream.Read32()
        self.fHighModifiedTime = stream.Read32()

    def write(self, stream, really=1):
        hsKeyedObject.write(self,stream,really)

        stream.WriteByte(0x02)    # always version 0x02
        stream.WriteByte(self.fPixelSize)
        stream.WriteByte(self.fSpace)
        stream.Write16(self.fFlags)
        stream.WriteByte(self.fCompressionType)

        if (self.fCompressionType != plBitmap.Compression["kUncompressed"]  and  self.fCompressionType != plBitmap.Compression["kJPEGCompression"]):
            stream.WriteByte(self.BitmapInfo.fDirectXInfo.fBlockSize)
            stream.WriteByte(self.BitmapInfo.fDirectXInfo.fCompressionType)
        else:
            stream.WriteByte(self.BitmapInfo.fUncompressedInfo.fType)

        stream.Write32(self.fLowModifiedTime)
        stream.Write32(self.fHighModifiedTime)



class plMipMap(plBitmap):                    # Type 0x04

    Color = \
    { \
        "kColor8Config" :  0x0, \
        "kGray44Config" :  0x1, \
        "kGray4Config"  :  0x2, \
        "kGray8Config"  :  0x8, \
        "kRGB16Config"  : 0x10, \
        "kRGB32Config"  : 0x18, \
        "kARGB32Config" : 0x20  \
    }

    CreateDetail = \
    { \
        "kCreateDetailAlpha" :  0x1, \
        "kCreateDetailAdd"   :  0x2, \
        "kCreateDetailMult"  :  0x4, \
        "kCreateDetailMask"  :  0x7, \
        "kCreateCarryAlpha"  : 0x10, \
        "kCreateCarryBlack"  : 0x20, \
        "kCreateCarryMask"   : 0x38  \
    }

    hsGPixelType = \
    { \
        "kPixelARGB4444" : 0, \
        "kPixelARGB1555" : 1, \
        "kPixelAI88"     : 2, \
        "kPixelI8"       : 3  \
    }

    hsGCopyOptions = \
    { \
        "kCopyLODMask" : 0 \
    }

    Data = \
    { \
        "kColorDataRLE" : 0x1, \
        "kAlphaDataRLE" : 0x2  \
    }

    CompositeFlags = \
    { \
        "kForceOpaque"      :  0x1, \
        "kCopySrcAlpha"     :  0x2, \
        "kBlendSrcAlpha"    :  0x4, \
        "kMaskSrcAlpha"     :  0x8, \
        "kBlendWriteAlpha"  : 0x10  \
    }

    ScaleFilter = \
    { \
        "kBoxFilter"     : 0, \
        "kDefaultFilter" : 0  \
    }


    def __init__(self,parent,name="unnamed",type=0x0004):
        plBitmap.__init__(self,parent,name,type)

        self.fImages = []
        self.fWidth = 0
        self.fHeight = 0
        self.fRowBytes = 0

        self.fTotalSize = 0
        self.fNumLevels = 0
        self.fLevelSizes = []

        # setting of fields from plBitmap
        self.fPixelSize = 32

        # fields used for internal processing

        self.Processed = 0

        self.Cached_BlenderImage = None
        self.texCacheExtension = ".tex"

    def _Find(page,name):
        return page.find(0x0004,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0004,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self, stream, really=1,silent=0):
        plBitmap.read(self,stream,really)

        nread = 0;
        self.fWidth = stream.Read32()
        self.fHeight = stream.Read32()
        self.fRowBytes = stream.Read32()
        self.fTotalSize = stream.Read32()
        self.fNumLevels = stream.ReadByte()


        if self.fTotalSize == 0:
            return

        self.fImages = []

        if self.fCompressionType == plBitmap.Compression["kJPEGCompression"]:
            data=tJpgImage(self.fWidth,self.fHeight)
            data.read(stream)
            self.fImages.append(data)

        elif self.fCompressionType == plBitmap.Compression["kDirectXCompression"]:
            if (self.fNumLevels > 0):
                for i in range(self.fNumLevels):
                    data=tDxtImage(self.fWidth>>i,self.fHeight>>i, self.BitmapInfo.fDirectXInfo.fCompressionType)
                    data.read(stream)
                    self.fImages.append(data)

        elif self.fCompressionType == plBitmap.Compression["kUncompressed"]:
            if (self.fNumLevels > 0):
                for i in range(self.fNumLevels):
                    data=tImage(self.fWidth>>i,self.fHeight>>i)
                    data.read(stream)
                    self.fImages.append(data)
        else:
            return

        return

    def write(self,stream, really=1,silent=0):
        plBitmap.write(self,stream,really)

        self.fRowBytes = int(self.fWidth * (self.fPixelSize / 8.0))

        padding_needed = (4 - (self.fRowBytes % 4) ) # fRowBytes needs to be padded to a multiple of 4

        if (padding_needed > 0 and padding_needed < 4):
            self.fRowbytes = self.fRowBytes + padding_needed

        stream.Write32(self.fWidth)
        stream.Write32(self.fHeight)
        stream.Write32(self.fRowBytes)

        offset_fTotalSize = stream.tell() # store offset of this field
        stream.Write32(self.fTotalSize) # write dummy fTotalSize

        self.fNumLevels=len(self.fImages)
        stream.WriteByte(self.fNumLevels)

        offset_ImageDataStart=stream.tell() # save begin position of image data
        for img in self.fImages: # write all the images
            img.write(stream)
        offset_ImageDataEnd=stream.tell() # save end position of image data


        self.fTotalSize = offset_ImageDataEnd - offset_ImageDataStart # calculate actual size
        stream.seek(offset_fTotalSize) # reposition stream to fTotalSize field
        stream.Write32(self.fTotalSize) # write actual fTotalSize
        stream.seek(offset_ImageDataEnd) # reposition stream to end of object


    def SetConfig(self,Config):
        if Config == plMipMap.Color["kColor8Config"]:
            self.fPixelSize = 8
            self.fSpace = 3
            self.fFlags = plBitmap.Flags["kNoFlag"]

        elif Config == plMipMap.Color["kGray44Config"]:
            self.fPixelSize = 8
            self.fSpace = 2
            self.fFlags = plBitmap.Flags["kAlphaChannelFlag"]

        elif Config == plMipMap.Color["kGray4Config"]:
            self.fPixelSize = 4
            self.fSpace = 2
            self.fFlags = plBitmap.Flags["kNoFlag"]

        elif Config == plMipMap.Color["kGray8Config"]:
            self.fPixelSize = 8
            self.fSpace = 1
            self.fFlags = plBitmap.Flags["kNoFlag"]

        elif Config == plMipMap.Color["kRGB16Config"]:
            self.fPixelSize = 16
            self.fSpace = 1
            self.fFlags = plBitmap.Flags["kAlphaBitFlag"]

        elif Config == plMipMap.Color["kRGB32Config"]:
            self.fPixelSize = 32
            self.fSpace = 1
            self.fFlags = plBitmap.Flags["kNoFlag"]

        elif Config == plMipMap.Color["kARGB32Config"]:
            self.fPixelSize = 32
            self.fSpace = 1
            self.fFlags = plBitmap.Flags["kAlphaChannelFlag"]

    ###################################
    ##                               ##
    ##      Interface Functions      ##
    ##                               ##
    ###################################

    def ToBlenderImage(self):
        # retrieve the image from cache if it's there
        if self.Cached_BlenderImage!=None:
            return self.Cached_BlenderImage

        print "     [MipMap %s]"%str(self.Key.name)

        # Build up a temprary file path and name
        resmanager=self.getResManager()
        BasePath=resmanager.getBasePath()
        TexPath = BasePath + "/TMP_Textures/"

        ## Sirius' MODIF - Convert to TGA
        # Since I don't want to find or write a converter for these, it's
        # a lot easier to import them as TGA.
        # Note: this requires a new script for PIL
        # image type can be set in AlcConfig.py
        Name=stripIllegalChars(str(self.Key.name)) + alcconfig.import_texture_type
        TexFileName = TexPath + "/" + Name

        # create the temporary Texture Path
        try:
            os.mkdir(TexPath)
        except OSError:
            pass

        # get the first image in the list (return None if it isn't there)
        if len(self.fImages)==0:
            return None

        myimg = self.fImages[0]

        # save it to the temporary folder
        myimg.save(TexFileName)

        # and load it again as a blender image
        BlenderImg=Blender.Image.Load(TexFileName)
        #################### DISABLED PACKING ###################
        #BlenderImg.pack() # disabled to not pack texture in blender file (smaller output)


        # cache it for easy fetching
        self.Cached_BlenderImage=BlenderImg

        return BlenderImg

    def ToBlenderTex(self,name=None):
        print "     [MipMap %s]"%str(self.Key.name)

        if name == None:
            name = str(self.Key.name)

        # Form the Blender cubic env map MTex
        Tex=Blender.Texture.New(name)
        Tex.setImage(self.ToBlenderImage())
        Tex.type  = Blender.Texture.Types["IMAGE"]


        return Tex




class plCubicEnvironMap(plBitmap):          # Type 0x05

    Faces = {
        "kLeftFace"     : 0,
        "kRightFace"    : 1,
        "kFrontFace"    : 2,
        "kBackFace"     : 3,
        "kTopFace"      : 4,
        "kBottomFace"   : 5
    }

    def __init__(self,parent,name="unnamed",type=0x0005):
        plBitmap.__init__(self,parent,name,type)
        self.fFaces = []

        self.Processed = 0

        self.Cached_BlenderCubicMap = None
        self.texCacheExtension = ".qmap"

    def _Find(page,name):
        return page.find(0x0005,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0005,name,1)
    FindCreate = staticmethod(_FindCreate)


    def read(self, stream):
        plBitmap.read(self,stream);

        self.fFaces = []
        for i in range(6):
            mipmap = plMipMap(self.parent)
            mipmap.read(stream,0) # "Really" is set to 0, to avoid reading hsKeyedObject code
            self.fFaces.append(mipmap)

    def write(self, stream):
        plBitmap.write(self,stream);

        for i in range(6):
            self.fFaces[i].write(stream,0) # "Really" is set to 0, to avoid writing hsKeyedObject code

    ###################################
    ##                               ##
    ##      Interface Functions      ##
    ##                               ##
    ###################################

    def ToBlenderCubicMap(self):
        # retrieve the image from cache if it's there
        if self.Cached_BlenderCubicMap==None:
            print "     [CubicEnvMap %s]"%str(self.Key.name)

            # Build up a temprary file path and name
            resmanager=self.getResManager()
            BasePath=resmanager.getBasePath()
            TexPath = BasePath + "/TMP_Textures/"

            Name=stripIllegalChars(str(self.Key.name)) + alcconfig.import_texture_type
            TexFileName = TexPath + "/" + Name
            TexFileName = TexFileName.replace("*","_") # strip out unwanted characters


            # Convert images to Blender images for easy processing
            RawImages = []
            for i in (0,3,1,5,4,2):
                rawimg = self.fFaces[i].ToBlenderImage()
                RawImages.append(rawimg)

            # Stitch together 6 images
            xpart,ypart, = RawImages[0].getSize()
            print "      Size of maps: %i x %i" % (xpart,ypart)

            width = xpart*3
            height = ypart*2

            CookedImage = Image.new("RGBA",(width,height))

            try:

                ImageBuffer=cStringIO.StringIO()
                # Copy bottom three images
                for y in range(ypart-1,-1,-1):
                    for i in range(0,3):
                        for x in range(0,xpart):
                            try:
                                r,g,b,a = RawImages[i].getPixelF(x,y)
                                ImageBuffer.write(struct.pack("BBBB",r*255,g*255,b*255,a*255))
                            except Exception, detail:
                                print "      Now in image # %i"% i
                                print "      Size of image:",RawImages[i].getSize()
                                print "      Value of X and Y: %i, %i" % (x,y)
                                raise Exception, detail

                # Copy top three images
                for y in range(ypart-1,-1,-1):
                    for i in range(3,6):
                        for x in range(0,xpart):
                            try:
                                r,g,b,a = RawImages[i].getPixelF(x,y)
                                ImageBuffer.write(struct.pack("BBBB",r*255,g*255,b*255,a*255))
                            except Exception, detail:
                                print "      Now in image # %i"% i
                                print "      Size of image:",RawImages[i].getSize()
                                print "      Value of X and Y: %i, %i" % (x,y)
                                raise Exception, detail

                # Transfer buffer to image
                ImageBuffer.seek(0)

                CookedImage.fromstring(ImageBuffer.read())

            except Exception, detail:
                print "      Exception:",detail
                print "      Continuing"

            # And save the image...
            CookedImage.save(TexFileName)

            # Load it back in to process in blender
            self.Cached_BlenderCubicMap = Blender.Image.Load(TexFileName)

        return self.Cached_BlenderCubicMap

    def ToBlenderTex(self,name=None):

        if name == None:
            name = str(self.Key.name)

        # Form the Blender cubic env map MTex
        Tex=Blender.Texture.New(name)
        Tex.setImage(self.ToBlenderCubicMap())
        Tex.type  = Blender.Texture.Types["ENVMAP"]
        Tex.stype = Blender.Texture.STypes["ENV_LOAD"]

        return Tex



class plDynamicTextMap(plMipMap):
    def __init__(self,parent=None,name="unnamed",type=0x00AD):
        plMipMap.__init__(self,parent,name,type)
        self.fVisWidth = 512;
        self.fVisHeight = 512;
        self.fHasAlpha = False;

    def _Find(page,name):
        return page.find(0x00AD,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00AD,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self, stream, really=1):
        plBitmap.read(self,stream,really)

        self.fVisWidth = stream.Read32()
        self.fVisHeight = stream.Read32()
        self.fHasAlpha = stream.ReadBool()



    def write(self,stream,really=1):
        plBitmap.write(self,stream,really)

        stream.Write32(self.fVisWidth)
        stream.Write32(self.fVisHeight)
        stream.WriteBool(self.fHasAlpha)

        stream.Write32(0) #DO NOT HANDLE THE INSANITY!



    def ToBlenderTex(self,name=None):
        print "     [MipMap %s]"%str(self.Key.name)

        if name == None:
            name = str(self.Key.name)

        # Form the Blender MTex
        Tex=Blender.Texture.New(name)
        Tex.type  = Blender.Texture.Types["NOISE"]


        return Tex

class plLayerAnimationBase(plLayerInterface):
    def __init__(self,parent,name="unnamed",type=0x00EF):
        plLayerInterface.__init__(self,parent,name,type)

        self.fEvalTime = -1.0
        self.fCurrentTime = -1.0
        self.fSegmentID = None
        self.fPreshadeColorCtl = None
        self.fRuntimeColorCtl = None
        self.fAmbientColorCtl = None
        self.fSpecularColorCtl = None
        self.fOpacityCtl = None
        self.fTransformCtl = None

    def _Find(page,name):
        return page.find(0x00EF,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00EF,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self, stream, size):
        plLayerInterface.read(self,stream)
        self.fPreshadeColorCtl = alc_AnimClasses.PrpController(stream.Read16(), self.getVersion())
        self.fPreshadeColorCtl.read(stream)
        self.fRuntimeColorCtl = alc_AnimClasses.PrpController(stream.Read16(), self.getVersion())
        self.fRuntimeColorCtl.read(stream)
        self.fAmbientColorCtl = alc_AnimClasses.PrpController(stream.Read16(), self.getVersion())
        self.fAmbientColorCtl.read(stream)
        self.fSpecularColorCtl = alc_AnimClasses.PrpController(stream.Read16(), self.getVersion())
        self.fSpecularColorCtl.read(stream)
        self.fOpacityCtl = alc_AnimClasses.PrpController(stream.Read16(), self.getVersion())
        self.fOpacityCtl.read(stream)
        self.fTransformCtl = alc_AnimClasses.PrpController(stream.Read16(), self.getVersion())
        self.fTransformCtl.read(stream)

    def write(self, stream):
        plLayerInterface.write(self,stream)
        self.fPreshadeColorCtl.write(stream)
        self.fRuntimeColorCtl.write(stream)
        self.fAmbientColorCtl.write(stream)
        self.fSpecularColorCtl.write(stream)
        self.fOpacityCtl.write(stream)
        self.fTransformCtl.write(stream)

class plLayerAnimation(plLayerAnimationBase):
    def __init__(self,parent=None,name="unnamed",type=0x0043):
        plLayerAnimationBase.__init__(self,parent,name,type)
        self.fTimeConvert = None

    def _Find(page,name):
        return page.find(0x0043,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0043,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self, stream, size):
        start = stream.tell() # Keep start offset in case of trouble...
        try:
            plLayerAnimationBase.read(self, stream, size)
            if self.fTimeConvert == None:
                self.fTimeConvert = alc_AnimClasses.plAnimTimeConvert()
            self.fTimeConvert.read(stream)
        except:
            print "/---------------------------------------------------------"
            print "|  WARNING:"
            print "|   Could not read in portion of plLayerAnimation."
            print "|   -> Skipping %i bytes ahead " % ( (start + size) - stream.tell())
            print "|   -> Total object size: %i bytes"% (size)
            print "\---------------------------------------------------------\n"
            stream.seek(start + size) #skip to the end

    def write(self, stream):
        plLayerAnimationBase.write(self, stream)
        self.fTimeConvert.write(stream)

    def FromBlender(self,obj,mat,mtex,chan = 0):
        print "   [LayerAnimation %s]"%(str(self.Key.name))
        # We have to grab the animation stuff here...
        ipo = mat.ipo
        ipo.channel = chan
        endFrame = 0

        if (Ipo.MA_OFSX in ipo) and (Ipo.MA_OFSY in ipo) and (Ipo.MA_OFSZ in ipo):
            KeyList = []

            # We need to get the list of BezCurves
            # Then get the value for each and create a matrix
            # Then store that in a frame and store than in the list
            curves = ipo[Ipo.MA_OFSX].bezierPoints
            for frm in range(len(curves)):
                frame = alc_AnimClasses.hsMatrix44Key()
                num = curves[frm].pt[0]
                if num == 1:
                    num = 0
                frame.fFrameNum = int(num)
                frame.fFrameTime = num/30.0

                matx = hsMatrix44()
                matx.translate((curves[frm].pt[1], ipo[Ipo.MA_OFSY].bezierPoints[frm].pt[1], ipo[Ipo.MA_OFSZ].bezierPoints[frm].pt[1]))

                frame.fValue = matx
                KeyList.append(frame)

            self.fTransformCtl = alc_AnimClasses.PrpController(0x0234, self.getVersion())
            self.fTransformCtl.data.fKeys = KeyList
            endFrame = curves[-1].pt[0]
        else:
            self.fTransformCtl = alc_AnimClasses.PrpController(0x8000, self.getVersion())

        ##MAJOR HACK HERE
        self.fPreshadeColorCtl = alc_AnimClasses.PrpController(0x8000, self.getVersion())
        self.fRuntimeColorCtl = alc_AnimClasses.PrpController(0x8000, self.getVersion())
        self.fAmbientColorCtl = alc_AnimClasses.PrpController(0x8000, self.getVersion())
        self.fSpecularColorCtl = alc_AnimClasses.PrpController(0x8000, self.getVersion())
        self.fOpacityCtl = alc_AnimClasses.PrpController(0x8000, self.getVersion())

        self.fTimeConvert = alc_AnimClasses.plAnimTimeConvert()
        self.fTimeConvert.fFlags |= 0x22
        self.fTimeConvert.fBegin = 0.0
        self.fTimeConvert.fEnd = endFrame/30.0
        self.fTimeConvert.fLoopEnd = endFrame/30.0
        self.fTimeConvert.fLoopBegin = 0.0

    def ToBlenderMTex(self,mtex,obj):
        print "     [Layer %s]"%(str(self.Key.name))
        # TODO: Implement this to set mtex.colfac, mtex.neg and obj.data.mode
        print "        WARNING: Layer animation settings have not been"
        print "        converted into Blender texture settings!"

class plLayerMovie(plLayerAnimation):     # Type 0x41 (uru)
    def __init__(self,parent,name="unnamed",type=None):
        plLayerAnimation.__init__(self,parent,name,type)


    def read(self,stream):
        plLayerAnimation.read(self,stream)


    def write(self,stream):
        plLayerAnimation.write(self,stream)

class plLayerBink(plLayerMovie):
    def __init__(self,parent,name="unnamed",type=0x0046):
        plLayerMovie.__init__(self,parent,name,type)
        self.fMovieName = ""

    def read(self,stream):
        plLayerMovie.read(self,stream)


    def write(self,stream):
        plLayerMovie.write(self,stream)
        stream.Write32(len(str(self.fMovieName)))
        stream.write(str(self.fMovieName))

    def _Find(page,name):
        return page.find(0x0046,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0046,name,1)
    FindCreate = staticmethod(_FindCreate)


    def ToBlenderMTex(self,mtex,obj):
        print "     [Layer %s]"%(str(self.Key.name))
        # TODO: Implement this to set mtex.colfac, mtex.neg and obj.data.mode
        print "        WARNING: Layer Bink settings have not been"
        print "        converted into Blender texture settings!"


