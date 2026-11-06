import json, math, sys

src, out = sys.argv[1], sys.argv[2]
g = json.load(open(src, encoding="utf-8"))

NAMES = {
    "66001": "Pereira", "66045": "Apía", "66075": "Balboa", "66088": "Belén de Umbría",
    "66170": "Dosquebradas", "66318": "Guática", "66383": "La Celia", "66400": "La Virginia",
    "66440": "Marsella", "66456": "Mistrató", "66572": "Pueblo Rico", "66594": "Quinchía",
    "66682": "Santa Rosa de Cabal", "66687": "Santuario",
}

import unicodedata
def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper().strip()
BY_NAME = {norm(v): k for k, v in NAMES.items()}

def in_risaralda(f):
    geom = f["geometry"]
    ring = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"][0][0]
    lon = sum(c[0] for c in ring) / len(ring); lat = sum(c[1] for c in ring) / len(ring)
    return -76.5 < lon < -75.3 and 4.6 < lat < 5.6

feats = []
for f in g["features"]:
    n = norm(f["properties"]["shapeName"])
    if n in BY_NAME and in_risaralda(f):
        f["properties"]["MPIO_CCNCT"] = BY_NAME[n]
        feats.append(f)
print(len(feats), sorted(norm(f["properties"]["shapeName"]) for f in feats), file=sys.stderr)
AREAS = {"66001": 702, "66045": 150, "66075": 119, "66088": 180, "66170": 70, "66318": 101,
         "66383": 92, "66400": 33, "66440": 149, "66456": 565, "66572": 614, "66594": 140,
         "66682": 543, "66687": 191}
rings_all = []
for f in feats:
    geom = f["geometry"]
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    f["_polys"] = polys
    for p in polys:
        rings_all.extend(p)

xs = [c[0] for r in rings_all for c in r]
ys = [c[1] for r in rings_all for c in r]
lat0 = (min(ys) + max(ys)) / 2
k = math.cos(math.radians(lat0))
W = 900.0
pad = 30
sx = (W - 2 * pad) / ((max(xs) - min(xs)) * k)
H = (max(ys) - min(ys)) * sx + 2 * pad

X_MIN, Y_MAX = min(xs), max(ys)
def proj(c):
    return ((c[0] - X_MIN) * k * sx + pad, (Y_MAX - c[1]) * sx + pad)

def ring_area_centroid(pts):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        cr = x1 * y2 - x2 * y1
        a += cr; cx += (x1 + x2) * cr; cy += (y1 + y2) * cr
    a /= 2
    return a, (cx / (6 * a), cy / (6 * a)) if a else pts[0]

def inside(pt, pts):
    x, y = pt; res = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            res = not res
    return res

def edge_dist(pt, pts):
    best = 1e9
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(pt[0] - x1 - t * dx, pt[1] - y1 - t * dy))
    return best

def label_point(pts):
    # punto interior lejos de los bordes (búsqueda en rejilla), sesgado hacia el centroide
    _, c = ring_area_centroid(pts)
    bx = [p[0] for p in pts]; by = [p[1] for p in pts]
    best, bestv = c, -1e9
    n = 40
    for i in range(n + 1):
        for j in range(n + 1):
            p = (min(bx) + (max(bx) - min(bx)) * i / n, min(by) + (max(by) - min(by)) * j / n)
            if inside(p, pts):
                v = edge_dist(p, pts) - 0.15 * math.hypot(p[0] - c[0], p[1] - c[1])
                if v > bestv:
                    best, bestv = p, v
    return best

def simplificar(pts, eps):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1
    i_max, d_max = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * (pts[i][0] - x1) - dx * (pts[i][1] - y1)) / n if (dx or dy) else math.hypot(pts[i][0] - x1, pts[i][1] - y1)
        if d > d_max:
            i_max, d_max = i, d
    if d_max <= eps:
        return [pts[0], pts[-1]]
    return simplificar(pts[:i_max + 1], eps)[:-1] + simplificar(pts[i_max:], eps)

munis = []
vert_owner = {}
for f in feats:
    code = f["properties"]["MPIO_CCNCT"]
    d = []
    biggest = None
    for poly in f["_polys"]:
        for ri, ring in enumerate(poly):
            # ajuste a rejilla de 1 px: los vértices compartidos caen en el mismo punto,
            # así los bordes vecinos siguen coincidiendo exactamente
            pts = []
            for c in ring:
                x, y = proj(c)
                p = (round(x, 1), round(y, 1))
                if not pts or pts[-1] != p:
                    pts.append(p)
            if pts[0] == pts[-1]:
                pts = pts[:-1]
            if len(pts) < 3:
                continue
            d.append("M" + "L".join(f"{x},{y}" for x, y in pts) + "Z")
            if ri == 0:
                a, _ = ring_area_centroid(pts)
                if biggest is None or abs(a) > biggest[0]:
                    biggest = (abs(a), pts)
            for p in pts:
                vert_owner.setdefault(p, set()).add(code)
    # los cálculos internos usan el contorno simplificado; el que se dibuja no cambia
    anillo = simplificar(biggest[1], 0.3)
    lx, ly = label_point(simplificar(biggest[1], 1.5))
    munis.append({"code": code, "name": NAMES[code], "d": "".join(d),
                  "lx": round(lx, 1), "ly": round(ly, 1),
                  "area": AREAS[code], "_anillo": anillo, "_denso": biggest[1]})

