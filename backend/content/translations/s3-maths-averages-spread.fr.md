---
slug: s3-maths-averages-spread
language: fr
title: Moyennes et mesures de dispersion
summary: Calculer la moyenne, la médiane, le mode, l'étendue et l'écart interquartile d'une série de données, y compris à partir d'un tableau d'effectifs, et choisir la valeur centrale la mieux adaptée à une situation.
reviewed: false
---
## Pourquoi des valeurs centrales et des mesures de dispersion ?

Une liste de nombres est difficile à comprendre d'un seul coup d'œil. La statistique résume les données à l'aide de deux sortes de nombres :

- une **valeur centrale** (une mesure de tendance centrale), c'est-à-dire une seule valeur qui représente toute la série ;
- une **mesure de dispersion**, qui montre à quel point les valeurs sont éparpillées.

Deux conducteurs de moto-taxi peuvent gagner tous les deux 10 000 FRW par jour en moyenne, alors que l'un gagne presque la même somme chaque jour et que l'autre gagne des sommes très différentes. La moyenne est la même, mais la dispersion ne l'est pas.

## Les trois valeurs centrales

**La moyenne.** On additionne toutes les valeurs et on divise par le nombre de valeurs :

$$\bar{x} = \frac{\sum x}{n}$$

**La médiane.** On range les valeurs dans l'ordre. La médiane est la valeur du milieu, celle de rang $\frac{n + 1}{2}$. Si $n$ est pair, c'est la moyenne des deux valeurs du milieu.

**Le mode.** C'est la valeur qui apparaît le plus souvent. Une série peut avoir un seul mode, plusieurs modes ou aucun.

## Les mesures de dispersion

**Étendue** $=$ plus grande valeur $-$ plus petite valeur.

**L'écart interquartile (noté IQR, de l'anglais *interquartile range*).** On range les données dans l'ordre et on les partage en une moitié inférieure et une moitié supérieure. Le **premier quartile** $Q_1$ est la médiane de la moitié inférieure et le **troisième quartile** $Q_3$ est la médiane de la moitié supérieure. Si $n$ est impair, on n'inclut la médiane elle-même dans aucune des deux moitiés. Alors

$$\text{IQR} = Q_3 - Q_1$$

L'écart interquartile mesure la dispersion de la moitié centrale des données ; il n'est donc pas influencé par une seule valeur très grande ou très petite.

### Exemple corrigé 1 : la semaine d'un conducteur de moto

Un conducteur de moto-taxi à Kigali a noté ses recettes (en FRW) pendant une semaine :

8 000 · 12 500 · 6 000 · 9 500 · 15 000 · 11 000 · 8 000

- **Moyenne :** total $= 70\,000$, donc $\bar{x} = \frac{70\,000}{7} = 10\,000$ FRW.
- **Médiane :** dans l'ordre, 6 000 · 8 000 · 8 000 · **9 500** · 11 000 · 12 500 · 15 000. Avec $n = 7$, la médiane est la valeur de rang $\frac{7 + 1}{2} = 4$, soit 9 500 FRW.
- **Mode :** 8 000 FRW apparaît deux fois, donc le mode est 8 000 FRW.
- **Étendue :** $15\,000 - 6\,000 = 9\,000$ FRW.

## Données présentées dans un tableau d'effectifs

Quand des valeurs se répètent, un tableau d'effectifs évite de tout recopier. On multiplie chaque valeur $x$ par son effectif $f$ :

$$\bar{x} = \frac{\sum fx}{\sum f}$$

### Exemple corrigé 2 : la taille des ménages

Une enquête menée auprès de 20 ménages d'un village de Rwamagana a relevé le nombre de personnes vivant dans chacun d'eux.

| Personnes par ménage, $x$ | 2 | 3 | 4 | 5 | 6 | Total |
|---|---|---|---|---|---|---|
| Effectif, $f$ | 3 | 5 | 6 | 4 | 2 | 20 |
| $fx$ | 6 | 15 | 24 | 20 | 12 | 77 |
| Effectif cumulé | 3 | 8 | 14 | 18 | 20 | |

