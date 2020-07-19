""" ctostape.py
    Scott Baker, http://www.smbaker.com/

    Parse a convergent tape archive.

    The idea here is to make a copy of your tape on a linux box using
    something like dd. I happened to have a couple archive SCSI tape
    drives that I found on ebay that made short work of this.

    Once, you have the image, use this tool to see what's in it.
"""

from ctosdisk import *

TAPE_FILE_HEADER_FIELDS = [
    (0, 2, "Checksum"),
    (2, 2, "FileHeaderPageNumber"),
    (4, 51, "sbFileName"),
    (55, 13, "sbFileNamePassword"),
    (68, 13, "sbDirectoryName"),
    (81, 2, "FileHeaderNumber"),
    (83, 2, "ExtensionFileHeaderNumber"),
    (85, 1, "bHeaderSequenceNumber"),
    (86, 1, "bFileClass"),
    (87, 1, "bAccessProtection"),
    (88, 4, "lfaDirPage"),
    (92, 4, "CreationDate"),
    (96, 4, "ModificationDate"),
    (100, 4, "AccessDate"),
    (104, 4, "ExpirationDate"),
    (108, 1, "fNoSave"),
    (109, 1, "fNoDirPrint"),
    (110, 1, "fNoDelete"),
    (111, 4, "cbFile"),
    (115, 4, "defaultExpansion"),
    (119, 2, "iFreeRun")]

class TapeReader():
    def __init__(self):
        self.TapeHeader = {}
        self.RecLen = None
        self.RecQuadID = None
        self.RecBuf = ""
        self.AbsPos = 0
        self.RecStart = 0
        self.Started = False

    def TryDecodeFileHeader(self, data):
        if self.RecLen == 256:
            fh = DecodeStructAsDict(data, TAPE_FILE_HEADER_FIELDS)

            nameLen = ord(fh["sbFileName"][0])
            if (nameLen<1) or (nameLen>50):
                return None

            name = fh["sbFileName"][1:nameLen+1]
            fh["nameStr"] = name

            passLen = ord(fh["sbFileNamePassword"][0])
            if (passLen>13):
                return None

            passw = fh["sbFileNamePassword"][1:passLen+1]
            fh["passStr"] = passw

            dirLen = ord(fh["sbDirectoryName"][0])
            if (dirLen<1) or (dirLen>13):
                return None

            dir = fh["sbDirectoryName"][1:dirLen+1]
            fh["dirStr"] = dir

            return fh


    def HandleRecord(self):
        #print "Record len=%d, quadID=%08X, AbsPos=%X. RecStart=%X" % (self.RecLen, self.RecQuadID, self.AbsPos, self.RecStart)
        fh = self.TryDecodeFileHeader(self.RecBuf[6:])
        if fh is not None:
            print "%s/%s" % (fh["dirStr"], fh["nameStr"])


    def StartNewRecord(self):
        self.Started = True
        self.RecBuf = ""
        self.RecLen = None
        self.RecQuadID = None
        self.RecStart = self.AbsPos + 1

    def HandleByte(self, b):
        self.RecBuf = self.RecBuf + b
        if len(self.RecBuf) == 2:
            self.RecLen = struct.unpack_from("<H", self.RecBuf, 0)[0]
            #print "RecLen %d, AbsPos=%X" % (self.RecLen, self.AbsPos)
            if self.RecLen == 0:
                print "XXX Bad Block (RecLen=0) At RecStart=%X" % (self.AbsPos-2)
            if self.RecLen>512:
                print "XXX Bad Block (RecLen=%d) At RecStart=%X" % (self.AbsPos-2, self.RecLen)
        elif len(self.RecBuf) == 6:
            self.RecQuadID = struct.unpack_from("<L", self.RecBuf, 2)[0]
        elif (self.RecLen!=None) and (len(self.RecBuf) == self.RecLen+6):
            self.HandleRecord()
            self.StartNewRecord()

    def ForceFinishRecord(self):
        if not self.Started:
            return
        if len(self.RecBuf) < 6:
            #print "Non-record bytes at, RecStart=%X" % self.RecStart
            self.StartNewRecord()
        elif len(self.RecBuf) != self.RecLen:
            print "Short record, RecStart=%X, len=%d, RecLen=%X" % (self.RecStart, len(self.RecBuf), self.RecLen)
            self.StartNewRecord()

    def HandleBlock(self, data, offs):
        pointer = struct.unpack_from("<H", data, offs+6)[0]
        blockOffs = 8
        self.AbsPos = offs + blockOffs
        if pointer>0:
            for i in range(0, pointer):
                self.HandleByte(data[offs+blockOffs+i])
                self.AbsPos += 1
            blockOffs = pointer+8
            self.AbsPos = offs + blockOffs

        self.ForceFinishRecord()

        #print "offs=%X, blockOffs=%X" % (offs, blockOffs)
        while blockOffs<1536:
            self.HandleByte(data[offs+blockOffs])
            blockOffs += 1
            self.AbsPos += 1

            # Don't start a new record if it would be empty
            if (self.RecLen == None) and (blockOffs>=1532):
                return

    def ReadTape(self, data):
        self.tapeHeader = {"name": data[0:55],
                    "date": data[55:80],
                    "vol": data[80:160]}

        offs = 512
        tapeLen = len(data)
        blockNum = 0
        while (offs<tapeLen):
            checkWord = struct.unpack_from("<H", data, offs)[0]

            if (checkWord != 0xa13d):
                print "Likely bad block %d, checkword=%d, offs=%X, tapeLen=%X" % (blockNum, checkWord, offs, tapeLen)
            else:
                self.HandleBlock(data, offs)

            #print("%d %d %d" % (blockNum, checkWord, offs))

            offs = offs + 1536
            blockNum = blockNum + 1

def main():
    if len(sys.argv)<2:
        print "syntax: ctostape <image-name>"
        sys.exit(-1)

    fn = sys.argv[1]

    data = open(fn).read()
    TapeReader().ReadTape(data)

if __name__ == "__main__":
    main()




