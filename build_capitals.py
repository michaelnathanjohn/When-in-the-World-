"""Builds data/capitals.js: the capital cities to show on each globe.
Usage:  python build_capitals.py <path to cshapes_2_gw.topojson or .topojson.xz>
(The file ships with the CShapes R package: github.com/cran/cshapes, inst/extdata.)

Globes from 1886 on take their capitals from CShapes 2.0 at the globe's date, with the fixes in FIX below.
Globes before 1886 (CShapes starts in 1886) use the hand-made lists in EARLY.
Names are written in their modern form here. The game turns them into the name used at the time
(Constantinople, Peking, Léopoldville...) with its NAMES table in index.html, so cities and capitals agree."""
import json, lzma, sys, os

# globe year -> date to read CShapes at. Add a line here when you add a globe.
DATES = {1900: "1902-07-01", 1914: "1914-06-01", 1920: "1920-07-01", 1930: "1930-01-01", 1936: "1936-02-01",
         1938: "1938-07-01", 1945: "1945-07-01", 1951: "1951-05-01", 1960: "1960-12-01", 1972: "1972-09-01",
         1980: "1980-09-01", 1987: "1987-01-01", 1994: "1994-07-01", 1998: "1998-09-01", 2004: "2004-02-01",
         2009: "2009-09-01", 2012: "2012-11-01", 2016: "2016-06-01"}

# Where CShapes puts the capital in the wrong place for the period.
# country: [(from date, to date, capital name or None to show no capital, lat, lon), ...]
FIX = {
 "Nigeria": [("1900-01-01", "1991-12-12", "Lagos", 6.45, 3.39)],
 "Tanzania (Tanganyika)": [("1891-01-01", "1996-02-01", "Dar es Salaam", -6.80, 39.28)],
 "Malawi": [("1891-01-01", "1975-01-01", "Zomba", -15.39, 35.32)],
 "Zambia": [("1911-01-01", "1935-07-01", "Livingstone", -17.85, 25.86)],
 "Uganda": [("1894-01-01", "1962-10-09", "Entebbe", 0.05, 32.46)],
 "Morocco": [("1886-01-01", "1912-06-01", "Fez", 34.03, -4.98)],
 "Mauritania": [("1900-01-01", "1960-11-28", None, 0, 0)],          # run from Saint-Louis, in Senegal
 "Botswana": [("1886-01-01", "1965-02-03", None, 0, 0)],             # run from Mafeking, in South Africa
 "United Arab Emirates": [("1886-01-01", "1971-12-02", None, 0, 0)], # Trucial States had no single capital
 "China": [("1928-06-15", "1937-11-20", "Nanjing", 32.06, 118.80),
           ("1937-11-20", "1946-05-05", "Chongqing", 29.56, 106.55),
           ("1946-05-05", "1949-10-01", "Nanjing", 32.06, 118.80)],
 "Cameroon": [("1940-01-01", "1946-01-01", "Douala", 4.05, 9.70)],
 "Comoros": [("1886-01-01", "1962-01-01", "Dzaoudzi", -12.78, 45.28)],
 "Sabah (North Borneo)": [("1946-07-15", "1963-09-16", "Jesselton", 5.98, 116.07)],
 "British Somaliland (Somaliland Republic)": [("1941-01-01", "1960-07-01", "Hargeisa", 9.56, 44.06)],
 "Alaska": [("1886-01-01", "1906-01-01", "Sitka", 57.05, -135.33)],
 "Vietnam (Annam/Cochin China/Tonkin)": [("1949-06-14", "1954-05-01", "Saigon", 10.78, 106.70)],
 "German Federal Republic": [("1945-05-08", "1949-09-21", None, 0, 0)],
 "German Democratic Republic": [("1945-05-08", "1949-10-07", "Berlin", 52.52, 13.40)],
}
SKIP = {"West Bank", "Gaza", "Inini"}   # not states; their dots would sit on top of real capitals
# CShapes spellings -> clean modern names (the game adds the historical name)
CLEAN = {"Kinshasa (Léopoldville)": "Kinshasa", "New Delhi (Delhi)": "New Delhi", "Saint Petersburg (Petrograd)": "St. Petersburg",
 "(East) Jerusalem": "Jerusalem", "East Berlin": "East Berlin", "Bukarest": "Bucharest", "T'bilisi": "Tbilisi", "Masqat": "Muscat",
 "Pape'ete": "Papeete", "Tirane": "Tirana", "Singapore City": "Singapore", "Pietermatritzburg": "Pietermaritzburg",
 "Chipata (Fort Jameson)": "Fort Jameson", "Old Calabar (Calabar)": "Old Calabar", "Sandakan (Elopura)": "Sandakan",
 "Rabaul (Simpsonhafen)": "Rabaul", "Brasilia": "Brasília", "Bogota": "Bogotá", "Yaounde": "Yaoundé", "San Jose": "San José", "Asuncion": "Asunción",
 "Reykjavik": "Reykjavík", "Lome": "Lomé", "Male": "Malé", "Tetuan": "Tétouan", "Noumea": "Nouméa", "El Aaiun": "El Aaiún", "Tulaghi": "Tulagi", "Durres": "Durrës", "Ulan Bator": "Ulaanbaatar"}

