"""Film Checker — Oscar & Palme d'Or tracker, single-file edition."""

import os, sqlite3, re
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, BaseLoader

DB_PATH = Path(os.getenv("DB_PATH", "/data/films.db"))

# ── Helpers ──────────────────────────────────────────────────────────
def _column_exists(c, col):
    cols = [r[1] for r in c.execute("PRAGMA table_info(films)").fetchall()]
    return col in cols


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS films (
        annee INTEGER PRIMARY KEY, oscar TEXT NOT NULL DEFAULT '',
        palme TEXT NOT NULL DEFAULT '', realisateur TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS votes (
        annee INTEGER NOT NULL, personne TEXT NOT NULL CHECK(personne IN ('seb','paul')),
        film_type TEXT NOT NULL CHECK(film_type IN ('oscar','palme')),
        sub_idx INTEGER NOT NULL DEFAULT 0, vu INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (annee, personne, film_type, sub_idx)
    )""")
    # Migrations for new columns
    if not _column_exists(c, "synopsis"):
        c.execute("ALTER TABLE films ADD COLUMN synopsis TEXT NOT NULL DEFAULT ''")
    if not _column_exists(c, "pays"):
        c.execute("ALTER TABLE films ADD COLUMN pays TEXT NOT NULL DEFAULT ''")
    if not _column_exists(c, "fetch_status"):
        c.execute("ALTER TABLE films ADD COLUMN fetch_status TEXT NOT NULL DEFAULT ''")
    if c.execute("SELECT COUNT(*) FROM films").fetchone()[0] == 0:
        _seed(c)
    c.commit()
    return c


def _seed(c):
    films = [
        (1929, "Les Ailes", "", "", ""),
        (1930, "Broadway Melody", "", "", ""),
        (1931, "La Ruée vers l'Ouest", "", "", ""),
        (1932, "Grand Hotel", "", "", ""),
        (1934, "Cavalcade", "", "", ""),
        (1935, "New York-Miami", "", "", ""),
        (1936, "Les Révoltés du Bounty", "", "", ""),
        (1937, "Le Grand Ziegfeld", "", "", ""),
        (1938, "La Vie d'Émile Zola", "", "", ""),
        (1939, "Vous ne l'emporterez pas avec vous", "Pacific Express", "Cecil B. DeMille", ""),
        (1940, "Autant en emporte le vent", "", "", ""),
        (1941, "Rebecca", "", "", ""),
        (1942, "Qu'elle était verte ma vallée", "", "", ""),
        (1943, "Madame Miniver", "", "", ""),
        (1944, "Casablanca", "", "", ""),
        (1945, "La Route semée d'étoiles", "", "", ""),
        (1946, "Le Poison", "", "", ""),
        (1947, "Les Plus Belles Années de notre vie", "", "", ""),
        (1948, "Le Mur invisible", "", "", ""),
        (1949, "Hamlet", "Le Troisième Homme", "Carol Reed", ""),
        (1950, "Les Fous du roi", "", "", "Pas de festival cette année-là"),
        (1951, "Ève", "Mademoiselle Julie / Miracle à Milan", "Alf Sjöberg / Vittorio De Sica", ""),
        (1952, "Un Américain à Paris", "Othello / Deux Sous d'espoir", "Orson Welles / Renato Castellani", ""),
        (1953, "Sous le plus grand chapiteau du monde", "Le Salaire de la peur", "Henri-Georges Clouzot", ""),
        (1954, "Tant qu'il y aura des hommes", "La Porte de l'enfer", "Teinosuke Kinugasa", ""),
        (1955, "Sur les quais", "Marty", "Delbert Mann", ""),
        (1956, "Marty", "Le Monde du silence", "Jacques-Yves Cousteau et Louis Malle", ""),
        (1957, "Le Tour du monde en quatre-vingts jours", "La Loi du Seigneur", "William Wyler", ""),
        (1958, "Le Pont de la rivière Kwaï", "Quand passent les cigognes", "Mikhaïl Kalatozov", ""),
        (1959, "Gigi", "Orfeu Negro", "Marcel Camus", ""),
        (1960, "Ben-Hur", "La dolce vita", "Federico Fellini", ""),
        (1961, "La Garçonnière", "Une aussi longue absence / Viridiana", "Henri Colpi / Luis Buñuel", ""),
        (1962, "West Side Story", "La Parole donnée", "Anselmo Duarte", ""),
        (1963, "Lawrence d'Arabie", "Le Guépard", "Luchino Visconti", ""),
        (1964, "Tom Jones", "Les Parapluies de Cherbourg", "Jacques Demy", ""),
        (1965, "My Fair Lady", "Le Knack... et comment l'avoir", "Richard Lester", ""),
        (1966, "La Mélodie du bonheur", "Un homme et une femme / Ces messieurs dames", "Claude Lelouch / Pietro Germi", ""),
        (1967, "Un homme pour l'éternité", "Blow-Up", "Michelangelo Antonioni", ""),
        (1968, "Dans la chaleur de la nuit", "", "", "Festival interrompu (mai 68)"),
        (1969, "Oliver !", "If....", "Lindsay Anderson", ""),
        (1970, "Macadam Cowboy", "MASH", "Robert Altman", ""),
        (1971, "Patton", "Le Messager", "Joseph Losey", ""),
        (1972, "French Connection", "La classe ouvrière va au paradis / L'Affaire Mattei", "Elio Petri / Francesco Rosi", ""),
        (1973, "Le Parrain", "La Méprise / L'Épouvantail", "Alan Bridges / Jerry Schatzberg", ""),
        (1974, "L'Arnaque", "Conversation secrète", "Francis Ford Coppola", ""),
        (1975, "Le Parrain, 2e partie", "Chronique des années de braise", "Mohammed Lakhdar-Hamina", ""),
        (1976, "Vol au-dessus d'un nid de coucou", "Taxi Driver", "Martin Scorsese", ""),
        (1977, "Rocky", "Padre padrone", "Paolo et Vittorio Taviani", ""),
        (1978, "Annie Hall", "L'Arbre aux sabots", "Ermanno Olmi", ""),
        (1979, "Voyage au bout de l'enfer", "Apocalypse Now / Le Tambour", "Francis Ford Coppola / Volker Schlöndorff", ""),
        (1980, "Kramer contre Kramer", "Que le spectacle commence / Kagemusha, l'Ombre du guerrier", "Bob Fosse / Akira Kurosawa", ""),
        (1981, "Des gens comme les autres", "L'Homme de fer", "Andrzej Wajda", ""),
        (1982, "Les Chariots de feu", "Missing / Yol, la permission", "Costa-Gavras / Yılmaz Güney et Şerif Gören", ""),
        (1983, "Gandhi", "La Ballade de Narayama", "Shōhei Imamura", ""),
        (1984, "Tendres Passions", "Paris, Texas", "Wim Wenders", ""),
        (1985, "Amadeus", "Papa est en voyage d'affaires", "Emir Kusturica", ""),
        (1986, "Out of Africa", "Mission", "Roland Joffé", ""),
        (1987, "Platoon", "Sous le soleil de Satan", "Maurice Pialat", ""),
        (1988, "Le Dernier Empereur", "Pelle le Conquérant", "Bille August", ""),
        (1989, "Rain Man", "Sexe, Mensonges et Vidéo", "Steven Soderbergh", ""),
        (1990, "Miss Daisy et son chauffeur", "Sailor et Lula", "David Lynch", ""),
        (1991, "Danse avec les loups", "Barton Fink", "Joel Coen", ""),
        (1992, "Le Silence des agneaux", "Les Meilleures Intentions", "Bille August", ""),
        (1993, "Impitoyable", "Adieu ma concubine / La Leçon de piano", "Chen Kaige / Jane Campion", ""),
        (1994, "La Liste de Schindler", "Pulp Fiction", "Quentin Tarantino", ""),
        (1995, "Forrest Gump", "Underground", "Emir Kusturica", ""),
        (1996, "Braveheart", "Secrets et Mensonges", "Mike Leigh", ""),
        (1997, "Le Patient anglais", "Le Goût de la cerise / L'Anguille", "Abbas Kiarostami / Shōhei Imamura", ""),
        (1998, "Titanic", "L'Éternité et Un Jour", "Theo Angelopoulos", ""),
        (1999, "Shakespeare in Love", "Rosetta", "Luc et Jean-Pierre Dardenne", ""),
        (2000, "American Beauty", "Dancer in the Dark", "Lars von Trier", ""),
        (2001, "Gladiator", "La Chambre du fils", "Nanni Moretti", ""),
        (2002, "Un homme d'exception", "Le Pianiste", "Roman Polanski", ""),
        (2003, "Chicago", "Elephant", "Gus Van Sant", ""),
        (2004, "Le Seigneur des anneaux : Le Retour du roi", "Fahrenheit 9/11", "Michael Moore", ""),
        (2005, "Million Dollar Baby", "L'Enfant", "Luc et Jean-Pierre Dardenne", ""),
        (2006, "Collision", "Le vent se lève", "Ken Loach", ""),
        (2007, "Les Infiltrés", "Quatre mois, trois semaines, deux jours", "Cristian Mungiu", ""),
        (2008, "No Country for Old Men", "Entre les murs", "Laurent Cantet", ""),
        (2009, "Slumdog Millionaire", "Le Ruban blanc", "Michael Haneke", ""),
        (2010, "Démineurs", "Oncle Boonmee, celui qui se souvient de ses vies antérieures", "Apichatpong Weerasethakul", ""),
        (2011, "Le Discours d'un roi", "The Tree of Life", "Terrence Malick", ""),
        (2012, "The Artist", "Amour", "Michael Haneke", ""),
        (2013, "Argo", "La Vie d'Adèle", "Abdellatif Kechiche", ""),
        (2014, "Twelve Years a Slave", "Winter Sleep", "Nuri Bilge Ceylan", ""),
        (2015, "Birdman", "Dheepan", "Jacques Audiard", ""),
        (2016, "Spotlight", "Moi, Daniel Blake", "Ken Loach", ""),
        (2017, "Moonlight", "The Square", "Ruben Östlund", ""),
        (2018, "La Forme de l'eau", "Une affaire de famille / Le Livre d'image", "Hirokazu Kore-eda / Jean-Luc Godard", ""),
        (2019, "Green Book", "Parasite", "Bong Joon-ho", ""),
        (2020, "Parasite", "", "", "Pas de festival (Covid-19)"),
        (2021, "Nomadland", "Titane", "Julia Ducournau", ""),
        (2022, "Coda", "Sans filtre", "Ruben Östlund", ""),
        (2023, "Everything Everywhere All at Once", "Anatomie d'une chute", "Justine Triet", ""),
        (2024, "Oppenheimer", "Anora", "Sean Baker", ""),
        (2025, "Anora", "Un simple accident", "Jafar Panahi", ""),
        (2026, "Une bataille après l'autre", "Fjord", "Cristian Mungiu", ""),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO films (annee, oscar, palme, realisateur, notes) VALUES (?,?,?,?,?)",
        films,
    )


# ── Wikipedia data fetching ──────────────────────────────────────────
import httpx

WIKI_UA = "FilmChecker/1.0 (https://films.alaloupe.fr; bot@example.com)"
WIKI_API = "https://{lang}.wikipedia.org/w/api.php"


def _wiki_query(params, lang="en"):
    """Call the Wikipedia action API."""
    params["format"] = "json"
    try:
        resp = httpx.get(
            WIKI_API.format(lang=lang),
            params=params,
            headers={"User-Agent": WIKI_UA},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _search_wiki(title, lang="en"):
    """Search for a Wikipedia page and get its summary extract.
    Tries the exact title, then with (film) suffix, and skips disambiguation pages.
    """
    candidates = [
        title + " (film)",
        title + " (Film)",
        title,
    ]

    for q in candidates:
        data = _wiki_query(
            {
                "action": "query",
                "titles": q,
                "prop": "extracts|pageprops",
                "exintro": True,
                "explaintext": True,
                "redirects": 1,
                "exchars": 600,
            },
            lang,
        )
        if data is None:
            continue
        pages = data.get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if pid == "-1":
                continue
            extract = page.get("extract", "")
            if not extract:
                continue
            # Skip disambiguation pages
            pageprops = page.get("pageprops", {})
            if pageprops.get("disambiguation"):
                continue
            # Skip if extract looks like a disambiguation
            extract_lower = extract.lower()
            if "peut faire référence" in extract_lower or "peut désigner" in extract_lower or "may refer to" in extract_lower:
                if len(extract) < 200:
                    # Try with (film) suffix if we haven't already
                    if q == title:
                        continue
                    continue
            return {
                "title": page.get("title", q),
                "extract": extract,
                "pageid": pid,
            }

    return None


def _fetch_infobox(title, lang="en"):
    """Extract director and country from Wikipedia page infobox."""
    data = _wiki_query(
        {
            "action": "parse",
            "page": title,
            "prop": "text",
            "section": 0,
        },
        lang,
    )
    if not data:
        return {"director": "", "country": ""}

    html = data.get("parse", {}).get("text", {}).get("*", "")
    if not html:
        return {"director": "", "country": ""}

    director = ""
    country = ""

    # Try various patterns for director
    for pattern in [
        r'(?:[Dd]irector|R[ée]alis[ée]\s*(?:par|ateu[rt]|rice)?)\s*</th>\s*<td[^>]*>(.*?)</td>',
        r'(?:[Dd]irected by)\s*</th>\s*<td[^>]*>(.*?)</td>',
    ]:
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if m:
            text = re.sub(r'<[^>]+>', "", m.group(1)).strip()
            # Clean up multiple names
            text = text.split("\n")[0].strip()
            text = re.sub(r'\s*\(.*?\)', "", text).strip()
            text = re.sub(r'&#\d+;', "", text).strip()
            text = re.sub(r'\[\d+\]', "", text).strip()
            if text and not text.startswith("{{"):
                director = text
                break

    # Try various patterns for country
    for pattern in [
        r'(?:[Cc]ountry|Pays|Origine|[Cc]ountries)\s*</th>\s*<td[^>]*>(.*?)</td>',
        r'(?:Country of origin)\s*</th>\s*<td[^>]*>(.*?)</td>',
    ]:
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if m:
            text = re.sub(r'<[^>]+>', "", m.group(1)).strip()
            text = text.split("\n")[0].strip()
            text = re.sub(r'\s*\(.*?\)', "", text).strip()
            # Clean HTML entities and sup tags
            text = re.sub(r'&#\d+;', "", text).strip()
            text = re.sub(r'\[\d+\]', "", text).strip()
            if text and not text.startswith("{{"):
                country = text
                break

    return {"director": director, "country": country}


def fetch_film_metadata(title_fr, title_en=None):
    """Fetch director, synopsis, country for a film using Wikipedia."""
    data = {"synopsis": "", "director": "", "country": "", "status": ""}

    # Try French Wikipedia first (titles are in French)
    fr_result = _search_wiki(title_fr, "fr")
    if fr_result and fr_result.get("extract"):
        data["synopsis"] = fr_result["extract"][:500]
        data["status"] = "fr"
        page_title = fr_result.get("title", title_fr)
        info = _fetch_infobox(page_title, "fr")
        if info.get("director"):
            data["director"] = info["director"]
        if info.get("country"):
            data["country"] = info["country"]

    # Try English Wikipedia for any missing data
    en_title = title_en or title_fr
    en_result = _search_wiki(en_title, "en")
    if en_result and en_result.get("extract"):
        if not data["synopsis"]:
            data["synopsis"] = en_result["extract"][:500]
            data["status"] = "en"
        if not data["director"] or not data["country"]:
            page_title = en_result.get("title", en_title)
            info = _fetch_infobox(page_title, "en")
            if not data["director"] and info.get("director"):
                data["director"] = info["director"]
            if not data["country"] and info.get("country"):
                data["country"] = info["country"]
        if not data["status"]:
            data["status"] = "en"

    if not data["status"]:
        data["status"] = "not_found"
    else:
        data["status"] = "ok"

    return data


# ── Jinja template (inline) ──────────────────────────────────────────
TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Film Checker — Oscar &amp; Palme</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0f0f14;--card:#1a1a24;--border:#2a2a3a;--text:#e8e8f0;--muted:#8888a0;--accent-oscar:#f5c542;--accent-palme:#4ade80;--accent-seb:#60a5fa;--accent-paul:#f472b6;--toast-bg:#1e293b;--toast-border:#334155}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding:1rem}
.container{max-width:1200px;margin:0 auto}
header{text-align:center;padding:2rem 1rem 1.5rem}
h1{font-size:1.6rem;font-weight:700}
h1 .dim{opacity:.7}
.subtitle{color:var(--muted);font-size:.9rem;margin-top:.3rem}
.tabs{display:flex;gap:.5rem;justify-content:center;margin-bottom:1.5rem}
.tabs a{display:inline-flex;align-items:center;gap:.4rem;padding:.6rem 1.6rem;border-radius:999px;text-decoration:none;font-weight:600;font-size:.95rem;transition:all .2s;border:2px solid transparent}
.tabs a.seb{color:var(--accent-seb);border-color:var(--accent-seb);background:transparent}
.tabs a.seb.active{background:var(--accent-seb);color:#000}
.tabs a.paul{color:var(--accent-paul);border-color:var(--accent-paul);background:transparent}
.tabs a.paul.active{background:var(--accent-paul);color:#000}
.stats-bar{display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap;margin-bottom:1.5rem;font-size:.85rem;color:var(--muted)}
.stats-bar .stat{background:var(--card);padding:.3rem .8rem;border-radius:6px}
.stats-bar .num{font-weight:700;color:var(--text)}
.filter-bar{display:flex;align-items:center;justify-content:center;gap:.6rem;flex-wrap:wrap;margin-bottom:1rem}
.filter-bar label{font-size:.85rem;color:var(--muted)}
.filter-bar select,.filter-bar input{background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:.35rem .6rem;font-size:.85rem}
.filter-bar input{min-width:180px}
.filter-bar input::placeholder{color:var(--muted);opacity:.6}
.table-wrap{overflow-x:auto;border-radius:12px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:.82rem}
thead th{background:#12121c;padding:.5rem .35rem;text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);border-bottom:2px solid var(--border);white-space:nowrap;position:sticky;top:0;cursor:pointer;-webkit-user-select:none;user-select:none}
thead th:hover{color:var(--text)}
thead th .sort-dir{display:inline-block;margin-left:3px;font-size:.65rem;opacity:.5}
tbody tr{border-bottom:1px solid var(--border);transition:background .15s}
tbody tr:hover{background:rgba(255,255,255,.03)}
tbody tr td{padding:.4rem .35rem;vertical-align:middle}
td.year{font-weight:600;width:45px;text-align:center;white-space:nowrap}
.badge{display:inline-block;font-size:.6rem;font-weight:700;padding:.15rem .4rem;border-radius:4px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap}
.badge.oscar{background:rgba(245,197,66,.15);color:var(--accent-oscar)}
.badge.palme{background:rgba(74,222,128,.15);color:var(--accent-palme)}
td.title{max-width:200px}
td.title .main{font-weight:500}
td.director{max-width:140px;font-size:.78rem;color:var(--text)}
td.country{max-width:100px;font-size:.78rem;color:var(--muted)}
td.synopsis{max-width:220px;font-size:.75rem;color:var(--muted);line-height:1.3}
td.synopsis .trunc{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
td.synopsis .full{display:none}
td.notes-cell{font-size:.72rem;color:var(--muted);font-style:italic;max-width:100px}
td.check{text-align:center;width:44px}
.check-wrap{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:6px;cursor:pointer;transition:all .15s;border:2px solid var(--border);background:transparent;font-size:.9rem}
.check-wrap.checked{border-color:currentColor}
.check-wrap.checked.seb{background:rgba(96,165,250,.15);color:var(--accent-seb);border-color:var(--accent-seb)}
.check-wrap.checked.paul{background:rgba(244,114,182,.15);color:var(--accent-paul);border-color:var(--accent-paul)}
.check-wrap input{display:none}
.fetch-btn{font-size:.65rem;padding:.15rem .5rem;border-radius:4px;border:1px solid var(--border);background:var(--card);color:var(--muted);cursor:pointer;transition:all .15s}
.fetch-btn:hover{color:var(--text);border-color:var(--accent-oscar)}
/* Toast */
#toast-container{position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;pointer-events:none}
.toast{background:var(--toast-bg);border:1px solid var(--toast-border);border-radius:10px;padding:.6rem 1rem .6rem .8rem;box-shadow:0 8px 24px rgba(0,0,0,.4);font-size:.85rem;display:flex;align-items:center;gap:.5rem;animation:toastIn .25s ease forwards;pointer-events:auto;max-width:320px}
.toast.out{animation:toastOut .25s ease forwards}
.toast .toast-icon{font-size:1rem;flex-shrink:0}
.toast .toast-msg{flex:1}
@keyframes toastIn{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}
@keyframes toastOut{from{opacity:1;transform:translateX(0)}to{opacity:0;transform:translateX(40px)}}
footer{text-align:center;padding:2rem 1rem;font-size:.8rem;color:var(--muted)}
footer a{color:var(--accent-oscar);text-decoration:none}
/* Responsive */
@media(max-width:900px){td.synopsis{display:none}th.synopsis-h{display:none}}
@media(max-width:700px){table{font-size:.76rem}td.title{max-width:140px}td.director{max-width:100px}td.country{max-width:70px}td.year{width:32px}td.check{width:36px}.filter-bar input{min-width:130px}h1{font-size:1.1rem}}
/* Loading spinner for fetch */
.spinner{display:inline-block;width:12px;height:12px;border:2px solid var(--muted);border-top-color:var(--accent-oscar);border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="container">
<header><h1><span class="dim">Oscar</span> · <span class="dim">Palme</span> Checker</h1><p class="subtitle">Cochez les films que vous avez deja vus</p></header>
<div class="tabs">
<a href="/?p=seb" class="seb {{ 'active' if person == 'seb' else '' }}">Sebastien</a>
<a href="/?p=paul" class="paul {{ 'active' if person == 'paul' else '' }}">Paul</a>
</div>
<div class="stats-bar" id="stats-bar">
<span class="stat">Oscar vus: <span class="num" id="oscar-count">0</span></span>
<span class="stat">Palme vues: <span class="num" id="palme-count">0</span></span>
<span class="stat">Total: <span class="num" id="total-count">0</span></span>
</div>
<div class="filter-bar">
<label for="s">Rechercher:</label>
<input type="text" id="s" placeholder="Titre, realisateur, synopsis, pays..." oninput="searchTable(this.value)">
<label for="f">Filtrer:</label>
<select id="f" onchange="filterTable(this.value)">
<option value="all">Tous</option>
<option value="vu">Vus</option>
<option value="pasvu">Pas encore vus</option>
<option value="oscar">Oscars seulement</option>
<option value="palme">Palmes seulement</option>
</select>
</div>
<div class="table-wrap"><table><thead><tr>
<th onclick="sortTable('annee')">Annee<span class="sort-dir" id="sd-annee"></span></th>
<th>Type</th>
<th onclick="sortTable('title')">Film<span class="sort-dir" id="sd-title"></span></th>
<th onclick="sortTable('director')">Realisateur<span class="sort-dir" id="sd-director"></span></th>
<th class="synopsis-h" onclick="sortTable('synopsis')">Synopsis<span class="sort-dir" id="sd-synopsis"></span></th>
<th onclick="sortTable('country')">Pays<span class="sort-dir" id="sd-country"></span></th>
<th>Notes</th>
<th title="Vu ?">Vu</th>
</tr></thead><tbody>
{% for f in films %}
<tr class="film-row" data-type="{{ f.type }}" data-vu="{{ '1' if f.vu else '0' }}" data-annee="{{ f.annee }}" data-title="{{ f.titre|lower }}" data-director="{{ f.realisateur|lower }}" data-synopsis="{{ f.synopsis|lower }}" data-country="{{ f.pays|lower }}">
<td class="year">{{ f.annee }}</td>
<td><span class="badge {{ f.type }}">{{ 'Oscar' if f.type == 'oscar' else 'Palme' }}</span></td>
<td class="title"><span class="main">{{ f.titre }}</span></td>
<td class="director">{% if f.realisateur %}{{ f.realisateur }}{% else %}<span style="color:var(--muted);font-size:.7rem">—</span>{% endif %}</td>
<td class="synopsis"><span class="trunc">{% if f.synopsis %}{{ f.synopsis }}{% else %}<span style="color:var(--muted);font-size:.7rem">—</span>{% endif %}</span></td>
<td class="country">{% if f.pays %}{{ f.pays }}{% else %}<span style="color:var(--muted);font-size:.7rem">—</span>{% endif %}</td>
<td class="notes-cell">{% if f.type == 'palme' and not f.notes %}{% if f.annee == 1950 %}Pas de festival{% elif f.annee == 1968 %}Annule (Mai 68){% elif f.annee == 2020 %}Annule (Covid){% else %}—{% endif %}{% else %}{{ f.notes if f.notes else '—' }}{% endif %}</td>
<td class="check"><label class="check-wrap{{ ' checked' if f.vu else '' }} {{ person }}" onclick="toggle({{ f.annee }},'{{ f.type }}',{{ f.sub_idx }},'{{ person }}',this)"><input type="checkbox"{{ ' checked' if f.vu else '' }}>{% if f.vu %}&#10003;{% endif %}</label></td>
</tr>
{% endfor %}
</tbody></table></div>
<div style="text-align:center;margin-top:1rem">
<button class="fetch-btn" onclick="fetchAllMetadata()" id="fetch-all-btn">Mettre a jour les metadonnees (Wikipedia)</button>
<span id="fetch-status" style="font-size:.78rem;color:var(--muted);margin-left:.5rem"></span>
</div>
<footer><a href="https://docs.google.com/spreadsheets/d/1ixMU8HQCyMXFwO4-Rn5UBqZLGi1CavtnwT2uNWob9Pc/edit" target="_blank">Voir le Google Sheet original</a></footer>
</div>
<div id="toast-container"></div>
<script>
// ── Toast system ──
function showToast(msg, icon) {
    var c = document.getElementById('toast-container');
    var t = document.createElement('div');
    t.className = 'toast';
    t.innerHTML = '<span class="toast-icon">' + (icon || '&#10003;') + '</span><span class="toast-msg">' + msg + '</span>';
    c.appendChild(t);
    setTimeout(function(){ t.classList.add('out'); setTimeout(function(){ if(t.parentNode) t.parentNode.removeChild(t); }, 280); }, 2200);
}

// ── Toggle watched ──
async function toggle(a, t, s, p, el) {
    var inp = el.querySelector('input');
    var wasChecked = inp.checked;
    var v = wasChecked ? 0 : 1;
    try {
        var r = await fetch('/vote', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({annee: a, film_type: t, sub_idx: s, personne: p, vu: v})
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);
    } catch(e) {
        console.error(e);
        showToast('Erreur lors de la mise a jour', '&#9888;');
        return;
    }
    inp.checked = v === 1;
    el.classList.toggle('checked', v === 1);
    el.innerHTML = '<input type="checkbox"' + (inp.checked ? ' checked' : '') + '>' + (v ? '&#10003;' : '');
    var row = el.closest('.film-row');
    if (row) row.dataset.vu = v;
    updateStats();
    var typeLabel = t === 'oscar' ? 'Oscar' : 'Palme';
    showToast((v ? 'Vu : ' : 'Pas vu : ') + typeLabel + ' ' + a, v ? '&#10003;' : '&#10007;');
}

// ── Search ──
function searchTable(q) {
    q = q.toLowerCase().trim();
    document.querySelectorAll('.film-row').forEach(function(r) {
        var match = !q ||
            r.dataset.title.indexOf(q) !== -1 ||
            r.dataset.director.indexOf(q) !== -1 ||
            r.dataset.synopsis.indexOf(q) !== -1 ||
            r.dataset.country.indexOf(q) !== -1 ||
            r.dataset.annee.indexOf(q) !== -1;
        // Also check current filter
        var f = document.getElementById('f').value;
        var typeOk = true;
        if (f === 'vu') typeOk = r.dataset.vu === '1';
        else if (f === 'pasvu') typeOk = r.dataset.vu === '0';
        else if (f === 'oscar') typeOk = r.dataset.type === 'oscar';
        else if (f === 'palme') typeOk = r.dataset.type === 'palme';
        r.style.display = (match && typeOk) ? '' : 'none';
    });
}

// ── Filter ──
function filterTable(v) {
    var q = document.getElementById('s').value;
    searchTable(q);
}

// ── Sort ──
var sortState = {col: '', dir: 1};
function sortTable(col) {
    if (sortState.col === col) sortState.dir *= -1;
    else { sortState.col = col; sortState.dir = 1; }
    // Update header indicators
    document.querySelectorAll('.sort-dir').forEach(function(s) { s.textContent = ''; });
    var ind = document.getElementById('sd-' + col);
    if (ind) ind.textContent = sortState.dir > 0 ? '▲' : '▼';

    var tbody = document.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('.film-row'));
    rows.sort(function(a, b) {
        var va, vb;
        if (col === 'annee') {
            va = parseInt(a.dataset.annee);
            vb = parseInt(b.dataset.annee);
        } else if (col === 'title') {
            va = a.dataset.title;
            vb = b.dataset.title;
        } else if (col === 'director') {
            va = a.dataset.director;
            vb = b.dataset.director;
        } else if (col === 'synopsis') {
            va = a.dataset.synopsis;
            vb = b.dataset.synopsis;
        } else if (col === 'country') {
            va = a.dataset.country;
            vb = b.dataset.country;
        }
        if (va < vb) return -1 * sortState.dir;
        if (va > vb) return 1 * sortState.dir;
        return 0;
    });
    rows.forEach(function(r) { tbody.appendChild(r); });
}

// ── Stats ──
async function updateStats() {
    try {
        var r = await fetch('/api/stats');
        if (!r.ok) return;
        var s = await r.json();
        var p = '{{ person }}';
        var o = 0, l = 0;
        s.forEach(function(x) {
            if (x.personne !== p) return;
            if (x.film_type === 'oscar') o = x.n;
            if (x.film_type === 'palme') l = x.n;
        });
        document.getElementById('oscar-count').textContent = o;
        document.getElementById('palme-count').textContent = l;
        document.getElementById('total-count').textContent = o + l;
    } catch(e) {}
}

// ── Fetch metadata from Wikipedia ──
async function fetchAllMetadata() {
    var btn = document.getElementById('fetch-all-btn');
    var status = document.getElementById('fetch-status');
    btn.disabled = true;
    btn.textContent = 'Recherche en cours...';
    status.textContent = '';

    // Get years that need fetching
    try {
        var r = await fetch('/api/missing-metadata');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        var years = await r.json();
        if (years.length === 0) {
            status.textContent = 'Toutes les donnees sont deja completes.';
            btn.disabled = false;
            btn.textContent = 'Mettre a jour les metadonnees (Wikipedia)';
            return;
        }
        var total = years.length;
        var done = 0;
        for (var y of years) {
            status.textContent = done + '/' + total + ' annees traitees...';
            try {
                await fetch('/api/fetch-metadata/' + y, {method: 'POST'});
                done++;
            } catch(e) { console.error('Failed for', y); }
            // Small delay to be nice to Wikipedia API
            if (done < total) await new Promise(r => setTimeout(r, 800));
        }
        status.textContent = 'Termine ! ' + done + '/' + total + ' annees mises a jour.';
        showToast(done + ' annee(s) mises a jour depuis Wikipedia', '&#9733;');
        // Reload page to show new data
        setTimeout(function() { location.reload(); }, 1500);
    } catch(e) {
        status.textContent = 'Erreur: ' + e.message;
        showToast('Erreur lors de la recuperation', '&#9888;');
    }
    btn.disabled = false;
    btn.textContent = 'Mettre a jour les metadonnees (Wikipedia)';
}

updateStats();
</script>
</body>
</html>"""

jinja = Environment(loader=BaseLoader())
jinja_template = jinja.from_string(TEMPLATE)

# ── FastAPI ─────────────────────────────────────────────────────────────
app = FastAPI(title="Film Checker")


@app.on_event("startup")
async def startup():
    db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    person = request.query_params.get("p", "seb")
    if person not in ("seb", "paul"):
        person = "seb"
    conn = db()
    cur = conn.execute("SELECT * FROM films ORDER BY annee ASC")
    films = [dict(r) for r in cur.fetchall()]

    cur = conn.execute(
        "SELECT annee, film_type, sub_idx, vu FROM votes WHERE personne=?",
        (person,),
    )
    votes = {
        (r["annee"], r["film_type"], r["sub_idx"]): r["vu"] for r in cur.fetchall()
    }
    conn.close()

    expanded = []
    for f in films:
        real = f.get("realisateur", "")
        syn = f.get("synopsis", "")
        pays = f.get("pays", "")

        expanded.append({
            "annee": f["annee"],
            "titre": f["oscar"],
            "type": "oscar",
            "sub_idx": 0,
            "notes": f.get("notes", ""),
            "realisateur": real,
            "synopsis": syn,
            "pays": pays,
            "vu": votes.get((f["annee"], "oscar", 0), False),
        })
        if f.get("palme"):
            palme_titles = [x.strip() for x in f["palme"].split(" / ")]
            realisateurs = [x.strip() for x in real.split(" / ")] if real else []
            for i, p in enumerate(palme_titles):
                # Match director position or use the full field
                dir_for_palme = realisateurs[i] if i < len(realisateurs) else real
                expanded.append({
                    "annee": f["annee"],
                    "titre": p,
                    "type": "palme",
                    "sub_idx": i,
                    "notes": "",
                    "realisateur": dir_for_palme,
                    "synopsis": syn,
                    "pays": pays,
                    "vu": votes.get((f["annee"], "palme", i), False),
                })

    return jinja_template.render(
        films=expanded, person=person, other="paul" if person == "seb" else "seb"
    )


@app.post("/vote")
async def vote(
    annee: int = Form(...),
    film_type: str = Form(...),
    sub_idx: int = Form(0),
    personne: str = Form(...),
    vu: int = Form(0),
):
    conn = db()
    conn.execute(
        """INSERT INTO votes (annee, personne, film_type, sub_idx, vu)
           VALUES (?,?,?,?,?) ON CONFLICT(annee,personne,film_type,sub_idx)
           DO UPDATE SET vu=excluded.vu""",
        (annee, personne, film_type, sub_idx, vu),
    )
    conn.commit()
    conn.close()
    return JSONResponse({"ok": True})


@app.get("/api/stats")
async def stats():
    conn = db()
    cur = conn.execute(
        "SELECT personne, film_type, COUNT(*) as n FROM votes WHERE vu=1 GROUP BY personne, film_type"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return JSONResponse(rows)


@app.get("/api/missing-metadata")
async def missing_metadata():
    """Return list of years that are missing synopsis or country data."""
    conn = db()
    cur = conn.execute(
        """SELECT annee FROM films
           WHERE (synopsis = '' OR pays = '')
           AND fetch_status != 'not_found'
           ORDER BY annee ASC"""
    )
    years = [r["annee"] for r in cur.fetchall()]
    conn.close()
    return JSONResponse(years)


@app.post("/api/fetch-metadata/{annee}")
async def fetch_metadata(annee: int):
    """Fetch director, synopsis, country from Wikipedia for a given year."""
    conn = db()
    cur = conn.execute(
        "SELECT oscar, palme, realisateur, synopsis, pays FROM films WHERE annee=?",
        (annee,),
    )
    film = cur.fetchone()
    if not film:
        conn.close()
        return JSONResponse({"error": "Not found"}, status_code=404)

    data = dict(film)
    updated = {}

    # Try fetching for the Oscar film first
    if data["oscar"]:
        # Use French title for Wikipedia
        result = fetch_film_metadata(data["oscar"])
        if result["status"] == "ok":
            if not data["synopsis"] and result["synopsis"]:
                updated["synopsis"] = result["synopsis"]
            if not data["realisateur"] and result["director"]:
                updated["realisateur"] = result["director"]
            if not data["pays"] and result["country"]:
                updated["pays"] = result["country"]

    # Try fetching for the first Palme d'Or if no data yet
    if (not updated.get("synopsis") or not updated.get("pays")) and data["palme"]:
        palme_first = data["palme"].split(" / ")[0].strip()
        result = fetch_film_metadata(palme_first)
        if result["status"] == "ok":
            if not updated.get("synopsis") and result["synopsis"]:
                updated["synopsis"] = result["synopsis"]
            if not updated.get("realisateur") and result["director"]:
                updated["realisateur"] = result["director"]
            if not updated.get("pays") and result["country"]:
                updated["pays"] = result["country"]

    if updated:
        fields = ", ".join(f"{k}=?" for k in updated)
        values = list(updated.values())
        conn.execute(
            f"UPDATE films SET {fields}, fetch_status='ok' WHERE annee=?",
            (*values, annee),
        )
    else:
        conn.execute("UPDATE films SET fetch_status='not_found' WHERE annee=?", (annee,))

    conn.commit()
    conn.close()
    return JSONResponse({"annee": annee, "updated": updated})


@app.get("/health")
async def health():
    return {"status": "ok"}
