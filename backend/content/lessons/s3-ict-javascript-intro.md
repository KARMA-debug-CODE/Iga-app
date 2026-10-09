---
slug: s3-ict-javascript-intro
subject: ict
grade: S3
unit: 4
order: 1
title: "JavaScript: make your page interactive"
summary: Variables, data types, decisions, functions, loops and events — write your first JavaScript program that reacts to a button click.
minutes: 50
simulations:
---
## The third language of the web

A web page is built with three languages that work together:

- **HTML**: the structure (headings, paragraphs, buttons, boxes to type in)
- **CSS**: the style (colours, sizes, layout)
- **JavaScript**: the behaviour (what happens when you click, type or scroll)

When you tap a button and a message appears at once, without a new page loading, JavaScript is usually doing the work. It runs inside the **browser**, the app you use to open web pages.

A **program** is a list of instructions that the computer carries out in order, from top to bottom. Each instruction is a **statement**, and we end each one with a semicolon `;`. On a web page, JavaScript goes between `<script>` and `</script>` tags, usually just before `</body>`.

## Variables

A **variable** is a named box that stores a value. You create one with `let` or `const`:

```js
let name = "Eric";
let age = 15;
const school = "GS Kigali";   // const: cannot be reassigned
age = 16;                     // allowed, because age was made with let
```

- `let` makes a variable whose value can change later.
- `const` makes a **constant**: once it has a value, you cannot give it a new one. `school = "GS Huye";` would cause an error.
- Older code often uses `var` instead. Like `let`, it makes a variable that can be changed. In this lesson we use only `let` and `const`.
- `=` means "store this value". It is the **assignment** operator, and it does **not** mean "is equal to".
- Text after `//` is a **comment**. The computer ignores it; comments explain the code to people.

Names can use letters, digits and `_`, but must not start with a digit or contain spaces. JavaScript is **case-sensitive**: `age`, `Age` and `AGE` are three different names.

## Data types: text, numbers and true/false

Every value has a **data type**. You need three of them:

| Type | Meaning | Examples |
|---|---|---|
| string | text, inside quotes | `"Keza"`, `"Musanze"`, `"500"` |
| number | a number, no quotes | `500`, `3.5`, `-2` |
| boolean | only `true` or `false` | `72 >= 50` gives `true` |

Watch the quotes! `500` is a number, but `"500"` is a **string** (text) that only looks like a number. This matters because `+` does two different jobs:

- With two numbers, `+` adds: `5 + 3` gives `8`.
- With strings, `+` **joins** them end to end: `"5" + "3"` gives `"53"`. Joining strings is called **concatenation**.

To turn a string into a number, use `Number()`. So `Number("5") + Number("3")` gives `8`. If the string is not a number, `Number("abc")` gives `NaN`, which means "Not a Number".

### Worked example 1: why 500 + 300 gave 500300

Keza sells tomatoes at the market. She types two sales, 500 FRW and 300 FRW, into two boxes on her web page. Anything read from a box is a string, so her program receives `"500"` and `"300"`.

1. Her first try is `let total = "500" + "300";`. Both values are strings, so `+` joins them: `total` is `"500300"`. Wrong!
2. The fix is to convert each string first: `let total = Number("500") + Number("300");`.
3. `Number("500")` gives the number 500, and `Number("300")` gives 300.
4. Now `+` has two numbers, so it adds: `500 + 300` gives `800`.

Check: 500 FRW + 300 FRW = 800 FRW ✓. The rule: **text from a box is always a string, so convert it with `Number()` before you do maths.**

## Showing results on the page

Many books use `console.log()` to show results. The **console** is a hidden panel for programmers, and the editors in this lesson cannot show it, so **`console.log()` output will not appear**. Use one of these instead:

- **`textContent`** puts text inside an element on the page, such as a paragraph.
- **`alert("Muraho!")`** pops up a small message box, which you close with OK.

The boxes marked **HTML · CSS · JS** are live editors. Change the code, then press **Run** to see the result. If you get lost, **Reset** brings back the original code.

