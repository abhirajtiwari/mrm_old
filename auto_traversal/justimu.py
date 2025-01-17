import smbus
import time
import math


min_x=0
max_x=0
min_y=0
max_y=0
min_z=0
max_z=0

l=360-180
'''
('X OFFSET:', 1.9555)
('Y OFFSET:', 0.7795000000000001)

28 thursday
('X OFFSET:', 0.13050000000000006)
('Y OFFSET:', 1.0655000000000001)
'''
x_manual=1.6635
y_manual=0.8835

bus = smbus.SMBus(1)

def twos_complement(val, bits):
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val

bus.write_byte_data(0x1E, 0x20, 0b01111100)
bus.write_byte_data(0x1E, 0x21, 0b00000000)
bus.write_byte_data(0x1E, 0x22, 0b00000000)
bus.write_byte_data(0x1E, 0x23, 0b00001100)


def getHead():
    while(True):

        out_x_m_l = bus.read_byte_data(0x1E, 0x28)
        out_x_m_h = bus.read_byte_data(0x1E, 0x29)
        x = twos_complement((out_x_m_h << 8) | out_x_m_l, 16) / 1e3
        #print("X=", x, "gauss")



        out_y_m_l = bus.read_byte_data(0x1E, 0x2A)
        out_y_m_h = bus.read_byte_data(0x1E, 0x2B)
        y= twos_complement((out_y_m_h << 8) | out_y_m_l, 16) / 1e3
        #print("Y=", y, "gauss")


        out_z_m_l = bus.read_byte_data(0x1E, 0x2C)
        out_z_m_h = bus.read_byte_data(0x1E, 0x2D)
        z = twos_complement((out_z_m_h << 8) | out_z_m_l, 16) / 1e3
        #print("Z=",z, "gauss")

        print("")

        '''if x< min_x:
            min_x=x
        if x>max_x:
            max_x=x

        if y< min_y:
            min_y=y
        if y>max_y:
            max_y=y

        if z< min_z:
            min_z=z
        if z>max_z:
            max_z=z

        offset_x= (max_x + min_x) / 2
        offset_y =(max_y + min_y) / 2
        offset_z =(max_z + min_z) / 2'''

        #x=x-offset_x
        #y=y-offset_y
        #z=z-offset_z
        x=x-x_manual
        y=y-y_manual

        degree= math.atan2(y,x)*180/math.pi

        if degree<0:
            degree +=360

        degree = (degree+l)% 360

        return degree

        #print("HEADING:", degree)
        #print("xoffset:",x)
        #print("yoffset:",y)

