---
slug: s3-maths-sets-venn-diagrams
language: fr
title: Ensembles et diagrammes de Venn
summary: Utiliser les notations des ensembles, déterminer des réunions, des intersections et des complémentaires, et résoudre des problèmes de dénombrement à l'aide de diagrammes de Venn.
reviewed: false
---
## Qu'est-ce qu'un ensemble ?

Un **ensemble** est une collection d'objets bien définie. Ces objets s'appellent des **éléments**. On désigne les ensembles par des lettres majuscules et on écrit la liste de leurs éléments entre accolades.

- $V = \{a, e, i, o, u\}$ est l'ensemble des voyelles de l'alphabet anglais.
- $E = \{x : x \text{ est un nombre pair}, 1 \le x \le 10\} = \{2, 4, 6, 8, 10\}$. Lisez les deux-points comme « tel que ».

« Bien définie » signifie que l'on peut toujours décider si un objet appartient ou non à l'ensemble. « L'ensemble des élèves de grande taille » n'est **pas** bien défini, car « grand » est une question d'opinion. « L'ensemble des élèves qui mesurent plus de 160 cm » est bien défini.

## Vocabulaire et symboles

| Terme | Symbole | Signification | Exemple |
|---|---|---|---|
| appartient à | $\in$ | est un élément de l'ensemble | $e \in V$ |
| n'appartient pas à | $\notin$ | n'est pas un élément de l'ensemble | $b \notin V$ |
| nombre d'éléments (cardinal) | $n(A)$ | combien d'éléments $A$ contient | $n(V) = 5$ |
| ensemble vide | $\varnothing$ ou $\{\ \}$ | ensemble qui ne contient aucun élément | les mois de 32 jours |
| ensemble universel (référentiel) | $\xi$ ou $U$ | tous les éléments étudiés | $\xi = \{1, 2, \dots, 12\}$ |
| sous-ensemble (inclusion) | $A \subseteq B$ | tout élément de $A$ est aussi dans $B$ | $\{2, 4\} \subseteq E$ |

L'ensemble vide est un sous-ensemble de tout ensemble, et tout ensemble est un sous-ensemble de lui-même. Un ensemble à $n$ éléments possède $2^n$ sous-ensembles. Par exemple, $\{a, b\}$ possède $2^2 = 4$ sous-ensembles : $\varnothing$, $\{a\}$, $\{b\}$ et $\{a, b\}$.

## Combiner des ensembles

- **Réunion** $A \cup B$ : les éléments qui sont dans $A$ **ou** dans $B$ **ou dans les deux**.
- **Intersection** $A \cap B$ : les éléments qui sont à la fois dans $A$ **et** dans $B$.
- **Complémentaire** $A'$ : les éléments de $\xi$ qui ne sont **pas** dans $A$.
- Deux ensembles sont **disjoints** s'ils n'ont aucun élément en commun, c'est-à-dire si $A \cap B = \varnothing$.

### Exemple corrigé 1

Soit $\xi = \{1, 2, 3, \dots, 12\}$, $A = \{\text{nombres pairs}\}$ et $B = \{\text{multiples de } 3\}$.

- $A = \{2, 4, 6, 8, 10, 12\}$ et $B = \{3, 6, 9, 12\}$.
- $A \cap B = \{6, 12\}$ : les nombres présents dans les deux listes.
- $A \cup B = \{2, 3, 4, 6, 8, 9, 10, 12\}$. On n'écrit $6$ et $12$ qu'une seule fois, donc $n(A \cup B) = 8$.
- $A' = \{1, 3, 5, 7, 9, 11\}$.
- $(A \cup B)' = \{1, 5, 7, 11\}$, donc $n\big((A \cup B)'\big) = 12 - 8 = 4$.

## Les diagrammes de Venn

Un **diagramme de Venn** représente des ensembles par des dessins. Un rectangle représente l'ensemble universel $\xi$ et chaque ensemble est un cercle tracé à l'intérieur. Des cercles qui se chevauchent ont des éléments en commun. Deux cercles qui se chevauchent partagent le rectangle en quatre régions :

