#
# $Id: alcdraw.py 477 2006-04-30 15:48:27Z AdamJohnso $
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
        from Blender import Mesh, Mathutils
    except Exception, detail:
        print detail
except ImportError:
    pass

import array, random, binascii
from alc_AbsClasses import *
import alcconfig

class VertexCoderElement:
    def __init__(self,base=0,count=0):
        self.base = base #FLOAT
        self.count = count #WORD

    def read(self,buf,granularity):
        if (self.count == 0):
            self.base = buf.ReadFloat()
            self.count = buf.Read16()
        if (self.count != 0):
            self.count = self.count - 1
            return (self.base + granularity * buf.Read16())
        raise RuntimeError, "VertexCoderElement prematurely reached end of count"

class VertexCoderColorElement:
    def __init__(self,base=0,count=0):
        self.base = base
        self.count = count
        self.RLE = None #Bool


    def read(self,buf):
        if (self.count == 0):
            self.count = buf.Read16()
            if ((self.count & 0x8000) != 0):
                self.RLE = 1
                self.base = buf.ReadByte()
                self.count &= 0x7FFF
            else:
                self.RLE = 0
        if (self.count != 0):
            self.count = (self.count - 1)
            if self.RLE:
                return self.base
            else:
                return buf.ReadByte()
        else:
           raise RuntimeError, "VertexCoderColorElement prematurely reached end of count."
4

class plVertexCoder:
    # Still uses struct.pack and struct.unpack, but that is no problem

    def __init__(self):
        #State vars
        self.Elements=[]
        for i in range(30):
            self.Elements.append(VertexCoderElement())
        self.Colors=[]
        for i in range(4):
            self.Colors.append(VertexCoderColorElement())

    def read(self,bufferGroup,buf,count):
        #read encoded vertex info
        for i in range(count):
            #Vertex Coordinates
            vert=Vertex()
            vert.x=self.Elements[0].read(buf,1.0/1024.0)
            vert.y=self.Elements[1].read(buf,1.0/1024.0)
            vert.z=self.Elements[2].read(buf,1.0/1024.0)
            #Vertex weights
            for e in range(bufferGroup.GetNumSkinWeights()):
                vert.blend.append(self.Elements[3+e].read(buf,1.0/32768.0))
            if bufferGroup.GetNumSkinWeights() and bufferGroup.GetSkinIndices():
                b1,b2,b3,b4,=struct.unpack("BBBB",buf.read(4)) #4 bones
                vert.bones=[b1,b2,b3,b4] #absolute bone index
            #normals
            vert.nx = (buf.Read16() / 32767.0)
            vert.ny = (buf.Read16() / 32767.0)
            vert.nz = (buf.Read16() / 32767.0)
            #colors
            vert.color.b = self.Colors[0].read(buf)
            vert.color.g = self.Colors[1].read(buf)
            vert.color.r = self.Colors[2].read(buf)
            vert.color.a = self.Colors[3].read(buf)
            #texture coordinates
            for j in range(bufferGroup.GetUVCount()):
                tex=[]
                tex.append(self.Elements[6+(3*j)].read(buf,1.0/65536.0))
                tex.append(self.Elements[7+(3*j)].read(buf,1.0/65536.0))
                tex.append(self.Elements[8+(3*j)].read(buf,1.0/65536.0))
                vert.tex.append(tex)
            bufferGroup.fVertBuffStorage.append(vert)


    def write(self,bufferGroup,buf,count):
        #State vars
        VarA=[] #vertex coords (3)
        Vector=[] #real vector
        VBase=[] #vertex coords base
        offset=[] #offsets
        xVector=[]
        VarB=[] #vertex weights (nblends)
        BBase=[] #weight base
        VarC=[] #vertex colors RGBA (4)
        color=[] #the last color
        VarD=[] #vertex tex coords (3 * ntex)
        TBase=[] #tex coords base
        for i in range(3):
            VarA.append(0)
            Vector.append(0)
            xVector.append(0)
            VBase.append(0)
            offset.append(0)
        for i in range(bufferGroup.GetNumSkinWeights()):
            VarB.append(0)
            BBase.append(0)
        for i in range(4):
            VarC.append(0)
            color.append(0)
        for i in range(3*bufferGroup.GetUVCount()):
            VarD.append(0)
            TBase.append(0)
        compress=alcconfig.vertex_compression
        n = count
        #write encoded vertex info
        for i in range(count):
            vert=bufferGroup.fVertBuffStorage[i]
            #Vertex Coordinates
            Vector[0]=vert.x
            Vector[1]=vert.y
            Vector[2]=vert.z
            if not compress:
                #uncompressed
                for e in range(3):
                   buf.write(struct.pack("fHH",Vector[e],1,0)) #vertex base, n_vertexs, offset
            else:
                #compressed
                for e in range(3):
                    if VarA[e]==0:
                        #first vertex with new base
                        VBase[e]=Vector[e]
                        #count vertex with same base
                        for vi in range(n-i):
                            xxvert = bufferGroup.fVertBuffStorage[vi+i]
                            xVector[0]=xxvert.x
                            xVector[1]=xxvert.y
                            xVector[2]=xxvert.z
                            off = (xVector[e]-VBase[e]) * 1024.0
                            #32768
                            if off<65536 and off>=0:
                                VarA[e]=VarA[e]+1
                            else:
                                break
                        buf.write(struct.pack("fH",VBase[e],VarA[e]))
                    off = (Vector[e]-VBase[e]) * 1024.0
                    buf.write(struct.pack("H",off))
                    VarA[e]=VarA[e]-1

            #Vertex weights
            if not compress:
                for e in range(bufferGroup.GetNumSkinWeights()):
                    buf.write(struct.pack("fHH",vert.blend[e],1,0)) #blend base, n, offset
            else:
                for e in range(bufferGroup.GetNumSkinWeights()):
                    if VarB[e]==0:
                        #first
                        BBase[e]=vert.blend[e]
                        #count
                        for vi in range(n-i):
                            xxvert = bufferGroup.fVertBuffStorage[vi+i]
                            off = (xxvert.blend[e] - BBase[e]) * 32768.0
                            if off<65536 and off>=0:
                                VarB[e]=VarB[e]+1
                            else:
                                break
                        buf.write(struct.pack("fH",BBase[e],VarB[e]))
                    off = (vert.blend[e] - BBase[e]) * 32768.0
                    buf.write(struct.pack("H",off))
                    VarB[e]=VarB[e]-1
            if bufferGroup.GetNumSkinWeights() and bufferGroup.GetSkinIndices():
                buf.write(struct.pack("BBBB",vert.bones[0],vert.bones[1],vert.bones[2],vert.bones[3]))
            #normals
            nx = int(vert.nx * 32768.0)
            ny = int(vert.ny * 32768.0)
            nz = int(vert.nz * 32768.0)
            if nx > 32767:
                nx = 32767
            elif nx < -32767:
                nx = -32767
            if ny > 32767:
                ny = 32767
            elif ny < -32767:
                ny = -32767
            if nz > 32767:
                nz = 32767
            elif nz < -32767:
                nz = -32767
            try:
                buf.write(struct.pack("hhh",nx,ny,nz))
            except:
                raise "wtf %i %i %i, %i %i %i" %(vert.nx,vert.ny,vert.nz,nx,ny,nz)
            #colors
            #vcolor=vert.color.uget()
            vcolor=[vert.color.b,vert.color.g,vert.color.r,vert.color.a]
            if not compress:
                for e in range(4):
                    buf.write(struct.pack("H",1))
                    buf.write(struct.pack("B",vcolor[e]))
            else:
                for e in range(4):
                    if VarC[e]==0:
                        #first
                        color[e]=vcolor[e]
                        #count
                        for vi in range(n-i):
                            vicolor=[bufferGroup.fVertBuffStorage[vi+i].color.b,bufferGroup.fVertBuffStorage[vi+i].color.g,bufferGroup.fVertBuffStorage[vi+i].color.r,bufferGroup.fVertBuffStorage[vi+i].color.a]
                            if vicolor[e]==color[e]:
                                VarC[e]=VarC[e]+1
                            else:
                                break
                        if VarC[e]==1:
                            cf=0
                        else:
                            cf=0x8000
                        buf.write(struct.pack("HB",VarC[e] | cf,color[e]))
                    VarC[e]=VarC[e]-1
            #texture coordinates
            if not compress:
                for j in range(bufferGroup.GetUVCount()):
                    for k in range(3):
                        buf.write(struct.pack("fHH",vert.tex[j][k],1,0)) #base, n, offset
                        #buf.write(struct.pack("fHH",0,1,0))
            else:
                for j in range(bufferGroup.GetUVCount()):
                    for k in range(3):
                        e=(3*j)+k
                        if VarD[e]==0:
                            #first
                            TBase[e]=vert.tex[j][k]
                            #count
                            for vi in range(n-i):
                                xbase=bufferGroup.fVertBuffStorage[vi+i].tex[j][k]
                                off = (xbase - TBase[e]) * 65536.0
                                if off<65536 and off>=0:
                                    VarD[e]=VarD[e]+1
                                else:
                                    break
                            buf.write(struct.pack("fH",TBase[e],VarD[e]))
                        #print vert.tex[j][k],TBase[e]
                        off=(vert.tex[j][k]-TBase[e]) * 65536.0
                        #assert((TBase[e]+(off/65536.0))==vert.tex[j][k])
                        #print i,j,k,e,off
                        buf.write(struct.pack("H",off))
                        VarD[e]=VarD[e]-1


