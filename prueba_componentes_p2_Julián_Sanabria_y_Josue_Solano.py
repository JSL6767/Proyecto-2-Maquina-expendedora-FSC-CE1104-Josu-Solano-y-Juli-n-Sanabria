import machine
from machine import ADC, Pin, PWM
from time import sleep
import time

# Potenciómetro
pot = ADC(Pin(26))
productos = ["Doritos", "Coca-Cola", "Gomitas"]

# Display 7 segmentos (GP0 al GP6)
segmentos = [Pin(i, Pin.OUT) for i in range(7)]

# Servo
servo = PWM(Pin(16), freq=50)

digitos = [
    [1, 1, 1, 1, 1, 1, 0],  # 0
    [0, 1, 1, 0, 0, 0, 0],  # 1
    [1, 1, 0, 1, 1, 0, 1],  # 2
    [1, 1, 1, 1, 0, 0, 1],  # 3
    [0, 1, 1, 0, 0, 1, 1],  # 4
    [1, 0, 1, 1, 0, 1, 1],  # 5
    [1, 0, 1, 1, 1, 1, 1],  # 6
    [1, 1, 1, 0, 0, 0, 0],  # 7
    [1, 1, 1, 1, 1, 1, 1],  # 8
    [1, 1, 1, 1, 0, 1, 1],  # 9
]

def mostrar(numero):
    for i, seg in enumerate(segmentos):
        seg.value(digitos[numero][i])

def apagar_display():
    for seg in segmentos:
        seg.value(0)

while True:
    valor = pot.read_u16()

    if valor < 21845:
        producto = productos[0]
        apagar_display()
    elif valor < 43690:
        producto = productos[1]
        mostrar(2)
    else:
        producto = productos[2]
        apagar_display()
        servo.duty_u16(4915)   # se mueve a 90 grados
        sleep(1)
        servo.duty_u16(1640)   # vuelve a 0 grados
        sleep(1)

    print(f"Producto elegido: {producto}")
    time.sleep(0.2)