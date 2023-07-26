#!/usr/bin/env python

"""
This file contains three classes: plc, axis and pneumatic

It contains functions that interact with tc_mca_std_lib on a Beckhoff PLC.
"""
import sys, os
from datetime import datetime
import pyads as pyads
import time
from enum import *
from eAxisParameters import E_AxisParameters


class E_MotionFunctions(Enum):
    eMoveAbsolute = 0
    eMoveRelative = 1
    eMoveVelocity = 2
    eMoveModulo = 3
    eGearInMultiMaster = 4
    eGearOut = 5
    eHome = 10
    eWriteParameter = 50
    eReadParameter = 60


class E_HomingRoutines(Enum):
    eNoHoming = 0
    eHomeToLimit_Bwd = 1
    eHomeToLimit_Fwd = 2
    #eHomeToLimit_Bwd_2Speeds = 3
    #eHomeToLimit_Fwd_2Speeds = 4

    eHomeToRef_Bwd = 11
    eHomeToRef_Fwd = 12
    #eHomeToRef_Bwd_2Speeds = 13
    #eHomeToRef_Fwd_2Speeds = 14

    eHomeToEncPulse_Bwd = 21
    eHomeToEncPulse_Fwd = 22
    eHomeToEncPulse_viaBwdLimit = 23
    eHomeToEncPulse_viaFwdLimit = 24

    eHomeDirect = 90

class E_PneumaticAxisErrors(Enum):
    eNoError = 0
    eExtractTimedOut = 1 
    eRetractTimedOut = 2 
    eNotMovingExtract = 3 
    eNotMovingRetract = 4 
    eInterlockOn = 5 
    eNoPSSPermit = 6 
    eAirPressureError = 7 

# SLEEP_INTERVAL is the default that the software will sleep while waiting
# for a bit to change state
# Most if not all functions can specify this as an optional parameter if you
# want a different sleep time for one particular function.
# If not specified this is the default.
SLEEP_INTERVAL = 1  # s
MARGIN_OF_SAFETY = 2
verboseMode = True
dateTimeObj = datetime.now()
prevPrintString = "Empty"


class plc:
    # If running on Windows then TwinCAT should create a
    # route for you already and thus senderIp and
    # senderAmsNetId don't need to be provided
    def __init__(
        self,
        plcAmsNetId,
        plcPort,
        plcIp=None,
        senderAmsNetId=None,
        senderIp=None,
        hostname=None,
        username="Administrator",
        password="1", 
        connection=None
    ):
    
        print("Constructor for PLC")

        self.plcAmsNetId = plcAmsNetId
        self.plcPort = plcPort
        self.plcIp = plcIp
        self.senderAmsNetId = senderAmsNetId
        self.senderIp = senderIp
        self.hostname = hostname
        self.username = username
        self.password = password
        self.connection = pyads.Connection(self.plcAmsNetId, self.plcPort)
        
    def __del__(self):
        print("Destructor for PLC: Close connection")
        self.connection.close()

    def connect(self):
        print("Connect to PLC")
        """
        platformIsLinux = pyads.utils.platform_is_linux()
        print(f"isLinux()={platformIsLinux}")
        if platformIsLinux:
            if self.senderAmsNetId != None and self.senderIp != None:
                pyads.add_route_to_plc(
                    self.senderAmsNetId,
                    # The second argument here should be hostname
                    # instead of senderIp but we prefer not to use
                    # hostname
                    self.senderIp,
                    self.plcIp,
                    self.username,
                    self.password,
                    route_name=self.hostname,
                )
            else:
                print(
                    "Either senderAmsNetId or senderIp set to none so assuming"
                    "the route has already been created"
                )

        local_port = pyads.open_port()
        """
        self.connection.open()
        print(f"is_open()={self.connection.is_open}")

        #pyads.set_local_address(self.senderAmsNetId)
        print(f"get_local_address()={pyads.get_local_address()}")

        # If the connection was not successful this command will fail
        print(f"read_device_info()={self.connection.read_device_info()}")
        self.noOfAxes = self.connection.read_by_name(
            "GVL_APP.nAXIS_NUM", pyads.PLCTYPE_INT
        )
        print(f"GVL_APP.nAXIS_NUM={self.noOfAxes}")

        return self
    # For reading and writing any variable you can use the pyads function of the plc:
    # E.g.: plc_obj.connection.read_by_name("varName", pyads.PLCTYPE_XXX)
    # E.g.: plc_obj.connection.write_by_name("varName", value, pyads.PLCTYPE_XXX)
    