class plGBufferCell:
    def __init__(self):
        self.VertexIndex = 0 #DWORD
        self.ColorIndex = -1 #DWORD
        self.NumVerts = 0 #DWORD


    def read(self,buf):
        self.VertexIndex = buf.Read32()
        assert(self.VertexIndex == 0)
        self.ColorIndex = buf.ReadSigned32()
        assert(self.ColorIndex == -1)
        self.NumVerts = buf.Read32()


    def write(self,buf):
        buf.Write32(self.VertexIndex)
        buf.WriteSigned32(self.ColorIndex)
        buf.Write32(self.NumVerts)


class plGBufferColor:
    def __init__(self):
        self.DRed = 0
        self.DGreen = 0
        self.DBlue = 0
        self.DAlpha = 0
        self.SRed = 0
        self.SGreen = 0
        self.SBlue = 0
        self.SAlpha = 0


    def read(self,buf):
        self.DRed = buf.ReadByte()
        self.DGreen = buf.ReadByte()
        self.DBlue = buf.ReadByte()
        self.DAlpha = buf.ReadByte()
        self.SRed = buf.ReadByte()
        self.SGreen = buf.ReadByte()
        self.SBlue = buf.ReadByte()
        self.SAlpha = buf.ReadByte()


    def write(self,buf):
        buf.WriteByte(self.DRed)
        buf.WriteByte(self.DGreen)
        buf.WriteByte(self.DBlue)
        buf.WriteByte(self.DAlpha)
        buf.WriteByte(self.SRed)
        buf.WriteByte(self.SGreen)
        buf.WriteByte(self.SBlue)
        buf.WriteByte(self.SAlpha)


class plGBufferGroup:
    Formats = \
    { \
        "kUVCountMask"          :  0xF, \
        "kSkinNoWeights"        :  0x0, \
        "kSkin1Weight"          : 0x10, \
        "kSkin2Weights"         : 0x20, \
        "kSkin3Weights"         : 0x30, \
        "kSkinWeightMask"       : 0x30, \
        "kSkinIndices"          : 0x40, \
        "kEncoded"              : 0x80  \
    }

    Reserve = \
    { \
        "kReserveInterleaved"   :  0x1, \
        "kReserveVerts"         :  0x2, \
        "kReserveColors"        :  0x4, \
        "kReserveSeparated"     :  0x8, \
        "kReserveIsolate"       : 0x10  \
    }

    def __init__(self):
        self.VertStrideLength = 0 #Byte
        #...
        self.fVertBuffStorage = hsTArray()#<Vertex>
        self.fIdxBuffStorage = hsTArray()#<Int16>
        self.fVertBuffSizes = hsTArray()
        #...
        self.fFormat = 0 #Byte
        self.fStride = 0 #?
        self.fCells = hsTArray()#<hsTArray<plGBufferCell>>
        # Added Slice attributes
        #self.fSkinIndices=0       # Was self .blend # PyPRP unique - (int)(fFormat & kSkinIndices > 0)
        #self.fNumSkinWeights=0  # Was self .NumBlendWeights
        #self.fUVCount=0 # Was self .ntex

    def GetSkinIndices(self):
        return (self.fFormat & plGBufferGroup.Formats["kSkinIndices"] > 0)

    def SetSkinIndices(self,value):
        if value == True:
            self.fFormat = self.fFormat | plGBufferGroup.Formats["kSkinIndices"]
        else:
            self.fFormat = self.fFormat & ~plGBufferGroup.Formats["kSkinIndices"]

    def GetUVCount(self):
        return self.fFormat & plGBufferGroup.Formats["kUVCountMask"]

    def SetUVCount(self,value):
        # force to maximum of 8, to avoid trouble
        if(value > 8):
            value = 8

        # clear mask
        self.fFormat = self.fFormat & ~plGBufferGroup.Formats["kUVCountMask"]
        # set new value
        self.fFormat = self.fFormat | (value & plGBufferGroup.Formats["kUVCountMask"])

    def GetNumSkinWeights(self):
        return (self.fFormat & plGBufferGroup.Formats["kSkinWeightMask"]) >> 4

    def SetNumSkinWeights(self,value):
        # force to maximum of 3
        if(value > 3):
            value = 3

        # clean out the old value
        self.fFormat = self.fFormat & ~plGBufferGroup.Formats["kSkinWeightMask"]
        # and set the value
        self.fFormat = self.fFormat | (( value << 4 ) & plGBufferGroup.Formats["kSkinWeightMask"])


    def ICalcVertexSize(self):
        lStride = ((self.fFormat & plGBufferGroup.Formats["kUVCountMask"]) + 2) * 12;

        SkinWeightField = self.fFormat & plGBufferGroup.Formats["kSkinWeightMask"]
        if   SkinWeightField == plGBufferGroup.Formats["kSkinNoWeights"]:
            fNumSkinWeights = 0

        elif SkinWeightField == plGBufferGroup.Formats["kSkin1Weight"]:
            fNumSkinWeights = 1

        elif SkinWeightField == plGBufferGroup.Formats["kSkin2Weights"]:
            fNumSkinWeights = 2

        elif SkinWeightField == plGBufferGroup.Formats["kSkin3Weights"]:
            fNumSkinWeights = 3

        else:
            fNumSkinWeights = 0

        if fNumSkinWeights != 0:
            lStride = lStride + fNumSkinWeights * 4
            if self.fFormat & plGBufferGroup.Formats["kSkinIndices"] > 0:
                lStride = lStride + 4

        return lStride + 8;


    def read(self,buf):
        self.fFormat = buf.ReadByte()                # was self-PackedVertexFormat
        self.fStride = self.ICalcVertexSize()  # was self-VertAndColorStrideLength
        # This is written out in write(), but when read in, it
        # doesn't seem to be used anywhere
        buf.Read32()

        coder = plVertexCoder() # initialize new Vertex Coder
        VertexStorageCount = buf.Read32()
        #assert(VertexStorageCount == 1)
        for j in range(VertexStorageCount):
            if(self.fFormat & plGBufferGroup.Formats["kEncoded"]):
                count = buf.Read16()
