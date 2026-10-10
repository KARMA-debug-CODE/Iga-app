---
slug: s3-maths-trigonometric-ratios
language: fr
title: Sinus, cosinus et tangente
summary: Utiliser le sinus, le cosinus et la tangente dans un triangle rectangle pour calculer des côtés et des angles inconnus, y compris des angles d'élévation et de dépression.
reviewed: false
---
## Nommer les côtés

La **trigonométrie** relie les angles d'un triangle aux longueurs de ses côtés. Dans ce chapitre, nous travaillons avec des **triangles rectangles**. Choisissez l'un des deux angles aigus et appelez-le $\theta$ (thêta). Les trois côtés sont alors nommés **par rapport à $\theta$** :

- **Hypoténuse (H) :** le plus long côté, opposé à l'angle droit.
- **Côté opposé (O) :** le côté situé en face de $\theta$.
- **Côté adjacent (A) :** le côté qui touche $\theta$ et qui n'est pas l'hypoténuse.

```text
            P
            |\
            | \
            |  \
  opposé    |   \  hypoténuse
            |    \
            |_    \
            |_|__θ_\
            Q       R
             adjacent
```

Si vous choisissez plutôt l'autre angle aigu, le côté opposé et le côté adjacent s'échangent. L'hypoténuse, elle, ne change jamais.

## Les trois rapports

$$\sin\theta = \frac{\text{côté opposé}}{\text{hypoténuse}} \qquad \cos\theta = \frac{\text{côté adjacent}}{\text{hypoténuse}} \qquad \tan\theta = \frac{\text{côté opposé}}{\text{côté adjacent}}$$

Un moyen mnémotechnique : **SOH CAH TOA** (Sinus = Opposé / Hypoténuse, Cosinus = Adjacent / Hypoténuse, Tangente = Opposé / Adjacent ; on dit aussi « CAH SOH TOA »).

Les rapports dépendent uniquement de l'angle, et non de la taille du triangle, car des triangles semblables ont des côtés proportionnels. L'hypoténuse étant le plus long côté, pour un angle aigu, $\sin\theta$ et $\cos\theta$ sont toujours compris entre 0 et 1. $\tan\theta$ peut être n'importe quel nombre positif.

### Exemple corrigé 1 : écrire les rapports

Un triangle rectangle a des côtés de 5 cm, 12 cm et 13 cm, et $\theta$ est l'angle opposé au côté de 5 cm.

- Hypoténuse $= 13$ (le plus long côté), côté opposé $= 5$, côté adjacent $= 12$.
- $\sin\theta = \frac{5}{13} \approx 0.385$, $\cos\theta = \frac{12}{13} \approx 0.923$ et $\tan\theta = \frac{5}{12} \approx 0.417$.

## Les angles remarquables

Ces valeurs exactes proviennent de la moitié d'un triangle équilatéral (30° et 60°) et de la moitié d'un carré (45°).

| | $30^\circ$ | $45^\circ$ | $60^\circ$ |
|---|---|---|---|
| $\sin\theta$ | $\frac{1}{2}$ | $\frac{\sqrt{2}}{2}$ | $\frac{\sqrt{3}}{2}$ |
| $\cos\theta$ | $\frac{\sqrt{3}}{2}$ | $\frac{\sqrt{2}}{2}$ | $\frac{1}{2}$ |
| $\tan\theta$ | $\frac{\sqrt{3}}{3}$ | $1$ | $\sqrt{3}$ |

Remarquez que $\sin 30^\circ = \cos 60^\circ$. De manière générale, $\sin\theta = \cos(90^\circ - \theta)$.

## Calculer un côté inconnu

1. Nommez les côtés O, A et H à partir de l'angle donné.
2. Choisissez le rapport qui fait intervenir le côté connu et le côté cherché.
3. Remplacez par les valeurs et résolvez. Vérifiez d'abord que votre calculatrice est en **mode degrés** (DEG).

### Exemple corrigé 2 : une échelle

Une échelle de 6 m est appuyée contre le mur d'une maison et forme un angle de $70^\circ$ avec le sol. À quelle hauteur atteint-elle le mur, et à quelle distance du mur se trouve son pied ?

- L'échelle est l'hypoténuse, $H = 6$. La hauteur est le côté opposé à l'angle de $70^\circ$ et la distance au sol est le côté adjacent.
- Hauteur : $\sin 70^\circ = \frac{h}{6}$, donc $h = 6\sin 70^\circ \approx 6 \times 0.9397 \approx 5.64$ m.
- Pied : $\cos 70^\circ = \frac{d}{6}$, donc $d = 6\cos 70^\circ \approx 6 \times 0.3420 \approx 2.05$ m.
- Vérification avec le théorème de Pythagore : $5.64^2 + 2.05^2 \approx 31.81 + 4.20 = 36.01 \approx 6^2$. C'est juste.

### Exemple corrigé 3 : l'inconnue au dénominateur

Un câble en acier soutient un pylône de télécommunication. Il est fixé au pylône à 15 m au-dessus du sol et forme un angle de $58^\circ$ avec le sol. Quelle est la longueur du câble ?

