"""
Génère le site statique de SPTI (hébergé sur GitHub Pages).

    python build.py

Les pages juridiques de Pastille sont produites à partir de ../copyManager/Legal/*.md : relancer ce script après
chaque modification du contrat ou de la politique, puis publier (git commit + push).
"""
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEGAL = ROOT.parent / "copyManager" / "Legal"
APP_ASSETS = ROOT.parent / "copyManager" / "packaging" / "Assets"

# --- À compléter --------------------------------------------------------------------------------------------------
COMPANY = "SPTI"
SITE_URL = "https://solutionspasserelleti.ca"  # adresse publique du site (sitemap, liens canoniques)
LEGAL_NAME = "9575-4255 Québec inc."
SAME_AS = []  # pages officielles de l'entreprise (ex. "https://www.linkedin.com/company/…"), reprises dans les données structurées
EMAIL = "SPTI@solutionspasserelleti.ca"  # courriel de contact affiché sur le site, ex. "info@solutionspasserelleti.ca" (vide = masqué)
STORE_URL = ""  # lien de la fiche Pastille dans le Microsoft Store, ex. "https://apps.microsoft.com/detail/XXXXXXXXXXXX"
# -------------------------------------------------------------------------------------------------------------------

T = {
    "fr": {
        "lang": "fr-CA", "home": "Accueil", "products": "Produits", "contact": "Contact",
        "services": "Services", "apps": "Applications", "sectors": "Secteurs", "about": "Notre approche",
        "theme": "Changer de thème (clair / sombre)",
        "privacy": "Confidentialité", "license": "Contrat de licence", "other": "English",
        "store": "Obtenir sur le Microsoft Store", "soon": "Bientôt sur le Microsoft Store",
        "made": "Conçu au Québec", "back": "Retour à Pastille",
        "notfound": "Page introuvable", "notfound_text": "Cette page n'existe pas ou a été déplacée.",
    },
    "en": {
        "lang": "en-CA", "home": "Home", "products": "Products", "contact": "Contact",
        "services": "Services", "apps": "Apps", "sectors": "Industries", "about": "Our approach",
        "theme": "Switch theme (light / dark)",
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


# Version du logo dans son adresse : les navigateurs gardent longtemps l'icône d'onglet en cache, une nouvelle
# adresse à chaque changement du fichier les force à la recharger.
def versioned(path: str) -> str:
    return f"{path}?v=" + hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:8]


LOGO = versioned("assets/logo.svg")        # symbole détaillé (en-tête, données structurées)
FAVICON = versioned("assets/favicon.svg")  # symbole simplifié pour l'onglet du navigateur
FAVICON_PNG = versioned("assets/favicon-192.png")  # Google affiche ce format dans ses résultats (multiple de 48 px)
APPLE_ICON = versioned("assets/apple-touch-icon.png")


def rel(from_page: str, to_path: str) -> str:
    # Les liens visent le dossier (« en/ ») et non « en/index.html » : sinon Google découvre
    # deux adresses pour la même page et signale « Autre page avec balise canonique correcte ».
    path, sep, anchor = to_path.partition("#")
    path = path.removesuffix("index.html")
    target = "../" * from_page.count("/") + path
    return (target or "./") + sep + anchor


def store_button(lang: str) -> str:
    t = T[lang]
    if STORE_URL:
        return f'<a class="button" href="{html.escape(STORE_URL)}">{t["store"]}</a>'
    return f'<span class="button disabled">{t["soon"]}</span>'


THEME_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
              'stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>')

# Thème : choix enregistré dans le navigateur (si permis), sinon celui du système.
THEME_SCRIPT = """<script>
(function () {
  var root = document.documentElement, key = "spti-theme";
  try { var saved = localStorage.getItem(key); if (saved) root.setAttribute("data-theme", saved); } catch (e) {}
  window.sptiToggleTheme = function () {
    var dark = root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
    var next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem(key, next); } catch (e) {}
  };
})();
</script>"""


def url(path: str) -> str:
    """Adresse publique d'une page : « pastille/index.html » devient « https://…/pastille/ »."""
    return f"{SITE_URL}/{path.removesuffix('index.html')}"


