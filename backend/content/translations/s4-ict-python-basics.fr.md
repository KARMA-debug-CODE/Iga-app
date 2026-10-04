---
slug: s4-ict-python-basics
language: fr
title: "Programmer en Python : premiers pas"
summary: Écrire et exécuter de vrais programmes Python à l'aide de variables, de types de données, d'opérateurs, de conditions, de boucles et de fonctions.
reviewed: false
---
## Pourquoi Python ?

**Python** est un langage de programmation facile à lire et à écrire. On l'utilise pour créer des sites web, analyser des données, piloter des robots et apprendre aux ordinateurs à reconnaître des images.

Un **programme** est une liste d'instructions que l'ordinateur exécute dans l'ordre, de haut en bas. Les blocs de code munis d'un bouton **Exécuter** sont des éditeurs interactifs : appuyez sur **Exécuter** pour voir le résultat, modifiez le code, puis exécutez-le à nouveau.

```python-run
print("Muraho, Rwanda!")
print("J'apprends Python.")
```

## Variables et types de données

Une **variable** est un nom qui stocke une valeur. On la crée avec `=`, l'opérateur d'**affectation**. Par exemple, `district = "Huye"` stocke le texte Huye dans une variable appelée `district`.

| Type | Signification | Exemple |
|---|---|---|
| `int` | nombre entier | `850` |
| `float` | nombre décimal | `3.5` |
| `str` | texte (une chaîne de caractères), écrit entre guillemets | `"Huye"` |
| `bool` | vrai ou faux | `True` |

Règles pour les noms de variables : utilisez des lettres, des chiffres et `_` ; ne commencez pas par un chiffre ; pas d'espaces ni de `-` ; et n'utilisez pas un **mot-clé** de Python comme `if`, `for` ou `class`. Python distingue les majuscules des minuscules : `Mark` et `mark` sont donc deux variables différentes. Utilisez `type(value)` pour connaître le type d'une valeur.

## Opérateurs arithmétiques

| Opérateur | Signification | Exemple | Résultat |
|---|---|---|---|
| `+` | addition | `7 + 2` | `9` |
| `-` | soustraction | `7 - 2` | `5` |
| `*` | multiplication | `7 * 2` | `14` |
| `/` | division | `7 / 2` | `3.5` |
| `//` | division entière (quotient) | `7 // 2` | `3` |
| `%` | reste (modulo) | `7 % 2` | `1` |
| `**` | puissance | `7 ** 2` | `49` |

Python respecte l'ordre habituel des opérations : d'abord `**`, puis `*`, `/`, `//`, `%`, et enfin `+` et `-`. L'opérateur `/` donne toujours un `float`.

### Exemple corrigé 1 : le prix d'une course en moto

Supposons qu'une moto facture une prise en charge de 300 FRW, plus 150 FRW par kilomètre. Écrivez un programme pour un trajet de 4,5 km.

```python-run
start_fare = 300  # FRW
per_km = 150  # FRW par km
distance = 4.5  # km

fare = start_fare + per_km * distance
print("Distance :", distance, "km")
print("Prix :", fare, "FRW")
```

Comment cela fonctionne :

1. La multiplication passe avant l'addition : `per_km * distance` $= 150 \times 4.5 = 675$ est donc calculé en premier.
2. Ensuite, `fare` $= 300 + 675 = 975.0$. C'est un `float`, car `distance` est un float.
3. Le programme affiche `Distance : 4.5 km`, puis `Prix : 975.0 FRW`.

Le texte qui suit `#` est un **commentaire**. Python l'ignore ; les commentaires expliquent le code aux personnes qui le lisent.

## Demander une saisie à l'utilisateur

`input()` affiche un message et attend que l'utilisateur tape quelque chose. Cette fonction **renvoie toujours une chaîne de caractères** : convertissez donc les nombres avec `int()` ou `float()` avant de faire des calculs.

```python-run
name = input("Quel est votre prénom ? ")
age = int(input("Quel âge avez-vous ? "))
print("Bonjour", name)
print("Dans 5 ans, votre âge sera", age + 5)
```

Avant d'appuyer sur Exécuter, tapez deux lignes dans la zone **Entrée**, par exemple `Keza` et `16`. La dernière ligne affiche alors `Dans 5 ans, votre âge sera 21`.

