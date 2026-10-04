---
slug: s3-ict-javascript-intro
language: fr
title: "JavaScript : rendez votre page interactive"
summary: Variables, fonctions et événements — écrivez votre premier programme JavaScript qui réagit à un clic sur un bouton.
reviewed: false
---
## Le troisième langage du Web

- **HTML** — la structure
- **CSS** — le style
- **JavaScript** — le comportement (ce qui se passe quand vous cliquez, tapez au clavier ou faites défiler la page)

## Les variables

Une variable stocke une valeur :

```js
let name = "Eric";
let age = 15;
const school = "GS Kigali";   // const : ne peut pas être réaffectée
```

## Opérateurs et décisions

```js
let mark = 72;
if (mark >= 50) {
  console.log("Réussi");
} else {
  console.log("Réessayez");
}
```

## Les fonctions

Une fonction est un bloc de code réutilisable :

```js
function average(a, b, c) {
  return (a + b + c) / 3;
}
average(60, 75, 90);   // 75
```

## Les événements : réagir à l'utilisateur

JavaScript peut trouver un élément HTML et exécuter une fonction quand quelque chose lui arrive :

```js
document.querySelector("#btn").addEventListener("click", sayHello);
```

## Essayez : un calculateur de moyenne

Exécutez le programme, puis améliorez-le : affichez « Réussi » ou « Échec » à côté de la moyenne, et empêchez-le de planter quand une case est vide.

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

## Les boucles

```js
for (let i = 1; i <= 5; i++) {
  console.log(i * i);   // 1 4 9 16 25
}
```

## Testez-vous

1. Quelle est la différence entre `let` et `const` ?
2. Écrivez une fonction `double(n)` qui renvoie le double de `n`.
3. Quelle méthode relie un clic sur un bouton à une fonction ?
