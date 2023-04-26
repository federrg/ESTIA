import pandas as pd
import pyads
import time
import sys
from motionFunctionsLib import *

AMSNetId='5.82.112.102.1.1'

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

#Functions to be used
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
    axis8.moveAbsoluteAndWait(axis8.getHomePosition())
    print(f"Axis 8 in position: {axis8.getActPos()}")
    axis8.moveAbsolute(0)
    time.sleep(0.5)
    while axis8.getMovingStatus():
        if axis8.getErrorStatus():
            print(f'   ERROR. axis 8 has error ID = {axis8.getErrorId()}')
            return False
    if plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewInserted8", pyads.PLCTYPE_BOOL):
        print(f"Hex Screw Axis 8 fully inserted")
        return True
    elif plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewCollided8", pyads.PLCTYPE_BOOL):
        print(f"Hex screw Axis 8 in Collided state")
        while not plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewInserted8", pyads.PLCTYPE_BOOL):
            axis10.moveRelativeAndWait(30)
        if plc1.connection.read_by_name("Hex_Screw_States_8_9.bHexScrewInserted8", pyads.PLCTYPE_BOOL):
            print(f"Hex screw Axis 8 fully inserted")
            return True
    else:
            print(f"   ERROR Could not fully insert Hex key of Axis 8, check psotion of axis 6 and 7")
            return False

def fullRotationAxis10():
    axis10.jogBwd()
    time.sleep(0.5)
    if axis10.waitForStatusBit(axis10.getMovingStatus, False): #Check if it is better to use lag error
        axis10.jogStop()
        maxBwdPos = axis10.getActPos()
        axis10.axisInit()
    
    axis10.jogBwd()
    time.sleep(0.5)
    if axis10.waitForStatusBit(axis10.getMovingStatus, False): #Check if it is better to use lag error
        axis10.jogStop()
        maxFwdPos = axis10.getActPos()
        axis10.axisInit()

    totalRange = maxFwdPos - maxBwdPos
    return totalRange
    

# Initialization
# Homing axes 8 and 9
print(f"    INITIALIZING TEST")
print(f"  Homing axes 8 and 9")
axis8.home()
axis9.home()

if axis8.waitForStatusBit(axis8.getHomedStatus, True) and axis9.waitForStatusBit(axis9.getHomedStatus, True):
    print(f"Axis 8 and 9 homed")
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
if not axis10.getHomedStatus():
    print(f"Axis 10 not homed, moving to first screw")
    axis6.moveAbsolute(Axis6Pos[0])
    axis7.moveAbsolute(Axis7Pos[0])
    if waitForAxis6n7inPosition():
        print(f"Axis 6 in position {Axis6Pos[0]} and axis 7 in {Axis7Pos[0]} ")
        if insertAxis8():
            print(f"Homing axis 10")
            axis10.home()
            time.sleep(1)
            if axis10.getHomedStatus():
                print(f"Axis 10 homed")
            else:
                print(f"   ERROR: Cannot home axis 10")
                sys.exit()
    else:
        print(f"   ERROR: error in positioning axis 6 or 7. Position not reached")
        sys.exit()

#Hex screws test sequence
print(f"    Hex position testing ready to begin")

for i in range(len(hexScrews)):
    print(f'Moving axis 6 to position [{i}]: {Axis6Pos[i]}')
    axis6.moveAbsolute(Axis6Pos[i])

    print(f'Moving axis 7 to position [{i}]: {Axis7Pos[i]}')
    axis7.moveAbsolute(Axis7Pos[i])
    
    if waitForAxis6n7inPosition():
        time.sleep(0.5)
        if insertAxis8():
            hexScrews.loc[i,'Range-Axis10']=fullRotationAxis10()
        else:
            hexScrews.loc[i,'Range-Axis10']="FAIL"
            


