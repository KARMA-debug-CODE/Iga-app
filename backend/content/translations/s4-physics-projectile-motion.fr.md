---
slug: s4-physics-projectile-motion
language: fr
title: Le mouvement d'un projectile
summary: Décomposer le mouvement en une partie horizontale et une partie verticale pour trouver la durée du vol, la hauteur maximale et la portée.
reviewed: false
---
## L'idée principale

Un **projectile** est un objet lancé en l'air qui se déplace ensuite sous l'action de la seule pesanteur (on néglige la résistance de l'air). Sa trajectoire est une **parabole**.

L'astuce essentielle : étudier les mouvements **horizontal** et **vertical** **séparément**.

- Horizontalement, aucune force n'agit, donc la vitesse est **constante**.
- Verticalement, il existe une accélération constante dirigée vers le bas, $g \approx 9.8\ \text{m/s}^2$.

## Décomposer la vitesse de lancement

Une balle lancée avec une vitesse $u$ et un angle $\theta$ au-dessus de l'horizontale a pour composantes

$$u_x = u\cos\theta \qquad u_y = u\sin\theta$$

## Les équations (lancement et arrivée à la même hauteur)

**Durée du vol :** la balle monte puis redescend lorsque $u_y t - \tfrac{1}{2} g t^2 = 0$ :

$$T = \frac{2u\sin\theta}{g}$$

**Hauteur maximale :** au sommet, la vitesse verticale est nulle :

$$H = \frac{u^2 \sin^2\theta}{2g}$$

**Portée :** distance horizontale $= u_x \times T$ :

$$R = \frac{u^2 \sin 2\theta}{g}$$

Comme $\sin 2\theta$ est maximal lorsque $2\theta = 90^\circ$, la **portée maximale est obtenue à 45°**. Deux angles dont la somme vaut 90° (par exemple 30° et 60°) donnent la **même portée**.

## Exemple corrigé

Un ballon de football est frappé à 20 m/s avec un angle de 30° par rapport au sol. Prenez $g = 9.8\ \text{m/s}^2$.

- $T = \dfrac{2 \times 20 \times \sin 30^\circ}{9.8} = \dfrac{20}{9.8} \approx 2.04$ s
- $H = \dfrac{20^2 \times 0.5^2}{2 \times 9.8} = \dfrac{100}{19.6} \approx 5.10$ m
- $R = \dfrac{20^2 \times \sin 60^\circ}{9.8} \approx \dfrac{400 \times 0.866}{9.8} \approx 35.3$ m

## Expérience

Utilisez le laboratoire virtuel pour vérifier l'exemple corrigé, puis répondez : quel angle donne la plus grande portée ? Doubler la vitesse double-t-il la portée ?

```sim
projectile-lab
```

## Testez-vous

1. Une pierre est lancée à 15 m/s avec un angle de 45°. Calculez sa portée ($g = 9.8$).
2. Quel angle de lancement donne la même portée que 20° ?
3. Quelle est la vitesse verticale d'un projectile en son point le plus haut ?

*Réponses : 1) environ 23,0 m · 2) 70° · 3) elle est nulle*
