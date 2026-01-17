"""
ctos disk structures
Scott Baker, https://www.smbaker.com/

This is basically the result of a thorough read of
http://bitsavers.org/pdf/convergent/manuals_btos/BTOS_CTOS_Disk_Structures.pdf.

For the actual command-line tool, see ctostool.py
"""

from __future__ import print_function

import math
import os, struct
import sys
import itertools
import unicodedata
import string

VHB_FIELDS = [
    (0,  2, "Checksum"),
    (2,  4, "LfaSysImagebase"),
    (6,  2, "CPagesSysImage"),
    (8,  4, "LfaBadBlkbase"),
    (12, 2, "CPagesBadBlk"),
    (14, 4, "LfaCrashDumpbase"),
    (18, 2, "CPagesCrashDump"),
    (20, 13, "VolName"),
    (33, 13, "VolPassword"),
    (46, 4, "LfaVHB"),
    (50, 4, "LfaInitialVHB"),
    (54, 4, "CreationDT"),
    (58, 4, "ModificationDT"),
    (62, 4, "LfaMFDbase"),
    (66, 2, "CPagedMFD"),
    (68, 4, "LfaLogbase"),
    #(70, 2, "Unknown"),  # documentation error?
    (72, 2, "CPagesLog"),
    (74, 2, "CurrentLogPage"),
    (76, 2, "CurrentLogBytes"),
    (78, 4, "LfaFileHeadersbase"),
    (82, 2, "CPagesFilesHeaders"),
    (84, 2, "AltFileHeaderPageOffset"),
    (86, 2, "IFreeFileHeader"),
    (88, 2, "CFreeFileHeaders"),
    (90, 2, "ClusterFactor"),
    (92, 2, "DefaultExtend"),
    (94, 2, "AllocSkipCnt"),
    (96, 4, "LfaAllocBitMapbase"),
    (100, 2, "CPagesAllocBitMap"),
    (102, 2, "LastAllocBitMapPage"),
    (104, 2, "LastAllocWord"),
    (106, 2, "LastAllocBit"),
    (108, 4, "CFreePages"),
    (112, 2, "IDev"),
    (114, 105, "RgLruDirEntries"),
    (219, 2, "MagicWd"), # 0x7C39
    (221, 1, "SysImageBaseSector"),
    (222, 1, "SysImageBaseHead"),
    (223, 2, "SysImageBaseCylinder"),
    (225, 2, "SysImageMaxPageCount"),
    (227, 1, "BadBlkBaseSector"),
    (228, 1, "BadBlkBaseHead"),
    (229, 2, "BadBlkBaseCylinder"),
    (231, 2, "BadBlkBaseMaxPageCouint"),
    (233, 1, "DumpBaseSector"),
    (234, 1, "DumpBaseHead"),
    (235, 2, "DumpBaseCylinder"),
    (237, 2, "DumpBaseMaxPageCount"),
    (239, 2, "BytesPerSector"),
    (241, 2, "SectorsPerTrack"),
    (243, 2, "TracksPerCylinder"),
    (245, 2, "CylindersPerDisk"),
    (247, 1, "InterleaveFactor"),
    (248, 2, "SectorSize"),
    (250, 1, "SpiralFactor"),
    (251, 1, "StartingSector"),
    (252, 4, "Reserved")]

MFD_FIELDS = [
    (0, 13, "DirectoryName"),
    (13, 13, "DirPassword"),
    (26, 4, "LfaDirbase"),
    (30, 2, "CPages"),
    (32, 1, "DefaultAccessCode"),
    (33, 2, "LruCnt")
]

MFD_SECTOR_FIELDS = [
    (0, 2, "Header"),
    (2, 490, "rgMFDEntries")
]

DIR_FIELDS = [
    (0, 1, "cbFileName"),
    (1, None, "FileName"),  # length is set by the first byte
    (None, 2, "FileHeaderOffset")  # offset is after the previous field
]

FILE_HEADER_FIELDS = [
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
    (119, 2, "iFreeRun"),
    (121, 128, "rgLfaExtents"),
    (249, 128, "rgcbExtents"),
    (377, 71, "Reserved"),
    (448, 64, "AppSpecific")
]

BAD_BLOCK_FIELDS = [
    (0, 128, "RgbBadSector"),
    (128, 128, "RgbBadHead"),
    (256, 256, "RgbBadCylinder")
]

