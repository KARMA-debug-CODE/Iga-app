---
slug: s4-physics-projectile-motion
language: fr
title: Le mouvement d'un projectile
summary: Décomposer le mouvement en une partie horizontale et une partie verticale pour trouver la durée du vol, la hauteur maximale, la portée et la vitesse d'un objet lancé en biais ou horizontalement.
reviewed: false
---
## L'idée principale

Un **projectile** est un objet lancé, frappé ou projeté en l'air, qui se déplace ensuite sous l'action de la seule pesanteur. Un ballon frappé sur un terrain d'école à Huye, une pierre lancée dans le lac Kivu et l'eau qui sort d'un tuyau d'arrosage sont des projectiles. Dans cette leçon, on néglige la résistance de l'air.

Le chemin suivi par un projectile s'appelle sa **trajectoire**. Sans résistance de l'air, la trajectoire est une courbe appelée **parabole**. L'objet monte, ralentit, passe par un sommet, puis redescend.

L'astuce essentielle de cette leçon est simple : étudier le mouvement **horizontal** et le mouvement **vertical** **séparément**. Ils se produisent en même temps, mais ils n'agissent pas l'un sur l'autre.

- Horizontalement, aucune force n'agit sur le ballon. La vitesse horizontale reste donc **constante**.
- Verticalement, la pesanteur tire le ballon vers le bas. Il existe donc une accélération constante vers le bas, $g = 9.8\ \text{m/s}^2$.

Les deux mouvements n'ont qu'une chose en commun : le **temps**. Le ballon passe le même nombre de secondes à avancer qu'à monter et descendre.

> **Astuce :** lâchez une pierre et lancez-en une autre horizontalement, de la même hauteur et au même instant. Elles touchent le sol plat en même temps. La vitesse horizontale ne change pas la façon dont une pierre tombe.

## Décomposer la vitesse de lancement

Supposons qu'un ballon soit lancé avec une vitesse $u$ et un angle $\theta$ au-dessus de l'horizontale. On divise, ou **décompose**, cette vitesse en deux **composantes** : une horizontale et une verticale.

$$u_x = u\cos\theta \qquad u_y = u\sin\theta$$

Voici un ballon frappé à $u = 20$ m/s avec $\theta = 30^\circ$ :

```text
                  /|
    u = 20 m/s  /  |
              /    | u_y = 20 sin 30°
            /      |     = 10 m/s
          /  30°   |
         +---------+
   u_x = 20 cos 30° = 17,3 m/s
```

Les deux composantes et $u$ forment un triangle rectangle, donc le théorème de Pythagore permet de les vérifier : $\sqrt{17.32^2 + 10^2} = \sqrt{300 + 100} = 20$ m/s, comme prévu.

> Vérifiez que votre calculatrice est en mode **degrés** (elle affiche D ou DEG). Testez-la : $\sin 30^\circ$ doit donner $0.5$.

## Les équations du mouvement, avec les signes

Pour un mouvement en ligne droite avec une accélération constante $a$, trois équations classiques relient la vitesse de départ $u$, la vitesse $v$ au bout d'un temps $t$ et le **déplacement** $s$ (la distance entre l'objet et son point de départ, avec un signe) :

$$v = u + at \qquad s = ut + \tfrac{1}{2}at^2 \qquad v^2 = u^2 + 2as$$

Un projectile se déplace dans deux directions à la fois : on utilise donc ces équations deux fois, une fois horizontalement et une fois verticalement.

Il nous faut d'abord une **convention de signes** : une règle qui dit quel sens est positif. Dans cette leçon, **le haut est positif** et le bas est négatif. La pesanteur est dirigée vers le bas, donc l'accélération verticale vaut $a = -g = -9.8\ \text{m/s}^2$. On mesure les positions $x$ et $y$ à partir du point de lancement.

| | Horizontal ($x$) | Vertical ($y$, le haut est +) |
|---|---|---|
| Accélération | $0$ | $-g$ |
| Vitesse à l'instant $t$ | $v_x = u_x$ (constante) | $v_y = u_y - gt$ |
| Position à l'instant $t$ | $x = u_x t$ | $y = u_y t - \tfrac{1}{2} g t^2$ |
| Sans $t$ | — | $v_y^2 = u_y^2 - 2gy$ |

