---
slug: s3-maths-quadratic-equations
language: fr
title: Résoudre des équations du second degré
summary: Résoudre ax² + bx + c = 0 par factorisation, en complétant le carré et à l'aide de la formule générale, puis utiliser les équations du second degré pour résoudre des problèmes concrets.
reviewed: false
---
## Qu'est-ce qu'une équation du second degré ?

Une **équation du second degré** est une équation dans laquelle la plus grande puissance de l'inconnue est 2. Sa **forme générale** est

$$ax^2 + bx + c = 0, \qquad a \neq 0$$

où $a$, $b$ et $c$ sont des nombres. Par exemple :

- $x^2 - 9 = 0$ a pour coefficients $a = 1$, $b = 0$, $c = -9$.
- $2x^2 + 3x - 5 = 0$ a pour coefficients $a = 2$, $b = 3$, $c = -5$.
- $x^2 = 4x$ est aussi une équation du second degré : on la réécrit sous la forme $x^2 - 4x = 0$.

Les valeurs de $x$ qui rendent l'égalité vraie sont ses **solutions** ou **racines**. Une équation du second degré a **au plus deux** racines réelles.

**Règle d'or :** commencez toujours par écrire l'équation sous sa forme générale (tous les termes d'un côté, $0$ de l'autre).

## Méthode 1 : la factorisation

La factorisation utilise la **règle du produit nul** :

$$\text{si } p \times q = 0, \text{ alors } p = 0 \text{ ou } q = 0$$

Si l'on écrit l'expression du second degré comme le produit de deux parenthèses, chaque parenthèse donne donc une racine. Pour factoriser $x^2 + bx + c$, cherchez deux nombres dont le **produit vaut $c$** et dont la **somme vaut $b$**.

### Exemple corrigé 1

Résolvez $x^2 - 5x - 14 = 0$.

- Il nous faut deux nombres de produit $-14$ et de somme $-5$. Essayons les couples : $1$ et $-14$ (somme $-13$), $2$ et $-7$ (somme $-5$) ✓.
- Donc $(x + 2)(x - 7) = 0$.
- Soit $x + 2 = 0$, ce qui donne $x = -2$, soit $x - 7 = 0$, ce qui donne $x = 7$.
- Vérification : $7^2 - 5(7) - 14 = 49 - 35 - 14 = 0$ ✓ et $(-2)^2 - 5(-2) - 14 = 4 + 10 - 14 = 0$ ✓.

Deux cas particuliers reviennent souvent :

- **Facteur commun :** $x^2 - 4x = 0$ donne $x(x - 4) = 0$, donc $x = 0$ ou $x = 4$. Ne divisez jamais les deux membres par $x$ : vous perdriez la racine $x = 0$.
- **Différence de deux carrés :** $x^2 - 9 = 0$ donne $(x - 3)(x + 3) = 0$, donc $x = 3$ ou $x = -3$.

## Méthode 2 : compléter le carré

Cette méthode utilise l'identité $(x + p)^2 = x^2 + 2px + p^2$. Lorsque $a = 1$, on ajoute $\left(\frac{b}{2}\right)^2$ aux deux membres.

### Exemple corrigé 2

Résolvez $x^2 + 6x - 7 = 0$.

- Faites passer la constante à droite : $x^2 + 6x = 7$.
- La moitié de $6$ est $3$, et $3^2 = 9$. Ajoutez $9$ aux deux membres : $x^2 + 6x + 9 = 16$.
- Le membre de gauche est un carré parfait : $(x + 3)^2 = 16$.
- Prenez la racine carrée des deux membres : $x + 3 = \pm 4$.
- Donc $x = -3 + 4 = 1$ ou $x = -3 - 4 = -7$.

## Méthode 3 : la formule générale

En complétant le carré dans l'équation générale $ax^2 + bx + c = 0$, on obtient la **formule générale** de résolution :

$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

Elle fonctionne toujours, même lorsque l'expression ne se factorise pas facilement.

### Exemple corrigé 3

Résolvez $2x^2 + 3x - 5 = 0$.

- Ici $a = 2$, $b = 3$, $c = -5$.
- $b^2 - 4ac = 3^2 - 4(2)(-5) = 9 + 40 = 49$.
- $x = \dfrac{-3 \pm \sqrt{49}}{2(2)} = \dfrac{-3 \pm 7}{4}$.
- Donc $x = \dfrac{4}{4} = 1$ ou $x = \dfrac{-10}{4} = -2.5$.

