# $Id: alcresmanager.py 876 2007-12-15 22:15:11Z Paradox $
#
#    Copyright (C) 2005-2008  Alcugs PyPRP Project Team and 2008 GoW PyPRP Project Team
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
    from Blender import Object
except ImportError:
    pass


import glob, dircache, os
from os.path import *
from binascii import *
import operator
import alcconfig
from alc_hsStream import *
from alcm5crypt import *
from alcspecialobjs import *
from alcprpfile import *
from alcurutypes import *
from alc_Classes import *
from alc_LightClasses import *
from alc_ObjClasses import *
from alc_AbsClasses import *
from alc_Functions import *
from alcmfsgen import *
from alc_LogicClasses import *
from alc_QuickScripts import *

class alcUruPage:
    TypeFlags = \
    { \
        "kNone"      :  0x0, \
        "kLocalOnly" :  0x1, \
        "kVolatile"  :  0x2, \
        "kReserved"  :  0x4, \
        "kBuiltIn"   :  0x8, \
        "kItinerant" : 0x10  \
    }
    def __init__(self,parent,name="unnamed",num=0,hide=0,type=0x00):
        self.type="page"
        self.age=parent
        self.resmanager=parent.resmanager
        self.name=name
        self.num=num
        self.hide=hide
        self.type=type
        self.prp=None
        if self.resmanager.filesystem:
            self.ignore=[0x00,]
        else:
            self.ignore=[0x00,0x4C,]


    def getPath(self,version=None):
        if version==None:
            version=self.age.version
        if version!=6:
            return self.age.base + "/" + self.age.name + "_District_" + self.name + ".prp"
        else:
            return self.age.base + "/" + self.age.name + "_" + self.name + ".prp"


    def preLoad(self):
        #print " PreLoading %s" %(self.name)
        prpinfo=PrpFileInfo()
        try:
            #f=file(self.getPath(),"rb")
            f=hsStream(self.getPath(),"rb")
        except:
            print "Warning: Not found page %s for age %s" %(self.name,self.age.name)
            return
        prpinfo.read(f)
        f.close()
        #verify seq and num
        if self.age.getSeq()==0:
            raise RuntimeError, "age sequence is not set - but it should be!"
        pid=xPageId()
        pid.setRaw(prpinfo.page_id,prpinfo.page_type,self.age.getSeq())
        self.type=prpinfo.page_type
        pnum=self.num
        if prpinfo.name.name!=self.age.name:
            print "Error: Age name mismatch %s in manifest %s in page" %(self.age.name,prpinfo.name.name)
            print "Page %s in manifest %s in page" %(self.name,prpinfo.page.name)
            print "Debug: Age %s, Page: %s, path: %s, manifest contents:" %(self.age.name,self.name,self.getPath())
            for xpage in self.age.pages:
                print xpage.name, xpage.getPath()
            raise "Error: Age name mismatch %s in manifest %s in page" %(self.age.name,prpinfo.name.name)
        if prpinfo.page.name!=self.name:
            raise "Error: Page name mismatch %s in manifest %s in page" %(self.name,prpinfo.page.name)
        pid2=xPageId()
        pid2.setPage(self.age.getSeq(),pnum,None,prpinfo.page_type)
        if pid2.getRaw()!=pid.getRaw():
            raise "%s Page Id mismatch %08X in manifest, %08X in page" \
                  %(prpinfo.name.name + " " + prpinfo.page.name,pid2.getRaw(),pid.getRaw())


    def load(self):
        if self.prp==None:
            self.prp=PrpFile(self)
            try:
                f=hsStream(self.getPath(),"rb")
            except IOError:
                self.prp=None
                print "Warning: Not found page %s for age %s" %(self.name,self.age.name)
                return
            self.prp.read(f)
            #self.resmanager.addPrp(self.prp)
            f.close()


    def unload(self):
        if self.prp!=None:
            #self.prp.resmanager.delPrp(self.prp)
            del self.prp


    def save(self):
        if self.prp==None:
            return
        print "@ Saving page %s %i" %(self.name,self.num)
        #f=file(self.getPath(),"wb")
        f=hsStream(self.getPath(),"wb")
        #self.update_page()
        self.prp.write(f)
        f.close()


    def update_page(self):
        thenum=self.num
        if self.type in (0x04,0x00):
            flags=KAgeData
        elif (self.type==0x08 and self.num==-2):
            #self.num=0
            thenum=0
            flags=KAgeSDLHook
        elif (self.type==0x08 and self.num==-1):
            #self.num=0
            thenum=0
            flags=KAgeTextures
        else:
            raise RuntimeError, "Cannot save, Incorrect type of page %i,%i" %(self.type,self.num)
        self.prp.setName(self.age.name)
        self.prp.setPageName(self.name)
        self.prp.setPage(self.age.getSeq(),thenum,flags,0)
        #removed update refs, you may want to turn it on
        ### self.prp.setPage(self.seq,thenum,flags,1) <--

    # proxy functions to self.prp
    def find(self,type,name,create=0):
        if not self.prp is None:
            return self.prp.find(type,name,create)
        else:
            return None

    def findref(self,ref,create=0):
        if not self.prp is None:
            return self.prp.findref(ref,create)
        else:
            return None

    def import_all(self):
        print "#########################################"
        print "##"
        print "## => Importing page %s %i <=" %(self.name,self.num)
        print "##"
        print "#########################################"


        if self.prp==None:
            print ""
            print "-> LOADING PAGE - This can take a while...."
            print "   If you have something better to do, now is the time to do so...."
            print ""

            self.load()
            if self.prp==None:
                return

        ## Sirius' modif - extract ALL textures
        # Since I'm on a cruisade to import Ages to Unreal, this comes in handy.
        # Textures that are sub-layers of animated layers aren't read by PyPRP,
        # which means they are not extracted and cannot be used once in UDK.
        # This extracts all mipmaps from any loaded PRP.
        # It doesn't take much longer since most of them are extracted anyway.
        #
        # This code only runs if we use the correct option from the import menu.
        if alcconfig.extractAllTextures:
            print "Extracting ALL textures from this PRP..."
            for mipmap in self.prp.listobjects(0x0004):
                mipmap.data.ToBlenderImage()
            print "Done extracting textures."

        #import
        if self.type in (0x04,0x00):
            #find sceneNode and import all sceneobjects linked to it
            scn = self.prp.getSceneNode()
            #Dustin
            print "self.type=" + `self.type`
            #/Dustin
            if scn==None:
                raise RuntimeError, "This age does not have a Scene Node?"


            scene = Blender.Scene.New(self.name)

            scn.data.import_all(scene)
        elif self.num == -2:
            # Check for an AgeSDLHook

            if not self.age.attach.has_key('AgeSDLHook'):
                self.age.attach['AgeSDLHook'] = False

            scenobj = plSceneObject.Find(self.prp,"AgeSDLHook")
            if scenobj != None:
                # Check for the python file mod
                name = str("VeryVerySpecialPythonFileMod")
                pymod = plPythonFileMod.Find(self,"VeryVerySpecialPythonFileMod")
                if pymod != None:
                    print ">>> AgeSDLHook discovered"
                    self.age.attach['AgeSDLHook'] = True



