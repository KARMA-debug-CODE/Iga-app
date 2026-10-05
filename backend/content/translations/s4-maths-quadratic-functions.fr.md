---
slug: s4-maths-quadratic-functions
language: fr
title: Les fonctions du second degré et leurs paraboles
summary: L'allure de y = ax² + bx + c, la recherche du sommet, de l'axe de symétrie et des racines.
reviewed: false
---
## La forme générale

Une **fonction du second degré** (ou fonction polynôme de degré 2) s'écrit sous la forme

$$f(x) = ax^2 + bx + c, \qquad a \neq 0$$

Sa courbe représentative est une **parabole**.

- Si $a > 0$, la parabole est tournée **vers le haut** (un « sourire ») et admet un **minimum**.
- Si $a < 0$, elle est tournée **vers le bas** (une « grimace ») et admet un **maximum**.

## Axe de symétrie et sommet

La parabole est symétrique par rapport à la droite verticale

$$x = -\frac{b}{2a}$$

Le **sommet** se trouve sur cette droite. Substituez $x = -\frac{b}{2a}$ dans l'expression de $f$ pour trouver son ordonnée ($y$).

**Exemple.** Pour $f(x) = x^2 - 4x + 3$ : $a = 1$, $b = -4$, donc l'axe est $x = 2$ et $f(2) = 4 - 8 + 3 = -1$. Le sommet est $(2, -1)$ ; c'est un minimum.

## Racines (points d'intersection avec l'axe des abscisses)

Les racines sont les solutions de $ax^2 + bx + c = 0$. Utilisez la **formule générale** :

$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

Le **discriminant** $\Delta = b^2 - 4ac$ indique le nombre de racines :

| $\Delta$ | racines | courbe |
|---|---|---|
| $\Delta > 0$ | deux racines réelles distinctes | coupe l'axe des $x$ en deux points |
| $\Delta = 0$ | une racine double | touche l'axe des $x$ en son sommet |
| $\Delta < 0$ | aucune racine réelle | ne rencontre jamais l'axe des $x$ |

Pour $x^2 - 4x + 3$ : $\Delta = 16 - 12 = 4 > 0$, et $x = \frac{4 \pm 2}{2}$, donc $x = 1$ ou $x = 3$.

## Explorez

Sélectionnez **Second degré** ci-dessous. Gardez $b = 0$ et $c = 0$, puis faites varier $a$ ; ensuite, faites varier $c$ seul ; enfin, $b$ seul. Décrivez dans votre cahier l'effet de chaque coefficient.

```sim
function-grapher
```

## Forme canonique

En complétant le carré, on obtient $f(x) = a(x - h)^2 + k$, où $(h, k)$ est le sommet.

$$x^2 - 4x + 3 = (x - 2)^2 - 1$$

## Testez-vous

1. La fonction $y = -2x^2 + 8x - 5$ admet-elle un maximum ou un minimum ? Trouvez le sommet.
2. Combien de racines réelles l'équation $x^2 + 2x + 5 = 0$ admet-elle ?
3. Écrivez $x^2 + 6x + 1$ sous forme canonique.

*Réponses : 1) un maximum en $(2, 3)$ · 2) aucune ($\Delta = -16$) · 3) $(x+3)^2 - 8$*
