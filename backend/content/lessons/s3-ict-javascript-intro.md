---
slug: s3-ict-javascript-intro
subject: ict
grade: S3
unit: 2
order: 1
title: "JavaScript: make your page interactive"
summary: Variables, functions and events — write your first JavaScript program that reacts to a button click.
minutes: 35
simulations:
---
## The third language of the web

- **HTML** — structure
- **CSS** — style
- **JavaScript** — behaviour (what happens when you click, type or scroll)

## Variables

A variable stores a value:

```js
let name = "Eric";
let age = 15;
const school = "GS Kigali";   // const: cannot be reassigned
```

## Operators and decisions

```js
let mark = 72;
if (mark >= 50) {
  console.log("Pass");
} else {
  console.log("Try again");
}
```

## Functions

A function is a reusable block of code:

```js
function average(a, b, c) {
  return (a + b + c) / 3;
}
average(60, 75, 90);   // 75
```

## Events: reacting to the user

JavaScript can find an HTML element and run a function when something happens to it:

```js
document.querySelector("#btn").addEventListener("click", sayHello);
```

## Try it: an average calculator

Run the program, then improve it: show "Pass" or "Fail" next to the average, and stop it crashing when a box is empty.

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <h2>Average calculator</h2>
  <input id="a" type="number" placeholder="Mark 1">
  <input id="b" type="number" placeholder="Mark 2">
  <input id="c" type="number" placeholder="Mark 3">
  <button id="btn">Calculate</button>
  <p id="result"></p>

  <script>
    function calculate() {
      const a = Number(document.querySelector("#a").value);
      const b = Number(document.querySelector("#b").value);
      const c = Number(document.querySelector("#c").value);
      const avg = (a + b + c) / 3;
      document.querySelector("#result").textContent = "Average: " + avg.toFixed(1);
    }
    document.querySelector("#btn").addEventListener("click", calculate);
  </script>
</body>
</html>
```

## Loops

```js
for (let i = 1; i <= 5; i++) {
  console.log(i * i);   // 1 4 9 16 25
}
```

## Check yourself

1. What is the difference between `let` and `const`?
2. Write a function `double(n)` that returns twice `n`.
3. Which method connects a button click to a function?
