import pandas as pd
import pyads
import time
import sys
from motionFunctionsLib import *
import math
import argparse

AMSNetId='5.82.112.102.1.1'

############################################################################
#Command line argument parser
parser = argparse.ArgumentParser(description='Test the rotation range of the ESTIA Selene guides')
parser.add_argument('--top',
                    default=None,
                    action='store_true',     
                    help='Test all the mirrors of the top section (default test all mirrors)')
parser.add_argument('--bottom', 
                    default=None,
                    action='store_true',     
                    help='Test all the mirrors of the bottom section (default test all mirrors)')

parser.add_argument('-m', '--manual', 
                    default=False, 
                    action='store_true',     
                    help='Activate manual mode')

args = parser.parse_args()

############################################################################
#Preparing pandas data
hexScrews = pd.read_csv('HexKeysPos.txt', header=None)
hexScrews.columns = ['X-Axis6','Z-Axis7']
hexScrews['Range-Axis10']='0'
print(hexScrews)

Axis6Pos = hexScrews['X-Axis6']
print(f'{Axis6Pos} \n')

Axis7Pos = hexScrews['Z-Axis7']
print(f'{Axis7Pos} \n')

rangeAxis10 = hexScrews['Range-Axis10']
print(f'{rangeAxis10} \n')

#Position index accoridng to option top, bottom or everything
screwArrayTop = []
screwArrayBottom = []
screwArrayTotal = list(range(0, len(hexScrews)))
arrayDone = False

if args.top:
    print(f"Testing top section mirrors hex inserts")
    index = 0
    indexLimit = 2
    factor3 = 2
    while not arrayDone:
        while index <= indexLimit:
            if  index == len(hexScrews):
                break
            else:
                screwArrayTop.append(index)
                index = index + 1

            if index == indexLimit+1:
                index = 3*factor3
                indexLimit = 3*factor3+2
                break
        
        factor3 = factor3+2
        if index >= len(hexScrews):
            arrayDone = True
    positionsIndex = screwArrayTop

elif args.bottom:
    print(f"Testing bottom section mirrors hex inserts")
    index = 3
    indexLimit = 5
    factor3 = 3
    while not arrayDone:
        while index <= indexLimit:
            if  index == len(hexScrews):
                break
            else:
                screwArrayBottom.append(index)
                index = index + 1
            if index == indexLimit+1:
                index = 3*factor3
                indexLimit = 3*factor3+2
                break
        
        factor3 = factor3+2
        if index >= len(hexScrews):
            arrayDone = True
    positionsIndex = screwArrayBottom
else:
    print(f"Testing all mirrors hex inserts")
    positionsIndex = screwArrayTotal

print(f'Array of positions to be tested {positionsIndex}')
############################################################################
#PLC connection
plc1=plc(plcAmsNetId=AMSNetId, plcPort=852)
plc1.connect()

#Axis objects
axis6=axis(plc1, axisNum=6)
axis7=axis(plc1, axisNum=7)
axis8=axis(plc1, axisNum=8)
axis9=axis(plc1, axisNum=9)
axis10=axis(plc1, axisNum=10)
axis11=axis(plc1, axisNum=11)

############################################################################
#Functions to be used
def manualMode(manual=args.manual, skipPosition=False):
    if manual and skipPosition:
        key=input("Press ENTER to continue or s to skip this position: ")
        if key == '':
            return False
        elif key == 's' or key =='S':
            return True
    elif manual and not skipPosition:
        input('"Press ENTER to continue...')
        return 
    else:
        return 


def waitForAxis6n7inPosition():
    inPosition = False
    i = 0
    timeout = 100000
    while not inPosition:
        if axis6.getErrorStatus():
            print(f"   ERROR while positionnig axis 6")
            print(f"   ERROR ID: {axis6.getErrorId()}")
            return False
        elif axis7.getErrorStatus():
            print(f"   ERROR while positionnig axis 7")
            print(f"   ERROR ID: {axis7.getErrorId()}")
            return False
        elif i == timeout:
            print(f"   TIMEOUT: position never reached")
            return False
        inPosition = axis6.getInTargetPosition() and axis7.getInTargetPosition()
        time.sleep(1)
        i = i + 1
    if inPosition:
        print(f" Axes 6 and 7 are in target position")
        return True

def insertAxis8():
    axis8.moveAbsoluteAndWait(axis8.getHomePosition()+1)
    print(f"Axis 8 in position: {axis8.getActPos()}")
    axis8.moveAbsolute(0)
    time.sleep(0.5)
    retries = 5
    tries = 1
    while axis8.getMovingStatus():
        if axis8.getErrorStatus():
            print(f'   ERROR. axis 8 has error ID = {axis8.getErrorId()}')
            return False
    if plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewInserted8", pyads.PLCTYPE_BOOL):

        print(f"Hex Screw Axis 8 fully inserted")
        return True
    elif plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewCollided8", pyads.PLCTYPE_BOOL):
        print(f"Hex screw Axis 8 in Collided state")
        while tries <= retries:
            axis10.moveRelativeAndWait(30)
            if plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewInserted8", pyads.PLCTYPE_BOOL):
                print(f"Hex screw Axis 8 fully inserted")
                return True
            else:
                tries = tries + 1
        print(f"   ERROR Axis 8 still in collision state after 5 tries ")
        return False
    elif plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewMissed8", pyads.PLCTYPE_BOOL):
        print(f"Axis 8 missed, move to a hex screw insert posiiton")
        return False
    else:
        print(f"   ERROR Axis 8 not fully inserted cehck current state in TwinCAT")
        return False