class axis:
    def __init__(self, plcConnection, axisNum):
        print("Constructor for axis")
        self.plc = plcConnection
        self.axisNum = axisNum

    def __del__(self):
        print("Destructor for axis: Resetting jog commands")
        self.jogStop()

    # Generic function for getting any variable on the Axis
    def getGenericVariable(self, plcVarPath, plcVarType):
        plcVarName = f"GVL.astAxes[{self.axisNum}].{plcVarPath}"
        returnValue = self.plc.connection.read_by_name(plcVarName, plcVarType)
        global prevPrintString
        printString = f"{plcVarName}=: {returnValue}"
        if prevPrintString != printString:
            print(f"{dateTimeObj.now()} {printString}")
        prevPrintString = printString
        return returnValue

    # Get ST_Status variables
    def getEnabledStatus(self):
        return self.getGenericVariable("stStatus.bEnabled", pyads.PLCTYPE_BOOL)

    def getCommandAbortedStatus(self):
        return self.getGenericVariable("stStatus.bCommandAborted", pyads.PLCTYPE_BOOL)

    def getBusyStatus(self):
        return self.getGenericVariable("stStatus.bBusy", pyads.PLCTYPE_BOOL)

    def getDoneStatus(self):
        return self.getGenericVariable("stStatus.bDone", pyads.PLCTYPE_BOOL)

    def getHomedStatus(self):
        return self.getGenericVariable("stStatus.bHomed", pyads.PLCTYPE_BOOL)

    def getMovingStatus(self):
        return self.getGenericVariable("stStatus.bMoving", pyads.PLCTYPE_BOOL)

    def getMovingFwdStatus(self):
        return self.getGenericVariable("stStatus.bMovingForward", pyads.PLCTYPE_BOOL)

    def getMovingBwdStatus(self):
        return self.getGenericVariable("stStatus.bMovingBackward", pyads.PLCTYPE_BOOL)

    def getFwdEnabled(self):
        return self.getGenericVariable("stStatus.bFwEnabled", pyads.PLCTYPE_BOOL)

    def getBwdEnabled(self):
        return self.getGenericVariable("stStatus.bBwEnabled", pyads.PLCTYPE_BOOL)

    def getInterlockedFwd(self):
        return self.getGenericVariable("stStatus.bInterlockedFwd", pyads.PLCTYPE_BOOL)

    def getInterlockedBwd(self):
        return self.getGenericVariable("stStatus.bInterlockedBwd", pyads.PLCTYPE_BOOL)

    def getInTargetPosition(self):
        return self.getGenericVariable("stStatus.bInTargetPosition", pyads.PLCTYPE_BOOL)

    def getGearedStatus(self):
        return self.getGenericVariable("stStatus.bGeared", pyads.PLCTYPE_BOOL)

    def getCoupledGear1(self):
        return self.getGenericVariable("stStatus.bCoupledGear1", pyads.PLCTYPE_BOOL)

    def getCoupledGear2(self):
        return self.getGenericVariable("stStatus.bCoupledGear2", pyads.PLCTYPE_BOOL)

    def getCoupledGear3(self):
        return self.getGenericVariable("stStatus.bCoupledGear3", pyads.PLCTYPE_BOOL)

    def getCoupledGear4(self):
        return self.getGenericVariable("stStatus.bCoupledGear4", pyads.PLCTYPE_BOOL)

    def getActPos(self):
        return self.getGenericVariable("stStatus.fActPosition", pyads.PLCTYPE_LREAL)

    def getActVel(self):
        return self.getGenericVariable("stStatus.fActVelocity", pyads.PLCTYPE_LREAL)

    def getErrorStatus(self):
        return self.getGenericVariable("stStatus.bError", pyads.PLCTYPE_BOOL)

    def getErrorId(self):
        return self.getGenericVariable("stStatus.nErrorID", pyads.PLCTYPE_UDINT)
    
    #Status of the ST_AxisStatus of the AXIS_REF
    def getConstantVelocityStatus(self):
        return self.getGenericVariable("Axis.Status.ConstantVelocity", pyads.PLCTYPE_BOOL)

    def getAcceleratingStatus(self):
        return self.getGenericVariable("Axis.Status.Accelerating", pyads.PLCTYPE_BOOL)

    def getDeceleratingStatus(self):
        return self.getGenericVariable("Axis.Status.Decelerating", pyads.PLCTYPE_BOOL)

    def getStandstillStatus(self):
        return self.getGenericVariable("Axis.Status.Standstill", pyads.PLCTYPE_BOOL)

    # Get ST_Config variables
    def getHomeSequence(self):
        return self.getGenericVariable("stConfig.eHomeSeq", pyads.PLCTYPE_INT)

    def getHomePosition(self):
        return self.getGenericVariable("stConfig.fHomePosition", pyads.PLCTYPE_LREAL)

    def getHomeFinishDistance(self):
        return self.getGenericVariable("stConfig.fHomeFinishDistance", pyads.PLCTYPE_LREAL)

    def getVelocity(self):
        return self.getGenericVariable("stControl.fVelocity", pyads.PLCTYPE_LREAL)

    def getAcceleration(self):
        return self.getGenericVariable("stControl.fAcceleration", pyads.PLCTYPE_LREAL)

    def getDeceleration(self):
        return self.getGenericVariable("stControl.fDeceleration", pyads.PLCTYPE_LREAL)

    def getPosition(self):
        return self.getGenericVariable("stControl.fPosition", pyads.PLCTYPE_LREAL)

    def getMultiMasterAxis(self, masterIndex):
        return self.getGenericVariable(
            f"stConfig.astMultiMasterAxis[{masterIndex}].nIndex", pyads.PLCTYPE_UINT)

    def getMultiMasterRatio(self, masterIndex):
        return self.getGenericVariable(
            f"stConfig.astMultiMasterAxis[{masterIndex}].fRatio", pyads.PLCTYPE_LREAL)

    def getMultiMasterAxisLatched(self, masterIndex):
        return self.getGenericVariable(
            f"stConfig.astMultiMasterAxisLatched[{masterIndex}].nIndex",
            pyads.PLCTYPE_UINT)

    def getMultiMasterRatioLatched(self, masterIndex):
        return self.getGenericVariable(
            f"stConfig.astMultiMasterAxisLatched[{masterIndex}].fRatio",
            pyads.PLCTYPE_LREAL)

    def getMultiSlaveAxisRatio(self, slaveNum):
        return self.getGenericVariable(
            f"stConfig.afMultiSlaveAxisRatio[{slaveNum}]", pyads.PLCTYPE_LREAL)

    def getVelocityHomeToCam(self):
        return self.getGenericVariable("stConfig.fHomingVelToCam", pyads.PLCTYPE_LREAL)

    def getVelocityHomeFromCam(self):
        return self.getGenericVariable(
            "stConfig.fHomingVelFromCam", pyads.PLCTYPE_LREAL)

    def getVelocityMax(self):
        return self.getGenericVariable("stConfig.fVeloMax", pyads.PLCTYPE_LREAL)
    
    def getAccelMax(self):
        return self.getGenericVariable("stConfig.fMaxAcc", pyads.PLCTYPE_LREAL)

    def getDecelMax(self):
        return self.getGenericVariable("stConfig.fMaxDec", pyads.PLCTYPE_LREAL)

    def getSoftLimitFwdValue(self):
        return self.getGenericVariable("stConfig.fMaxSoftPosLimit", pyads.PLCTYPE_LREAL)

    def getSoftLimitBwdValue(self):
        return self.getGenericVariable("stConfig.fMinSoftPosLimit", pyads.PLCTYPE_LREAL)

    def getSoftLimitFwdEnableStatus(self):
        return self.getGenericVariable(
            "stConfig.bEnMaxSoftPosLimit", pyads.PLCTYPE_BOOL)

    def getSoftLimitBwdEnableStatus(self):
        return self.getGenericVariable(
            "stConfig.bEnMinSoftPosLimit", pyads.PLCTYPE_BOOL)

    def getAxisVeloManFast(self):
        return self.getGenericVariable(
            "stConfig.fVelocityDefaultFast", pyads.PLCTYPE_LREAL)

    def getAxisVeloManSlow(self):
        return self.getGenericVariable(
            "stConfig.fVelocityDefaultSlow", pyads.PLCTYPE_LREAL)

    def getAxisEnPositionLagMonitoring(self):
        return self.getGenericVariable(
            "stConfig.bEnPositionLagMonitoring", pyads.PLCTYPE_BOOL)

    def getAxisPositionLagValue(self):
        return self.getGenericVariable("stConfig.fMaxPosLagValue", pyads.PLCTYPE_LREAL)

    def getAxisEnTargetPositionMonitoring(self):
        return self.getGenericVariable(
            "stConfig.bEnTargetPositionMonitoring", pyads.PLCTYPE_BOOL
        )

    def getAxisTargetPositionWindow(self):
        return self.getGenericVariable(
            "stConfig.fTargetPositionWindow", pyads.PLCTYPE_LREAL
        )

    # Get ST_Input variables
    def getLimitFwd(self):
        return self.getGenericVariable("stInputs.bLimitFwd", pyads.PLCTYPE_BOOL)

    def getLimitBwd(self):
        return self.getGenericVariable("stInputs.bLimitBwd", pyads.PLCTYPE_BOOL)

    def getHomeSwitch(self):
        return self.getGenericVariable("stInputs.bHome", pyads.PLCTYPE_BOOL)

    # Generic function for setting any variable on the plc
    def setGenericVariable(self, plcVarPath, plcVarValue, plcVarType):
        plcVarName = f"GVL.astAxes[{self.axisNum}].{plcVarPath}"
        print(f"{dateTimeObj.now()} {plcVarName}={plcVarValue}")
        self.plc.connection.write_by_name(plcVarName, plcVarValue, plcVarType)

    # Set ST_Control variables
    def executeAxis(self):
        self.setGenericVariable("stControl.bExecute", True, pyads.PLCTYPE_BOOL)

    def resetAxis(self):
        self.setGenericVariable("stControl.bReset", True, pyads.PLCTYPE_BOOL)

    def haltAxis(self):
        self.setGenericVariable("stControl.bHalt", True, pyads.PLCTYPE_BOOL)

    def stopAxis(self):
        self.setGenericVariable("stControl.bStop", True, pyads.PLCTYPE_BOOL)

    def enableAxis(self):
        self.setGenericVariable("stControl.bEnable", True, pyads.PLCTYPE_BOOL)

    def disableAxis(self):
        self.setGenericVariable("stControl.bEnable", False, pyads.PLCTYPE_BOOL)

    def setMotionCommand(self, command): #Called by the functions regarding a move
        plcVarName = f"GVL.astAxes[{self.axisNum}].stControl.eCommand"
        print(f"{dateTimeObj.now()} {plcVarName}={command.name}")
        self.plc.connection.write_by_name(plcVarName, command.value, pyads.PLCTYPE_INT)

    def setVelocity(self, value):
        self.setGenericVariable("stControl.fVelocity", value, pyads.PLCTYPE_LREAL)

    def setJogVelocity(self, value):
        self.setGenericVariable("stControl.fJogVelocity", value, pyads.PLCTYPE_LREAL)

    def setAcceleration(self, value):
        self.setGenericVariable("stControl.fAcceleration", value, pyads.PLCTYPE_LREAL)

    def setDeceleration(self, value):
        self.setGenericVariable("stControl.fDeceleration", value, pyads.PLCTYPE_LREAL)

    def setPosition(self, value):
        self.setGenericVariable("stControl.fPosition", value, pyads.PLCTYPE_LREAL)

    # Set ST_Config variables
    def setOverride(self, value):
        self.setGenericVariable("stConfig.fOveride", value, pyads.PLCTYPE_LREAL)

    def setHomePosition(self, value):
        self.setGenericVariable("stConfig.fHomePosition", value, pyads.PLCTYPE_LREAL)

    def setHomeFinishDistance(self, value):
        self.setGenericVariable("stConfig.fHomeFinishDistance", value, pyads.PLCTYPE_LREAL)

    def setHomeSequence(self, sequence): #Called by the function home() and homeSpecific()
        plcVarName = f"GVL.astAxes[{self.axisNum}].stConfig.eHomeSeq"
        print(f"{dateTimeObj.now()} {plcVarName}={sequence.name}")
        self.plc.connection.write_by_name(plcVarName, sequence.value, pyads.PLCTYPE_INT)

    def setMultiMasterAxis(self, masterNum, masterAxisNum, gearRatio):
        self.setGenericVariable(
            f"stConfig.astMultiMasterAxis[{masterNum}].nIndex",
            masterAxisNum,
            pyads.PLCTYPE_UINT)
        self.setGenericVariable(
            f"stConfig.astMultiMasterAxis[{masterNum}].fRatio",
            gearRatio,
            pyads.PLCTYPE_LREAL)
            
    # Set some Nc Parameters that aren't exposed
    def setSoftLimitsOn(self):
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitFwd, 1.0)
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitBwd, 1.0)

    def setSoftLimitsOff(self):
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitFwd, 0.0)
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitBwd, 0.0)

    def setFwdSoftLimitsOn(self):
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitFwd, 1.0)

    def setBwdSoftLimitsOn(self):
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitBwd, 1.0)
        
    def setFwdSoftLimitsOff(self):
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitFwd, 0.0)
    
    def setBwdSoftLimitsOff(self):
        axis.setNcAxisParam(self, E_AxisParameters.EnableLimitBwd, 0.0)

    def setSoftLimitFwdValue(self, softLimitFwdValue):
        axis.setNcAxisParam(self, E_AxisParameters.SWLimitFwd, softLimitFwdValue)

    def setSoftLimitBwdValue(self, softLimitBwdValue):
        axis.setNcAxisParam(self, E_AxisParameters.SWLimitBwd, softLimitBwdValue)

    def setAxisVeloManSlow(self, AxisVeloManSlow):
        axis.setNcAxisParam(self, E_AxisParameters.AxisVeloManSlow, AxisVeloManSlow)

    def setAxisEnTargetPositionMonitoringON(self):
        axis.setNcAxisParam(self, E_AxisParameters.AxisEnTargetPositionMonitoring, 1.0)

    def setAxisEnTargetPositionMonitoringOFF(self):
        axis.setNcAxisParam(self, E_AxisParameters.AxisEnTargetPositionMonitoring, 0.0)

    def setAxisTargetPositionWindow(self, axisTargetPositionWindow):
        axis.setNcAxisParam(
            self, E_AxisParameters.AxisTargetPositionWindow, axisTargetPositionWindow
        )

    ###Motion commands###
    def moveAbsolute(self, position):
        print(f"Axis {self.axisNum}: Move absolute to position {position:.2f}")
        self.setPosition(position)
        self.setMotionCommand(E_MotionFunctions.eMoveAbsolute)
        self.executeAxis()

    def moveAbsoluteAndWait(self, position):
        self.moveAbsolute(position)
        timeout = self.calcTravelTimeForMove()+1
        self.waitForCommandDone(timeoutDoneTrue=timeout)
        return self.getDoneStatus()

    def moveRelative(self, position):
        print(f"Axis {self.axisNum}: Move relative to position {position:.2f}")
        self.setPosition(position)
        self.setMotionCommand(E_MotionFunctions.eMoveRelative)
        self.executeAxis()

    def moveRelativeAndWait(self, position):
        self.moveRelative(position)
        timeout = self.calcTravelTimeForMove()+1
        self.waitForCommandDone(timeoutDoneTrue=timeout)
        return self.getDoneStatus()

    def jogFwd(self):
        #self.setMotionCommand(E_MotionFunctions.eJog)
        #self.setGenericVariable("stControl.bJogFwd", True, pyads.PLCTYPE_BOOL)
        self.setVelocity(self.getAxisVeloManSlow())
        self.setMotionCommand(E_MotionFunctions.eMoveVelocity)
        self.executeAxis()

    def jogBwd(self):
        #self.setMotionCommand(E_MotionFunctions.eJog)
        #self.setGenericVariable("stControl.bJogBwd", True, pyads.PLCTYPE_BOOL)
        self.setVelocity(-(self.getAxisVeloManSlow()))
        self.setMotionCommand(E_MotionFunctions.eMoveVelocity)
        self.executeAxis()

    def jogStop(self):
        #self.setGenericVariable("stControl.bJogFwd", False, pyads.PLCTYPE_BOOL)
        #self.setGenericVariable("stControl.bJogBwd", False, pyads.PLCTYPE_BOOL)
        self.haltAxis()

    def moveVelocity(self, velocity):
        print(f"Axis {self.axisNum}: Move velocity with speed {velocity:.2f}")
        self.setVelocity(velocity)
        self.setMotionCommand(E_MotionFunctions.eMoveVelocity)
        self.executeAxis()

    def moveToSwitchFwd(self, velo, timeout):
        print(f"    Activate moving to Forward Limit Switch sequence...")
        if self.getSoftLimitFwdEnableStatus():
            print(' Disabling soft limits forward...')
            self.setFwdSoftLimitsOff()
            time.sleep(SLEEP_INTERVAL)
            self.setBwdSoftLimitsOff()
            time.sleep(SLEEP_INTERVAL)
            if self.getSoftLimitFwdEnableStatus() or self.getSoftLimitBwdEnableStatus():
                print(f'    Error: Failed to disable soft limits')
                return False
              
        else:
            print(f"    Soft limits disabled, starting movement")

        if not self.getLimitFwd():
            print("     Axis possibly on the limit switch, moving away of it...")
            for i in range(3):
                if self.moveRelativeAndWait(-3):
                    time.sleep(1)
                    if self.getLimitFwd():
                        print("     Axis not on the limit switch anymore...")
                        break
                    else:
                        i += 1
                if i == 3:
                    print("     ERROR: Timeout. Possibly limit without Power")
                    return False
                    
        print('     Moving to Fwd Swtich...')
        time.sleep(SLEEP_INTERVAL)
        self.moveVelocity(velo)
        
        if self.waitForStatusBit(self.getLimitFwd, False, timeout):
            print('     Fwd Limit reached...')
            self.haltAxis()
            time.sleep(SLEEP_INTERVAL)
            return True
        else:
            print(f'    ERROR: Axis {self.axisNum}: Timeout error waiting for LimitFwd to return False')
            self.haltAxis()
            return False
    
    def moveToSwitchBwd(self, velo, timeout):
        if velo is None: 
            velo = axis1.getJogVelocity()

        print(f"    Activate moving to Backward Limit Switch sequence...")
        if self.getSoftLimitFwdEnableStatus() or self.getSoftLimitBwdEnableStatus():
            print(' Disabling soft limits...')
            self.setFwdSoftLimitsOff()
            time.sleep(SLEEP_INTERVAL)
            self.setBwdSoftLimitsOff()
            time.sleep(SLEEP_INTERVAL)
            if self.getSoftLimitFwdEnableStatus() or self.getSoftLimitBwdEnableStatus():
                print(f'    Error: Failed to disable soft limits')
                return False
                
        else:
            print(f"    Soft limits disabled, starting movement")

        if not self.getLimitBwd():
            print("     Axis possibly on the limit switch, moving away of it...")
            for i in range(3):
                if self.moveRelativeAndWait(3):
                    time.sleep(1)
                    if self.getLimitBwd():
                        print("     Axis not on the limit switch anymore...")
                        break
                    else:
                        i += 1
                if i == 3:
                    print("     ERROR: Timeout. Possibly limit without Power")
                    return False
                    
        print('     Moving to Bwd Swtich...')
        time.sleep(SLEEP_INTERVAL)
        self.moveVelocity(-velo)

        if self.waitForStatusBit(self.getLimitBwd, False, timeout):
            print('     Bwd Limit reached...')
            self.haltAxis()
            time.sleep(SLEEP_INTERVAL)
            return True
        else:
            print(f'    ERROR: Axis {self.axisNum}: Timeout error waiting for LimitFwd to return False')
            self.haltAxis()
            return False
            
            
    def gearInMultiMaster(
        self,
        master1=None,
        ratio1=None,
        master2=None,
        ratio2=None,
        master3=None,
        ratio3=None,
        master4=None,
        ratio4=None,
    ):
        print(f"Axis {self.axisNum}: Gear in multi master")
        print(f"MasterAxis1 = {master1} with GearRatio1 = {ratio1}")
        print(f"MasterAxis2 = {master2} with GearRatio2 = {ratio2}")
        print(f"MasterAxis3 = {master3} with GearRatio3 = {ratio3}")
        print(f"MasterAxis4 = {master4} with GearRatio4 = {ratio4}")

        self.setMotionCommand(E_MotionFunctions.eGearInMultiMaster)
        if not master1 == None:
            self.setMultiMasterAxis(1, master1, ratio1)
        if not master2 == None:
            self.setMultiMasterAxis(2, master2, ratio2)
        if not master3 == None:
            self.setMultiMasterAxis(3, master3, ratio3)
        if not master4 == None:
            self.setMultiMasterAxis(4, master4, ratio4)

        self.executeAxis()

    def gearOut(self):
        print(f"Axis {self.axisNum}: Gear Out")
        self.setMotionCommand(E_MotionFunctions.eGearOut)
        self.executeAxis()

    def homeSpecific(self, homeSeq, homePos=0, homeFinishDist=0):
        print(f"Axis {self.axisNum}: Home with HomeSeq={homeSeq}, HomePos={homePos}, HomeFinishDistance={homeFinishDist}")
        self.setHomeSequence(E_HomingRoutines(homeSeq))
        self.setHomePosition(homePos)
        self.setHomeFinishDistance(homeFinishDist)
        self.setMotionCommand(E_MotionFunctions.eHome)
        self.executeAxis()

    def home(self):
        self.homeSeq = self.getHomeSequence()
        self.homePos = self.getHomePosition()
        self.homeFinishDist = self.getHomeFinishDistance()
        print(f"Axis {self.axisNum}: Home with HomeSeq={self.homeSeq}, HomePos={self.homePos}, HomeFinishDistance={self.homeFinishDist}")
        self.setMotionCommand(E_MotionFunctions.eHome)
        self.executeAxis()

    def setNcAxisParam(self, axisParam, writeAxisParam):
        self.setMotionCommand(E_MotionFunctions.eWriteParameter)

        plcVarName = f"GVL.astAxes[{self.axisNum}].stConfig.eAxisParameters"
        print(f"{dateTimeObj.now()} {plcVarName}={axisParam.name}")
        self.plc.connection.write_by_name(
            plcVarName, axisParam.value, pyads.PLCTYPE_INT
        )

        plcVarName = f"GVL.astAxes[{self.axisNum}].stConfig.fWriteAxisParameter"
        print(f"{dateTimeObj.now()} {plcVarName}={writeAxisParam}")
        self.plc.connection.write_by_name(
            plcVarName, writeAxisParam, pyads.PLCTYPE_LREAL
        )

        self.executeAxis()
        time.sleep(0.05)

    def getNcAxisParam(self, axisParam):
        self.setMotionCommand(E_MotionFunctions.eReadParameter)

        plcVarName = f"GVL.astAxes[{self.axisNum}].stConfig.eAxisParameters"
        print(f"{dateTimeObj.now()} {plcVarName}={axisParam.name}")
        self.plc.connection.write_by_name(
            plcVarName, axisParam.value, pyads.PLCTYPE_INT
        )
        self.executeAxis()
        time.sleep(SLEEP_INTERVAL)

        plcVarName = f"GVL.astAxes[{self.axisNum}].stConfig.fReadAxisParameter"
        readAxisParam = self.plc.connection.read_by_name(
            plcVarName, pyads.PLCTYPE_LREAL
        )
        print(f"{dateTimeObj.now()} {plcVarName}=?: {readAxisParam}")

        return readAxisParam

    ###Functions useful for testing###

    #This function disables, reset and enables the axis
    def axisInit(self):
        #Disable Axis
        if self.getEnabledStatus():
            print(f"    Disabling Axis...")
            self.disableAxis()
            time.sleep(1)
            if self.waitForStatusBit(self.getEnabledStatus, False):
                print(f"    Axis disabled")
        else:
            print("     Axis disabled")

        #Reset Axis
        print('     Resetting axis...')
        self.resetAxis()
        time.sleep(SLEEP_INTERVAL)

        #Enable Axis
        if not self.getEnabledStatus():
            print(f"    Enabling Axis...")
            self.enableAxis()
            time.sleep(SLEEP_INTERVAL)
            if self.waitForStatusBit(self.getEnabledStatus, True):
                print(f"    Axis Enabled")

    def waitForVariable(self, varName, plcVarType, expectedValue, timeout=30, sleepInterval=SLEEP_INTERVAL):
         # If timeout is negative time then just use a default
        if timeout < 0:
            timeout = 1

        timeLimit = time.time() + timeout
        timeoutError = False
        while True:
            variableValue=self.plc.connection.read_by_name(varName, plcVarType)
            if str(variableValue) == str(expectedValue):
                break
            if time.time() > timeLimit:
                timeoutError = True
                break
            if sleepInterval > 0:
                time.sleep(sleepInterval)

        if timeoutError:
            print(
                f"  Axis {self.axisNum}: Timeout error waiting for {varName} with value {variableValue} to return {expectedValue}"
            )
            return False
        else:
            return True

    # boolValue is the status you're waiting for
    # if you're waiting a bit to go high then this should be True
    def waitForStatusBit(
        self, getStatusBitFunction, boolValue, timeout=30, sleepInterval=SLEEP_INTERVAL
    ):
        # If timeout is negative time then just use a default
        if timeout < 0:
            timeout = 1

        timeLimit = time.time() + timeout
        timeoutError = False
        while True:
            statusBit = getStatusBitFunction()
            if statusBit == boolValue:
                break
            if time.time() > timeLimit:
                timeoutError = True
                break
            if sleepInterval > 0:
                time.sleep(sleepInterval)

        if timeoutError:
            print(
                f"  Axis {self.axisNum}: Timeout error waiting for {getStatusBitFunction.__name__} to return {boolValue}"
            )
            return False
        else:
            return True

    def waitForCommandAborted(self):
        return self.waitForStatusBit(self.getCommandAbortedStatus, True)
    
    # This ones a bit different to the previous generic waitForStatusBit
    # It waits for bDone to go low, then bBusy high, then bDone high
    def waitForCommandDone(
        self,
        timeoutDoneFalse=5,
        timeoutBusyTrue=5,
        timeoutDoneTrue=30,
        sleepInterval=SLEEP_INTERVAL,
    ):
        if not self.waitForStatusBit(
            self.getDoneStatus,
            False,
            timeout=timeoutDoneFalse,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bDone status did not go low within {timeoutDoneFalse} seconds"
            )
            return False
        if not self.waitForStatusBit(
            self.getBusyStatus,
            True,
            timeout=timeoutBusyTrue,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bBusy status did not go high within {timeoutBusyTrue} seconds"
            )
            return False
        if not self.waitForStatusBit(
            self.getDoneStatus,
            True,
            timeout=timeoutDoneTrue,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bDone status did not go high within {timeoutDoneTrue} seconds"
            )
            return False
        return True

    # This one is also a bit special as I don't think we currently have a
    # stop bit in the ast.axisStruct
    # Therefore this function checks the actual velocity is 0
    def waitForStop(
        self, timeout=30, sleepInterval=SLEEP_INTERVAL, roundVelDecimalPlaces=2
    ):
        # If timeout is negative time then just use a default
        if timeout < 0:
            timeout = 1

        timeLimit = time.time() + timeout
        bTimeoutError = False
        while True:
            if round(self.getActVel(), roundVelDecimalPlaces) == 0 or not self.getMovingStatus():
                break
            if time.time() > timeLimit:
                bTimeoutError = True
                break
            if sleepInterval > 0:
                time.sleep(sleepInterval)

        if bTimeoutError:
            print(
                f"  Axis {self.axisNum} Error: Timeout of {timeout} exceeded waiting for velocity to be zero"
            )
            return False
        else:
            return True

    # Check that the position is within the specificed range post move
    def checkTargetPositionWindow(self, targetPos=None):
        # Not sure if getPos is the best variable, this is just what's in the
        # axisStuct and not the setPos in the NC
        actPos = self.getActPos()
        if targetPos == None:
            targetPos = self.getPosition()
        targetPosWindow = self.getAxisTargetPositionWindow()

        error = abs(actPos - targetPos)

        print(
            f"Set Pos: {targetPos:.2f}, Act Pos: {actPos:.2f}, Error: {error:.2f}, Pos Window: {targetPosWindow:.2f}"
        )

        if error < targetPosWindow:
            return True
        else:
            return False

    def calcTravelTimeForMove(self, marginOfSafety=MARGIN_OF_SAFETY):
        print(f"Calculating expected travel time for current move")

        vel = self.getVelocity()
        acc = self.getAcceleration()
        dec = self.getDeceleration()
        currentPos = self.getActPos()
        finalPos = self.getPosition()

        print(
            f"Vel={vel:.2f}, Acc={acc:.2f}, Dec={dec:.2f}, Curr Pos={currentPos:.2f},Final Pos={finalPos:.2f}"
        )

        timeToAcc = abs(vel / acc)
        timeToDec = abs(vel / dec)

        accDist = 0.5 * acc * timeToAcc * timeToAcc
        decDist = 0.5 * acc * timeToDec * timeToDec

        distToTravel = abs(currentPos - finalPos)

        distForConstVel = distToTravel - accDist - decDist

        if vel == 0:
            print("  Error: Can't divide by a velocity of 0")
            return -1

        timeAtConstVel = abs(distForConstVel / vel)

        totalTravelTime = timeToAcc + timeAtConstVel + timeToDec

        estTravelTime = totalTravelTime * marginOfSafety

        print(
            f"Estimated time for the move is: {estTravelTime:.2f}s with a safety factor of {marginOfSafety}"
        )

        return estTravelTime

    def calcTravelTimeForPosition(self, finalPos,  marginOfSafety=MARGIN_OF_SAFETY):
        print(f"Calculating expected travel time for current move")

        vel = self.getVelocity()
        acc = self.getAcceleration()
        dec = self.getDeceleration()
        currentPos = self.getActPos()
        
        print(
            f"Vel={vel:.2f}, Acc={acc:.2f}, Dec={dec:.2f}, Curr Pos={currentPos:.2f},Final Pos={finalPos:.2f}"
        )

        timeToAcc = abs(vel / acc)
        timeToDec = abs(vel / dec)

        accDist = 0.5 * acc * timeToAcc * timeToAcc
        decDist = 0.5 * acc * timeToDec * timeToDec

        distToTravel = abs(currentPos - finalPos)

        distForConstVel = distToTravel - accDist - decDist

        if vel == 0:
            print(" Error: Can't divide by a velocity of 0")
            return -1

        timeAtConstVel = abs(distForConstVel / vel)

        totalTravelTime = timeToAcc + timeAtConstVel + timeToDec

        estTravelTime = totalTravelTime * marginOfSafety

        print(
            f"Estimated time for the move is: {estTravelTime:.2f}s with a safety factor of {marginOfSafety}"
        )

        return estTravelTime

    # This calculation uses the soft limits to calculate the max distance the
    # axis would have to move.
    # This distance divided by the homing speed estimates the max homing time
    # and can thus be used for the timeout when homing
    def calcTravelTimeForRange(self, marginOfSafety=MARGIN_OF_SAFETY):
        print(f"Calculating expected travel time for axis range")
        softLimFwd = self.getSoftLimitFwdValue()
        softLimNeg = self.getSoftLimitBwdValue()
        homingVelocity = self.getVelocityHomeFromCam()

        if (softLimFwd == 0 and softLimNeg == 0):
            print(f'    ERROR: No soft limits defined, cannot calculate travel range')
            return -1

        travelRange = abs(softLimFwd - softLimNeg)

        # Use 2 * travel range because if you start homing in the wrong direction
        # you might need to move the whol range twice
        # Use homing from cam as it's a slower speed
        if homingVelocity == 0:
            print(" Error: Can't divide by a homing velocity of 0")
            return -1

        totalTravelTime = abs(2 * travelRange / homingVelocity)

        print(f"Range={travelRange:.2f}, Homing Vel={homingVelocity:.2f}")

        estTravelTime = totalTravelTime * marginOfSafety

        print(
            f"Estimated time for the axis range is: {estTravelTime:.2f}s with a safety factor of {marginOfSafety:.2f}"
        )

        return estTravelTime

    def calcTimeForAccel(self, marginOfSafety=MARGIN_OF_SAFETY):
        print(f"Calculating expected travel time for axis acceleration")

        setVel = (
            self.getVelocityHomeFromCam()
        )  # perhaps should be changed as it could be to cam as well
        accel = self.getAcceleration()

        if accel == 0:
            print(" Error: Can't divide by an acceleration of 0")
            return -1

        timeForAccel = abs(setVel / accel)

        print(f"Set Velocity={setVel:.2f}, Acceleration={accel:.2f}")

        estTravelTime = timeForAccel * marginOfSafety

        print(
            f"Estimated Acceleration time for the axis is: {estTravelTime:.2f}s with a safety factor of {marginOfSafety:.2f}"
        )

        return estTravelTime

    def calcTimeForDecel(self, marginOfSafety=MARGIN_OF_SAFETY):
        print(f"Calculating expected travel time for axis deceleration")

        # Since this is just used for timeouts mostly I've used max vel
        # instead of actVel as there were issues with delays and actVel
        # not always being accurate
        actVel = self.getVelocityMax()
        decel = self.getDeceleration()

        if decel == 0:
            print(" Error: Can't divide by a deceleration of 0")
            return -1

        timeForDecel = abs(actVel / decel)

        print(f"Act Velocity={actVel:.2f}, Deceleration={decel:.2f}")

        estTravelTime = timeForDecel * marginOfSafety

        print(
            f"Estimated deceleration time for the axis is: {estTravelTime:.2f}s with a safety factor of {marginOfSafety:.2f}"
        )

        return estTravelTime