#                print "reading geometry (%i vertexs (%i,%i,%i)) - this will take several minutes..." %(count,self.fSkinIndices,self.fNumSkinWeights,self.fUVCount)
                coder.read(self,buf,count)
            elif 1:
                # Support for uncompressed data below is untested, and
                # Isn't neccessary, since plasma doesn't do uncompressed
                # vertices :)

                # set "elif 1:" to "elif 0:" to test the code below should it become
                # neccessary
                raise RuntimeError, "Encountered non-compressed vertex data - not supported"
            else:
                # This should work in theory....
                vtxSize = buf.Read32()
                self.fVertBuffSizes.append(vtxSize) # was self-VertexStorageLengths
                self.fVertBuffStarts.append(0)
                self.fVertBuffEnds.append(-1)

                vData = [vtxSize]
                for i in range(vtxSize):
                    vData[i] = buf.ReadByte()

                self.fVertBuffStorage.append(vData) # was self-VertexStorage

                colorCount = buf.Read32()
                self.fColorBuffCounts.append(colorCount) # was self-ColorStorageLengths
                if colorCount:
                    colors = hsTArray() # new array
                    for i in range(colorCount):
                        colors.append(plGBufferColor())
                    self.fColorBuffStorage.append(colors)

        count = buf.Read32()
        for j in range(count):
            idxCount = buf.Read32()
            indexList = hsTArray()
            for k in range(idxCount):
                indexList.append(buf.Read16())
            self.fIdxBuffStorage.append(indexList) # was self-IndexStorage

        for j in range(VertexStorageCount):
            count = buf.Read32()
            assert(count == 1)
            cells = hsTArray()
            for j in range(count):
                cell = plGBufferCell()
                cell.read(buf)
                cells.append(cell)
            self.fCells.append(cells) # Was self.fCells


    def write(self,buf): #Compressed Output ONLY (just as in plasma :) )
        # Ensure some format bits that are always set

        self.fFormat |= 0x80
        # RTR: We only write out one vertex storage - and so does Cyan!
        VertexStorageCount = 1
        # Calculate the size
        size = 0
        for i in range(VertexStorageCount):
            size += len(self.fVertBuffStorage)
        for i in range(len(self.fIdxBuffStorage)):
            size += len(self.fIdxBuffStorage[i])
        buf.WriteByte(self.fFormat)
        buf.Write32(size)
        coder = plVertexCoder()
        buf.Write32(VertexStorageCount)
        for i in range(VertexStorageCount):
            count = len(self.fVertBuffStorage)
            buf.Write16(count)

            if False: # Enable if neccesary
                if(count > 100000): # only say this if we have a really big number of vertices
                    print "=> Storing %i vertices of geometry - this can take some time...." % count
                else:
                    print "=> Storing %i vertices of geometry..." % count
            coder.write(self,buf,count)
        buf.Write32(len(self.fIdxBuffStorage))
        for i in range(len(self.fIdxBuffStorage)):
            indexStorageLength = len(self.fIdxBuffStorage[i])
            buf.Write32(indexStorageLength)
            for j in range(indexStorageLength):
                buf.Write16(self.fIdxBuffStorage.vector[i].vector[j])

        # RTR: put in one cell in a list for now
        cell = plGBufferCell()
        cell.VertexIndex = 0
        cell.ColorIndex = -1
        cell.NumVerts = len(self.fVertBuffStorage)
        cells = hsTArray()
        cells.append(cell)
        self.fCells.append(cells)
        for i in range(VertexStorageCount):
            buf.Write32(len(self.fCells.vector[i]))
            for j in range(len(self.fCells.vector[i])):
                self.fCells.vector[i].vector[j].write(buf)

class plDISpanIndex: #NOTE: This is a pile of guesswork (it still is on 28/nov/07)
    Flags = \
    { \
        "kMesh" : 0x00, \
        "kBone" : 0x01 \
    }

    def __init__(self):
        self.fFlags = 0
        self.fIndices = hsTArray()#<Int32>


    def read(self,buf):
        self.fFlags = buf.Read32()
        i = buf.Read32()
        for j in range(i):
            self.fIndices.append(buf.Read32())


    def write(self,buf):
        buf.Write32(self.fFlags)
        buf.Write32(len(self.fIndices))
        for i in self.fIndices.vector:
            buf.Write32(i)


class plSpaceTreeNode:
    def __init__(self):
        self.box = hsBounds3Ext()
        # on leaves the box matches with the mesh transformed bbox
        # on branches, the box should contain all child objects (they are also on axis)
        #self.subsets = None #plIcicle
        #self.leaf = 0
        self.flags = 0 #WORD
        # 0x01 - leaf
        # 0x00 - branch
        # 0x04 flag - unknown? (balance?)
        # 0x08 strange flag - unknown data stored in p,l.r fields
        self.parent = 0 #WORD
        # -1 on root node
        self.left = 0 #WORD
        # left child node if branch, link to mesh if leave
        self.right = 0 #WORD
        # 0 if leave, else child node


    def read(self,buf):
        self.box.read(buf)
        self.flags = buf.Read16()
        if self.flags not in [0x00,0x01,0x04,0x05,0x08]:
            raise "plSpaceTreeNode has unknown flag " + self.flags
        self.parent = buf.ReadSigned16()
        self.left = buf.Read16()
        self.right = buf.Read16()
        if self.flags & 0x01:
            assert(self.right==0)


    def write(self,buf):
        self.box.write(buf)
        buf.Write16(self.flags)
        buf.WriteSigned16(self.parent)
        buf.Write16(self.left)
        buf.Write16(self.right)


    def __str__(self):
        return "b:%s,t:%X,p:%04i,l:%04i,r:%04i" %(str(self.box),self.flags,self.parent,self.left,self.right)


