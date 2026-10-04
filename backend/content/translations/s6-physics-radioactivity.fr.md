---
slug: s6-physics-radioactivity
language: fr
title: La radioactivité et les désintégrations nucléaires
summary: Pourquoi certains noyaux sont instables, les propriétés des rayonnements alpha, bêta et gamma, les équations de désintégration, et la loi de décroissance exponentielle avec la demi-vie.
reviewed: false
---
## Le noyau

Tout atome possède un **noyau** minuscule et dense, constitué de protons et de neutrons, appelés ensemble **nucléons**. Un nucléide s'écrit

$${}^{A}_{Z}\text{X}$$

- $Z$ = **nombre de protons** (numéro atomique), qui détermine l'élément ;
- $A$ = **nombre de nucléons** (nombre de masse) = protons + neutrons ;
- nombre de neutrons $N = A - Z$.

Les **isotopes** sont des atomes d'un même élément qui ont des nombres de neutrons différents, par exemple ${}^{12}_{6}\text{C}$ (6 neutrons) et ${}^{14}_{6}\text{C}$ (8 neutrons).

L'**interaction nucléaire forte** maintient les nucléons ensemble malgré la répulsion électrique entre les protons. Un noyau qui a trop ou trop peu de neutrons par rapport à son nombre de protons est **instable**. Tous les très gros noyaux, qui ont plus de 82 protons, sont eux aussi instables.

Construisez quelques noyaux dans la simulation. Gardez le nombre de protons fixe et ajoutez ou retirez des neutrons : à quel moment la simulation indique-t-elle que le noyau est instable ?

```sim
phet-build-an-atom
```

## La radioactivité

Un noyau instable devient plus stable en émettant un rayonnement. C'est la **désintégration radioactive**. Elle est :

- **spontanée** : elle n'est influencée ni par la température, ni par la pression, ni par les combinaisons chimiques ;
- **aléatoire** : on ne peut pas prévoir quand un noyau donné va se désintégrer, seulement la fraction d'un grand nombre de noyaux qui se désintégrera pendant une durée donnée.

## Les rayonnements alpha, bêta et gamma

| Propriété | Alpha (α) | Bêta moins (β⁻) | Gamma (γ) |
|---|---|---|---|
| Nature | noyau d'hélium, ${}^{4}_{2}\text{He}$ | électron rapide, ${}^{0}_{-1}e$ | onde électromagnétique (photon) |
| Charge | $+2e$ | $-e$ | 0 |
| Pouvoir ionisant | fort | moyen | faible |
| Arrêté par | une feuille de papier ou quelques cm d'air | quelques mm d'aluminium | intensité réduite par plusieurs cm de plomb ou un béton épais |
| Dévié par les champs électriques et magnétiques ? | oui | oui, dans le sens opposé et plus fortement | non |

## Les équations de désintégration

Dans toute équation nucléaire, le **nombre de nucléons** et le **nombre de protons** (la charge) sont tous deux conservés : les totaux de $A$ et de $Z$ sont les mêmes des deux côtés.

**Désintégration alpha :** $A$ diminue de 4 et $Z$ diminue de 2.

$${}^{238}_{92}\text{U} \rightarrow {}^{234}_{90}\text{Th} + {}^{4}_{2}\text{He}$$

**Désintégration bêta moins :** un neutron du noyau se transforme en un proton, un électron et un antineutrino, ${}^{1}_{0}n \rightarrow {}^{1}_{1}p + {}^{0}_{-1}e + \bar{\nu}$. Ainsi, $A$ ne change pas et $Z$ augmente de 1.

$${}^{14}_{6}\text{C} \rightarrow {}^{14}_{7}\text{N} + {}^{0}_{-1}e + \bar{\nu}$$

**Émission gamma :** le noyau perd un excès d'énergie. $A$ et $Z$ ne changent pas. Les rayons gamma accompagnent souvent une désintégration alpha ou bêta.

### Exemple corrigé 1 : une famille radioactive

Le thorium 232 (${}^{232}_{90}\text{Th}$) se désintègre en plomb 208 stable (${}^{208}_{82}\text{Pb}$) par une série de désintégrations alpha et bêta moins. Combien y en a-t-il de chaque type ?

- Seule la désintégration alpha modifie $A$. Diminution de $A = 232 - 208 = 24$, donc le nombre de désintégrations alpha $= \dfrac{24}{4} = 6$.
- Six désintégrations alpha font baisser $Z$ de $6 \times 2 = 12$, ce qui donne $90 - 12 = 78$.
- Or le plomb a $Z = 82$. Chaque désintégration bêta moins augmente $Z$ de 1, donc le nombre de désintégrations bêta $= 82 - 78 = 4$.

**Réponse : 6 désintégrations alpha et 4 désintégrations bêta moins.**

## L'activité et la loi de décroissance

L'**activité** $A$ d'un échantillon est le nombre de noyaux qui se désintègrent par seconde ; elle se mesure en **becquerels** (1 Bq = 1 désintégration par seconde). Elle est proportionnelle au nombre $N$ de noyaux non encore désintégrés (ne confondez pas cette activité $A$ avec le nombre de nucléons $A$) :

$$A = \lambda N$$

où $\lambda$ est la **constante radioactive** (s⁻¹), c'est-à-dire la probabilité par seconde qu'un noyau se désintègre. Comme $\dfrac{dN}{dt} = -\lambda N$, le nombre de noyaux diminue de façon **exponentielle** :

