---
slug: s2-maths-linear-graphs
language: fr
title: Représentation graphique d'une droite, y = mx + c
summary: Lire le coefficient directeur et l'ordonnée à l'origine directement dans une équation, et tracer une droite sans tableau de valeurs.
reviewed: false
---
## L'équation d'une droite

Toute droite (sauf les droites verticales) peut s'écrire sous la forme

$$y = mx + c$$

- $m$ est le **coefficient directeur**, ou pente (l'inclinaison de la droite),
- $c$ est l'**ordonnée à l'origine** (l'endroit où la droite coupe l'axe des $y$).

## La pente

La pente, c'est « la montée divisée par l'avancée » :

$$m = \frac{\text{variation de } y}{\text{variation de } x} = \frac{y_2 - y_1}{x_2 - x_1}$$

- $m > 0$ : la droite **monte** de gauche à droite.
- $m < 0$ : la droite **descend**.
- $m = 0$ : la droite est **horizontale**.

**Exemple.** Calculez la pente de la droite qui passe par $(1, 3)$ et $(4, 9)$.

$$m = \frac{9 - 3}{4 - 1} = \frac{6}{3} = 2$$

## Essayez : déplacez les curseurs

Choisissez **Linear** (linéaire) dans le traceur ci-dessous. Modifiez $m$ et $c$ et observez ce qui se passe. Pouvez-vous obtenir une droite qui descend et coupe l'axe des $y$ en $-2$ ?

```sim
function-grapher
```

## Tracer rapidement une droite

Pour tracer $y = 2x - 1$ :

1. Placez le point d'intersection avec l'axe des ordonnées, $(0, -1)$.
2. À partir de ce point, avancez de **1 vers la droite et montez de 2** (car $m = 2$), puis placez $(1, 1)$.
3. Reliez les points à la règle et prolongez la droite.

## Droites parallèles

Des droites de **même pente** sont parallèles. $y = 3x + 1$ et $y = 3x - 4$ ne se coupent jamais.

## Dans la vie courante

Un moto-taxi facture un montant fixe de 300 FRW, plus 200 FRW par kilomètre. Le coût est

$$C = 200d + 300$$

La pente (200) est le prix par km ; l'ordonnée à l'origine (300) est le prix de départ.

## Testez-vous

1. Donnez la pente et l'ordonnée à l'origine de $y = -4x + 7$.
2. Calculez la pente de la droite qui passe par $(-2, 5)$ et $(2, -3)$.
3. Laquelle de ces droites est parallèle à $y = 5x$ : $y = x + 5$, $y = 5x - 2$, $y = -5x$ ?

*Réponses : 1) $m=-4$, $c=7$ · 2) $-2$ · 3) $y = 5x - 2$*
