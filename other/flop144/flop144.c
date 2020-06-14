/* flop144.c
 *
 * Look for the dcb for f0, and change its cylinder count to 180.
 *
 * Optionally accepts two parameters, device name, and cylinder count.
 */

#include <stdio.h>
#include <stdlib.h>

int getDCBName(int seg, int ofs, char *name) {
    int len = peekb(seg, ofs+6);
    int i;
    if (len == 0) {
        fprintf(stderr, "zero length dcb name\n");
        return 0;
    }
    if (len > 12) {
        fprintf(stderr, "too long dcb name (%d)\n", len);
        return 0;
    }
    for (i=0; i<len; i++) {
        name[i] = peekb(seg, ofs+7+i);
    }
    name[len] = 0;
    return 1;
}
    
int main(int argc, char *argv[]) {
    int os_seg;
    int os_ofs, dcblist_ofs, dcb_ofs;

    char desiredName[14];
    int desiredCyls = 0xB4;

    strcpy(desiredName, "f0");

    if ((argc>1) && (argv[1]!=0) && (strlen(argv[1])>0)) {
        strcpy(desiredName, argv[1]);
    }

    if ((argc>2) && (argv[2]!=0) && (strlen(argv[2])>0)) {
        desiredCyls = atoi(argv[2]);
    }

    fprintf(stdout, "flop144, Scott Baker, http://www.smbaker.com/\n");

    fprintf(stdout, "lookForDeviceName=%s, desiredCyls=%d\n", 
        desiredName,
        desiredCyls);

    os_seg = peek(0, 0x242);
    os_ofs = peek(0, 0x27C);

    fprintf(stdout, "dcb_list_ptr_ptr = %x:%x\n", os_seg, os_ofs);
    dcblist_ofs = peek(os_seg, os_ofs);
    fprintf(stdout, "dcb_list = %x:%x\n", os_seg, dcblist_ofs);

    while (1) {
        char name[13];
        int bytesPerSector, sectorsPerTrack, tracksPerCylinder;
        int cylindersPerDisk;
        dcb_ofs = peek(os_seg, dcblist_ofs);
        if (dcb_ofs == 0) {
            return 0;
        }
        fprintf(stdout, "dcb at = %x:%x\n", os_seg, dcb_ofs);

        if (!getDCBName(os_seg, dcb_ofs, name)) {
            goto nextdcb;
        }

        bytesPerSector = peek(os_seg, dcb_ofs+68);
        sectorsPerTrack = peek(os_seg, dcb_ofs+70);
        tracksPerCylinder = peek(os_seg, dcb_ofs+72);
        cylindersPerDisk = peek(os_seg, dcb_ofs+74);
        fprintf(stdout, "Name: %s, SecSize: %d, Sec: %d, Head: %d, Cyl: %d\n",
            name,
            bytesPerSector,
            sectorsPerTrack,
            tracksPerCylinder,
            cylindersPerDisk);

        if (strcmp(name, desiredName)!=0) {
            goto nextdcb;
        }

        if (desiredCyls <= 0) {
            goto nextdcb;
        }

        fprintf(stdout, "patching dcb cyls to %d\n", desiredCyls);
        poke(os_seg, dcb_ofs+74, desiredCyls);

nextdcb:
        dcblist_ofs = dcblist_ofs + 2;
    } 

}