class alcUruAge:
    def __init__(self,parent,name="test",basename="./",prefix=0,version=5):
        self.type="age"
        self.resmanager=parent
        self.base=basename
        self.name=name
        self.book=None
        self.version=version
        self.attach = {}

        self.specialtex = []

        self.options = {}
        self.pages=[]

        self.setDefaults(prefix)

    def setDefaults(self,prefix=None):
        self.options={}
        self.pages=[]
        if prefix==None:
            prefix=self.getOpt("sequenceprefix")
            if prefix==None:
                prefix=0
        self.mfs=mfs(prefix)
        self.mfs.addFile(self.base + "/" + self.name + ".age")

        self.addOpt("StartDateTime","0000000000")
        self.addOpt("DayLength",24.0)
        self.addOpt("MaxCapacity",150)
        self.addOpt("LingerTime",180)
        self.addOpt("SequencePrefix",prefix)
        self.attach["AgeSDLHook"] = False

    def addOpt(self,name,value):
        if name=="SequencePrefix":
            self.mfs.seq=int(value)
        if name == "StartDateTime":
            value = int(value,10)

        self.options[name] = value


    def getOpt(self,name):
        try:
            return self.options[name]
        except:
            return None

    def findPage(self,name,agename=None):
        for page in self.pages:
            if page.name==name:
                return page
        return None


    def findPageByNum(self,num):
        for page in self.pages:
            if page.num==num:
                return page
        return None


    def addPage(self,name,num,hide,type=0x00):
        page=self.findPageByNum(num)
        self.mfs.addFile(self.base + "/" + self.name + "_District_" + name + ".prp")
        if page!=None:
            page.name=name
            page.hide=int(hide)
            page.type=int(type)
            return
        page=alcUruPage(self,name,num,hide,type)
        self.pages.append(page)


    def getInit(self):
        fpath=self.base + "/" + self.name + ".fni"
        if self.version==6:
            f=M5Crypt()
        else:
            f=Wdys()
        try:
            f.open(fpath,"rb")
            txt=f.read()
            f.close()
        except IOError:
            txt=""
        return txt


    def setInit(self,txt):
        fpath=self.base + "/" + self.name + ".fni"
        if self.version==6:
            f=M5Crypt()
        else:
            f=Wdys()
        f.open(fpath,"wb")
        f.write(txt)
        f.close()


    def read(self):
        fpath=self.base + "/" + self.name + ".age"
        f=Wdys()
        try:
            f.open(fpath)
            self.version=5
        except NotWdys:
            try:
                f=M5Crypt()
                f.open(fpath)
                self.version=6
            except NotM5Crypt:
                f=file(fpath,"rb")
                self.version=5
        buf = cStringIO.StringIO()
        buf.write(f.read())
        f.close()
        buf.seek(0)
        IAddedBuiltInPages=0
        for line in buf.readlines():
            print line
            w = line.strip().split("=")
            if w[0].lower()!="page":
                #Dustin
                if len(w)>1:
                    self.addOpt(w[0],w[1])
                #/Dustin
            else:
                if not IAddedBuiltInPages:
                    IAddedBuiltInPages=1
                    self.addBuiltInPages()
                x = w[1].split(",")
                try:
                    flag=int(x[2])
                except IndexError:
                    flag=0
                self.addPage(x[0],int(x[1]),flag)
        buf.close()
        self.preLoadAllPages()


    def preLoadAllPages(self):
        for page in self.pages:
            page.preLoad()


    def write(self):
        print self.options
        if self.resmanager.prp_version==6:
            self.f=M5Crypt()
        else:
            self.f=Wdys()
        self.f.open(self.base + "/" + self.name + ".age","wb")
        for key in self.options.keys():
            self.f.write(key + "=" + str(self.options[key]) + "\r\n")
        for page in self.pages:
            if page.type in (0x04,0x00):
                if page.hide==1:
                    self.f.write("Page=%s,%i,%i\r\n" %(page.name,page.num,page.hide))
                else:
                    self.f.write("Page=%s,%i\r\n" %(page.name,page.num))
        self.f.close()


    def setSeq(self,val):
        self.addOpt("SequencePrefix",str(val))


    def getSeq(self):
        return(int(self.getOpt("SequencePrefix")))


    def addBuiltInPages(self):
        seq=self.getSeq()
        if seq<0:
            return
        else:
            self.addPage("Textures",-1,0,0x08)
            if self.version!=6:
                self.addPage("BuiltIn",-2,0,0x08)

    def import_book(self):
        self.book=alcBook(self)

        if self.resmanager.filesystem:
            self.book.save2xml()
        else:
             self.book.storeToBlender()



    def import_page(self,name):
        for page in self.pages:
            if page.name==name:
                page.import_all()
                return
        #raise RunTimeError"The page %s is not in the %s manifest" %(name,self.name)


    def find(self,type,name,agename=None):
        for page in self.pages:
            if page.prp!=None:
                res=page.prp.find(type,name,0)
                if res!=None:
                    return res
        return None


    def findref(self,ref):
        if ref.flag==0x01:
            seq=self.getSeq()
            for page in self.pages:
                pid=xPageId()
                pid.setPage(seq,page.num,None,page.type)
                if pid.getRaw()==ref.Key.page_id:
                    if page.prp!=None:
                        return page.prp.findref(ref)
        return None