| Région | En mots | Notation | Exemple corrigé 1 |
|---|---|---|---|
| dans $A$ mais pas dans $B$ | seulement $A$ | $A \cap B'$ | $\{2, 4, 8, 10\}$ |
| dans la partie commune | à la fois $A$ et $B$ | $A \cap B$ | $\{6, 12\}$ |
| dans $B$ mais pas dans $A$ | seulement $B$ | $A' \cap B$ | $\{3, 9\}$ |
| à l'extérieur des deux cercles | ni l'un ni l'autre | $(A \cup B)'$ | $\{1, 5, 7, 11\}$ |

Chaque élément de $\xi$ se trouve dans une seule région ; les quatre régions réunies contiennent donc les 12 nombres : $4 + 2 + 2 + 4 = 12$ ✓.

## Dénombrer avec un diagramme de Venn

Quand on additionne $n(A)$ et $n(B)$, les éléments de la partie commune sont comptés **deux fois**. On les soustrait donc une fois :

$$n(A \cup B) = n(A) + n(B) - n(A \cap B)$$

Vérification avec l'exemple corrigé 1 : $6 + 4 - 2 = 8$ ✓.

**Astuce :** pour remplir un diagramme de Venn, commencez toujours par la **partie commune**, puis allez vers l'extérieur.

### Exemple corrigé 2

Dans une classe de S3 de 40 élèves d'une école de Huye, 25 élèves jouent au football ($F$), 18 jouent au volley-ball ($V$) et 7 ne pratiquent aucun de ces deux sports. Combien d'élèves pratiquent les deux ?

- Élèves qui pratiquent au moins un sport : $n(F \cup V) = 40 - 7 = 33$.
- Utilisez la formule : $33 = 25 + 18 - n(F \cap V)$, donc $n(F \cap V) = 43 - 33 = 10$.
- Remplissez le diagramme en partant du centre : les deux $= 10$, football seulement $= 25 - 10 = 15$, volley-ball seulement $= 18 - 10 = 8$, aucun des deux $= 7$.
- Vérification : $15 + 10 + 8 + 7 = 40$ ✓.

### Exemple corrigé 3 : utiliser une inconnue

Une enquête menée auprès de 60 ménages d'un village de Rwamagana a montré que 35 élèvent des vaches, 30 élèvent des chèvres et 5 n'élèvent ni vaches ni chèvres. Soit $x$ le nombre de ménages qui élèvent les deux.

- Vaches seulement $= 35 - x$, les deux $= x$, chèvres seulement $= 30 - x$, aucun des deux $= 5$.
- La somme des quatre régions vaut 60 : $(35 - x) + x + (30 - x) + 5 = 60$.
- On simplifie : $70 - x = 60$, donc $x = 10$.
- Ainsi, 10 ménages élèvent les deux, 25 élèvent seulement des vaches et 20 seulement des chèvres. Vérification : $25 + 10 + 20 + 5 = 60$ ✓.

## Erreurs fréquentes

- Écrire deux fois un élément commun dans une réunion. Chaque élément ne s'écrit qu'une fois.
- Placer la totalité de $n(A)$ dans la région « seulement $A$ ». Soustrayez d'abord la partie commune.
- Oublier la région située à l'extérieur des cercles. « Ni l'un ni l'autre » fait aussi partie de $\xi$.

## Testez-vous

1. $\xi = \{1, 2, \dots, 10\}$, $P = \{\text{nombres premiers}\}$ et $Q = \{\text{nombres impairs}\}$. Écrivez $P \cap Q$ en extension et calculez $n(P \cup Q)$.
2. $n(A) = 14$, $n(B) = 9$ et $n(A \cup B) = 19$. Calculez $n(A \cap B)$.
3. Combien de sous-ensembles l'ensemble $\{x, y, z\}$ possède-t-il ?

*Réponses : 1) $P = \{2, 3, 5, 7\}$ et $Q = \{1, 3, 5, 7, 9\}$, donc $P \cap Q = \{3, 5, 7\}$ et $n(P \cup Q) = 4 + 5 - 3 = 6$ · 2) $14 + 9 - 19 = 4$ · 3) $2^3 = 8$*
