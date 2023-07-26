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
parser.add_argument('--eight',
                    default=None,
                    action='store_true',     
                    help='Test mirrors with axis 8')
parser.add_argument('--nine',
                    default=None,
                    action='store_true',     
                    help='Test mirrors with axis 9')
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
hexScrews['Range-Axis11']='0'
print(hexScrews)

Axis6Pos = hexScrews['X-Axis6']
print(f'{Axis6Pos} \n')

Axis7Pos = hexScrews['Z-Axis7']
print(f'{Axis7Pos} \n')

rangeAxis10 = hexScrews['Range-Axis10']
print(f'{rangeAxis10} \n')

rangeAxis11 = hexScrews['Range-Axis11']
print(f'{rangeAxis11} \n')

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
    if not plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewFulluOut8", pyads.PLCTYPE_BOOL):
        axis8.moveVelocity(5)
        #Insert waitforgenericvariable () function once it is defined.

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
            print(f"   ERROR Axis 8 not fully inserted check current state in TwinCAT")
            return False

def insertAxis9():
    axis9.moveAbsoluteAndWait(axis9.getHomePosition()+1)
    print(f"Axis 9 in position: {axis9.getActPos()}")
    axis9.moveAbsolute(0)
    time.sleep(0.5)
    retries = 5
    tries = 1
    while axis9.getMovingStatus():
        if axis9.getErrorStatus():
            print(f'   ERROR. axis 9 has error ID = {axis9.getErrorId()}')
            return False
    if plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewInserted9", pyads.PLCTYPE_BOOL):

        print(f"Hex Screw Axis 9 fully inserted")
        return True
    elif plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewCollided9", pyads.PLCTYPE_BOOL):
        print(f"Hex screw Axis 9 in Collided state")
        while tries <= retries:
            axis10.moveRelativeAndWait(30)
            if plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewInserted9", pyads.PLCTYPE_BOOL):
                print(f"Hex screw Axis 9 fully inserted")
                return True
            else:
                tries = tries + 1
        print(f"   ERROR Axis 9 still in collision state after 5 tries ")
        return False
    elif plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewMissed9", pyads.PLCTYPE_BOOL):
        print(f"Axis 9 missed, move to a hex screw insert posiiton")
        return False
    else:
        print(f"   ERROR Axis 9 not fully inserted cehck current state in TwinCAT")
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
    axis10.moveVelocity(-90)
    time.sleep(0.5)
    if axis10.waitForStatusBit(axis10.getErrorStatus, True, timeout=200): #Check if it is better to use lag error
        print(f"Backward limit reached")
        axis10.haltAxis()
        maxBwdPos = axis10.getActPos()
        axis10.axisInit()
        axis10.moveRelativeAndWait(10)
    else:
        axis10.haltAxis()
        axis10.moveRelativeAndWait(10)
        print(f"TIMEOUT ERROR: did not reach an end backwards")
        maxBwdPos=None
    
    axis10.moveVelocity(90)
    time.sleep(0.5)
    if axis10.waitForStatusBit(axis10.getErrorStatus, True, timeout=200): #Check if it is better to use lag error
        print(f"Forward limit reached")
        axis10.haltAxis()
        maxFwdPos = axis10.getActPos()
        axis10.axisInit()
        axis10.moveRelativeAndWait(-10)
    else:
        axis10.haltAxis()
        axis10.moveRelativeAndWait(-10)
        print(f"TIMEOUT ERROR: did not reach an end forward")
        maxFwdPos=None

    if maxBwdPos is None or maxFwdPos is None:
        totalRange=0
    else:    
        totalRange = maxFwdPos - maxBwdPos
    print(f"maximum position forward = {maxFwdPos}")
    print(f"maximum position backward = {maxBwdPos}")
    print(f"Total range = {totalRange}")
    return totalRange
    
