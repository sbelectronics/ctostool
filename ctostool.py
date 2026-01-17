"""
ctostool
(c) Scott Baker, http://www.smbaker.com/

Tool for inspecting CTOS floppy images. Examples:

    # dump the mfd, directory, vhds, etc
    ctostool.py test.img dump 

    # return stats about a file
    ctostool.py test.img stat Sys Install.Sub 

    # extract a file to stdout
    ctostool.py test.img extract Sys Install.sub
"""

from __future__ import print_function

from ctosdisk import *
import argparse
import ConfigParser
import sys
import string

DEFAULT_CONFIG_FILE = "ctostool.conf"

def hex_escape(s):
    printable = string.ascii_letters + string.digits + string.punctuation + ' '
    return ''.join(c if c in printable else r'\x{0:02x}'.format(ord(c)) for c in s)

def parse_args():
    defaults = {}

    # Get the config file argument

    conf_parser = argparse.ArgumentParser(add_help=False)
    _help = 'Config file name (default: %s)' % DEFAULT_CONFIG_FILE
    conf_parser.add_argument(
        '-c', '--conf_file', dest='conf_file',
        default=DEFAULT_CONFIG_FILE,
        type=str,
        help=_help)
    args, remaining_argv = conf_parser.parse_known_args()

    # Load the config file

    if args.conf_file:
        if not os.path.exists(args.conf_file):
            if args.conf_file!=DEFAULT_CONFIG_FILE:
                print("Config file %s does not exist. Not reading config." % args.conf_file, file=sys.stderr)
        else:
            config = ConfigParser.SafeConfigParser()
            config.read(args.conf_file)
            defaults.update(dict(config.items("defaults")))

    # Parse the rest of the args

    parser = argparse.ArgumentParser(parents=[conf_parser])

    _help = 'Escape non-printable characters (default: %0.1f)' % False
    parser.add_argument(
        '-e', '--escape', dest='escape',
        default=False,
        action="store_true",
        help=_help)

    _help = 'Write output to a filename (default: write to stdout)'
    parser.add_argument(
        '-o', '--output', dest='output',
        default="",
        action="store",
        type=str,
        help=_help)

    #_help = 'Some help (default: %0.1f)' % SOME_DEFAULT
    #parser.add_argument(
    #    '-s', '--someoption', dest='someoption',
    #    default=defaults["someoption"],
    #    help=_help)

    parser.add_argument("imagefilename")
    parser.add_argument("command")
    parser.add_argument("args", nargs="*")

    args = parser.parse_args()

    return args

def makeSafeFileName(fn):
    return fn.replace(">", "_").replace("/", "_")

def getOutputFile(args):
    if args.output == "":
        return sys.stdout
    return open(args.output, "wb")

def loadFile(args):
    f = open(args.imagefilename, "rb")
    data = f.read()
    f.close()
    data = bytearray(data)
    return data

def saveFile(args, data):
    f = open(args.imagefilename, "wb")
    f.write(data)
    f.close()

def openFile(data, dirName, fileName, vhb=None, mfd=None, dir=None):
    if not vhb:
        vhb=LoadVHB(data, vhb)
    if not mfd:
        mfd=ReadMFD(data, vhb=vhb)
    if not dir:
        dir=ReadDir(data, dirName, vhb=vhb, mfd=mfd)

    if dir is None:
        print("Error: Dir Not Found: %s" % dirName, file=sys.stderr)
        sys.exit(-1)

    fh = FindFile(dir, fileName)

    if fh is None:
        print("Error: File Not Found: %s" % fileName, file=sys.stderr)
        sys.exit(-1)

    return fh

def chkdsk(args):
    data = loadFile(args)
    errors = CheckDisk(data)
    print("Checkdisk Complete, %d errors" % errors)


def dump(args):
    data = loadFile(args)
    print("== Backup VHB")
    PrintStruct(data, VHB_FIELDS)

    print("\n== Active VHB")
    print(LoadVHB(data, which="backup")["LfaVHB"])
    PrintStruct(data[LoadVHB(data, which="backup")["LfaVHB"]:], VHB_FIELDS)

    VerifyVHBChecksum(data)
    VerifyActiveVHB(data)

    DumpEverything(data)


def listdir(args):
    if len(args.args)<1:
        print("Error: required argument <directory> is missing", file=sys.stderr)
        sys.exit(-1)

    data = loadFile(args)

    VerifyVHBChecksum(data)

    for arg in args.args:
        dirEntries = ReadDir(data, arg)
        PrintDir(dirEntries)

def dumpbitmap(args):
    data = loadFile(args)
    bitmap = ReadAllocationBitmap(data)
    for i, bit in enumerate(bitmap):
        print("%d:%d" % (i, bit))


