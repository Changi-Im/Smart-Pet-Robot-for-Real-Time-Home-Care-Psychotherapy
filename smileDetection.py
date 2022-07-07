from __future__ import print_function
import cv2
import mediapipe as mp
import timeit
import argparse
import imutils
import time
from time import sleep
import os
import RPi.GPIO as GPIO
import serial

eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')
smile_cascade = cv2.CascadeClassifier('haarcascade_smile.xml')

mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils


panPin = 3
tiltPin = 2

global panServoAngle
panServoAngle = 90
global tiltServoAngle
tiltServoAngle =90
servoSignal = '0'

ser = serial.Serial(                 # serial 객체 생성
        port='/dev/ttyAMA1',         # 시리얼통신에 사용할 포트
        baudrate=115200,                # 통신속도 지정
        parity=serial.PARITY_NONE,       # 패리티 비트 설정방식
        stopbits=serial.STOPBITS_ONE,     # 스톱비트 지정
        bytesize=serial.EIGHTBITS,        # 데이터 비트수 지정
        timeout=1                        # 타임아웃 설정
        )

def setServoAngle(servo, angle):
	assert angle >=10 and angle <= 150
	pwm = GPIO.PWM(servo, 50)
	pwm.start(8)
	dutyCycle = angle / 18. + 3.
	pwm.ChangeDutyCycle(dutyCycle)
	sleep(0.01)
	pwm.stop()
	
def setGPIO(servo, angle):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(servo, GPIO.OUT)
    setServoAngle(servo, angle)
    GPIO.cleanup()
        
def servoPosition(x, y):
    global panServoAngle
    global tiltServoAngle
    if (x > 170):
        panServoAngle += 10
        if panServoAngle > 140:
            panServoAngle = 140
        setGPIO(panPin, panServoAngle)

    if (x < 150):
        panServoAngle -= 10
        if panServoAngle < 10:
            panServoAngle = 10
        setGPIO(panPin, panServoAngle)

    if (y < 110):
        tiltServoAngle += 10
        if tiltServoAngle > 140:
            tiltServoAngle = 140
        setGPIO(panPin, panServoAngle)

    if (y > 130):
        tiltServoAngle -= 10
        if tiltServoAngle < 40:
            tiltServoAngle = 40
        setGPIO(panPin, panServoAngle)
        
def smile():
    global servoSignal
    cap = cv2.VideoCapture(0)
    cap.set(3, 320) # 중앙 160 150 < cx < 170
    cap.set(4, 240) # 중앙 120 110 < cy < 130
    with mp_face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5) as face_detection:
      while cap.isOpened():
        success, image = cap.read()
        r = image.shape[0]
        c = image.shape[1]
        if not success:
          print("웹캠을 찾을 수 없습니다.")
          # 비디오 파일의 경우 'continue'를 사용하시고, 웹캠에 경우에는 'break'를 사용하세요.
          continue
        # 보기 편하기 위해 이미지를 좌우를 반전하고, BGR 이미지를 RGB로 변환합니다.
        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    	# 성능을 향상시키려면 이미지를 작성 여부를 False으로 설정하세요.
        image.flags.writeable = False
        results = face_detection.process(image)

        # 영상에 얼굴 감지 주석 그리기 기본값 : True.
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        if results.detections:
           for detection in results.detections:
             servoSignal = '0'
             bounding_box = detection.location_data.relative_bounding_box
             x = int(bounding_box.xmin * c)
             w = int(bounding_box.width * c)

             y = int(bounding_box.ymin * r)
             h = int(bounding_box.height * r)
            
             cx = (2 * x + w) // 2  # center of width
             cy = (2 * y + h) // 2  # center of height
             servoPosition(cx, cy)
             cv2.rectangle(image, (x, y), (x + w, y + h), color=(255, 255, 255), thickness=2)
             cv2.circle(image, (cx, cy), 5, (255, 0, 0), -1)
             roi_gray = gray[y:y + h, x:x + w]
             roi_color = image[y:y + h, x:x + w]

             smiles = smile_cascade.detectMultiScale(roi_gray, 1.2, 20)
             for (sx, sy, sw, sh) in smiles:
                 cv2.rectangle(roi_color, (sx, sy), ((sx + sw), (sy + sh)), (0, 0, 255), 2)
                 servoSignal = '1'
        cv2.imshow('MediaPipe Face Detection', image)
         
        if servoSignal == '1':
            ser.write((servoSignal).encode())
        if cv2.waitKey(5) & 0xFF == 27:
            break
    cap.release()
    
def googleAssistant():
    os.system("python3 /home/pi/assistant-sdk-python/google-assistant-sdk/googlesamples/assistant/grpc/pushtotalk.py")
    
def smile_thread():
	thread=threading.Thread(target=smile) #thread를 동작시킬 함수를 target 에 대입해줍니다
	thread.daemon=True #프로그램 종료시 프로세스도 함께 종료 (백그라운드 재생 X)
	thread.start() #thread를 시작합니다

if __name__ == "__main__":
	smile() # 웃는 얼굴만 테스트
	
	# 웃는 얼굴 백그라운드 실행, google assisant 동작
	'''
    smile_thread()
	googleAssistant()
	''' 