### Exemple corrigé 4 : des solutions avec des radicaux

Résolvez $x^2 - 4x - 1 = 0$. Donnez les valeurs exactes, puis des valeurs approchées à 2 décimales.

- $a = 1$, $b = -4$, $c = -1$, donc $b^2 - 4ac = 16 + 4 = 20$.
- $x = \dfrac{4 \pm \sqrt{20}}{2} = \dfrac{4 \pm 2\sqrt{5}}{2} = 2 \pm \sqrt{5}$.
- Comme $\sqrt{5} \approx 2.236$ : $x \approx 4.24$ ou $x \approx -0.24$.

## Combien de racines ? Le discriminant

L'expression $b^2 - 4ac$ placée sous la racine carrée s'appelle le **discriminant**. Son signe vous indique combien il y a de racines réelles, avant même de résoudre l'équation.

| Valeur de $b^2 - 4ac$ | Nombre de racines réelles |
|---|---|
| positive | deux racines distinctes |
| nulle | une racine double |
| négative | aucune racine réelle |

Par exemple, pour $x^2 + 4x + 7 = 0$, on a $b^2 - 4ac = 16 - 28 = -12$, qui est négatif : l'équation n'a donc aucune racine réelle.

## Quelle méthode choisir ?

| Méthode | À privilégier quand… |
|---|---|
| Factorisation | les nombres sont petits et l'on repère vite le couple de facteurs |
| Compléter le carré | $a = 1$ et $b$ est pair |
| Formule générale | pour toute équation du second degré, surtout lorsque les racines ne sont pas des nombres entiers |

## Résoudre des problèmes avec des équations du second degré

### Exemple corrigé 5

Un agriculteur de Musanze possède une parcelle rectangulaire de pommes de terre. Sa longueur dépasse sa largeur de 5 m et son aire est de 84 m². Trouvez ses dimensions. La clôture coûte 1 500 FRW le mètre : combien coûtera la clôture de la parcelle ?

- Soit $w$ la largeur en mètres ; la longueur est alors $w + 5$ mètres.
- Aire : $w(w + 5) = 84$, donc $w^2 + 5w - 84 = 0$.
- Deux nombres de produit $-84$ et de somme $5$ : $12$ et $-7$. Donc $(w + 12)(w - 7) = 0$.
- $w = -12$ ou $w = 7$. Une largeur ne peut pas être négative, donc $w = 7$ m et la longueur est de $12$ m. Vérification : $7 \times 12 = 84$ ✓.
- Périmètre $= 2(7 + 12) = 38$ m. Coût $= 38 \times 1\,500 = 57\,000$ FRW.

Demandez-vous toujours si chaque racine a un sens dans la situation réelle, et rejetez celles qui n'en ont pas.

## Voir les racines sur un graphique

Les racines de $ax^2 + bx + c = 0$ sont les valeurs de $x$ pour lesquelles la courbe de $y = ax^2 + bx + c$ coupe l'axe des $x$. Choisissez **Quadratic** (fonction du second degré) dans le traceur de courbes et réglez $a = 1$, $b = -1$, $c = -6$. Vérifiez que les racines sont $-2$ et $3$, car $x^2 - x - 6 = (x + 2)(x - 3)$. Augmentez ensuite lentement $c$. À partir de quand la courbe ne rencontre-t-elle plus l'axe des $x$, et quel est alors le signe du discriminant ?

```sim
function-grapher
```

## Testez-vous

1. Résolvez $x^2 + x - 20 = 0$ par factorisation.
2. Résolvez $3x^2 - 5x - 2 = 0$ à l'aide de la formule générale.
3. Sans résoudre, combien de racines réelles l'équation $x^2 + 3x + 5 = 0$ a-t-elle ?

*Réponses : 1) $(x + 5)(x - 4) = 0$, donc $x = -5$ ou $x = 4$ · 2) $b^2 - 4ac = 25 + 24 = 49$ et $x = \frac{5 \pm 7}{6}$, donc $x = 2$ ou $x = -\frac{1}{3}$ · 3) aucune, car $b^2 - 4ac = 9 - 20 = -11 < 0$*
