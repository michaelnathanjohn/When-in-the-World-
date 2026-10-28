"""Turns historical-basemaps GeoJSON snapshots into one small data/maps.js file.
Usage:  python build_maps.py  <path-to-historical-basemaps-master>
Edit YEARS to add more snapshots (any world_YEAR.geojson in the geojson folder)."""
import json, math, sys, os
YEARS = [1800, 1815, 1880, 1994]   # the game uses 1800-1880; 1994 is only the land backdrop
TOL = 0.15
# EDIT ME: the source data shows many countries under their modern names on old maps.
# "Modern name": [(map year is BEFORE this year, "name used back then"), ...]
RENAME = {
 "Papua New Guinea": [(1945,"New Guinea (colonial)"),(1975,"Papua and New Guinea")],   # independent 1975
 "Ghana":[(1957,"Gold Coast")], "Zimbabwe":[(1980,"Southern Rhodesia")], "Zambia":[(1964,"Northern Rhodesia")],
 "Malawi":[(1964,"Nyasaland")], "Kenya":[(1920,"British East Africa"),(1963,"Kenya Colony")], "Uganda":[(1962,"Uganda Protectorate")],
 "Botswana":[(1966,"Bechuanaland")], "Lesotho":[(1966,"Basutoland")],
 "Namibia":[(1915,"German South West Africa"),(1990,"South West Africa")],
 "Angola":[(1975,"Portuguese Angola")], "Mozambique":[(1975,"Portuguese East Africa")], "Guinea-Bissau":[(1974,"Portuguese Guinea")],
 "Guinea":[(1958,"French Guinea")], "Mali":[(1960,"French Sudan")], "Benin":[(1975,"Dahomey")], "Burkina Faso":[(1984,"Upper Volta")],
 "Sudan":[(1956,"Anglo-Egyptian Sudan")], "Libya":[(1951,"Italian Libya")], "Zaire":[(1960,"Belgian Congo"),(1971,"Congo (Léopoldville)")], "Congo":[(1960,"French Congo")],
 "Central African Republic":[(1960,"Ubangi-Shari")], "Equatorial Guinea":[(1968,"Spanish Guinea")], "Djibouti":[(1977,"French Somaliland")],
 "Bangladesh":[(1947,"Bengal (British India)"),(1971,"East Pakistan")], "Pakistan":[(1947,"British India (NW)")],
 "Indonesia":[(1949,"Dutch East Indies")], "Malaysia":[(1957,"British Malaya"),(1963,"Malaya")], "Sri Lanka":[(1972,"Ceylon")],
 "Cambodia":[(1953,"Cambodia (French)")], "Laos":[(1953,"Laos (French)")], "Vietnam":[(1975,"Vietnam (divided)")],
 "Israel":[(1948,"Palestine")], "Jordan":[(1946,"Transjordan")], "Syria":[(1946,"Syria (French)")],
 "United Arab Emirates":[(1971,"Trucial States")],
 "Kingdom of Hawaii":[(1959,"Hawaii (U.S. territory)")],   # annexed 1898; state only from 1959
 "Zaire (Belgium)":[(1960,"Belgian Congo"),(1971,"Congo (Léopoldville)")],   # source uses the 1971 name on 1920s maps
}
EARLY = {"Papua New Guinea": "New Guinea"}   # for maps before 1900
def era_name(name, year):
    if year < 1900: return EARLY.get(name, name)   # the table above only fixes 1900+ maps
    for until, new in RENAME.get(name, []):
        if year < until: return new
    return name      # simplification in degrees (bigger = smaller file)
src = sys.argv[1] if len(sys.argv) > 1 else "historical-basemaps-master"

def dp(pts, tol):
    if len(pts) < 3: return pts
    keep = [False]*len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts)-1)]
    while stack:
        a, b = stack.pop(); (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2-x1, y2-y1; L = math.hypot(dx, dy); best, bi = 0, -1
        for i in range(a+1, b):
            x, y = pts[i]
            d = math.hypot(x-x1, y-y1) if L == 0 else abs(dy*(x-x1)-dx*(y-y1))/L
            if d > best: best, bi = d, i
        if best > tol: keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]

def area(r): return 0.5*sum(r[i][0]*r[(i+1) % len(r)][1]-r[(i+1) % len(r)][0]*r[i][1] for i in range(len(r)))
def centroid(r):
    a = area(r)
    if abs(a) < 1e-9: return [sum(p[0] for p in r)/len(r), sum(p[1] for p in r)/len(r)]
    cx = cy = 0
    for i in range(len(r)):
        x1, y1 = r[i]; x2, y2 = r[(i+1) % len(r)]; f = x1*y2-x2*y1; cx += (x1+x2)*f; cy += (y1+y2)*f
    return [cx/(6*a), cy/(6*a)]