class plSpaceTree:
    def __init__(self,version):
        self.version = version
        self.type = 0x8000 # Default to NULL tree
        self.totalNodesMinusRoot = 0
        self.numLeaves = 0
        self.nodes = hsTArray() #plSpaceTreeNode


    def read(self,buf,numIcicles):
        self.type = buf.Read16()
        if (self.type == 0x8000): # NULL
            return
        # Sanity check 1: type
        if self.version==6:
            assert(self.type==0x0240) #plSpaceTree
        else:
            assert(self.type==0x0258) #plSpaceTree
        self.totalNodesMinusRoot = buf.Read16()
        # Sanity Check 2: this binary space tree should have (2 * numIcicles) -1 nodes
        assert(self.totalNodesMinusRoot == ((2*numIcicles)-2) or (self.totalNodesMinusRoot == 0 and numIcicles == 0))
        self.numLeaves = buf.Read32()
        # Sanity Check 3: leaves vs icicles
        assert(self.numLeaves == numIcicles)
        numNodes = buf.Read32()
        # Sanity check 4: nodes vs total
        assert(numNodes == (self.totalNodesMinusRoot+1))
        for i in range(numNodes):
            node = plSpaceTreeNode()
            node.read(buf)
            # Sanity check 5: node flags
            if node.flags & 0x01:
                assert(node.left==i)
                assert(i<numIcicles)
                #print i, node.parent, numIcicles
                assert(node.parent>=numIcicles or (node.parent==-1 and numIcicles==1))
            if node.flags==0x00:
                assert(i>=numIcicles)
            if node.flags & 0x08:       #female,male,live_male,live_female
                if node.parent not in [0x0A52,0x290A,0x0000]:
                    raise "tree parent is %04X" % node.parent
                if node.left not in [0xE120,0x000A,0x0000]:
                    raise "tree left is %04X" % node.left
                if node.right not in [0x070F,0x676E,0x0000,0x3F80]:
                    raise "tree right is %04X" % node.right
            self.nodes.append(node)


    def write(self,buf):
        buf.Write16(self.type)
        if self.type == 0x8000: # NULL
            return
        buf.Write16(self.totalNodesMinusRoot)
        buf.Write32(self.numLeaves)
        buf.Write32(len(self.nodes))
        for node in self.nodes.vector:
            node.write(buf)

class plDrawable(hsKeyedObject):
    Props =\
    { \
        "kPropNoDraw"       :   0x1, \
        "kPropUNUSED"       :   0x2, \
        "kPropSortSpans"    :   0x4, \
        "kPropSortFaces"    :   0x8, \
        "kPropVolatile"     :  0x10, \
        "kPropNoReSort"     :  0x20, \
        "kPropPartialSort"  :  0x40, \
        "kPropCharacter"    :  0x80, \
        "kPropSortAsOne"    : 0x100, \
        "kPropHasVisLOS"    : 0x200
    }
    Crit =\
    { \
        "kCritStatic"       :  0x1, \
        "kCritSortSpans"    :  0x2, \
        "kCritSortFaces"    :  0x8, \
        "kCritCharacter"    :  0x10
    }
    plDrawableType =\
    { \
        "kNormal"           :      0x1, \
        "kNonDrawable"      :      0x2, \
        "kEnviron"          :      0x4, \
        "kLightProxy"       :  0x10000, \
        "kOccluderProxy"    :  0x20000, \
        "kAudibleProxy"     :  0x40000, \
        "kPhysicalProxy"    :  0x80000, \
        "kCoordinateProxy"  : 0x100000, \
        "kOccSnapProxy"     : 0x200000, \
        "kGenericProxy"     : 0x400000, \
        "kCameraProxy"      : 0x800000, \
        "kAllProxies"       : 0xFF0000, \
        "kAllTypes"         : 0x0000FF  \
    }
    plSubDrawableType =\
    { \
        "kSubNormal"        :  0x1, \
        "kSubNonDrawable"   :  0x2, \
        "kSubEnviron"       :  0x4, \
        "kSubAllTypes"      : 0xFF  \
    }
    plAccessFlags =\
    { \
        "kReadSrc"          : 0x1, \
        "kWriteDst"         : 0x2, \
        "kWriteSrc"         : 0x4  \
    }
    MsgTypes =\
    { \
        "kMsgMaterial"      : 0, \
        "kMsgDISpans"       : 1, \
        "kMsgFogEnviron"    : 2, \
        "kMsgPermaLight"    : 3, \
        "kMsgPermaProj"     : 4, \
        "kMsgPermaLightDI"  : 5, \
        "kMsgPermaProjDI"   : 6  \
    }

    Mapping = \
    { \
        "Flat"  : 0, \
        "Cube"  : 1, \
        "Tube"  : 2, \
        "Sphere": 3 \
    }

