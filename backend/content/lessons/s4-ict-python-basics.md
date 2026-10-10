---
slug: s4-ict-python-basics
subject: ict
grade: S4
unit: 4
order: 1
title: Programming in Python: first steps
summary: Write and run real Python programs using variables, data types, operators, decisions, loops and functions.
minutes: 45
simulations:
---
## Why Python?

**Python** is a programming language that is easy to read and write. It is used to build websites, analyse data, control robots and teach computers to recognise images.

A **program** is a list of instructions that the computer carries out in order, from top to bottom. The code boxes with a **Run** button are live editors: press **Run** to see the output, change the code, and run it again.

```python-run
print("Muraho, Rwanda!")
print("I am learning Python.")
```

## Variables and data types

A **variable** is a name that stores a value. We create one with `=`, the **assignment** operator. For example, `district = "Huye"` stores the text Huye in a variable called `district`.

| Type | Meaning | Example |
|---|---|---|
| `int` | whole number | `850` |
| `float` | decimal number | `3.5` |
| `str` | text (a string), written in quotes | `"Huye"` |
| `bool` | true or false | `True` |

Rules for variable names: use letters, digits and `_`; do not start with a digit; no spaces or `-`; and do not use a Python **keyword** such as `if`, `for` or `class`. Names are case-sensitive, so `Mark` and `mark` are different variables. Use `type(value)` to check a value's type.

## Arithmetic operators

| Operator | Meaning | Example | Result |
|---|---|---|---|
| `+` | add | `7 + 2` | `9` |
| `-` | subtract | `7 - 2` | `5` |
| `*` | multiply | `7 * 2` | `14` |
| `/` | divide | `7 / 2` | `3.5` |
| `//` | whole-number (floor) division | `7 // 2` | `3` |
| `%` | remainder (modulus) | `7 % 2` | `1` |
| `**` | power | `7 ** 2` | `49` |

Python follows the usual order of operations: `**` first, then `*`, `/`, `//`, `%`, then `+` and `-`. The `/` operator always gives a `float`.

### Worked example 1: a moto fare

Suppose a moto charges a starting fare of 300 FRW plus 150 FRW for every kilometre. Write a program for a 4.5 km trip.

```python-run
start_fare = 300  # FRW
per_km = 150  # FRW for each km
distance = 4.5  # km

fare = start_fare + per_km * distance
print("Distance:", distance, "km")
print("Fare:", fare, "FRW")
```

How it works:

1. Multiplication comes before addition, so `per_km * distance` $= 150 \times 4.5 = 675$ is worked out first.
2. Then `fare` $= 300 + 675 = 975.0$. It is a `float` because `distance` is a float.
3. The output is `Distance: 4.5 km` and then `Fare: 975.0 FRW`.

Text after `#` is a **comment**. Python ignores it; comments explain the code to people.

## Getting input from the user

`input()` shows a message and waits for the user to type. It **always returns a string**, so convert numbers with `int()` or `float()` before doing arithmetic.

```python-run
name = input("What is your name? ")
age = int(input("How old are you? "))
print("Hello", name)
print("In 5 years you will be", age + 5)
```

Before pressing Run, type two lines in the **Input** box, for example `Keza` and `16`. The last line then shows `In 5 years you will be 21`.

## Making decisions: if, elif, else

A **condition** is an expression that is either `True` or `False`. We build conditions with comparison operators: `==` (equal to), `!=` (not equal to), `<`, `>`, `<=` and `>=`. Remember that `=` stores a value but `==` compares two values.

The lines inside an `if` block must be **indented** (usually 4 spaces). Python uses indentation to know which lines belong to the block.

### Worked example 2: a grade from a mark

A school gives grades like this: 80 and above is A, 70 to 79 is B, 60 to 69 is C, 50 to 59 is D, and below 50 is F.

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

print("Mark:", mark, "Grade:", grade)
```

Trace it: is `72 >= 80`? False. Is `72 >= 70`? True, so `grade = "B"` and Python skips the remaining branches. The output is `Mark: 72 Grade: B`. Change `mark` to 45, then to 80, and predict each output before you run it.

## Repeating: for and while loops

A **for loop** repeats once for each value in a sequence. `range(1, 6)` gives 1, 2, 3, 4, 5. It stops **before** 6.

### Worked example 3: saving in an ikimina

Aline saves 2,000 FRW every week in her savings group (*ikimina*). How much has she saved after 5 weeks?

```python-run
savings = 0
for week in range(1, 6):
    savings = savings + 2000
    print("Week", week, "savings:", savings, "FRW")

print("Total:", savings, "FRW")
```

| `week` | `savings` after that pass of the loop |
|---|---|
| 1 | 2000 |
| 2 | 4000 |
| 3 | 6000 |
| 4 | 8000 |
| 5 | 10000 |

The last line printed is `Total: 10000 FRW`.

A **while loop** repeats as long as its condition is true. How many weeks does it take to reach 15,000 FRW when saving 2,500 FRW a week?

```python-run
target = 15000
savings = 0
weeks = 0
while savings < target:
    savings = savings + 2500
    weeks = weeks + 1
print("Weeks needed:", weeks)
```

It prints `Weeks needed: 6`, because $6 \times 2500 = 15000$. Something inside a while loop must change, or the loop runs forever. If that happens, press **Stop**.

## Lists and functions

A **list** stores many values in order: `marks = [65, 78, 54, 90]`. Then `len(marks)` is 4, `sum(marks)` is 287 and `max(marks)` is 90.

A **function** is a named block of code that you can reuse. Define it with the keyword `def` and send back a result with `return`:

```python-run
def average(numbers):
    return sum(numbers) / len(numbers)


marks = [65, 78, 54, 90]
print("Average mark:", average(marks))
print("Highest mark:", max(marks))
```

Since $287 \div 4 = 71.75$, it prints `Average mark: 71.75`.

## Safety in the computer lab

Keep food and drinks away from keyboards, never touch sockets or cables with wet hands, report damaged plugs to your teacher, and rest your eyes by looking away from the screen every 20 to 30 minutes.

## Check yourself

1. What does `print(17 // 5, 17 % 5)` display?
2. What is the data type of the value `4.0`?
3. How many times does the body of `for i in range(2, 8):` run?

*Answers: 1) `3 2` · 2) `float` · 3) 6 times (i = 2, 3, 4, 5, 6, 7)*