def escape2(text):
    import itertools
    # Use characters of control category
    nonprintable = itertools.chain(range(0x00,0x20),range(0x7f,0xa0))
    # Use translate to remove all non-printable characters
    return text.translate({character:None for character in nonprintable})

def escape(my_string):
        return ''.join([x if x in string.printable else '' for x in my_string])

def byteArraySliceToString(ba, start, end):
    result = ""
    for b in ba[start:end]:
        result = result + chr(b)
    return result

def SanityCheck(st):
    offs = 0
    for field in st:
        if field[0] != offs:
            print("Sanity Check: Incorrect offs %d != %d" % (field, offs), file=sys.stderr)
        offs = offs + field[1]

def SanityCheckAll():
    SanityCheck(VHB_FIELDS)
    SanityCheck(MFD_FIELDS)
    SanityCheck(MFD_SECTOR_FIELDS)
    # SanityCheck(DIR_FIELDS)
    SanityCheck(FILE_HEADER_FIELDS)
    SanityCheck(BAD_BLOCK_FIELDS)

def FieldToSpec(field):
    if field[1] == 1:
        spec = "<B"
    elif field[1] == 2:
        spec = "<H"
    elif field[1] == 4:
        spec = "<L"
    else:
        spec = "%ds" % field[1]
    return spec

def DecodeStructAsList(data, st):
    result = []
    offs = 0
    for field in st:
        spec = FieldToSpec(field)
        result.append( (field[2], struct.unpack_from(spec, data, offs)[0]) )
        offs = offs + field[1]

    return result

def DecodeStructAsDict(data, st):
    resultList = DecodeStructAsList(data, st)
    result = {}
    for item in resultList:
        result[item[0]] = item[1]
    return result

def EncodeStruct(src, dest, st, offset=0):
    #dest = dest.encode("utf-8")
    for field in st:
        (offs, size, name) = field
        v = src[name]
        spec = FieldToSpec(field)
        struct.pack_into(spec, dest, offs + offset, v)

    return dest

def PrintStruct(data, st):
    fields = DecodeStructAsList(data, st)
    for field in fields:
        print("%20s %s" % (field[0], escape(str(field[1]))))

def ComputeVHBChecksum(data):
    w = 0x7C39
    for i in range(127):
        w = w - struct.unpack_from("<H", data, 2*i+2)[0]
    return (w & 0xFFFF)

cpdwarn = False

def LoadVHB(data, which="active"):
    d = DecodeStructAsDict(data, VHB_FIELDS)
    if which == "backup":
        return d
    d = DecodeStructAsDict(data[d["LfaVHB"]:], VHB_FIELDS)
    if d["CylindersPerDisk"] == 2:
        # my AWS formatted the disk like this??
        global cpdwarn
        if not cpdwarn:
          print("Warning: CylindersPerDisk is very low (%d). Changing to 77." % d["CylindersPerDisk"] , file=sys.stderr)
          cpdwarn = True
        d["CylindersPerDisk"] = 77
    return d

def VerifyVHBChecksum(data, which="backup"):
    d = DecodeStructAsDict(data, VHB_FIELDS)
    w = ComputeVHBChecksum(data)
    if d["Checksum"] != w:
        print("Checksum mismatch in %s VHD %X != %X" % (which, d["Checksum"], w), file=sys.stderr)

def VerifyActiveVHB(data):
    vhb = DecodeStructAsDict(data, VHB_FIELDS)
    vhb2 = DecodeStructAsDict(data[vhb["LfaVHB"]:], VHB_FIELDS)
    VerifyVHBChecksum(data[vhb["LfaVHB"]:], "active")

    for (k, v) in vhb.items():
        if vhb2[k] != v:
            print("Active/Backup VHB Mismatch (field=%s, backup=%s, active=%s)" % (k, escape(str(v)), escape(str(vhb2[k]))), file=sys.stderr)

def ReadMFD(data, vhb=None):
    if not vhb:
        vhb = LoadVHB(data)
    entries = []

    offs = vhb["LfaMFDbase"]
    blkoffs = offs
    for i in range(vhb["CPagedMFD"]):
        offs = blkoffs + 1 # skip the header
        for j in range(14):
            mfdEntry = DecodeStructAsDict(data[offs:], MFD_FIELDS) 

            dirNameLen = ord(mfdEntry["DirectoryName"][0])
            mfdEntry["dirNameStr"] = mfdEntry["DirectoryName"][1:dirNameLen+1]

            dirPassLen = ord(mfdEntry["DirPassword"][0])
            mfdEntry["dirPassStr"] = mfdEntry["DirPassword"][1:dirPassLen+1]

            if (dirNameLen > 0):
                entries.append(mfdEntry)

            offs = offs + 35

        blkoffs = blkoffs + vhb["BytesPerSector"]

    return entries

