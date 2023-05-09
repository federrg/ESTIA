#!/bin/sh

#Prepare file

#File to modify
filename="Hex_screw_positions_v1.txt"

grep "^ *Screw(" $filename |
sed -e "s/    Screw(//g" -e "s/ //g" -e "s/,0.*//g" > HexKeysPos.txt