class PneumaticAxis:
    def __init__(self, plcConnection, axisNum):
        print("Constructor for axis")
        self.plc = plcConnection
        self.axisNum = axisNum

    def __del__(self):
        print("Destructor for pneumatic axis: going to fail safe state")
        self.setValveOff()

    # Generic function for getting any variable on the pneumatic axis
    def getGenericVariable(self, plcVarPath, plcVarType):
        plcVarName = f"GVL.astPneumaticAxes[{self.axisNum}].{plcVarPath}"
        returnValue = self.plc.connection.read_by_name(plcVarName, plcVarType)
        global prevPrintString
        printString = f"{plcVarName}=: {returnValue}"
        if prevPrintString != printString:
            print(f"{dateTimeObj.now()} {printString}")
        prevPrintString = printString
        return returnValue
    
    # Get ST_PneumaticAxisStatus variables
    def getExtendingStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bExtending", pyads.PLCTYPE_BOOL)

    def getRetractingStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bRetracting", pyads.PLCTYPE_BOOL)
    
    def getExtendedStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bExtended", pyads.PLCTYPE_BOOL)
    
    def getRetractedStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bRetracted", pyads.PLCTYPE_BOOL)

    def getSolenoidActiveStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bSolenoidActive", pyads.PLCTYPE_BOOL)

    def getInterlockedStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bInterlocked", pyads.PLCTYPE_BOOL)

    def getPSSPermitOKStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bPSSPermitOK", pyads.PLCTYPE_BOOL)
    
    def getErrorStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.bError", pyads.PLCTYPE_BOOL)
    
    def getTimeElapsedExtend(self):
         return self.getGenericVariable("stPneumaticAxisStatus.nTimeElapsedExtend", pyads.PLCTYPE_INT)

    def getTimeElapsedRetract(self):
        return self.getGenericVariable("stPneumaticAxisStatus.nTimeElapsedRetract", pyads.PLCTYPE_INT)

    def getStatus(self):
        return self.getGenericVariable("stPneumaticAxisStatus.sStatus", pyads.PLCTYPE_STRING)

    # Get ST_PneumaticAxisConfig variables
    def getTimeToExtend(self):
         return self.getGenericVariable("stPneumaticAxisConfig.nTimeToExtend", pyads.PLCTYPE_INT)

    def getTimeToRetract(self):
        return self.getGenericVariable("stPneumaticAxisConfig.nTimeToRetract", pyads.PLCTYPE_INT)
    
    # Get ST_PneumaticAxisInputs variables
    def getEndSwitchFwd(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bEndSwitchFwd", pyads.PLCTYPE_BOOL)

    def getEndSwitchBwd(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bEndSwitchBwd", pyads.PLCTYPE_BOOL)

    def getSolenoidActive(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bSolenoidActive", pyads.PLCTYPE_BOOL)

    def getPSSPermit(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bPSSPermit", pyads.PLCTYPE_BOOL)
    
    def getPressureExtend(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bPressureExtend", pyads.PLCTYPE_BOOL)

    def getPressureRetract(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bPressureRetract", pyads.PLCTYPE_BOOL)

    def getOpenManual(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bOpenManual", pyads.PLCTYPE_BOOL)

    def getCloseManual(self):
        return self.getGenericVariable("stPneumaticAxisInputs.bCloseManual", pyads.PLCTYPE_BOOL)

    def getAirPressureValve(self):
        return self.getGenericVariable("stPneumaticAxisInputs.nAirPressureValve", pyads.PLCTYPE_INT)

    def getPressureValue(self):
         return self.getGenericVariable("stPneumaticAxisInputs.nPressureValue", pyads.PLCTYPE_INT)

    # Get ST_PneumaticAxisOutputs variables
    def getValveState(self):
        return self.getGenericVariable("stPneumaticAxisOutputs.bValveOn", pyads.PLCTYPE_BOOL)

    def getAirPressureOnState(self):
        return self.getGenericVariable("stPneumaticAxisOutputs.bAirPressureOn", pyads.PLCTYPE_BOOL)

    # Generic function for setting any variable on the plc
    def setGenericVariable(self, plcVarPath, plcVarValue, plcVarType):
        plcVarName = f"GVL.astPneumaticAxes[{self.axisNum}].{plcVarPath}"
        print(f"{dateTimeObj.now()} {plcVarName}={plcVarValue}")
        self.plc.connection.write_by_name(plcVarName, plcVarValue, plcVarType)
    
    # Set ST_PneumaticAxisControl variables
    def extendPneumaticAxis(self):
        self.setGenericVariable("stPneumaticAxisControl.bExtend", True, pyads.PLCTYPE_BOOL)

    def retractPneumaticAxis(self):
        self.setGenericVariable("stPneumaticAxisControl.bRetract", True, pyads.PLCTYPE_BOOL)

    def interlockPneumaticAxis(self):
        self.setGenericVariable("stPneumaticAxisControl.bInterlock", True, pyads.PLCTYPE_BOOL)
    
    def resetPneumaticAxis(self):
        self.setGenericVariable("stPneumaticAxisControl.bReset", True, pyads.PLCTYPE_BOOL)

    # Set ST_PneumaticAxisConfig variables
    def setTimeToExtend(self, value):
         return self.setGenericVariable("stPneumaticAxisConfig.nTimeToExtend", value, pyads.PLCTYPE_INT)

    def setTimeToRetract(self, value):
        return self.setGenericVariable("stPneumaticAxisConfig.nTimeToRetract", value, pyads.PLCTYPE_INT)

     # Set ST_PneumaticAxisOutputs variables
    def setValveOn(self):
        self.setGenericVariable("stPneumaticAxisOutputs.bValveOn", True, pyads.PLCTYPE_BOOL)
    
    def setValveOff(self):
        self.setGenericVariable("stPneumaticAxisOutputs.bValveOn", False, pyads.PLCTYPE_BOOL)
    
    ###Motion commands###
    def extendAndWait(self):
        timeout = self.getTimeToExtend()
        self.extendPneumaticAxis()
        self.waitForExtended(timeoutExtended=timeout)
        return self.getExtendedStatus()

    def retractAndWait(self):
        timeout = self.getTimeToRetract()
        self.retractPneumaticAxis()
        self.waitForRetracted(timeoutRetracted=timeout)
        return self.getRetractedStatus()

    def ValveOffAndWait(self, timeoutMovement):
        self.setValveOff()
        self.waitForValveStateChange(timeoutMovementDone=timeoutMovement)
        return self.getValveState()

    def ValveONAndWait(self, timeoutMovement):
        self.setValveOn()
        self.waitForValveStateChange(timeoutMovementDone=timeoutMovement)
        return self.getValveState()

    # boolValue is the status you're waiting for
    # if you're waiting a bit to go high then this should be True
    def waitForStatusBit(
        self, getStatusBitFunction, boolValue, timeout=30, sleepInterval=SLEEP_INTERVAL
    ):
        # If timeout is negative time then just use a default
        if timeout < 0:
            timeout = 1

        timeLimit = time.time() + timeout
        timeoutError = False
        while True:
            statusBit = getStatusBitFunction()
            if statusBit == boolValue:
                break
            if time.time() > timeLimit:
                timeoutError = True
                break
            if sleepInterval > 0:
                time.sleep(sleepInterval)

        if timeoutError:
            print(
                f"  Axis {self.axisNum}: Timeout error waiting for {getStatusBitFunction.__name__} to return {boolValue}"
            )
            return False
        else:
            return True

    def waitForExtended(self, 
        timeoutExtended=30,
        timeoutRetractedFalse=3,
        timeoutExtending=3,
        sleepInterval=SLEEP_INTERVAL):

        if not self.waitForStatusBit(
            self.getRetractedStatus,
            False,
            timeout=timeoutRetractedFalse,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bRetracted status did not go low within {timeoutRetractedFalse} seconds"
            )
            return False
        if not self.waitForStatusBit(
            self.getExtendingStatus,
            True,
            timeout=timeoutExtending,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bExtending status did not go high within {timeoutExtending} seconds"
            )
            return False
        if not self.waitForStatusBit(
            self.getExtendedStatus,
            True,
            timeout=timeoutExtended,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bExtended status did not go high within {timeoutExtended} seconds"
            )
            return False
        return True

    def waitForRetracted(self,
        timeoutRetracted=30,
        timeoutExtendedFalse=3,
        timeoutRetracting=3,
        sleepInterval=SLEEP_INTERVAL):

        if not self.waitForStatusBit(
            self.getExtendedStatus,
            False,
            timeout=timeoutExtendedFalse,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bExtended status did not go low within {timeoutExtendedFalse} seconds"
            )
            return False
        if not self.waitForStatusBit(
            self.getRetractingStatus,
            True,
            timeout=timeoutRetracting,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bRetracting status did not go high within {timeoutRetracting} seconds"
            )
            return False
        if not self.waitForStatusBit(
            self.getRetractedStatus,
            True,
            timeout=timeoutRetracted,
            sleepInterval=sleepInterval,
        ):
            print(
                f"  Axis {self.axisNum} Error: bRetracted status did not go high within {timeoutRetracted} seconds"
            )
            return False
        return True
    
    def waitForSwitchStateChange(self, 
        timeoutMovementDone=30,
        timeoutEndSwitchOff=3,
        timeoutMoving=3,
        sleepInterval=SLEEP_INTERVAL):

        if self.getEndSwitchBwd():
            if not self.waitForStatusBit(
                self.getEndSwitchBwd,
                False,
                timeout=timeoutEndSwitchOff,
                sleepInterval=sleepInterval,
            ):
                print(
                    f"  Axis {self.axisNum} Error: bEndSwitchBwd status did not go low within {timeoutEndSwitchOff} seconds"
                )
                return False
            
            if not self.waitForStatusBit(
                self.getEndSwitchFwd,
                True,
                timeout=timeoutMovementDone,
                sleepInterval=sleepInterval,
            ):
                print(
                    f"  Axis {self.axisNum} Error: bEndSwitchFwd status did not go high within {timeoutMovementDone} seconds"
                )
                return False
            return True
        else:
            if not self.waitForStatusBit(
                self.getEndSwitchFwd,
                False,
                timeout=timeoutEndSwitchOff,
                sleepInterval=sleepInterval,
            ):
                print(
                    f"  Axis {self.axisNum} Error: bEndSwitchFwd status did not go low within {timeoutEndSwitchOff} seconds"
                )
                return False
            
            if not self.waitForStatusBit(
                self.getEndSwitchBwd,
                True,
                timeout=timeoutMovementDone,
                sleepInterval=sleepInterval,
            ):
                print(
                    f"  Axis {self.axisNum} Error: bEndSwitchBwd status did not go high within {timeoutMovementDone} seconds"
                )
                return False
            return True