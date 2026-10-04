---
slug: s5-maths-differentiation
language: fr
title: "La dérivation : pentes et taux de variation"
summary: La dérivée mesure la rapidité avec laquelle une fonction varie ; apprenez les règles de dérivation et utilisez-les pour les tangentes, les taux de variation et les valeurs maximales ou minimales.
reviewed: false
---
## Qu'est-ce qu'une dérivée ?

Sur une droite, la pente (le coefficient directeur) est la même partout. Sur une courbe, la pente change d'un point à l'autre. La **pente d'une courbe en un point** est la pente de la **tangente** en ce point : la droite qui touche tout juste la courbe en ce point.

La **dérivée** de $f(x)$, notée $f'(x)$ ou $\dfrac{dy}{dx}$, est une nouvelle fonction qui donne cette pente pour chaque valeur de $x$. C'est aussi le **taux de variation** de $y$ par rapport à $x$. Le calcul de la dérivée s'appelle la **dérivation**.

## La dérivée à partir de la définition

Prenons deux points de la courbe, $P\big(x, f(x)\big)$ et $Q\big(x+h, f(x+h)\big)$. La pente de la corde $PQ$ est $\dfrac{f(x+h)-f(x)}{h}$. Lorsque $Q$ glisse vers $P$, $h \to 0$ et la corde devient la tangente. Ainsi

$$f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$$

On utilise ici les limites étudiées dans l'unité 1.

### Exemple corrigé 1 : à partir de la définition

Trouvez $f'(x)$ pour $f(x) = x^2 + 3x$.

1. $f(x+h) = (x+h)^2 + 3(x+h) = x^2 + 2xh + h^2 + 3x + 3h$
2. $f(x+h) - f(x) = 2xh + h^2 + 3h$
3. On divise par $h$ : $\dfrac{2xh + h^2 + 3h}{h} = 2x + h + 3$
4. On fait tendre $h \to 0$ : $f'(x) = 2x + 3$

Donc, en $x = 1$, la pente de la courbe vaut $2(1) + 3 = 5$.

## Règles de dérivation

La définition fonctionne toujours, mais elle est longue à appliquer. Les règles suivantes en découlent toutes :

| Fonction $y$ | Dérivée $\dfrac{dy}{dx}$ |
|---|---|
| $c$ (une constante) | $0$ |
| $x^n$ | $nx^{n-1}$ |
| $k\,f(x)$ | $k\,f'(x)$ |
| $f(x) + g(x)$ | $f'(x) + g'(x)$ |
| $\sin x$ | $\cos x$ |
| $\cos x$ | $-\sin x$ |

Pour $\sin x$ et $\cos x$, l'angle $x$ doit être exprimé en **radians**.

Pour les produits, les quotients et les fonctions composées, on utilise :

- **Dérivée d'un produit :** $\dfrac{d}{dx}(uv) = u'v + uv'$
- **Dérivée d'un quotient :** $\dfrac{d}{dx}\left(\dfrac{u}{v}\right) = \dfrac{u'v - uv'}{v^2}$
- **Dérivée d'une fonction composée :** si $y = f(u)$ et $u = g(x)$, alors $\dfrac{dy}{dx} = \dfrac{dy}{du} \times \dfrac{du}{dx}$

Exemples rapides :

- $y = (2x+1)(x^2 - 3)$ : $\;y' = 2(x^2-3) + (2x+1)(2x) = 2x^2 - 6 + 4x^2 + 2x = 6x^2 + 2x - 6$
- $y = \dfrac{x+1}{x-1}$ : $\;y' = \dfrac{(1)(x-1) - (x+1)(1)}{(x-1)^2} = \dfrac{-2}{(x-1)^2}$
- $y = (3x^2+1)^4$ : posons $u = 3x^2 + 1$, alors $y' = 4u^3 \times 6x = 24x(3x^2+1)^3$

### Exemple corrigé 2 : pente et tangente

Trouvez l'équation de la tangente à $y = 4x^3 - 5x^2 + 7x - 2$ en $x = 1$.