In the code below, `document.querySelector("#line1")` finds the paragraph whose `id` is `line1` (the `#` means "id"). Then `.textContent = ...` puts text inside that paragraph. Try it now:

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <h2>My first JavaScript</h2>
  <p id="line1"></p>
  <p id="line2"></p>
  <p id="line3"></p>
  <p id="line4"></p>

  <script>
    let name = "Keza";
    document.querySelector("#line1").textContent = "Muraho, " + name + "!";
    document.querySelector("#line2").textContent = "Joining strings: " + ("5" + "3");
    document.querySelector("#line3").textContent = "Adding numbers: " + (Number("5") + Number("3"));
    document.querySelector("#line4").textContent = "Type of 15: " + typeof 15;
  </script>
</body>
</html>
```

You should see `Muraho, Keza!`, then `53`, `8` and `number` (`typeof` gives the data type of a value). Change `name` to your own name and run it again.

## Operators and decisions

**Operators** are symbols that do something with values:

| Operator | Meaning | Example | Result |
|---|---|---|---|
| `+` `-` `*` `/` | add, subtract, multiply, divide | `7 * 2` | `14` |
| `%` | remainder after dividing | `7 % 2` | `1` |
| `===` | is equal to | `5 === 5` | `true` |
| `!==` | is not equal to | `5 !== 5` | `false` |
| `>` `<` | greater than, less than | `3 > 8` | `false` |
| `>=` `<=` | at least, at most | `72 >= 50` | `true` |

As in maths, `*` and `/` come before `+` and `-`, unless there are brackets. So `3 * 4 + 1` is 12 + 1 = 13, but `3 * (4 + 1)` is 3 × 5 = 15.

An **if statement** makes a decision. It checks a **condition**, a question whose answer is `true` or `false`:

```js
let mark = 72;
let message;
if (mark >= 50) {
  message = "Pass";
} else {
  message = "Try again";
}
```

The line `let message;` creates a variable with no value yet; the `if` statement gives it one. If the condition is `true`, the code in the first pair of curly brackets `{ }` runs. If it is `false`, the code after `else` runs. Only one of the two blocks runs.

### Worked example 2: tracing if/else

To **trace** code means to follow it step by step, as the computer does.

**When the mark is 72:**

1. `mark` stores 72, so the condition becomes `72 >= 50`.
2. Is 72 at least 50? Yes, so the condition is `true`.
3. The first block runs, and the `else` block is skipped. `message` is `"Pass"`.

**When the mark is 45:**

1. The condition becomes `45 >= 50`. This is `false`, because 45 is less than 50.
2. The first block is skipped, and the `else` block runs. `message` is `"Try again"`.

Check: a mark of exactly 50 gives `50 >= 50`, which is `true`, because `>=` means "greater than **or equal to**". So 50 gives `"Pass"` ✓.

## Functions

A **function** is a named block of code that does one job. You write it once and use it many times.

```js
function average(a, b, c) {
  return (a + b + c) / 3;
}
let result = average(60, 75, 90);   // result is 75
```

- `function average(a, b, c)` **defines** the function. `a`, `b` and `c` are its **parameters**: empty boxes that will receive values.
- `return` sends an answer back to where the function was used.
- `average(60, 75, 90)` **calls** (runs) the function. 60, 75 and 90 are the **arguments**. They go into `a`, `b` and `c`, in that order.

A function does nothing until you call it. Without the brackets around `a + b + c`, only `c` would be divided by 3.

### Worked example 3: a market bill

Uwase buys 3 kg of tomatoes at 800 FRW per kg and pays 500 FRW for the moto home. This function works out her bill:

```js
function bill(pricePerKg, kg, transport) {
  return pricePerKg * kg + transport;
}
let total = bill(800, 3, 500);
```

What is stored in `total`?

1. The call copies the arguments into the parameters, in order: `pricePerKg` is 800, `kg` is 3 and `transport` is 500.
2. The function works out `800 * 3 + 500`. Multiplication comes first: 800 × 3 = 2400.
3. Then the addition: 2400 + 500 = 2900.
4. `return` sends 2900 back, so `total` stores `2900`.

Check: 3 kg cost 2,400 FRW, and 500 FRW for transport makes 2,900 FRW ✓.

## Loops: repeating code

A **loop** repeats code, so you do not have to write the same line many times. The most common one is the **for loop**:

```js
let text = "";
for (let i = 1; i <= 5; i++) {
  text = text + (i * i) + " ";
}
// text is now "1 4 9 16 25 "
```

The brackets after `for` hold three parts, separated by semicolons:

1. **Start:** `let i = 1` creates a counter `i` that starts at 1.
2. **Condition:** the loop keeps going while `i <= 5` is `true`.
3. **Step:** `i++` adds 1 to `i` after each pass. It is short for `i = i + 1`.

### Worked example 4: a trace table for a loop

A **trace table** records the variables after each pass of a loop. `text` starts as `""`, an empty string.

| Pass | `i` | `i * i` | `text` after the pass |
|---|---|---|---|
| 1 | 1 | 1 | `"1 "` |
| 2 | 2 | 4 | `"1 4 "` |
| 3 | 3 | 9 | `"1 4 9 "` |
| 4 | 4 | 16 | `"1 4 9 16 "` |
| 5 | 5 | 25 | `"1 4 9 16 25 "` |

After pass 5, `i++` makes `i` equal to 6. Now `6 <= 5` is `false`, so the loop stops.

Check: the loop ran 5 times, and the last square is 5 × 5 = 25 ✓.

Counting can also start at 0: `for (let i = 0; i < 5; i++)` also runs 5 times, with `i` = 0, 1, 2, 3, 4. It stops when `i` is 5, because `5 < 5` is `false`.

Run the loop below. Change the `5` to `10`, and predict the last number before you press Run.

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <h2>Square numbers</h2>
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

## Events: reacting to the user

An **event** is something that happens on the page, such as a click, a tap or a key press. JavaScript can find an element and run a function when an event happens to it:

```js
function sayHello() {
  document.querySelector("#msg").textContent = "Muraho! Welcome to Iga.";
}
document.querySelector("#btn").addEventListener("click", sayHello);
```

Read the last line from left to right:

1. `document` is the whole web page.
2. `querySelector("#btn")` finds the element whose `id` is `btn`. The `#` means "id".
3. `addEventListener("click", sayHello)` means "every time this is clicked, run `sayHello`".

