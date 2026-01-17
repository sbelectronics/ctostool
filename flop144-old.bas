10 ossegp! = makepointer(&H242, 0)
20 osofsp! = makepointer(&H27C, 0)
25 osseg% = peek("W",ossegp!)
26 osofs% = peek("W",osofsp!)
30 os! = makepointer(osofs%, osseg%)
40 dcblistofs% = peek("W",os!)
50 desired$ = "f0"

100 dcblistp! = makepointer(dcblistofs%, osseg%)
110 dcbofs% = PEEK("W",dcblistp!)
120 if dcbofs% = 0 then end
121 if dcbofs% = -1 then end
122 if dcbofs% = 255 then end
130 gosub 1000
140 bps% = peek("W", makepointer(dcbofs%+68, osseg%))
150 sps% = peek("W", makepointer(dcbofs%+70, osseg%))
160 tps% = peek("W", makepointer(dcbofs%+72, osseg%))
170 cpd% = peek("W", makepointeR(dcbofs%+74, osseg%))
180 print dname$, bps%, sps%, tps%, cpd%
190 if dname$ == desired$ then gosub 2000
200 dcblistofs% = dcblistofs% + 2
210 goto 100

999 end

1000 rem getdcbname
1005 dname$ = ""
1010 lenp! = makepointer(dcbofs%+6, osseg%)
1020 l% = PEEK("B", lenp!)
1030 rem print l%
1040 for i% = 1 to l%
1050 namep = makepointer(dcbofs%+6+i%, osseg%)
1060 ch% = PEEK("B", namep!)
1070 dname$ = dname$ + chr$(ch%) 
1080 next i%
1090 return

2000 print "found"
2005 poke "W", makepointer(dcbofs%+74, osseg%), &HB4
2010 return