def FindMfd(mfd, name):
    for mfdEntry in mfd:
        if mfdEntry["dirNameStr"].lower() == name.lower():
            return mfdEntry
    return None

def PrintMfd(mfd):
    for mfdEntry in mfd:
        print("%-13s %-13s %d (%d pages)" % (mfdEntry["dirNameStr"], mfdEntry["dirPassStr"], mfdEntry["LfaDirbase"], mfdEntry["CPages"]))

def ReadFileHeader(data, fho):
    vhb = LoadVHB(data)
    offset = vhb["LfaFileHeadersbase"] + fho*512

    if offset>len(data):
        # XXX smbaker: maybe an exception would be better
        # XXX this was observed on scott's AWS disk image
        print("ERROR: File header offset %d out of range (file header number %d)" % (offset, fho), file=sys.stderr)
        return None

    fh = DecodeStructAsDict(data[offset:], FILE_HEADER_FIELDS)

    nameLen = ord(fh["sbFileName"][0])
    name = fh["sbFileName"][1:nameLen+1]
    fh["nameStr"] = name

    extents = []
    for i in range(32):
        if i >= fh["iFreeRun"]:
            # iFreeRun contains the index of the next available entry in the extent list
            continue
        sector = struct.unpack_from("<L", fh["rgLfaExtents"], i*4)[0]
        length = struct.unpack_from("<L", fh["rgcbExtents"], i*4)[0]
        if sector != 0:
            extents.append( (sector, length) )

    fh["vhb"] = vhb
    fh["extents"] = extents
    fh["fho"] = fho
    fh["offset"] = vhb["LfaFileHeadersbase"] + fho*512    

    return fh

def EncodeExtents(fh):
    # clear existing extents
    lfas = bytearray(fh["rgLfaExtents"])
    cbs = bytearray(fh["rgcbExtents"])
    for i in range(32):
        struct.pack_into("<L", lfas, i*4, 0)
        struct.pack_into("<L", cbs, i*4, 0)

    for i, extent in enumerate(fh["extents"]):
        struct.pack_into("<L", lfas, i*4, extent[0])
        struct.pack_into("<L", cbs, i*4, extent[1])

    fh["iFreeRun"] = len(fh["extents"])

    fh["rgLfaExtents"] = bytes(lfas)
    fh["rgcbExtents"] = bytes(cbs)

def MarkFHDeleted(fh):
    # deleted file header is indicated by 0 in name length field
    fh["sbFileName"] = b'\x00' + fh["sbFileName"][1:]

# ReadDirOld - I believe this was wrong, and the wrongness was found on my AWS disk image
# The directory isn't a series of contiguous sectors, but rather a series of pages, each starting
# with a byte (meaning unknown). When we hit the first 0 on a page, we are done with it.

def ReadDirOld(data, name, vhb=None, mfd=None):
    if not vhb:
        vhb = LoadVHB(data)
    if not mfd:
        mfd = ReadMFD(data, vhb=vhb)

    mfdEntry = FindMfd(mfd, name)
    if not mfdEntry:
        print("Failed to find %s in mfd" % name, file=sys.stderr)
        return []

    entries = []
    offs = mfdEntry["LfaDirbase"]

    lastOffs = offs + mfdEntry["CPages"] * vhb["BytesPerSector"]

    while offs < lastOffs:
        if data[offs] == 0x00:
            offs += 1
            continue

        if data[offs] == 0xFF:
            # not sure what FF is for, but found it in the OS dir of my copy1 image
            offs += 1
            continue

        nameLen = data[offs]
        offs += 1
        name = data[offs:offs+nameLen]
        offs += nameLen
        fho = struct.unpack_from("<H", data, offs)[0]
        offs += 2

        fh = ReadFileHeader(data, fho)
        if fh is None:
            continue

        if fh["nameStr"] != name:
            print("File header name mismatch %s != %s" % (name, fh["nameStr"]), file=sys.stderr)

        entries.append( {"name": name, "offset": fho, "fh": fh} )

    return entries

