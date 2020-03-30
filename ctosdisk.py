from __future__ import print_function

import os, struct
import sys

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
    (84, 2, "AllFileHeaderPageOffset"),
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
    # I hate unicode
    b=bytearray(len(dest))
    for i in range(len(dest)):
        b[i] = dest[i]
    dest = b

    #dest = dest.encode("utf-8")
    for field in st:
        (offs, size, name) = field
        v = src[name]
        spec = FieldToSpec(field)
        struct.pack_into(spec, dest, offs + offset, v)

    # unicode hates me too
    s=""
    for i in range(len(dest)):
        s = s + chr(dest[i])
    dest = s

    return dest

def PrintStruct(data, st):
    fields = DecodeStructAsList(data, st)
    for field in fields:
        print("%20s %s" % (field[0], field[1]))

def ComputeVHBChecksum(data):
    w = 0x7C39
    for i in range(127):
        w = w - struct.unpack_from("<H", data, 2*i+2)[0]
    return (w & 0xFFFF)

def LoadVHB(data, which="active"):
    d = DecodeStructAsDict(data, VHB_FIELDS)
    if which == "backup":
        return d
    d = DecodeStructAsDict(data[d["LfaVHB"]:], VHB_FIELDS)
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
            print("Active/Backup VHB Mismatch (field=%s, backup=%s, active=%s)" % (k, v, vhb2[k]), file=sys.stderr)

def ReadMFD(data):
    vhb = LoadVHB(data)
    entries = []

    offs = vhb["LfaMFDbase"]
    for i in range(vhb["CPagedMFD"]):
        offs += 1 # skip the header
        for j in range(14):
            mfdEntry = DecodeStructAsDict(data[offs:], MFD_FIELDS) 

            dirNameLen = ord(mfdEntry["DirectoryName"][0])
            mfdEntry["dirNameStr"] = mfdEntry["DirectoryName"][1:dirNameLen+1]

            dirPassLen = ord(mfdEntry["DirPassword"][0])
            mfdEntry["dirPassStr"] = mfdEntry["DirPassword"][1:dirPassLen+1]

            if (dirNameLen > 0):
                entries.append(mfdEntry)

            offs = offs + 35

        offs = offs + vhb["BytesPerSector"]

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
    offset = vhb["LfaFileHeadersbase"]
    offset = offset + fho*512
    fh = DecodeStructAsDict(data[offset:], FILE_HEADER_FIELDS)

    nameLen = ord(fh["sbFileName"][0])
    name = fh["sbFileName"][1:nameLen+1]
    fh["nameStr"] = name

    extents = []
    for i in range(32):
        sector = struct.unpack_from("<L", fh["rgLfaExtents"], i*4)[0]
        length = struct.unpack_from("<L", fh["rgcbExtents"], i*4)[0]
        if sector != 0:
            extents.append( (sector, length) )

    fh["extents"] = extents

    return fh

def ReadDir(data, name):
    vhb = LoadVHB(data)
    mfd = ReadMFD(data)
    mfdEntry = FindMfd(mfd, name)
    if not mfdEntry:
        print("Failed to find %s in mfd" % name, file=sys.stderr)
        return []

    entries = []
    offs = mfdEntry["LfaDirbase"]
    lastOffs = offs + mfdEntry["CPages"] * vhb["BytesPerSector"]
    while offs < lastOffs:
        if ord(data[offs]) == 0:
            offs += 1
            continue
        nameLen = ord(data[offs])
        offs += 1
        name = data[offs:offs+nameLen]
        offs += nameLen
        fho = struct.unpack_from("<H", data, offs)[0]
        offs += 2

        fh = ReadFileHeader(data, fho)
        if fh["nameStr"] != name:
            print("File header name mismatch %s != %s" % (name, fh["nameStr"]), file=sys.stderr)

        entries.append( {"name": name, "offset": fho, "fh": fh} )

    return entries


def PrintDir(dirEntries):
    print("%-20s %4s %8s %s" % ("NAME", "OFFS", "SIZE", "EXTENTS"))
    for dirEntry in dirEntries:
        print("%-20s %4d %8d" % (dirEntry["name"], dirEntry["offset"], dirEntry["fh"]["cbFile"]), end="")
        for extent in dirEntry["fh"]["extents"]:
            print(" <offs %d, len %d>" % (extent[0], extent[1]), end="")
        print("")


def FindFile(dirEntries, name):
    for dirEntry in dirEntries:
        if dirEntry["name"].lower() == name.lower():
            return dirEntry["fh"]
    return None


def RetrieveContents(data, fh):
    result = ""
    for extent in fh["extents"]:
        start = extent[0]
        end = extent[0] + extent[1]
        result = result + data[start:end]

    result = result[:fh["cbFile"]]

    return result

