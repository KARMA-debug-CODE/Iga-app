---
slug: s6-biology-populations-ecology
language: fr
title: Populations et écologie
summary: Estimer l'effectif d'une population, modéliser la croissance exponentielle et logistique, et expliquer comment les facteurs dépendants et indépendants de la densité régulent les populations.
reviewed: false
---
## Termes clés

- **Population** : l'ensemble des organismes d'une même espèce vivant dans la même zone au même moment, capables de se reproduire entre eux.
- **Communauté** : l'ensemble des populations d'espèces différentes qui vivent et interagissent dans une zone.
- **Écosystème** : une communauté et son environnement abiotique (non vivant), comme le sol, l'eau et le climat.
- **Habitat** : le lieu où vit un organisme.
- **Niche écologique** : le rôle d'une espèce dans son écosystème : ce qu'elle mange, ce qui la mange, où et quand elle est active.
- **Densité de population** : nombre d'individus par unité de surface (ou de volume), par exemple en plantes m⁻².

L'effectif d'une population varie selon

$$\Delta N = (\text{naissances} + \text{immigration}) - (\text{décès} + \text{émigration})$$

## Estimer l'effectif d'une population

On peut rarement compter tous les individus : on procède donc par **échantillonnage**.

### Les quadrats (plantes et animaux peu mobiles)

