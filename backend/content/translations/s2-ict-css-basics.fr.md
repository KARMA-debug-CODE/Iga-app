---
slug: s2-ict-css-basics
language: fr
title: Mettre en forme des pages web avec CSS
summary: Utilisez les sélecteurs CSS, les couleurs, les polices, les espacements et le modèle de boîte pour donner une belle apparence au HTML.
reviewed: false
---
## Le HTML pour la structure, le CSS pour le style

Le **CSS** (Cascading Style Sheets, ou feuilles de style en cascade) contrôle l'apparence du HTML : couleurs, polices, tailles, espacements et mise en page.

Une **règle** CSS comporte un **sélecteur** et des **déclarations** :

```css
h1 {
  color: #00A1DE;
  font-size: 32px;
}
```

- `h1` est le sélecteur (les éléments à mettre en forme).
- `color: #00A1DE;` est une déclaration : une **propriété** et une **valeur**.

## Trois types de sélecteurs

| Sélecteur | Exemple | Sélectionne |
|---|---|---|
| élément | `p { }` | chaque `<p>` |
| classe | `.card { }` | chaque élément ayant `class="card"` |
| id | `#header { }` | l'unique élément ayant `id="header"` |

## Le modèle de boîte

Chaque élément est une boîte formée de quatre couches, de l'intérieur vers l'extérieur :

**contenu (content) → marge intérieure (padding) → bordure (border) → marge extérieure (margin)**

```css
.card {
  padding: 16px;          /* espace à l'intérieur de la bordure */
  border: 2px solid #20603D;
  margin: 12px;           /* espace à l'extérieur de la bordure */
  border-radius: 12px;    /* coins arrondis */
}
```

## Essayez

La page ci-dessous utilise les couleurs du drapeau rwandais. Changez les couleurs, arrondissez davantage les cartes et ajoutez un effet au survol.

```playground html
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: system-ui, sans-serif; background: #f5f7fb; padding: 20px; }
  h1 { color: #00A1DE; }
  .card {
    background: white;
    border-left: 6px solid #FAD201;
    padding: 16px;
    margin-bottom: 12px;
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,.08);
  }
  .card:hover { border-left-color: #20603D; }
  .tag { background: #20603D; color: white; padding: 2px 8px; border-radius: 999px; font-size: 12px; }
</style>
</head>
<body>
  <h1>Plan de révision</h1>
  <div class="card"><span class="tag">Maths</span> S'entraîner sur les graphiques de droites</div>
  <div class="card"><span class="tag">Physique</span> Réviser la loi d'Ohm</div>
</body>
</html>
```

## Couleurs

Vous pouvez écrire les couleurs avec leur nom (`red`), avec un code hexadécimal (`#FAD201`) ou avec `rgb(250, 210, 1)`.

## Testez-vous

1. Écrivez une règle qui affiche chaque paragraphe en gris et en 18 px.
2. Quelle est la différence entre padding (marge intérieure) et margin (marge extérieure) ?
3. Comment sélectionner tous les éléments ayant `class="note"` ?
