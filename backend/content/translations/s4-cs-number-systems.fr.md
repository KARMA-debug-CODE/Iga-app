---
slug: s4-cs-number-systems
language: fr
title: "Les systèmes de numération : binaire, octal, décimal et hexadécimal"
summary: Pourquoi les ordinateurs utilisent le binaire, comment fonctionne la valeur de position en base 2, 8, 10 et 16, et comment passer d'une base à l'autre par divisions successives et en regroupant les bits.
reviewed: false
---
## Pourquoi les ordinateurs utilisent le binaire

Un ordinateur est construit avec des millions de minuscules interrupteurs électroniques appelés **transistors**. Chaque interrupteur est soit éteint, soit allumé : il n'a donc que deux états. On écrit ces deux états 0 et 1.

Un seul 0 ou 1 est un **bit**, abréviation de l'anglais *binary digit* (chiffre binaire). Un groupe de 8 bits est un **octet**. Chaque nombre, chaque lettre, chaque photo, chaque chanson et chaque message MoMo d'un téléphone est stocké sous la forme d'une longue suite de bits.

Pourquoi seulement deux états ? Ils sont faciles à distinguer, même quand la tension est un peu faible ou perturbée : l'ordinateur se trompe donc rarement. Les interrupteurs à deux états sont aussi petits, bon marché et rapides. Une machine à dix niveaux de tension, un pour chaque chiffre décimal, serait beaucoup plus difficile à construire de façon fiable.

## Les systèmes de numération et la valeur de position

Un **système de numération** est une façon d'écrire les nombres avec un ensemble fixe de chiffres. Le nombre de chiffres qu'il utilise est sa **base** (ou radix).

| Système de numération | Base | Chiffres |
|---|---|---|
| Binaire | 2 | 0 et 1 |
| Octal | 8 | de 0 à 7 |
| Décimal | 10 | de 0 à 9 |
| Hexadécimal | 16 | de 0 à 9, puis de A à F |

En hexadécimal, les lettres représentent les valeurs de dix à quinze : A = 10, B = 11, C = 12, D = 13, E = 14 et F = 15.

Les mêmes chiffres peuvent représenter des nombres différents selon la base. On écrit donc la base en petit après les chiffres : $11_{10}$ vaut onze, mais $11_2$ vaut trois, $11_8$ vaut neuf et $11_{16}$ vaut dix-sept.

Tous les systèmes de numération utilisent la **valeur de position**. En décimal, $3\,054 = 3 \times 1000 + 0 \times 100 + 5 \times 10 + 4 \times 1$. Les valeurs de position sont des puissances de 10 : $10^0 = 1$, $10^1 = 10$, $10^2 = 100$, et ainsi de suite. En base $b$, les valeurs de position sont des puissances de $b$, en commençant par $b^0 = 1$ à droite.

| Base | Valeurs de position, de droite à gauche |
|---|---|
| 2 | 1, 2, 4, 8, 16, 32, 64, 128, … |
| 8 | 1, 8, 64, 512, 4096, … |
| 16 | 1, 16, 256, 4096, … |

## Convertir en décimal : utilisez les valeurs de position

Écrivez les valeurs de position au-dessus des chiffres, multipliez chaque chiffre par sa valeur de position, puis additionnez.

### Exemple corrigé 1 : vers le décimal

Convertissez en décimal (a) $101101_2$, (b) $157_8$ et (c) $\mathrm{1A3}_{16}$.

(a) Écrivez les valeurs de position binaires au-dessus des bits :

| Valeur de position | 32 | 16 | 8 | 4 | 2 | 1 |
|---|---|---|---|---|---|---|
| Bit | 1 | 0 | 1 | 1 | 0 | 1 |

- Un bit vaut 0 ou 1 : il suffit donc d'additionner les valeurs de position au-dessus des 1 : $32 + 8 + 4 + 1 = 45$.
- Donc $101101_2 = 45_{10}$.

(b) Les valeurs de position en octal sont 64, 8 et 1.

- $1 \times 64 + 5 \times 8 + 7 \times 1 = 64 + 40 + 7 = 111$, donc $157_8 = 111_{10}$.

(c) Les valeurs de position en hexadécimal sont 256, 16 et 1, et A vaut 10.

- $1 \times 256 + 10 \times 16 + 3 \times 1 = 256 + 160 + 3 = 419$, donc $\mathrm{1A3}_{16} = 419_{10}$.

## Convertir depuis le décimal : les divisions successives

