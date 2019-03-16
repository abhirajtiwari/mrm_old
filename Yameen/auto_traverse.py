import smbus
import time
import math as m
from gps3 import gps3
import numpy as np
import RPi.GPIO as GPIO

add=0x1e

lat2 = 13.3478
lon2 = 74.79223
#lat1=0.000000
#lon1=0.000000
#distance = 0.000000
degree = 0.000000

gpsdsock = gps3.GPSDSocket()
data = gps3.DataStream()
gpsdsock.connect()
gpsdsock.watch()


adjustment=360
x_manual=-0.2125
y_manual=0.8025

i2c=smbus.SMBus(1)
i2c.write_byte_data(add,0x20,0b01011100)#high performance
i2c.write_byte_data(add,0x21,0b00000000)#4 gauss range
i2c.write_byte_data(add,0x22,0b00000000)
i2c.write_byte_data(add,0x23,0b00001000)

GPIO.setmode(GPIO.BCM)

echo_left = 26
trigger_left = 19
echo_right = 11
trigger_right = 9
echo_side_l = 16
trigger_side_l = 20
echo_side_r = 25
trigger_side_r = 8

ldir = 5
rdir = 23
lspeed = 13
rspeed = 18

min_x=0
max_x=0
min_y=0
max_y=0
min_z=0
max_z=0

GPIO.setup(trigger_left, GPIO.OUT)
GPIO.setup(echo_left, GPIO.IN)

GPIO.setup(trigger_right, GPIO.OUT)
GPIO.setup(echo_right, GPIO.IN)
      
GPIO.setup(trigger_side_l, GPIO.OUT)
GPIO.setup(echo_side_l, GPIO.IN)

GPIO.setup(trigger_side_r, GPIO.OUT)
GPIO.setup(echo_side_r, GPIO.IN)


GPIO.setup(ldir, GPIO.OUT)
GPIO.setup(rdir,GPIO.OUT)
GPIO.setup(lspeed, GPIO.OUT)
GPIO.setup(rspeed,GPIO.OUT)

pwm_l=GPIO.PWM(lspeed,100)
pwm_r=GPIO.PWM(rspeed,100)
pwm_l.start(50)
pwm_r.start(50)


def Ultrasonic(pin,pin2):
	time.sleep(0.1)
	GPIO.output(pin2,False)
	time.sleep(0.001)

	GPIO.output(pin2,True)
	time.sleep(0.00001)
	GPIO.output(pin2,False)

	while GPIO.input(pin)==0:
		pass
	pulse_begins = time.time()
	
	while GPIO.input(pin)==1:
		pulse_stops = time.time()
		if (pulse_stops-pulse_begins>0.004):
			pulse_duration = pulse_stops-pulse_begins
			distance = pulse_duration*34000/2
			return distance,'not alert'
			break
	
	pulse_duration = pulse_stops-pulse_begins
	distance = pulse_duration*34000/2
	return distance,'alert'


def twos_comp(val, bits):
	"""compute the 2's comp of int value val"""
	if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
		val = val - (1 << bits)		# compute negative value
	return val


def Bearing(lat2,lon2):
	for new_data in gpsdsock:
		if new_data:
			data.unpack(new_data)
			lat1 = data.TPV['lat']
			lon1 = data.TPV['lon']
			#print('inside if')

			if (lat1 == 'n/a'):
				continue
			if (lon1 == 'n/a'):
				continue
		# convert to radians
			dLat = (lat2 - lat1) * m.pi / 180.0
			dLon = (lon2 - lon1) * m.pi / 180.0

		# convert to radians
			lat1 = (lat1) * m.pi / 180.0
			lat2 = (lat2) * m.pi / 180.0

			y = m.cos(lat2) * m.sin(dLon)
			x = (m.cos(lat1) * m.sin(lat2)) - (m.sin(lat1) * m.cos(lat2) * m.cos(dLon))
			degree = m.atan2(y, x) * 180 / m.pi

			if degree < 0:
				degree += 360

		# apply formulae
			a = (pow(m.sin(dLat / 2), 2) + pow(m.sin(dLon / 2), 2) * m.cos(lat1) * m.cos(lat2))
			rad = 6378.1*1000
			c = 2 * m.asin(m.sqrt(a))

			distance = rad * c
			print('dist',distance)
			return distance, degree

def state(st1,st2,st3,st4):
	#lspeed.ChangeDutyCycle(50)
	#rspeed.ChangeDutyCycle(50)
	GPIO.output(ldir,st1)
	GPIO.output(rdir,st3)
	if (st1 != st3):
		pwm_l.ChangeDutyCycle(50)
		pwm_r.ChangeDutyCycle(50)
	else:
		pwm_l.ChangeDutyCycle(50)
		pwm_r.ChangeDutyCycle(50)
	#GPIO.output(lspeed,st2)
	#GPIO.output(rspeed,st4)


