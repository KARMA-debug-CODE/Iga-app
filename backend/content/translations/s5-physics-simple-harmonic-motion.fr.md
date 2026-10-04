---
slug: s5-physics-simple-harmonic-motion
language: fr
title: Le mouvement harmonique simple
summary: Définir le MHS par a = −ω²x, puis déterminer la période, la vitesse et l'énergie d'une masse suspendue à un ressort et d'un pendule simple.
reviewed: false
---
## Les oscillations autour de nous

Un enfant sur une balançoire dans une aire de jeux de Kigali, une moto-taxi qui rebondit sur ses ressorts le long d'une piste en murram, une corde de guitare : tous **oscillent**, c'est-à-dire qu'ils effectuent des allers-retours autour d'une **position d'équilibre** fixe.

Le type d'oscillation le plus simple et le plus important est le **mouvement harmonique simple (MHS)**.

## Définition

> Un corps est animé d'un mouvement harmonique simple lorsque son accélération est **directement proportionnelle** à son déplacement par rapport à un point fixe et est toujours **dirigée vers** ce point.

$$a = -\omega^2 x$$

- $x$ est l'élongation, c'est-à-dire le déplacement par rapport à la position d'équilibre (m).
- $\omega$ est la **pulsation** (rad/s), une constante pour ce mouvement.
- Le signe moins indique que l'accélération est toujours dirigée **vers** la position d'équilibre.

La pulsation est liée à la fréquence $f$ et à la période $T$ par

$$\omega = 2\pi f = \frac{2\pi}{T}$$

## Élongation, vitesse et accélération

Si l'on déclenche le chronomètre au moment où le corps est lâché sans vitesse depuis son **amplitude** $A$ (l'élongation maximale), alors

$$x = A\cos\omega t$$

La vitesse pour une élongation $x$ quelconque est

$$v = \pm\,\omega\sqrt{A^2 - x^2}$$

On en déduit :

- la vitesse maximale $v_{\max} = \omega A$, à la position d'équilibre ($x = 0$) ;
- l'accélération maximale $a_{\max} = \omega^2 A$, aux positions extrêmes ($x = \pm A$).

| Position | Élongation | Vitesse | Accélération | Énergie cinétique | Énergie potentielle |
|---|---|---|---|---|---|
| Équilibre | 0 | maximale, $\omega A$ | 0 | maximale | minimale |
| Extrêmes | $\pm A$ | 0 | maximale, $\omega^2 A$ | 0 | maximale |

## Deux oscillateurs importants

### Masse suspendue à un ressort

Un ressort obéit à la loi de Hooke : lorsqu'une masse $m$ est écartée de $x$, la force de rappel vaut $F = -kx$, où $k$ est la raideur du ressort (N/m). D'après la deuxième loi de Newton :

$$ma = -kx \quad\Rightarrow\quad a = -\frac{k}{m}x$$

Cette relation est de la forme $a = -\omega^2 x$ : le mouvement est donc un MHS avec $\omega^2 = \dfrac{k}{m}$ et

$$T = 2\pi\sqrt{\frac{m}{k}}$$

### Pendule simple

Une petite masse $m$ est suspendue à un fil léger de longueur $L$. Pour de petits angles (moins de 10° environ), la force de rappel vaut approximativement $-\dfrac{mg}{L}x$, donc $a = -\dfrac{g}{L}x$. C'est un MHS avec $\omega^2 = \dfrac{g}{L}$ et

$$T = 2\pi\sqrt{\frac{L}{g}}$$

La période d'un pendule ne dépend **pas** de la masse suspendue ni (pour de petites oscillations) de l'amplitude. Une horloge à pendule transportée au sommet du mont Karisimbi (4507 m) retarderait légèrement, car $g$ y est un peu plus faible, si bien que $T$ y est un peu plus longue.

| | Masse suspendue à un ressort | Pendule simple |
|---|---|---|
| Force de rappel | $-kx$ | $-\frac{mg}{L}x$ (petits angles) |
| $\omega^2$ | $\frac{k}{m}$ | $\frac{g}{L}$ |
| Période | $2\pi\sqrt{m/k}$ | $2\pi\sqrt{L/g}$ |
| Dépend de la masse ? | oui | non |

## L'énergie dans un MHS

En l'absence de frottements, l'énergie totale reste constante. Elle se convertit sans cesse d'énergie cinétique (Ec) en énergie potentielle (Ep), et inversement :

$$E = \tfrac{1}{2}kA^2 = \tfrac{1}{2}m\omega^2 A^2$$