def ReadDir(data, name, vhb=None, mfd=None):
    if not vhb:
        vhb = LoadVHB(data)
    if not mfd:
        mfd = ReadMFD(data, vhb=vhb)

    mfdEntry = FindMfd(mfd, name)
    if not mfdEntry:
        print("Failed to find %s in mfd" % name, file=sys.stderr)
        return []

    entries = []
    pageOffs = mfdEntry["LfaDirbase"]

    for i in range(0, mfdEntry["CPages"]):
        # dir entries always start after the first byte
        offs = pageOffs + 1
        # lastOffs is the end of this page
        lastOffs = offs + vhb["BytesPerSector"]
        while offs < lastOffs:
            if data[offs] == 0x00:
                break

            nameLen = data[offs]
            offs += 1
            name = byteArraySliceToString(data,offs,offs+nameLen)
            offs += nameLen
            fho = struct.unpack_from("<H", data, offs)[0]
            offs += 2

            fh = ReadFileHeader(data, fho)
            if fh is None:
                continue

            if fh["nameStr"] != name:
                print("File header name mismatch %s != %s" % (name, fh["nameStr"]), file=sys.stderr)

            entries.append( {"name": name, "offset": fho, "fh": fh} )

        # point to the next page offset
        pageOffs = pageOffs + vhb["BytesPerSector"]

    return entries

def RemoveDirEntry(data, directory, nameToDelete, vhb=None, mfd=None):
    if not vhb:
        vhb = LoadVHB(data)
    if not mfd:
        mfd = ReadMFD(data, vhb=vhb)

    mfdEntry = FindMfd(mfd, directory)
    if not mfdEntry:
        print("Failed to find %s in mfd" % name, file=sys.stderr)
        return []

    pageOffs = mfdEntry["LfaDirbase"]

    for i in range(0, mfdEntry["CPages"]):
        # dir entries always start after the first byte
        offs = pageOffs + 1
        # lastOffs is the end of this page
        lastOffs = offs + vhb["BytesPerSector"]
        while offs < lastOffs:
            if data[offs] == 0x00:
                break

            nameLen = data[offs]
            offs += 1
            name = byteArraySliceToString(data,offs,offs+nameLen)
            offs += nameLen
            fho = struct.unpack_from("<H", data, offs)[0]
            offs += 2

            if name == nameToDelete:
                # shift remaining entries up
                entrySize = 1 + nameLen + 2
                nextEntryOffs = offs
                while nextEntryOffs < lastOffs:
                    data[offs - entrySize] = data[nextEntryOffs]
                    offs += 1
                    nextEntryOffs += 1
                # zero out the remaining bytes at the end
                for j in range(offs - entrySize, lastOffs):
                    data[j] = 0x00
                # done with this page
                break

        # point to the next page offset
        pageOffs = pageOffs + vhb["BytesPerSector"]

    return 

def PrintDir(dirEntries):
    print("%-20s %4s %8s %s" % ("NAME", "OFFS", "SIZE", "EXTENTS"))
    for dirEntry in dirEntries:
        print("%-20s %4d %8d" % (escape(dirEntry["name"]), dirEntry["offset"], dirEntry["fh"]["cbFile"]), end="")
        for extent in dirEntry["fh"]["extents"]:
            print(" <offs %d, len %d>" % (extent[0], extent[1]), end="")
        print("")


def FindFile(dirEntries, name):
    for dirEntry in dirEntries:
        if dirEntry["name"].lower() == name.lower():
            return dirEntry["fh"]
    return None

def BitmapSize(vhb):
    nSectors = vhb["SectorsPerTrack"] * vhb["TracksPerCylinder"] * vhb["CylindersPerDisk"]
    bitmapSize = int(math.ceil(nSectors/8.0))
    return bitmapSize

def ReadAllocationBitmap(data):
    # 1 = sector is free, 0 = sector is allocated
    vhb = LoadVHB(data)
    startOffset = vhb["LfaAllocBitMapbase"]
    nSectors = vhb["SectorsPerTrack"] * vhb["TracksPerCylinder"] * vhb["CylindersPerDisk"]
    bitmapSize = BitmapSize(vhb)
    bitmap = []
    for b in data[startOffset:startOffset+bitmapSize]:
        for i in range(8):
            bitmap.append(b & 1)
            b = b >> 1
    bitmap = bitmap[:nSectors]
    return bitmap

