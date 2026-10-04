---
slug: s1-ict-first-web-page
language: fr
title: Votre première page web en HTML
summary: Créez une vraie page web avec les balises HTML des titres, des paragraphes, des listes, des liens et des images, et voyez le résultat en direct.
reviewed: false
---
## Qu'est-ce que le HTML ?

Le **HTML** (HyperText Markup Language, ou langage de balisage hypertexte) décrit la *structure* d'une page web. On entoure le contenu de **balises** :

```html
<p>Ceci est un paragraphe.</p>
```

- `<p>` est la **balise ouvrante**, `</p>` la **balise fermante**.
- Tout ce qui se trouve entre les deux est le **contenu**.
- Balises + contenu = un **élément**.

## Le squelette de toute page

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Ma page</title>
  </head>
  <body>
    <!-- tout ce qui s'affiche à l'écran se place ici -->
  </body>
</html>
```

## Les balises courantes

| Balise | Signification |
|---|---|
| `<h1>` … `<h6>` | titres, du plus grand au plus petit |
| `<p>` | paragraphe |
| `<ul>` / `<ol>` avec `<li>` | liste à puces / liste numérotée |
| `<a href="...">` | lien |
| `<img src="..." alt="...">` | image (pas de balise fermante) |
| `<strong>`, `<em>` | texte important, texte mis en valeur |

## Essayez vous-même

Modifiez le code à gauche et appuyez sur **Exécuter**. Remplacez le titre par votre nom, ajoutez un troisième élément à la liste et ajoutez un lien vers votre site web préféré.

```playground html
<!DOCTYPE html>
<html>
  <body>
    <h1>Muraho ! Je m'appelle Aline</h1>
    <p>Je suis élève en <strong>Senior 1</strong> et j'adore les sciences.</p>

    <h2>Mes matières préférées</h2>
    <ul>
      <li>Mathématiques</li>
      <li>TIC</li>
    </ul>

    <p>Visitez le site du <a href="https://www.reb.gov.rw">Rwanda Basic Education Board</a>.</p>
  </body>
</html>
```

## Les attributs

Les informations supplémentaires se placent dans la balise ouvrante sous forme d'**attribut** : `href` indique à un lien où aller ; `alt` décrit une image pour les personnes qui ne peuvent pas la voir — ajoutez-le toujours.

## Les bonnes habitudes

- Indentez les éléments imbriqués pour que votre code soit facile à lire.
- Fermez chaque balise que vous ouvrez (sauf les balises « vides » comme `<img>` et `<br>`).
- Utilisez les titres dans l'ordre : un seul `<h1>`, puis des `<h2>`, et ainsi de suite.

## Testez-vous

1. Quelle balise produit le plus grand titre ?
2. Écrivez le code HTML d'un lien vers `https://www.geogebra.org` avec le texte « GeoGebra ».
3. Pourquoi chaque image doit-elle avoir un attribut `alt` ?