def LSM(min_x,max_x,min_y,max_y,min_z,max_z):
		out_x_m_l = i2c.read_byte_data(0x1E, 0x28)
		out_x_m_h = i2c.read_byte_data(0x1E, 0x29)
		x = twos_comp((out_x_m_h << 8) | out_x_m_l, 16) / 1e3

		out_y_m_l = i2c.read_byte_data(0x1E, 0x2A)
		out_y_m_h = i2c.read_byte_data(0x1E, 0x2B)
		y = twos_comp((out_y_m_h << 8) | out_y_m_l, 16) / 1e3


		out_z_m_l = i2c.read_byte_data(0x1E, 0x2C)
		out_z_m_h = i2c.read_byte_data(0x1E, 0x2D)
		z = twos_comp((out_z_m_h << 8) | out_z_m_l, 16) / 1e3
		
		if x< min_x:
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
		offset_z =(max_z + min_z) / 2

		x=x-x_manual
		y=y-y_manual
		z=z-offset_z


		heading = m.atan2(y,x)*180/m.pi

		if heading<0:
			heading +=360


		heading=(heading+adjustment)%360

		#print("HEADING is", heading)


		dist, deg = Bearing(lat2, lon2)
		print('head',heading)
		print('deg',deg)

	###########degree is angle of the given gps coordinate from the north
	###########heading is the orientation of the imu from north
		turn = heading - deg
		
		if dist<5:
			print('destination reached')
			state(0,0,0,0)
			quit()
		print('turn',turn)
		return turn,heading




while True:
	#time.sleep(0.1)
	try:
		turning, head = LSM(min_x, max_x, min_y, max_y, min_z, min_z)

		dist_lf,alert_lf = Ultrasonic(echo_left,trigger_left)
		dist_rf,alert_rf = Ultrasonic(echo_right,trigger_right)
		dist_sl, alert_l = Ultrasonic(echo_side_l,trigger_side_l)
		dist_sr, alert_r = Ultrasonic(echo_side_r,trigger_side_r)
		
		print(alert_l,alert_lf,alert_rf,alert_r)
		
		
		if ((alert_lf == 'alert' and alert_rf == 'not alert') or (alert_lf == 'alert' and alert_rf == 'alert')):
			turning, init_head = LSM(min_x, max_x, min_y, max_y, min_z, min_z)
			while True:
				print('Turn Right')
				print(abs(head-init_head))
				state(1,1,0,1)
				turning, head = LSM(min_x, max_x, min_y, max_y, min_z, min_z)
				if (abs(head-init_head)<75 or abs(head-init_head)>295):
					continue
				dist_lf,alert_lf = Ultrasonic(echo_left,trigger_left)
				dist_rf,alert_rf = Ultrasonic(echo_right,trigger_right)
				dist_sl, alert_l = Ultrasonic(echo_side_l,trigger_side_l)
				dist_sr, alert_r = Ultrasonic(echo_side_r,trigger_side_r)
				break

		elif (alert_rf == 'alert' and alert_lf == 'not alert'):
			turning, init_head = LSM(min_x, max_x, min_y, max_y, min_z, min_z)
			while True:
				print('Turn Left')
				print(abs(head-init_head))
				state(0,1,1,1)
				turning, head = LSM(min_x, max_x, min_y, max_y, min_z, min_z)
				if (abs(head-init_head)<75 or abs(head-init_head)>295):
					continue
				dist_lf,alert_lf = Ultrasonic(echo_left,trigger_left)
				dist_rf,alert_rf = Ultrasonic(echo_right,trigger_right)
				dist_sl, alert_l = Ultrasonic(echo_side_l,trigger_side_l)
				dist_sr, alert_r = Ultrasonic(echo_side_r,trigger_side_r)
				break		
			
		

		if (alert_rf == 'not alert' and alert_lf == 'not alert'):
			if (alert_r == 'alert' and alert_l == 'not alert'):
				if((turning)<0 and (turning)<=-195):
					print('anti-clock1', 360 + turning)
					#print('turning',turning)
					state(0,1,1,1)
				elif((turning)>15 and (turning)<165):
					print('anti-clock2', turning)
					#print('turning',turning)
					state(0,1,1,1)
				else:
					print('go straight in 1')
					state(1,1,1,1)
			elif (alert_l == 'alert' and alert_r == 'not alert'):
				if((turning)<-15 and (turning)>-165):
					print('clock1', -turning)
					#print('turning',turning)
					state(1,1,0,1)
				elif((turning)>0 and (turning)>=195):
					print('clock2', 360 - turning)
					#print('turning',turning)
					state(1,1,0,1)
				else:
					print('go straight in 2')
					state(1,1,1,1)
			elif (alert_r == 'not alert' and alert_l == 'not alert'):
				if((turning)<0 and (turning)<=-195):
					print('anti-clock1 in not', 360 + turning)
					#print('turning',turning)
					state(0,1,1,1)
				elif((turning)>15 and (turning)<165):
					print('turning',  	turning)
					print('anti-clock2 in not', turning)
					#print('turning',turning)
					state(0,1,1,1)
				elif((turning)<-15 and (turning)>-165):
					print('clock1 in not', -turning)
					#print('turning',turning)
					state(1,1,0,1)
				elif((turning)>0 and (turning)>=195):
					print('clock2 in not', 360 - turning)
					#print('turning',turning)
					state(1,1,0,1)
				else:
					print('go straight in 3')
					state(1,1,1,1)
			else:
				print('straight')
				state(1,1,1,1)
	
	#print('___________________________')

	except KeyboardInterrupt:
		GPIO.cleanup()