import time
import network
import socket
from machine import ADC, Pin, PWM
 #
SSID     = "aifondetupadre"
PASSWORD = "papoi6767"
PUERTO   = 1717
 

# CONEXIÓN WIFI

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando a WiFi...", end="")
    while not wlan.isconnected():
        print(".", end="")
        time.sleep(0.5)
    print("\nConectado:", wlan.ifconfig())
    return wlan.ifconfig()[0]
 

# PINES

pot       = ADC(Pin(26))
segmentos = [Pin(i, Pin.OUT) for i in range(8)]
led_verde = Pin(15, Pin.OUT)
led_rojo  = Pin(14, Pin.OUT)
boton     = Pin(13, Pin.IN, Pin.PULL_UP)
servo     = PWM(Pin(16), freq=50)
 

# TABLA 7 SEGMENTOS

digitos = [
    [1,1,1,0,1,1,1],
    [1,0,0,0,1,0,0],
    [0,1,1,1,1,1,0],
    [0,1,1,1,0,1,1],
    [1,1,0,1,0,0,1],
    [1,0,1,1,0,1,1],
    [1,0,1,1,1,1,1],
    [0,1,1,0,0,0,1],
    [1,1,1,1,1,1,1],
    [1,1,1,1,0,1,1],
]
 

# DATOS

productos = [
    {"nombre": "Doritos",   "stock": 3, "ventas": 0},
    {"nombre": "Coca-Cola", "stock": 5, "ventas": 0},
    {"nombre": "Gomitas",   "stock": 9, "ventas": 0},
]
eventos      = []
modo_mant    = False                                    # Estado del modo mantenimiento
ultimo_prod  = -1                                       # Para detectar cambio de producto
 

# FUNCIONES DE HARDWARE

def mostrar_numero(n):
    n = max(0, min(9, n))
    for i in range(7):
        segmentos[i].value(digitos[n][i])
 
def apagar_7segmentos():
    for i in range(7):
        segmentos[i].value(0)
 
def actualizar_leds(stock):
    if stock > 0:
        led_verde.value(1)
        led_rojo.value(0)
    else:
        led_verde.value(0)
        led_rojo.value(1)
 
def mover_servo():
    servo.duty_u16(4915)
    time.sleep(1)
    servo.duty_u16(1640)
    time.sleep(0.5)
 
def leer_producto():
    valor = pot.read_u16()
    if valor < 21845:
        return 0
    elif valor < 43690:
        return 1
    else:
        return 2
 
def boton_presionado():
    if boton.value() == 1:
        return False
    time.sleep(0.05)
    if boton.value() == 1:
        return False
    while boton.value() == 0:
        time.sleep(0.01)
    time.sleep(0.05)
    return True
 

# LÓGICA DE COMPRA

def hacer_compra(idx):
    global modo_mant
    nombre = productos[idx]["nombre"]
 
    if modo_mant:                                       # Bloquea compra en mantenimiento
        msg = f"MANT|{idx}"
        eventos.append(f"Compra bloqueada (mant): {nombre}")
        print("Máquina en mantenimiento")
        return msg
 
    if productos[idx]["stock"] <= 0:
        eventos.append(f"Sin existencias: {nombre}")
        print("Sin existencias")
        return "SIN_STOCK|" + str(idx)
 
    productos[idx]["stock"]  -= 1
    productos[idx]["ventas"] += 1
    eventos.append(f"Compra: {nombre}")
    print("Artículo comprado:", nombre)
 
    mover_servo()
    actualizar_leds(productos[idx]["stock"])
    mostrar_numero(productos[idx]["stock"])
 
    return "OK|" + str(idx) + "|" + str(productos[idx]["stock"])
 

# PROCESAR MENSAJES DEL CLIENTE

def procesar_mensaje(msg):
    global modo_mant, eventos
 
    producto_actual = leer_producto()
 
    if msg == "STOCK":                                  # Devuelve stock de los 3 productos
        texto = ""
        for p in productos:
            texto += p["nombre"] + ": " + str(p["stock"]) + "\n"
        return texto
 
    elif msg == "ESTADO":                               # Devuelve estado completo
        return "ESTADO|{}|{}|{}|{}|{}|{}".format(
            productos[0]["stock"],  productos[1]["stock"],  productos[2]["stock"],
            productos[0]["ventas"], productos[1]["ventas"], productos[2]["ventas"]
        )
 
    elif msg == "EVENTOS":                              # Devuelve eventos pendientes y los limpia
        if len(eventos) == 0:
            return "SIN_EVENTOS"
        texto  = "\n".join(eventos)
        eventos = []
        return texto
 
    elif msg == "MANT_ON":                              # Activa modo mantenimiento
        modo_mant = True
        eventos.append("Mantenimiento activado")
        return "MANT_ON"
 
    elif msg == "MANT_OFF":                             # Desactiva modo mantenimiento
        modo_mant = False
        eventos.append("Mantenimiento desactivado")
        return "MANT_OFF"
 
    elif msg.startswith("REPONER|"):                    # Repone stock de un producto
        partes = msg.split("|")
        idx    = int(partes[1])
        cant   = int(partes[2])
        productos[idx]["stock"] = min(9, productos[idx]["stock"] + cant)
        mostrar_numero(productos[idx]["stock"])         # Actualiza el 7 segmentos
        actualizar_leds(productos[idx]["stock"])
        eventos.append(f"Reposición: {productos[idx]['nombre']} +{cant}")
        return "REPUESTO|" + str(idx) + "|" + str(productos[idx]["stock"])
 
    elif msg == "PRODUCTO":
        return productos[producto_actual]["nombre"]
 
    else:
        return "Echo: " + msg
 

# INICIO

ip = connect_wifi()
 
s = socket.socket()
s.bind((ip, PUERTO))
s.listen(1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.settimeout(0.5)
print("Servidor listo en:", ip, "puerto", PUERTO)
 
apagar_7segmentos()
led_verde.value(0)
led_rojo.value(0)
 

# LOOP PRINCIPAL

while True:
    producto_actual = leer_producto()
    stock_actual    = productos[producto_actual]["stock"]
 
    if producto_actual != ultimo_prod:                  # Si cambió el producto seleccionado
        nombre = productos[producto_actual]["nombre"]
        print(f"Producto seleccionado: {nombre}")
        eventos.append(f"Seleccionado: {nombre}")       # Notifica al cliente
        ultimo_prod = producto_actual
 
    mostrar_numero(stock_actual)
    actualizar_leds(stock_actual)
 
    if boton_presionado():                              # Compra física con el botón
        hacer_compra(producto_actual)
 
    try:
        conn, addr = s.accept()
        data = conn.recv(1024)
        if data:
            msg      = data.decode().strip()
            respuesta = procesar_mensaje(msg)
            conn.send(respuesta.encode())
        conn.close()
    except:
        pass
 
    time.sleep(0.01)