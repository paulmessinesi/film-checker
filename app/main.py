"""Film Checker — Oscar & Palme d'Or tracker, single-file edition."""

import os, sqlite3
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, BaseLoader

DB_PATH = Path(os.getenv("DB_PATH", "/data/films.db"))

# ── SQL ────────────────────────────────────────────────────────────────
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""
        CREATE TABLE IF NOT EXISTS films (
            annee INTEGER PRIMARY KEY, oscar TEXT NOT NULL DEFAULT '',
            palme TEXT NOT NULL DEFAULT '', realisateur TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            annee INTEGER NOT NULL, personne TEXT NOT NULL CHECK(personne IN ('seb','paul')),
            film_type TEXT NOT NULL CHECK(film_type IN ('oscar','palme')),
            sub_idx INTEGER NOT NULL DEFAULT 0, vu INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (annee, personne, film_type, sub_idx)
        )
    """)
    if c.execute("SELECT COUNT(*) FROM films").fetchone()[0] == 0:
        _seed(c)
    c.commit()
    return c

def _seed(c):
    films = [
        (1929,"Les Ailes","","",""),(1930,"Broadway Melody","","",""),
        (1931,"La Ruée vers l'Ouest","","",""),(1932,"Grand Hotel","","",""),
        (1934,"Cavalcade","","",""),(1935,"New York-Miami","","",""),
        (1936,"Les Révoltés du Bounty","","",""),(1937,"Le Grand Ziegfeld","","",""),
        (1938,"La Vie d'Émile Zola","","",""),
        (1939,"Vous ne l'emporterez pas avec vous","Pacific Express","Cecil B. DeMille",""),
        (1940,"Autant en emporte le vent","","",""),(1941,"Rebecca","","",""),
        (1942,"Qu'elle était verte ma vallée","","",""),(1943,"Madame Miniver","","",""),
        (1944,"Casablanca","","",""),(1945,"La Route semée d'étoiles","","",""),
        (1946,"Le Poison","","",""),(1947,"Les Plus Belles Années de notre vie","","",""),
        (1948,"Le Mur invisible","","",""),
        (1949,"Hamlet","Le Troisième Homme","Carol Reed",""),
        (1950,"Les Fous du roi","","","Pas de festival cette année-là"),
        (1951,"Ève","Mademoiselle Julie / Miracle à Milan","Alf Sjöberg / Vittorio De Sica",""),
        (1952,"Un Américain à Paris","Othello / Deux Sous d'espoir","Orson Welles / Renato Castellani",""),
        (1953,"Sous le plus grand chapiteau du monde","Le Salaire de la peur","Henri-Georges Clouzot",""),
        (1954,"Tant qu'il y aura des hommes","La Porte de l'enfer","Teinosuke Kinugasa",""),
        (1955,"Sur les quais","Marty","Delbert Mann",""),
        (1956,"Marty","Le Monde du silence","Jacques-Yves Cousteau et Louis Malle",""),
        (1957,"Le Tour du monde en quatre-vingts jours","La Loi du Seigneur","William Wyler",""),
        (1958,"Le Pont de la rivière Kwaï","Quand passent les cigognes","Mikhaïl Kalatozov",""),
        (1959,"Gigi","Orfeu Negro","Marcel Camus",""),
        (1960,"Ben-Hur","La dolce vita","Federico Fellini",""),
        (1961,"La Garçonnière","Une aussi longue absence / Viridiana","Henri Colpi / Luis Buñuel",""),
        (1962,"West Side Story","La Parole donnée","Anselmo Duarte",""),
        (1963,"Lawrence d'Arabie","Le Guépard","Luchino Visconti",""),
        (1964,"Tom Jones","Les Parapluies de Cherbourg","Jacques Demy",""),
        (1965,"My Fair Lady","Le Knack... et comment l'avoir","Richard Lester",""),
        (1966,"La Mélodie du bonheur","Un homme et une femme / Ces messieurs dames","Claude Lelouch / Pietro Germi",""),
        (1967,"Un homme pour l'éternité","Blow-Up","Michelangelo Antonioni",""),
        (1968,"Dans la chaleur de la nuit","","","Festival interrompu (mai 68)"),
        (1969,"Oliver !","If....","Lindsay Anderson",""),
        (1970,"Macadam Cowboy","MASH","Robert Altman",""),
        (1971,"Patton","Le Messager","Joseph Losey",""),
        (1972,"French Connection","La classe ouvrière va au paradis / L'Affaire Mattei","Elio Petri / Francesco Rosi",""),
        (1973,"Le Parrain","La Méprise / L'Épouvantail","Alan Bridges / Jerry Schatzberg",""),
        (1974,"L'Arnaque","Conversation secrète","Francis Ford Coppola",""),
        (1975,"Le Parrain, 2e partie","Chronique des années de braise","Mohammed Lakhdar-Hamina",""),
        (1976,"Vol au-dessus d'un nid de coucou","Taxi Driver","Martin Scorsese",""),
        (1977,"Rocky","Padre padrone","Paolo et Vittorio Taviani",""),
        (1978,"Annie Hall","L'Arbre aux sabots","Ermanno Olmi",""),
        (1979,"Voyage au bout de l'enfer","Apocalypse Now / Le Tambour","Francis Ford Coppola / Volker Schlöndorff",""),
        (1980,"Kramer contre Kramer","Que le spectacle commence / Kagemusha, l'Ombre du guerrier","Bob Fosse / Akira Kurosawa",""),
        (1981,"Des gens comme les autres","L'Homme de fer","Andrzej Wajda",""),
        (1982,"Les Chariots de feu","Missing / Yol, la permission","Costa-Gavras / Yılmaz Güney et Şerif Gören",""),
        (1983,"Gandhi","La Ballade de Narayama","Shōhei Imamura",""),
        (1984,"Tendres Passions","Paris, Texas","Wim Wenders",""),
        (1985,"Amadeus","Papa est en voyage d'affaires","Emir Kusturica",""),
        (1986,"Out of Africa","Mission","Roland Joffé",""),
        (1987,"Platoon","Sous le soleil de Satan","Maurice Pialat",""),
        (1988,"Le Dernier Empereur","Pelle le Conquérant","Bille August",""),
        (1989,"Rain Man","Sexe, Mensonges et Vidéo","Steven Soderbergh",""),
        (1990,"Miss Daisy et son chauffeur","Sailor et Lula","David Lynch",""),
        (1991,"Danse avec les loups","Barton Fink","Joel Coen",""),
        (1992,"Le Silence des agneaux","Les Meilleures Intentions","Bille August",""),
        (1993,"Impitoyable","Adieu ma concubine / La Leçon de piano","Chen Kaige / Jane Campion",""),
        (1994,"La Liste de Schindler","Pulp Fiction","Quentin Tarantino",""),
        (1995,"Forrest Gump","Underground","Emir Kusturica",""),
        (1996,"Braveheart","Secrets et Mensonges","Mike Leigh",""),
        (1997,"Le Patient anglais","Le Goût de la cerise / L'Anguille","Abbas Kiarostami / Shōhei Imamura",""),
        (1998,"Titanic","L'Éternité et Un Jour","Theo Angelopoulos",""),
        (1999,"Shakespeare in Love","Rosetta","Luc et Jean-Pierre Dardenne",""),
        (2000,"American Beauty","Dancer in the Dark","Lars von Trier",""),
        (2001,"Gladiator","La Chambre du fils","Nanni Moretti",""),
        (2002,"Un homme d'exception","Le Pianiste","Roman Polanski",""),
        (2003,"Chicago","Elephant","Gus Van Sant",""),
        (2004,"Le Seigneur des anneaux : Le Retour du roi","Fahrenheit 9/11","Michael Moore",""),
        (2005,"Million Dollar Baby","L'Enfant","Luc et Jean-Pierre Dardenne",""),
        (2006,"Collision","Le vent se lève","Ken Loach",""),
        (2007,"Les Infiltrés","Quatre mois, trois semaines, deux jours","Cristian Mungiu",""),
        (2008,"No Country for Old Men","Entre les murs","Laurent Cantet",""),
        (2009,"Slumdog Millionaire","Le Ruban blanc","Michael Haneke",""),
        (2010,"Démineurs","Oncle Boonmee, celui qui se souvient de ses vies antérieures","Apichatpong Weerasethakul",""),
        (2011,"Le Discours d'un roi","The Tree of Life","Terrence Malick",""),
        (2012,"The Artist","Amour","Michael Haneke",""),
        (2013,"Argo","La Vie d'Adèle","Abdellatif Kechiche",""),
        (2014,"Twelve Years a Slave","Winter Sleep","Nuri Bilge Ceylan",""),
        (2015,"Birdman","Dheepan","Jacques Audiard",""),
        (2016,"Spotlight","Moi, Daniel Blake","Ken Loach",""),
        (2017,"Moonlight","The Square","Ruben Östlund",""),
        (2018,"La Forme de l'eau","Une affaire de famille / Le Livre d'image","Hirokazu Kore-eda / Jean-Luc Godard",""),
        (2019,"Green Book","Parasite","Bong Joon-ho",""),
        (2020,"Parasite","","","Pas de festival (Covid-19)"),
        (2021,"Nomadland","Titane","Julia Ducournau",""),
        (2022,"Coda","Sans filtre","Ruben Östlund",""),
        (2023,"Everything Everywhere All at Once","Anatomie d'une chute","Justine Triet",""),
        (2024,"Oppenheimer","Anora","Sean Baker",""),
        (2025,"Anora","Un simple accident","Jafar Panahi",""),
        (2026,"Une bataille après l'autre","Fjord","Cristian Mungiu",""),
    ]
    c.executemany("INSERT OR IGNORE INTO films VALUES (?,?,?,?,?)", films)

# ── Jinja template (inline) ────────────────────────────────────────────
TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Film Checker — Oscar 🏆 &amp; Palme 🌴</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0f0f14;--card:#1a1a24;--border:#2a2a3a;--text:#e8e8f0;--muted:#8888a0;--accent-oscar:#f5c542;--accent-palme:#4ade80;--accent-seb:#60a5fa;--accent-paul:#f472b6}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding:1rem}
.container{max-width:1000px;margin:0 auto}
header{text-align:center;padding:2rem 1rem 1.5rem}
h1{font-size:1.6rem;font-weight:700}
h1 span{opacity:.7}
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
.filter-bar{text-align:center;margin-bottom:1rem}
.filter-bar label{font-size:.85rem;color:var(--muted);margin-right:.4rem}
.filter-bar select{background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:.3rem .6rem;font-size:.85rem}
.table-wrap{overflow-x:auto;border-radius:12px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:.88rem}
thead th{background:#12121c;padding:.6rem .4rem;text-align:left;font-size:.75rem;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);border-bottom:2px solid var(--border);white-space:nowrap;position:sticky;top:0}
tbody tr{border-bottom:1px solid var(--border);transition:background .15s}
tbody tr:hover{background:rgba(255,255,255,.03)}
tbody tr td{padding:.5rem .4rem;vertical-align:middle}
td.year{font-weight:600;width:50px;text-align:center}
.badge{display:inline-block;font-size:.65rem;font-weight:700;padding:.15rem .4rem;border-radius:4px;text-transform:uppercase;letter-spacing:.3px}
.badge.oscar{background:rgba(245,197,66,.15);color:var(--accent-oscar)}
.badge.palme{background:rgba(74,222,128,.15);color:var(--accent-palme)}
td.title{max-width:280px}
td.title .main{font-weight:500}
td.title .sub{display:block;font-size:.75rem;color:var(--muted);margin-top:1px}
td.notes{font-size:.75rem;color:var(--muted);font-style:italic;max-width:140px}
td.check{text-align:center;width:60px}
.check-wrap{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;cursor:pointer;transition:all .15s;border:2px solid var(--border);background:transparent;font-size:1rem}
.check-wrap.checked{border-color:currentColor}
.check-wrap.checked.seb{background:rgba(96,165,250,.15);color:var(--accent-seb);border-color:var(--accent-seb)}
.check-wrap.checked.paul{background:rgba(244,114,182,.15);color:var(--accent-paul);border-color:var(--accent-paul)}
.check-wrap input{display:none}
footer{text-align:center;padding:2rem 1rem;font-size:.8rem;color:var(--muted)}
footer a{color:var(--accent-oscar);text-decoration:none}
@media(max-width:700px){table{font-size:.8rem}td.title{max-width:180px}td.year{width:36px}td.check{width:44px}h1{font-size:1.2rem}}
</style>
</head>
<body>
<div class="container">
<header><h1>🏆 Oscar · 🌴 Palme <span>Checker</span></h1><p class="subtitle">Cochez les films que vous avez déjà vus</p></header>
<div class="tabs">
<a href="/?p=seb" class="seb {{ 'active' if person == 'seb' else '' }}">👤 Sébastien</a>
<a href="/?p=paul" class="paul {{ 'active' if person == 'paul' else '' }}">👤 Paul</a>
</div>
<div class="stats-bar" id="stats-bar">
<span class="stat">🏆 Oscar vus: <span class="num" id="oscar-count">0</span></span>
<span class="stat">🌴 Palme vues: <span class="num" id="palme-count">0</span></span>
<span class="stat">Total: <span class="num" id="total-count">0</span></span>
</div>
<div class="filter-bar">
<label for="f">Filtrer:</label>
<select id="f" onchange="filterTable(this.value)">
<option value="all">Tous les films</option>
<option value="vu">Déjà vus ✅</option>
<option value="pasvu">Pas encore vus</option>
<option value="oscar">Oscars seulement</option>
<option value="palme">Palmes seulement</option>
</select>
</div>
<div class="table-wrap"><table><thead><tr><th>Année</th><th>Type</th><th>Film</th><th>Notes</th><th title="Vu ?">Vu ?</th></tr></thead><tbody>
{% for f in films %}
<tr class="film-row" data-type="{{ f.type }}" data-vu="{{ '1' if f.vu else '0' }}">
<td class="year">{{ f.annee }}</td>
<td><span class="badge {{ f.type }}">{{ 'Oscar' if f.type == 'oscar' else 'Palme' }}</span></td>
<td class="title"><span class="main">{{ f.titre }}</span>{% if f.notes %}<span class="sub">{{ f.notes }}</span>{% endif %}</td>
<td class="notes">{% if f.type == 'palme' and not f.notes %}{% if f.annee == 1950 %}Pas de festival{% elif f.annee == 1968 %}Annulé (Mai 68){% elif f.annee == 2020 %}Annulé (Covid){% else %}—{% endif %}{% else %}{{ f.notes if f.notes else '—' }}{% endif %}</td>
<td class="check"><label class="check-wrap{{ ' checked' if f.vu else '' }} {{ person }}" onclick="toggle({{ f.annee }},'{{ f.type }}',{{ f.sub_idx }},'{{ person }}',this)"><input type="checkbox"{{ ' checked' if f.vu else '' }}>{% if f.vu %}✅{% endif %}</label></td>
</tr>
{% endfor %}
</tbody></table></div>
<footer><a href="https://docs.google.com/spreadsheets/d/1ixMU8HQCyMXFwO4-Rn5UBqZLGi1CavtnwT2uNWob9Pc/edit" target="_blank">📊 Voir le Google Sheet original</a></footer>
</div>
<script>
async function toggle(a,t,s,p,el){const i=el.querySelector('input');const v=i.checked?0:1;try{await fetch('/vote',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({annee:a,film_type:t,sub_idx:s,personne:p,vu:v})})}catch(e){console.error(e);return}
i.checked=v===1;el.classList.toggle('checked',v===1);el.innerHTML=v?'✅':'';const r=el.closest('.film-row');if(r)r.dataset.vu=v;updateStats()}
function filterTable(v){document.querySelectorAll('.film-row').forEach(r=>{const t=r.dataset.type;const u=r.dataset.vu==='1';let s=true;if(v==='vu')s=u;else if(v==='pasvu')s=!u;else if(v==='oscar')s=t==='oscar';else if(v==='palme')s=t==='palme';r.style.display=s?'':'none'})}
async function updateStats(){try{const r=await fetch('/api/stats');if(!r.ok)return;const s=await r.json();const p='{{ person }}';let o=0,l=0;s.forEach(x=>{if(x.personne!==p)return;if(x.film_type==='oscar')o=x.n;if(x.film_type==='palme')l=x.n});document.getElementById('oscar-count').textContent=o;document.getElementById('palme-count').textContent=l;document.getElementById('total-count').textContent=o+l}catch(e){}}
updateStats()
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

    cur = conn.execute("SELECT annee, film_type, sub_idx, vu FROM votes WHERE personne=?", (person,))
    votes = {(r["annee"], r["film_type"], r["sub_idx"]): r["vu"] for r in cur.fetchall()}
    conn.close()

    expanded = []
    for f in films:
        expanded.append({
            "annee": f["annee"], "titre": f["oscar"], "type": "oscar",
            "sub_idx": 0, "notes": f.get("notes", ""),
            "vu": votes.get((f["annee"], "oscar", 0), False),
        })
        if f.get("palme"):
            for i, p in enumerate(x.strip() for x in f["palme"].split(" / ")):
                expanded.append({
                    "annee": f["annee"], "titre": p, "type": "palme",
                    "sub_idx": i, "notes": "",
                    "vu": votes.get((f["annee"], "palme", i), False),
                })

    return jinja_template.render(films=expanded, person=person, other="paul" if person == "seb" else "seb")


@app.post("/vote")
async def vote(annee: int = Form(...), film_type: str = Form(...),
               sub_idx: int = Form(0), personne: str = Form(...), vu: int = Form(0)):
    conn = db()
    conn.execute("""INSERT INTO votes (annee, personne, film_type, sub_idx, vu)
                     VALUES (?,?,?,?,?) ON CONFLICT(annee,personne,film_type,sub_idx)
                     DO UPDATE SET vu=excluded.vu""",
                 (annee, personne, film_type, sub_idx, vu))
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


@app.get("/health")
async def health():
    return {"status": "ok"}
