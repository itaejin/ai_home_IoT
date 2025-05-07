# 얼굴 인식 + 현관문 초음파 센서 + LED 제어 + EMQ X Broker

import cv2
import numpy as np
import paho.mqtt.client as mqtt_client
from os import listdir
from os.path import isdir, isfile, join
from PIL import ImageFont, ImageDraw, Image, ImageTk
import tkinter as tk
from gpiozero import Servo
from gpiozero import LED
from gpiozero import DistanceSensor
from time import sleep, time
import threading

# MQTT 설정
broker = '192.168.0.36'
port = 1883
topic = "sensor/facetime"
client_id = 'qwer_facetime'
username = 'facetime'  # 여기에 사용자 이름 입력
password = '1q2w3e4r'  # 여기에 비밀번호 입력

# LED 핀 설정 (신발장)
led1 = LED(3)

#초음파핀 설정
TRIG = 5
ECHO = 6
sensor = DistanceSensor(echo=ECHO, trigger=TRIG)


# 서보모터 핀 설정 (BCM 모드 기준)
servo_pin = 18  # GPIO 18번 핀 사용

# 서보모터 객체 생성
# min_pulse_width와 max_pulse_width는 서보모터의 특성에 따라 조정할 수 있습니다.
servo = Servo(servo_pin, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, frame_width=20/1000)

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("MQTT Broker 연결 성공!")
        else:
            print("연결 실패, 코드로 돌아갑니다. %d\n", rc)
    
    client = mqtt_client.Client(client_id=client_id)  # 기본 API 사용
    client.username_pw_set(username, password)  # 사용자 이름과 비밀번호 설정
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def publish(client, distance):
    result = client.publish(topic, distance)
    status = result[0]
    if status == 0:
        print(f"Sent `Distance: {distance:.2f} cm` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic {topic}")


# 각도 설정 함수
def setServoPos(degree):
    # 각도는 180도를 넘을 수 없다.
    if degree > 180:
        degree = 180
    
    # GPIOZero의 Servo 클래스는 -1(0도)에서 1(180도)까지 범위를 가집니다.
    # 따라서, 각도를 -1에서 1 사이의 값으로 변환합니다.
    position = (degree / 180.0) * 2 - 1
    print(f"Degree: {degree} to Position: {position}")
    
    # 서보의 위치를 설정합니다.
    servo.value = position

    # 서보모터가 움직임을 멈춘 후 PWM 신호를 끊어 모터를 중지
    sleep(0.5)  # 모터가 움직일 시간 대기
    servo.detach()  # 모터에 신호를 중단하여 가만히 있게 만듦


# 데이터 경로 설정
data_path = '/home/qwer/project/face'

# 사용자 디렉토리 리스트 얻기
user_dirs = [d for d in listdir(data_path) if isdir(join(data_path, d))]

# 데이터와 매칭될 라벨 변수
Training_Data, Labels = [], []

# 사용자 디렉토리 각각에 대해 루프
for label, user_dir in enumerate(user_dirs):
    user_path = join(data_path, user_dir)
    onlyfiles = [f for f in listdir(user_path) if isfile(join(user_path, f))]
    
    # 각 디렉토리 내의 파일 개수 만큼 루프
    for files in onlyfiles:
        image_path = join(user_path, files)
        # 이미지 불러오기
        images = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        # 이미지 파일이 아니거나 못 읽어 왔다면 무시
        if images is None:
            continue
        # Training_Data 리스트에 이미지를 바이트 배열로 추가
        Training_Data.append(np.asarray(images, dtype=np.uint8))
        # Labels 리스트엔 디렉토리 이름 추가
        Labels.append(label)

# 훈련할 데이터가 없다면 종료
if len(Labels) == 0:
    print("학습할 데이터가 없습니다.")
    exit()

# Labels를 32비트 정수로 변환
Labels = np.asarray(Labels, dtype=np.int32)

# 모델 생성
model = cv2.face.LBPHFaceRecognizer_create()
# 학습 시작
model.train(np.asarray(Training_Data), np.asarray(Labels))
print("학습 완료.")

# 얼굴 인식기 초기화
face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def face_detector(img, size=0.5):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_classifier.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return img, []
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 255), 2)
        roi = img[y:y+h, x:x+w]
        roi = cv2.resize(roi, (200, 200))
    return img, roi  # 검출된 좌표에 사각 박스를 그리고(img), 검출된 부위를 잘라(roi) 전달

def draw_text(img, text, position, font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size=20, font_color=(255, 255, 255)):
    # PIL을 사용하여 이미지를 그리고 텍스트를 추가합니다.
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(font_path, font_size)  # 영어 폰트 사용
    draw.text(position, text, font=font, fill=font_color)
    return np.array(img_pil)

def unlock_door():
    global door_locked
    print("문이 열립니다")
    # servo.value = 0.8  # 서보모터를 오른쪽으로 (130도)
    setServoPos(0)
    led1.on()

    sleep(10)

    print("문이 닫힙니다")
    # servo.value = -0.5  # 서보모터를 왼쪽으로 (0도)
    setServoPos(120)
    led1.off()
    sleep(1)

    door_locked = True  # 다시 문을 잠급니다

# 사용자 이름 리스트
user_names = user_dirs

# Tkinter 설정
window = tk.Tk()
window.title("Face Recognition")
window.geometry("800x600")

label = tk.Label(window)
label.pack()

cap1 = cv2.VideoCapture(2)

door_locked = True  # 초기 상태는 문이 잠긴 상태

# 얼굴 인식 함수
def update_frame():
    
    global door_locked
    ret, frame = cap1.read()
    if not ret:
        return
    image, face = face_detector(frame)
    try:
        if not door_locked:
            image = draw_text(image, "Unlocked", (250, 400), '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30, (0, 255, 0))
        else:
            face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
            result = model.predict(face)
            if result[1] < 500:
                confidence = int(100 * (1 - (result[1]) / 300))
                display_string = f"{confidence}% likely to be {user_names[result[0]]}"
                image = draw_text(image, display_string, (200, 50), '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20, (250, 120, 255))
            if confidence > 75:
                image = draw_text(image, "Unlocked", (250, 400), '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30, (0, 255, 0))
                door_locked = False  # 문이 열리면 잠금 해제
                threading.Thread(target=unlock_door).start()  # 비동기적으로 문을 여는 동작 수행
            else:
                image = draw_text(image, "Locked", (250, 400), '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30, (0, 0, 255))

    except:
        image = draw_text(image, "Face not found", (150, 400), '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30, (255, 0, 0))

    img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    imgtk = ImageTk.PhotoImage(image=img)
    label.imgtk = imgtk
    label.configure(image=imgtk)
    window.after(10, update_frame)



def monitor_distance():
    while True:
        distance = sensor.distance * 100
        print(f"Distance: {distance:.2f} cm")
        if distance <= 10:
            print("신발장 LED ON")
            led1.on()
            sleep(10)
            print("신발장 LED OFF")
            led1.off()
        sleep(1)

threading.Thread(target=setServoPos).start()
threading.Thread(target=monitor_distance).start()
threading.Thread(target=update_frame).start()

# client = connect_mqtt()
# client.loop_start()

#update_frame()
window.mainloop()

cap1.release()
cv2.destroyAllWindows()

# client.loop_stop()
# client.disconnect()


