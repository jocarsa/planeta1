import sqlite3  # Importamos la librería sqlite3 para gestionar bases de datos
import numpy as np  # Importamos numpy para operaciones numéricas avanzadas
import ttkbootstrap as ttk  # Importamos ttkbootstrap para la interfaz gráfica
from ttkbootstrap.constants import *  # Importamos constantes de ttkbootstrap
from PIL import Image, ImageTk, ImageDraw  # Importamos PIL para manipulación de imágenes
import random  # Importamos random para generación de números aleatorios
import os  # Importamos os para operaciones del sistema operativo
import noise  # Importamos noise para generar ruido Perlin
import math  # Importamos math para operaciones matemáticas
import time  # Importamos time para manipular el tiempo

# Crear el directorio de render si no existe
directorio_salida = "render"  # Definimos el nombre del directorio de salida
os.makedirs(directorio_salida, exist_ok=True)  # Creamos el directorio si no existe

# Función para interpolar entre dos colores
def interpolar_color(color1, color2, factor):
    return tuple(int(a + (b - a) * factor) for a, b in zip(color1, color2))

# Función para interpolar entre dos valores
def interpolar_valor(val1, val2, factor):
    return val1 + (val2 - val1) * factor

# Función para oscurecer un color
def oscurecer_color(color, factor):
    return tuple(int(c * (1 - factor)) for c in color)

# Variables globales para la hora del día y la luz ambiental
hora_del_dia = 12.0  # Comenzamos al mediodía
velocidad_tiempo = 1.0  # Velocidad de progresión del tiempo
luz_ambiental = 1.0  # Máximo brillo al mediodía

# Función para actualizar la luz ambiental
def actualizar_luz_ambiental():
    global luz_ambiental, hora_del_dia
    # Calcular la luz ambiental basada en la hora del día
    if 6 <= hora_del_dia <= 18:  # Si es de día
        luz_ambiental = interpolar_valor(0.5, 1.0, (hora_del_dia - 6) / 12)
    else:  # Si es de noche
        if hora_del_dia < 6:  # Temprano en la mañana
            luz_ambiental = interpolar_valor(0.0, 0.5, hora_del_dia / 6)
        else:  # Tarde en la noche
            luz_ambiental = interpolar_valor(1.0, 0.5, (hora_del_dia - 18) / 6)
    
    actualizar_lienzo()  # Actualizamos el lienzo
    raiz.after(int(1000 / velocidad_tiempo), actualizar_hora)  # Programamos la próxima actualización

# Función para actualizar la hora
def actualizar_hora():
    global hora_del_dia, velocidad_tiempo
    hora_del_dia += velocidad_tiempo * 0.1  # Incrementamos la hora del día
    if hora_del_dia >= 24:  # Si pasa las 24 horas, reiniciamos
        hora_del_dia -= 24
    actualizar_luz_ambiental()  # Actualizamos la luz ambiental

