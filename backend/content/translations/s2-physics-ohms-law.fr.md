---
slug: s2-physics-ohms-law
language: fr
title: Intensité du courant, tension et loi d'Ohm
summary: Ce que sont la charge, l'intensité du courant et la tension, comment la résistance limite le courant, comment utiliser V = IR avec des mA et des kΩ, et comment trouver une résistance à partir d'un tableau ou d'un graphique.
reviewed: false
---
## La charge électrique et le courant

Tout ce qui vous entoure contient de minuscules particules qui portent une **charge électrique**. Dans un fil métallique, certaines de ces particules, appelées **électrons**, peuvent se déplacer librement. Lorsqu'elles avancent toutes dans le même sens le long du fil, on a un courant électrique.

La charge se mesure en **coulombs** (C). Un coulomb, c'est beaucoup de charge : c'est la charge d'environ six milliards de milliards d'électrons.

L'**intensité du courant** est la quantité de charge qui passe en un point du circuit chaque seconde. Son symbole est $I$ et son unité est l'**ampère** (A). Un courant de 1 A signifie que 1 coulomb passe chaque seconde.

$$I = \frac{Q}{t} \qquad \text{ou} \qquad Q = It$$

Ici, $Q$ est la charge en coulombs et $t$ est le temps en **secondes**.

On mesure l'intensité du courant avec un **ampèremètre**. Il se branche **en série** : on ouvre le circuit et on place l'ampèremètre dans l'ouverture, pour que tout le courant le traverse.

### Exemple corrigé 1 : une lampe torche restée allumée

L'ampoule d'une lampe torche est traversée par un courant de 0,5 A pendant 2 minutes. Quelle charge traverse l'ampoule ?

1. Écrivez ce que vous savez : $I = 0.5$ A et $t = 2$ minutes.
2. Convertissez le temps en secondes : $t = 2 \times 60 = 120$ s.
3. Utilisez $Q = It$ : $Q = 0.5 \times 120 = 60$ C.
4. Vérification : $\dfrac{60\ \text{C}}{120\ \text{s}} = 0.5$ A, c'est bien le courant de départ ✓.

## La tension : l'énergie de chaque coulomb

Une pile ne fabrique pas de charge. La charge se trouve déjà dans les fils. La pile donne de l'**énergie** à la charge et la pousse dans le circuit. La charge cède ensuite cette énergie à l'ampoule, à la radio ou au ventilateur.

La **tension**, aussi appelée **différence de potentiel** (d.d.p.), indique combien d'énergie porte chaque coulomb. L'énergie se mesure en **joules** (J). La tension se mesure en **volts** (V) :

$$1\ \text{V} = 1\ \text{joule par coulomb}$$

Ainsi, une batterie de 12 V donne 12 J d'énergie à chaque coulomb qui la traverse. Si 60 C la traversent, elle fournit $12 \times 60 = 720$ J.

On mesure la tension avec un **voltmètre**. Il se branche **en dérivation** : ses deux fils sont reliés aux deux bornes du composant, un de chaque côté. Il compare l'énergie de la charge avant et après le composant.

## La résistance et la loi d'Ohm

La **résistance** indique à quel point il est difficile pour le courant de traverser un composant. Son symbole est $R$ et son unité est l'**ohm** ($\Omega$). Une grande résistance ne laisse passer qu'un faible courant.

Voici les trois grandeurs côte à côte :

| Grandeur | Symbole | Unité | Mesurée avec | Imaginez-la comme… |
|---|---|---|---|---|
| Intensité du courant | $I$ | ampère (A) | ampèremètre (en **série**) | la quantité de charge qui passe chaque seconde |
| Tension (d.d.p.) | $V$ | volt (V) | voltmètre (en **dérivation**) | l'énergie donnée à chaque coulomb |
| Résistance | $R$ | ohm ($\Omega$) | ohmmètre | la difficulté qu'a la charge à circuler |

Une analogie avec l'eau aide à comprendre. La tension ressemble à la hauteur d'un réservoir d'eau, le courant au débit de l'eau dans le tuyau, et la résistance à une partie étroite du tuyau.

Dans les années 1820, le scientifique allemand Georg Ohm a trouvé une règle simple. Pour un fil métallique maintenu à **température constante**, l'intensité du courant est **proportionnelle** à la tension. Cela veut dire que si l'on double la tension, l'intensité double aussi. Si on la triple, l'intensité triple. Cette règle est la **loi d'Ohm** :

$$V = IR$$

