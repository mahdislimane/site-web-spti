"""
Génère le site statique de Solutions Passerelle TI (hébergé sur GitHub Pages).

    python build.py

Les pages juridiques de Pastille sont produites à partir de ../copyManager/Legal/*.md : relancer ce script après
chaque modification du contrat ou de la politique, puis publier (git commit + push).
"""
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEGAL = ROOT.parent / "copyManager" / "Legal"
APP_ASSETS = ROOT.parent / "copyManager" / "packaging" / "Assets"

# --- À compléter --------------------------------------------------------------------------------------------------
COMPANY = "Solutions Passerelle TI"
EMAIL = "SPTI@solutionspasserelleti.ca"  # courriel de contact affiché sur le site, ex. "info@solutionspasserelleti.ca" (vide = masqué)
STORE_URL = ""  # lien de la fiche Pastille dans le Microsoft Store, ex. "https://apps.microsoft.com/detail/XXXXXXXXXXXX"
# -------------------------------------------------------------------------------------------------------------------

T = {
    "fr": {
        "lang": "fr-CA", "home": "Accueil", "products": "Produits", "contact": "Contact",
        "privacy": "Confidentialité", "license": "Contrat de licence", "other": "English",
        "store": "Obtenir sur le Microsoft Store", "soon": "Bientôt sur le Microsoft Store",
        "made": "Conçu au Québec", "back": "Retour à Pastille",
        "notfound": "Page introuvable", "notfound_text": "Cette page n'existe pas ou a été déplacée.",
    },
    "en": {
        "lang": "en-CA", "home": "Home", "products": "Products", "contact": "Contact",
        "privacy": "Privacy", "license": "License agreement", "other": "Français",
        "store": "Get it from the Microsoft Store", "soon": "Coming soon to the Microsoft Store",
        "made": "Made in Québec", "back": "Back to Pastille",
        "notfound": "Page not found", "notfound_text": "This page does not exist or has moved.",
    },
}

# Chemin de chaque page dans chaque langue (sert au lien « English / Français »).
PAGES = {
    "home": {"fr": "index.html", "en": "en/index.html"},
    "pastille": {"fr": "pastille/index.html", "en": "en/pastille/index.html"},
    "privacy": {"fr": "pastille/confidentialite.html", "en": "en/pastille/privacy.html"},
    "license": {"fr": "pastille/contrat.html", "en": "en/pastille/license.html"},
}


def rel(from_page: str, to_path: str) -> str:
    depth = from_page.count("/")
    return "../" * depth + to_path


def store_button(lang: str) -> str:
    t = T[lang]
    if STORE_URL:
        return f'<a class="button" href="{html.escape(STORE_URL)}">{t["store"]}</a>'
    return f'<span class="button disabled">{t["soon"]}</span>'


def layout(lang: str, key: str, page: str, title: str, description: str, body: str) -> str:
    t = T[lang]
    other = "en" if lang == "fr" else "fr"
    other_page = PAGES[key][other] if key in PAGES else PAGES["home"][other]
    r = lambda p: rel(page, p)
    contact = (f' · <a href="mailto:{html.escape(EMAIL)}">{html.escape(EMAIL)}</a>' if EMAIL else "")
    return f"""<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="icon" href="{r('assets/favicon.png')}">
<link rel="stylesheet" href="{r('assets/style.css')}">
</head>
<body>
<header class="site-header">
  <div class="wrap header-row">
    <a class="brand" href="{r(PAGES['home'][lang])}">{html.escape(COMPANY)}</a>
    <nav>
      <a href="{r(PAGES['pastille'][lang])}">Pastille</a>
      <a href="{r(other_page)}" hreflang="{other}">{T[other]['lang'][:2].upper()}</a>
    </nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    © 2026 9575-4255 Québec inc. ({html.escape(COMPANY)}) · {t['made']}{contact}<br>
    <a href="{r(PAGES['privacy'][lang])}">{t['privacy']}</a> ·
    <a href="{r(PAGES['license'][lang])}">{t['license']}</a> ·
    <a href="{r(other_page)}" hreflang="{other}">{t['other']}</a>
  </div>
</footer>
</body>
</html>
"""


