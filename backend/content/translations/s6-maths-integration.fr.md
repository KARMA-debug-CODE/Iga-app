---
slug: s6-maths-integration
language: fr
title: L'intégration et ses applications
summary: L'intégration est l'opération inverse de la dérivation ; utilisez-la pour trouver des primitives, calculer des intégrales définies, ainsi que des aires, des distances et des volumes.
reviewed: false
---
## L'opération inverse de la dérivation

Si $F'(x) = f(x)$, alors $F(x)$ est une **primitive** de $f(x)$. Par exemple, $\dfrac{d}{dx}(x^3) = 3x^2$, donc $x^3$ est une primitive de $3x^2$. Mais $x^3 + 5$ et $x^3 - 100$ en sont aussi, car la dérivée d'une constante est nulle. On écrit donc l'**intégrale indéfinie** sous la forme

$$\int f(x)\,dx = F(x) + C$$

où $C$ est la **constante d'intégration**. La recherche d'une primitive s'appelle l'**intégration**.

## Intégrales usuelles

| $f(x)$ | $\int f(x)\,dx$ |
|---|---|
| $k$ (une constante) | $kx + C$ |
| $x^n$, avec $n \neq -1$ | $\dfrac{x^{n+1}}{n+1} + C$ |
| $\dfrac{1}{x}$ | $\ln \lvert x \rvert + C$ |
| $e^x$ | $e^x + C$ |
| $\cos x$ | $\sin x + C$ |
| $\sin x$ | $-\cos x + C$ |

L'intégration est **linéaire** : l'intégrale d'une somme est la somme des intégrales, et un facteur constant peut être sorti de l'intégrale, $\int k\,f(x)\,dx = k\int f(x)\,dx$.

### Exemple corrigé 1 : une intégrale indéfinie

Calculez $\int (6x^2 - 4x + 5)\,dx$.

1. On augmente chaque exposant de un et on divise par le nouvel exposant : $\dfrac{6x^3}{3} - \dfrac{4x^2}{2} + 5x$
2. On simplifie et on ajoute la constante : $2x^3 - 2x^2 + 5x + C$
3. On vérifie en dérivant : $6x^2 - 4x + 5$, la fonction de départ.

## L'intégration par changement de variable

Lorsque la fonction à intégrer contient une fonction et (un multiple de) sa dérivée, on pose une nouvelle variable. Pour $\int 2x(x^2+3)^4\,dx$, posons $u = x^2 + 3$ ; alors $\dfrac{du}{dx} = 2x$ et $du = 2x\,dx$ :

$$\int 2x(x^2+3)^4\,dx = \int u^4\,du = \frac{u^5}{5} + C = \frac{(x^2+3)^5}{5} + C$$

## Les intégrales définies

Le **théorème fondamental de l'analyse** affirme que si $F$ est une primitive quelconque de $f$, alors

$$\int_a^b f(x)\,dx = \Big[F(x)\Big]_a^b = F(b) - F(a)$$

La constante $C$ s'élimine lors de la soustraction ; on ne l'écrit donc pas. Les nombres $a$ et $b$ sont les **bornes** d'intégration.

## L'aire sous une courbe

Si $f(x) \ge 0$ pour $a \le x \le b$, alors $\int_a^b f(x)\,dx$ est l'aire du domaine limité par la courbe, l'axe des abscisses et les droites $x = a$ et $x = b$.

### Exemple corrigé 2 : l'aire sous une courbe

Calculez l'aire comprise entre $y = x^2 + 1$, l'axe des abscisses, $x = 0$ et $x = 3$.

$$\int_0^3 (x^2 + 1)\,dx = \left[\frac{x^3}{3} + x\right]_0^3 = \left(\frac{27}{3} + 3\right) - (0 + 0) = 9 + 3 = 12$$

L'aire vaut **12 unités d'aire**.

### Attention : les domaines situés sous l'axe

Là où une courbe est située **sous** l'axe des abscisses, l'intégrale définie est **négative**. Pour $y = x^2 - 4x$ entre $x = 0$ et $x = 4$ :

$$\int_0^4 (x^2 - 4x)\,dx = \left[\frac{x^3}{3} - 2x^2\right]_0^4 = \frac{64}{3} - 32 = -\frac{32}{3}$$

L'aire est la valeur positive, $\dfrac{32}{3} \approx 10.67$ unités d'aire. Si un domaine est situé en partie au-dessus et en partie au-dessous de l'axe, intégrez chaque partie séparément et additionnez les valeurs des aires.

L'aire **comprise entre deux courbes**, lorsque $f(x) \ge g(x)$ sur $[a, b]$, vaut $\int_a^b \big(f(x) - g(x)\big)\,dx$.

## La distance à partir de la vitesse

La vitesse est la dérivée du déplacement ; le déplacement est donc l'intégrale de la vitesse :

$$s = \int_{t_1}^{t_2} v\,dt$$

### Exemple corrigé 3 : une moto qui démarre au feu

Une moto-taxi démarre à un feu de circulation à Kicukiro. Pendant les 5 premières secondes, sa vitesse est $v = 3t - 0.3t^2$ m/s. Quelle distance parcourt-elle pendant ce temps ?

$$s = \int_0^5 (3t - 0.3t^2)\,dt = \Big[1.5t^2 - 0.1t^3\Big]_0^5 = 1.5(25) - 0.1(125) = 37.5 - 12.5 = 25$$

Elle parcourt **25 m**. Sa vitesse à $t = 5$ est $v = 3(5) - 0.3(25) = 15 - 7.5 = 7.5$ m/s, soit 27 km/h.

## Les volumes de révolution

Lorsqu'on fait tourner le domaine situé sous $y = f(x)$, de $x = a$ à $x = b$, d'un angle de $360^\circ$ autour de l'axe des abscisses, on engendre un solide de volume

$$V = \pi \int_a^b y^2\,dx$$

Par exemple, la rotation de $y = \sqrt{x}$ de $x = 0$ à $x = 4$ donne un **paraboloïde** plein, qui a la même forme courbe qu'une antenne parabolique. Ici $y^2 = x$ :

$$V = \pi \int_0^4 x\,dx = \pi \left[\frac{x^2}{2}\right]_0^4 = \pi \times \frac{16}{2} = 8\pi \approx 25.13 \text{ unités de volume}$$

Les ingénieurs utilisent la même idée pour calculer la capacité des réservoirs d'eau aux formes courbes et la quantité de béton d'un pilier courbe.

## Explorez

Dans GeoGebra, tapez `Integral(x^2 + 1, 0, 3)` pour colorier l'aire de l'exemple corrigé 2 et vérifier qu'elle vaut 12. Essayez ensuite `Integral(x^2 - 4x, 0, 4)` et remarquez que la valeur obtenue est négative.

```sim
geogebra-graphing
```

## Testez-vous

1. Calculez $\int (3x^2 + 2)\,dx$.
2. Calculez $\int_1^2 4x^3\,dx$.
3. Calculez l'aire comprise entre $y = 2x$, l'axe des abscisses et les droites $x = 0$ et $x = 5$.

*Réponses : 1) $x^3 + 2x + C$ · 2) $\big[x^4\big]_1^2 = 16 - 1 = 15$ · 3) $\big[x^2\big]_0^5 = 25 - 0 = 25$ unités d'aire (vérification avec le triangle : $\frac{1}{2} \times 5 \times 10 = 25$)*