def fullRotationAxis11():
    axis11.moveVelocity(-90)
    time.sleep(0.5)
    if axis11.waitForStatusBit(axis11.getErrorStatus, True, timeout=200): #Check if it is better to use lag error
        print(f"Backward limit reached")
        axis11.haltAxis()
        maxBwdPos = axis11.getActPos()
        axis11.axisInit()
        axis11.moveRelativeAndWait(10)
    else:
        axis11.haltAxis()
        axis11.moveRelativeAndWait(10)
        print(f"TIMEOUT ERROR: did not reach an end backwards")
        maxBwdPos=0
    
    
    axis11.moveVelocity(90)
    time.sleep(0.5)
    if axis11.waitForStatusBit(axis11.getErrorStatus, True, timeout=200): #Check if it is better to use lag error
        print(f"Forward limit reached")
        axis11.haltAxis()
        maxFwdPos = axis11.getActPos()
        axis11.axisInit()
        axis11.moveRelativeAndWait(-10)
    else:
        axis11.haltAxis()
        axis11.moveRelativeAndWait(-10)
        print(f"TIMEOUT ERROR: did not reach an end forward")
        maxFwdPos=0

    if maxBwdPos is None or maxFwdPos is None:
        totalRange=0
    else:    
        totalRange = maxFwdPos - maxBwdPos

    print(f"maximum position forward = {maxFwdPos}")
    print(f"maximum position backward = {maxBwdPos}")
    print(f"Total range = {totalRange}")
    return totalRange
############################################################################
# Initialization
# Homing axes 8 and 9
print("TESTING new function")
if axis9.waitForVariable("MAIN.fTestFloat", pyads.PLCTYPE_LREAL, 3.58):
    print("Hex_Screw_States_8_9.bHexScrewFullyOut8 wwent FALSE")
manualMode()
print(f"    INITIALIZING TEST")
print(f"  Homing axes 8 and 9")
manualMode()
axis8.axisInit()
axis8.home()
axis9.axisInit()
axis9.home()

if axis8.waitForStatusBit(axis8.getHomedStatus, True) and axis9.waitForStatusBit(axis9.getHomedStatus, True):
    print(f"Axis 8 and 9 homed")
    manualMode()
elif not axis8.getHomedStatus():
    print(f"    ERROR:  Axis 8 cannot be homed")
    sys.exit()
elif not axis9.getHomedStatus():
    print(f"    ERROR:  Axis 9 cannot be homed")
    sys.exit()
else:
    print(f"    ERROR: when homing")
    sys.exit()


# Homing axis 10 and 11
axis10.axisInit()
axis11.axisInit()
if not axis10.getHomedStatus() or not axis11.getHomedStatus():
    axis10.home()
    axis11.home()
    time.sleep(1)
    if axis10.getHomedStatus() and axis11.getHomedStatus():
        print(f"Axis 10 and 11 homed")
        manualMode()
    else:
        print(f"   ERROR: Cannot home axis 10 or 11")
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
            if args.eight:
                print("Ready to insert Hex key")
                manualMode()
                if insertAxis8():
                    print("Start rotation process")
                    manualMode()
                    totalRange10=fullRotationAxis10()
                    if totalRange10 is 0:
                        hexScrews.loc[positionsIndex[i],'Range-Axis10']="FAIL"
                        print("Range measurmenet FAILED. Press enter to go to next position")
                        manualMode()
                    else:
                        hexScrews.loc[positionsIndex[i],'Range-Axis10']=totalRange10
                        print("Going to the middle point ")
                        manualMode()
                        middlePoint10=totalRange10/2
                        axis10.moveRelativeAndWait(-middlePoint10)
                        print("Going to the next position")
                        manualMode()
                else:
                    hexScrews.loc[positionsIndex[i],'Range-Axis10']="FAIL"
                    print("Range measurmenet FAILED. Press enter to go to next position")
                    manualMode()
            elif arg.nine:
                print("Ready to insert Hex key")
                manualMode()
                if insertAxis9():
                    print("Start rotation process")
                    manualMode()
                    totalRange11=fullRotationAxis11()
                    if totalRange11 is 0:
                        hexScrews.loc[positionsIndex[i],'Range-Axis11']="FAIL"
                        print("Range measurmenet FAILED. Press enter to go to next position")
                        manualMode()
                    else:
                        hexScrews.loc[positionsIndex[i],'Range-Axis11']=totalRange11
                        print("Going to the middle point")
                        manualMode()
                        middlePoint11=totalRange11/2
                        axis11.moveRelativeAndWait(-middlePoint11)
                        print("Going to the next position")
                        manualMode()
                else:
                    hexScrews.loc[positionsIndex[i],'Range-Axis11']="FAIL"
                    print("Range measurmenet FAILED. Press enter to go to next position")
                    manualMode()
            else:
                print( f"ERROR: No axis selected for the approach")
        hexScrews.to_csv("HexKeysPosWithRotation.txt", mode='w+') #try using just +

        #Add catch keyboard interrupt and stop all motors.