def axis8and9fullyOut():
    if (plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewFullyOut8", pyads.PLCTYPE_BOOL)
     and plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewFullyOut9", pyads.PLCTYPE_BOOL)):
        return True
    else:
        axis8.moveAbsolute(28)
        axis9.moveAbsolute(28)
        fullyOutState = False
        while not fullyOutState:
            fullyOutState = (plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewFullyOut8", pyads.PLCTYPE_BOOL) 
                         and plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewFullyOut9", pyads.PLCTYPE_BOOL))
        if fullyOutState:
            return True
        else: 
            return False


def fullRotationAxis10():
    axis10.jogBwd()
    time.sleep(0.5)
    if axis10.waitForStatusBit(axis10.getErrorStatus, True, timeout=200): #Check if it is better to use lag error
        axis10.jogStop()
        maxBwdPos = axis10.getActPos()
        axis10.axisInit()
    
    axis10.jogFwd()
    time.sleep(0.5)
    if axis10.waitForStatusBit(axis10.getErrorStatus, True, timeout=200): #Check if it is better to use lag error
        axis10.jogStop()
        maxFwdPos = axis10.getActPos()
        axis10.axisInit()

    totalRange = maxFwdPos - maxBwdPos
    return totalRange
    
############################################################################
# Initialization
# Homing axes 8 and 9
print(f"    INITIALIZING TEST")
print(f"  Homing axes 8 and 9")
manualMode()
axis8.axisInit()
axis8.home()
axis9.axisInit()
axis9.home()

if axis8.waitForStatusBit(axis8.getHomedStatus, True) and axis9.waitForStatusBit(axis9.getHomedStatus, True):
    print(f"Axis 8 and 9 homed")
    input("Axis 8 and 9 homed Press enter to continue...")
elif not axis8.getHomedStatus():
    print(f"    ERROR:  Axis 8 cannot be homed")
    sys.exit()
elif not axis9.getHomedStatus():
    print(f"    ERROR:  Axis 9 cannot be homed")
    sys.exit()
else:
    print(f"    ERROR: when homing")
    sys.exit()


# Homing axis 10
axis10.axisInit()
if not axis10.getHomedStatus():
    print(f"Axis 10 not homed, moving to first screw")
    manualMode()
    axis6.moveAbsolute(Axis6Pos[0])
    axis7.moveAbsolute(Axis7Pos[0])
    if waitForAxis6n7inPosition():
        print(f"Axis 6 in position {Axis6Pos[0]} and axis 7 in {Axis7Pos[0]} ")
        manualMode()
        if insertAxis8():
            print(f"Homing axis 10")
            axis10.home()
            time.sleep(1)
            if axis10.getHomedStatus():
                print(f"Axis 10 homed")
                manualMode()
                print('    Moving Axis 8 to position :28')
                axis8.moveAbsoluteAndWait(28)
            else:
                print(f"   ERROR: Cannot home axis 10")
                sys.exit()
    else:
        print(f"   ERROR: error in positioning axis 6 or 7. Position not reached")
        sys.exit()

#Hex screws test sequence

print(f"    Hex position testing ready to begin")
manualMode()
for i in range(len(positionsIndex)):
    
    axis8and9fullyOut()

    print(f'Moving axis 6 to position [{positionsIndex[i]}]: {Axis6Pos[positionsIndex[i]]}')
    print(f'Moving axis 7 to position [{positionsIndex[i]}]: {Axis7Pos[positionsIndex[i]]}')
    if manualMode(skipPosition=True):
        i=i+1
    else:
        axis6.moveAbsolute(Axis6Pos[positionsIndex[i]])
        axis7.moveAbsolute(Axis7Pos[positionsIndex[i]])
    
        if waitForAxis6n7inPosition():
            manualSkip = False
            time.sleep(0.5)
            manualMode()
            if insertAxis8():
                print("Start rotation process")
                manualMode()
                hexScrews.loc[i,'Range-Axis10']=fullRotationAxis10()
                print("Press enter to go to next position")
                manualMode()
            else:
                hexScrews.loc[i,'Range-Axis10']="FAIL"
                print("Range measurmenet FAILED. Press enter to go to next position")
                manualMode()
    hexScrews.to_csv("HexKeysPosWithRotation.txt", mode='w+') #try using just +