Ici, $V$ est en volts, $I$ en ampères et $R$ en ohms. Un composant qui obéit à la loi d'Ohm est appelé **conducteur ohmique**.

## Réarranger V = IR

On peut trouver n'importe laquelle des trois grandeurs si l'on connaît les deux autres. Utilisez l'algèbre :

- Pour trouver $I$, divisez les deux membres de $V = IR$ par $R$ : $I = \dfrac{V}{R}$.
- Pour trouver $R$, divisez les deux membres de $V = IR$ par $I$ : $R = \dfrac{V}{I}$.

Certains élèves utilisent un **triangle de formule**. Cachez la lettre que vous cherchez : les deux autres vous montrent quoi faire.

```text
        /\
       /  \
      / V  \
     /------\
    / I | R  \
   /____|_____\
```

Cachez $V$ et vous voyez $I \times R$. Cachez $I$ et vous voyez $\dfrac{V}{R}$. Cachez $R$ et vous voyez $\dfrac{V}{I}$.

> **Attention :** le triangle ne fonctionne que si $V$ est en haut. Si vous placez mal les lettres, vous obtiendrez des réponses comme $R = \dfrac{I}{V}$, ce qui est faux. Apprenez aussi l'algèbre, et vérifiez toujours votre réponse en la remettant dans $V = IR$.

### Exemple corrigé 2 : un système solaire domestique à Nyagatare

Une famille du district de Nyagatare possède un système solaire domestique avec une batterie de 12 V.

(a) Quand elle éclaire normalement, leur lampe est traversée par un courant de 0,5 A. Trouvez sa résistance.

1. On cherche $R$, donc on utilise $R = \dfrac{V}{I}$.
2. $R = \dfrac{12}{0.5} = 24\ \Omega$.
3. Vérification : $V = IR = 0.5 \times 24 = 12$ V ✓.

(b) Une résistance de 48 Ω est branchée sur la même batterie. Quel courant circule ?

1. On cherche $I$, donc on utilise $I = \dfrac{V}{R}$.
2. $I = \dfrac{12}{48} = 0.25$ A.
3. Vérification : $0.25 \times 48 = 12$ V ✓. Une résistance deux fois plus grande donne un courant deux fois plus faible.

## Petites et grandes unités : mA et kΩ

Les vrais circuits utilisent souvent de très faibles courants et de très grandes résistances. On utilise donc des **préfixes** :

- **milli** (m) veut dire un millième. $1\ \text{mA} = 0.001$ A, donc 1 A = 1000 mA.
- **kilo** (k) veut dire mille. $1\ \text{k}\Omega = 1000\ \Omega$.

| Pour convertir | Faites ceci | Exemple |
|---|---|---|
| des mA en A | divisez par 1000 | 250 mA = 0,25 A |
| des A en mA | multipliez par 1000 | 0,004 A = 4 mA |
| des kΩ en Ω | multipliez par 1000 | 2,2 kΩ = 2200 Ω |

> **Règle :** avant d'utiliser $V = IR$, convertissez toutes les valeurs en volts, en ampères et en ohms.

### Exemple corrigé 3 : une pile de 9 V et une résistance de 2,2 kΩ

Une pile de 9 V est branchée sur une résistance de 2,2 kΩ. Trouvez l'intensité du courant en mA.

1. Convertissez la résistance en ohms : $2.2\ \text{k}\Omega = 2.2 \times 1000 = 2200\ \Omega$.
2. Utilisez $I = \dfrac{V}{R}$ : $I = \dfrac{9}{2200} \approx 0.0041$ A.
3. Convertissez en mA : $0.0041 \times 1000 = 4.1$ mA.
4. Vérification : $V = IR = 0.0041 \times 2200 \approx 9$ V ✓.

Si vous oubliez l'étape 1, vous obtenez $\dfrac{9}{2.2} \approx 4.1$ A. C'est 1000 fois trop grand !

## Trouver une résistance à partir d'un tableau ou d'un graphique

Au laboratoire, on change la tension, on lit l'intensité à chaque fois et on note les résultats dans un tableau. Ensuite, on calcule $R = \dfrac{V}{I}$ pour chaque ligne.

### Exemple corrigé 4 : tester une résistance

Une élève de Huye teste une résistance et obtient ces mesures. Est-ce un conducteur ohmique, et quelle est sa résistance ?

| $V$ (V) | 1,5 | 3,0 | 4,5 | 6,0 |
|---|---|---|---|---|
| $I$ (A) | 0,10 | 0,20 | 0,30 | 0,40 |

