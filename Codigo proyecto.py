# cliente_celect.py - CElect: Administrador de Máquina Dispensadora
# Python (PC) - Tkinter GUI con conexión WiFi
# CE-1104 Fundamentos de Sistemas Computacionales

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import socket
import time
from bs4 import BeautifulSoup

# ip y puerto del servidor en el pico w
SERVER_IP = "172.20.10.8"
PORT      = 1717

# lock para que dos hilos no envíen al pico al mismo tiempo
lock = threading.Lock()

def enviar_pico(mensaje):
    with lock:  # solo un hilo a la vez puede enviar
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)                             # espera máximo 3 segundos respuesta
            s.connect((SERVER_IP, PORT))                # conecta al servidor del pico
            s.send(mensaje.encode())                    # envía el mensaje como bytes
            respuesta = s.recv(1024).decode()           # recibe la respuesta
            s.close()
            return respuesta
        except:
            return None                                 # si falla retorna None

def conectar_al_inicio():
    time.sleep(1)                                       # espera que la ventana cargue antes de conectar
    respuesta = enviar_pico("ESTADO")                   # pide el estado completo al pico
    if respuesta and respuesta.startswith("ESTADO|"):
        partes = respuesta.split("|")
        for i in range(3):
            stocks[i] = int(partes[i + 1])              # actualiza stocks con los del pico
            ventas[i] = int(partes[i + 4])              # actualiza ventas con las del pico
        ventana.after(0, actualizar_ui)
        ventana.after(0, lambda: lbl_conexion.config(text="conectado al pico w", fg="green"))
        ventana.after(0, lambda: log("conectado. stocks sincronizados."))
    else:
        ventana.after(0, lambda: lbl_conexion.config(text="sin conexion con el pico w", fg="red"))
        ventana.after(0, lambda: log("no se pudo conectar al pico w."))

# guarda el estado anterior para detectar cambios sin depender de eventos del pico
estado_anterior = [0, 0, 0, 0, 0, 0]

def poll_eventos():
    def _poll():
        global estado_anterior
        r = enviar_pico("ESTADO")                       # pide el estado actual al pico
        if r and r.startswith("ESTADO|"):
            partes = r.split("|")
            nuevo = [int(partes[i+1]) for i in range(6)]   # extrae los 6 valores (3 stocks + 3 ventas)
            for i in range(3):
                if nuevo[i] < estado_anterior[i]:       # si bajó el stock, hubo una compra
                    ventana.after(0, lambda n=nombres[i]: log(f"compra: {n}"))
            for i in range(3):
                stocks[i] = nuevo[i]                    # actualiza stocks locales
                ventas[i] = nuevo[i+3]                  # actualiza ventas locales
            if nuevo != estado_anterior:                # si cambió algo, actualiza la interfaz
                estado_anterior = nuevo
                ventana.after(0, actualizar_ui)
    threading.Thread(target=_poll, daemon=True).start() # corre en hilo separado para no bloquear la ui
    ventana.after(500, poll_eventos)                    # se repite cada 500ms

def obtener_tipo_cambio():
    global TIPO_CAMBIO
    try:
        response = requests.get(
            "https://api.exchangerate.host/latest?base=USD&symbols=CRC", timeout=5)
        data = response.json()
        TIPO_CAMBIO = data["rates"]["CRC"]
        ventana.after(0, lambda: lbl_tipo_cambio.config(
            text=f"tipo de cambio: c/{TIPO_CAMBIO:,.2f} por $1"))
    except:
        ventana.after(0, lambda: lbl_tipo_cambio.config(
            text="tipo de cambio: c/520.00 (sin conexion)"))

# datos de los productos: nombres, precios en dolares, stocks y ventas iniciales
nombres   = ["Doritos", "Coca-Cola", "Gomitas"]
precios   = [1.50, 2.00, 1.25]
stocks    = [3, 5, 9]
ventas    = [0, 0, 0]
modo_mant = False
TIPO_CAMBIO = 520.0