def ring(r, exterior):
    r = [[round(x, 1), round(y, 1)] for x, y in dp([tuple(p[:2]) for p in r], TOL)]
    out = [r[0]]
    for p in r[1:]:
        if p != out[-1]: out.append(p)
    if len(out) < 4: return None
    if (area(out) < 0) != exterior: out.reverse()   # d3 wants exterior clockwise, holes counter-clockwise
    return out

def region(poly):
    r = poly[0]; x = sum(p[0] for p in r)/len(r); y = sum(p[1] for p in r)/len(r)
    if -172 <= x <= -129 and 51 <= y <= 72: return "AK"
    if -161 <= x <= -154 and 18 <= y <= 23: return "HI"
    return None
def regroup(name, keep, y):
    """Alaska and Hawaii were not U.S. states until 1959, so give them their own labels on older maps."""
    if name in ("United States", "United States of America") and y < 1959:
        ak = [p for p in keep if region(p) == "AK"]; hi = [p for p in keep if region(p) == "HI"]
        rest = [p for p in keep if region(p) is None]
        if y >= 1898: return [(name, rest), ("Alaska (U.S. territory)", ak), ("Hawaii (U.S. territory)", hi)]
        return [(name, rest+hi), ("Alaska (U.S. territory)", ak)]
    if name == "Polynesians" and y == 1800:      # the Hawaiian islands were already a kingdom (Kamehameha, 1795)
        hi = [p for p in keep if region(p) == "HI"]; rest = [p for p in keep if region(p) != "HI"]
        return [(name, rest), ("Kingdom of Hawaii", hi)]
    if name == "Russian Empire" and y >= 1800:
        ak = [p for p in keep if region(p) == "AK"]; rest = [p for p in keep if region(p) != "AK"]
        return [(name, rest)] + ([("Russian America", ak)] if y < 1867 else [])   # after 1867 Alaska belongs to the U.S.
    return [(name, keep)]
def mkfeat(name, keep):
    best = (0, [0, 0]); tot = 0
    for poly in keep:
        a = abs(area(poly[0]))*math.cos(math.radians(centroid(poly[0])[1])); tot += a
        if a > best[0]: best = (a, centroid(poly[0]))
    return {"n": name, "c": [round(best[1][0], 1), round(best[1][1], 1)], "a": round(tot), "g": keep}

maps = {}
for y in YEARS:
    data = json.load(open(os.path.join(src, "geojson", f"world_{y}.geojson")))
    feats = []
    for f in data["features"]:
        name = f["properties"].get("NAME")
        name = era_name(name.strip(), y) if name and name.strip() else None
        g = f["geometry"]
        if not name or not g: continue
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]] if g["type"] == "Polygon" else []
        keep, tot, big = [], 0, (0, [0, 0])
        for poly in polys:
            ext = ring(poly[0], True)
            if not ext: continue
            a = abs(area(ext))*math.cos(math.radians(centroid(ext)[1]))
            xs = [p[0] for p in ext]; ys = [p[1] for p in ext]
            if max(xs)-min(xs) < 0.4 and max(ys)-min(ys) < 0.4: continue   # skip specks
            holes = [h for h in (ring(h, False) for h in poly[1:]) if h]
            keep.append([ext]+holes); tot += a
            if a > big[0]: big = (a, centroid(ext))
        for nm, grp in regroup(name, keep, y):
            if grp: feats.append(mkfeat(nm, grp))
    if 1992 <= y < 2006:   # Serbia + Montenegro were one state (F.R. Yugoslavia, then Serbia and Montenegro)
        sm = [f for f in feats if f["n"] in ("Serbia", "Montenegro")]
        if len(sm) == 2:
            feats = [f for f in feats if f not in sm]
            feats.append(mkfeat("Yugoslavia" if y < 2003 else "Serbia and Montenegro", sm[0]["g"]+sm[1]["g"]))
    maps[y] = feats
    print(y, len(feats), "countries")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps.js")   # input for build_globes.py
with open(out, "w") as fh:
    fh.write("window.MAPS="+json.dumps(maps, separators=(",", ":"))+";")
print("maps.js KB:", os.path.getsize(out)//1024)
