---
slug: s3-ict-javascript-intro
language: fr
title: "JavaScript : rendez votre page interactive"
summary: Variables, types de données, décisions, fonctions, boucles et événements — écrivez votre premier programme JavaScript qui réagit à un clic sur un bouton.
reviewed: false
---
## Le troisième langage du Web

Une page Web est construite avec trois langages qui travaillent ensemble :

- **HTML** : la structure (titres, paragraphes, boutons, cases où l'on écrit)
- **CSS** : le style (couleurs, tailles, mise en page)
- **JavaScript** : le comportement (ce qui se passe quand vous cliquez, tapez au clavier ou faites défiler la page)

Quand vous touchez un bouton et qu'un message apparaît aussitôt, sans qu'une nouvelle page se charge, c'est en général JavaScript qui travaille. Il s'exécute dans le **navigateur**, l'application qui sert à ouvrir les pages Web.

Un **programme** est une liste de consignes que l'ordinateur exécute une par une, de haut en bas. Chaque consigne s'appelle une **instruction** (en anglais *statement*), et on termine chacune par un point-virgule `;`. Dans une page Web, le JavaScript se place entre les balises `<script>` et `</script>`, en général juste avant `</body>`.

## Les variables

Une **variable** est une boîte qui porte un nom et qui stocke une valeur. On la crée avec `let` ou `const` :

```js
let name = "Eric";
let age = 15;
const school = "GS Kigali";   // const : ne peut pas être réaffectée
age = 16;                     // autorisé, car age a été créée avec let
```

- `let` crée une variable dont la valeur peut changer plus tard.
- `const` crée une **constante** : une fois qu'elle a une valeur, on ne peut pas lui en donner une nouvelle. `school = "GS Huye";` provoquerait une erreur.
- Dans du code plus ancien, on trouve souvent `var` à la place. Comme `let`, il crée une variable que l'on peut modifier. Dans cette leçon, nous utilisons seulement `let` et `const`.
- `=` veut dire « range cette valeur ». C'est l'opérateur d'**affectation**, et il ne veut **pas** dire « est égal à ».
- Le texte placé après `//` est un **commentaire**. L'ordinateur l'ignore ; les commentaires expliquent le code aux personnes.

Un nom peut contenir des lettres, des chiffres et `_`, mais il ne doit pas commencer par un chiffre ni contenir d'espace. JavaScript **distingue les majuscules des minuscules** : `age`, `Age` et `AGE` sont trois noms différents.

## Les types de données : texte, nombres et vrai/faux

Chaque valeur a un **type de données**. Vous en avez besoin de trois :

| Type | Signification | Exemples |
|---|---|---|
| chaîne (string) | du texte, entre guillemets | `"Keza"`, `"Musanze"`, `"500"` |
| nombre (number) | un nombre, sans guillemets | `500`, `3.5`, `-2` |
| booléen (boolean) | seulement `true` (vrai) ou `false` (faux) | `72 >= 50` donne `true` |

Attention aux guillemets ! `500` est un nombre, mais `"500"` est une **chaîne de caractères** (du texte) qui ressemble seulement à un nombre. C'est important, car `+` fait deux travaux différents :

- Avec deux nombres, `+` additionne : `5 + 3` donne `8`.
- Avec des chaînes, `+` les **colle** bout à bout : `"5" + "3"` donne `"53"`. Coller des chaînes s'appelle la **concaténation**.

Pour transformer une chaîne en nombre, on utilise `Number()`. Ainsi, `Number("5") + Number("3")` donne `8`. Si la chaîne n'est pas un nombre, `Number("abc")` donne `NaN`, qui veut dire « Not a Number » (« pas un nombre »).

### Exemple corrigé 1 : pourquoi 500 + 300 a donné 500300

Keza vend des tomates au marché. Elle tape deux ventes, 500 FRW et 300 FRW, dans deux cases de sa page Web. Tout ce qu'on lit dans une case est une chaîne, donc son programme reçoit `"500"` et `"300"`.

1. Son premier essai est `let total = "500" + "300";`. Les deux valeurs sont des chaînes, donc `+` les colle : `total` vaut `"500300"`. Faux !
2. La correction consiste à convertir chaque chaîne d'abord : `let total = Number("500") + Number("300");`.
3. `Number("500")` donne le nombre 500, et `Number("300")` donne 300.
4. Maintenant, `+` a deux nombres, donc il additionne : `500 + 300` donne `800`.

Vérification : 500 FRW + 300 FRW = 800 FRW. C'est juste. La règle : **le texte d'une case est toujours une chaîne, donc convertissez-le avec `Number()` avant de calculer.**

## Afficher les résultats sur la page

Beaucoup de livres utilisent `console.log()` pour afficher les résultats. La **console** est un panneau caché pour les programmeurs, et les éditeurs de cette leçon ne peuvent pas l'afficher : **ce qu'écrit `console.log()` n'apparaîtra pas**. Utilisez plutôt l'un de ces moyens :

- **`textContent`** met du texte dans un élément de la page, par exemple un paragraphe.
- **`alert("Muraho !")`** ouvre une petite boîte de message, que l'on ferme avec OK.

Les cadres marqués **HTML · CSS · JS** sont des éditeurs en direct. Modifiez le code, puis appuyez sur **Exécuter** pour voir le résultat. Si vous vous perdez, **Réinitialiser** remet le code de départ.

Dans le code ci-dessous, `document.querySelector("#line1")` trouve le paragraphe dont l'`id` est `line1` (le `#` veut dire « id »). Ensuite, `.textContent = ...` met du texte dans ce paragraphe. Essayez maintenant :

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <h2>Mon premier JavaScript</h2>
  <p id="line1"></p>
  <p id="line2"></p>
  <p id="line3"></p>
  <p id="line4"></p>

  <script>
    let name = "Keza";
    document.querySelector("#line1").textContent = "Muraho, " + name + " !";
    document.querySelector("#line2").textContent = "Chaînes collées : " + ("5" + "3");
    document.querySelector("#line3").textContent = "Nombres additionnés : " + (Number("5") + Number("3"));
    document.querySelector("#line4").textContent = "Type de 15 : " + typeof 15;
  </script>
</body>
</html>
```

Vous devriez voir `Muraho, Keza !`, puis `53`, `8` et `number` (`typeof` donne le type de données d'une valeur). Remplacez `name` par votre propre prénom et exécutez de nouveau.

## Opérateurs et décisions

Les **opérateurs** sont des symboles qui font quelque chose avec des valeurs :

| Opérateur | Signification | Exemple | Résultat |
|---|---|---|---|
| `+` `-` `*` `/` | additionner, soustraire, multiplier, diviser | `7 * 2` | `14` |
| `%` | reste de la division | `7 % 2` | `1` |
| `===` | est égal à | `5 === 5` | `true` |
| `!==` | n'est pas égal à | `5 !== 5` | `false` |
| `>` `<` | supérieur à, inférieur à | `3 > 8` | `false` |
| `>=` `<=` | au moins, au plus | `72 >= 50` | `true` |

Comme en mathématiques, `*` et `/` passent avant `+` et `-`, sauf s'il y a des parenthèses. Ainsi, `3 * 4 + 1` vaut 12 + 1 = 13, mais `3 * (4 + 1)` vaut 3 × 5 = 15.

Une **instruction if** permet de prendre une décision. Elle teste une **condition**, une question dont la réponse est `true` (vrai) ou `false` (faux) :

```js
let mark = 72;
let message;
if (mark >= 50) {
  message = "Réussi";
} else {
  message = "Réessayez";
}
```

La ligne `let message;` crée une variable qui n'a pas encore de valeur ; l'instruction `if` lui en donne une. Si la condition est `true`, le code dans la première paire d'accolades `{ }` s'exécute. Si elle est `false`, c'est le code après `else` qui s'exécute. Un seul des deux blocs s'exécute.

### Exemple corrigé 2 : suivre un if/else pas à pas

**Faire la trace** d'un code veut dire le suivre pas à pas, comme le fait l'ordinateur.

**Quand la note est 72 :**

1. `mark` stocke 72, donc la condition devient `72 >= 50`.
2. 72 est-il au moins égal à 50 ? Oui, donc la condition est `true`.
3. Le premier bloc s'exécute et le bloc `else` est sauté. `message` vaut `"Réussi"`.

**Quand la note est 45 :**

1. La condition devient `45 >= 50`. Elle est `false`, car 45 est plus petit que 50.
2. Le premier bloc est sauté et le bloc `else` s'exécute. `message` vaut `"Réessayez"`.

Vérification : une note d'exactement 50 donne `50 >= 50`, qui est `true`, car `>=` veut dire « supérieur **ou égal** à ». Donc 50 donne `"Réussi"`. C'est juste.

## Les fonctions

Une **fonction** est un bloc de code qui porte un nom et qui fait un seul travail. On l'écrit une fois et on l'utilise autant de fois qu'on veut.

```js
function average(a, b, c) {
  return (a + b + c) / 3;
}
let result = average(60, 75, 90);   // result vaut 75
```

- `function average(a, b, c)` **définit** la fonction. `a`, `b` et `c` sont ses **paramètres** : des boîtes vides qui vont recevoir des valeurs.
- `return` renvoie une réponse à l'endroit où la fonction a été utilisée.
- `average(60, 75, 90)` **appelle** (exécute) la fonction. 60, 75 et 90 sont les **arguments**. Ils vont dans `a`, `b` et `c`, dans cet ordre.

Une fonction ne fait rien tant qu'on ne l'appelle pas. Sans les parenthèses autour de `a + b + c`, seul `c` serait divisé par 3.

### Exemple corrigé 3 : une facture au marché

Uwase achète 3 kg de tomates à 800 FRW le kilo et paie 500 FRW pour rentrer en moto. Cette fonction calcule sa facture :

```js
function bill(pricePerKg, kg, transport) {
  return pricePerKg * kg + transport;
}
let total = bill(800, 3, 500);
```

Que contient `total` ?

1. L'appel copie les arguments dans les paramètres, dans l'ordre : `pricePerKg` vaut 800, `kg` vaut 3 et `transport` vaut 500.
2. La fonction calcule `800 * 3 + 500`. La multiplication passe d'abord : 800 × 3 = 2400.
3. Puis l'addition : 2400 + 500 = 2900.
4. `return` renvoie 2900, donc `total` stocke `2900`.

Vérification : 3 kg coûtent 2 400 FRW, et 500 FRW de transport donnent 2 900 FRW. C'est juste.

## Les boucles : répéter du code

Une **boucle** répète du code, pour ne pas avoir à écrire la même ligne de nombreuses fois. La plus courante est la **boucle for** :

```js
let text = "";
for (let i = 1; i <= 5; i++) {
  text = text + (i * i) + " ";
}
// text vaut maintenant "1 4 9 16 25 "
```

Les parenthèses après `for` contiennent trois parties, séparées par des points-virgules :

1. **Départ :** `let i = 1` crée un compteur `i` qui commence à 1.
2. **Condition :** la boucle continue tant que `i <= 5` est `true`.
3. **Pas :** `i++` ajoute 1 à `i` après chaque tour. C'est une façon courte d'écrire `i = i + 1`.

### Exemple corrigé 4 : un tableau de suivi pour une boucle

Un **tableau de suivi** note la valeur des variables après chaque tour de boucle. `text` commence à `""`, une chaîne vide.

| Tour | `i` | `i * i` | `text` après le tour |
|---|---|---|---|
| 1 | 1 | 1 | `"1 "` |
| 2 | 2 | 4 | `"1 4 "` |
| 3 | 3 | 9 | `"1 4 9 "` |
| 4 | 4 | 16 | `"1 4 9 16 "` |
| 5 | 5 | 25 | `"1 4 9 16 25 "` |

Après le tour 5, `i++` donne à `i` la valeur 6. Alors `6 <= 5` est `false`, et la boucle s'arrête.

Vérification : la boucle a tourné 5 fois, et le dernier carré est 5 × 5 = 25. C'est juste.

On peut aussi compter à partir de 0 : `for (let i = 0; i < 5; i++)` tourne aussi 5 fois, avec `i` = 0, 1, 2, 3, 4. Elle s'arrête quand `i` vaut 5, car `5 < 5` est `false`.

Exécutez la boucle ci-dessous. Remplacez le `5` par `10`, et prévoyez le dernier nombre avant d'appuyer sur Exécuter.

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <h2>Les nombres carrés</h2>
  <p id="out"></p>

  <script>
    let text = "";
    for (let i = 1; i <= 5; i++) {
      text = text + (i * i) + " ";
    }
    document.querySelector("#out").textContent = text;
  </script>
</body>
</html>
```

## Les événements : réagir à l'utilisateur

Un **événement** est quelque chose qui se passe sur la page, comme un clic, une pression du doigt sur l'écran ou l'appui sur une touche du clavier. JavaScript peut trouver un élément et exécuter une fonction quand un événement lui arrive :

```js
function sayHello() {
  document.querySelector("#msg").textContent = "Muraho ! Bienvenue sur Iga.";
}
document.querySelector("#btn").addEventListener("click", sayHello);
```

Lisez la dernière ligne de gauche à droite :

1. `document` est toute la page Web.
2. `querySelector("#btn")` trouve l'élément dont l'`id` est `btn`. Le `#` veut dire « id ».
3. `addEventListener("click", sayHello)` veut dire « chaque fois qu'on clique dessus, exécute `sayHello` ».

On écrit `sayHello` **sans** parenthèses : on confie la fonction, pour qu'elle soit exécutée plus tard, à chaque clic. `sayHello()` avec des parenthèses l'exécuterait une seule fois, tout de suite, avant que quelqu'un clique.

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <button id="btn">Dire bonjour</button>
  <p id="msg"></p>

  <script>
    function sayHello() {
      document.querySelector("#msg").textContent = "Muraho ! Bienvenue sur Iga.";
    }
    document.querySelector("#btn").addEventListener("click", sayHello);
  </script>
</body>
</html>
```

Appuyez sur Exécuter, puis touchez **Dire bonjour**. Modifiez le message, ou remplacez la ligne qui est dans `sayHello` par `alert("Muraho !");`.

## Projet : un calculateur de moyenne

Maintenant, rassemblez tout. Exécutez le programme, tapez trois notes, puis appuyez sur **Calculer**.

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <h2>Calculateur de moyenne</h2>
  <input id="a" type="number" placeholder="Note 1">
  <input id="b" type="number" placeholder="Note 2">
  <input id="c" type="number" placeholder="Note 3">
  <button id="btn">Calculer</button>
  <p id="result"></p>

  <script>
    function calculate() {
      const a = Number(document.querySelector("#a").value);
      const b = Number(document.querySelector("#b").value);
      const c = Number(document.querySelector("#c").value);
      const avg = (a + b + c) / 3;
      document.querySelector("#result").textContent = "Moyenne : " + avg.toFixed(1);
    }
    document.querySelector("#btn").addEventListener("click", calculate);
  </script>
</body>
</html>
```

### Exemple corrigé 5 : comment marche le calculateur

Voici ce qui se passe quand vous tapez 70, 85 et 92 puis appuyez sur Calculer.

1. La dernière ligne, `addEventListener("click", calculate)`, attendait. Votre clic lui fait exécuter `calculate`.
2. `document.querySelector("#a")` trouve la case dont l'`id` est `"a"`.
3. `.value` lit ce qui est tapé dedans. C'est toujours une chaîne, donc c'est `"70"`.
4. `Number(...)` transforme `"70"` en nombre 70, et `const a = ...` le stocke. Les deux lignes suivantes font la même chose pour 85 et 92.
5. `(a + b + c) / 3` vaut 247 ÷ 3 = 82,333…, rangé dans `avg`.
6. `avg.toFixed(1)` arrondit à **1 décimale** et donne le texte `"82.3"` (JavaScript écrit les décimales avec un point).
7. `"Moyenne : " + "82.3"` colle les chaînes et donne `"Moyenne : 82.3"`.
8. `textContent` met ce texte dans le paragraphe dont l'`id` est `"result"`, et il apparaît sur la page.

Vérification : 70 + 85 + 92 = 247, et 247 ÷ 3 ≈ 82,3. C'est juste.

Sans `Number()`, `a + b + c` collerait `"70"`, `"85"` et `"92"` en `"708592"`, et la page afficherait `Moyenne : 236197.3`. Cela n'a aucun sens !

## Améliorez-le : Réussi ou Échec, et cases vides

Il vous reste deux problèmes à corriger :

1. Affichez « Réussi » (une moyenne de 50 ou plus) ou « Échec » à côté de la moyenne.
2. Laissez une case vide et appuyez sur Calculer. Le programme ne plante pas, mais la réponse est fausse ! `Number("")` vaut `0`, donc une case vide compte comme une note de 0.

Essayez d'abord vous-même dans le calculateur ci-dessus. Quelques indices :

- Rangez la `.value` de chaque case dans une variable **avant** de la convertir.
- Une case vide a pour valeur `""`, une chaîne vide. Testez-la avec `=== ""`.
- `||` veut dire « ou » : `x === "" || y === ""` est `true` si **l'une ou l'autre** valeur est vide.
- Dans une fonction, `return;` arrête la fonction immédiatement.

Voici une solution possible. Comparez-la avec la vôtre :

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <h2>Calculateur de moyenne</h2>
  <input id="a" type="number" placeholder="Note 1">
  <input id="b" type="number" placeholder="Note 2">
  <input id="c" type="number" placeholder="Note 3">
  <button id="btn">Calculer</button>
  <p id="result"></p>

  <script>
    function calculate() {
      const aText = document.querySelector("#a").value;
      const bText = document.querySelector("#b").value;
      const cText = document.querySelector("#c").value;

      // Arrêter tout de suite si une case est vide
      if (aText === "" || bText === "" || cText === "") {
        document.querySelector("#result").textContent = "Veuillez taper les trois notes.";
        return;
      }

      const avg = (Number(aText) + Number(bText) + Number(cText)) / 3;
      let verdict;
      if (avg >= 50) {
        verdict = "Réussi";
      } else {
        verdict = "Échec";
      }
      document.querySelector("#result").textContent =
        "Moyenne : " + avg.toFixed(1) + " (" + verdict + ")";
    }
    document.querySelector("#btn").addEventListener("click", calculate);
  </script>
</body>
</html>
```

Testez-la avec 55, 48 et 40 : la moyenne est 143 ÷ 3 ≈ 47,7, donc vous devriez voir `Moyenne : 47.7 (Échec)`. Laissez ensuite une case vide et vérifiez que le message apparaît. Si vos cases acceptent n'importe quel texte (`type="text"`), testez aussi `isNaN(Number(aText))`, qui vaut `true` quand quelqu'un tape quelque chose comme `abc`.

## Erreurs fréquentes

- **`=` au lieu de `===`.** `if (mark = 50)` range 50 dans `mark` au lieu de le comparer. Utilisez `===` pour comparer.
- **Mauvaises majuscules.** Écrivez `Number`, `querySelector`, `textContent` et `addEventListener` exactement ainsi ; `textcontent` ne marchera pas.
- **Guillemets ou parenthèses manquants.** Chaque `"` a besoin de son partenaire, et chaque `(` et `{` a besoin de son `)` ou `}`. Si rien ne se passe, comptez-les.
- **`calculate()` au lieu de `calculate` dans `addEventListener`.** Avec les parenthèses, la fonction s'exécute une fois au chargement de la page, et non à chaque clic.
- **Oublier `Number()`.** Les valeurs des cases sont des chaînes, donc `"5" + "3"` donne `"53"`.
- **Coller avant d'additionner.** `"Total : " + 2 + 3` donne `"Total : 23"`, car JavaScript travaille de gauche à droite et le texte vient en premier. Écrivez `"Total : " + (2 + 3)` pour obtenir `"Total : 5"`.
- **Oublier le `#`.** Pour `id="result"`, écrivez `querySelector("#result")`.

## Testez-vous

1. Quelle est la différence entre `let` et `const` ?
2. Écrivez une fonction `double(n)` qui renvoie le double de `n`.
3. Quelle méthode relie un clic sur un bouton à une fonction ?
4. Prévoyez le résultat de `"4" + "6"` et de `Number("4") + Number("6")`.
5. Que renvoie `f(2, 5)` si `function f(a, b) { return a * b + 1; }` ?
6. Combien de fois la boucle `for (let i = 0; i < 5; i++)` tourne-t-elle, et quelles valeurs `i` prend-il ?
7. Qu'est-ce qui ne va pas dans `button.addEventListener("click", calculate());` ?
8. Prévoyez ce que donne `"Total : " + 2 + 3`. Comment lui faire donner `"Total : 5"` ?

*Réponses : 1) une variable créée avec `let` peut recevoir une nouvelle valeur plus tard ; une `const` ne peut pas être réaffectée · 2) `function double(n) { return n * 2; }` · 3) `addEventListener`, par exemple `button.addEventListener("click", sayHello)` · 4) `"46"` (les chaînes sont collées) et `10` · 5) `11`, car 2 × 5 + 1 = 11 · 6) 5 fois, avec `i` = 0, 1, 2, 3, 4 · 7) les parenthèses exécutent `calculate` une fois, tout de suite ; écrivez `calculate` sans parenthèses pour qu'elle s'exécute à chaque clic · 8) `"Total : 23"` ; utilisez des parenthèses : `"Total : " + (2 + 3)`*