We write `sayHello` **without** brackets, which hands the function over to run later, on each click. `sayHello()` with brackets would run it once, straight away, before anyone clicks.

```playground html
<!DOCTYPE html>
<html>
<body style="font-family: system-ui; padding: 16px">
  <button id="btn">Say hello</button>
  <p id="msg"></p>

  <script>
    function sayHello() {
      document.querySelector("#msg").textContent = "Muraho! Welcome to Iga.";
    }
    document.querySelector("#btn").addEventListener("click", sayHello);
  </script>
</body>
</html>
```

Press Run, then tap **Say hello**. Change the message, or replace the line inside `sayHello` with `alert("Muraho!");`.

## Project: an average calculator

Now put it all together. Run the program, type three marks, then press **Calculate**.

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

### Worked example 5: how the calculator works

Here is what happens when you type 70, 85 and 92 and press Calculate.

1. The last line, `addEventListener("click", calculate)`, has been waiting. Your click makes it run `calculate`.
2. `document.querySelector("#a")` finds the input box with `id="a"`.
3. `.value` reads what is typed in it. It is always a string, so it is `"70"`.
4. `Number(...)` turns `"70"` into the number 70, and `const a = ...` stores it. The next two lines do the same for 85 and 92.
5. `(a + b + c) / 3` is 247 ÷ 3 = 82.333…, stored in `avg`.
6. `avg.toFixed(1)` rounds to **1 decimal place** and gives the text `"82.3"`.
7. `"Average: " + "82.3"` joins the strings into `"Average: 82.3"`.
8. `textContent` puts that text in the paragraph with `id="result"`, so it appears on the page.

Check: 70 + 85 + 92 = 247, and 247 ÷ 3 ≈ 82.3 ✓.

