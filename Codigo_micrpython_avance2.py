# main.py - CElect: Avance 2
# MicroPython - Raspberry Pi Pico W
# CE-1104 Fundamentos de Sistemas Computacionales

import time                                             # Delays y tiempos
from machine import ADC, Pin, PWM                       # Hardware de la raspberry

# Componentes
pot = ADC(Pin(26))                                      # Potenciómetro en GP26 (entrada analógica ADC0)



segmentos = [Pin(i, Pin.OUT) for i in range(8)]         # Pines GP0-GP7 como salida para cada segmento


led_verde = Pin(15, Pin.OUT)                            # LED verde en GP15
led_rojo  = Pin(14, Pin.OUT)                            # LED rojo en GP14


boton = Pin(13, Pin.IN, Pin.PULL_UP)                    # Botón en GP13, otro lado a GND
servo = PWM(Pin(16), freq=50)                           # Servo en GP16, frecuencia 50Hz (estándar)

# digitos para el 7 segmentos
digitos = [
    [1, 1, 0, 1, 1, 1, 1],                             # 0: A B C D E F
    [0, 0, 0, 1, 1, 0, 0],                             # 1: B C
    [1, 1, 1, 0, 1, 1, 0],                             # 2: A B D E G
    [1, 1, 1, 0, 0, 1, 1],                             # 3: A B C D G
    [0, 1, 1, 1, 0, 0, 1],                             # 4: B C F G
    [1, 0, 1, 1, 0, 1, 1],                             # 5: A C D F G
    [1, 0, 1, 1, 1, 1, 1],                             # 6: A C D E F G
    [1, 1, 0, 0, 0, 0, 1],                             # 7: A B C
    [1, 1, 1, 1, 1, 1, 1],                             # 8: todos
    [1, 1, 1, 1, 0, 1, 1],                             # 9: A B C D F G
]

# productos
productos = [
    {"nombre": "Doritos",   "stock": 3},                # Producto 1 - inicia con 3
    {"nombre": "Coca-Cola", "stock": 5},                # Producto 2 - inicia con 5
    {"nombre": "Gomitas",   "stock": 7},                # Producto 3 - inicia con 7
]

# Mostrar numero en 7 segmentos
def mostrar_numero(n):
    n = max(0, min(9, n))                               # Limita el número entre 0 y 9
    for i in range(7):                                  # Solo los 7 segmentos, ignora el dp (GP7)
        segmentos[i].value(digitos[n][i])               # Enciende o apaga según la tabla

# Apagar 7segmentos
def apagar_7segmentos():
    for i in range(7):                                  # Solo apaga los 7 segmentos, ignora el dp
        segmentos[i].value(0)                           # Apaga cada segmento

# Actualizacion de leds
def actualizar_leds(stock):
    if stock > 0:                                       # Si hay unidades disponibles
        led_verde.value(1)                              # Enciende LED verde
        led_rojo.value(0)                               # Apaga LED rojo
    else:                                               # Si no hay unidades
        led_verde.value(0)                              # Apaga LED verde
        led_rojo.value(1)                               # Enciende LED rojo

# Movimiento del servomotor
def mover_servo():
    servo.duty_u16(4915)                                # Mueve el servo a ~90 grados
    time.sleep(1)                                       # Espera 1 segundo
    servo.duty_u16(1640)                                # Regresa el servo a ~0 grados
    time.sleep(0.5)                                     # Espera a que el servo termine de regresar

# Identificacion del producto
def leer_producto():
    valor = pot.read_u16()                              # Lee el valor analógico (0-65535)
    if valor < 21845:                                   # Tercio inferior del rango
        return 0                                        # Producto 1
    elif valor < 43690:                                 # Tercio medio del rango
        return 1                                        # Producto 2
    else:                                               # Tercio superior del rango
        return 2                                        # Producto 3

# Detectar presion del boton
def boton_presionado():
    if boton.value() == 1:                              # Si el pin está en alto, no hay presión
        return False
    time.sleep(0.05)                                    # Espera 50ms para confirmar que no es ruido
    if boton.value() == 1:                              # Confirma que sigue sin presión (falsa alarma)
        return False
    while boton.value() == 0:                          # Espera a que se suelte el botón
        time.sleep(0.01)
    time.sleep(0.05)                                    # Pequeña pausa tras soltar para evitar rebotes
    return True                                         # Confirma que fue una presión real


producto_anterior = -1                                  # Guarda el producto anterior para detectar cambios

apagar_7segmentos()                                     # 7 segmentos apagado al arrancar
led_verde.value(0)                                      # LEDs apagados al inicio
led_rojo.value(0)


# LOOP PRINCIPAL

while True:                                             # Bucle infinito principal

    # Leer potenciómetro
    producto_actual = leer_producto()                   # Lee qué producto está seleccionado
    stock_actual = productos[producto_actual]["stock"]  # Obtiene el stock del producto actual

    # Si cambió el producto, imprimir en consola
    if producto_actual != producto_anterior:            # Solo imprime si el producto cambió
        nombre = productos[producto_actual]["nombre"]   # Obtiene el nombre del producto
        print(f"Producto seleccionado: {nombre}")       # Muestra en consola el producto seleccionado
        producto_anterior = producto_actual             # Actualiza el producto anterior

    # Actualizar 7 segmentos y LED según producto actual
    mostrar_numero(stock_actual)                        # Muestra el stock en el 7 segmentos
    actualizar_leds(stock_actual)                       # Actualiza el LED según el stock

    # Revisar botón de compra
    if boton_presionado():                              # Solo continúa si fue una presión real y completa
        if stock_actual <= 0:                           # Si no hay stock disponible
            print("Sin existencias")                    # Avisa en consola que no hay stock
        else:                                           # Si hay stock disponible
            productos[producto_actual]["stock"] -= 1    # Descuenta una unidad del inventario
            print("Artículo comprado")                  # Confirma la compra en consola
            mover_servo()                               # Mueve el servo para entregar el producto
            actualizar_leds(productos[producto_actual]["stock"])  # Actualiza LED con el nuevo stock
            mostrar_numero(productos[producto_actual]["stock"])   # Actualiza 7 segmentos con el nuevo stock

    time.sleep(0.05)                                    # Pequeña pausa para no saturar el CPU