Placez des quadrats à des emplacements choisis **au hasard** (à l'aide de coordonnées tirées au hasard, pour éviter les biais), comptez les individus dans chacun, puis extrapolez :

$$\text{population estimée} = \text{nombre moyen par quadrat} \times \frac{\text{aire totale}}{\text{aire d'un quadrat}}$$

#### Exemple corrigé 1

Un élève estime le nombre de plants de bident poilu (*Bidens pilosa*), une mauvaise herbe, dans un pâturage de 50 m × 40 m à Nyagatare. Dix quadrats de 1 m² donnent :

3, 5, 0, 2, 4, 6, 1, 3, 2, 4

1. Total : $3 + 5 + 0 + 2 + 4 + 6 + 1 + 3 + 2 + 4 = 30$
2. Moyenne par quadrat : $\dfrac{30}{10} = 3.0$, donc la densité est de 3,0 plantes m⁻²
3. Aire du pâturage : $50 \times 40 = 2000\ \text{m}^2$
4. Estimation : $3.0 \times \dfrac{2000}{1} = 6000$ plantes

### Capture–marquage–lâcher–recapture (animaux mobiles)

Capturez un échantillon, marquez chaque animal sans lui faire de mal, relâchez-les, puis capturez un second échantillon plus tard. L'**indice de Lincoln** donne

$$N = \frac{n_1 \times n_2}{m_2}$$

où $n_1$ = nombre d'animaux marqués dans le premier échantillon, $n_2$ = nombre d'animaux capturés dans le second échantillon, et $m_2$ = nombre d'animaux marqués dans le second échantillon.

#### Exemple corrigé 2

Une coopérative de pisciculture de Rwamagana veut savoir combien de tilapias vivent dans son étang. Ses membres pêchent au filet 120 poissons, les marquent en leur coupant un petit morceau de nageoire, puis les relâchent. Une semaine plus tard, ils pêchent 150 poissons, dont 24 sont marqués.

$$N = \frac{120 \times 150}{24} = \frac{18\,000}{24} = 750 \text{ tilapias}$$

La méthode suppose que :

- les animaux marqués se mélangent au hasard avec le reste de la population
- les marques ne tombent pas et ne rendent pas les animaux plus faciles à capturer pour les prédateurs
- il n'y a pas de naissances, de décès, d'immigration ou d'émigration importants entre les deux échantillonnages
- les animaux marqués et non marqués ont la même probabilité d'être capturés

## La croissance des populations

### La croissance exponentielle

Avec une nourriture et un espace illimités, sans prédateurs ni maladies, une population croît de façon **exponentielle** : plus elle est grande, plus elle croît vite.

$$\frac{dN}{dt} = rN$$

où $r$ est le taux intrinsèque d'accroissement naturel. La courbe de $N$ en fonction du temps est **en forme de J**.

C'est le cas des bactéries qui se divisent toutes les 20 minutes. En partant de 500 cellules, 2 heures correspondent à $\frac{120}{20} = 6$ générations, donc

$$N = 500 \times 2^6 = 500 \times 64 = 32\,000 \text{ cellules}$$

La jacinthe d'eau, une espèce envahissante qui peut se propager rapidement sur les lacs de la Province de l'Est, et des ravageurs comme la chenille légionnaire d'automne dans les champs de maïs ont eux aussi une croissance presque exponentielle juste après leur installation.

### La croissance logistique (sigmoïde)

Dans les milieux réels, les ressources viennent à manquer. La croissance ralentit et la population se stabilise à la **capacité de charge** $K$ : l'effectif maximal qu'un milieu peut supporter à long terme.

$$\frac{dN}{dt} = rN\left(\frac{K - N}{K}\right)$$

| Phase | Ce qui se passe | Pourquoi |
|---|---|---|
| Latence | Croissance lente | Peu d'individus reproducteurs ; les organismes s'adaptent à l'habitat |
| Exponentielle (log) | Croissance rapide | Ressources abondantes ; les naissances dépassent largement les décès |
| Ralentissement | La croissance ralentit | La compétition pour la nourriture et l'espace augmente ; plus de prédation et de maladies |
| Stationnaire | $N$ fluctue autour de $K$ | Les naissances compensent à peu près les décès |

Dans un flacon fermé contenant des levures, une **phase de déclin** suit, car le sucre s'épuise et l'éthanol, toxique, s'accumule.

#### Exemple corrigé 3

Une population d'antilopes a un taux $r = 0.4$ par an et une capacité de charge $K = 1000$. Calculez la vitesse de croissance lorsque $N = 200$.

$$\frac{dN}{dt} = 0.4 \times 200 \times \frac{1000 - 200}{1000} = 80 \times 0.8 = 64 \text{ antilopes par an}$$

Lorsque $N = 500 = \frac{K}{2}$ : $0.4 \times 500 \times 0.5 = 100$ par an, soit la croissance la plus rapide. Lorsque $N = K = 1000$, la parenthèse est nulle, donc la croissance s'arrête.

## Qu'est-ce qui limite les populations ?

| Facteurs dépendants de la densité | Facteurs indépendants de la densité |
|---|---|
| Leur effet augmente à mesure que la population devient plus dense | Leur effet est le même quelle que soit la densité |
| Compétition pour la nourriture, l'eau, l'espace et les partenaires sexuels | Sécheresses, inondations et glissements de terrain |
| Prédation | Incendies |
| Maladies et parasites (qui se propagent plus vite dans une foule) | Gel, chaleur extrême |
| Accumulation de déchets toxiques | Éruptions volcaniques |

Les facteurs dépendants de la densité **régulent** une population autour de $K$ par rétroaction négative.

La **compétition** peut être **intraspécifique** (au sein d'une même espèce ; c'est la plus intense, car les individus partagent la même niche) ou **interspécifique** (entre espèces différentes). Si deux espèces occupent exactement la même niche, l'une finit par éliminer l'autre : c'est le **principe d'exclusion compétitive**.

### Les cycles prédateurs–proies

Lorsque les proies sont abondantes, les prédateurs survivent et se reproduisent bien : leur nombre augmente. Davantage de prédateurs mangent davantage de proies : le nombre de proies diminue. Avec moins de nourriture, les prédateurs déclinent à leur tour, et les proies se reconstituent. Les pics de prédateurs sont généralement **en retard** sur les pics de proies. Dans le parc national de l'Akagera, où des lions ont été réintroduits en 2015, les écologues étudient comment les prédateurs et les herbivores tels que les impalas s'influencent mutuellement.

## La conservation au Rwanda

La protection, les patrouilles anti-braconnage et le tourisme communautaire ont permis à la population mondiale de gorilles de montagne, dont les groupes du parc national des Volcans, d'atteindre un peu plus de 1 000 individus en 2018. Sur le lac Kivu, les *sambaza*, des poissons introduits depuis le lac Tanganyika à la fin des années 1950, font vivre de nombreuses familles de pêcheurs. Des règles sur la taille des mailles des filets et sur les saisons de pêche visent à maintenir les prises en dessous du rythme auquel la population peut se renouveler.

## Explorez

Lancez la simulation avec une nourriture limitée, puis ajoutez des loups. Esquissez la courbe de la population. Reconnaissez-vous une croissance exponentielle, une stabilisation et les effets des prédateurs ?

```sim
phet-natural-selection
```

## Sécurité lors des sorties sur le terrain

- Travaillez en groupe, dites à votre enseignant où vous allez et restez loin des eaux profondes sur les rives des lacs.
- Portez des chaussures fermées, un pantalon long et un chapeau ; faites attention aux serpents, aux orties et aux fourmis qui mordent.
- Manipulez les animaux capturés avec douceur et brièvement, utilisez des marques inoffensives, et relâchez-les là où ils ont été capturés.
- Lavez-vous les mains après avoir manipulé de la terre, des échantillons d'eau ou des animaux.

## Testez-vous

1. On marque et on relâche 60 coléoptères. Dans un second échantillon de 50 coléoptères, 12 sont marqués. Estimez l'effectif de la population.
2. Donnez un facteur dépendant de la densité et un facteur indépendant de la densité qui pourraient affecter les sambaza du lac Kivu.
3. Pour une population avec $r = 0.2$ par an, $K = 800$ et $N = 400$, calculez $\frac{dN}{dt}$.

*Réponses : 1) $N = \frac{60 \times 50}{12} = 250$ coléoptères · 2) Dépendant de la densité : la compétition pour le plancton, la prédation, les maladies ; indépendant de la densité : un changement brutal de la température de l'eau ou une pollution · 3) $0.2 \times 400 \times \frac{800 - 400}{800} = 80 \times 0.5 = 40$ par an*