Pour écrire un nombre décimal en base $b$, divisez-le par $b$ encore et encore, en notant chaque reste, jusqu'à obtenir un quotient égal à 0. Les restes, lus **de bas en haut**, sont les chiffres de la réponse. Le premier reste est le chiffre le plus à droite.

### Exemple corrigé 2 : du décimal au binaire

Convertissez 156 en binaire.

| Division | Quotient | Reste |
|---|---|---|
| 156 ÷ 2 | 78 | 0 |
| 78 ÷ 2 | 39 | 0 |
| 39 ÷ 2 | 19 | 1 |
| 19 ÷ 2 | 9 | 1 |
| 9 ÷ 2 | 4 | 1 |
| 4 ÷ 2 | 2 | 0 |
| 2 ÷ 2 | 1 | 0 |
| 1 ÷ 2 | 0 | 1 |

- Lisez les restes de bas en haut : $156 = 10011100_2$.
- Vérification : $128 + 16 + 8 + 4 = 156$. C'est correct.

### Exemple corrigé 3 : du décimal à l'hexadécimal et à l'octal

Le mont Karisimbi culmine à 4 507 m. Écrivez 4 507 en hexadécimal et en octal.

| Division | Quotient | Reste |
|---|---|---|
| 4507 ÷ 16 | 281 | 11, qui s'écrit B |
| 281 ÷ 16 | 17 | 9 |
| 17 ÷ 16 | 1 | 1 |
| 1 ÷ 16 | 0 | 1 |

- De bas en haut : $4507 = \mathrm{119B}_{16}$. Un reste de 11 s'écrit avec un seul chiffre : B.
- Vérification : $1 \times 4096 + 1 \times 256 + 9 \times 16 + 11 = 4096 + 256 + 144 + 11 = 4507$. C'est correct.
- Pour l'octal, divisez par 8 : $4507 \div 8 = 563$ reste 3, $563 \div 8 = 70$ reste 3, $70 \div 8 = 8$ reste 6, $8 \div 8 = 1$ reste 0, et $1 \div 8 = 0$ reste 1.
- De bas en haut : $4507 = 10633_8$.
- Vérification : $1 \times 4096 + 0 \times 512 + 6 \times 64 + 3 \times 8 + 3 = 4096 + 384 + 24 + 3 = 4507$. C'est correct.

## Compter en binaire

Compter en binaire fonctionne comme le compteur kilométrique d'une moto. Quand un chiffre dépasse sa plus grande valeur, il revient à 0 et on retient 1 vers la gauche. En binaire, le plus grand chiffre est 1, donc $1 + 1 = 10_2$, et $111_2 + 1 = 1000_2$.

| Décimal | Binaire | Octal | Hexadécimal |
|---|---|---|---|
| 0 | 0000 | 0 | 0 |
| 1 | 0001 | 1 | 1 |
| 2 | 0010 | 2 | 2 |
| 3 | 0011 | 3 | 3 |
| 4 | 0100 | 4 | 4 |
| 5 | 0101 | 5 | 5 |
| 6 | 0110 | 6 | 6 |
| 7 | 0111 | 7 | 7 |
| 8 | 1000 | 10 | 8 |
| 9 | 1001 | 11 | 9 |
| 10 | 1010 | 12 | A |
| 11 | 1011 | 13 | B |
| 12 | 1100 | 14 | C |
| 13 | 1101 | 15 | D |
| 14 | 1110 | 16 | E |
| 15 | 1111 | 17 | F |

Avec $n$ bits, on peut écrire $2^n$ nombres différents, de 0 à $2^n - 1$. Quatre bits donnent 16 nombres, de 0 à 15. Un octet (8 bits) donne $2^8 = 256$ nombres, de 0 à 255, et $255 = 11111111_2 = \mathrm{FF}_{16}$.

### Exemple corrigé 4 : combien de bits ?

Le Rwanda compte 30 districts. Un programme donne à chaque district son propre code binaire. Quel est le plus petit nombre de bits nécessaire pour chaque code ?

- 4 bits donnent $2^4 = 16$ codes. Ce n'est pas assez pour 30 districts.
- 5 bits donnent $2^5 = 32$ codes. C'est assez, et il reste 2 codes libres.
- Chaque code a donc besoin de 5 bits.

## Du binaire à l'octal et à l'hexadécimal : regrouper les bits

Comme $8 = 2^3$, un chiffre octal représente exactement 3 bits. Comme $16 = 2^4$, un chiffre hexadécimal représente exactement 4 bits. On peut donc convertir sans passer par le décimal : découpez les bits en groupes **à partir de la droite**, puis remplacez chaque groupe par un chiffre à l'aide du tableau ci-dessus.

