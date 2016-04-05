#!/usr/bin/python
#
# Copyright (c) 2009, Georgia Tech Research Corporation
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Georgia Tech Research Corporation nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY GEORGIA TECH RESEARCH CORPORATION ''AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL GEORGIA TECH BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

## Controlling Robotis Dynamixel RX-28 & RX-64 servos from python
## using the USB2Dynamixel adaptor.

## Authors: Travis Deyle, Advait Jain & Marc Killpack (Healthcare Robotics Lab, Georgia Tech.)

import time
import thread
import sys, optparse
import math
import string
import serial_manager

class Robotis_Servo():
    ''' Class to use a robotis RX-28 or RX-64 servo.
    '''
    def __init__(self, SerialManager, servo_id):
        ''' USB2Dynamixel - USB2Dynamixel_Device object to handle serial port.
                            Handles threadsafe operation for multiple servos
            servo_id - servo ids connected to USB2Dynamixel 1,2,3,4 ... (1 to 253)
                       [0 is broadcast if memory serves]
            series - Just a convenience for defining "good" defaults on MX series.
                     When set to "MX" it uses these values, otherwise it uses values
                     better for AX / RX series.  Any of the defaults can be overloaded
                     on a servo-by-servo bases in servo_config.py
        '''
        defaults = {
            'home_encoder': 0x7FF,
            'max_encoder': 0xFFF,
            'rad_per_enc': math.radians(360.0) / 1024, 
            'max_ang': math.radians(180),
            'min_ang': math.radians(-180),
            'flipped': False,
            'max_speed': math.radians(360)
        }

        self.position = 1800

        # Error Checking
        if SerialManager == None:
            raise RuntimeError('lib_robotis: Robotis Servo requires serial connection!\n')
        else:
            self.dyn = SerialManager

        # ID exists on bus?
        self.servo_id = servo_id
        try:
            self.read_address(3)
        except:
            raise RuntimeError('lib_robotis: Error encountered.  Could not find ID (%d)\n' %( servo_id ))

        # Set Return Delay time - Used to determine when next status can be requested
        data = self.read_address( 0x05, 1)
        self.return_delay = data[0] * 2e-6

        # Set various parameters.  Load from servo_config.
        self.settings = {}
        try:
            import servo_config as sc
            if sc.servo_param.has_key( self.servo_id ):
                self.settings = sc.servo_param[ self.servo_id ]
            else:
                print 'Warning: servo_id ', self.servo_id, ' not found in servo_config.py.  Using defaults.'
        except:
            print 'Warning: servo_config.py not found.  Using defaults.'

        # Set to default any parameter not specified in servo_config
        for key in defaults.keys():
            if self.settings.has_key( key ):
                pass
            else:
                self.settings[ key ] = defaults[ key ]

    def init_cont_turn(self):
        '''sets CCW angle limit to zero and allows continuous turning (good for wheels).
        After calling this method, simply use 'set_angvel' to command rotation.  This 
        rotation is proportional to torque according to Robotis documentation.
        '''
        self.write_address(0x08, [0,0])

    def kill_cont_turn(self):
        '''resets CCW angle limits to allow commands through 'move_angle' again
        '''
        self.write_address(0x08, [255, 3])

    def is_moving(self):
        ''' returns True if servo is moving.
        '''
        data = self.read_address( 0x2e, 1 )
        return data[0] != 0

    def read_voltage(self):
        ''' returns voltage (Volts)
        '''
        data = self.read_address( 0x2a, 1 )
        return data[0] / 10.

    def read_temperature(self):
        ''' returns the temperature (Celcius)
        '''
        data = self.read_address( 0x2b, 1 )
        return data[0]

    def read_load(self):
        ''' number proportional to the torque applied by the servo.
            sign etc. might vary with how the servo is mounted.
        '''
        data = self.read_address( 0x28, 2 )
        load = data[0] + (data[1] >> 6) * 256
        if data[1] >> 2 & 1 == 0:
            return -1.0 * load
        else:
            return 1.0 * load

    def read_encoder(self):
        ''' returns position in encoder ticks
        '''
        data = self.read_address( 0x24, 2 )
        enc_val = data[0] + data[1] * 256
        return enc_val

    def read_angle(self):
        ''' returns the current servo angle (radians)
        '''
        ang = (self.read_encoder() - self.settings['home_encoder']) * self.settings['rad_per_enc']
        if self.settings['flipped']:
            ang = ang * -1.0
        return ang

    def read_propGain(self):
        data = self.read_address( 0X1C , 1 )
        return data[0]

    def write_propGain(self, value):
        if value > 0:
            data = self.write_address( 0X1C , [value] )

    def read_dervGain(self):
        data = self.read_address( 0X1A , 1 )
        return data[0]

    def write_dervGain(self, value):
        if value > 0:
            data = self.write_address( 0X1A , [value] )

    def read_intGain(self):
        data = self.read_address( 0X1B , 1 )
        return data[0]

    def write_intGain(self, value):
        if value > 0:
            data = self.write_address( 0X1B , [value] )

    def move_angle(self, ang, angvel=None, blocking=True):
        ''' move to angle in DEGREES
        '''
        #print "angle: "+ang
        if not isinstance(ang, float) or not isinstance(ang, int):
            ang= float(ang)
        #ang= math.radians(ang) #comment out for rads
        if angvel == None:
            angvel = self.settings['max_speed']

        if angvel > self.settings['max_speed']:
            print 'lib_robotis.move_angle: angvel too high - %.2f deg/s' % (math.degrees(angvel))
            print 'lib_robotis.ignoring move command.'
            return

        if ang > self.settings['max_ang'] or ang < self.settings['min_ang']:
            print 'lib_robotis.move_angle: angle out of range- ', math.degrees(ang)
            print 'lib_robotis.ignoring move command.'
            return
        
        self.set_angvel(angvel)

        if self.settings['flipped']:
            ang = ang * -1.0
        enc_tics = int(round( ang / self.settings['rad_per_enc'] ))
        enc_tics += self.settings['home_encoder']
        self.move_to_encoder( enc_tics )

        if blocking == True:
            while(self.is_moving()):
                continue

    def move_to_encoder(self, n):
        ''' move to encoder position n
        '''
        # In some border cases, we can end up above/below the encoder limits.
        #   eg. int(round(math.radians( 180 ) / ( math.radians(360) / 0xFFF ))) + 0x7FF => -1
        n = min( max( n, 0 ), self.settings['max_encoder'] ) 
        hi,lo = n / 256, n % 256
        return self.write_address( 0x1e, [lo,hi] )

    def enable_torque(self):
        return self.write_address(0x18, [1])

    def disable_torque(self):
        return self.write_address(0x18, [0])

    def set_angvel(self, angvel):
        ''' angvel - in rad/sec
        '''     
        rpm = angvel / (2 * math.pi) * 60.0
        angvel_enc = int(round( rpm / 0.111 ))
        if angvel_enc<0:
            hi,lo = abs(angvel_enc) / 256 + 4, abs(angvel_enc) % 256
        else:
            hi,lo = angvel_enc / 256, angvel_enc % 256
        
        return self.write_address( 0x20, [lo,hi] )

    def write_id(self, id):
        ''' changes the servo id
        '''
        return self.write_address( 0x03, [id] )

    def __calc_checksum(self, msg):
        chksum = 0
        for m in msg:
            chksum += m
        chksum = ( ~chksum ) % 256
        return chksum

    def set_cw_limit(self, cw_limit):
        ''' set the clockwise servo limit
        '''
        self.write_address(0x06, [cw_limit % 256, cw_limit / 256])

    def set_ccw_limit(self, ccw_limit):
        ''' set the counterclockwise servo limit
        '''
        self.write_address(0x08, [ccw_limit % 256, ccw_limit / 256])

    def read_multi_offset(self):
        ''' gets the offset in multi-turn mode
        '''
        return self.read_address(0x14, 2)

    def set_multi_offset(self, offset):
        ''' sets the offset in multi-turn mode
        '''
        self.write_address(0x14, [offset % 256, offset / 256])

    def read_address(self, address, nBytes=1):
        ''' reads nBytes from address on the servo.
            returns [n1,n2 ...] (list of parameters)
        '''
        msg = [ 0x02, address, nBytes ]
        return self.send_instruction( msg, self.servo_id )

    def write_address(self, address, data):
        ''' writes data at the address.
            data = [n1,n2 ...] list of numbers.
            return [n1,n2 ...] (list of return parameters)
        '''
        msg = [ 0x03, address ] + data
        return self.send_instruction( msg, self.servo_id )

    def send_instruction(self, instruction, id):
        msg = [ id, len(instruction) + 1 ] + instruction # instruction includes the command (1 byte + parameters. length = parameters+2)
        chksum = self.__calc_checksum( msg )
        msg = [ 0xff, 0xff ] + msg + [chksum]
        
        self.dyn.acq_mutex()

        try:
            self.send_serial( msg )
            data, err = self.receive_reply()
        except:
            self.dyn.rel_mutex()
            raise
        self.dyn.rel_mutex()
        
        if err != 0:
            self.process_err( err )

        return data

    def process_err( self, err ):
        raise RuntimeError('lib_robotis: An error occurred: %d\n' % err)

    def receive_reply(self):
        start = self.dyn.read_serial( 2 )
        if start != '\xff\xff':
            raise RuntimeError('lib_robotis: Failed to receive start bytes\n')
        servo_id = self.dyn.read_serial( 1 )
        if ord(servo_id) != self.servo_id:
            raise RuntimeError('lib_robotis: Incorrect servo ID received: %d\n' % ord(servo_id))
        data_len = self.dyn.read_serial( 1 )
        err = self.dyn.read_serial( 1 )
        data = self.dyn.read_serial( ord(data_len) - 2 )
        checksum = self.dyn.read_serial( 1 ) # I'm not going to check...
        return [ord(v) for v in data], ord(err)

    def send_serial(self, msg):
        """ sends the command to the servo
        """
        out = ''
        for m in msg:
            out += chr(m)
        self.dyn.serial_io.write( out )

    def move_cw(self):
        self.move(20)
        print "Moving Dynamixel"

    def move_ccw(self):
        self.move(-20)
        print "Moving Dynamixel"

    def move(self, adjustment):
        self.position = self.position + adjustment
        self.position = min(self.position, 4095)
        self.position = max(1, self.position)
        self.move_to_encoder(int(self.position))

    def send_command(self, command):
        print command
        #self.manager.acquire_mutex()
        self.manager.serial_io.write(command)
        #self.manager.release_mutex()