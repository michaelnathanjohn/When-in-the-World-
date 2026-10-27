"""Builds data/globes.js: every globe in the game.
Usage (run from the site folder):  python source/build_globes.py <cshapes_2_gw.topojson.xz> [source/maps.js]
 - cshapes_2_gw.topojson.xz ships with the CShapes R package (github.com/cran/cshapes, inst/extdata).
 - source/maps.js comes from build_maps.py (Historical Basemaps) and supplies the 1800, 1815 and 1880 globes
   and the land backdrop. CShapes only starts in 1886.

From 1886 on there is a globe for every stretch of years in which nothing visible changed: borders,
country names, capitals and city names. A snapshot is taken on 1 July of each year; years that look
identical are merged, and that run of years is the globe's full-marks window."""
import json, lzma, math, sys, hashlib, os
from build_capitals import FIX, CLEAN, EARLY, SKIP
TOL = 0.15
LAST_DATA_YEAR, PRESENT = 2019, 2026     # CShapes ends in 2019; later years reuse its 2019 borders with later names
HB = {1800: (1800, 1802, "Spain still holds Louisiana, the Batavian Republic exists, and India is divided among the Maratha Confederacy, the Sikhs and others."),
      1815: (1815, 1818, "After the Congress of Vienna: Prussia, the Austrian Empire and the German states are redrawn, Sweden and Norway share a king, and Latin America is still under Spanish viceroyalties."),
      1880: (1878, 1883, "Germany and Italy are unified, Africa is mostly still independent (the Scramble begins in the 1880s), and the Transvaal and Orange Free State exist.")}