class plDrawableSpans(plDrawable):
    def __init__(self,parent,name="unnamed",type=0x004C):
        hsKeyedObject.__init__(self,parent,name,type)

        self.fLocalBounds = hsBounds3Ext() # flags == 0x00: max and min vertex of the entire set
        self.fWorldBounds = hsBounds3Ext() # flags == 0x01: same
        self.fMaxWorldBounds = hsBounds3Ext() # flags == 0x01: same

        # Notice!!! Do NOT ReadVector or WriteVector with Typless Classes!
        #
        # Below are sets of 4 matrices (2 pairs, normal and inverted)
        # they contain transformations indexed in the groups with flag 0x01
        # these are bones. matrices are local, bones have a coordinate
        # interface for correct placement in the age
        self.fLocalToWorlds = hsTArray([],self.getVersion()) #hsMatrix44
        self.fWorldToLocals = hsTArray([],self.getVersion()) #hsMatrix44
        self.fLocalToBones = hsTArray([],self.getVersion()) #hsMatrix44
        self.fBoneToLocals = hsTArray([],self.getVersion()) #hshsMatrix44

        self.fMaterials = hsTArray([0x07],self.getVersion()) #hsGMaterial
        self.fSpaceTree = plSpaceTree(self.getVersion())

        self.fIcicles = hsTArray([],self.getVersion()) #plIcicle
        self.fIcicles2 = hsTArray([],self.getVersion()) #plIcicle

        self.fGroups = hsTArray([],self.getVersion()) #plGBufferGroup
        self.fDIIndices = hsTArray([],self.getVersion()) #plDISpanIndex
        self.fProps = 0 #DWORD
        self.fCriteria = 0 #DWORD
        self.fRenderLevel = plRenderLevel()

        self.fSceneNode=UruObjectRef(self.getVersion()) #link to the plSceneNode
        self.fSourceSpans = hsTArray([],self.getVersion()) #plGeometrySpan


    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)
        for i in self.fMaterials:
            i.changePageRaw(sid,did,stype,dtype)
        for icicle in self.fIcicles:
            for light in icicle.lights1:
                light.changePageRaw(sid,did,stype,dtype)
            for light in icicle.lights2:
                light.changePageRaw(sid,did,stype,dtype)
        self.fSceneNode.changePageRaw(sid,did,stype,dtype)


    def read(self,buf):
        hsKeyedObject.read(self,buf)
        self.fProps = buf.Read32()
        self.fCriteria = buf.Read32()
        self.fRenderLevel.fLevel = buf.Read32()

        self.fMaterials.ReadVector(buf)
        i = buf.Read32()
        for j in range(i):
            icicle = plIcicle(self.getVersion())
            icicle.read(buf)
            self.fIcicles.append(icicle)
        i = buf.Read32()
        for j in range(i):
            icicle = plIcicle(self.getVersion())
            icicle.read(buf)
            self.fIcicles2.append(icicle)
        count = buf.Read32()
        for i in range(count):
            idx = buf.Read32()
            # This is just the same as i; it is used to set the
            # internal NativeTransform array, which is just the
            # same as the Icicles array. So, we will do nothing with it.
        for i in range(count):
            # These references are always nil
            self.fIcicles[i].fFogEnvironment.read(buf)
        if (count):
            self.fLocalBounds.read(buf)
            self.fWorldBounds.read(buf)
            self.fMaxWorldBounds.read(buf)
        else:
            self.fLocalBounds.flags |= 2
            self.fWorldBounds.flags |= 2
            self.fMaxWorldBounds.flags |= 2
        for i in range(count):
            if (self.fIcicles[i].fProps & plSpan.Props["kPropHasPermaLights"]):
                self.fIcicles[i].fPermaLights.ReadVector(buf)
            if (self.fIcicles[i].fProps & plSpan.Props["kPropHasPermaProjs"]):
                self.fIcicles[i].fPermaProjs.ReadVector(buf)
        i = buf.Read32()
        for j in range(i):
            # There are never any geometry spans in the Cyan ages,
            # so this code will never get exercised
            geometrySpan = plGeometrySpan()
            geometrySpan.read(buf)
            self.fSourceSpans.append(geometrySpan)
        i = buf.Read32()
        for j in range(i):
            k = hsMatrix44()
            k.read(buf)
            self.fLocalToWorlds.append(k)
            l = hsMatrix44()
            l.read(buf)
            self.fWorldToLocals.append(l)
            m = hsMatrix44()
            m.read(buf)
            self.fLocalToBones.append(m)
            n = hsMatrix44()
            n.read(buf)
            self.fBoneToLocals.append(n)
        i = buf.Read32()
        for j in range(i):
            spanIndex = plDISpanIndex()
            spanIndex.read(buf) # Read Function of plDISpanIndex is written out here in plasma
            self.fDIIndices.append(spanIndex)
        i = buf.Read32()
        for j in range(i):
            bufferGroup = plGBufferGroup()
            bufferGroup.read(buf)
            self.fGroups.append(bufferGroup)
        self.fSpaceTree.read(buf,len(self.fIcicles))
        self.fSceneNode.setVersion(self.getVersion())
        self.fSceneNode.read(buf)
        assert(self.fSceneNode.verify(self.Key))


    def write(self,buf):
        hsKeyedObject.write(self,buf)
        buf.Write32(self.fProps)
        buf.Write32(self.fCriteria)
        buf.Write32(self.fRenderLevel.fLevel)
        self.fMaterials.WriteVector(buf)
        buf.Write32(len(self.fIcicles))
        for icicle in self.fIcicles.vector:
            icicle.write(buf)
        buf.Write32(len(self.fIcicles2))
        for icicle in self.fIcicles2.vector:
            icicle.write(buf)
        count=len(self.fIcicles)
        buf.Write32(count)
        for i in range(count):
            buf.Write32(i)
        for i in range(count):
            self.fIcicles[i].fFogEnvironment.write(buf)
        if count!=0:
            self.fLocalBounds.write(buf)
            self.fWorldBounds.write(buf)
            self.fMaxWorldBounds.write(buf)
        for i in range(count):
            if (self.fIcicles[i].fProps & 0x80):
                self.fIcicles[i].fPermaLights.WriteVector(buf)
            if (self.fIcicles[i].fProps & 0x100):
                self.fIcicles[i].fPermaProjs.WriteVector(buf)
        buf.Write32(len(self.fSourceSpans))
        for geometrySpans in self.fSourceSpans.vector:
            geometrySpans.write(buf)
        buf.Write32(len(self.fLocalToWorlds))
        for i in range(len(self.fLocalToWorlds)):
            self.fLocalToWorlds[i].write(buf)
            self.fWorldToLocals[i].write(buf)
            self.fLocalToBones[i].write(buf)
            self.fBoneToLocals[i].write(buf)
        buf.Write32(len(self.fDIIndices))
        for spanIndex in self.fDIIndices.vector:
            spanIndex.write(buf)
        buf.Write32(len(self.fGroups))
        for bufferGroup in self.fGroups.vector:
            bufferGroup.write(buf)
        self.fSpaceTree.write(buf)
        self.fSceneNode.update(self.Key)
        assert(self.fSceneNode.flag == 0x01)
        self.fSceneNode.write(buf)

    def _Find(page,name):
        return page.find(0x004C,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x004C,name,1)
    FindCreate = staticmethod(_FindCreate)

    def updateName(self):
        if self.fRenderLevel.fLevel==0:
            sfx="Spans"
        else:
            sfx="BlendSpans"
        root=self.getRoot()
        one="%08x" % self.fRenderLevel.fLevel
        two="%x" % self.fCriteria
        testname=str(root.name) + "_District_" + str(root.page) + "_" + one + "_" + two + sfx
        self.Key.name.set(testname)


    def import_all(self):
        for i in range(len(self.fDIIndices)):
            self.import_object(i,"obj%02i" % i)


    def import_mesh(self,obj,groupidx,drawidx=0):
        root = self.getRoot()
        name = str(obj.name)
        # Do Mesh import here
        print "  [Drawable Spans]"
        if groupidx==-1 or groupidx == 0xFFFFFFFF: # Check both signed and unsigned representations (unfortunate hack)
            return []
        if self.fDIIndices[groupidx].fFlags==plDISpanIndex.Flags["kBone"]:
            return []

        resmanager=self.getResManager()

        # Find span index
        spanIndex = self.fDIIndices[groupidx] # plDISpanIndex

        # find the Mesh Object
        mesh = obj.getData(False,True) # gets a Mesh object instead of an NMesh

        # The icicle has a list of vertex groups

        # As this list has been generated by us before, it is safe to assum that it is all already connected
        MatList = []
        print "   Mesh's material list:",obj.getMaterials()
        for bmat in obj.getMaterials():
            MatList.append(bmat)
        print "   There are %d materials already on the object"%(len(MatList))

        MatIndices = {}

        # Parse the materials used by this DIIndexSet
        for i in range(len(spanIndex.fIndices)):
            icicle = self.fIcicles[spanIndex.fIndices[i]]

            #Find the material
            matref=self.fMaterials[icicle.fMaterialIdx]
            mat=root.findref(matref)
            if mat==None:
                print "   Material %s not found" %str(matref)
                BlenderMat = Blender.Material.New("MatUnknown")
            else:
                BlenderMat=mat.data.ToBlenderMat(obj)

            midx = -1
            for i in range(len(MatList)):
                bmat = MatList[i]
                if bmat == BlenderMat:
                    print "   Material %s is already in the list"%(bmat.name)
                    midx = i

            if midx == -1:
                # append to the list
                MatList.append(BlenderMat)
                print "   Appending Material %s to the list"%(BlenderMat.name)
                midx = len(MatList) - 1
            # ass to the index dictionary (used to get the material index back from the reference.)
            MatIndices[icicle.fMaterialIdx] = midx

        if len(MatList) > 16:
            print "-------------------------------------------------------"
            print "WARNING! Blender only supports 16 materials per object."
            print "This object has %d materials." %(len(MatList))
            print "Truncating list to 16 materials."
            print "-------------------------------------------------------"
            MatList = MatList[0:16]

        print "   There are %d materials now on the object"%(len(MatList))

        # assign these materials (Has to be assigned to the object)
        obj.setMaterials(MatList)
        obj.colbits=(1<< len(MatList)) - 1 # set all materials to be used
        obj.activeMaterial = 1

        print "   Mesh's material list:",obj.getMaterials()


        # Ensure that we have the correct vertexcolor layers
        list = mesh.getColorLayerNames()
        if not ("Alpha" in list and "Col" in list and len(list) == 2):
            for layer in list:
                mesh.removeColorLayer(layer)
            mesh.addColorLayer("Col")
            mesh.addColorLayer("Alpha")

        # Create a list of all lights in this page....
        lights = []
        lights.extend(root.listobjects(0x55)) # List of plDirectionalLight in this page
        lights.extend(root.listobjects(0x56)) # List of plOmniLight in this page
        lights.extend(root.listobjects(0x57)) # List of plSpotLight in this page



        # Parse Vertex Group Mesh Data
        for i in range(len(spanIndex.fIndices)):
            print "   Material group",i
            VGroup_StartIdx = len(mesh.verts) # Store the Start index for this vertex group
            VGroup_StartFace = len(mesh.faces)
            VGroup_GroupName = "VtxGroup" + str(len(mesh.getVertGroupNames())+1)

            # get the icicle (contains material info and info about which vertexes to extract from the buffer group)
            icicle = self.fIcicles[spanIndex.fIndices[i]]

            # get the buffergroup that stores the vertices of this span
            bufferGroup = self.fGroups[icicle.fGroupIdx]

            # Ensure that we have the correct UV Layers
            UVLayers = mesh.getUVLayerNames()
            if len(UVLayers) < bufferGroup.GetUVCount():
                for i in range(len(UVLayers),bufferGroup.GetUVCount()):
                    mesh.addUVLayer("UVLayer" + str(i))
            UVLayers = mesh.getUVLayerNames()


            # verts is a list of all vertices in the buffergroup
            verts=bufferGroup.fVertBuffStorage

            print "    Vertices... (%d of them)"%(icicle.fVLength)
            # Create the Vertex Group
            mesh.addVertGroup(VGroup_GroupName)
            for e in range(icicle.fVLength):
                s=icicle.fVStartIdx + e  # originally used icicle.fCellOffset
                plvert = verts[s]
                mesh.verts.extend((Mathutils.Vector(plvert.X(),plvert.Y(),plvert.Z())))

                vertidx = len(mesh.verts)-1
                vert = mesh.verts[vertidx]
                normalVector = Mathutils.Vector(plvert.nx,plvert.ny,plvert.nz)
                vert.no = normalVector

                if bufferGroup.GetNumSkinWeights() > 0:
                    weight = plvert.blend[0]
                else:
                    weight = bufferGroup.GetSkinIndices()
                mesh.assignVertsToGroup(VGroup_GroupName, [vertidx,] , weight, Blender.Mesh.AssignModes.REPLACE)

                if e%500 == 0 and not e == 0:
                    print "\r     %d"%(e),
            print "\n",

            # #
            # # Blender Stores U/V Coordinates in the faces, as well as vertex colors and materials
            # # This makes the face extractor a bit more painful as a process, sigh....
            # #

            # Begin with the face process
            mesh.vertexColors = True # set vertex colors to true

            # Get the buffer that stores the faces (Indices)
            surface = bufferGroup.fIdxBuffStorage[icicle.fIBufferIdx]

            # Extract the faces from the buffergroup by making a list of faces
            # (Tuples of 3)

            print "    Faces...    (%d of them)" %(icicle.fILength/3)
            # Faces are stored in a giant array of icicle.fILength * (3 indices)
            e=0
            while e < icicle.fILength:
                s=icicle.fIPackedIdx + e # Calculate base address for this face
                # putthe next 3 indices into a list to make a face
                myface = [surface[s+0]-icicle.fVStartIdx + VGroup_StartIdx, \
                          surface[s+1]-icicle.fVStartIdx + VGroup_StartIdx, \
                          surface[s+2]-icicle.fVStartIdx + VGroup_StartIdx  \
                         ]
                mesh.faces.extend((myface))
                face = mesh.faces[len(mesh.faces)-1]

                if MatIndices[icicle.fMaterialIdx] < len(MatList):
                    face.mat = MatIndices[icicle.fMaterialIdx]

                # now set vertex specific data
                for vi in range(3):
                    # get the vertex index in the verts array
                    sidx=surface[s+vi]
                    vert = verts[sidx] # get a reference to the plasma face

                    mesh.activeColorLayer = "Alpha"
                    face.col[vi].r = vert.color.a
                    face.col[vi].g = vert.color.a
                    face.col[vi].b = vert.color.a
                    face.col[vi].a = 255

                    mesh.activeColorLayer = "Col"
                    face.col[vi].r = vert.color.r
                    face.col[vi].g = vert.color.g
                    face.col[vi].b = vert.color.b
                    face.col[vi].a = 255

                    for uvidx in range(bufferGroup.GetUVCount()):
                        UVLayerName = UVLayers[uvidx]
                        mesh.activeUVLayer = UVLayerName
                        face.uv[vi].x = vert.tex[uvidx][0]
                        face.uv[vi].y = 1-vert.tex[uvidx][1]

                fcount = e/3
                if fcount%500 == 0 and not fcount == 0:
                    print "\r     %d"%(fcount),
                e=e+3 # put the base index 3 places further
            print "\n",

            # Set the first UV Layer as the active one
            if len(UVLayers) > 0:
                mesh.activeUVLayer = UVLayers[0]

            L2W=icicle.fLocalToWorld.get()
            L2W.transpose()

            # Update the normals
            mesh.calcNormals()

             # Lighting - Still need to find a way to have lamps being processed first....

            if MatIndices[icicle.fMaterialIdx] < len(MatList):
                mat = MatList[MatIndices[icicle.fMaterialIdx]]
                if len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector) > 0:
                    mat.mode &= ~Blender.Material.Modes["SHADELESS"]

                    # Only assign a lightgroup if not all lamps in the page are linked to this object
                    if (len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector)) < len(lights):
                        print "    Limited light sources (%d sources)"%(len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector))

                        lightgroup = Blender.Group.New(str(mat.name))
                        objlist = Blender.Scene.GetCurrent().objects
                        for obj in objlist:
                            if obj.getType() == "Lamp":
                                dataname = obj.getData(True) # first param set to True, returns only datablock's name as string
                                for a in icicle.fPermaLights.vector:
                                    if str(a.Key.name) == str(obj.name) or str(a.Key.name) == dataname:
                                        print "     Connecting Light",str(a.Key.name),"to lamp",str(obj.name)
                                        lightgroup.objects.link(obj)

                                for a in icicle.fPermaProjs.vector:
                                    if str(a.Key.name) == str(obj.name) or str(a.Key.name) == dataname:
                                        print "     Connecting Light",str(a.Key.name),"to lamp",str(obj.name)
                                        lightgroup.objects.link(obj)
                        # Assign the light group to the material
                        mat.lightGroup = lightgroup
                        # And set the group_exclusive bit
                        #mat.mode |= Blender.Material.Modes["GROUP_EXCLUSIVE"]
                    else:
                        print "    Fully lit object (%d sources)"%(len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector))

                else:
                    print "    Shadeless object"

                    mat.mode |= Blender.Material.Modes["SHADELESS"]

         # set object to display in first layer
        obj.layers=[1,]

    def import_create_mesh(self,objList,groupidx,objname):
        # Sirius:
        # at some point this code broke material handling for shaded object (which ended up with less materials than they should).
        # Doesn't occur anymore, so should be fine.


        root = self.getRoot()
        if len(objList):
            obj = objList[-1]
        else:
            obj = Blender.Object.New('Mesh',objname)
            mesh = Mesh.New(objname)
            obj.link(mesh)
            obj.layers=[1,]
            objList.append(obj)

        name = str(obj.name)



        # Do Mesh import here
        print "  [Drawable Spans]"
        if groupidx==-1 or groupidx == 0xFFFFFFFF: # Check both signed and unsigned representations (unfortunate hack)
            print "   (Object is a particle emitter, no need to find faces)"
            return []
        if self.fDIIndices[groupidx].fFlags==plDISpanIndex.Flags["kBone"]:
            return []



        resmanager=self.getResManager()

        # Find span index
        spanIndex = self.fDIIndices[groupidx] # plDISpanIndex

        # find the Mesh Object
        mesh = obj.getData(False,True) # gets a Mesh object instead of an NMesh

        # The icicle has a list of vertex groups

        # As this list has been generated by us before, it is safe to assum that it is all already connected
        MatList = []
        print "   Mesh's material list:",obj.getMaterials()
        for bmat in obj.getMaterials():
            MatList.append(bmat)
        print "   There are %d materials already on the object"%(len(MatList))

        MatIndices = {}



        # Create a list of all lights in this page....
        lights = []
        lights.extend(root.listobjects(0x55)) # List of plDirectionalLight in this page
        lights.extend(root.listobjects(0x56)) # List of plOmniLight in this page
        lights.extend(root.listobjects(0x57)) # List of plSpotLight in this page



        # Parse Vertex Group Mesh Data
        for i in range(len(spanIndex.fIndices)):
            print "   Material group",i

            # get the icicle (contains material info and info about which vertexes to extract from the buffer group)
            icicle = self.fIcicles[spanIndex.fIndices[i]]


            #################### MATERIAL HANDLING #######################

            matref=self.fMaterials[icicle.fMaterialIdx]
            mat=root.findref(matref)
            if mat==None:
                print "   Material %s not found" %str(matref)
                BlenderMat = Blender.Material.New("MATUNKNOWN")
            else:
                BlenderMat=mat.data.ToBlenderMat(obj)

            if len(MatList) < 16:
                midx = -1
                for i in range(len(MatList)):
                    bmat = MatList[i]
                    if bmat == BlenderMat:
                        print "   Material %s is already in the list"%(bmat.name)
                        midx = i

                if midx == -1:
                    # append to the list
                    MatList.append(BlenderMat)
                    print "   Appending Material %s to the list"%(BlenderMat.name)
                    midx = len(MatList) - 1
                # ass to the index dictionary (used to get the material index back from the reference.)
                MatIndices[icicle.fMaterialIdx] = midx
            else:
                print "   Too many materials - have to split up object."

                MatIndices = {icicle.fMaterialIdx: 0}
                MatList = [BlenderMat]

                obj = Blender.Object.New('Mesh',objname)
                mesh = Mesh.New(objname)
                obj.link(mesh)
                obj.layers=[1,]
                objList.append(obj)
                mesh = obj.getData(False,True) # gets a Mesh object instead of an NMesh


            # assign these materials (Has to be assigned to the object)
            obj.setMaterials(MatList)
            obj.colbits=(1<< len(MatList)) - 1 # set all materials to be used
            obj.activeMaterial = 1






            # Ensure that we have the correct vertexcolor layers
            list = mesh.getColorLayerNames()
            if not ("Alpha" in list and "Col" in list and len(list) == 2):
                for layer in list:
                    mesh.removeColorLayer(layer)
                mesh.addColorLayer("Col")
                mesh.addColorLayer("Alpha")

            #################### /MATERIAL HANDLING ######################


            VGroup_StartIdx = len(mesh.verts) # Store the Start index for this vertex group
            VGroup_StartFace = len(mesh.faces)
            VGroup_GroupName = "VtxGroup" + str(len(mesh.getVertGroupNames())+1)


            # get the buffergroup that stores the vertices of this span
            bufferGroup = self.fGroups[icicle.fGroupIdx]

            # Ensure that we have the correct UV Layers
            UVLayers = mesh.getUVLayerNames()
            if len(UVLayers) < bufferGroup.GetUVCount():
                for i in range(len(UVLayers),bufferGroup.GetUVCount()):
                    mesh.addUVLayer("UVLayer" + str(i))
            UVLayers = mesh.getUVLayerNames()


            # verts is a list of all vertices in the buffergroup
            verts=bufferGroup.fVertBuffStorage

            print "    Vertices... (%d of them)"%(icicle.fVLength)
            # Create the Vertex Group
            mesh.addVertGroup(VGroup_GroupName)
            for e in range(icicle.fVLength):
                s=icicle.fVStartIdx + e  # originally used icicle.fCellOffset
                plvert = verts[s]
                mesh.verts.extend((Mathutils.Vector(plvert.X(),plvert.Y(),plvert.Z())))

                vertidx = len(mesh.verts)-1
                vert = mesh.verts[vertidx]
                normalVector = Mathutils.Vector(plvert.nx,plvert.ny,plvert.nz)
                vert.no = normalVector

                if bufferGroup.GetNumSkinWeights() > 0:
                    weight = plvert.blend[0]
                else:
                    weight = bufferGroup.GetSkinIndices()
                mesh.assignVertsToGroup(VGroup_GroupName, [vertidx,] , weight, Blender.Mesh.AssignModes.REPLACE)

                if e%500 == 0 and not e == 0:
                    print "\r     %d"%(e),
            print "\n",

            # #
            # # Blender Stores U/V Coordinates in the faces, as well as vertex colors and materials
            # # This makes the face extractor a bit more painful as a process, sigh....
            # #

            # Begin with the face process
            mesh.vertexColors = True # set vertex colors to true

            # Get the buffer that stores the faces (Indices)
            surface = bufferGroup.fIdxBuffStorage[icicle.fIBufferIdx]

            # Extract the faces from the buffergroup by making a list of faces
            # (Tuples of 3)

            print "    Faces...    (%d of them)" %(icicle.fILength/3)
            # Faces are stored in a giant array of icicle.fILength * (3 indices)
            e=0
            while e < icicle.fILength:
                s=icicle.fIPackedIdx + e # Calculate base address for this face
                # putthe next 3 indices into a list to make a face
                myface = [surface[s+0]-icicle.fVStartIdx + VGroup_StartIdx, \
                          surface[s+1]-icicle.fVStartIdx + VGroup_StartIdx, \
                          surface[s+2]-icicle.fVStartIdx + VGroup_StartIdx  \
                         ]
                mesh.faces.extend((myface))
                face = mesh.faces[len(mesh.faces)-1]

                if MatIndices[icicle.fMaterialIdx] < len(MatList):
                    face.mat = MatIndices[icicle.fMaterialIdx]

                # now set vertex specific data
                for vi in range(3):
                    # get the vertex index in the verts array
                    sidx=surface[s+vi]
                    vert = verts[sidx] # get a reference to the plasma face

                    mesh.activeColorLayer = "Alpha"
                    face.col[vi].r = vert.color.a
                    face.col[vi].g = vert.color.a
                    face.col[vi].b = vert.color.a
                    face.col[vi].a = 255

                    mesh.activeColorLayer = "Col"
                    face.col[vi].r = vert.color.r
                    face.col[vi].g = vert.color.g
                    face.col[vi].b = vert.color.b
                    face.col[vi].a = 255

                    for uvidx in range(bufferGroup.GetUVCount()):
                        UVLayerName = UVLayers[uvidx]
                        mesh.activeUVLayer = UVLayerName
                        face.uv[vi].x = vert.tex[uvidx][0]
                        face.uv[vi].y = 1-vert.tex[uvidx][1]

                fcount = e/3
                if fcount%500 == 0 and not fcount == 0:
                    print "\r     %d"%(fcount),
                e=e+3 # put the base index 3 places further
            print "\n",

            # Set the first UV Layer as the active one
            if len(UVLayers) > 0:
                mesh.activeUVLayer = UVLayers[0]

            L2W=icicle.fLocalToWorld.get()
            L2W.transpose()

            # Update the normals
            mesh.calcNormals()

             # Lighting - Still need to find a way to have lamps being processed first....

            if MatIndices[icicle.fMaterialIdx] < len(MatList):
                mat = MatList[MatIndices[icicle.fMaterialIdx]]
                #print "   -> MatList:", obj.getMaterials()
                if len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector) > 0:
                    mat.mode &= ~Blender.Material.Modes["SHADELESS"]

                    # Only assign a lightgroup if not all lamps in the page are linked to this object
                    if (len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector)) < len(lights):
                        print "    Limited light sources (%d sources)"%(len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector))

                        lightgroup = Blender.Group.New(str(mat.name))
                        lobjlist = Blender.Scene.GetCurrent().objects
                        for lobj in lobjlist:
                            if lobj.getType() == "Lamp":
                                dataname = lobj.getData(True) # first param set to True, returns only datablock's name as string
                                for a in icicle.fPermaLights.vector:
                                    if str(a.Key.name) == str(lobj.name) or str(a.Key.name) == dataname:
                                        print "     Connecting Light",str(a.Key.name),"to lamp",str(lobj.name)
                                        lightgroup.objects.link(lobj)

                                for a in icicle.fPermaProjs.vector:
                                    if str(a.Key.name) == str(lobj.name) or str(a.Key.name) == dataname:
                                        print "     Connecting Light",str(a.Key.name),"to lamp",str(lobj.name)
                                        lightgroup.objects.link(lobj)
                        # Assign the light group to the material
                        mat.lightGroup = lightgroup
                        # And set the group_exclusive bit
                        #mat.mode |= Blender.Material.Modes["GROUP_EXCLUSIVE"]
                    else:
                        print "    Fully lit object (%d sources)"%(len(icicle.fPermaLights.vector) + len(icicle.fPermaProjs.vector))

                else:
                    print "    Shadeless object"

                    mat.mode |= Blender.Material.Modes["SHADELESS"]
            #print "   -> MatList:", obj.getMaterials()



