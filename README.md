# ctostool
## (c) Scott Baker, https://www.smbaker.com/

This is a tool for reading and manipulating CTOS format floppy disk images. CTOS (aka BTOS) was an operating system used back in the 1980s, and perhaps into the early 1990s.  Bitsavers has a whole lot of CTOS images online, and even a VirtualBox VM with a CTOS install.

Machines that natively ran CTOS back in the day were often built/distributed by Convergent Technologies, Burroughs, and/or Unisys

## Installation

The tool is written in python, you'll need python 2.7 or a 3.x variant of python to run it.

## Usage

This is a command line tool. Usage examples are:

```bash
# dump the mfd, directory, vhds, etc
ctostool.py test.img dump 

# return stats about a file
ctostool.py test.img stat Sys Install.Sub 

# extract a file to stdout
ctostool.py test.img extract Sys Install.sub

# extract all files and folders to output folder
ctostool.py test.img extractall -o output

# change the geometry to 80 tracks, 2 heads, 16 secotrs, 256 b/sector
ctostool.py test.img setgeometry 80 2 16 256 > new.img
```

## Changing Geometry

One of the purposes behind this tool was to get some 3.5" 1.44MB images to work on my NGEN workstation which only understands DS/HD disks of about 640K or so. To do this, I booted up the Bitsavers CTOS Oracle VM, and copied the 1.44MB image to a 720K image (720K was the closes I could get to the format I desired). Then I modified the geometry from 80/2/9/512 to 90/2/16/256. Using HxC tools I was able to read the raw file and write it to an HFE image with 90/2/16/256 parameters. I could then read those disks using a Gotek running flashfloppy, installed in the NGEN workstation.

This was kind of a roundabout way to get what I wanted, and I'm not entirely sure the workstation would read tracks beyond 80, but it didn't really matter as the disk I was trying to convert was only partially full. CTOS appears to fill up the disk from track 0 on out, it won't put data on the furthermost tracks unless it has to. It will stick a VHB and MHD right in the middle of the disk, so converting a 1.44MB image directly in this manner would not work, but converting a 720K image seemed to work fine.

## Other uses

You can also use the tool to inspect file and directory contents. The `dump` command will dump out the Volume Home Block (VHB) as well as the Master File Directory (MFD) and all directories on the disk. The `extract` command will extract a file to stdout.

## Future work

I'd really like to write a "compact" command, so that I could simply take a 1.44MB image and compact it down to 640KB, without having to go through the motions of copying it to a 720KB image first. That would be a bit of work as it would require adjusting LFAs in all of the data structures as well as adjusting the bitmap. If I do end up doing this, I might just implement `write` functionality, and then implement `compact` as `read + write`.