# Before 1886: (name, lat, lon). Capitals of the main states and colonies on those globes.
EARLY = {
 1800: [("London",51.51,-0.13),("Paris",48.86,2.35),("Madrid",40.42,-3.70),("Lisbon",38.72,-9.14),("Vienna",48.21,16.37),
        ("Berlin",52.52,13.40),("St. Petersburg",59.94,30.31),("Istanbul",41.01,28.98),("Stockholm",59.33,18.07),
        ("Copenhagen",55.68,12.57),("Rome",41.90,12.50),("Naples",40.85,14.27),("Cagliari",39.22,9.11),("The Hague",52.08,4.30),
        ("Bern",46.95,7.45),("Dresden",51.05,13.74),("Munich",48.14,11.58),("Washington",38.90,-77.04),("Mexico City",19.43,-99.13),
        ("Lima",-12.05,-77.04),("Buenos Aires",-34.60,-58.38),("Bogotá",4.71,-74.07),("Rio de Janeiro",-22.91,-43.17),
        ("Quebec City",46.81,-71.21),("Havana",23.11,-82.37),("Caracas",10.49,-66.88),("Santiago",-33.45,-70.67),
        ("Guatemala City",14.63,-90.51),("Cairo",30.04,31.24),("Tehran",35.69,51.39),("Kabul",34.53,69.17),("Pune",18.52,73.86),
        ("Calcutta",22.57,88.36),("Delhi",28.66,77.23),("Kathmandu",27.71,85.32),("Amarapura",21.90,96.05),("Bangkok",13.75,100.50),
        ("Hue",16.46,107.59),("Beijing",39.90,116.40),("Seoul",37.57,126.98),("Tokyo",35.68,139.69),("Cape Town",-33.92,18.42),
        ("Algiers",36.75,3.06),("Tunis",36.81,10.18),("Tripoli",32.89,13.19),("Fez",34.03,-4.98),("Gondar",12.61,37.47),
        ("Kumasi",6.69,-1.62),("Abomey",7.18,1.99),("Muscat",23.59,58.41),("Diriyah",24.73,46.57),("Bukhara",39.77,64.42),
        ("Khiva",41.38,60.36),("Antananarivo",-18.88,47.51),("Batavia",-6.13,106.81),("Manila",14.60,120.98),("Warsaw",52.23,21.01)],
 1815: [("London",51.51,-0.13),("Paris",48.86,2.35),("Madrid",40.42,-3.70),("Lisbon",38.72,-9.14),("Vienna",48.21,16.37),
        ("Berlin",52.52,13.40),("St. Petersburg",59.94,30.31),("Istanbul",41.01,28.98),("Stockholm",59.33,18.07),("Oslo",59.91,10.75),
        ("Copenhagen",55.68,12.57),("Rome",41.90,12.50),("Naples",40.85,14.27),("Turin",45.07,7.69),("Amsterdam",52.37,4.90),
        ("Warsaw",52.23,21.01),("Dresden",51.05,13.74),("Munich",48.14,11.58),("Stuttgart",48.78,9.18),("Hanover",52.37,9.73),
        ("Washington",38.90,-77.04),("Mexico City",19.43,-99.13),("Lima",-12.05,-77.04),("Buenos Aires",-34.60,-58.38),
        ("Bogotá",4.71,-74.07),("Rio de Janeiro",-22.91,-43.17),("Quebec City",46.81,-71.21),("Havana",23.11,-82.37),
        ("Caracas",10.49,-66.88),("Santiago",-33.45,-70.67),("Guatemala City",14.63,-90.51),("Cairo",30.04,31.24),("Tehran",35.69,51.39),
        ("Kabul",34.53,69.17),("Lahore",31.55,74.34),("Pune",18.52,73.86),("Calcutta",22.57,88.36),("Kathmandu",27.71,85.32),
        ("Amarapura",21.90,96.05),("Bangkok",13.75,100.50),("Hue",16.46,107.59),("Beijing",39.90,116.40),("Seoul",37.57,126.98),
        ("Tokyo",35.68,139.69),("Cape Town",-33.92,18.42),("Algiers",36.75,3.06),("Tunis",36.81,10.18),("Tripoli",32.89,13.19),
        ("Fez",34.03,-4.98),("Sokoto",13.06,5.24),("Kumasi",6.69,-1.62),("Abomey",7.18,1.99),("Muscat",23.59,58.41),
        ("Diriyah",24.73,46.57),("Bukhara",39.77,64.42),("Khiva",41.38,60.36),("Antananarivo",-18.88,47.51),("Batavia",-6.13,106.81),
        ("Manila",14.60,120.98)],
 1880: [("London",51.51,-0.13),("Paris",48.86,2.35),("Madrid",40.42,-3.70),("Lisbon",38.72,-9.14),("Vienna",48.21,16.37),
        ("Berlin",52.52,13.40),("St. Petersburg",59.94,30.31),("Istanbul",41.01,28.98),("Stockholm",59.33,18.07),("Oslo",59.91,10.75),
        ("Copenhagen",55.68,12.57),("Rome",41.90,12.50),("Amsterdam",52.37,4.90),("Brussels",50.85,4.35),("Bern",46.95,7.45),
        ("Athens",37.98,23.73),("Belgrade",44.79,20.45),("Bucharest",44.43,26.10),("Cetinje",42.39,18.92),("Sofia",42.70,23.32),
        ("Tehran",35.69,51.39),("Kabul",34.53,69.17),("Bukhara",39.77,64.42),("Khiva",41.38,60.36),("Calcutta",22.57,88.36),
        ("Kathmandu",27.71,85.32),("Mandalay",21.97,96.08),("Bangkok",13.75,100.50),("Hue",16.46,107.59),("Beijing",39.90,116.40),
        ("Seoul",37.57,126.98),("Tokyo",35.68,139.69),("Washington",38.90,-77.04),("Ottawa",45.42,-75.70),("Mexico City",19.43,-99.13),
        ("Guatemala City",14.63,-90.51),("Tegucigalpa",14.07,-87.19),("San Salvador",13.69,-89.19),("Managua",12.11,-86.24),
        ("San José",9.93,-84.08),("Havana",23.11,-82.37),("Port-au-Prince",18.54,-72.34),("Santo Domingo",18.49,-69.93),
        ("Caracas",10.49,-66.88),("Bogotá",4.71,-74.07),("Quito",-0.18,-78.47),("Lima",-12.05,-77.04),("Sucre",-19.03,-65.26),
        ("Santiago",-33.45,-70.67),("Buenos Aires",-34.60,-58.38),("Montevideo",-34.90,-56.16),("Asunción",-25.26,-57.58),
        ("Rio de Janeiro",-22.91,-43.17),("Cairo",30.04,31.24),("Khartoum",15.50,32.56),("Tunis",36.81,10.18),("Algiers",36.75,3.06),
        ("Fez",34.03,-4.98),("Tripoli",32.89,13.19),("Zanzibar City",-6.16,39.19),("Cape Town",-33.92,18.42),("Pretoria",-25.75,28.19),
        ("Bloemfontein",-29.12,26.21),("Pietermaritzburg",-29.60,30.38),("Antananarivo",-18.88,47.51),("Kumasi",6.69,-1.62),
        ("Monrovia",6.30,-10.80),("Freetown",8.48,-13.23),("Wellington",-41.29,174.78),("Honolulu",21.31,-157.86),
        ("Batavia",-6.13,106.81),("Manila",14.60,120.98),("Muscat",23.59,58.41)],
}

