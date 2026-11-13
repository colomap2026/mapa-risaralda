"""Genera img/relieve.png: el sombreado de montañas de Risaralda, alineado con el mapa.

Uso:  python -I fuentes/relieve.py fuentes/datos/zona.geojson fuentes/datos/dem img/relieve.png

- Elevación: Terrain Tiles de AWS (formato "terrarium", zoom 11; datos SRTM y otros).
  Si faltan teselas, el script imprime sus direcciones y se detiene (código 2).
- La proyección es la misma de build.py, así que la imagen cae exactamente sobre el mapa
  (ocupa todo el viewBox 0 0 W H).
- Salida: PNG gris + transparencia. Laderas al sol = blanco translúcido, laderas en sombra =
  negro translúcido, terreno plano = transparente. Las cumbres más altas (páramo y nevado) se aclaran.
Solo usa la biblioteca estándar de Python.
"""
import json, math, os, struct, sys, unicodedata, zlib

src, carpeta_dem, salida = sys.argv[1], sys.argv[2], sys.argv[3]
ZOOM = 11
ESCALA = 2           # píxeles de la imagen por unidad del mapa (más nitidez al acercar)
EXAGERACION = 1.0    # exageración vertical del sombreado
SUAVIZADO = 2        # radio (en píxeles de la imagen) del suavizado de la elevación
SOMBRA, BRILLO = 0.58, 0.3  # opacidad máxima de las sombras y de las laderas al sol
SOL_AZ, SOL_ALT = 315, 45   # luz desde el noroeste, como en los mapas clásicos

# ---- misma proyección que build.py ----
NAMES = {"66001", "66045", "66075", "66088", "66170", "66318", "66383", "66400", "66440", "66456",
         "66572", "66594", "66682", "66687"}
NOMBRES = ["Pereira", "Apía", "Balboa", "Belén de Umbría", "Dosquebradas", "Guática", "La Celia", "La Virginia",
           "Marsella", "Mistrató", "Pueblo Rico", "Quinchía", "Santa Rosa de Cabal", "Santuario"]
def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper().strip()
VALIDOS = {norm(n) for n in NOMBRES}
def in_risaralda(f):
    geom = f["geometry"]
    ring = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"][0][0]
    lon = sum(c[0] for c in ring) / len(ring); lat = sum(c[1] for c in ring) / len(ring)
    return -76.5 < lon < -75.3 and 4.6 < lat < 5.6

g = json.load(open(src, encoding="utf-8"))
xs, ys = [], []
for f in g["features"]:
    if norm(f["properties"]["shapeName"]) in VALIDOS and in_risaralda(f):
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for p in polys:
            for r in p:
                xs.extend(c[0] for c in r); ys.extend(c[1] for c in r)
lat0 = (min(ys) + max(ys)) / 2
k = math.cos(math.radians(lat0))
W = 900.0; pad = 30
sx = (W - 2 * pad) / ((max(xs) - min(xs)) * k)
H = (max(ys) - min(ys)) * sx + 2 * pad
X_MIN, Y_MAX = min(xs), max(ys)
W_int, H_int = int(f"{W:.0f}"), int(f"{H:.0f}")   # el viewBox que escribe build.py
def lonlat(x, y):
    return (x - pad) / (k * sx) + X_MIN, Y_MAX - (y - pad) / sx

# ---- teselas necesarias ----
N = 2 ** ZOOM
def a_tesela(lon, lat):
    t = math.radians(lat)
    return (lon + 180) / 360 * N, (1 - math.asinh(math.tan(t)) / math.pi) / 2 * N
