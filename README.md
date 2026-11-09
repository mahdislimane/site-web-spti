# Site de Solutions Passerelle TI

Site statique (HTML/CSS, sans dépendance) publié avec **GitHub Pages** sur **https://solutionspasserelleti.ca**.

| Page | Adresse |
|---|---|
| Accueil | `/` · `/en/` |
| Pastille | `/pastille/` · `/en/pastille/` |
| Politique de confidentialité (à donner au Microsoft Store) | `/pastille/confidentialite.html` · `/en/pastille/privacy.html` |
| Contrat de licence | `/pastille/contrat.html` · `/en/pastille/license.html` |

## Modifier le site

Les pages sont générées par `build.py` (textes en haut du fichier). Les pages juridiques sont produites à partir de
`../copyManager/Legal/*.md` : la même source que l'application, donc toujours identiques.

```
python build.py
```

En haut de `build.py`, à compléter : `EMAIL` (courriel affiché) et `STORE_URL` (lien de la fiche Store, une fois
Pastille publiée ; sinon le bouton affiche « Bientôt sur le Microsoft Store »). Le script signale les zones `[…]`
encore à remplir dans les textes juridiques (surlignées en jaune sur le site).

Ouvrir `index.html` dans le navigateur pour vérifier, puis publier : `git add -A`, `git commit`, `git push`.
GitHub met le site à jour en une minute environ.

## Mise en ligne (une seule fois)

### 1. Dépôt GitHub
1. Créer un dépôt **public** nommé `site-web-spti` sur https://github.com/new (compte `mahdislimane`) ; GitHub Pages gratuit exige un dépôt public.
2. Dans ce dossier :
   ```
   git add -A
   git commit -m "Site initial"
   git remote add origin https://github.com/mahdislimane/site-web-spti.git
   git push -u origin main
   ```
3. Dépôt › **Settings › Pages** : *Source* = « Deploy from a branch », branche `main`, dossier `/ (root)`.

### 2. Vérifier le domaine (protège contre le détournement du domaine)
Photo de profil › **Settings › Pages › Add a domain** : `solutionspasserelleti.ca`. GitHub affiche un
enregistrement TXT à créer chez le registraire (nom `_github-pages-challenge-mahdislimane`), puis **Verify**.

### 3. DNS chez le registraire du domaine
Supprimer d'abord les enregistrements A/AAAA/CNAME existants sur `@` et `www` (page de « parking »), puis ajouter :

| Type | Nom (hôte) | Valeur |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| AAAA | `@` | `2606:50c0:8000::153` |
| AAAA | `@` | `2606:50c0:8001::153` |
| AAAA | `@` | `2606:50c0:8002::153` |
| AAAA | `@` | `2606:50c0:8003::153` |
| CNAME | `www` | `mahdislimane.github.io` |

Ne pas toucher aux enregistrements **MX** (courriel) s'il y en a.

### 4. Domaine personnalisé et HTTPS
Dépôt › **Settings › Pages › Custom domain** : `solutionspasserelleti.ca` (le fichier `CNAME` du dépôt le contient
déjà), **Save**. Quand la vérification DNS est verte (de quelques minutes à 24 h), cocher **Enforce HTTPS**
(le certificat peut prendre jusqu'à une heure). `www.solutionspasserelleti.ca` redirige alors vers le domaine principal.

Vérifier depuis Windows :
```
nslookup solutionspasserelleti.ca
nslookup www.solutionspasserelleti.ca
```

### 5. Microsoft Store
Dans Partner Center, adresse de la politique de confidentialité :
`https://solutionspasserelleti.ca/pastille/confidentialite.html` (fiche fr-CA) et
`https://solutionspasserelleti.ca/en/pastille/privacy.html` (fiche en-US) ; site web : `https://solutionspasserelleti.ca`.