### Exemple corrigé 5 : regrouper les bits

(a) Convertissez $11010111_2$ en hexadécimal et en octal. (b) Convertissez $\mathrm{B4}_{16}$ en binaire.

- (a) Groupes de 4 à partir de la droite : 1101 | 0111. Comme 1101 = D et 0111 = 7, $11010111_2 = \mathrm{D7}_{16}$.
- Groupes de 3 à partir de la droite : 11 | 010 | 111. Le groupe de gauche n'a que 2 bits : ajoutez un 0 devant. On obtient 011 | 010 | 111 = 3 | 2 | 7. Donc $11010111_2 = 327_8$.
- Vérification par le décimal : $11010111_2 = 128 + 64 + 16 + 4 + 2 + 1 = 215$, $\mathrm{D7}_{16} = 13 \times 16 + 7 = 215$ et $327_8 = 3 \times 64 + 2 \times 8 + 7 = 215$. Les trois sont corrects.
- (b) Écrivez chaque chiffre hexadécimal sur 4 bits : B = 1011 et 4 = 0100. Donc $\mathrm{B4}_{16} = 10110100_2$.

Les programmeurs aiment l'hexadécimal parce qu'il est court : un octet s'écrit toujours avec deux chiffres hexadécimaux, de 00 à FF. On le rencontre dans les couleurs des pages Web (le bleu ciel du drapeau du Rwanda s'écrit souvent `#00A1DE` : rouge 00 = 0, vert A1 = 161 et bleu DE = 222), dans les adresses de la mémoire et dans l'adresse d'une carte réseau.

## Vérifiez vos réponses avec la calculatrice

La [Calculatrice](/calculator) a un mode **Programmeur** qui affiche un même nombre en HEX, DEC, OCT et BIN en même temps. Ouvrez-la, choisissez **Programmeur** dans son menu, choisissez DEC, tapez 4507, puis comparez les lignes HEX et OCT avec l'exemple corrigé 3. Servez-vous-en pour vérifier votre travail, mais apprenez les méthodes : à l'examen, vous devez montrer chaque étape.

## Erreurs fréquentes

- **Lire les restes de haut en bas.** Le premier reste est le chiffre le plus à droite : 156 s'écrit $10011100_2$, et non $00111001_2$.
- **Regrouper les bits à partir de la gauche.** Commencez toujours par la droite, et ajoutez des zéros à gauche du dernier groupe : $11010111_2$ devient 011 | 010 | 111.
- **Écrire un reste de 10 à 15 avec deux chiffres.** En hexadécimal, un reste de 11 s'écrit avec le seul chiffre B : 4507 s'écrit $\mathrm{119B}_{16}$, et non « 11911 ».
- **Utiliser un chiffre qui n'existe pas dans la base.** Le binaire n'utilise que 0 et 1, et l'octal seulement de 0 à 7 : « 1092 » ne peut donc pas être un nombre octal.
- **Oublier la base.** « 10 » peut vouloir dire dix, deux, huit ou seize. Écrivez $10_2$, $10_8$ ou $10_{16}$.
- **Commencer les valeurs de position à 2.** La valeur de position la plus à droite est toujours $b^0 = 1$.

## Testez-vous

1. Convertissez $110011_2$ en décimal.
2. Convertissez 100 en binaire.
3. Convertissez $\mathrm{7C}_{16}$ en décimal et en binaire.
4. Convertissez $1011101_2$ en octal et en hexadécimal.
5. Quel est le plus grand nombre que l'on peut écrire avec 6 bits ? Donnez-le en binaire et en décimal.
6. Lequel de ces nombres n'est pas un nombre octal : 725, 1080 ou 17 ? Pourquoi ?
7. Vous comptez en binaire. Quel nombre vient juste après $1011_2$ ?

*Réponses : 1) $32 + 16 + 2 + 1 = 51$ · 2) $1100100_2$, car $64 + 32 + 4 = 100$ · 3) $7 \times 16 + 12 = 124$, et 0111 | 1100 donne $1111100_2$ · 4) 1 | 011 | 101 donne $135_8$, et 101 | 1101 donne $\mathrm{5D}_{16}$ (les deux valent 93) · 5) $111111_2 = 2^6 - 1 = 63$ · 6) 1080, car 8 n'est pas un chiffre octal · 7) $1100_2$, car $11 + 1 = 12$*