# As the draw interface is linked closely to the DrawableSpans, it is included here:

class plDrawInterface(plObjInterface):
    def __init__(self,parent,name="unnamed",type=0x0016):
        plObjInterface.__init__(self,parent,name,type)
        self.reset() # contains initialization of f-variables

        self.blenderobjects=[]

    def reset(self):
        if self.getVersion()==6:
            self.fDrawables=hsTArray([0x0049],self.getVersion(),True)
            self.fRegions=hsTArray([0x00E9],self.getVersion(),True)
            self.fDrawableIndices = hsTArray()
        else:
            self.fDrawables=hsTArray([0x004C],self.getVersion(),True)
            self.fRegions=hsTArray([0x0116],self.getVersion(),True)
            self.fDrawableIndices = hsTArray()


    def changePageRaw(self,sid,did,stype,dtype):
        plObjInterface.changePageRaw(self,sid,did,stype,dtype)
        self.fDrawables.changePageRaw(sid,did,stype,dtype)
        self.fRegions.changePageRaw(sid,did,stype,dtype)


    def read(self,stream):
        plObjInterface.read(self,stream)
        self.fDrawables.size = stream.Read32()
        # spans are different than normal UruObjectRef reads, since
        # they have the groups intermingled with the refs
        for i in range(self.fDrawables.size):
            gi = stream.ReadSigned32()
            self.fDrawableIndices.append(gi)
            self.fDrawables.ReadRef(stream)
        self.fRegions.ReadVector(stream)


    def write(self,stream):
        plObjInterface.write(self,stream)
        stream.Write32(self.fDrawables.size)
        for i in range(self.fDrawables.size):
            stream.WriteSigned32(self.fDrawableIndices[i])
            self.fDrawables[i].update(self.Key)
            self.fDrawables[i].write(stream)
        self.fRegions.WriteVector(stream)

    def _Find(page,name):
        return page.find(0x0016,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0016,name,1)
    FindCreate = staticmethod(_FindCreate)

    def import_obj(self,obj):
        root = self.getRoot()
        print " [DrawInterface %s]"%(str(self.Key.name))

        # Import all drawables in this list
        for i in range(len(self.fDrawableIndices)):
            print "  Importing set",(i+1),"of",len(self.fDrawableIndices)
            group = self.fDrawableIndices[i]
            spanref = self.fDrawables[i]
            drawspans = root.findref(spanref)
            drawspans.data.import_mesh(obj,group)

    def import_create_obj(self):
        root = self.getRoot()
        print " [DrawInterface %s]"%(str(self.Key.name))

        objList = []

        # Import all drawables in this list
        for i in range(len(self.fDrawableIndices)):
            print "  Importing set",(i+1),"of",len(self.fDrawableIndices)
            group = self.fDrawableIndices[i]
            spanref = self.fDrawables[i]
            drawspans = root.findref(spanref)
            drawspans.data.import_create_mesh(objList,group,str(self.Key.name))


        return objList

    def _Import(scnobj,prp,obj):
        if not scnobj.draw.isNull():
            draw = prp.findref(scnobj.draw)
            if draw!=None:
                draw.data.import_obj(obj)

    Import = staticmethod(_Import)

    def _ImportCreate(scnobj,prp):
        if not scnobj.draw.isNull():
            draw = prp.findref(scnobj.draw)
            if draw!=None:
                objs = draw.data.import_create_obj()
                return objs
        return []

    ImportCreate = staticmethod(_ImportCreate)