def sitemap() -> str:
    """Toutes les pages, chacune avec sa version dans l'autre langue (hreflang)."""
    entries = []
    for pages in PAGES.values():
        alternates = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{T[l]["lang"]}" href="{url(p)}"/>'
                             for l, p in pages.items())
        alternates += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{url(pages["fr"])}"/>'
        entries += [f"  <url>\n    <loc>{url(p)}</loc>{alternates}\n  </url>" for p in pages.values()]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(entries) + "\n</urlset>\n")


def layout(lang: str, key: str, page: str, title: str, description: str, body: str, wrap: bool = True) -> str:
    t = T[lang]
    other = "en" if lang == "fr" else "fr"
    other_page = PAGES[key][other] if key in PAGES else PAGES["home"][other]
    if page == "404.html":
        seo = '<meta name="robots" content="noindex">\n'
    else:
        seo = f'<link rel="canonical" href="{url(page)}">\n' + "".join(
            f'<link rel="alternate" hreflang="{T[l]["lang"]}" href="{url(p)}">\n' for l, p in PAGES[key].items())
    r = lambda p: rel(page, p)
    home = r(PAGES["home"][lang])
    contact = (f' · <a href="mailto:{html.escape(EMAIL)}">{html.escape(EMAIL)}</a>' if EMAIL else "")
    main = f'<main class="wrap">\n{body}\n</main>' if wrap else f"<main>\n{body}\n</main>"
    return f"""<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
{seo}<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="{r(FAVICON_PNG)}" type="image/png" sizes="192x192">
<link rel="icon" href="{r(FAVICON)}" type="image/svg+xml">
<link rel="apple-touch-icon" href="{r(APPLE_ICON)}">
<link rel="stylesheet" href="{r('assets/style.css')}">
{THEME_SCRIPT}
</head>
<body>
<header class="site-header">
  <div class="wrap header-row">
    <a class="brand" href="{home}"><img src="{r(LOGO)}" alt="" width="34" height="34"><span>{html.escape(COMPANY)}</span></a>
    <nav>
      <span class="nav-links">
        <a href="{home}#services">{t['services']}</a>
        <a href="{home}#applications">{t['apps']}</a>
        <a href="{home}#a-propos">{t['about']}</a>
        <a href="{home}#contact">{t['contact']}</a>
      </span>
      <a href="{r(other_page)}" hreflang="{other}" title="{t['other']}">{T[other]['lang'][:2].upper()}</a>
      <button class="theme-toggle" type="button" onclick="sptiToggleTheme()" title="{t['theme']}" aria-label="{t['theme']}">{THEME_ICON}</button>
    </nav>
  </div>
</header>
{main}
<footer class="site-footer">
  <div class="wrap footer-row">
    <div>© 2026 {LEGAL_NAME} ({html.escape(COMPANY)}) · {t['made']}{contact}</div>
    <div>
      <a href="{r(PAGES['pastille'][lang])}">Pastille</a> ·
      <a href="{r(PAGES['privacy'][lang])}">{t['privacy']}</a> ·
      <a href="{r(PAGES['license'][lang])}">{t['license']}</a> ·
      <a href="{r(other_page)}" hreflang="{other}">{t['other']}</a>
    </div>
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
ICONS = {
    "apps": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M17.5 14v7M14 17.5h7"/>',
    "flow": '<circle cx="5" cy="6" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="M7.5 6H14a4 4 0 0 1 4 4v5.5"/><path d="m15.5 13 2.5 2.5 2.5-2.5"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "cloud": '<path d="M7 18h10a4.5 4.5 0 0 0 .5-9 6 6 0 0 0-11.6 1.7A3.7 3.7 0 0 0 7 18z"/><path d="M12 12v4M10.5 13.5 12 12l1.5 1.5"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "code": '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
    "plane": '<path d="M10.5 13.5 3 11l1.5-1.5 8 1 4-4a2 2 0 0 1 3 3l-4 4 1 8L15 22l-2.5-7.5"/>',
    "bank": '<path d="M3 10h18L12 4 3 10zM5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18"/>',
    "hotel": '<path d="M3 20V8l9-4 9 4v12M3 20h18M9 20v-5h6v5M8 10h.01M12 10h.01M16 10h.01"/>',
    "energy": '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>',
    "shield": '<path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6l-8-3z"/><path d="m9 12 2 2 4-4"/>',
    "speed": '<path d="M12 14l4-4"/><path d="M3.5 18a9 9 0 1 1 17 0"/><path d="M12 14h.01"/>',
    "quality": '<circle cx="12" cy="9" r="6"/><path d="m9.5 9 1.8 1.8L14.8 7.3"/><path d="M8.5 14 7 22l5-3 5 3-1.5-8"/>',
    "smile": '<circle cx="12" cy="12" r="9"/><path d="M8.5 14.5a4.5 4.5 0 0 0 7 0M9 9.5h.01M15 9.5h.01"/>',
    "factory": '<path d="M3 20V9l6 4V9l6 4V5h6v15H3z"/><path d="M7 16h2M12 16h2M17 16h2"/>',
}


def icon(name: str) -> str:
    return ('<span class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg></span>')


HOME = {
    "fr": {
        "eyebrow": "Firme de services TI",
        "title": "Power Platform, Dynamics 365 et Azure à Québec",
        "headline": "Des solutions d'affaires sur mesure, de l'analyse à la mise en production.",
        "intro": "Établie à Québec, SPTI conçoit, intègre et automatise vos applications Microsoft Power Platform, "
                 "Dynamics 365 et Azure, et développe des logiciels qui respectent la vie privée de leurs utilisateurs.",
        "cta": "Discuter de votre projet", "cta2": "Voir nos services",
        "stats": [("6 secteurs", "d'activité servis, du transport aérien à l'assurance"),
                  ("Certifiée", "expertise Microsoft Power Platform, niveau Expert"),
                  ("Agile", "livraisons courtes et démonstrations régulières"),
                  ("FR · EN", "accompagnement en français et en anglais")],
        "services_title": "Ce que nous faisons",
        "services_intro": "Une seule équipe, de la compréhension de vos besoins jusqu'à l'intégration avec vos systèmes existants.",
        "services": [
            ("apps", "Applications d'affaires Power Platform",
             "Applications Power Apps (Canvas et Model-Driven), portails Power Pages et modèles de données Dataverse, adaptés à vos processus.",
             ["Power Apps", "Power Pages", "Dataverse", "Power Fx"]),
            ("flow", "Automatisation des processus",
             "Approbations, notifications, mises à jour de données et génération de documents Word ou Excel, sans tâches manuelles répétitives.",
             ["Power Automate", "Logic Apps", "VBA"]),
            ("link", "Dynamics 365 et intégrations ERP",
             "Personnalisation de Dynamics 365 (dont Field Service) et échanges de données avec vos ERP, comme JD Edwards EnterpriseOne.",
             ["Dynamics 365", "Field Service", "JD Edwards", "API REST"]),
            ("cloud", "Cloud Azure et sécurité",
             "Azure Functions, Logic Apps et Blob Storage, sécurité Dataverse (rôles, unités d'affaires) et accès protégés par Entra ID et OAuth.",
             ["Azure", "Entra ID", "OAuth", "Plugins C#"]),
            ("chart", "Données et tableaux de bord",
             "Rapports Power BI et indicateurs clés, à partir de Dataverse, SQL Server, PostgreSQL, SharePoint ou Excel.",
             ["Power BI", "DAX", "Power Query", "SQL"]),
            ("code", "Développement web et logiciel",
             "Applications web React et Angular, services Node.js et .NET, et logiciels Windows comme Pastille.",
             ["React · TypeScript", "Angular", "Node.js", "C# · .NET"]),
        ],
        "sectors_title": "Secteurs où nous avons livré",
        "sectors": [
            ("plane", "Transport aérien", "Gestion des accès du personnel, des véhicules et des zones de sécurité d'un aéroport international."),
            ("bank", "Services financiers", "Solution interne pour la productivité des conseillers : applications, base de données et tableaux de bord."),
            ("energy", "Énergie et distribution", "Intégration d'un ERP avec Dynamics 365 Field Service pour un distributeur de produits pétroliers."),
            ("hotel", "Hôtellerie", "Gestion centralisée des clients, des réservations, des services et de la facturation."),
            ("shield", "Assurance", "Parcours de souscription en ligne et assistant conversationnel pour les réclamations."),
            ("factory", "Industrie et organismes", "Audit de conformité des processus et génération automatique de documents."),
        ],
        "apps_title": "Nos applications",
        "apps_intro": "Nous développons aussi des logiciels qui simplifient le travail de bureau au quotidien.",
        "pastille": "L'outil de productivité des employés de bureau. Pastille garde à portée de main tout ce qui est "
                    "copié au fil de la journée (textes, captures d'écran, fichiers), lit le texte des images et protège "
                    "les renseignements personnels lors de l'utilisation d'outils d'IA. Moins de ressaisie, moins "
                    "d'erreurs, et tout reste sur l'ordinateur.",
        "pastille_status": "Bientôt sur le Microsoft Store", "pastille_more": "Découvrir Pastille",
        "custom_title": "Votre application ?", "custom_text": "Vous avez une idée ou un processus à outiller ? Nous la concevons avec vous, de la maquette à la mise en ligne.",
        "about_title": "Des résultats concrets, livrés avec rigueur",
        "about_text": "Chaque mandat est mené avec la même exigence : comprendre votre réalité, livrer rapidement une "
                      "solution qui fonctionne et vous accompagner jusqu'à ce que vos équipes l'aient adoptée.",
        "pillars": [("speed", "Efficacité", "Des livraisons courtes et priorisées : vos équipes gagnent du temps dès les premières semaines, pas seulement à la fin du projet."),
                    ("quality", "Qualité", "Des solutions testées, sécurisées et documentées, construites selon les bonnes pratiques Microsoft pour durer et évoluer."),
                    ("smile", "Satisfaction client", "Une communication transparente, des démonstrations régulières et un soutien après la mise en production : vous gardez le contrôle à chaque étape.")],
        "steps_title": "Notre démarche",
        "certs_title": "Expertise certifiée Microsoft",
        "certs": ["Power Platform Solution Architect Expert", "Power Platform Developer Associate",
                  "Power Platform Functional Consultant Associate", "Power Platform App Maker Associate"],
        "steps": [("Analyse", "Ateliers avec vos équipes, besoins traduits en exigences claires."),
                  ("Estimation", "Plan de travail, priorités et coûts connus d'avance."),
                  ("Réalisation agile", "Livraisons courtes, démonstrations régulières et ajustements."),
                  ("Mise en production", "Déploiement, sécurité, documentation et soutien.")],
        "contact_title": "Parlons de votre projet",
        "contact_text": "Décrivez-nous votre besoin : nous vous répondons rapidement, en français ou en anglais.",
        "contact_cta": "Nous écrire",
    },
    "en": {
        "eyebrow": "IT services firm",
        "title": "Power Platform, Dynamics 365 and Azure in Québec City",
        "headline": "Custom business solutions, from analysis to production.",
        "intro": "Based in Québec City, SPTI designs, integrates and automates your Microsoft Power Platform, "
                 "Dynamics 365 and Azure applications, and builds software that respects its users' privacy.",
        "cta": "Discuss your project", "cta2": "See our services",
        "stats": [("6 industries", "served, from air transport to insurance"),
                  ("Certified", "Microsoft Power Platform expertise, Expert level"),
                  ("Agile", "short iterations and regular demos"),
                  ("EN · FR", "support in English and French")],
        "services_title": "What we do",
        "services_intro": "One team, from understanding your needs to integrating with your existing systems.",
        "services": [
            ("apps", "Power Platform business apps",
             "Power Apps (Canvas and Model-Driven), Power Pages portals and Dataverse data models, tailored to your processes.",
             ["Power Apps", "Power Pages", "Dataverse", "Power Fx"]),
            ("flow", "Process automation",
             "Approvals, notifications, data updates and Word or Excel document generation, without repetitive manual work.",
             ["Power Automate", "Logic Apps", "VBA"]),
            ("link", "Dynamics 365 and ERP integration",
             "Dynamics 365 customization (including Field Service) and data exchange with your ERP, such as JD Edwards EnterpriseOne.",
             ["Dynamics 365", "Field Service", "JD Edwards", "REST APIs"]),
            ("cloud", "Azure cloud and security",
             "Azure Functions, Logic Apps and Blob Storage, Dataverse security (roles, business units) and access protected by Entra ID and OAuth.",
             ["Azure", "Entra ID", "OAuth", "C# plugins"]),
            ("chart", "Data and dashboards",
             "Power BI reports and key indicators, from Dataverse, SQL Server, PostgreSQL, SharePoint or Excel.",
             ["Power BI", "DAX", "Power Query", "SQL"]),
            ("code", "Web and software development",
             "React and Angular web apps, Node.js and .NET services, and Windows software such as Pastille.",
             ["React · TypeScript", "Angular", "Node.js", "C# · .NET"]),
        ],
        "sectors_title": "Industries we have delivered for",
        "sectors": [
            ("plane", "Air transport", "Access management for staff, vehicles and security zones at an international airport."),
            ("bank", "Financial services", "Internal solution for advisor productivity: apps, database and dashboards."),
            ("energy", "Energy and distribution", "ERP integration with Dynamics 365 Field Service for a petroleum products distributor."),
            ("hotel", "Hospitality", "Centralized management of guests, bookings, services and billing."),
            ("shield", "Insurance", "Online policy subscription journey and conversational assistant for claims."),
            ("factory", "Industry and non-profits", "Process compliance auditing and automatic document generation."),
        ],
        "apps_title": "Our apps",
        "apps_intro": "We also build software that makes everyday office work simpler.",
        "pastille": "The productivity tool for office workers. Pastille keeps everything copied during the day close at "
                    "hand (text, screenshots, files), reads text from images and protects personal information when "
                    "using AI tools. Less retyping, fewer errors, and everything stays on the computer.",
        "pastille_status": "Coming soon to the Microsoft Store", "pastille_more": "Discover Pastille",
        "custom_title": "Your app?", "custom_text": "Have an idea or a process to equip? We design it with you, from mockup to launch.",
        "about_title": "Concrete results, delivered with rigor",
        "about_text": "Every engagement is held to the same standard: understand your reality, quickly deliver a "
                      "solution that works, and support you until your teams have adopted it.",
        "pillars": [("speed", "Efficiency", "Short, prioritized deliveries: your teams save time from the first weeks, not only at the end of the project."),
                    ("quality", "Quality", "Tested, secure and documented solutions, built on Microsoft best practices to last and evolve."),
                    ("smile", "Client satisfaction", "Transparent communication, regular demos and support after go-live: you stay in control at every step.")],
        "steps_title": "How we work",
        "certs_title": "Certified Microsoft expertise",
        "certs": ["Power Platform Solution Architect Expert", "Power Platform Developer Associate",
                  "Power Platform Functional Consultant Associate", "Power Platform App Maker Associate"],
        "steps": [("Analysis", "Workshops with your teams, needs turned into clear requirements."),
                  ("Estimate", "Work plan, priorities and costs known upfront."),
                  ("Agile delivery", "Short iterations, regular demos and adjustments."),
                  ("Go-live", "Deployment, security, documentation and support.")],
        "contact_title": "Let's talk about your project",
        "contact_text": "Tell us what you need: we reply quickly, in English or French.",
        "contact_cta": "Write to us",
    },
}

PASTILLE = {
    "fr": {
        "tagline": "L'assistant presse-papiers des employés de bureau",
        "intro": "Courriels, formulaires, rapports : Pastille garde l'historique de tout ce que vous copiez, le recolle "
                 "en un clic dans la fenêtre où vous travaillez et masque les renseignements personnels avant qu'ils ne "
                 "quittent votre poste. Moins de ressaisie, moins d'erreurs, plus de temps pour l'essentiel.",
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
        "tagline": "The clipboard assistant for office workers",
        "intro": "Emails, forms, reports: Pastille keeps a history of everything you copy, pastes it back in one click "
                 "into the window you are working in and masks personal information before it leaves your computer. "
                 "Less retyping, fewer errors, more time for what matters.",
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


def structured_data(lang: str) -> str:
    """Fiche de l'entreprise pour les moteurs de recherche (schema.org, JSON-LD)."""
    h = HOME[lang]
    data = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "@id": f"{SITE_URL}/#organisation",
        "name": COMPANY,
        "legalName": LEGAL_NAME,
        "url": url(PAGES["home"][lang]),
        "logo": f"{SITE_URL}/{LOGO}",
        "image": f"{SITE_URL}/{LOGO}",
        "description": h["intro"],
        "email": EMAIL,
        "address": {"@type": "PostalAddress", "addressLocality": "Québec", "addressRegion": "QC", "addressCountry": "CA"},
        "areaServed": [{"@type": "City", "name": "Québec"}, {"@type": "AdministrativeArea", "name": "Québec"},
                       {"@type": "Country", "name": "Canada"}],
        "knowsLanguage": ["fr-CA", "en-CA"],
        "knowsAbout": ["Microsoft Power Platform", "Power Apps", "Power Automate", "Power BI", "Dynamics 365",
                       "Microsoft Azure", "Dataverse"],
        "hasOfferCatalog": {"@type": "OfferCatalog", "name": h["services_title"], "itemListElement": [
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": title, "description": text}}
            for _, title, text, _ in h["services"]]},
    }
    if SAME_AS:
        data["sameAs"] = SAME_AS
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{payload}\n</script>'