def WriteAllocationBitmap(data, bitmap):
    vhb = LoadVHB(data)
    startOffset = vhb["LfaAllocBitMapbase"]
    bitmapSize = BitmapSize(vhb)
    for i in range(bitmapSize):
        b = 0
        for j in range(8):
            bitIndex = i*8 + j
            if bitIndex < len(bitmap):
                b = b | (bitmap[bitIndex] << j)
        struct.pack_into("<B", data, startOffset + i, b)

def GetFreeSector(bitmap):
    for i, bit in enumerate(bitmap):
        if bit == 1:
            bitmap[i] = 0  # Set the bit to allocated
            return i
    return None

def RetrieveContents(data, fh):
    result = ""
    for extent in fh["extents"]:
        start = extent[0]
        end = extent[0] + extent[1]
        result = result + data[start:end]

    result = result[:fh["cbFile"]]

    return result

def TruncateContents(data, fh, bitmap):
    for extent in fh["extents"]:
        (sectorAddr, length) = extent
        sector = sectorAddr/512
        count =  int(math.ceil(length/512.0))
        for i in range(count):
            bitmap[sector + i] = 1
    fh["extents"] = []

def Delete(data, directory, fh, bitmap):
    TruncateContents(data, fh, bitmap)
    WriteAllocationBitmap(data, bitmap)
    RemoveDirEntry(data, directory, fh["nameStr"])
    MarkFHDeleted(fh)
    UpdateFHChecksum(fh)
    EncodeStruct(fh, data, FILE_HEADER_FIELDS, fh["offset"])

    # secondary file headers are a pain...
    if fh["vhb"]["AltFileHeaderPageOffset"] > 0:
        secondaryFho = fh["fho"] + fh["vhb"]["AltFileHeaderPageOffset"]
        secondaryFh = ReadFileHeader(data, secondaryFho)
        if secondaryFh["FileHeaderNumber"] == fh["FileHeaderNumber"]:
            MarkFHDeleted(secondaryFh)
            UpdateFHChecksum(secondaryFh)
            EncodeStruct(secondaryFh, data, FILE_HEADER_FIELDS, secondaryFh["offset"])

    errors = CheckDisk(data)
    if errors != 0:
        print("Error: disk check failed after ReplaceContents", file=sys.stderr)
        sys.exit(-1)

def ReplaceContents(data, fh, bitmap, srcData):
    TruncateContents(data, fh, bitmap)

    origSrcData = srcData

    newLen = len(srcData)
    curExtent = None
    while len(srcData) > 0:
        sector = GetFreeSector(bitmap)
        if sector is None:
            print("Error: no free sectors available", file=sys.stderr)
            sys.exit(-1)

        sectorAddr = sector*512

        thisData = srcData[:512]
        srcData = srcData[512:]

        if curExtent != None and (curExtent[0] + curExtent[1] == sectorAddr):
            # extend current extent
            curExtent[1] += 512
            fh["extents"][-1] = curExtent
        else:
            curExtent = [sectorAddr, 512]
            fh["extents"].append(curExtent)

        fh["cbFile"] = newLen

        struct.pack_into("<512s", data, sectorAddr, thisData.ljust(512, '\x00'))

    EncodeExtents(fh)
    UpdateFHChecksum(fh)
    EncodeStruct(fh, data, FILE_HEADER_FIELDS, fh["offset"])

    WriteAllocationBitmap(data, bitmap)

    errors = CheckDisk(data)
    if errors != 0:
        print("Error: disk check failed after ReplaceContents", file=sys.stderr)
        sys.exit(-1)

    fh = ReadFileHeader(data, fh["fho"])
    writtenContents = RetrieveContents(data, fh)
    if writtenContents != origSrcData:
        print("Error: contents verification failed after ReplaceContents", file=sys.stderr)
        #open("/tmp/one","w").write(writtenContents)
        #open("/tmp/two","w").write(origSrcData)
        sys.exit(-1)

def CheckFHChecksum(fh):
    data = bytearray(512)
    EncodeStruct(fh, data, FILE_HEADER_FIELDS, 0)
    w = fh["vhb"]["MagicWd"]
    for i in range(256):
        w = (w - struct.unpack_from("<H", data, 2*i)[0]) & 0xFFFF
    return (w==0)