$$N = N_0 e^{-\lambda t} \qquad A = A_0 e^{-\lambda t}$$

La **demi-vie** $T_{1/2}$ est la durée nécessaire pour que la moitié des noyaux radioactifs d'un échantillon se désintègrent, de sorte que le nombre de noyaux non désintégrés (et l'activité) tombe à la moitié de sa valeur initiale :

$$T_{1/2} = \frac{\ln 2}{\lambda} \approx \frac{0.693}{\lambda} \qquad N = N_0\left(\tfrac{1}{2}\right)^{t/T_{1/2}}$$

| Nucléide | Demi-vie | Utilisation |
|---|---|---|
| Iode 131 | 8 jours | traitement des maladies de la thyroïde |
| Phosphore 32 | 14,3 jours | traceur dans l'étude des plantes et des engrais |
| Cobalt 60 | 5,3 ans | radiothérapie, stérilisation du matériel médical |
| Américium 241 | 432 ans | détecteurs de fumée |
| Carbone 14 | 5730 ans | datation de matières organiques anciennes |

### Exemple corrigé 2 : une livraison à l'hôpital

Un hôpital de Kigali reçoit un échantillon d'iode 131 dont l'activité est de 640 MBq. Sa demi-vie est de 8 jours. Quelle est son activité au bout de 24 jours ?

Nombre de demi-vies $= \dfrac{24}{8} = 3$.

$$640 \rightarrow 320 \rightarrow 160 \rightarrow 80\ \text{MBq}$$

Vérification : $640 \times \left(\tfrac{1}{2}\right)^3 = \dfrac{640}{8} = 80$ MBq.

### Exemple corrigé 3 : constante radioactive et activité

Le radon 222 a une demi-vie de 3,82 jours. Calculez sa constante radioactive, ainsi que l'activité d'un échantillon contenant $1.0 \times 10^{10}$ noyaux de radon.

Demi-vie en secondes : $3.82 \times 24 \times 3600 = 330\,048 \approx 3.30 \times 10^{5}$ s

$$\lambda = \frac{0.693}{3.30 \times 10^{5}} = 2.10 \times 10^{-6}\ \text{s}^{-1}$$

$$A = \lambda N = 2.10 \times 10^{-6} \times 1.0 \times 10^{10} = 2.1 \times 10^{4}\ \text{Bq}$$

### Exemple corrigé 4 : la datation au carbone 14

Les êtres vivants conservent une proportion constante de carbone 14. Après la mort, le carbone 14 se désintègre. Un morceau de charbon de bois ancien trouvé dans une grotte présente 30 % de l'activité en carbone 14 d'un bois frais. Quel est son âge ?

$$0.30 = e^{-\lambda t} \quad\Rightarrow\quad t = \frac{\ln(1/0.30)}{\lambda} = T_{1/2} \times \frac{\ln(1/0.30)}{\ln 2}$$

$$t = 5730 \times \frac{1.2040}{0.6931} = 5730 \times 1.737 \approx 9950\ \text{ans}$$

## Utilisations et radioactivité naturelle

Les radio-isotopes servent à traiter le cancer, à stériliser les seringues, et comme **traceurs** : des chercheurs en agronomie peuvent ajouter un peu de phosphore 32 à un engrais et mesurer à quelle vitesse des plants de haricots de Musanze l'absorbent.

Nous sommes tous exposés à un faible **rayonnement ambiant** (la radioactivité naturelle) provenant des roches et du sol, du radon, des aliments, des radiographies médicales et des rayons cosmiques. Le rayonnement cosmique est plus intense en altitude : un alpiniste sur le mont Karisimbi (4507 m) reçoit donc plus de rayonnement cosmique qu'un pêcheur sur le lac Kivu (environ 1460 m).

## Sécurité

Les rayonnements ionisants peuvent endommager les cellules vivantes et l'ADN. Dans un laboratoire scolaire :

- seul l'enseignant manipule les sources scellées, toujours à l'aide de longues **pinces**, en les tenant à bout de bras et sans jamais les diriger vers quelqu'un ;
- rangez les sources dans leur **boîte doublée de plomb** lorsqu'elles ne sont pas utilisées ;
- respectez les trois règles : **réduire le temps** d'exposition, **augmenter la distance**, utiliser un **écran de protection** ;
- ne mangez et ne buvez jamais au laboratoire, et lavez-vous les mains après la séance de travaux pratiques.

## Testez-vous

1. Un radio-isotope a une demi-vie de 6 heures. Quelle fraction en reste-t-il au bout d'une journée ?
2. Complétez l'équation ${}^{210}_{84}\text{Po} \rightarrow \text{Pb} + {}^{4}_{2}\text{He}$ en donnant $A$ et $Z$ pour le plomb.
3. Quel rayonnement est le plus pénétrant, et qu'utilise-t-on pour l'absorber ?

*Réponses : 1) 24 h correspondent à 4 demi-vies, donc $\left(\tfrac{1}{2}\right)^4 = \tfrac{1}{16}$ · 2) ${}^{206}_{82}\text{Pb}$ ($210 - 4 = 206$, $84 - 2 = 82$) · 3) le rayonnement gamma ; on l'atténue avec une épaisse couche de plomb ou de béton*