# ---- country names as used at the time (CShapes name -> [(before this year, old name)]) ----
# Names as people used them at the time. "name": [(before this year, old name), ...]; the cleaned name is the default.
OVR = {
 "Russia (Soviet Union)": [(1917,"Russian Empire"),(1922,"Russia"),(1992,"U.S.S.R.")],
 "Turkey (Ottoman Empire)": [(1923,"Ottoman Empire")], "Iran (Persia)": [(1935,"Persia")],
 "Sri Lanka (Ceylon)": [(1972,"Ceylon")], "Myanmar (Burma)": [(1989,"Burma")],
 "Zimbabwe (Rhodesia)": [(1965,"Southern Rhodesia"),(1980,"Rhodesia")], "Tanzania (Tanganyika)": [(1964,"Tanganyika")],
 "Burkina Faso (Upper Volta)": [(1984,"Upper Volta")], "Cambodia (Kampuchea)": [(1976,"Cambodia"),(1990,"Kampuchea")],
 "Congo, Democratic Republic of (Zaire)": [(1908,"Congo Free State"),(1960,"Belgian Congo"),(1971,"Congo (Léopoldville)"),(1997,"Zaire")],
 "Swaziland (Eswatini)": [(2018,"Swaziland")], "Macedonia (FYROM/North Macedonia)": [(2019,"Macedonia")],
 "Belarus (Byelorussia)": [(1991,"Byelorussia")], "Germany (Prussia)": [(1919,"German Empire")],
 "German Federal Republic": [(1950,"Germany (Western Allied zones)"),(1991,"West Germany")],   # reunified Oct 1990, after the July snapshot
 "German Democratic Republic": [(1950,"Germany (Soviet zone)"),(9999,"East Germany")],
 "Vietnam (Annam/Cochin China/Tonkin)": [(9999,"French Indochina")], "Vietnam, Democratic Republic of": [(1976,"North Vietnam")],
 "Vietnam, Republic of": [(9999,"South Vietnam")], "Korea, People's Republic of": [(9999,"North Korea")],
 "Korea, Republic of": [(9999,"South Korea")], "Korea": [(1910,"Korean Empire"),(1946,"Korea (Japan)")],
 "Yemen (Arab Republic of Yemen)": [(1990,"North Yemen")], "Yemen, People's Republic of": [(9999,"South Yemen")],
 "Jordan": [(1946,"Transjordan")], "Sabah (North Borneo)": [(1963,"North Borneo")], "Rumania": [(9999,"Romania")],
 "Cote D'Ivoire": [(9999,"Ivory Coast")], "New Guinea (German New Guinea) (Kaiser Wilhelmsland)": [(9999,"New Guinea (Australia)")],
 "Papua": [(9999,"Papua (Australia)")], "Papua New Guinea": [(1975,"Papua and New Guinea")],
 "West Irian (Dutch New Guinea)": [(9999,"Dutch New Guinea")], "Taiwan": [(1946,"Formosa (Japan)")],
 "Alaska": [(1959,"Alaska (U.S. territory)")], "Hawaii": [(1898,"Kingdom of Hawaii"),(1959,"Hawaii (U.S. territory)")],
 "Indonesia": [(1949,"Dutch East Indies")], "Ghana": [(1957,"Gold Coast")], "Kenya": [(1920,"British East Africa"),(1963,"Kenya Colony")],
 "Zambia": [(1964,"Northern Rhodesia")], "Malawi": [(1964,"Nyasaland")], "Uganda": [(1962,"Uganda Protectorate")],
 "Botswana": [(1966,"Bechuanaland")], "Lesotho": [(1966,"Basutoland")], "Namibia": [(1915,"German South West Africa"),(1990,"South West Africa")],
 "Angola": [(1975,"Portuguese Angola")], "Mozambique": [(1975,"Portuguese East Africa")], "Guinea-Bissau": [(1974,"Portuguese Guinea")],
 "Guinea": [(1958,"French Guinea")], "Mali": [(1960,"French Sudan")], "Benin": [(1975,"Dahomey")], "Sudan": [(1956,"Anglo-Egyptian Sudan")],
 "Libya": [(1951,"Italian Libya")], "Congo": [(1960,"French Congo")], "Central African Republic": [(1960,"Ubangi-Shari")],
 "Equatorial Guinea": [(1968,"Spanish Guinea")], "Djibouti": [(1977,"French Somaliland")], "Malaysia": [(1957,"British Malaya"),(1963,"Malaya")],
 "Cambodia": [(1953,"Cambodia (French)")], "Laos": [(1953,"Laos (French)")], "Israel": [(1948,"Palestine")], "Syria": [(1946,"Syria (French)")],
 "United Arab Emirates": [(1971,"Trucial States")], "Madagascar (Malagasy)": [(9999,"Madagascar")], "Italy/Sardinia": [(9999,"Italy")],
 "Yugoslavia": [(1929,"Kingdom of S.H.S."),(2003,"Yugoslavia"),(2006,"Serbia and Montenegro")],
 "Thailand": [(1939,"Siam")],
 "Kyrgyz Republic": [(9999,"Kyrgyzstan")], "Bosnia-Herzegovina": [(9999,"Bosnia and Herzegovina")],
}
DEFAULT = {"Congo, Democratic Republic of (Zaire)": "D.R. Congo", "Swaziland (Eswatini)": "Eswatini",
 "Macedonia (FYROM/North Macedonia)": "North Macedonia", "Vietnam, Democratic Republic of": "Vietnam",
 "Yemen (Arab Republic of Yemen)": "Yemen", "Yugoslavia": "Yugoslavia",
 "German Federal Republic": "Germany", "German Democratic Republic": "East Germany"}   # CShapes treats reunified Germany (Oct 1990) as the FRG continuing
def era_name(name, y):
    rules = OVR.get(name)
    if rules:
        for until, n in rules:
            if y < until: return n
        if all(u == 9999 for u, _ in rules): return rules[-1][1]
    return DEFAULT.get(name, name.split(" (")[0])