def actualizar_ui():
    for i in range(3):
        color = "#2ecc71" if stocks[i] > 0 else "#e74c3c"  # verde si hay stock, rojo si no
        lbl_stock[i].config(text=f"{stocks[i]}/9", fg=color)
        gan_col = ventas[i] * precios[i] * TIPO_CAMBIO     # ganancias en colones
        gan_usd = ventas[i] * precios[i]                   # ganancias en dolares
        tabla.item(f"prod{i}", values=(
            nombres[i], stocks[i], ventas[i],
            f"c/{gan_col:,.0f}", f"${gan_usd:.2f}"
        ))
    total_col = sum(ventas[i] * precios[i] * TIPO_CAMBIO for i in range(3))
    total_usd = sum(ventas[i] * precios[i] for i in range(3))
    lbl_total_ventas.config(text=f"ventas totales: {sum(ventas)}")
    lbl_total_col.config(text=f"ganancias: c/{total_col:,.0f}  /  ${total_usd:.2f}")
    if modo_mant:
        lbl_mant.config(text="modo mantenimiento activo", fg="orange", font=("Arial", 11, "bold"))
        btn_mant.config(text="desactivar mantenimiento")
        frame_reponer.pack(pady=6, before=frame_tabla_label)  # muestra el panel de reposicion
    else:
        lbl_mant.config(text="maquina operativa", fg="green", font=("Arial", 11))
        btn_mant.config(text="activar mantenimiento")
        frame_reponer.pack_forget()                         # oculta el panel de reposicion

def toggle_mantenimiento():
    global modo_mant
    modo_mant = not modo_mant                              # alterna entre activado y desactivado
    cmd = "MANT_ON" if modo_mant else "MANT_OFF"
    threading.Thread(target=lambda: enviar_pico(cmd), daemon=True).start()  # avisa al pico
    actualizar_ui()
    log("mantenimiento activado" if modo_mant else "mantenimiento desactivado")

def reponer(idx):
    if not modo_mant:                                      # solo permite reponer en mantenimiento
        messagebox.showwarning("Error", "solo se puede reponer en modo mantenimiento")
        return
    cant = entry_reponer[idx].get()
    if not cant.isdigit() or int(cant) <= 0:
        messagebox.showwarning("Error", "ingresa una cantidad valida")
        return
    def _rep():
        respuesta = enviar_pico(f"REPONER|{idx}|{cant}")   # envía el comando de reposicion al pico
        if respuesta and respuesta.startswith("REPUESTO|"):
            partes = respuesta.split("|")
            stocks[int(partes[1])] = int(partes[2])        # actualiza el stock con el valor real del pico
        else:
            stocks[idx] = min(9, stocks[idx] + int(cant))  # si no hay conexion, actualiza localmente
        ventana.after(0, actualizar_ui)
        ventana.after(0, lambda: log(f"reposicion: {nombres[idx]} +{cant}, stock: {stocks[idx]}/9"))
    threading.Thread(target=_rep, daemon=True).start()

def log(texto):
    txt_log.insert(tk.END, texto + "\n")                   # agrega una línea al log
    txt_log.see(tk.END)                                    # hace scroll al final

def salir():
    ventana.destroy()

# construccion de la interfaz
ventana = tk.Tk()
ventana.title("CElect - Administrador")
ventana.geometry("720x820")
ventana.resizable(False, False)

frame_top = tk.Frame(ventana, bg="#2c3e50", pady=6)
frame_top.pack(fill="x")
tk.Label(frame_top, text="CElect", bg="#2c3e50", fg="white",
         font=("Arial", 14, "bold")).pack(side="left", padx=12)
tk.Button(frame_top, text="Salir", command=salir,
          bg="#e74c3c", fg="white").pack(side="right", padx=8)

lbl_conexion = tk.Label(ventana, text="conectando...", fg="orange", font=("Arial", 10, "bold"))
lbl_conexion.pack(pady=(4, 0))