- **Moyenne :** $\bar{x} = \frac{77}{20} = 3.85$ personnes. Une moyenne n'est pas forcément un nombre entier.
- **Médiane :** $n = 20$, donc la médiane se situe entre la 10e et la 11e valeur. Les effectifs cumulés montrent que les valeurs de rang 9 à 14 valent toutes 4, donc la médiane est 4.
- **Mode :** 4 a l'effectif le plus élevé (6), donc le mode est 4.
- **Étendue :** $6 - 2 = 4$.

### Exemple corrigé 3 : quand la moyenne induit en erreur

Six personnes travaillent dans un petit atelier de couture à Kigali. Leurs salaires mensuels (en FRW) sont :

60 000 · 60 000 · 70 000 · 75 000 · 85 000 · 450 000 (le propriétaire)

- **Moyenne :** total $= 800\,000$, donc $\bar{x} = \frac{800\,000}{6} \approx 133\,333$ FRW.
- **Médiane :** $n = 6$ est pair, on prend donc la moyenne des 3e et 4e valeurs : $\frac{70\,000 + 75\,000}{2} = 72\,500$ FRW.

Cinq des six personnes gagnent **moins** que la moyenne, car le salaire élevé du propriétaire la tire vers le haut. La médiane, 72 500 FRW, décrit bien mieux un salaire typique.

### Exemple corrigé 4 : les quartiles d'une récolte de maïs

Huit agriculteurs de Nyagatare ont récolté les nombres de sacs de maïs suivants, déjà rangés dans l'ordre :

12 · 15 · 18 · 20 · 22 · 25 · 27 · 35

- Médiane $= \frac{20 + 22}{2} = 21$ sacs.
- Moitié inférieure : 12, 15, 18, 20, donc $Q_1 = \frac{15 + 18}{2} = 16.5$.
- Moitié supérieure : 22, 25, 27, 35, donc $Q_3 = \frac{25 + 27}{2} = 26$.
- $\text{IQR} = 26 - 16.5 = 9.5$ sacs, alors que l'étendue vaut $35 - 12 = 23$ sacs. La seule grosse récolte de 35 sacs allonge l'étendue, mais modifie à peine l'écart interquartile.

## Choisir la bonne mesure

| Mesure | Point fort | Point faible |
|---|---|---|
| Moyenne | utilise toutes les valeurs | influencée par les valeurs extrêmes |
| Médiane | n'est pas influencée par les valeurs extrêmes | ne tient pas compte de la grandeur de la plupart des valeurs |
| Mode | convient aux catégories, comme la culture la plus répandue | peut ne pas exister, ou il peut y en avoir plusieurs |
| Étendue | rapide et simple | dépend uniquement des deux valeurs extrêmes |
| Écart interquartile | ne tient pas compte des valeurs extrêmes | plus long à calculer |

Par exemple, un commerçant du marché de Kimironko qui veut savoir quelle pointure de chaussures stocker en plus grande quantité doit utiliser le **mode**.

## Activité en classe

Demandez à 15 camarades combien de minutes ils mettent pour venir à l'école. Calculez la moyenne, la médiane, le mode et l'étendue de vos données, puis indiquez quelle valeur centrale décrit le mieux un trajet typique, et pourquoi.

## Testez-vous

1. Calculez la moyenne, la médiane, le mode et l'étendue de la série 5, 10, 3, 10, 4, 16.
2. La moyenne de cinq nombres est 12. Quatre d'entre eux sont 11, 14, 9 et 15. Trouvez le cinquième nombre.
3. Quelle valeur centrale convient le mieux pour connaître la taille d'uniforme scolaire la plus vendue dans un magasin, et pourquoi ?

*Réponses : 1) moyenne $= \frac{48}{6} = 8$ ; dans l'ordre 3, 4, 5, 10, 10, 16, donc médiane $= \frac{5 + 10}{2} = 7.5$ ; mode $= 10$ ; étendue $= 16 - 3 = 13$ · 2) total $= 5 \times 12 = 60$, et $60 - (11 + 14 + 9 + 15) = 60 - 49 = 11$ · 3) le mode, car les tailles sont des catégories et le magasin veut celle qui revient le plus souvent*
