---
slug: s2-physics-ohms-law
language: fr
title: Intensité du courant, tension et loi d'Ohm
summary: Ce que sont l'intensité du courant et la tension, comment la résistance limite le courant, et comment utiliser V = IR.
reviewed: false
---
## Trois grandeurs

| Grandeur | Symbole | Unité | Mesurée avec | Imaginez-la comme… |
|---|---|---|---|---|
| Intensité du courant | $I$ | ampère (A) | ampèremètre (en **série**) | la quantité de charge qui passe chaque seconde |
| Tension (d.d.p.) | $V$ | volt (V) | voltmètre (en **dérivation**) | la « poussée » donnée aux charges |
| Résistance | $R$ | ohm ($\Omega$) | ohmmètre | la difficulté qu'a la charge à circuler |

Une analogie avec l'eau aide à comprendre : la tension ressemble à la hauteur d'un réservoir d'eau, le courant au débit de l'eau dans le tuyau, et la résistance à une partie étroite du tuyau.

## Loi d'Ohm

Pour un conducteur métallique à température constante, l'intensité du courant est **proportionnelle** à la tension :

$$V = IR$$

En réarrangeant : $I = \dfrac{V}{R}$ et $R = \dfrac{V}{I}$.

**Exemple 1.** Une pile de 6 V fait circuler un courant dans une résistance de 3 Ω. $I = \frac{6}{3} = 2$ A.

**Exemple 2.** Une lampe alimentée sous 12 V est traversée par un courant de 0,5 A. $R = \frac{12}{0.5} = 24\ \Omega$.

## Essayez

Augmentez la tension : que devient l'intensité du courant ? Ensuite, gardez la tension fixe et augmentez la résistance.

```sim
ohms-law-lab
```

## Le graphique V–I

Si l'on trace $V$ en fonction de $I$ pour une résistance, on obtient une **droite passant par l'origine**. La pente est égale à la résistance. Une lampe à filament donne une *courbe*, car sa résistance augmente lorsqu'elle chauffe : une lampe n'obéit donc **pas** à la loi d'Ohm.

## Sécurité

Au Rwanda, la tension du secteur est de 230 V. Même un faible courant qui traverse le corps peut être dangereux. Ne touchez jamais de fils dénudés et n'introduisez jamais d'objets métalliques dans les prises.

## Testez-vous

1. Calculez l'intensité du courant dans une résistance de 10 Ω branchée sur une alimentation de 5 V.
2. Quelle tension faut-il pour faire passer 3 A dans 4 Ω ?
3. Pourquoi branche-t-on un ampèremètre en série ?

*Réponses : 1) 0,5 A · 2) 12 V · 3) pour que tout le courant de cette partie du circuit le traverse*