lbl_tipo_cambio = tk.Label(ventana, text="tipo de cambio: cargando...", font=("Arial", 9), fg="gray")
lbl_tipo_cambio.pack(pady=(4, 0))

lbl_mant = tk.Label(ventana, text="maquina operativa", fg="green", font=("Arial", 11))
lbl_mant.pack(pady=(4, 0))

btn_mant = tk.Button(ventana, text="activar mantenimiento",
                     command=toggle_mantenimiento, bg="#e67e22",
                     fg="white", font=("Arial", 10, "bold"))
btn_mant.pack(pady=4)

# tarjetas de stock, una por producto
frame_stocks = tk.Frame(ventana)
frame_stocks.pack(pady=6)
lbl_stock = []
for i, nombre in enumerate(nombres):
    frame_card = tk.LabelFrame(frame_stocks, text=nombre,
                               font=("Arial", 10, "bold"), padx=10, pady=6)
    frame_card.grid(row=0, column=i, padx=10)
    lbl = tk.Label(frame_card, text="-/9", font=("Arial", 22, "bold"), fg="#2ecc71")
    lbl.pack()
    lbl_stock.append(lbl)

# panel de reposicion, oculto hasta que se active el mantenimiento
frame_reponer = tk.LabelFrame(ventana, text="reponer stock",
                              font=("Arial", 10, "bold"), padx=10, pady=6)
entry_reponer = []
for i, nombre in enumerate(nombres):
    frame_fila = tk.Frame(frame_reponer)
    frame_fila.pack(pady=2)
    tk.Label(frame_fila, text=f"{nombre}:", width=10, anchor="w").pack(side="left")
    ent = tk.Entry(frame_fila, width=5, justify="center")
    ent.insert(0, "1")
    ent.pack(side="left", padx=4)
    entry_reponer.append(ent)
    tk.Button(frame_fila, text="reponer", bg="#8e44ad", fg="white",
              command=lambda idx=i: reponer(idx)).pack(side="left")

frame_tabla_label = tk.Label(ventana, text="estadisticas", font=("Arial", 11, "bold"))
frame_tabla_label.pack(pady=(10, 2))

frame_tabla = tk.Frame(ventana)
frame_tabla.pack()
cols = ("producto", "stock", "ventas", "colones", "dolares")
tabla = ttk.Treeview(frame_tabla, columns=cols, show="headings", height=4)
tabla.heading("producto", text="producto")
tabla.heading("stock",    text="stock")
tabla.heading("ventas",   text="ventas")
tabla.heading("colones",  text="ganancias (c/)")
tabla.heading("dolares",  text="ganancias ($)")
for col in cols:
    tabla.column(col, width=130, anchor="center")
for i, nombre in enumerate(nombres):
    tabla.insert("", "end", iid=f"prod{i}", values=(nombre, "-", "-", "-", "-"))
tabla.pack()

lbl_total_ventas = tk.Label(ventana, text="ventas totales: 0", font=("Arial", 10))
lbl_total_ventas.pack()
lbl_total_col = tk.Label(ventana, text="ganancias: c/0  /  $0.00", font=("Arial", 10))
lbl_total_col.pack()

tk.Label(ventana, text="log de eventos", font=("Arial", 10, "bold")).pack(pady=(10, 0))
txt_log = tk.Text(ventana, height=7, width=85, bg="#1e1e1e", fg="#dcdcdc", font=("Courier", 9))
txt_log.pack(padx=10)
tk.Button(ventana, text="salir", command=salir,
          bg="#e74c3c", fg="white", width=12).pack(pady=8)

# inicio de la aplicacion
actualizar_ui()
log("aplicacion iniciada. conectando al pico w...")
log(f"ip: {SERVER_IP}:{PORT}")

threading.Thread(target=obtener_tipo_cambio, daemon=True).start()   # obtiene tipo de cambio en segundo plano
threading.Thread(target=conectar_al_inicio, daemon=True).start()    # conecta al pico al arrancar
ventana.after(2000, poll_eventos)                                    # el polling arranca 2s despues

ventana.mainloop()