# ---- city names as used at the time: modern name -> [(before this year, old name)] ----
NAMES = {
 "Istanbul": [(1930, "Constantinople")], "Ankara": [(1930, "Angora")], "Izmir": [(1930, "Smyrna")],
 "Beijing": [(1928, "Peking"), (1949, "Peiping"), (1979, "Peking")], "Nanjing": [(1979, "Nanking")], "Chongqing": [(1979, "Chungking")],
 "St. Petersburg": [(1914, "St. Petersburg"), (1924, "Petrograd"), (1991, "Leningrad")], "Oslo": [(1925, "Christiania")],
 "Kinshasa": [(1966, "Léopoldville")], "Harare": [(1982, "Salisbury")], "Maputo": [(1976, "Lourenço Marques")],
 "Jakarta": [(1949, "Batavia")], "Banjul": [(1973, "Bathurst")], "Malabo": [(1973, "Santa Isabel")], "N'Djamena": [(1973, "Fort-Lamy")],
 "Ulaanbaatar": [(1924, "Urga"), (1992, "Ulan Bator")], "Bishkek": [(1926, "Pishpek"), (1991, "Frunze")], "Almaty": [(1921, "Verny"), (1993, "Alma-Ata")],
 "Dushanbe": [(1929, "Dyushambe"), (1961, "Stalinabad")], "Ashgabat": [(1919, "Askhabad"), (1927, "Poltoratsk"), (1992, "Ashkhabad")],
 "Tbilisi": [(1936, "Tiflis")], "Yerevan": [(1936, "Erivan")], "Chisinau": [(1990, "Kishinev")], "Kiev": [(1995, "Kiev"), (9999, "Kyiv")],
 "Tallinn": [(1919, "Reval")], "Dhaka": [(1982, "Dacca")], "Rangoon": [(1989, "Rangoon"), (9999, "Yangon")], "Calcutta": [(2001, "Calcutta"), (9999, "Kolkata")],
 "Saigon": [(1976, "Saigon"), (9999, "Ho Chi Minh City")], "Seoul": [(1910, "Hanseong"), (1946, "Keijō")], "Taipei": [(1895, "Taipei"), (1946, "Taihoku")],
 "Tokyo": [(1868, "Edo")], "Antananarivo": [(1896, "Antananarivo"), (1975, "Tananarive")], "Bandar Seri Begawan": [(1970, "Brunei Town")],
 "Astana": [(1998, "Akmola"), (2019, "Astana"), (2022, "Nur-Sultan")], "Podgorica": [(1946, "Podgorica"), (1992, "Titograd")],
 "Kokopo": [(1918, "Herbertshöhe")], "Usumbura": [], "Bujumbura": [(1962, "Usumbura")], "Durrës": [(1925, "Durazzo")],
}
def city_name(n, y):
    for until, old in NAMES.get(n, []):
        if y < until: return old
    return n