Par exemple, la position verticale vient de $s = ut + \tfrac{1}{2}at^2$ avec $s = y$, $u = u_y$ et $a = -g$. Tout ce qui suit dans cette leçon vient de ce tableau.

## Trois formules pour un sol horizontal

Lorsque le ballon retombe à la même hauteur que celle de son départ, on peut établir trois formules utiles. Démontrons chacune d'elles étape par étape.

**Durée du vol $T$.** C'est le temps total passé en l'air. Le ballon revient à sa hauteur de départ lorsque $y = 0$. Remplacez $y$ par $0$ et $u_y$ par $u\sin\theta$ dans $y = u_y t - \tfrac{1}{2} g t^2$ :

$$u\sin\theta \, t - \tfrac{1}{2} g t^2 = 0$$

Mettez le facteur commun $t$ en évidence :

$$t\left(u\sin\theta - \tfrac{1}{2} g t\right) = 0$$

Donc soit $t = 0$, qui est l'instant du lancement, soit $u\sin\theta = \tfrac{1}{2} g t$, qui correspond à l'arrivée. Résolvez la seconde égalité pour trouver $t$ : multipliez les deux membres par 2, puis divisez-les par $g$ :

$$T = \frac{2u\sin\theta}{g}$$

**Hauteur maximale $H$.** Au point le plus haut, le ballon cesse de monter pendant un instant, donc $v_y = 0$. Remplacez $v_y$ par $0$, $y$ par $H$ et $u_y^2$ par $u^2\sin^2\theta$ dans $v_y^2 = u_y^2 - 2gy$ :

$$0 = u^2\sin^2\theta - 2gH$$

Ajoutez $2gH$ aux deux membres : $2gH = u^2\sin^2\theta$. Puis divisez les deux membres par $2g$ :

$$H = \frac{u^2 \sin^2\theta}{2g}$$

Le temps pour atteindre le sommet vient de $v_y = u_y - gt$ avec $v_y = 0$. On obtient $0 = u\sin\theta - gt$, donc $t_{\text{sommet}} = \dfrac{u\sin\theta}{g}$. C'est exactement la **moitié** de $T$ : la montée dure autant que la descente.

**Portée $R$.** La **portée** est la distance horizontale parcourue. La vitesse horizontale est constante, donc distance = vitesse × temps :

$$R = u_x \times T = u\cos\theta \times \frac{2u\sin\theta}{g} = \frac{u^2 \times 2\sin\theta\cos\theta}{g}$$

Une identité de trigonométrie dit que $2\sin\theta\cos\theta = \sin 2\theta$. Vérifiez-la avec $\theta = 30^\circ$ : $2 \times 0.5 \times 0.866 = 0.866$, et $\sin 60^\circ = 0.866$ aussi. Donc

$$R = \frac{u^2 \sin 2\theta}{g}$$

> Ces trois formules ne sont valables **que** si le lancement et l'arrivée sont à la même hauteur. Pour une falaise ou une table, revenez au tableau des équations.

### Exemple corrigé 1 : un tir au football à Huye

Un footballeur frappe un ballon à 20 m/s avec un angle de 30° par rapport au sol. Trouvez la durée du vol, la hauteur maximale et la portée. Prenez $g = 9.8\ \text{m/s}^2$.

1. Composantes : $u_x = 20\cos 30^\circ = 17.32$ m/s et $u_y = 20\sin 30^\circ = 10$ m/s.
2. Durée du vol : $T = \dfrac{2 \times 10}{9.8} = \dfrac{20}{9.8} \approx 2.04$ s.
3. Hauteur maximale : $H = \dfrac{20^2 \times 0.5^2}{2 \times 9.8} = \dfrac{100}{19.6} \approx 5.10$ m.
4. Portée : $R = \dfrac{20^2 \times \sin 60^\circ}{9.8} = \dfrac{400 \times 0.866}{9.8} \approx 35.3$ m.
5. Vérification : la portée doit aussi être égale à $u_x \times T = 17.32 \times 2.04 \approx 35.3$ m. C'est juste.

## Quel angle va le plus loin ?

La valeur de $\sin 2\theta$ ne peut jamais dépasser 1. Elle vaut 1 lorsque $2\theta = 90^\circ$. La **portée maximale sur un sol horizontal est donc obtenue à 45°**.