def extract(args):
    if len(args.args)<2:
        print("Error: required argument <directory> and <filename> are missing", file=sys.stderr)
        sys.exit(-1)

    data = loadFile(args)
    fh = openFile(data, args.args[0], args.args[1])

    contents = RetrieveContents(data, fh)

    if args.escape:
        contents = hex_escape(contents)

    getOutputFile(args).write(contents)

def replace(args):
    if len(args.args)<3:
        print("Error: required argument <directory> and <filename> and <srcfile> are missing", file=sys.stderr)
        sys.exit(-1)

    data = loadFile(args)
    fh = openFile(data, args.args[0], args.args[1])

    bitmap = ReadAllocationBitmap(data)

    srcData = open(args.args[2], "rb").read()
    ReplaceContents(data, fh, bitmap, srcData)

    saveFile(args, data)

def delete(args):
    if len(args.args)<3:
        print("Error: required argument <directory> and <filename> and <srcfile> are missing", file=sys.stderr)
        sys.exit(-1)

    data = loadFile(args)
    fh = openFile(data, args.args[0], args.args[1])

    bitmap = ReadAllocationBitmap(data)

    srcData = open(args.args[2], "rb").read()
    ReplaceContents(data, fh, bitmap, srcData)

    saveFile(args, data)
    
def extractAll(args):
    if len(args.args)<1:
        print("Error: required argument <destdir> is missing", file=sys.stderr)
        sys.exit(-1)

    rootDir = args.args[0]

    data = loadFile(args)

    vhb = LoadVHB(data)
    mfd = ReadMFD(data, vhb=vhb)

    for mfdEntry in mfd:
        dirName = mfdEntry["dirNameStr"]
        if dirName == "." or dirName == "..":
            print("Skipping directory %s" % dirName, file=sys.stderr)
            continue

        destDir = os.path.join(rootDir, dirName)
        if not os.path.exists(destDir):
            os.makedirs(destDir)

        dirEntries = ReadDir(data, dirName, vhb=vhb, mfd=mfd)
        for dirEntry in dirEntries:
            fileName = dirEntry["name"]
            if fileName == "." or fileName=="..":
                print("Skipping file %s % fileName", file=sys.stderr)
                cotninue

            fh = openFile(data, dirName, fileName, vhb=vhb, mfd=mfd, dir=dirEntries)
            contents = RetrieveContents(data, fh)

            destFileName = os.path.join(destDir, makeSafeFileName(fileName))
            print("Creating %s" % destFileName)
            open(destFileName, "w").write(contents)

def stat(args):
    if len(args.args)<2:
        print("Error: required argument <directory> and <filename> are missing", file=sys.stderr)
        sys.exit(-1)

    data = loadFile(args)
    fh = openFile(data, args.args[0], args.args[1])

    for k, v in fh.items():
        if k in ["sbFileName", "AppSpecific", "rgcbExtents", "rgLfaExtents"]:
            # nonprintable things
            continue
        print("%-20s %s" % (k, v))

def setgeometry(args):
    if len(args.args)<4:
        print("Error: required arguments <cylinders> <heads> <sectors> <bytesPerSector> are missing", file=sys.stderr)
        sys.exit(-1)

    cylinders = int(args.args[0])
    heads = int(args.args[1])
    sectors = int(args.args[2])
    bytesPerSector = int(args.args[3])

    data = loadFile(args)

    for (vhbName,fldName) in [("active", "LfaVHB"), ("backup", "LfaInitialVHB")]:
        vhb = LoadVHB(data, vhbName)
        activeOffs = vhb[fldName]
        vhb["BytesPerSector"] = bytesPerSector
        vhb["SectorsPerTrack"] = sectors
        vhb["TracksPerCylinder"] = heads
        vhb["CylindersPerDisk"] = cylinders
        data = EncodeStruct(vhb, data, VHB_FIELDS, activeOffs)
        vhb["Checksum"] = ComputeVHBChecksum(data[activeOffs:])
        data = EncodeStruct(vhb, data, VHB_FIELDS, activeOffs)

        vhb_test = LoadVHB(data, vhbName)
        if vhb_test != vhb:
            print("Error: mismatch in re-encoded FHB", file=sys.stderr)

    getOutputFile(args).write(data)

def main():
    SanityCheckAll()

    args = parse_args()

    if args.command == "dump":
        dump(args)
    elif args.command == "listdir":
        listdir(args)
    elif args.command == "dumpbitmap":
        dumpbitmap(args)
    elif args.command == "extract":
        extract(args)
    elif args.command == "extractall":
        extractAll(args)
    elif args.command == "stat":
        stat(args)
    elif args.command == "setgeometry":
        setgeometry(args)
    elif args.command == "replace":
        replace(args)
    elif args.command == "chkdsk":
        chkdsk(args)
    else:
        print("Unrecognized command: %s" % args.command, file=sys.stderr)

if __name__ == "__main__":
    main()