$$\text{Ep} = \tfrac{1}{2}kx^2 \qquad \text{Ec} = \tfrac{1}{2}k\left(A^2 - x^2\right)$$

## Exemple corrigé 1 : une masse suspendue à un ressort

Une masse de 0,50 kg est suspendue à un ressort de raideur $k = 200$ N/m. On la tire vers le bas de 4,0 cm, puis on la lâche.

**Pulsation :** $\omega = \sqrt{\dfrac{k}{m}} = \sqrt{\dfrac{200}{0.50}} = \sqrt{400} = 20$ rad/s

**Période :** $T = \dfrac{2\pi}{\omega} = \dfrac{2\pi}{20} \approx 0.314$ s, donc $f = \dfrac{1}{0.314} \approx 3.18$ Hz

**Vitesse maximale :** $v_{\max} = \omega A = 20 \times 0.040 = 0.80$ m/s

**Accélération maximale :** $a_{\max} = \omega^2 A = 400 \times 0.040 = 16$ m/s²

**Énergie totale :** $E = \tfrac{1}{2}kA^2 = 0.5 \times 200 \times 0.040^2 = 0.16$ J

Vérification : $\tfrac{1}{2}mv_{\max}^2 = 0.5 \times 0.50 \times 0.80^2 = 0.16$ J. ✓

**Vitesse lorsque $x = 2.0$ cm :**

$$v = 20\sqrt{0.040^2 - 0.020^2} = 20\sqrt{0.0012} \approx 20 \times 0.0346 \approx 0.69\ \text{m/s}$$

En ce point, Ep $= 0.5 \times 200 \times 0.020^2 = 0.04$ J et Ec $= 0.16 - 0.04 = 0.12$ J.

## Exemple corrigé 2 : mesurer g à Musanze

Une élève de Musanze installe un pendule de longueur 0,80 m. Elle chronomètre 20 oscillations complètes et obtient 36,0 s.

**Période :** $T = \dfrac{36.0}{20} = 1.80$ s

**On transforme** $T = 2\pi\sqrt{L/g}$ pour obtenir $g = \dfrac{4\pi^2 L}{T^2}$ :

$$g = \frac{4\pi^2 \times 0.80}{1.80^2} = \frac{31.58}{3.24} \approx 9.75\ \text{m/s}^2$$

Chronométrer 20 oscillations au lieu d'une seule réduit l'effet du temps de réaction humain. Pour obtenir un meilleur résultat, recommencez avec plusieurs longueurs, tracez $T^2$ en fonction de $L$ et utilisez $g = \dfrac{4\pi^2}{\text{pente}}$.

## Amortissement et résonance

Dans la réalité, les frottements et la résistance de l'air dissipent de l'énergie, si bien que l'amplitude diminue lentement. C'est l'**amortissement**. Les amortisseurs des bus et des motos-taxis sont conçus pour amortir rapidement les rebonds des ressorts sur les routes cahoteuses.

Si l'on pousse un système à sa propre fréquence naturelle, l'amplitude devient très grande. C'est la **résonance**. Vous l'utilisez lorsque vous poussez une balançoire exactement aux bons moments.

## Enquêtez

Utilisez le laboratoire du pendule. Modifiez la masse, puis la longueur, puis l'amplitude, et notez la période à chaque fois. Quel changement modifie la période ?

```sim
phet-pendulum-lab
```

## Sécurité au laboratoire

- Fixez solidement le support (statif) à la paillasse à l'aide d'une pince, ou posez un objet lourd sur son socle, pour qu'il ne puisse pas basculer.
- N'étirez pas les ressorts au-delà de leur limite d'élasticité : un ressort trop étiré peut revenir brusquement. Portez des lunettes de protection lorsque vous chargez des ressorts.
- Éloignez vos pieds des masses suspendues et gardez de petites oscillations pour que la masse du pendule ne heurte personne.

## Testez-vous

1. Calculez la période d'une masse de 2,0 kg qui oscille au bout d'un ressort de raideur $k = 50$ N/m.
2. On multiplie par 4 la longueur d'un pendule. Que devient sa période ?
3. À quel endroit d'une oscillation harmonique simple la vitesse est-elle maximale et l'accélération nulle ?

*Réponses : 1) $T = 2\pi\sqrt{2.0/50} = 2\pi \times 0.2 \approx 1.26$ s · 2) elle double, car $T \propto \sqrt{L}$ et $\sqrt{4} = 2$ · 3) à la position d'équilibre ($x = 0$)*