De plus, deux angles dont la somme vaut 90° donnent la **même portée**. Par exemple 30° et 60°, ou 25° et 65°. De tels angles sont dits **complémentaires**. Le tir avec le plus grand angle monte plus haut et reste plus longtemps en l'air, mais il retombe au même endroit.

### Exemple corrigé 2 : le même tir à 60°

Le footballeur frappe de nouveau à 20 m/s, mais cette fois à 60°. Comparez les résultats avec l'exemple corrigé 1.

1. Composantes : $u_x = 20\cos 60^\circ = 10$ m/s et $u_y = 20\sin 60^\circ = 17.32$ m/s.
2. Durée du vol : $T = \dfrac{2 \times 17.32}{9.8} \approx 3.53$ s, plus longue que 2,04 s.
3. Hauteur maximale : $H = \dfrac{17.32^2}{2 \times 9.8} = \dfrac{300}{19.6} \approx 15.3$ m, trois fois plus haut.
4. Portée : $R = \dfrac{400 \times \sin 120^\circ}{9.8} = \dfrac{400 \times 0.866}{9.8} \approx 35.3$ m.
5. Vérification : la portée est la même qu'à 30°, car $30^\circ + 60^\circ = 90^\circ$. C'est juste.

## La vitesse et la position à tout instant

La **vitesse** (au sens de vecteur vitesse) désigne la valeur de la vitesse avec sa direction. À tout instant $t$, la vitesse a deux composantes : $v_x = u_x$, qui ne change jamais, et $v_y = u_y - gt$. Pour obtenir la vitesse réelle, on les combine avec le théorème de Pythagore :

$$v = \sqrt{v_x^2 + v_y^2} \qquad \tan\alpha = \frac{|v_y|}{v_x}$$

Ici, $v$ est la valeur de la vitesse et $\alpha$ est l'angle entre la vitesse et l'horizontale. Les barres dans $|v_y|$ signifient « la valeur de $v_y$ sans son signe ». Si $v_y$ est positive, le ballon monte encore. Si $v_y$ est négative, le ballon descend. Pour trouver l'angle à partir de $\tan\alpha$, utilisez la touche $\tan^{-1}$ de votre calculatrice (souvent SHIFT puis tan).

Tout en haut, $v_y = 0$, mais $v_x$ n'est pas nulle. La vitesse au sommet vaut donc $u\cos\theta$ et elle est horizontale. Elle n'est **pas** nulle.

### Exemple corrigé 3 : le ballon après 1,5 seconde

Reprenez le tir de l'exemple corrigé 1 (20 m/s à 30°). Trouvez la vitesse du ballon 1,5 s après le tir.

1. Horizontalement : $v_x = u_x = 17.32$ m/s.
2. Verticalement : $v_y = 10 - 9.8 \times 1.5 = 10 - 14.7 = -4.7$ m/s. Le signe moins signifie que le ballon se déplace **vers le bas**.
3. Valeur de la vitesse : $v = \sqrt{17.32^2 + 4.7^2} = \sqrt{300 + 22.09} = \sqrt{322.09} \approx 17.9$ m/s.
4. Direction : $\tan\alpha = \dfrac{4.7}{17.32} \approx 0.271$, donc $\alpha = \tan^{-1} 0.271 \approx 15.2^\circ$ sous l'horizontale.
5. Vérification : le ballon atteint le sommet à $t_{\text{sommet}} = \dfrac{10}{9.8} \approx 1.02$ s. À 1,5 s, il a dépassé le sommet, il doit donc descendre, et $v_y$ est bien négative.

### Exemple corrigé 4 : passe-t-il au-dessus de la barre ?

Le même ballon (20 m/s à 30°) est frappé vers un but situé à 30 m. La barre transversale est à 2,44 m de hauteur. Le ballon passe-t-il au-dessus de la barre ?

1. Trouvez quand le ballon atteint la ligne de but. Horizontalement $x = u_x t$, donc $t = \dfrac{30}{17.32} \approx 1.732$ s.
2. Trouvez sa hauteur à cet instant, avec $\tfrac{1}{2} g = \tfrac{1}{2} \times 9.8 = 4.9$ : $y = u_y t - \tfrac{1}{2} g t^2 = 10 \times 1.732 - 4.9 \times 1.732^2$.
3. Comme $1.732^2 = 3.00$, on obtient $y = 17.32 - 14.70 = 2.62$ m.
4. Comparez : 2,62 m est supérieur à 2,44 m, donc le ballon passe environ 0,18 m (18 cm) **au-dessus** de la barre.
5. Vérification : 1,732 s est inférieur à $T = 2.04$ s, donc le ballon est bien encore en l'air lorsqu'il atteint le but.