1. On dérive terme à terme : $\dfrac{dy}{dx} = 12x^2 - 10x + 7$
2. Pente en $x = 1$ : $m = 12 - 10 + 7 = 9$
3. Point de la courbe : $y = 4 - 5 + 7 - 2 = 4$, donc le point est $(1, 4)$
4. Tangente : $y - 4 = 9(x - 1)$, ce qui donne $y = 9x - 5$

## Taux de variation

Si $s$ est une distance en mètres et $t$ un temps en secondes, alors $\dfrac{ds}{dt}$ est la **vitesse**. Une moto passe devant un arrêt à Nyabugogo et accélère, de sorte que $t$ secondes plus tard, sa distance à l'arrêt vaut $s = t^2 + 4t$. Sa vitesse est

$$v = \frac{ds}{dt} = 2t + 4$$

elle passe donc devant l'arrêt à $v = 4$ m/s, et 3 secondes plus tard $v = 2(3) + 4 = 10$ m/s, soit 36 km/h.

## Points stationnaires

En un **point stationnaire**, la tangente est horizontale, donc $f'(x) = 0$. La **dérivée seconde** $f''(x)$ indique la nature de ce point :

- $f''(x) > 0$ : un point **minimum** (la courbe est tournée vers le haut)
- $f''(x) < 0$ : un point **maximum** (la courbe est tournée vers le bas)
- $f''(x) = 0$ : il faut poursuivre l'étude (il peut s'agir d'un point d'inflexion)

Pour $f(x) = x^3 - 3x^2 - 9x + 5$ :

- $f'(x) = 3x^2 - 6x - 9 = 3(x-3)(x+1)$, donc $x = 3$ ou $x = -1$
- $f''(x) = 6x - 6$
- $f''(3) = 12 > 0$ et $f(3) = 27 - 27 - 27 + 5 = -22$ : minimum en $(3, -22)$
- $f''(-1) = -12 < 0$ et $f(-1) = -1 - 3 + 9 + 5 = 10$ : maximum en $(-1, 10)$

### Exemple corrigé 3 : le plus grand enclos

Un éleveur de Nyagatare dispose de 120 m de clôture pour construire un enclos rectangulaire pour ses vaches contre un grand mur rectiligne ; seuls trois côtés doivent donc être clôturés. Quelles dimensions donnent la plus grande aire ?

1. Soit $x$ m la longueur de chacun des côtés perpendiculaires au mur. Le côté parallèle au mur mesure $120 - 2x$ m.
2. Aire : $A = x(120 - 2x) = 120x - 2x^2$
3. $\dfrac{dA}{dx} = 120 - 4x = 0$ donne $x = 30$
4. $\dfrac{d^2A}{dx^2} = -4 < 0$, il s'agit donc d'un maximum.
5. Dimensions : 30 m sur $120 - 2(30) = 60$ m. Aire maximale $= 30 \times 60 = 1800$ m².

Les problèmes d'optimisation comme celui-ci aident les agriculteurs, les constructeurs et les entreprises à tirer le meilleur parti de matériaux ou d'un budget limités.

## Explorez

Dans GeoGebra, tapez `f(x) = x^3 - 3x^2 - 9x + 5`, puis `Derivative(f)` pour tracer $f'(x)$ dans le même repère. Où la courbe de $f'$ coupe-t-elle l'axe des abscisses ? Comparez ces valeurs de $x$ avec les abscisses des extremums de $f$.

```sim
geogebra-graphing
```

## Testez-vous

1. Dérivez $y = 5x^4 - 2x + 8$.
2. Trouvez la pente de $y = x^2 - 6x$ au point d'abscisse $x = 4$.
3. Trouvez le point stationnaire de $y = x^2 - 8x + 3$ et dites s'il s'agit d'un maximum ou d'un minimum.

*Réponses : 1) $\frac{dy}{dx} = 20x^3 - 2$ · 2) $\frac{dy}{dx} = 2x - 6$, donc la pente vaut $2(4) - 6 = 2$ · 3) $\frac{dy}{dx} = 2x - 8 = 0$ donne $x = 4$ et $y = 16 - 32 + 3 = -13$ ; $\frac{d^2y}{dx^2} = 2 > 0$, donc $(4, -13)$ est un minimum*