1. Calculez $R = \dfrac{V}{I}$ pour chaque colonne : $\dfrac{1.5}{0.10} = 15$, $\dfrac{3.0}{0.20} = 15$, $\dfrac{4.5}{0.30} = 15$ et $\dfrac{6.0}{0.40} = 15\ \Omega$.
2. $R$ est la même à chaque fois, donc c'est un conducteur ohmique : $R = 15\ \Omega$.
3. Tracez $V$ (vers le haut) en fonction de $I$ (vers la droite). Les points sont sur une **droite passant par l'origine** :

```text
 V (V)
  6,0 |                       x
  4,5 |                 x
  3,0 |           x
  1,5 |     x
    0 +-----+-----+-----+-----+--> I (A)
      0   0,10  0,20  0,30  0,40
```

4. La **pente** (l'inclinaison) de la droite vaut montée ÷ avancée $= \dfrac{6.0 - 0}{0.40 - 0} = 15\ \Omega$. Sur un graphique de $V$ en fonction de $I$, la pente est égale à la résistance.
5. Vérification : quand $V$ double, de 3,0 V à 6,0 V, $I$ double aussi, de 0,20 A à 0,40 A, comme le dit la loi d'Ohm ✓.

## Une lampe n'obéit pas à la loi d'Ohm

Une lampe à filament contient un fil métallique très fin, le **filament**. Quand le courant augmente, le filament devient très chaud et brille. Obéit-il encore à la loi d'Ohm ?

### Exemple corrigé 5 : tester une lampe de torche

| $V$ (V) | 1 | 2 | 4 | 6 |
|---|---|---|---|---|
| $I$ (A) | 0,10 | 0,16 | 0,24 | 0,30 |

1. Calculez $R = \dfrac{V}{I}$ pour chaque colonne : $\dfrac{1}{0.10} = 10\ \Omega$, $\dfrac{2}{0.16} = 12.5\ \Omega$, $\dfrac{4}{0.24} \approx 16.7\ \Omega$ et $\dfrac{6}{0.30} = 20\ \Omega$.
2. La résistance **augmente** quand la tension augmente. Le filament chauffe, et un métal plus chaud a une plus grande résistance.
3. La lampe n'est donc **pas un conducteur ohmique**. Sur un graphique de $V$ en fonction de $I$, ses points sont sur une **courbe** qui devient de plus en plus raide, et non sur une droite.
4. Vérification : de 2 V à 4 V, la tension double, mais l'intensité passe seulement de 0,16 A à 0,24 A. Elle ne double pas ✓.

La loi d'Ohm exige une température constante. La lampe ne respecte pas cette condition : c'est pourquoi elle n'obéit pas à la loi.

## De quoi dépend la résistance ?

La résistance d'un fil dépend de quatre choses :

- **La longueur :** un fil plus long a une plus grande résistance.
- **L'épaisseur :** un fil plus épais a une plus petite résistance, car la charge a plus de place pour circuler.
- **Le matériau :** le cuivre a une très faible résistance, c'est pourquoi les fils de connexion sont en cuivre. Certains alliages, comme le nichrome, ont une résistance bien plus grande.
- **La température :** pour un métal, un fil plus chaud a une plus grande résistance, comme on l'a vu avec la lampe.

## Les résistances en série

Quand des composants sont branchés les uns après les autres dans une seule boucle, ils sont **en série**.

```text
     +------| |------+
     |      12 V     |
     |               |
     +--[4 Ω]--[6 Ω]-+
```

Dans un circuit en série :

- le **même courant** traverse tous les composants, car il n'y a qu'un seul chemin ;
- la **résistance totale** est la somme : $R = R_1 + R_2$ ;
- les tensions aux bornes des composants **s'additionnent** pour donner la tension de la batterie.

### Exemple corrigé 6 : deux résistances sur une batterie de 12 V

Une résistance de 4 Ω et une résistance de 6 Ω sont branchées en série sur une batterie de 12 V, comme sur le schéma. Trouvez l'intensité du courant et la tension aux bornes de chaque résistance.

1. Résistance totale : $R = 4 + 6 = 10\ \Omega$.
2. Intensité : $I = \dfrac{V}{R} = \dfrac{12}{10} = 1.2$ A. Ce courant traverse les deux résistances.
3. Tension aux bornes de la résistance de 4 Ω : $V_1 = IR_1 = 1.2 \times 4 = 4.8$ V.
4. Tension aux bornes de la résistance de 6 Ω : $V_2 = IR_2 = 1.2 \times 6 = 7.2$ V.
5. Vérification : $4.8 + 7.2 = 12$ V, la tension de la batterie ✓.

Construisez vous-même ce circuit dans le kit PhET. Ajoutez un ampèremètre et un voltmètre, puis vérifiez les valeurs.

```sim
phet-circuit-construction-kit-dc
```

## Essayez

Utilisez le laboratoire ci-dessous pour refaire l'exemple corrigé 4.

1. Réglez la résistance sur 15 Ω.
2. Réglez la tension sur 1,5 V, 3 V, 4,5 V puis 6 V. Appuyez à chaque fois sur **Noter la mesure**.
3. Vérifiez que l'intensité vaut 0,10 A, 0,20 A, 0,30 A, puis 0,40 A.
4. Changez maintenant la résistance pour 30 Ω et gardez la tension à 6 V. Prévoyez d'abord l'intensité, puis vérifiez-la.

```sim
ohms-law-lab
```

## Sécurité

Au Rwanda, la tension du secteur est de 230 V. Même un faible courant qui traverse le corps peut être dangereux. Ne touchez jamais de fils dénudés et n'introduisez jamais d'objets métalliques dans les prises.

Faites vos expériences uniquement avec des piles, des batteries ou une alimentation basse tension fournie par votre enseignant. Ne branchez jamais un ampèremètre directement aux bornes d'une pile : sa résistance est très faible, donc un courant intense circule et peut endommager l'appareil.

## Erreurs fréquentes

- **Oublier de convertir les mA en A ou les kΩ en Ω.** Utilisez toujours des volts, des ampères et des ohms dans $V = IR$.
- **Laisser le temps en minutes dans $Q = It$.** Convertissez d'abord les minutes en secondes.
- **Mal brancher les appareils de mesure.** L'ampèremètre se branche en série. Le voltmètre se branche en dérivation, aux bornes du composant.
- **Utiliser la résistance d'une lampe à une tension pour prévoir le courant à une autre tension.** $R = \dfrac{V}{I}$ donne la résistance de la lampe seulement à cet instant. Sa résistance change quand elle chauffe.
- **Écrire la formule à l'envers,** par exemple $R = \dfrac{I}{V}$. Vérifiez en remettant votre réponse dans $V = IR$.
- **Croire que le courant est consommé.** Dans un circuit en série, l'intensité est la même partout. C'est l'**énergie** qui est cédée aux composants, pas la charge.

## Testez-vous

1. Calculez l'intensité du courant dans une résistance de 10 Ω branchée sur une alimentation de 5 V.
2. Quelle tension faut-il pour faire passer 3 A dans 4 Ω ?
3. Pourquoi branche-t-on un ampèremètre en série ?
4. Un courant de 0,25 A sort d'une batterie de 12 V pendant 5 minutes. (a) Quelle charge passe ? (b) Quelle énergie la batterie donne-t-elle à cette charge ?
5. Convertissez 80 mA en ampères et 4,7 kΩ en ohms.
6. Une pile de 6 V est branchée sur une résistance de 1,5 kΩ. Trouvez l'intensité du courant en mA.
7. Un élève obtient ces mesures pour un composant : 2,0 V et 0,25 A, 4,0 V et 0,50 A, 6,0 V et 0,75 A. Ce composant est-il un conducteur ohmique ? Quelle est sa résistance ?
8. Une résistance de 3 Ω et une résistance de 9 Ω sont branchées en série sur une pile de 6 V. Trouvez l'intensité du courant et la tension aux bornes de chaque résistance.

*Réponses : 1) $I = \frac{5}{10} = 0.5$ A · 2) $V = 3 \times 4 = 12$ V · 3) pour que tout le courant de cette partie du circuit le traverse · 4) (a) $t = 5 \times 60 = 300$ s, donc $Q = 0.25 \times 300 = 75$ C ; (b) chaque coulomb reçoit 12 J, donc $12 \times 75 = 900$ J · 5) 0,08 A et 4700 Ω · 6) $I = \frac{6}{1500} = 0.004$ A = 4 mA · 7) oui, c'est un conducteur ohmique : $\frac{2.0}{0.25} = \frac{4.0}{0.50} = \frac{6.0}{0.75} = 8\ \Omega$ à chaque fois · 8) $R = 3 + 9 = 12\ \Omega$ et $I = \frac{6}{12} = 0.5$ A ; les tensions valent $0.5 \times 3 = 1.5$ V et $0.5 \times 9 = 4.5$ V (vérification : $1.5 + 4.5 = 6$ V)*