## Le lancement horizontal

Beaucoup d'objets partent **horizontalement** depuis une certaine hauteur. Pensez à une bille qui roule hors d'une table, ou à une pierre lancée horizontalement du haut d'une falaise. Vous rencontrerez souvent ce type de question.

Pour un lancement horizontal, $\theta = 0^\circ$, donc :

- $u_x = u$, car toute la vitesse est horizontale ;
- $u_y = 0$, car il n'y a pas de vitesse verticale au départ.

L'objet tombe exactement comme une pierre qu'on lâche, tout en avançant à vitesse constante. S'il descend d'une hauteur $h$, alors $y = -h$ (le bas est négatif). L'équation verticale donne

$$-h = 0 - \tfrac{1}{2} g t^2$$

Multipliez les deux membres par $-2$ et divisez par $g$ pour obtenir $t^2 = \dfrac{2h}{g}$. Prenez ensuite la racine carrée :

$$t = \sqrt{\frac{2h}{g}}$$

Une fois $t$ connu, la distance horizontale vaut $x = ut$.

Le point d'arrivée est plus bas que le point de lancement, donc n'utilisez **pas** ici les formules de $T$, $H$ et $R$ pour un sol horizontal.

### Exemple corrigé 5 : une pierre lancée d'une falaise au bord du lac Kivu

Une élève se tient sur une falaise, à 20 m au-dessus de l'eau du lac Kivu. Elle lance une pierre horizontalement à 12 m/s. Trouvez (a) le temps avant que la pierre touche l'eau, (b) à quelle distance de la falaise elle tombe et (c) sa vitesse au moment où elle touche l'eau.

1. Ce que l'on sait : $u_x = 12$ m/s, $u_y = 0$, $y = -20$ m et $g = 9.8\ \text{m/s}^2$.
2. (a) Temps : remplacez $u_y$ par $0$ et $y$ par $-20$ dans $y = u_y t - \tfrac{1}{2} g t^2$. On obtient $-20 = -4.9t^2$, donc $t^2 = \dfrac{20}{4.9} \approx 4.08$ et $t = \sqrt{4.08} \approx 2.02$ s.
3. (b) Distance : $x = u_x t = 12 \times 2.02 \approx 24.2$ m.
4. (c) Vitesse verticale : $v_y = 0 - 9.8 \times 2.02 \approx -19.8$ m/s, vers le bas. La vitesse horizontale vaut toujours 12 m/s.
5. Valeur de la vitesse : $v = \sqrt{12^2 + 19.8^2} = \sqrt{144 + 392} = \sqrt{536} \approx 23.2$ m/s.
6. Direction : $\tan\alpha = \dfrac{19.8}{12} = 1.65$, donc $\alpha = \tan^{-1} 1.65 \approx 58.8^\circ$ sous l'horizontale.
7. Vérification avec l'équation « sans $t$ » : $v_y^2 = 0 - 2 \times 9.8 \times (-20) = 392$, et $\sqrt{392} \approx 19.8$. C'est juste.

## Les vrais ballons et la résistance de l'air

Nos formules négligent la **résistance de l'air** (aussi appelée **traînée**), c'est-à-dire la poussée de l'air contre un objet en mouvement. Les vrais ballons la subissent. Elle les ralentit, donc un vrai ballon retombe en général **moins loin** que ce que prévoit $R$, et il ne monte pas tout à fait aussi haut.

La vraie trajectoire n'est pas non plus une parabole parfaite : la descente est plus raide que la montée. Avec la résistance de l'air, le meilleur angle pour un long lancer est souvent un peu inférieur à 45°.

Pour un objet petit et lourd, comme une pierre, nos formules donnent une bonne estimation. Pour un objet léger, comme une boule de papier, la résistance de l'air compte beaucoup et les formules fonctionnent mal.

## Expérience

Ouvrez le laboratoire ci-dessous et choisissez la pesanteur terrestre.