# Función para generar una sección en perspectiva isométrica
def generar_seccion_isometrica(x_inicio, x_fin, y_inicio, y_fin, ancho, alto, escala, semilla, nivel_agua, multiplicador_altura, cursor, desfase_y_pixel, separacion_pixeles, desfase_nube, factor_sombra, transparencia_nube, brillo_nube):
    random.seed(semilla)  # Fijamos la semilla aleatoria
    
    ancho_iso, alto_iso = (x_fin - x_inicio) * separacion_pixeles, (y_fin - y_inicio) * separacion_pixeles
    seccion = Image.new("RGBA", (ancho_iso, alto_iso), (255, 255, 255, 255))  # Comenzamos con un fondo blanco

    dibujar = ImageDraw.Draw(seccion)
    
    centro_x, centro_y = ancho_iso // 2, alto_iso // 2
    
    # Consulta en la base de datos para obtener los datos del terreno
    cursor.execute("SELECT x, y, color, altura FROM terreno WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?",
                   (x_inicio, x_fin - 1, y_inicio, y_fin - 1))
    datos_terreno = cursor.fetchall()
    
    cursor.execute("SELECT x, y, color, altura FROM nubes WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?",
                   (x_inicio, x_fin - 1, y_inicio, y_fin - 1))
    datos_nube = cursor.fetchall()
    
    # Convertir los datos a un diccionario para acceso rápido
    dict_terreno = {(x, y): (color_str, altura) for x, y, color_str, altura in datos_terreno}
    dict_nube = {(x, y): (color_str, altura) for x, y, color_str, altura in datos_nube}
    
    # Primer pase: dibujar el terreno
    for x in range(x_inicio, x_fin):
        for y in range(y_inicio, y_fin):
            if (x, y) not in dict_terreno:
                continue
            
            color_str, altura = dict_terreno[(x, y)]
            color = tuple(map(int, color_str.split(',')))
            
            # Aplicar luz ambiental
            color = oscurecer_color(color, 1 - luz_ambiental)
            
            valor_normalizado = altura / 65535.0
            
            # Calcular coordenadas isométricas para el punto actual y sus vecinos
            iso_x = int(((x - x_inicio - (y - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + centro_x
            iso_y = int(((x - x_inicio + (y - y_inicio)) / 2 - valor_normalizado * multiplicador_altura) * separacion_pixeles) + centro_y - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel
            
            vecinos = [
                (x + 1, y), (x, y + 1), (x + 1, y + 1)
            ]
            
            iso_vecinos = []
            for nx, ny in vecinos:
                if (nx, ny) in dict_terreno:
                    n_color_str, n_altura = dict_terreno[(nx, ny)]
                    n_valor_normalizado = n_altura / 65535.0
                    n_iso_x = int(((nx - x_inicio - (ny - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + centro_x
                    n_iso_y = int(((nx - x_inicio + (ny - y_inicio)) / 2 - n_valor_normalizado * multiplicador_altura) * separacion_pixeles) + centro_y - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel
                    iso_vecinos.append((n_iso_x, n_iso_y, n_valor_normalizado))
                else:
                    iso_vecinos = []
                    break
            
            if len(iso_vecinos) == 3:
                # Verificar la opacidad del punto de nube encima
                opacidad_nube = 0
                if (x, y) in dict_nube and dict_nube[(x, y)][1] / 65535.0 > 0.5:  # Usando 0.5 como umbral para visibilidad de la nube
                    opacidad_nube = dict_nube[(x, y)][1] / 65535.0
                
                # Oscurecer color basado en la opacidad de la nube
                color_oscurecido = interpolar_color(color, (0, 0, 0), factor_sombra * opacidad_nube)
                
                # Dibujar la baldosa isométrica como un polígono lleno con vértices ajustados por la altura
                puntos = [
                    (iso_x, iso_y),  # Punto actual
                    (iso_vecinos[0][0], iso_vecinos[0][1]),  # Vecino derecho
                    (iso_vecinos[2][0], iso_vecinos[2][1]),  # Vecino inferior derecho
                    (iso_vecinos[1][0], iso_vecinos[1][1])   # Vecino inferior
                ]
                
                dibujar.polygon(puntos, fill=color_oscurecido)
                
                dibujar.line([puntos[0], puntos[1]], fill="black")
                dibujar.line([puntos[1], puntos[2]], fill="black")
                dibujar.line([puntos[2], puntos[3]], fill="black")
                dibujar.line([puntos[3], puntos[0]], fill="black")
            else:
                # Dibujar la baldosa isométrica alineada con el plano xy
                puntos = [
                    (iso_x, iso_y),  # Superior
                    (iso_x + separacion_pixeles * math.sqrt(3) / 2, iso_y + separacion_pixeles / 2),  # Derecha
                    (iso_x, iso_y + separacion_pixeles),  # Inferior
                    (iso_x - separacion_pixeles * math.sqrt(3) / 2, iso_y + separacion_pixeles / 2)  # Izquierda
                ]
                dibujar.polygon(puntos, fill=color)
                dibujar.line([puntos[0], puntos[1]], fill="black")
                dibujar.line([puntos[1], puntos[2]], fill="black")
                dibujar.line([puntos[2], puntos[3]], fill="black")
                dibujar.line([puntos[3], puntos[0]], fill="black")
    
    # Segundo pase: dibujar la superficie del agua
    superficie_agua = Image.new("RGBA", (ancho_iso, alto_iso), (0, 0, 0, 0))
    dibujar_agua = ImageDraw.Draw(superficie_agua)

    for x in range(x_inicio, x_fin):
        for y in range(y_inicio, y_fin):
            if (x, y) not in dict_terreno:
                continue

            color_str, altura = dict_terreno[(x, y)]
            color = tuple(map(int, color_str.split(',')))
            valor_normalizado = altura / 65535.0

            if valor_normalizado < nivel_agua:
                iso_x = int(((x - x_inicio - (y - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + centro_x
                iso_y = int(((x - x_inicio + (y - y_inicio)) / 2 - nivel_agua * multiplicador_altura) * separacion_pixeles) + centro_y - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel
                
                vecinos = [
                    (x + 1, y), (x, y + 1), (x + 1, y + 1)
                ]
                
                iso_vecinos = []
                for nx, ny in vecinos:
                    if (nx, ny) in dict_terreno:
                        n_color_str, n_altura = dict_terreno[(nx, ny)]
                        n_valor_normalizado = n_altura / 65535.0
                        n_iso_x = int(((nx - x_inicio - (ny - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + centro_x
                        n_iso_y = int(((nx - x_inicio + (ny - y_inicio)) / 2 - nivel_agua * multiplicador_altura) * separacion_pixeles) + centro_y - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel
                        iso_vecinos.append((n_iso_x, n_iso_y, n_valor_normalizado))
                    else:
                        iso_vecinos = []
                        break
                
                if len(iso_vecinos) == 3:
                    puntos_agua = [
                        (iso_x, iso_y),  # Punto actual
                        (iso_vecinos[0][0], iso_vecinos[0][1]),  # Vecino derecho
                        (iso_vecinos[2][0], iso_vecinos[2][1]),  # Vecino inferior derecho
                        (iso_vecinos[1][0], iso_vecinos[1][1])   # Vecino inferior
                    ]
                    
                    # Dibujar la superficie del agua con el color del terreno, pero añadiendo transparencia para indicar agua
                    dibujar_agua.polygon(puntos_agua, fill=(color[0], color[1], color[2], 128))  # Color original del terreno con transparencia


    
    # Combinar el terreno y la superficie del agua
    seccion = Image.alpha_composite(seccion, superficie_agua)
    
    # Tercer pase: dibujar las nubes
    capa_nube = Image.new("RGBA", (ancho_iso, alto_iso), (0, 0, 0, 0))
    dibujar_nubes = ImageDraw.Draw(capa_nube)
    
    for x in range(x_inicio, x_fin):
        for y in range(y_inicio, y_fin):
            if (x, y) not in dict_nube:
                continue

            color_str, altura = dict_nube[(x, y)]
            color = tuple(map(int, color_str.split(',')))
            valor_normalizado = altura / 65535.0

            if valor_normalizado > 0.5:  # Ajustar umbral para visibilidad de las nubes
                iso_x = int(((x - x_inicio - (y - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + centro_x
                iso_y = int(((x - x_inicio + (y - y_inicio)) / 2 - valor_normalizado * multiplicador_altura - desfase_nube) * separacion_pixeles) + centro_y - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel
                
                vecinos = [
                    (x + 1, y), (x, y + 1), (x + 1, y + 1)
                ]
                
                iso_vecinos = []
                for nx, ny in vecinos:
                    if (nx, ny) in dict_nube:
                        n_color_str, n_altura = dict_nube[(nx, ny)]
                        n_valor_normalizado = n_altura / 65535.0
                        n_iso_x = int(((nx - x_inicio - (ny - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + centro_x
                        n_iso_y = int(((nx - x_inicio + (ny - y_inicio)) / 2 - n_valor_normalizado * multiplicador_altura - desfase_nube) * separacion_pixeles) + centro_y - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel
                        iso_vecinos.append((n_iso_x, n_iso_y, n_valor_normalizado))
                    else:
                        iso_vecinos = []
                        break
                
                if len(iso_vecinos) == 3:
                    puntos_nube = [
                        (iso_x, iso_y),  # Punto actual
                        (iso_vecinos[0][0], iso_vecinos[0][1]),  # Vecino derecho
                        (iso_vecinos[2][0], iso_vecinos[2][1]),  # Vecino inferior derecho
                        (iso_vecinos[1][0], iso_vecinos[1][1])   # Vecino inferior
                    ]
                    # Calcular la opacidad basada en la altura, la transparencia de la nube y el brillo de la nube
                    if valor_normalizado > 0.5:  # Asegurando que solo las nubes visibles sean ajustadas
                        opacidad = int(255 * (valor_normalizado - 0.5) * 2 * transparencia_nube + brillo_nube)  # Escalar entre 0 y 255
                        opacidad = min(max(opacidad, 0), 255)  # Limitar a [0, 255]
                    else:
                        opacidad = 0
                    dibujar_nubes.polygon(puntos_nube, fill=(255, 255, 255, opacidad))  # Color blanco transparente
    

    # Calcular el centro de la sección
    centro_x_iso = ancho_iso // 2
    centro_y_iso = alto_iso // 2

    # Obtener el sprite actual del personaje según la dirección
    sprite_personaje = sprites[direccion_personaje]

    # Calcular la posición del personaje en coordenadas isométricas
    personaje_x = x_inicio + (x_fin - x_inicio) // 2
    personaje_y = y_inicio + (y_fin - y_inicio) // 2

    iso_personaje_x = int(((personaje_x - x_inicio - (personaje_y - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + centro_x
    iso_personaje_y = int(((personaje_x - x_inicio + (personaje_y - y_inicio)) / 2 - (altura / 65535.0) * multiplicador_altura) * separacion_pixeles) + centro_y - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel

    # Escalar el sprite del personaje
    ancho_escalado = int(ancho_sprite * escala_personaje)
    alto_escalado = int(alto_sprite * escala_personaje)
    sprite_escalado = sprite_personaje.resize((ancho_escalado, alto_escalado), Image.Resampling.LANCZOS)


    # Calcular la posición para colocar el sprite escalado del personaje (centrado)
    personaje_x = iso_personaje_x - ancho_escalado // 2
    personaje_y = iso_personaje_y - alto_escalado // 2

    # Dibujar el personaje en la sección
    seccion.paste(sprite_escalado, (personaje_x, personaje_y), sprite_escalado)

    # Combinar el terreno, la superficie del agua y la capa de nubes
    seccion = Image.alpha_composite(seccion, capa_nube)
    
    return seccion.convert("RGB")

# Establecer las dimensiones para la proyección equirectangular
multiplicador = 1024  # Definir multiplicador base
multiplica = 8  # Multiplicador adicional
ancho, alto = multiplicador * multiplica * 2, multiplicador * multiplica
escala = 5  # Definir la escala
escala_nube = 7  # Diferente escala para las nubes
nivel_agua = 0.5  # Nivel de agua por defecto, ajustable

# Inicializar semilla aleatoria
semilla = random.randint(0, 1000000)

# Definir el tamaño de la sección para el lienzo más grande
tamano_seccion = int(math.sqrt(0.00002 * ancho * alto)) * 2  # Aumentar el tamaño de la sección por un factor de 2

# Definir los puntos de inicio para la sección en el centro del terreno
x_inicio = (ancho - tamano_seccion) // 2
y_inicio = (alto - tamano_seccion) // 2

# Función para convertir coordenadas de terreno a coordenadas esféricas
def terreno_a_esferico(x, y, ancho, alto):
    lon = (x / ancho) * 2 * math.pi  # Longitud en [0, 2pi]
    lat = (y / alto) * math.pi  # Latitud en [0, pi]
    lat = lat - math.pi / 2  # Ajustar a rango [-pi/2, pi/2]
    return lat, lon

# Declarar la variable global `lienzo`
global lienzo, tk_img

# Cargar la hoja de sprites
hoja_sprites = Image.open("spritesheet.png")  # Cargar imagen de sprites

# Extraer los sprites individuales
ancho_sprite = hoja_sprites.width // 2
alto_sprite = hoja_sprites.height // 2

# Diccionario para almacenar los sprites recortados
sprites = {
    "este": hoja_sprites.crop((0, 0, ancho_sprite, alto_sprite)),
    "norte": hoja_sprites.crop((ancho_sprite, 0, ancho_sprite * 2, alto_sprite)),
    "sur": hoja_sprites.crop((0, alto_sprite, ancho_sprite, alto_sprite * 2)),
    "oeste": hoja_sprites.crop((ancho_sprite, alto_sprite, ancho_sprite * 2, alto_sprite * 2)),
}

# Variable global para la dirección del personaje
direccion_personaje = "sur"  # Dirección por defecto

# Variable global para la escala del personaje
escala_personaje = 0.25  # Escala por defecto

# Función para actualizar el lienzo con la nueva sección
def actualizar_lienzo():
    global lienzo, tk_img
    global x_inicio, y_inicio, tamano_seccion, cursor, multiplicador_altura, desfase_y_pixel, separacion_pixeles, desfase_nube, factor_sombra, transparencia_nube, brillo_nube
    x_fin = x_inicio + tamano_seccion
    y_fin = y_inicio + tamano_seccion
    
    # Generar la sección en perspectiva isométrica
    seccion = generar_seccion_isometrica(x_inicio, x_fin, y_inicio, y_fin, ancho, alto, escala, semilla, nivel_agua, multiplicador_altura, cursor, desfase_y_pixel, separacion_pixeles, desfase_nube, factor_sombra, transparencia_nube, brillo_nube)
    
    # Dibujar NPCs visibles en la sección actual
    for npc in npcs:
        if x_inicio <= npc.x < x_fin and y_inicio <= npc.y < y_fin:
            # Calcular la posición isométrica
            iso_x = int(((npc.x - x_inicio - (npc.y - y_inicio)) * math.sqrt(3) / 2) * separacion_pixeles) + seccion.width // 2

            # Consultar la altura para la posición actual del NPC en el terreno
            cursor.execute("SELECT altura FROM terreno WHERE x = ? AND y = ?", (npc.x, npc.y))
            resultado_altura = cursor.fetchone()
            altura_terreno = resultado_altura[0] if resultado_altura else 0
            valor_normalizado = altura_terreno / 65535.0

            # Ajustar iso_y basado en la altura del terreno
            iso_y = int(((npc.x - x_inicio + (npc.y - y_inicio)) / 2 - valor_normalizado * multiplicador_altura) * separacion_pixeles) + seccion.height // 2 - int(multiplicador_altura * separacion_pixeles * 0.65) + desfase_y_pixel

            npc.dibujar(seccion, iso_x, iso_y)
    
    # Convertir la sección a formato ImageTk
    tk_img = ImageTk.PhotoImage(seccion)
    
    # Calcular desplazamientos para centrar la imagen en el lienzo
    ancho_lienzo = lienzo.winfo_width()
    alto_lienzo = lienzo.winfo_height()
    desfase_x = (ancho_lienzo - seccion.width) // 2
    desfase_y = (alto_lienzo - seccion.height) // 2
    
    # Limpiar el lienzo y actualizarlo con la nueva sección
    lienzo.delete("all")
    lienzo.create_image(desfase_x, desfase_y, anchor=NW, image=tk_img)

# Función para dibujar la esfera
def dibujar_esfera():
    global cursor, lienzo_esfera, x_inicio, y_inicio, tamano_seccion, ancho, alto
    
    # Definir parámetros de la esfera
    radio = 200
    centro_x = radio + 50  # Ajustado para asegurar que la esfera esté centrada
    centro_y = radio + 50  # Ajustado para asegurar que la esfera esté centrada
    num_meridianos = 16
    num_paralelos = 8
    
    lienzo_esfera.delete("all")
    
    # Calcular el centro de la sección actual en coordenadas esféricas
    centro_x_terreno = x_inicio + tamano_seccion // 2
    centro_y_terreno = y_inicio + tamano_seccion // 2
    centro_lat, centro_lon = terreno_a_esferico(centro_x_terreno, centro_y_terreno, ancho, alto)
    
    def rotar(lat, lon, centro_lat, centro_lon):
        # Rotar la esfera para que centro_lat, centro_lon esté en el centro de la vista
        x = math.cos(lat) * math.cos(lon)
        y = math.cos(lat) * math.sin(lon)
        z = math.sin(lat)
        
        # Rotación alrededor del eje y (longitud)
        xz = math.sqrt(x*x + z*z)
        theta = math.atan2(z, x)
        theta -= centro_lon
        x = xz * math.cos(theta)
        z = xz * math.sin(theta)
        
        # Rotación alrededor del eje x (latitud)
        yz = math.sqrt(y*y + z*z)
        phi = math.atan2(y, z)
        phi -= centro_lat
        y = yz * math.sin(phi)
        z = yz * math.cos(phi)
        
        nueva_lat = math.asin(y)
        nueva_lon = math.atan2(z, x)
        
        return nueva_lat, nueva_lon
    
    def rotacion_inicial(lat, lon):
        # Rotar la esfera 90 grados alrededor del eje x para llevar el ecuador al centro
        x = math.cos(lat) * math.cos(lon)
        y = math.cos(lat) * math.sin(lon)
        z = math.sin(lat)
        
        # Realizar la rotación
        phi = math.pi / 2  # 90 grados
        phi = 0
        cos_phi = math.cos(phi)
        sin_phi = math.sin(phi)
        
        y_nueva = y * cos_phi - z * sin_phi
        z_nueva = y * sin_phi + z * cos_phi
        
        nueva_lat = math.asin(z_nueva)
        nueva_lon = math.atan2(y_nueva, x)
        
        return nueva_lat, nueva_lon

    def rotar_local(lat, lon, dlat, dlon):
        # Aplicar la rotación inicial
        lat, lon = rotacion_inicial(lat, lon)
        
        # Convertir lat/lon a coordenadas cartesianas
        x = math.cos(lat) * math.cos(lon)
        y = math.cos(lat) * math.sin(lon)
        z = math.sin(lat)

        # Rotar alrededor del eje x local (rotación de latitud)
        phi = dlat
        cos_phi = math.cos(phi)
        sin_phi = math.sin(phi)
        y_nueva = y * cos_phi - z * sin_phi
        z_nueva = y * sin_phi + z * cos_phi
        y = y_nueva
        z = z_nueva

        # Rotar alrededor del eje y local (rotación de longitud)
        theta = dlon
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        x_nueva = x * cos_theta - z * sin_theta
        z_nueva = x * sin_theta + z * cos_theta
        x = x_nueva
        z = z_nueva

        # Convertir de vuelta a coordenadas esféricas
        nueva_lat = math.asin(z)
        nueva_lon = math.atan2(y, x)

        return nueva_lat, nueva_lon

    def obtener_coordenadas_pantalla(lat, lon):
        x = radio * math.cos(lat) * math.cos(lon)
        y = radio * math.cos(lat) * math.sin(lon)
        z = radio * math.sin(lat)
        pantalla_x = centro_x + x / (1 + z / (2 * radio))
        pantalla_y = centro_y - y / (1 + z / (2 * radio))
        return pantalla_x, pantalla_y, z

    def obtener_color(lat, lon):
        terreno_x = int((lon / (2 * math.pi)) * ancho)
        terreno_y = int((lat + math.pi / 2) / math.pi * alto)
        cursor.execute("SELECT color FROM terreno WHERE x = ? AND y = ?", (terreno_x, terreno_y))
        resultado = cursor.fetchone()
        if resultado:
            color_str = resultado[0]
            color = "#" + "".join(f"{int(c):02x}" for c in map(int, color_str.split(',')))
            return color
        return "#000000"  # Por defecto negro si no se encuentra color
    
    poligonos = []
    for i in range(num_paralelos):
        lat1 = (i / num_paralelos) * math.pi - math.pi / 2
        lat2 = ((i + 1) / num_paralelos) * math.pi - math.pi / 2
        for j in range(num_meridianos):
            lon1 = (j / num_meridianos) * 2 * math.pi
            lon2 = ((j + 1) / num_meridianos) * 2 * math.pi
            
            # Rotar las coordenadas
            lat1_rot, lon1_rot = rotar_local(lat1, lon1, -y_inicio * math.pi / alto, -x_inicio * 2 * math.pi / ancho)
            lat2_rot, lon2_rot = rotar_local(lat2, lon2, -y_inicio * math.pi / alto, -x_inicio * 2 * math.pi / ancho)
            lat3_rot, lon3_rot = rotar_local(lat2, lon1, -y_inicio * math.pi / alto, -x_inicio * 2 * math.pi / ancho)
            lat4_rot, lon4_rot = rotar_local(lat1, lon2, -y_inicio * math.pi / alto, -x_inicio * 2 * math.pi / ancho)
            
            x1, y1, z1 = obtener_coordenadas_pantalla(lat1_rot, lon1_rot)
            x2, y2, z2 = obtener_coordenadas_pantalla(lat2_rot, lon2_rot)
            x3, y3, z3 = obtener_coordenadas_pantalla(lat3_rot, lon3_rot)
            x4, y4, z4 = obtener_coordenadas_pantalla(lat4_rot, lon4_rot)
            
            color1 = obtener_color(lat1, lon1)
            color2 = obtener_color(lat2, lon2)
            color3 = obtener_color(lat2, lon1)
            color4 = obtener_color(lat1, lon2)
            
            # Color promedio para la cara (enfoque simple)
            color_promedio = "#{:02x}{:02x}{:02x}".format(
                (int(color1[1:3], 16) + int(color2[1:3], 16) + int(color3[1:3], 16) + int(color4[1:3], 16)) // 4,
                (int(color1[3:5], 16) + int(color2[3:5], 16) + int(color3[3:5], 16) + int(color4[3:5], 16)) // 4,
                (int(color1[5:7], 16) + int(color2[5:7], 16) + int(color3[5:7], 16) + int(color4[5:7], 16)) // 4
            )
            
            # Añadir la cara como un polígono con su profundidad z promedio
            poligonos.append(((x1, y1, z1), (x2, y2, z2), (x3, y3, z3), (x4, y4, z4), color_promedio))
    
    # Ordenar los polígonos por su profundidad z promedio (de atrás hacia adelante)
    poligonos.sort(key=lambda p: (p[0][2] + p[1][2] + p[2][2] + p[3][2]) / 4, reverse=True)
    
    # Dibujar los polígonos
    for pol in poligonos:
        x1, y1, _ = pol[0]
        x2, y2, _ = pol[1]
        x3, y3, _ = pol[2]
        x4, y4, _ = pol[3]
        color_promedio = pol[4]
        
        # Dibujar la cara como un polígono
        lienzo_esfera.create_polygon(
            x1, y1, x3, y3, x2, y2, x4, y4,
            fill=color_promedio, outline="black"
        )
                
    # Dibujar el contorno de la esfera
    lienzo_esfera.create_oval(centro_x - radio, centro_y - radio, centro_x + radio, centro_y + radio, outline="white")

# Función para desplazar la vista
def desplazar(dx, dy, paso=1):
    global x_inicio, y_inicio, ancho, alto, tamano_seccion, direccion_personaje

    # Determinar la dirección del personaje basada en el movimiento
    if dx > 0:
        direccion_personaje = "este"
    elif dx < 0:
        direccion_personaje = "oeste"
    elif dy > 0:
        direccion_personaje = "sur"
    elif dy < 0:
        direccion_personaje = "norte"

    # Mover las posiciones de inicio por el tamaño del paso
    x_inicio = (x_inicio + dx * paso) % ancho
    y_inicio = (y_inicio + dy * paso) % alto
    actualizar_lienzo()  # Actualizar el lienzo
    dibujar_esfera()  # Redibujar la esfera
    actualizar_cruceta()  # Actualizar la cruceta

# Función para inicializar la base de datos
def iniciar_bd():
    conexion = sqlite3.connect("datos_terreno.db")
    cursor = conexion.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS terreno (x INTEGER, y INTEGER, color TEXT, altura INTEGER, PRIMARY KEY (x, y))")
    cursor.execute("CREATE TABLE IF NOT EXISTS nubes (x INTEGER, y INTEGER, color TEXT, altura INTEGER, PRIMARY KEY (x, y))")
    return conexion, cursor

# Función para actualizar el multiplicador de altura
def actualizar_multiplicador_altura(val):
    global multiplicador_altura
    multiplicador_altura = int(float(val))
    etiqueta_valor_multiplicador_altura.config(text=f"{multiplicador_altura}")
    actualizar_lienzo()

# Función para actualizar el desfase en píxeles en Y
def actualizar_desfase_y_pixel(val):
    global desfase_y_pixel
    desfase_y_pixel = int(float(val))
    etiqueta_valor_desfase_y_pixel.config(text=f"{desfase_y_pixel}")
    actualizar_lienzo()

# Función para actualizar la separación de píxeles
def actualizar_separacion_pixeles(val):
    global separacion_pixeles, lienzo  # Declarar lienzo como global
    separacion_pixeles = int(float(val))
    etiqueta_valor_separacion_pixeles.config(text=f"{separacion_pixeles}")
    lienzo.config(width=tamano_seccion * separacion_pixeles, height=tamano_seccion * separacion_pixeles)
    actualizar_lienzo()

# Función para actualizar el desfase de las nubes
def actualizar_desfase_nube(val):
    global desfase_nube
    desfase_nube = int(float(val))
    etiqueta_valor_desfase_nube.config(text=f"{desfase_nube}")
    actualizar_lienzo()

# Función para actualizar el factor de sombra
def actualizar_factor_sombra(val):
    global factor_sombra
    factor_sombra = float(val)
    etiqueta_valor_factor_sombra.config(text=f"{factor_sombra:.2f}")
    actualizar_lienzo()

# Función para actualizar el multiplicador de transparencia de las nubes
def actualizar_transparencia_nube(val):
    global transparencia_nube
    transparencia_nube = float(val)
    etiqueta_valor_transparencia_nube.config(text=f"{transparencia_nube:.2f}")
    actualizar_lienzo()

# Función para actualizar el brillo de las nubes
def actualizar_brillo_nube(val):
    global brillo_nube
    brillo_nube = int(float(val))
    etiqueta_valor_brillo_nube.config(text=f"{brillo_nube}")
    actualizar_lienzo()

# Función para actualizar la velocidad del tiempo
def actualizar_velocidad_tiempo(val):
    global velocidad_tiempo
    velocidad_tiempo = float(val)
    etiqueta_valor_velocidad_tiempo.config(text=f"{velocidad_tiempo:.1f}")

# Función para actualizar la escala del personaje
def actualizar_escala_personaje(val):
    global escala_personaje
    escala_personaje = float(val)
    etiqueta_valor_escala_personaje.config(text=f"{escala_personaje:.2f}")
    actualizar_lienzo()

# Función para dibujar el mapa equirectangular
def dibujar_mapa_equirectangular():
    global mapa_eq, img_eq, x_inicio, y_inicio, tamano_seccion, ancho, alto, cursor
    
    # Ajustar al tamaño real de la imagen
    ancho_eq, alto_eq = ancho // 16, alto // 16
    mapa_eq = Image.new("RGB", (ancho_eq, alto_eq))
    dibujar = ImageDraw.Draw(mapa_eq)
    
    for x in range(ancho_eq):
        for y in range(alto_eq):
            terreno_x = int((x / ancho_eq) * ancho)
            terreno_y = int((y / alto_eq) * alto)
            cursor.execute("SELECT color FROM terreno WHERE x = ? AND y = ?", (terreno_x, terreno_y))
            resultado = cursor.fetchone()
            if resultado:
                color_str = resultado[0]
                color = tuple(map(int, color_str.split(',')))
                dibujar.point((x, y), fill=color)
    
    # Convertir a formato ImageTk
    img_eq = ImageTk.PhotoImage(mapa_eq)
    
    # Actualizar la etiqueta con el nuevo mapa
    etiqueta_mapa_eq.config(image=img_eq)
    etiqueta_mapa_eq.image = img_eq
    
    # Dibujar la cruceta inicial
    actualizar_cruceta()

# Función para actualizar la cruceta en el mapa equirectangular
def actualizar_cruceta():
    global img_cruceta, x_inicio, y_inicio, tamano_seccion, ancho, alto, mapa_eq
    
    ancho_eq, alto_eq = mapa_eq.size
    
    # Crear una imagen de superposición para la cruceta
    img_cruceta = mapa_eq.copy()
    dibujar = ImageDraw.Draw(img_cruceta)
    
    # Calcular la posición de la cruceta
    eq_x = int((x_inicio + tamano_seccion // 2) * ancho_eq / ancho)
    eq_y = int((y_inicio + tamano_seccion // 2) * alto_eq / alto)
    
    # Dibujar la cruceta
    dibujar.line([(eq_x - 25, eq_y), (eq_x + 25, eq_y)], fill="red")
    dibujar.line([(eq_x, eq_y - 25), (eq_x, eq_y + 25)], fill="red")
    
    # Convertir a formato ImageTk
    img_cruceta_tk = ImageTk.PhotoImage(img_cruceta)
    
    # Actualizar la etiqueta con la superposición de la cruceta
    etiqueta_mapa_eq.config(image=img_cruceta_tk)
    etiqueta_mapa_eq.image = img_cruceta_tk

# Función para manejar clics en el mapa equirectangular
def en_clic_mapa_eq(evento):
    global x_inicio, y_inicio, ancho, alto, etiqueta_mapa_eq
    
    # Calcular las coordenadas del terreno correspondientes
    ancho_eq, alto_eq = mapa_eq.size
    clic_x = evento.x
    clic_y = evento.y
    x_inicio = int((clic_x / ancho_eq) * ancho - tamano_seccion // 2) % ancho
    y_inicio = int((clic_y / alto_eq) * alto - tamano_seccion // 2) % alto
    
    # Actualizar todo
    actualizar_lienzo()
    dibujar_esfera()
    actualizar_cruceta()

# Inicializar la base de datos
conexion, cursor = iniciar_bd()

# Pre-calcular los datos del terreno si no se ha hecho
if cursor.execute("SELECT COUNT(*) FROM terreno").fetchone()[0] == 0:
    print("Calculando datos del terreno. Esto puede tardar un rato...")
    for x in range(ancho):
        for y in range(alto):
            # Generar valor de ruido Perlin para las coordenadas esféricas
            lon = (x / ancho) * 2 * math.pi  # Longitud en [0, 2pi]
            lat = (y / alto) * math.pi  # Latitud en [0, pi]
            lat = lat - math.pi / 2  # Ajustar a rango [-pi/2, pi/2]
            
            nx = math.cos(lat) * math.cos(lon)
            ny = math.cos(lat) * math.sin(lon)
            nz = math.sin(lat)
            valor_perlin = noise.pnoise3(nx * escala, ny * escala, nz * escala, octaves=16, persistence=0.5, lacunarity=2.0)
            
            valor_normalizado = (valor_perlin + 1) / 2
            abs_lat = abs(lat)
            if abs_lat < math.pi / 4:
                umbral_costa = interpolar_valor(0.45, 0.425, abs_lat / (math.pi / 4))
            else:
                umbral_costa = 0.425
            
            umbral_agua = nivel_agua
            umbral_costa = interpolar_valor(umbral_agua + 0.05, umbral_costa, abs_lat / (math.pi / 2))
            
            if valor_normalizado < umbral_agua:
                color = interpolar_color((0, 0, 128), (200, 200, 255), valor_normalizado / umbral_agua)
            elif valor_normalizado < umbral_costa:
                color = interpolar_color((250, 240, 190), (244, 164, 96), (valor_normalizado - umbral_agua) / (umbral_costa - umbral_agua))
            elif valor_normalizado < 0.7:
                color_base = interpolar_color((244, 164, 96), (34, 139, 34), abs_lat / (math.pi / 2))
                color = interpolar_color(color_base, (107, 142, 35), (valor_normalizado - umbral_costa) / (0.7 - umbral_costa))
            else:
                color_base = interpolar_color((139, 137, 137), (34, 139, 34), abs_lat / (math.pi / 2))
                color = interpolar_color((200,200,200), (255, 255, 255), (valor_normalizado - 0.7) / (1.0 - 0.7))
            
            if valor_normalizado >= umbral_agua:
                factor_ruido = noise.pnoise3(x / 100.0, y / 100.0, semilla)
                factor_ruido = (factor_ruido + 1) / 2
                if abs_lat > 2 * math.pi / 5:
                    color = (255, 250, 250)
                elif abs_lat > math.pi / 4:
                    factor_nieve = ((abs_lat - math.pi / 4) / (math.pi / 20)) * factor_ruido
                    color = interpolar_color(color, (255, 255, 255), factor_nieve)
            
            color_str = ','.join(map(str, color))
            cursor.execute("INSERT INTO terreno (x, y, color, altura) VALUES (?, ?, ?, ?)", (x, y, color_str, int(valor_normalizado * 65535)))
    conexion.commit()
    print("Cálculo de datos del terreno completado.")

# Pre-calcular los datos de las nubes si no se ha hecho
if cursor.execute("SELECT COUNT(*) FROM nubes").fetchone()[0] == 0:
    print("Calculando datos de las nubes. Esto puede tardar un rato...")
    for x in range(ancho):
        for y in range(alto):
            # Generar valor de ruido Perlin para la capa de nubes
            lon = (x / ancho) * 2 * math.pi  # Longitud en [0, 2pi]
            lat = (y / alto) * math.pi  # Latitud en [0, pi]
            lat = lat - math.pi / 2  # Ajustar a rango [-pi/2, pi/2]
            
            nx = math.cos(lat) * math.cos(lon)
            ny = math.cos(lat) * math.sin(lon)
            nz = math.sin(lat)
            valor_perlin = noise.pnoise3(nx * escala_nube, ny * escala_nube, nz * escala_nube, octaves=8, persistence=0.5, lacunarity=2.0)
            
            valor_normalizado = (valor_perlin + 1) / 2
            color = interpolar_color((255, 255, 255), (200, 200, 200), valor_normalizado)
            
            color_str = ','.join(map(str, color))
            cursor.execute("INSERT INTO nubes (x, y, color, altura) VALUES (?, ?, ?, ?)", (x, y, color_str, int(valor_normalizado * 65535)))
    conexion.commit()
    print("Cálculo de datos de las nubes completado.")

# Inicializar multiplicador de altura, desfase de píxeles en Y, desfase de nubes, factor de sombra, y brillo de las nubes
multiplicador_altura = 150
desfase_y_pixel = 1000
desfase_nube = 16  # Desfase de nube por defecto
factor_sombra = 0.3  # Factor de oscurecimiento de sombra por defecto
transparencia_nube = 1.0  # Transparencia de nube por defecto
brillo_nube = 154  # Brillo de nube por defecto

# Factor de separación de píxeles para la proyección isométrica
separacion_pixeles = 8

# Crear la ventana ttkbootstrap
raiz = ttk.Window(themename="darkly")
raiz.title("Planeta 1")

# Crear la barra de herramientas superior para controles (deslizadores y botones)
barra_herramientas = ttk.Frame(raiz)
barra_herramientas.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

# Crear un deslizador para ajustar el multiplicador de altura
etiqueta_multiplicador_altura = ttk.Label(barra_herramientas, text="Multiplicador de altura")
etiqueta_multiplicador_altura.grid(row=0, column=0, padx=5)
deslizador_multiplicador_altura = ttk.Scale(barra_herramientas, from_=100, to=2000, orient=HORIZONTAL, command=actualizar_multiplicador_altura)
deslizador_multiplicador_altura.set(multiplicador_altura)
deslizador_multiplicador_altura.grid(row=1, column=0, padx=5)
etiqueta_valor_multiplicador_altura = ttk.Label(barra_herramientas, text=f"{multiplicador_altura}")
etiqueta_valor_multiplicador_altura.grid(row=1, column=1, padx=5)

# Crear un deslizador para ajustar el desfase en píxeles en Y
etiqueta_desfase_y_pixel = ttk.Label(barra_herramientas, text="Desfase del terreno")
etiqueta_desfase_y_pixel.grid(row=0, column=2, padx=5)
deslizador_desfase_y_pixel = ttk.Scale(barra_herramientas, from_=-tamano_seccion//2-200, to=tamano_seccion//2+5500, orient=HORIZONTAL, command=actualizar_desfase_y_pixel)
deslizador_desfase_y_pixel.set(desfase_y_pixel)
deslizador_desfase_y_pixel.grid(row=1, column=2, padx=5)
etiqueta_valor_desfase_y_pixel = ttk.Label(barra_herramientas, text=f"{desfase_y_pixel}")
etiqueta_valor_desfase_y_pixel.grid(row=1, column=3, padx=5)

# Crear un deslizador para ajustar la separación de píxeles
etiqueta_separacion_pixeles = ttk.Label(barra_herramientas, text="Separación de píxeles")
etiqueta_separacion_pixeles.grid(row=0, column=4, padx=5)
deslizador_separacion_pixeles = ttk.Scale(barra_herramientas, from_=1, to=10, orient=HORIZONTAL, command=actualizar_separacion_pixeles)
deslizador_separacion_pixeles.set(separacion_pixeles)
deslizador_separacion_pixeles.grid(row=1, column=4, padx=5)
etiqueta_valor_separacion_pixeles = ttk.Label(barra_herramientas, text=f"{separacion_pixeles}")
etiqueta_valor_separacion_pixeles.grid(row=1, column=5, padx=5)

# Crear un deslizador para ajustar el desfase de las nubes
etiqueta_desfase_nube = ttk.Label(barra_herramientas, text="Separación de las nubes")
etiqueta_desfase_nube.grid(row=0, column=6, padx=5)
deslizador_desfase_nube = ttk.Scale(barra_herramientas, from_=5, to=500, orient=HORIZONTAL, command=actualizar_desfase_nube)
deslizador_desfase_nube.set(desfase_nube)
deslizador_desfase_nube.grid(row=1, column=6, padx=5)
etiqueta_valor_desfase_nube = ttk.Label(barra_herramientas, text=f"{desfase_nube}")
etiqueta_valor_desfase_nube.grid(row=1, column=7, padx=5)

# Crear un deslizador para ajustar el factor de sombra
etiqueta_factor_sombra = ttk.Label(barra_herramientas, text="Factor de sombra")
etiqueta_factor_sombra.grid(row=0, column=8, padx=5)
deslizador_factor_sombra = ttk.Scale(barra_herramientas, from_=0.0, to=1.0, orient=HORIZONTAL, command=actualizar_factor_sombra)
deslizador_factor_sombra.set(factor_sombra)
deslizador_factor_sombra.grid(row=1, column=8, padx=5)
etiqueta_valor_factor_sombra = ttk.Label(barra_herramientas, text=f"{factor_sombra:.2f}")
etiqueta_valor_factor_sombra.grid(row=1, column=9, padx=5)

# Crear un deslizador para ajustar la transparencia de las nubes
etiqueta_transparencia_nube = ttk.Label(barra_herramientas, text="Transparencia de las nubes")
etiqueta_transparencia_nube.grid(row=0, column=10, padx=5)
deslizador_transparencia_nube = ttk.Scale(barra_herramientas, from_=0.1, to=2.0, orient=HORIZONTAL, command=actualizar_transparencia_nube)
deslizador_transparencia_nube.set(transparencia_nube)
deslizador_transparencia_nube.grid(row=1, column=10, padx=5)
etiqueta_valor_transparencia_nube = ttk.Label(barra_herramientas, text=f"{transparencia_nube:.2f}")
etiqueta_valor_transparencia_nube.grid(row=1, column=11, padx=5)

# Crear un deslizador para ajustar el brillo de las nubes
etiqueta_brillo_nube = ttk.Label(barra_herramientas, text="Brillo de las nubes")
etiqueta_brillo_nube.grid(row=0, column=12, padx=5)
deslizador_brillo_nube = ttk.Scale(barra_herramientas, from_=-255, to=255, orient=HORIZONTAL, command=actualizar_brillo_nube)
deslizador_brillo_nube.set(brillo_nube)
deslizador_brillo_nube.grid(row=1, column=12, padx=5)
etiqueta_valor_brillo_nube = ttk.Label(barra_herramientas, text=f"{brillo_nube}")
etiqueta_valor_brillo_nube.grid(row=1, column=13, padx=5)

# Crear un deslizador para ajustar la velocidad del tiempo
etiqueta_velocidad_tiempo = ttk.Label(barra_herramientas, text="Velocidad del tiempo")
etiqueta_velocidad_tiempo.grid(row=0, column=14, padx=5)
deslizador_velocidad_tiempo = ttk.Scale(barra_herramientas, from_=0.1, to=10.0, orient=HORIZONTAL, command=actualizar_velocidad_tiempo)
deslizador_velocidad_tiempo.set(velocidad_tiempo)
deslizador_velocidad_tiempo.grid(row=1, column=14, padx=5)
etiqueta_valor_velocidad_tiempo = ttk.Label(barra_herramientas, text=f"{velocidad_tiempo:.1f}")
etiqueta_valor_velocidad_tiempo.grid(row=1, column=15, padx=5)

# Crear un deslizador para ajustar la escala del personaje
etiqueta_escala_personaje = ttk.Label(barra_herramientas, text="Escala del personaje")
etiqueta_escala_personaje.grid(row=0, column=16, padx=5)
deslizador_escala_personaje = ttk.Scale(barra_herramientas, from_=0.1, to=2.0, orient=HORIZONTAL, command=actualizar_escala_personaje)
deslizador_escala_personaje.set(escala_personaje)
deslizador_escala_personaje.grid(row=1, column=16, padx=5)
etiqueta_valor_escala_personaje = ttk.Label(barra_herramientas, text=f"{escala_personaje:.2f}")
etiqueta_valor_escala_personaje.grid(row=1, column=17, padx=5)

# Crear un gran lienzo para la vista isométrica, ocupando la mitad derecha de la pantalla
lienzo = ttk.Canvas(raiz, width=960, height=1080)
lienzo.grid(row=1, column=1, padx=0, pady=0, sticky="nw")

# Crear un marco para las vistas del lado izquierdo
marco_izquierdo = ttk.Frame(raiz)
marco_izquierdo.grid(row=1, column=0, padx=0, pady=10, sticky="nsew")

# Crear un lienzo más pequeño para la esfera 3D
lienzo_esfera = ttk.Canvas(marco_izquierdo, width=480, height=480, background="black")
lienzo_esfera.grid(row=0, column=0, padx=10, pady=10)

# Crear una etiqueta para el mapa equirectangular
etiqueta_mapa_eq = ttk.Label(marco_izquierdo)
etiqueta_mapa_eq.grid(row=1, column=0, padx=10, pady=10)

# Vincular el evento de clic al mapa equirectangular
etiqueta_mapa_eq.bind("<Button-1>", en_clic_mapa_eq)

# Crear botones para controlar el desplazamiento
marco_btn = ttk.Frame(raiz)
btn_arriba = ttk.Button(marco_btn, text="↑", command=lambda: desplazar(0, -tamano_seccion // 10))
btn_abajo = ttk.Button(marco_btn, text="↓", command=lambda: desplazar(0, tamano_seccion // 10))
btn_izquierda = ttk.Button(marco_btn, text="←", command=lambda: desplazar(-tamano_seccion // 10, 0))
btn_derecha = ttk.Button(marco_btn, text="→", command=lambda: desplazar(tamano_seccion // 10, 0))

btn_arriba.grid(row=0, column=1, padx=5, pady=5)
btn_abajo.grid(row=2, column=1, padx=5, pady=5)
btn_izquierda.grid(row=1, column=0, padx=5, pady=5)
btn_derecha.grid(row=1, column=2, padx=5, pady=5)
marco_btn.grid(row=2, column=1, pady=10)

# Vincular teclas de flecha para desplazamiento, con Shift para movimiento más rápido
def presionar_tecla(evento):
    paso = 5 if evento.state & 0x0001 else 1  # Verificar modificador Shift, usando bitmask para la tecla Shift
    if evento.keysym == 'Up':
        desplazar(0, -1, paso)
    elif evento.keysym == 'Down':
        desplazar(0, 1, paso)
    elif evento.keysym == 'Left':
        desplazar(-1, 0, paso)
    elif evento.keysym == 'Right':
        desplazar(1, 0, paso)

raiz.bind('<Up>', presionar_tecla)
raiz.bind('<Down>', presionar_tecla)
raiz.bind('<Left>', presionar_tecla)
raiz.bind('<Right>', presionar_tecla)

# Crear la clase NPC
class NPC:
    def __init__(self, x, y, direccion="sur"):
        self.x = x
        self.y = y
        self.direccion = direccion
        self.sprite = sprites[self.direccion]
        self.ultima_giro = None  # Para rastrear la última dirección de giro

    def mover(self):
        # Vectores de dirección
        direcciones = {
            "norte": (0, -1),
            "sur": (0, 1),
            "este": (1, 0),
            "oeste": (-1, 0)
        }
        
        # Mapeo de dirección opuesta
        direccion_opuesta = {
            "norte": "sur",
            "sur": "norte",
            "este": "oeste",
            "oeste": "este"
        }

        # Posibles direcciones: adelante, izquierda, derecha
        movimientos_posibles = {
            "norte": ["norte", "oeste", "este"],
            "sur": ["sur", "este", "oeste"],
            "este": ["este", "norte", "sur"],
            "oeste": ["oeste", "sur", "norte"]
        }

        # Excluir la dirección de retroceso a menos que el NPC esté bloqueado por agua
        direcciones_posibles = movimientos_posibles[self.direccion]
        
        # Aleatorizar pero priorizar el movimiento hacia adelante, y prevenir giros repetitivos en la misma dirección
        random.shuffle(direcciones_posibles)
        for nueva_direccion in direcciones_posibles:
            if nueva_direccion == self.ultima_giro and nueva_direccion != direcciones_posibles[0]:
                continue  # Saltar si conduce a un movimiento circular
            
            dx, dy = direcciones[nueva_direccion]
            nuevo_x = (self.x + dx) % ancho
            nuevo_y = (self.y + dy) % alto

            # Verificar si la nueva posición es tierra o agua
            cursor.execute("SELECT altura FROM terreno WHERE x = ? AND y = ?", (nuevo_x, nuevo_y))
            resultado = cursor.fetchone()
            if resultado:
                valor_altura = resultado[0] / 65535.0
                if valor_altura >= nivel_agua:
                    # Mover a la nueva posición si es tierra
                    self.x = nuevo_x
                    self.y = nuevo_y
                    self.ultima_giro = None if nueva_direccion == self.direccion else nueva_direccion
                    self.direccion = nueva_direccion
                    break
            else:
                continue  # Si está fuera de límites, continuar a la siguiente dirección
        
        # Actualizar sprite basado en la nueva dirección
        self.sprite = sprites[self.direccion]

    def dibujar(self, lienzo, iso_x, iso_y):
        # Escalar el sprite basado en la escala global del personaje
        sprite_escalado = self.sprite.resize((int(ancho_sprite * escala_personaje), int(alto_sprite * escala_personaje)), Image.Resampling.LANCZOS)
        lienzo.paste(sprite_escalado, (iso_x - sprite_escalado.width // 2, iso_y - sprite_escalado.height // 2), sprite_escalado)
    
    def dibujar_en_mapa(self, dibujar, ancho_eq, alto_eq):
        # Dibujar cruceta en el mapa equirectangular
        eq_x = int((self.x / ancho) * ancho_eq)
        eq_y = int((self.y / alto) * alto_eq)
        dibujar.line([(eq_x - 25, eq_y), (eq_x + 25, eq_y)], fill="red")
        dibujar.line([(eq_x, eq_y - 25), (eq_x, eq_y + 25)], fill="red")

# Lista para almacenar todos los NPCs
npcs = []

# Inicializar 30 NPCs en posiciones aleatorias en tierra
for _ in range(130):
    while True:
        x = random.randint(0, ancho - 1)
        y = random.randint(0, alto - 1)
        cursor.execute("SELECT altura FROM terreno WHERE x = ? AND y = ?", (x, y))
        resultado = cursor.fetchone()
        if resultado and resultado[0] / 65535.0 >= nivel_agua:
            npc = NPC(x, y)
            npcs.append(npc)
            break

# Función para actualizar los NPCs
def actualizar_npcs():
    global lienzo, tk_img, etiqueta_mapa_eq, img_eq
    
    for npc in npcs:
        npc.mover()
    
    # Redibujar la vista isométrica con NPCs
    actualizar_lienzo()
    
    # Redibujar el mapa equirectangular con las posiciones de los NPCs
    ancho_eq, alto_eq = mapa_eq.size
    dibujar = ImageDraw.Draw(mapa_eq)
    for npc in npcs:
        npc.dibujar_en_mapa(dibujar, ancho_eq, alto_eq)
    
    # Convertir el mapa actualizado a formato ImageTk y actualizar la etiqueta
    img_eq = ImageTk.PhotoImage(mapa_eq)
    etiqueta_mapa_eq.config(image=img_eq)
    etiqueta_mapa_eq.image = img_eq

    # Programar la próxima actualización
    raiz.after(1000, actualizar_npcs)

# Iniciar el ciclo principal de ttkbootstrap
raiz.after(100, actualizar_lienzo)
raiz.after(100, dibujar_esfera)
raiz.after(100, dibujar_mapa_equirectangular)
raiz.after(100, actualizar_hora)
raiz.after(1000, actualizar_npcs)  # Iniciar actualizaciones de NPCs
raiz.mainloop()

# Cerrar la conexión a la base de datos cuando se cierra la aplicación
conexion.close()
