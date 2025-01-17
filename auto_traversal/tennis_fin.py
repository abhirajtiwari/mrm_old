import cv2
import matplotlib.pyplot as plt
import numpy as np
import time
import serial
# import client_encoded
import rec_UDP

#######TEMPORARY TCP COMMS FOR JUST RPI OP############
#Finally these commands should be replaced by atmega wireless calls
import socket
comm_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

host = socket.gethostname()

port = 1234
while True:
    try:
        comm_sock.bind(('', port))
        print 'opened socket at ', port
        break
    except socket.error:
        port += 1

comm_sock.listen(5)
comm_con, comm_addr = comm_sock.accept()

def tcp_send(data):
    comm_con.sendall(data)
######################################################

# ser = serial.Serial('/dev/ttyUSB0', 9600)
stopped = False

detected= False
started = False
votes_thresh = 8
# votes_thresh = 100
# frame_changed = False

cap = cv2.VideoCapture(0)
# count = 217 #photo count for testing

def adjust_gamma(image, gamma=1.0):
    if gamma == 0:
        gamma = 0.01
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
                      for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

while True and detected == False:
    if stopped == False:
        # ser.write('r')
        tcp_send('r')
    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    
    # _, un_frame = cap.read()
    un_frame = rec_UDP.getCameraFrame()
    if un_frame is None:
        print 'None image'
        continue
    # un_frame = client_encoded.getCameraFrame()
    # time.sleep(3)
    # count += 1
    # un_frame = cv2.imread('/home/abhiraj/Mars Rover Manipal/dataset/Day 1/Final Ball day1/{}.jpg'.format(count))
    # frame = cv2.GaussianBlur(un_frame, (5,5), 0)
    frame = np.copy(un_frame)

    gamma = 0.15
    # gamma = 1
    frame = adjust_gamma(frame, gamma=gamma)

    frame_HSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([29, 60, 20])
    upper_green = np.array([64, 255, 255])

    mask = cv2.inRange(frame_HSV, lower_green, upper_green)
    mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)))
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)), iterations=13)

    cv2.imshow('mask', mask)

    _, conts, hei = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    conts = np.array(conts)

###################################
    if started == False:
        started = True
        time_start = time.time()
        voter = np.zeros((32, 24)) ###inc thresh
    time_elapsed = time.time() - time_start

    if np.amax(voter) >= votes_thresh and started == True:
        started = False
        indices = np.where(voter == np.amax(voter))
        # print indices
        final_frame = cv2.circle(un_frame, (indices[0]*20, indices[1]*20) , 3, (255,0,0), 3) 
        detected = True
        print 'final ball detected'
        break

    if time_elapsed > 1:
        print 'voter reset'
        started = False
##################################

    if len(conts) > 0:
        for i, contour in enumerate(conts):
            (x,y), rad = cv2.minEnclosingCircle(contour)
            frame = cv2.circle(frame, (int(x), int(y)), 0, (0,0,255), 4)
            x1, y1, w, h = cv2.boundingRect(contour)
            # box = cv2.minAreaRect(contour)
            # if box[1][0]/box[1][1] 
            # print box
            moments = cv2.moments(contour)
            cx = int(moments['m10']/moments['m00'])
            cy = int(moments['m01']/moments['m00'])
            p = (w/100 + h/100)/2
            x1 = int(x1 - p)
            y1 = int(y1 - p)
            x2 = int(x1+w+p)
            y2 = int(y1+h+p)
            x1 = 0 if x1<0 else x1
            y1 = 0 if y1<0 else y1
            # frame = cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
            # r = un_frame[y1:y2, x1:x2] #r is roi
            r = un_frame[y1:y2, x1:x2, 1] 
            # cv2.imshow("r", exp_r)
            # r = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)
            # r = exp_r
            # hist = cv2.calcHist(r, [0], None, [256], [0,256]) 
            # if np.mean(hist[200:,0]) > np.mean(hist[:199,0]):
            #     r = cv2.bitwise_not(r)
            #     print 'inv'
            # print 'not'
            # r = cv2.equalizeHist(r) 
            # cv2.imshow('roi', r)
            # r = exp_r ##########################
            r = cv2.medianBlur(r, 3)
            # r = cv2.GaussianBlur(r, (5, 5), 1)
            # r = cv2.adaptiveThreshold(r, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 3, 0) ##ADDED NOW
            # j = cv2.Canny(r, 20, 200)
            # cv2.imshow('fin', j)
            # plt.plot(hist)
            # plt.pause(0.5)
            # cv2.imshow('r', r)
            # circles = cv2.HoughCircles(r , cv2.HOUGH_GRADIENT, 1, int(w), param1=128, param2=15, minRadius=int(w/6), maxRadius=int(w/2)) 

            #Try stronger hough params and stop the servo if a circle is detected, at the same time ensuring frames don't overlap with some buffer
            circles = cv2.HoughCircles(r , cv2.HOUGH_GRADIENT, 1, int(w), param1=128, param2=15, minRadius=int(w/6), maxRadius=int(w/2)) 
            stringent_circles = cv2.HoughCircles(r , cv2.HOUGH_GRADIENT, 1, int(w), param1=150, param2=30, minRadius=int(w/6), maxRadius=int(w/2)) 
            if stringent_circles is not None and detected == False:
                # ser.write('s')
                tcp_send('s')
                stopped = True
                print '############################################################# stop rotating ###################'
            else:
                stopped = False

            if circles is not None and detected == False:
                # if started == False:
                #     started = True
                #     time_start = time.time()
                #     voter = np.zeros((64, 48))
                time_elapsed = time.time() - time_start

                if started == True and time_elapsed < 1 and np.amax(voter) < votes_thresh:
                    # time_elapsed = time.time() - time_start
                    # print circles.shape
                    for circle in circles:
                        if ((cx-int(x1+circle[0][0]))**2 + (cy-int(y1+circle[0][1]))**2 - circle[0][2]**1.5) > 0: ###EDITED
                            continue
                        voter[int((x1+circle[0][0])/20), int((y1+circle[0][1])/20)] += 1
                        print 'voted'
                        # print voter
                        frame = cv2.circle(frame, (int(x1+circle[0][0]), int(y1+circle[0][1])), circle[0][2], (255,0,0), 3) 

                        time_elapsed = time.time() - time_start
                        if np.amax(voter) >= votes_thresh and started == True:
                            started = False
                            indices = np.where(voter == np.amax(voter))
                            # print indices
                            final_frame = cv2.circle(un_frame, (indices[0]*20, indices[1]*20) , 3, (255,0,0), 3) 
                            # detected = True
                            print 'final ball detected'
                            cv2.imshow('final_frame', final_frame)
                            tcp_send('d')
                            cv2.waitKey(0)
                            cv2.destroyWindow('final_frame')
                            # break
                        # if time_elapsed > 2:
                        #     print 'voter reset'
                        #     started = False


    # cv2.imshow('mask', mask)
    cv2.imshow('result',frame)

cv2.destroyAllWindows()
cv2.imshow('final_frame', final_frame)
# ser.write('q')
cv2.waitKey(0)
cv2.destroyAllWindows()
# ser.close()
tcp_send('d') 
comm_con.close()
comm_sock.close()