def load(path):
    raw = lzma.open(path).read() if path.endswith(".xz") else open(path, "rb").read()
    d = json.loads(raw)
    return [g["properties"] for g in list(d["objects"].values())[0]["geometries"]]

def capitals_at(P, date):
    out, seen = [], set()
    for p in P:
        if not (p["start"] <= date <= p["end"]) or p["country_name"] in SKIP: continue
        name, lat, lon = CLEAN.get(p["capname"], p["capname"]), p["caplat"], p["caplong"]
        for a, b, n, la, lo in FIX.get(p["country_name"], []):
            if a <= date < b: name, lat, lon = n, la, lo
        if not name or name in seen: continue
        seen.add(name); out.append([round(lat, 2), round(lon, 2), name])
    return out

if __name__ == "__main__":
    P = load(sys.argv[1] if len(sys.argv) > 1 else "cshapes_2_gw.topojson.xz")
    caps = {str(y): [[la, lo, n] for n, la, lo in v] for y, v in EARLY.items()}
    for y, date in DATES.items(): caps[str(y)] = capitals_at(P, date)
    os.makedirs("data", exist_ok=True)
    with open("data/capitals.js", "w") as fh: fh.write("window.CAPS=" + json.dumps(caps, ensure_ascii=False, separators=(",", ":")) + ";")
    for y in sorted(caps, key=int): print(y, len(caps[y]), "capitals")