- Le câble est l'hypoténuse $L$, et les 15 m sont le côté opposé à l'angle de $58^\circ$ : on utilise donc le sinus.
- $\sin 58^\circ = \frac{15}{L}$, donc $L = \frac{15}{\sin 58^\circ} \approx \frac{15}{0.8480} \approx 17.69$ m.

## Calculer un angle inconnu

Quand vous connaissez deux côtés, calculez le rapport, puis utilisez la fonction **réciproque** de votre calculatrice : $\sin^{-1}$, $\cos^{-1}$ ou $\tan^{-1}$ (en général, SHIFT puis sin, cos ou tan).

### Exemple corrigé 4 : une route en pente

Un tronçon de route rectiligne qui gravit une colline près de Kigali s'élève de 120 m à la verticale sur une distance horizontale de 1 500 m. Calculez l'angle entre la route et l'horizontale.

- 120 m est le côté opposé à $\theta$ et 1 500 m le côté adjacent : on utilise donc la tangente.
- $\tan\theta = \frac{120}{1\,500} = 0.08$
- $\theta = \tan^{-1}(0.08) \approx 4.6^\circ$

## Angles d'élévation et de dépression

- L'**angle d'élévation** se mesure **vers le haut**, depuis l'horizontale jusqu'à un objet situé au-dessus de vous.
- L'**angle de dépression** se mesure **vers le bas**, depuis l'horizontale jusqu'à un objet situé au-dessous de vous.

L'angle de dépression d'un point P vers un point Q est égal à l'angle d'élévation de Q vers P, car ce sont des angles alternes-internes formés avec deux droites horizontales parallèles.

### Exemple corrigé 5 : la hauteur d'un arbre

Une élève se tient à 25 m du pied d'un eucalyptus, sur un terrain plat. Elle tient un clinomètre à hauteur des yeux, à 1,5 m du sol, et mesure un angle d'élévation de $52^\circ$ pour le sommet de l'arbre. Quelle est la hauteur de l'arbre ?

- Hauteur au-dessus de ses yeux : $\tan 52^\circ = \frac{x}{25}$, donc $x = 25\tan 52^\circ \approx 25 \times 1.2799 \approx 32.0$ m.
- On ajoute la hauteur de ses yeux : $32.0 + 1.5 = 33.5$ m.

### Exemple corrigé 6 : un bateau sur le lac Kivu

Depuis le balcon d'un hôtel situé sur la rive à Rubavu, à 20 m au-dessus de la surface du lac Kivu, l'angle de dépression d'un bateau de pêche est de $12^\circ$. À quelle distance le bateau se trouve-t-il du point situé au bord de l'eau, juste sous le balcon ?

- L'angle d'élévation du bateau vers le balcon est aussi de $12^\circ$. La hauteur de 20 m est le côté opposé et la distance $d$ est le côté adjacent.
- $\tan 12^\circ = \frac{20}{d}$, donc $d = \frac{20}{\tan 12^\circ} \approx \frac{20}{0.2126} \approx 94.1$ m.

## Activité pratique : fabriquer un clinomètre

Fixez avec du ruban adhésif une paille le long du bord droit d'un rapporteur, et suspendez une petite pierre à un fil attaché au trou central. Quand la paille est horizontale, le fil pend à $90^\circ$. Visez le sommet d'un arbre ou du mât du drapeau de l'école à travers la paille : l'angle d'élévation est la différence entre $90^\circ$ et la valeur lue sur le fil. Mesurez à grands pas votre distance au pied de l'objet, puis calculez sa hauteur comme dans l'exemple corrigé 5.

> **Sécurité :** ne regardez jamais le soleil à travers la paille, car cela peut abîmer vos yeux. Travaillez à deux dans l'enceinte de l'école, loin des routes et de la circulation des motos, et ne grimpez ni aux arbres ni sur les murs pour prendre des mesures. Faites attention où vous mettez les pieds sur les pentes et près des fossés de drainage lorsque vous mesurez les distances à grands pas.

## Explorez

Dans Trig Tour, faites glisser le point le long du cercle et observez comment varient les valeurs du sinus, du cosinus et de la tangente. Pour quel angle compris entre $0^\circ$ et $90^\circ$ $\sin\theta$ et $\cos\theta$ sont-ils égaux ?

```sim
phet-trig-tour
```

## Testez-vous

1. Dans un triangle rectangle, l'hypoténuse mesure 20 cm et l'un des angles mesure $30^\circ$. Calculez la longueur du côté opposé à l'angle de $30^\circ$.
2. Le côté opposé et le côté adjacent d'un angle $\theta$ mesurent tous les deux 7 cm. Calculez $\theta$.
3. D'un point situé à 40 m du pied d'un immeuble, sur un terrain plat, l'angle d'élévation du sommet est de $35^\circ$. Calculez la hauteur de l'immeuble, arrondie au dixième.

*Réponses : 1) $20\sin 30^\circ = 20 \times 0.5 = 10$ cm · 2) $\tan\theta = \frac{7}{7} = 1$, donc $\theta = 45^\circ$ · 3) $40\tan 35^\circ \approx 40 \times 0.7002 \approx 28.0$ m*