class plInstanceDrawInterface(plDrawInterface):
    def __init__(self,parent,name="unnamed",type=0x00D2):
        plDrawInterface.__init__(self,parent,name,type)

        self.fTargetID=-1
        self.fDrawable = UruObjectRef()

    def _Find(page,name):
        return page.find(0x00D2,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00D2,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plDrawInterface.read(self,stream)

        self.fTargetID = stream.Read32()
        self.fDrawable.read(stream)

    def write(self,stream):
        plDrawInterface.write(self,stream)

        stream.Write32(self.fTargetID )
        self.fDrawable.write(stream)

    def import_obj(self,obj):
##        plDrawInterface.import_obj(self,obj)
        root = self.getRoot()
        print " [InstanceDrawInterface %s]"%(str(self.Key.name))

        # Import all drawables in this list

        drawspans = root.findref(self.fDrawable)
        drawspans.data.import_mesh(obj,self.fTargetID)

    def _Import(scnobj,prp,obj):
        if not scnobj.draw.isNull():
            draw = prp.findref(scnobj.draw)
            if draw!=None:
                draw.data.import_obj(obj)

    Import = staticmethod(_Import)


from alcurutypes import *
from alc_GeomClasses import *
from alcConvexHull import *
from alc_Functions import *
from alc_Classes import *
from alc_MatClasses import *
from alc_LightClasses import *