class alcResManager:
    def __init__(self,datadir="./",version=5,min_ver=12):
        self.type="rmgr"
        self.prp_version=version
        self.prp_min_ver=min_ver
        self.datadir=datadir
        self.ages=[]
        self.filesystem=0


    def setFilesystem(self):
        self.filesystem=1


    def getPRPVersion(self):
        return self.prp_version


    def getBasePath(self):
        return self.datadir


    def preload(self,datadir=None,age=None):
        if datadir==None:
            datadir=self.datadir
        ages=glob.glob(datadir + "/*.age")

        for a in ages:
            a=basename(a)[:-4]
            if(age == None or age == a):# or a[0:6] == 'Global' or a == 'GUI'):
                self.preLoadAge(a,datadir)



    def findAge(self,age,create=0,datadir=None,version=None):
        if version==None:
            version=self.prp_version
        for a in self.ages:
            if a.name==age:
                return a
        if not create:
            return None
        if datadir==None:
            datadir=self.datadir
        a=alcUruAge(self,age,datadir,None,version)
        self.ages.append(a)
        return a


    def preLoadAge(self,age,datadir=None):
        print "PreLoading %s" %age
        a=self.findAge(age,create=1,datadir=datadir)
        a.read()


    def import_book(self,agename):
        age=self.findAge(agename)
        if age==None:
            raise "Age %s does not exists!" %(agename)
        age.import_book()


    def find(self,type,name,agename=None):
        if agename==None:
            for a in self.ages:
                out=a.find(type,name)
                if out!=None:
                    return out
            return None
        for a in self.ages:
            if a.name==agename:
                return a.find(type,name)
        return None


    def findref(self,ref):
        if ref.flag==0x01:
            for a in self.ages:
                ret=a.findref(ref)
                if ret!=None:
                    return ret
        return None


    def xfindPage(self,pagename,agename=None):
        if agename==None:
            for age in self.ages:
                ret=age.findPage(pagename)
                if ret!=None:
                    return ret
        else:
            age=self.findAge(agename)
            if age==None:
                return None
            return age.findPage(pagename)
        return None


    def findPrp(self,name,agename=None):
        for age in self.ages:
            for page in age.pages:
                if page.name==name and page.prp!=None:
                    return page.prp