# major cities that are not always capitals: (lat, lon, zoom tier, "from year:name|from year:name")
CITIES = [[40.7, -74, 1, "1800:New York"],
 [51.5, -0.1, 1, "1800:London"],
 [48.9, 2.35, 1, "1800:Paris"],
 [52.5, 13.4, 1, "1800:Berlin"],
 [41.9, 12.5, 1, "1800:Rome"],
 [40.4, -3.7, 1, "1800:Madrid"],
 [30, 31.2, 1, "1800:Cairo"],
 [35.7, 139.7, 1, "1800:Edo|1868:Tokyo"],
 [-33.9, 151.2, 1, "1800:Sydney"],
 [-34.6, -58.4, 1, "1800:Buenos Aires"],
 [19.4, -99.1, 1, "1800:Mexico City"],
 [55.75, 37.6, 1, "1800:Moscow"],
 [-33.9, 18.4, 1, "1800:Cape Town"],
 [28.6, 77.2, 1, "1800:Delhi"],
 [31.2, 121.5, 1, "1800:Shanghai"],
 [-12.05, -77.05, 1, "1800:Lima"],
 [-22.9, -43.2, 1, "1800:Rio de Janeiro"],
 [41, 29, 1, "1800:Constantinople|1930:Istanbul"],
 [39.9, 116.4, 1, "1800:Peking|1930:Peiping|1950:Peking|1980:Beijing"],
 [19.1, 72.9, 1, "1800:Bombay|1995:Mumbai"],
 [22.6, 88.4, 1, "1800:Calcutta|2001:Kolkata"],
 [13.1, 80.3, 2, "1800:Madras|1996:Chennai"],
 [16.8, 96.2, 2, "1800:Rangoon|1989:Yangon"],
 [10.8, 106.7, 1, "1800:Saigon|1976:Ho Chi Minh City"],
 [-6.2, 106.8, 1, "1800:Batavia|1950:Jakarta"],
 [59.9, 30.3, 1, "1800:St. Petersburg|1915:Petrograd|1924:Leningrad|1991:St. Petersburg"],
 [48.7, 44.5, 2, "1800:Tsaritsyn|1925:Stalingrad|1961:Volgograd"],
 [50.45, 30.5, 2, "1800:Kiev|1995:Kyiv"],
 [37.6, 127, 2, "1800:Hanseong|1910:Keijō|1946:Seoul"],
 [-4.3, 15.3, 1, "1881:Léopoldville|1966:Kinshasa"],
 [-11.7, 27.5, 3, "1910:Élisabethville|1966:Lubumbashi"],
 [-17.8, 31.05, 2, "1890:Salisbury|1982:Harare"],
 [-26, 32.6, 2, "1800:Lourenço Marques|1976:Maputo"],
 [23.8, 90.4, 2, "1800:Dacca|1982:Dhaka"],
 [39.9, 32.85, 2, "1800:Angora|1930:Ankara"],
 [38.4, 27.1, 2, "1800:Smyrna|1930:Izmir"],
 [54.35, 18.65, 2, "1800:Danzig|1946:Gdańsk"],
 [51.1, 17, 2, "1800:Breslau|1946:Wrocław"],
 [54.7, 20.5, 2, "1800:Königsberg|1946:Kaliningrad"],
 [53.4, 14.55, 3, "1800:Stettin|1946:Szczecin"],
 [48.15, 17.1, 3, "1800:Pozsony|1919:Bratislava"],
 [46.05, 14.5, 3, "1800:Laibach|1919:Ljubljana"],
 [45.8, 16, 3, "1800:Agram|1919:Zagreb"],
 [49.84, 24.03, 2, "1800:Lemberg|1919:Lwów|1945:Lvov|1991:Lviv"],
 [54.7, 25.3, 2, "1800:Vilna|1920:Wilno|1945:Vilnius"],
 [59.4, 24.75, 3, "1800:Reval|1919:Tallinn"],
 [59.9, 10.75, 2, "1800:Christiania|1925:Oslo"],
 [50.8, 12.9, 3, "1800:Chemnitz|1953:Karl-Marx-Stadt|1990:Chemnitz"],
 [41.7, 44.8, 3, "1800:Tiflis|1936:Tbilisi"],
 [40.2, 44.5, 3, "1800:Erivan|1936:Yerevan"],
 [43.25, 76.9, 3, "1854:Verny|1921:Alma-Ata|1993:Almaty"],
 [42.9, 74.6, 3, "1825:Pishpek|1926:Frunze|1991:Bishkek"],
 [38.55, 68.8, 3, "1800:Dyushambe|1929:Stalinabad|1961:Dushanbe"],
 [47.9, 106.9, 3, "1800:Urga|1924:Ulan Bator"],
 [25, 121.5, 3, "1895:Taihoku|1946:Taipei"],
 [64.2, -51.7, 3, "1800:Godthåb|1979:Nuuk"],
 [3.75, 8.8, 3, "1827:Port Clarence|1844:Santa Isabel|1973:Malabo"],
 [-15.8, -47.9, 2, "1960:Brasília"],
 [56.3, 44, 3, "1800:Nizhny Novgorod|1932:Gorky|1990:Nizhny Novgorod"],
 [56.85, 60.6, 3, "1800:Yekaterinburg|1924:Sverdlovsk|1991:Yekaterinburg"],
 [53.2, 50.1, 3, "1800:Samara|1935:Kuybyshev|1991:Samara"],
 [55, 82.9, 3, "1893:Novonikolayevsk|1926:Novosibirsk"],
 [21, 105.85, 3, "1800:Thang Long|1831:Hanoi"]]

def cities_at(y, caps):
    out = []
    for la, lo, t, s in CITIES:
        n = None
        for part in s.split("|"):
            k, v = part.split(":", 1)
            if int(k) <= y: n = v
        if n and not any(abs(c[0]-la) < .5 and abs(c[1]-lo) < .5 for c in caps): out.append([la, lo, t, n])
    return out