Without `Number()`, `a + b + c` would join `"70"`, `"85"` and `"92"` into `"708592"`, and the page would show `Average: 236197.3`. Nonsense!

## Improve it: Pass or Fail, and empty boxes

Two problems are left for you to fix:

1. Show "Pass" (an average of 50 or more) or "Fail" next to the average.
2. Leave a box empty and press Calculate. It does not crash, but the answer is wrong! `Number("")` is `0`, so an empty box counts as a mark of 0.

Try it yourself in the calculator above first. Hints:

- Read each box's `.value` into a variable **before** you convert it.
- An empty box has the value `""`, an empty string. Test for it with `=== ""`.
- `||` means "or": `x === "" || y === ""` is `true` if **either** value is empty.
- Inside a function, `return;` stops the function at once.

Here is one model solution. Compare it with yours:

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
      const aText = document.querySelector("#a").value;
      const bText = document.querySelector("#b").value;
      const cText = document.querySelector("#c").value;

      // Stop early if any box is empty
      if (aText === "" || bText === "" || cText === "") {
        document.querySelector("#result").textContent = "Please type all three marks.";
        return;
      }

      const avg = (Number(aText) + Number(bText) + Number(cText)) / 3;
      let verdict;
      if (avg >= 50) {
        verdict = "Pass";
      } else {
        verdict = "Fail";
      }
      document.querySelector("#result").textContent =
        "Average: " + avg.toFixed(1) + " (" + verdict + ")";
    }
    document.querySelector("#btn").addEventListener("click", calculate);
  </script>
</body>
</html>
```

Test it with 55, 48 and 40: the average is 143 ÷ 3 ≈ 47.7, so you should see `Average: 47.7 (Fail)`. Then leave a box empty and check that the message appears. If your boxes accept any text (`type="text"`), also test `isNaN(Number(aText))`, which is `true` when someone types something like `abc`.

## Common mistakes

- **`=` instead of `===`.** `if (mark = 50)` stores 50 in `mark` instead of comparing it. Use `===` to compare.
- **Wrong capital letters.** Write `Number`, `querySelector`, `textContent` and `addEventListener` exactly like this; `textcontent` will not work.
- **Missing quotes or brackets.** Every `"` needs a partner, and every `(` and `{` needs its `)` or `}`. If nothing happens, count them.
- **`calculate()` instead of `calculate` in `addEventListener`.** With brackets, the function runs once when the page loads, not on each click.
- **Forgetting `Number()`.** Values from boxes are strings, so `"5" + "3"` is `"53"`.
- **Joining before adding.** `"Total: " + 2 + 3` gives `"Total: 23"`, because JavaScript works left to right and the text comes first. Write `"Total: " + (2 + 3)` to get `"Total: 5"`.
- **Forgetting the `#`.** For `id="result"`, write `querySelector("#result")`.

## Check yourself

1. What is the difference between `let` and `const`?
2. Write a function `double(n)` that returns twice `n`.
3. Which method connects a button click to a function?
4. Predict the result of `"4" + "6"` and of `Number("4") + Number("6")`.
5. What does `f(2, 5)` return if `function f(a, b) { return a * b + 1; }`?
6. How many times does the loop `for (let i = 0; i < 5; i++)` run, and what values does `i` take?
7. What is wrong with `button.addEventListener("click", calculate());`?
8. Predict what `"Total: " + 2 + 3` gives. How can you make it give `"Total: 5"`?

*Answers: 1) a variable made with `let` can be given a new value later; a `const` cannot be reassigned · 2) `function double(n) { return n * 2; }` · 3) `addEventListener`, for example `button.addEventListener("click", sayHello)` · 4) `"46"` (the strings are joined) and `10` · 5) `11`, because 2 × 5 + 1 = 11 · 6) 5 times, with `i` = 0, 1, 2, 3, 4 · 7) the brackets run `calculate` once, straight away; write `calculate` without brackets so it runs on each click · 8) `"Total: 23"`; use brackets: `"Total: " + (2 + 3)`*