def UpdateFHChecksum(fh):
    data = bytearray(512)
    fh["Checksum"] = 0
    EncodeStruct(fh, data, FILE_HEADER_FIELDS, 0)
    w = 0
    for i in range(0,256):
        w = (w + struct.unpack_from("<H", data, 2*i)[0]) & 0xFFFF
    fh["Checksum"] = (fh["vhb"]["MagicWd"] - w) & 0xFFFF

def CheckDisk(data):
    vhb = LoadVHB(data)
    bitmap = ReadAllocationBitmap(data)
    mfd = ReadMFD(data, vhb=vhb)
    errors = 0

    foundBitmap = [1]*len(bitmap)

    foundHeaders = {}

    foundBitmap[0] = 0  # sector 0 is always allocated

    bitmapSectors = int(math.ceil(BitmapSize(vhb)/512.0))
    if BitmapSize(vhb) % 512 == 0:
        # possible bug? Noticed one additional page if bitmap consumed the entire last sector
        bitmapSectors += 1
    for i in range(0, bitmapSectors):
        foundBitmap[vhb["LfaAllocBitMapbase"]/512 + i] = 0

    foundBitmap[vhb["LfaVHB"]/512] = 0

    for mfdEntry in mfd:
        for i in range(0, mfdEntry["CPages"]):
            foundBitmap[mfdEntry["LfaDirbase"]/512 + i] = 0

        dirEntries = ReadDir(data, mfdEntry["dirNameStr"], vhb=vhb, mfd=mfd)
        for dirEntry in dirEntries:
            fh = dirEntry["fh"]

            if not CheckFHChecksum(fh):
                print("Error: checksum failure in file header for fn=%s" % fh["nameStr"], file=sys.stderr)
                errors += 1

            foundHeaders[fh["fho"]] = fh

            if vhb["AltFileHeaderPageOffset"] > 0:
                secondaryFho = fh["fho"] + vhb["AltFileHeaderPageOffset"]
                secondaryFh = ReadFileHeader(data, secondaryFho)
                if secondaryFh["FileHeaderNumber"] == fh["FileHeaderNumber"]:
                    foundHeaders[secondaryFho] = secondaryFh

            for extent in fh["extents"]:
                start = extent[0]
                end = extent[0] + extent[1]
                startSector = start/512
                endSector = int(math.ceil(end/512.0))
                for sector in range(startSector, endSector):
                    if foundBitmap[sector] == 0:
                        print("Error: sector %d allocated more than once, fn=%s" % (sector, fh["nameStr"]), file=sys.stderr)
                        errors += 1
                    foundBitmap[sector] = 0
                    if bitmap[sector] != foundBitmap[sector]:
                        print("Error: allocation bitmap mismatch at sector %d: bitmap=%d, found=%d, fn=%s" % (sector, bitmap[sector], foundBitmap[sector], fh["nameStr"]), file=sys.stderr)
                        errors += 1


    for i in range(0, len(bitmap)):
        if foundBitmap[i]!=0 and bitmap[i] != foundBitmap[i]:
            print("Error: allocation bitmap mismatch at sector %d: bitmap=%d, found=%d" % (i, bitmap[i], foundBitmap[i]), file=sys.stderr)
            errors += 1

    #XXX some drama here around secondary file headers
    for fho in range(0, vhb["CPagesFilesHeaders"]):
        fh = ReadFileHeader(data, fho)
        if fh["sbFileName"][0] == '\0':
            continue
        if fho not in foundHeaders:
            print("Error: Found orphaned file header %d name = %s" % (fho, fh["nameStr"]), file=sys.stderr)
            errors += 1

    return errors

def DumpEverything(data):
    vhb = LoadVHB(data)

    allocated = 0
    bitmap = ReadAllocationBitmap(data)
    for bit in bitmap:
        if bit:
            allocated += 1

    print("\nAllocation Bitmap Bits Set: %d sectors free" % allocated)

    mfd = ReadMFD(data, vhb=vhb)
    print("\n== MFD:")
    PrintMfd(mfd)

    for mfdEntry in mfd:
        print("\n-- Dir %s" % mfdEntry["dirNameStr"])
        dirEntries = ReadDir(data, mfdEntry["dirNameStr"], vhb=vhb, mfd=mfd)
        PrintDir(dirEntries)