# ---- Caminos, ríos, cascadas y cerros reales (OpenStreetMap) ----
osm = json.load(open(sys.argv[4], encoding="utf-8"))["elements"]
RIOS_MAYORES = {"RIO CAUCA", "RIO RISARALDA", "RIO OTUN", "RIO SAN JUAN", "RIO TATAMA", "RIO CONSOTA"}
TOLERANCIA = 4.0  # px: ríos y cerros que van justo sobre el límite departamental

for m in munis:
    a = m["_anillo"]
    m["_caja"] = (min(p[0] for p in a), min(p[1] for p in a), max(p[0] for p in a), max(p[1] for p in a))
    m.update(rio1=[], via1=[], via2=[], cerros=[], cascadas=[])

CELDA = 8.0
rejilla = {}
for m in munis:
    for p in m["_denso"]:
        rejilla.setdefault((int(p[0] // CELDA), int(p[1] // CELDA)), []).append((p, m))

def muni_de(p, tolerante=False):
    for m in munis:
        c = m["_caja"]
        if c[0] <= p[0] <= c[2] and c[1] <= p[1] <= c[3] and inside(p, m["_anillo"]):
            return m
    if tolerante:
        i, j = int(p[0] // CELDA), int(p[1] // CELDA)
        mejor, dist = None, TOLERANCIA
        for a in range(i - 1, i + 2):
            for b in range(j - 1, j + 2):
                for q, m in rejilla.get((a, b), ()):
                    d = math.hypot(p[0] - q[0], p[1] - q[1])
                    if d < dist:
                        mejor, dist = m, d
        return mejor
    return None

def largo(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))

def tramos(geom, tolerante):
    pts = []
    for g in geom:
        p = proj((g["lon"], g["lat"]))
        if pts:
            d = math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1])
            pasos = int(d // 3)
            for k in range(1, pasos):
                pts.append((ultimo[0] + (p[0] - ultimo[0]) * k / pasos, ultimo[1] + (p[1] - ultimo[1]) * k / pasos))
        pts.append(p)
        ultimo = p
    corridas, actual, dueno = [], [], None
    for p in pts:
        m = muni_de(p, tolerante)
        if m is not dueno and actual:
            corridas.append((dueno, actual))
            actual = [actual[-1]] if m is not None and dueno is not None else []
        dueno = m
        if m is not None:
            actual.append(p)
    if actual and dueno is not None:
        corridas.append((dueno, actual))
    return corridas

def a_d(pts):
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts)

conteo = {"via1": 0, "via2": 0, "rio1": 0}
for e in osm:
    t = e.get("tags", {})
    if e["type"] != "way" or "geometry" not in e:
        continue
    hw = t.get("highway")
    if hw in ("motorway", "trunk", "primary", "secondary"):
        # solo el trazado general: fuera las calles urbanas que no hacen parte de una ruta numerada
        if "ref" not in t and norm(t.get("name", "")).split(" ")[0] in ("CALLE", "CARRERA", "AVENIDA", "DIAGONAL", "TRANSVERSAL"):
            continue
        clase, tol, minimo = ("via2" if hw == "secondary" else "via1"), False, 0.2
    elif t.get("waterway") == "river" and norm(t.get("name", "")) in RIOS_MAYORES:
        clase, tol, minimo = "rio1", True, 8
    else:
        continue
    for m, pts in tramos(e["geometry"], tol):
        if largo(pts) < minimo or (clase != "rio1" and "ref" not in t and largo(pts) < 6):
            continue
        s = simplificar(pts, 0.5)
        m[clase].append(a_d(s))
        conteo[clase] += 1
print("tramos:", conteo, file=sys.stderr)

# cerros y cascadas: solo con nombre real; los cerros, los más altos y bien separados
NO_CASCADA = {"PEQUENA", "PISCINAS NATURALES"}
candidatos, cascadas = [], []
for e in osm:
    t = e.get("tags", {})
    if e["type"] != "node":
        continue
    nombre = t.get("name", "").strip()
    p = None
    if t.get("natural") in ("peak", "volcano") and nombre and "ele" in t and len(nombre) > 3 and not nombre.isdigit():
        try:
            ele = float(t["ele"])
        except ValueError:
            continue
        p = proj((e["lon"], e["lat"]))
        m = muni_de(p, True)
        if m:
            candidatos.append((ele, nombre, p, m))
    elif (t.get("waterway") == "waterfall" or t.get("natural") == "waterfall") and nombre and norm(nombre) not in NO_CASCADA:
        p = proj((e["lon"], e["lat"]))
        m = muni_de(p, True)
        if m:
            cascadas.append((nombre, p, m))
candidatos.sort(key=lambda c: -c[0])
elegidos = []
for ele, nombre, p, m in candidatos:
    if all(math.hypot(p[0] - q[2][0], p[1] - q[2][1]) > 75 for q in elegidos):
        elegidos.append((ele, nombre, p, m))
    if len(elegidos) == 9:
        break
print("cerros dentro del departamento:", len(candidatos), file=sys.stderr)
for i, (ele, nombre, p, m) in enumerate(elegidos):
    print(f"  cerro: {nombre} {ele:.0f} m -> {m['name']}", file=sys.stderr)
    m["cerros"].append({"x": round(p[0], 1), "y": round(p[1], 1), "g": ele >= 3800})
for nombre, p, m in cascadas:
    print(f"  cascada: {nombre} -> {m['name']}", file=sys.stderr)
    m["cascadas"].append({"n": nombre, "x": round(p[0], 1), "y": round(p[1], 1)})

# los iconos están en su sitio real: si tapan el nombre de un municipio, se mueve el nombre
ocupado = []  # rectángulos (x0, y0, x1, y1) de iconos y de los nombres que siempre están visibles
for m in munis:
    for c in m["cascadas"]:
        ocupado.append((c["x"] - 9, c["y"] - 11, c["x"] + 9, c["y"] + 9))
    for c in m["cerros"]:
        ocupado.append((c["x"] - 17, c["y"] - 16, c["x"] + 17, c["y"] + 13))
def choca(m, x, y):
    ancho = min(len(m["name"]), 12) * 3.6 + 4
    alto = 15 if len(m["name"]) > 12 and " " in m["name"] else 9
    return any(x + ancho > r[0] and x - ancho < r[2] and y + alto > r[1] and y - alto < r[3] for r in ocupado)
for m in munis:
    if not choca(m, m["lx"], m["ly"]):
        continue
    mejor = None
    for r in range(6, 90, 4):
        for paso in range(16):
            ang = paso * math.pi / 8
            x, y = m["lx"] + r * math.cos(ang), m["ly"] + r * math.sin(ang)
            if inside((x, y), m["_anillo"]) and edge_dist((x, y), m["_anillo"]) > 12 and not choca(m, x, y):
                mejor = (x, y)
                break
        if mejor:
            break
    if mejor:
        m["lx"], m["ly"] = round(mejor[0], 1), round(mejor[1], 1)
    print("nombre movido:", m["name"], "OK" if mejor else "sin hueco", file=sys.stderr)

for m in munis:
    for capa in ("via1", "via2", "rio1"):
        m[capa] = "".join(m[capa])
    del m["_anillo"], m["_denso"], m["_caja"]

# adyacencia por vértices compartidos
adj = {m["code"]: set() for m in munis}
for owners in vert_owner.values():
    for a in owners:
        adj[a] |= owners - {a}

# coloreado con 3 colores (bandera); si no es posible, se permite una 4.ª variante
order = sorted(adj, key=lambda c: -len(adj[c]))
def solve(ncol):
    col = {}
    def bt(i):
        if i == len(order):
            return True
        c = order[i]
        for v in range(ncol):
            if all(col.get(n) != v for n in adj[c]):
                col[c] = v
                if bt(i + 1):
                    return True
                del col[c]
        return False
    return col if bt(0) else None

# Viaducto César Gaviria Trujillo: coordenadas reales, sobre el límite Pereira-Dosquebradas
vx, vy = proj((-75.68583, 4.81778))
borde = [p for p, o in vert_owner.items() if {"66001", "66170"} <= o]
print("distancia del viaducto al limite:", round(min(math.hypot(p[0] - vx, p[1] - vy) for p in borde), 1),
      "ancla:", round(vx, 1), round(vy, 1), file=sys.stderr)

# Mirador El Chaquiro: se ubica en el Alto El Chaquiro de OpenStreetMap
mx, my = proj((-75.6941666, 4.8683323))
# Termales de Santa Rosa de Cabal: coordenadas de hotspringsguides.com
tx, ty = proj((-75.5492288, 4.8384677))
# Casa de la Cultura de Marsella: nodo de OpenStreetMap
cx, cy = proj((-75.7385537, 4.9362359))
for etiqueta, a, b in (("mirador", mx, my), ("termales", tx, ty), ("casa de la cultura", cx, cy)):
    for m in feats:
        anillo = [proj(c) for c in m["_polys"][0][0]]
        if inside((a, b), anillo):
            print(etiqueta, "dentro de:", NAMES[m["properties"]["MPIO_CCNCT"]], "ancla:", round(a, 1), round(b, 1), file=sys.stderr)

tpl = open(sys.argv[3], encoding="utf-8").read()
html = (tpl.replace("__W__", f"{W:.0f}").replace("__H__", f"{H:.0f}")
           .replace("__VX__", f"{vx:.1f}").replace("__VY__", f"{vy:.1f}")
           .replace("__MX__", f"{mx:.1f}").replace("__MY__", f"{my:.1f}")
           .replace("__TX__", f"{tx:.1f}").replace("__TY__", f"{ty:.1f}")
           .replace("__CX__", f"{cx:.1f}").replace("__CY__", f"{cy:.1f}")
           .replace("__DATA__", json.dumps(munis, ensure_ascii=False, separators=(",", ":"))))
open(out, "w", encoding="utf-8").write(html)