# ---- geometry ----
def dp(pts, tol):
    if len(pts) < 3: return pts
    keep = [False]*len(pts); keep[0] = keep[-1] = True; st = [(0, len(pts)-1)]
    while st:
        a, b = st.pop(); (x1, y1), (x2, y2) = pts[a], pts[b]; dx, dy = x2-x1, y2-y1; L = math.hypot(dx, dy); best, bi = 0, -1
        for i in range(a+1, b):
            x, y = pts[i]; d = math.hypot(x-x1, y-y1) if L == 0 else abs(dy*(x-x1)-dx*(y-y1))/L
            if d > best: best, bi = d, i
        if best > tol: keep[bi] = True; st += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]
def area(r): return 0.5*sum(r[i][0]*r[(i+1) % len(r)][1]-r[(i+1) % len(r)][0]*r[i][1] for i in range(len(r)))
def centroid(r):
    a = area(r)
    if abs(a) < 1e-9: return [sum(p[0] for p in r)/len(r), sum(p[1] for p in r)/len(r)]
    cx = cy = 0
    for i in range(len(r)):
        x1, y1 = r[i]; x2, y2 = r[(i+1) % len(r)]; f = x1*y2-x2*y1; cx += (x1+x2)*f; cy += (y1+y2)*f
    return [cx/(6*a), cy/(6*a)]