## Prendre des décisions : if, elif, else

Une **condition** est une expression qui vaut soit `True` (vrai), soit `False` (faux). On construit des conditions avec les opérateurs de comparaison : `==` (égal à), `!=` (différent de), `<`, `>`, `<=` et `>=`. Attention : `=` stocke une valeur, alors que `==` compare deux valeurs.

Les lignes à l'intérieur d'un bloc `if` doivent être **indentées** (en général de 4 espaces). Python se sert de l'indentation pour savoir quelles lignes appartiennent au bloc.

### Exemple corrigé 2 : une mention à partir d'une note

Une école attribue les mentions ainsi : 80 et plus donne A, de 70 à 79 donne B, de 60 à 69 donne C, de 50 à 59 donne D, et moins de 50 donne F.

```python-run
mark = 72

if mark >= 80:
    grade = "A"
elif mark >= 70:
    grade = "B"
elif mark >= 60:
    grade = "C"
elif mark >= 50:
    grade = "D"
else:
    grade = "F"

print("Note :", mark, "Mention :", grade)
```

Suivons l'exécution : `72 >= 80` ? Faux. `72 >= 70` ? Vrai, donc `grade = "B"` et Python saute les branches restantes. Le programme affiche `Note : 72 Mention : B`. Remplacez `mark` par 45, puis par 80, et prédisez chaque affichage avant d'exécuter le code.

## Répéter : les boucles for et while

Une **boucle for** se répète une fois pour chaque valeur d'une séquence. `range(1, 6)` donne 1, 2, 3, 4, 5. Elle s'arrête **avant** 6.

### Exemple corrigé 3 : épargner dans un ikimina

Aline épargne 2 000 FRW chaque semaine dans son groupe d'épargne (*ikimina*). Combien a-t-elle épargné au bout de 5 semaines ?

```python-run
savings = 0
for week in range(1, 6):
    savings = savings + 2000
    print("Semaine", week, "épargne :", savings, "FRW")

print("Total :", savings, "FRW")
```

| `week` | `savings` après ce passage dans la boucle |
|---|---|
| 1 | 2000 |
| 2 | 4000 |
| 3 | 6000 |
| 4 | 8000 |
| 5 | 10000 |

La dernière ligne affichée est `Total : 10000 FRW`.

Une **boucle while** se répète tant que sa condition est vraie. Combien de semaines faut-il pour atteindre 15 000 FRW en épargnant 2 500 FRW par semaine ?

```python-run
target = 15000
savings = 0
weeks = 0
while savings < target:
    savings = savings + 2500
    weeks = weeks + 1
print("Semaines nécessaires :", weeks)
```

Le programme affiche `Semaines nécessaires : 6`, car $6 \times 2500 = 15000$. Quelque chose doit changer à l'intérieur d'une boucle while, sinon la boucle tourne indéfiniment. Si cela arrive, appuyez sur **Arrêter**.

## Listes et fonctions

Une **liste** stocke plusieurs valeurs dans l'ordre : `marks = [65, 78, 54, 90]`. Alors `len(marks)` vaut 4, `sum(marks)` vaut 287 et `max(marks)` vaut 90.

Une **fonction** est un bloc de code nommé que l'on peut réutiliser. On la définit avec le mot-clé `def` et on renvoie un résultat avec `return` :

```python-run
def average(numbers):
    return sum(numbers) / len(numbers)


marks = [65, 78, 54, 90]
print("Note moyenne :", average(marks))
print("Note la plus haute :", max(marks))
```

Comme $287 \div 4 = 71.75$, le programme affiche `Note moyenne : 71.75`.

## Sécurité en salle informatique

Gardez la nourriture et les boissons loin des claviers, ne touchez jamais les prises ou les câbles avec les mains mouillées, signalez les prises endommagées à votre enseignant, et reposez vos yeux en détournant le regard de l'écran toutes les 20 à 30 minutes.

## Testez-vous

1. Qu'affiche `print(17 // 5, 17 % 5)` ?
2. Quel est le type de données de la valeur `4.0` ?
3. Combien de fois le corps de `for i in range(2, 8):` est-il exécuté ?

*Réponses : 1) `3 2` · 2) `float` · 3) 6 fois (i = 2, 3, 4, 5, 6, 7)*