def home_page(lang: str) -> str:
    page = PAGES["home"][lang]
    h = HOME[lang]
    r = lambda p: rel(page, p)
    stats = "".join(f'<div class="stat"><strong>{a}</strong><span>{b}</span></div>' for a, b in h["stats"])
    services = "".join(
        f'<div class="card">{icon(i)}<h3>{title}</h3><p>{text}</p>'
        f'<div class="tags">{"".join(f"<span class=tag>{x}</span>" for x in tags)}</div></div>'
        for i, title, text, tags in h["services"])
    sectors = "".join(f'<div class="sector">{icon(i)}<div><h3>{title}</h3><p>{text}</p></div></div>'
                      for i, title, text in h["sectors"])
    steps = "".join(f"<li><strong>{a}</strong><span>{b}</span></li>" for a, b in h["steps"])
    certs = "".join(f"<li>{c}</li>" for c in h["certs"])
    pillars = "".join(f'<div class="card">{icon(i)}<h3>{a}</h3><p>{b}</p></div>' for i, a, b in h["pillars"])
    mail = f"mailto:{html.escape(EMAIL)}"
    body = f"""
<section class="hero">
  <div class="wrap">
    <p class="eyebrow">{h['eyebrow']}</p>
    <h1>{h['headline']}</h1>
    <p class="lead">{h['intro']}</p>
    <div class="actions">
      <a class="button" href="{mail}">{h['cta']}</a>
      <a class="button secondary" href="#services">{h['cta2']}</a>
    </div>
    <div class="stats">{stats}</div>
  </div>
</section>
<section id="services">
  <div class="wrap">
    <p class="eyebrow">{T[lang]['services']}</p>
    <h2>{h['services_title']}</h2>
    <p class="section-intro">{h['services_intro']}</p>
    <div class="grid">{services}</div>
  </div>
</section>
<section class="alt" id="secteurs">
  <div class="wrap">
    <p class="eyebrow">{T[lang]['sectors']}</p>
    <h2>{h['sectors_title']}</h2>
    <div class="sectors" style="margin-top:24px">{sectors}</div>
  </div>
</section>
<section id="applications">
  <div class="wrap">
    <p class="eyebrow">{T[lang]['apps']}</p>
    <h2>{h['apps_title']}</h2>
    <p class="section-intro">{h['apps_intro']}</p>
    <div class="grid">
      <div class="card app-card wide">
        <img src="{r('assets/pastille.png')}" alt="" width="88" height="88">
        <div>
          <h3>Pastille <span class="status">{h['pastille_status']}</span></h3>
          <p>{h['pastille']}</p>
          <a class="more" href="{r(PAGES['pastille'][lang])}">{h['pastille_more']} →</a>
        </div>
      </div>
      <div class="card cta-card">
        <h3>{h['custom_title']}</h3>
        <p>{h['custom_text']}</p>
        <a class="more" href="{mail}">{h['contact_cta']} →</a>
      </div>
    </div>
  </div>
</section>
<section class="alt" id="a-propos">
  <div class="wrap">
    <p class="eyebrow">{T[lang]['about']}</p>
    <h2>{h['about_title']}</h2>
    <p class="section-intro">{h['about_text']}</p>
    <div class="grid">{pillars}</div>
    <div class="about">
      <div>
        <h3>{h['steps_title']}</h3>
        <ol class="steps">{steps}</ol>
      </div>
      <div class="card">
        <h3>{h['certs_title']}</h3>
        <ul class="certs">{certs}</ul>
      </div>
    </div>
  </div>
</section>
<section class="contact" id="contact">
  <div class="wrap">
    <h2>{h['contact_title']}</h2>
    <p class="lead">{h['contact_text']}</p>
    <div class="actions"><a class="button" href="{mail}">{html.escape(EMAIL)}</a></div>
  </div>
</section>"""
    return layout(lang, "home", page, f"{COMPANY} – {h['title']}", h["intro"], body + structured_data(lang), wrap=False)