def main():
    raw = lzma.open(sys.argv[1]).read() if sys.argv[1].endswith(".xz") else open(sys.argv[1], "rb").read()
    topo = json.loads(raw)
    # simplify each shared border once, so neighbours still meet exactly
    arcs = [[(round(x, 1), round(y, 1)) for x, y in dp([tuple(p) for p in a], TOL)] for a in topo["arcs"]]
    def arc(i): return arcs[i] if i >= 0 else arcs[~i][::-1]
    def ring(ids):
        pts = []
        for i in ids:
            a = arc(i); pts += a if not pts else a[1:]
        out = [list(pts[0])]
        for p in pts[1:]:
            if list(p) != out[-1]: out.append(list(p))
        return out if len(out) >= 4 else None
    geoms = list(topo["objects"].values())[0]["geometries"]
    SHAPES, index = [], {}
    def add_shape(polys):
        keep, tot, best = [], 0, (0, [0, 0])
        for poly in polys:
            ext = poly[0]
            if not ext: continue
            xs = [q[0] for q in ext]; ys = [q[1] for q in ext]
            if max(xs)-min(xs) < 0.4 and max(ys)-min(ys) < 0.4: continue   # skip specks
            a = abs(area(ext))*math.cos(math.radians(centroid(ext)[1])); tot += a
            keep.append([ext]+[h for h in poly[1:] if h])
            if a > best[0]: best = (a, centroid(ext))
        if not keep: return None
        h = hashlib.md5(json.dumps(keep).encode()).hexdigest()
        if h not in index:
            index[h] = len(SHAPES); SHAPES.append({"c": [round(best[1][0], 1), round(best[1][1], 1)], "a": round(tot), "g": keep})
        return index[h]
    rows = []
    for g in geoms:
        if not g.get("arcs"): continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        sid = add_shape([[ring(r) for r in poly] for poly in polys])
        if sid is not None: rows.append((g["properties"], sid))

    def state(y):
        date = f"{min(y, LAST_DATA_YEAR)}-07-01" if y <= LAST_DATA_YEAR else f"{LAST_DATA_YEAR}-12-31"
        act = [(p, s) for p, s in rows if p["start"] <= date <= p["end"]]
        feats = sorted([s, era_name(p["country_name"], y)] for p, s in act)
        caps, seen = [], set()
        for p, s in act:
            if p["country_name"] in SKIP: continue
            n, la, lo = CLEAN.get(p["capname"], p["capname"]), p["caplat"], p["caplong"]
            for a, b, fn, fla, flo in FIX.get(p["country_name"], []):
                if a <= date < b: n, la, lo = fn, fla, flo
            if not n or n in seen: continue
            seen.add(n); caps.append([round(la, 2), round(lo, 2), city_name(n, y)])
        caps.sort()
        return feats, caps, cities_at(y, caps)

    globes, HBS = [], []
    # Historical Basemaps globes before CShapes starts (kept in their own file: different licence)
    hb = json.loads(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps.js")).read().split("=", 1)[1].rstrip(";\n"))
    for y, (lo, hi, note) in HB.items():
        feats = []
        for f in hb[str(y)]:
            sid = len(HBS); HBS.append({"c": f["c"], "a": f["a"], "g": f["g"]}); feats.append([sid, f["n"]])
        caps = [[la, lo_, city_name(n, y)] for n, la, lo_ in EARLY[y]]
        globes.append({"y": y, "lo": lo, "hi": hi, "note": note, "f": feats, "caps": caps, "cities": cities_at(y, caps)})
    land = [poly for f in hb["1994"] for poly in f["g"]]

    # CShapes: one globe per run of identical-looking years
    prev = None
    for y in range(1886, PRESENT+1):
        st = state(y)
        if prev and st == prev[1]: globes[-1]["hi"] = y; continue
        g = {"y": y, "lo": y, "hi": y, "f": st[0], "caps": st[1], "cities": st[2]}
        if prev: g["note"] = describe(prev[1], st, SHAPES)
        else: g["note"] = "This is the first year in the CShapes border data (1886)."
        globes.append(g); prev = (y, st)
    for g in globes:
        if g["lo"] == 2014: g["note"] += " Crimea is drawn inside Russia, as CShapes records it; Russia's 2014 annexation is not recognised by Ukraine or most other countries."
    globes[-1]["hi"] = PRESENT
    globes[-1]["note"] += f" No borders have changed on this map since {globes[-1]['lo']}, so it counts for every year up to the present."
    # Two files because the two sources have different licences (see CREDITS.txt)
    hbg = [g for g in globes if g["y"] in HB]; csg = [g for g in globes if g["y"] not in HB]
    os.makedirs("data", exist_ok=True)
    with open("data/globes-historical-basemaps.js", "w") as fh:
        fh.write("/* Derived from Historical Basemaps (aourednik and contributors), GNU GPL v3. See credits.html. */\n")
        fh.write("window.HB_SHAPES=" + json.dumps(HBS, separators=(",", ":")) + ";\n")
        fh.write("window.LAND=" + json.dumps(land, separators=(",", ":")) + ";\n")
        fh.write("window.HB_GLOBES=" + json.dumps(hbg, ensure_ascii=False, separators=(",", ":")) + ";\n")
    with open("data/globes-cshapes.js", "w") as fh:
        fh.write("/* Derived from CShapes 2.0 (Schvitz et al. 2022, ETH Zurich), licensed CC BY-NC-SA 4.0. Simplified and renamed by this game; this file is shared under the same licence. See credits.html. */\n")
        fh.write("window.CS_SHAPES=" + json.dumps(SHAPES, separators=(",", ":")) + ";\n")
        fh.write("window.CS_GLOBES=" + json.dumps(csg, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(len(globes), "globes,", len(SHAPES), "shapes")
    for g in globes: print(g["lo"], g["hi"], len(g["f"]), "|", g["note"][:150])

def describe(a, b, SHAPES):
    """What changed since the previous globe, biggest things first."""
    an, bn = {n for _, n in a[0]}, {n for _, n in b[0]}
    size = lambda n, fs: -sum(SHAPES[s]["a"] for s, m in fs if m == n)
    new = sorted(bn-an, key=lambda n: size(n, b[0]))[:5]; gone = sorted(an-bn, key=lambda n: size(n, a[0]))[:5]
    ag = {n: tuple(sorted(s for s, m in a[0] if m == n)) for n in an}; bg = {n: tuple(sorted(s for s, m in b[0] if m == n)) for n in bn}
    moved = sorted([n for n in an & bn if ag[n] != bg[n]], key=lambda n: size(n, b[0]))[:5]
    ac, bc = {c[2] for c in a[1]}, {c[2] for c in b[1]}
    cn = sorted(bc-ac)[:5]; cities = sorted({c[3] for c in b[2]}-{c[3] for c in a[2]})[:4]
    out = []
    if new: out.append("New on the map since the previous globe: " + ", ".join(new) + ".")
    if gone: out.append("Gone or renamed: " + ", ".join(gone) + ".")
    if moved: out.append("Borders changed for " + ", ".join(moved) + ".")
    if cn: out.append("New capital names or capitals: " + ", ".join(cn) + ".")
    if cities: out.append("Cities renamed: " + ", ".join(cities) + ".")
    return " ".join(out) or "Only small changes since the previous globe."

if __name__ == "__main__": main()