# --- Markdown minimal (titres, listes, paragraphes, gras, italique, liens) ----------------------------------------
def inline(text: str) -> str:
    s = html.escape(text, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(https?://[^\s<>()]+[^\s<>().,;:])", r'<a href="\1">\1</a>', s)
    s = re.sub(r"(?<![/\w.])(www\.[a-z0-9.-]+\.[a-z]{2,})", r'<a href="https://\1">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]", r'<mark>[\1]</mark>', s)  # zones à compléter, bien visibles
    s = re.sub(r"« ", "«&nbsp;", s)  # ponctuation française : pas de retour à la ligne avant « » : ; ! ?
    return re.sub(r" ([»:;!?])", r"&nbsp;\1", s)


def markdown(md: str) -> tuple[str, str]:
    """Retourne (titre, html)."""
    title, out, para, items = "", [], [], []

    def flush():
        if para:
            out.append("<p>" + "<br>".join(inline(p) for p in para) + "</p>")  # lignes consécutives = retours à la ligne (coordonnées)
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in md.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("# "):
            flush()
            title = s[2:].strip()
        elif s.startswith("## "):
            flush()
            out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("### "):
            flush()
            out.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("- "):
            if para:
                flush()
            items.append(s[2:])
        elif items and line.startswith("  "):
            items[-1] += " " + s
        else:
            if items:
                flush()
            para.append(s)
    flush()
    return title, "\n".join(out)


# --- Contenu -------------------------------------------------------------------------------------------------------
HOME = {
    "fr": ("Des logiciels simples, utiles et respectueux de votre vie privée.",
           "Solutions Passerelle TI conçoit au Québec des applications pour Windows qui fonctionnent sur votre "
           "ordinateur, sans compte, sans publicité et sans collecte de données.",
           "Gestionnaire de presse-papiers pour Windows : retrouvez tout ce que vous avez copié, collez en un clic "
           "et retirez les renseignements personnels avant de coller dans un outil d'IA.",
           "Découvrir Pastille"),
    "en": ("Simple, useful software that respects your privacy.",
           "Solutions Passerelle TI builds Windows applications in Québec that run on your computer, with no "
           "account, no ads and no data collection.",
           "Clipboard manager for Windows: find everything you copied, paste in one click and remove personal "
           "information before pasting into an AI tool.",
           "Discover Pastille"),
}

PASTILLE = {
    "fr": {
        "tagline": "Gestionnaire de presse-papiers pour Windows",
        "intro": "Pastille garde l'historique de vos copies, vous permet de les recoller dans la fenêtre "
                 "précédente et vous aide à masquer les renseignements personnels avant de les envoyer ailleurs.",
        "features": [
            ("Historique de vos copies", "Retrouvez un texte ou une capture d'écran copiés il y a une heure ou une semaine, épinglez ceux que vous réutilisez souvent."),
            ("Collage en un clic", "Un clic recolle la copie dans la fenêtre où vous travailliez. Raccourci Win+Maj+V."),
            ("Anonymisation", "Un dictionnaire remplace noms, courriels, téléphones ou numéros de dossier par des codes, puis les remet en clair au retour."),
            ("Mode Bouclier", "Copiez un texte, collez-le dans un outil d'IA sans vos renseignements personnels, récupérez la réponse avec les vraies valeurs. Tout se fait sur votre ordinateur."),
            ("Correcteur d'orthographe", "Les fautes sont soulignées dans vos copies, avec des suggestions au clic droit."),
            ("Privé par défaut", "Historique chiffré sur votre ordinateur, gestionnaires de mots de passe exclus, fenêtres masquées dans les partages d'écran."),
        ],
        "plans": "Gratuit ou Pro",
        "rows": [
            ("Historique", "100 copies", "2000 copies"),
            ("Images et captures d'écran", "10", "200"),
            ("Lecture du texte des images", "3 par jour", "Illimitée"),
            ("Copies épinglées", "5", "Illimitées"),
            ("Règles d'anonymisation", "3", "Illimitées"),
            ("Historique chiffré, orthographe, applications exclues", "✓", "✓"),
            ("Filtres rapides, historique des fichiers copiés", "—", "✓"),
            ("Anonymisation automatique (courriels, téléphones, NAS, cartes…)", "—", "✓"),
            ("Mode Bouclier, export et import du dictionnaire", "—", "✓"),
        ],
        "cols": ("", "Gratuit", "Pro"),
        "trial": "Pastille Pro s'achète une seule fois dans l'application, par le Microsoft Store. Un essai gratuit de 30 jours est offert.",
        "privacy_title": "Vos données restent chez vous",
        "privacy_text": "Pastille fonctionne entièrement sur votre ordinateur. Nous ne recevons ni vos copies, ni votre dictionnaire, ni aucune statistique d'utilisation.",
        "requirements": "Windows 10 (version 1809 ou plus récente) ou Windows 11, 64 bits. Français et anglais.",
    },
    "en": {
        "tagline": "Clipboard manager for Windows",
        "intro": "Pastille keeps a history of what you copy, pastes it back into the previous window and helps you "
                 "mask personal information before sending it elsewhere.",
        "features": [
            ("Copy history", "Find text or a screenshot you copied an hour or a week ago, and pin the ones you reuse often."),
            ("One-click paste", "One click pastes the copy into the window you were working in. Shortcut Win+Shift+V."),
            ("Anonymization", "A dictionary replaces names, emails, phone numbers or file numbers with codes, then restores them on the way back."),
            ("Shield mode", "Copy a text, paste it into an AI tool without your personal information, and get the answer back with the real values. Everything happens on your computer."),
            ("Spell checker", "Mistakes are underlined in your copies, with suggestions on right-click."),
            ("Private by default", "Encrypted history on your computer, password managers excluded, windows hidden during screen sharing."),
        ],
        "plans": "Free or Pro",
        "rows": [
            ("History", "100 copies", "2000 copies"),
            ("Images and screenshots", "10", "200"),
            ("Reading text from images", "3 per day", "Unlimited"),
            ("Pinned copies", "5", "Unlimited"),
            ("Anonymization rules", "3", "Unlimited"),
            ("Encrypted history, spell checking, excluded apps", "✓", "✓"),
            ("Quick filters, copied files history", "—", "✓"),
            ("Automatic anonymization (emails, phones, SIN, cards…)", "—", "✓"),
            ("Shield mode, dictionary export and import", "—", "✓"),
        ],
        "cols": ("", "Free", "Pro"),
        "trial": "Pastille Pro is a one-time purchase made in the app through the Microsoft Store. A free 30-day trial is available.",
        "privacy_title": "Your data stays with you",
        "privacy_text": "Pastille runs entirely on your computer. We never receive your copies, your dictionary or any usage statistics.",
        "requirements": "Windows 10 (version 1809 or later) or Windows 11, 64-bit. French and English.",
    },
}


def home_page(lang: str) -> str:
    page = PAGES["home"][lang]
    headline, intro, pastille, cta = HOME[lang]
    t = T[lang]
    body = f"""
<section class="hero">
  <h1>{headline}</h1>
  <p class="lead">{intro}</p>
</section>
<section>
  <h2>{t['products']}</h2>
  <a class="product" href="{rel(page, PAGES['pastille'][lang])}">
    <img src="{rel(page, 'assets/pastille.png')}" alt="" width="72" height="72">
    <div>
      <h3>Pastille</h3>
      <p>{pastille}</p>
      <span class="more">{cta} →</span>
    </div>
  </a>
</section>"""
    return layout(lang, "home", page, COMPANY, intro, body)


def pastille_page(lang: str) -> str:
    page = PAGES["pastille"][lang]
    p, t = PASTILLE[lang], T[lang]
    features = "".join(f"<div class=\"feature\"><h3>{h}</h3><p>{d}</p></div>" for h, d in p["features"])
    head = "".join(f"<th>{c}</th>" for c in p["cols"])
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in p["rows"])
    body = f"""
<section class="hero app-hero">
  <img src="{rel(page, 'assets/pastille.png')}" alt="" width="112" height="112">
  <div>
    <h1>Pastille</h1>
    <p class="tagline">{p['tagline']}</p>
    <p class="lead">{p['intro']}</p>
    {store_button(lang)}
  </div>
</section>
<section class="features">{features}</section>
<section>
  <h2>{p['plans']}</h2>
  <div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
  <p>{p['trial']}</p>
</section>
<section class="note">
  <h2>{p['privacy_title']}</h2>
  <p>{p['privacy_text']}</p>
  <p><a href="{rel(page, PAGES['privacy'][lang])}">{t['privacy']}</a> · <a href="{rel(page, PAGES['license'][lang])}">{t['license']}</a></p>
</section>
<p class="small">{p['requirements']}</p>"""
    return layout(lang, "pastille", page, f"Pastille – {p['tagline']}", p["intro"], body)


def legal_page(lang: str, key: str, source: str) -> str:
    page = PAGES[key][lang]
    title, content = markdown((LEGAL / source).read_text(encoding="utf-8-sig"))
    body = f"""
<article class="legal">
  <p class="small"><a href="{rel(page, PAGES['pastille'][lang])}">← {T[lang]['back']}</a></p>
  <h1>{inline(title)}</h1>
{content}
</article>"""
    return layout(lang, key, page, title, title, body)


def not_found() -> str:
    # GitHub Pages sert 404.html à la racine pour toute adresse inconnue : liens absolus, dans les deux langues.
    body = f"""
<section class="hero">
  <h1>404</h1>
  <p class="lead">{T['fr']['notfound_text']}<br>{T['en']['notfound_text']}</p>
  <p><a href="/">{T['fr']['home']}</a> · <a href="/en/">{T['en']['home']}</a></p>
</section>"""
    return layout("fr", "home", "404.html", f"{T['fr']['notfound']} – {COMPANY}", T["fr"]["notfound"], body) \
        .replace('href="assets/', 'href="/assets/').replace('href="index.html"', 'href="/"') \
        .replace('href="pastille/', 'href="/pastille/').replace('href="en/', 'href="/en/')


def write(path: str, content: str):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    print("  ", path)


def main():
    print("Génération du site :")
    (ROOT / "assets").mkdir(exist_ok=True)
    shutil.copyfile(APP_ASSETS / "Square44x44Logo.targetsize-256_altform-unplated.png", ROOT / "assets" / "pastille.png")
    shutil.copyfile(APP_ASSETS / "Square44x44Logo.targetsize-32_altform-unplated.png", ROOT / "assets" / "favicon.png")
    for lang in ("fr", "en"):
        write(PAGES["home"][lang], home_page(lang))
        write(PAGES["pastille"][lang], pastille_page(lang))
        suffix = "fr" if lang == "fr" else "en"
        write(PAGES["privacy"][lang], legal_page(lang, "privacy", f"Privacy.{suffix}.md"))
        write(PAGES["license"][lang], legal_page(lang, "license", f"Eula.{suffix}.md"))
    write("404.html", not_found())
    left = sum(p.read_text(encoding="utf-8").count("<mark>") for p in ROOT.rglob("*.html"))
    if left:
        print(f"Attention : {left} zone(s) [à compléter] encore présente(s) dans les pages juridiques.")


if __name__ == "__main__":
    main()