lon_a, lat_a = lonlat(0, 0); lon_b, lat_b = lonlat(W_int, H_int)
tx0, ty0 = a_tesela(lon_a, lat_a); tx1, ty1 = a_tesela(lon_b, lat_b)
TX = range(int(tx0) - 0, int(tx1) + 1); TY = range(int(ty0), int(ty1) + 1)
faltan = [(x, y) for x in TX for y in TY if not os.path.exists(os.path.join(carpeta_dem, f"{ZOOM}_{x}_{y}.png"))]
if faltan:
    for x, y in faltan:
        print(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{ZOOM}/{x}/{y}.png {ZOOM}_{x}_{y}.png")
    sys.exit(2)

# ---- lector de PNG (RGB/RGBA de 8 bits, como las teselas terrarium) ----
def leer_png(ruta):
    datos = open(ruta, "rb").read()
    assert datos[:8] == b"\x89PNG\r\n\x1a\n"
    i, idat = 8, b""
    while i < len(datos):
        largo, tipo = struct.unpack(">I4s", datos[i:i + 8])
        cuerpo = datos[i + 8:i + 8 + largo]
        if tipo == b"IHDR":
            ancho, alto, prof, color = struct.unpack(">IIBB", cuerpo[:10])
            assert prof == 8 and color in (2, 6), (ruta, prof, color)
        elif tipo == b"IDAT":
            idat += cuerpo
        i += 12 + largo
    bpp = 3 if color == 2 else 4
    crudo = zlib.decompress(idat)
    fila = ancho * bpp
    prev = bytearray(fila)
    elev = []
    pos = 0
    for _ in range(alto):
        filtro = crudo[pos]; linea = bytearray(crudo[pos + 1:pos + 1 + fila]); pos += 1 + fila
        if filtro == 1:
            for j in range(bpp, fila): linea[j] = (linea[j] + linea[j - bpp]) & 255
        elif filtro == 2:
            for j in range(fila): linea[j] = (linea[j] + prev[j]) & 255
        elif filtro == 3:
            for j in range(fila): linea[j] = (linea[j] + ((linea[j - bpp] if j >= bpp else 0) + prev[j]) // 2) & 255
        elif filtro == 4:
            for j in range(fila):
                a = linea[j - bpp] if j >= bpp else 0; b = prev[j]; c = prev[j - bpp] if j >= bpp else 0
                p = a + b - c; pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                linea[j] = (linea[j] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = linea
        elev.append([linea[j] * 256 + linea[j + 1] + linea[j + 2] / 256 - 32768 for j in range(0, fila, bpp)])
    return elev

mosaico = {}
for x in TX:
    for y in TY:
        mosaico[(x, y)] = leer_png(os.path.join(carpeta_dem, f"{ZOOM}_{x}_{y}.png"))
X0, Y0 = TX[0] * 256, TY[0] * 256
XMAX, YMAX = (TX[-1] + 1) * 256 - 1, (TY[-1] + 1) * 256 - 1
def alt_px(px, py):
    px = min(max(px, X0), XMAX); py = min(max(py, Y0), YMAX)
    return mosaico[(px // 256, py // 256)][py % 256][px % 256]
def altura(lon, lat):
    fx, fy = a_tesela(lon, lat)
    fx = fx * 256 - 0.5; fy = fy * 256 - 0.5
    ix, iy = math.floor(fx), math.floor(fy); dx, dy = fx - ix, fy - iy
    a = alt_px(ix, iy); b = alt_px(ix + 1, iy); c = alt_px(ix, iy + 1); d = alt_px(ix + 1, iy + 1)
    return (a * (1 - dx) + b * dx) * (1 - dy) + (c * (1 - dx) + d * dx) * dy

# ---- elevación en la rejilla de la imagen ----
AW, AH = W_int * ESCALA, H_int * ESCALA
E = []
for j in range(AH):
    E.append([altura(*lonlat((i + 0.5) / ESCALA, (j + 0.5) / ESCALA)) for i in range(AW)])
todas = [e for fila in E for e in fila]
print("elevación en el recuadro:", round(min(todas)), "a", round(max(todas)), "m", file=sys.stderr)

# suavizado (dos pasadas de caja): a la escala del mapa el detalle fino solo se ve como ruido
def suavizar(M, r):
    alto, ancho = len(M), len(M[0])
    tmp = []
    for fila in M:
        acum = [0.0]
        for v in fila: acum.append(acum[-1] + v)
        tmp.append([(acum[min(i + r + 1, ancho)] - acum[max(i - r, 0)]) / (min(i + r + 1, ancho) - max(i - r, 0)) for i in range(ancho)])
    sal = [[0.0] * ancho for _ in range(alto)]
    for i in range(ancho):
        acum = [0.0]
        for j in range(alto): acum.append(acum[-1] + tmp[j][i])
        for j in range(alto):
            a, b = max(j - r, 0), min(j + r + 1, alto)
            sal[j][i] = (acum[b] - acum[a]) / (b - a)
    return sal
for _ in range(2):
    E = suavizar(E, SUAVIZADO)

# ---- sombreado ----
celda = 111320 / (sx * ESCALA)   # metros por píxel (igual en x y en y)
az, alt = math.radians(SOL_AZ), math.radians(SOL_ALT)
L = (math.cos(alt) * math.sin(az), math.cos(alt) * math.cos(az), math.sin(alt))  # este, norte, arriba
plano = L[2]
pix = bytearray()
for j in range(AH):
    pix.append(0)  # filtro "ninguno"
    arriba, abajo = E[max(j - 1, 0)], E[min(j + 1, AH - 1)]
    fila = E[j]
    for i in range(AW):
        dzx = (fila[min(i + 1, AW - 1)] - fila[max(i - 1, 0)]) / (2 * celda) * EXAGERACION
        dzn = (arriba[i] - abajo[i]) / (2 * celda) * EXAGERACION   # hacia el norte
        n = math.sqrt(dzx * dzx + dzn * dzn + 1)
        luz = (-dzx * L[0] - dzn * L[1] + L[2]) / n
        delta = luz - plano
        if delta < 0:   # sombra: negro translúcido
            gris, a = 0.0, min(1.0, -delta * 1.4) * SOMBRA
        else:           # ladera al sol: blanco translúcido
            gris, a = 1.0, min(1.0, delta * 2.0) * BRILLO
        # páramo y nevado (más de ~3300 m): se aclaran poco a poco
        e = fila[i]
        if e > 3300:
            t = min(1.0, (e - 3300) / 1400) * 0.45
            sa = a + t * (1 - a)
            gris = (gris * a + 1.0 * t * (1 - a)) / sa if sa else 1.0
            a = sa
        pix.append(int(gris * 255 + 0.5))
        pix.append(int(a * 63 + 0.5) * 4)   # alfa en 64 niveles: comprime mucho mejor y no se nota

def bloque(tipo, cuerpo):
    return struct.pack(">I", len(cuerpo)) + tipo + cuerpo + struct.pack(">I", zlib.crc32(tipo + cuerpo) & 0xffffffff)
png = (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", AW, AH, 8, 4, 0, 0, 0))
       + bloque(b"IDAT", zlib.compress(bytes(pix), 9)) + bloque(b"IEND", b""))
os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
open(salida, "wb").write(png)
print(f"{salida}: {AW}x{AH} px, {len(png) // 1024} KB (mapa {W_int}x{H_int})", file=sys.stderr)

# vista previa opcional (4.º argumento): el relieve sobre el verde del mapa, dentro del departamento
if len(sys.argv) > 4:
    anillos = []
    for f in g["features"]:
        if norm(f["properties"]["shapeName"]) in VALIDOS and in_risaralda(f):
            geom = f["geometry"]
            for p in ([geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]):
                for r in p:
                    anillos.append([((c[0] - X_MIN) * k * sx + pad, (Y_MAX - c[1]) * sx + pad) for c in r])
    VERDE = (0x4c, 0x8f, 0x5a)
    filas = bytearray()
    for y in range(H_int):
        yc = y + 0.5
        cortes = []
        for r in anillos:
            for (x1, y1), (x2, y2) in zip(r, r[1:]):
                if (y1 > yc) != (y2 > yc):
                    cortes.append(x1 + (yc - y1) * (x2 - x1) / (y2 - y1))
        cortes.sort()
        dentro = [False] * W_int
        for a, b in zip(cortes[::2], cortes[1::2]):
            for x in range(max(0, int(a + 0.5)), min(W_int, int(b + 0.5))):
                dentro[x] = True
        filas.append(0)
        for x in range(W_int):
            if not dentro[x]:
                filas += b"\xff\xff\xff"; continue
            o = 1 + (y * ESCALA) * (AW * 2 + 1) + (x * ESCALA) * 2
            gris, a = pix[o] / 255, pix[o + 1] / 255
            filas += bytes(int(c * (1 - a) + gris * 255 * a) for c in VERDE)
    prev = (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", W_int, H_int, 8, 2, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(bytes(filas), 6)) + bloque(b"IEND", b""))
    open(sys.argv[4], "wb").write(prev)