def pastille_page(lang: str) -> str:
    page = PAGES["pastille"][lang]
    p, t = PASTILLE[lang], T[lang]
    features = "".join(f"<div class=\"feature\"><h3>{h}</h3><p>{d}</p></div>" for h, d in p["features"])
    head = "".join(f"<th>{c}</th>" for c in p["cols"])
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in p["rows"])
    body = f"""
<section class="page-hero">
  <div class="wrap app-hero">
    <img src="{rel(page, 'assets/pastille.png')}" alt="" width="112" height="112">
    <div>
      <p class="eyebrow">{t['apps']}</p>
      <h1>Pastille</h1>
      <p class="tagline">{p['tagline']}</p>
      <p class="lead">{p['intro']}</p>
      {store_button(lang)}
    </div>
  </div>
</section>
<section><div class="wrap features">{features}</div></section>
<section class="alt">
  <div class="wrap">
    <h2>{p['plans']}</h2>
    <div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
    <p>{p['trial']}</p>
  </div>
</section>
<section>
  <div class="wrap">
    <div class="note">
      <h2>{p['privacy_title']}</h2>
      <p>{p['privacy_text']}</p>
      <p><a href="{rel(page, PAGES['privacy'][lang])}">{t['privacy']}</a> · <a href="{rel(page, PAGES['license'][lang])}">{t['license']}</a></p>
    </div>
    <p class="small">{p['requirements']}</p>
  </div>
</section>"""
    return layout(lang, "pastille", page, f"Pastille – {p['tagline']}", p["intro"], body, wrap=False)


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
<section class="legal">
  <h1>404</h1>
  <p class="lead">{T['fr']['notfound_text']}<br>{T['en']['notfound_text']}</p>
  <p><a href="/">{T['fr']['home']}</a> · <a href="/en/">{T['en']['home']}</a></p>