1. Réglez l'angle sur 30° et la vitesse sur 20 m/s. Appuyez sur **Lancer**. Comparez la durée du vol, la hauteur maximale et la portée avec l'exemple corrigé 1 (2,04 s, 5,10 m et 35,3 m).
2. Changez l'angle pour 60° et lancez de nouveau. La portée est-elle la même ? La trajectoire est-elle plus haute ?
3. Essayez 40°, 45° et 50°. Quel angle va le plus loin ?
4. Revenez à 30° et doublez la vitesse : 40 m/s. Avant de lancer, regardez $u^2$ dans la formule de la portée et prévoyez : la portée double-t-elle ?

```sim
projectile-lab
```

Le laboratoire de projectiles PhET, proposé après la leçon dans « Essayer au labo », permet aussi d'ajouter la résistance de l'air et de comparer les trajectoires.

## Erreurs fréquentes

- **Utiliser $u$ au lieu d'une composante.** Dans les équations verticales, utilisez $u_y = u\sin\theta$. Dans les équations horizontales, utilisez $u_x = u\cos\theta$. Ne mettez jamais la vitesse $u$ entière dans l'une ou l'autre.
- **Confondre le temps de montée et la durée totale.** $t_{\text{sommet}} = \dfrac{u\sin\theta}{g}$ n'est que la moitié de $T = \dfrac{2u\sin\theta}{g}$.
- **Donner à $g$ le mauvais signe.** Avec le haut positif, l'accélération verticale vaut $-9.8\ \text{m/s}^2$. Un ballon qui descend a une $v_y$ négative, et un point situé sous le point de lancement a un $y$ négatif.
- **Laisser la calculatrice en radians.** En mode radians, $\sin 30$ donne $-0.988$ au lieu de $0.5$, et toutes les réponses suivantes sont fausses.
- **Dire que la vitesse est nulle au sommet.** Seule la composante verticale est nulle. Le ballon avance toujours horizontalement à $u\cos\theta$.
- **Utiliser $T$, $H$ et $R$ pour une falaise ou une table.** Ces formules exigent que le lancement et l'arrivée soient à la même hauteur.

## Testez-vous

1. Une pierre est lancée à 15 m/s avec un angle de 45°. Calculez sa portée ($g = 9.8$).
2. Quel angle de lancement donne la même portée que 20° ?
3. Quelle est la vitesse verticale d'un projectile en son point le plus haut ? Quelle est sa vitesse horizontale à cet endroit ?
4. Un ballon est lancé à 14 m/s avec un angle de 30° sur un sol horizontal. Trouvez (a) la durée de son vol et (b) sa hauteur maximale.
5. Pour le ballon de la question 4, trouvez la valeur et la direction de sa vitesse 1,0 s après le lancer.
6. Un garçon lance une balle horizontalement à 5 m/s depuis une fenêtre située à 4,9 m au-dessus du sol. Combien de temps la balle met-elle pour toucher le sol, et à quelle distance du mur tombe-t-elle ?
7. Un ballon frappé à 20 m/s avec un angle de 30° a une portée d'environ 35,3 m. Quelle est sa portée s'il est frappé à 40 m/s avec le même angle ?

*Réponses : 1) $R = \frac{15^2 \times \sin 90^\circ}{9.8} = \frac{225}{9.8} \approx 23.0$ m · 2) 70°, car $20^\circ + 70^\circ = 90^\circ$ · 3) la vitesse verticale est nulle ; la vitesse horizontale vaut toujours $u\cos\theta$, donc la balle n'est pas au repos · 4) $u_y = 14 \sin 30^\circ = 7$ m/s, donc (a) $T = \frac{2 \times 7}{9.8} \approx 1.43$ s et (b) $H = \frac{7^2}{2 \times 9.8} = \frac{49}{19.6} = 2.5$ m · 5) $v_x = 14\cos 30^\circ \approx 12.1$ m/s et $v_y = 7 - 9.8 \times 1.0 = -2.8$ m/s, donc $v = \sqrt{12.1^2 + 2.8^2} \approx 12.4$ m/s à environ 13,0° sous l'horizontale · 6) $t = \sqrt{\frac{2 \times 4.9}{9.8}} = 1.0$ s et $x = 5 \times 1.0 = 5.0$ m · 7) environ 141 m : doubler la vitesse rend la portée quatre fois plus grande, car $R$ dépend de $u^2$, donc $R \approx 4 \times 35.3 \approx 141$ m*