</section>"""
    return layout("fr", "home", "404.html", f"{T['fr']['notfound']} – {COMPANY}", T["fr"]["notfound"], body) \
        .replace('href="assets/', 'href="/assets/').replace('href="./"', 'href="/"') \
        .replace('href="pastille/', 'href="/pastille/').replace('href="en/', 'href="/en/') \
        .replace('src="assets/', 'src="/assets/').replace('href="./#', 'href="/#')


def write(path: str, content: str):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    print("  ", path)


def main():
    print("Génération du site :")
    (ROOT / "assets").mkdir(exist_ok=True)
    shutil.copyfile(APP_ASSETS / "Square44x44Logo.targetsize-256_altform-unplated.png", ROOT / "assets" / "pastille.png")
    for lang in ("fr", "en"):
        write(PAGES["home"][lang], home_page(lang))
        write(PAGES["pastille"][lang], pastille_page(lang))
        suffix = "fr" if lang == "fr" else "en"
        write(PAGES["privacy"][lang], legal_page(lang, "privacy", f"Privacy.{suffix}.md"))
        write(PAGES["license"][lang], legal_page(lang, "license", f"Eula.{suffix}.md"))
    write("404.html", not_found())
    write("sitemap.xml", sitemap())
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    left = sum(p.read_text(encoding="utf-8").count("<mark>") for p in ROOT.rglob("*.html"))
    if left:
        print(f"Attention : {left} zone(s) [à compléter] encore présente(s) dans les pages juridiques.")


if __name__ == "__main__":
    main()
