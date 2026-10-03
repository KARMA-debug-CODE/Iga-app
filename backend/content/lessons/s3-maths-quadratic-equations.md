---
slug: s3-maths-quadratic-equations
subject: mathematics
grade: S3
unit: 2
order: 1
title: Solving quadratic equations
summary: Solve ax² + bx + c = 0 by factorising, by completing the square and with the quadratic formula, then use quadratics to solve real problems.
minutes: 35
simulations: function-grapher, phet-graphing-quadratics, geogebra-graphing
---
## What is a quadratic equation?

A **quadratic equation** is an equation in which the highest power of the unknown is 2. Its **standard form** is

$$ax^2 + bx + c = 0, \qquad a \neq 0$$

where $a$, $b$ and $c$ are numbers. For example:

- $x^2 - 9 = 0$ has $a = 1$, $b = 0$, $c = -9$.
- $2x^2 + 3x - 5 = 0$ has $a = 2$, $b = 3$, $c = -5$.
- $x^2 = 4x$ is also quadratic: rearrange it to $x^2 - 4x = 0$.

The values of $x$ that make the equation true are its **solutions** or **roots**. A quadratic equation has **at most two** real roots.

**Golden rule:** always rearrange into standard form (everything on one side, $0$ on the other) before you start.

## Method 1: Factorising

Factorising uses the **zero product rule**:

$$\text{if } p \times q = 0, \text{ then } p = 0 \text{ or } q = 0$$

So if we write the quadratic as a product of two brackets, each bracket gives one root. To factorise $x^2 + bx + c$, look for two numbers that **multiply to $c$** and **add to $b$**.

### Worked example 1

Solve $x^2 - 5x - 14 = 0$.

- We need two numbers with product $-14$ and sum $-5$. Try the pairs: $1$ and $-14$ (sum $-13$), $2$ and $-7$ (sum $-5$) ✓.
- So $(x + 2)(x - 7) = 0$.
- Either $x + 2 = 0$, giving $x = -2$, or $x - 7 = 0$, giving $x = 7$.
- Check: $7^2 - 5(7) - 14 = 49 - 35 - 14 = 0$ ✓ and $(-2)^2 - 5(-2) - 14 = 4 + 10 - 14 = 0$ ✓.

Two special cases come up often:

- **Common factor:** $x^2 - 4x = 0$ gives $x(x - 4) = 0$, so $x = 0$ or $x = 4$. Never divide both sides by $x$: you would lose the root $x = 0$.
- **Difference of two squares:** $x^2 - 9 = 0$ gives $(x - 3)(x + 3) = 0$, so $x = 3$ or $x = -3$.

## Method 2: Completing the square

This method uses the pattern $(x + p)^2 = x^2 + 2px + p^2$. When $a = 1$, we add $\left(\frac{b}{2}\right)^2$ to both sides.

### Worked example 2

Solve $x^2 + 6x - 7 = 0$.

- Move the constant to the right: $x^2 + 6x = 7$.
- Half of $6$ is $3$, and $3^2 = 9$. Add $9$ to both sides: $x^2 + 6x + 9 = 16$.
- The left side is a perfect square: $(x + 3)^2 = 16$.
- Take the square root of both sides: $x + 3 = \pm 4$.
- So $x = -3 + 4 = 1$ or $x = -3 - 4 = -7$.

## Method 3: The quadratic formula

Completing the square on the general equation $ax^2 + bx + c = 0$ gives the **quadratic formula**:

$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

It always works, even when the quadratic does not factorise neatly.

### Worked example 3

Solve $2x^2 + 3x - 5 = 0$.

- Here $a = 2$, $b = 3$, $c = -5$.
- $b^2 - 4ac = 3^2 - 4(2)(-5) = 9 + 40 = 49$.
- $x = \dfrac{-3 \pm \sqrt{49}}{2(2)} = \dfrac{-3 \pm 7}{4}$.
- So $x = \dfrac{4}{4} = 1$ or $x = \dfrac{-10}{4} = -2.5$.

### Worked example 4: answers with surds

Solve $x^2 - 4x - 1 = 0$. Give exact answers and answers to 2 decimal places.

- $a = 1$, $b = -4$, $c = -1$, so $b^2 - 4ac = 16 + 4 = 20$.
- $x = \dfrac{4 \pm \sqrt{20}}{2} = \dfrac{4 \pm 2\sqrt{5}}{2} = 2 \pm \sqrt{5}$.
- Since $\sqrt{5} \approx 2.236$: $x \approx 4.24$ or $x \approx -0.24$.

## How many roots? The discriminant

The expression $b^2 - 4ac$ under the square root is called the **discriminant**. Its sign tells you how many real roots there are before you solve.

| Value of $b^2 - 4ac$ | Number of real roots |
|---|---|
| positive | two different roots |
| zero | one repeated root |
| negative | no real roots |

For example, $x^2 + 4x + 7 = 0$ has $b^2 - 4ac = 16 - 28 = -12$, which is negative, so it has no real roots.

## Which method should I use?

| Method | Best when… |
|---|---|
| Factorising | the numbers are small and you can spot the factor pair quickly |
| Completing the square | $a = 1$ and $b$ is even |
| Quadratic formula | any quadratic, especially when the roots are not whole numbers |

## Solving problems with quadratics

### Worked example 5

A farmer in Musanze has a rectangular plot for Irish potatoes. Its length is 5 m more than its width, and its area is 84 m². Find its dimensions. Fencing costs 1,500 FRW per metre: how much will it cost to fence the plot?

- Let the width be $w$ metres, so the length is $w + 5$ metres.
- Area: $w(w + 5) = 84$, so $w^2 + 5w - 84 = 0$.
- Two numbers with product $-84$ and sum $5$: $12$ and $-7$. So $(w + 12)(w - 7) = 0$.
- $w = -12$ or $w = 7$. A width cannot be negative, so $w = 7$ m and the length is $12$ m. Check: $7 \times 12 = 84$ ✓.
- Perimeter $= 2(7 + 12) = 38$ m. Cost $= 38 \times 1\,500 = 57\,000$ FRW.

Always ask whether each root makes sense in the real situation, and reject any that do not.

## See the roots on a graph

The roots of $ax^2 + bx + c = 0$ are the $x$-values where the graph of $y = ax^2 + bx + c$ crosses the $x$-axis. Choose **Quadratic** in the grapher and set $a = 1$, $b = -1$, $c = -6$. Check that the roots are $-2$ and $3$, because $x^2 - x - 6 = (x + 2)(x - 3)$. Then slowly increase $c$. When does the graph stop meeting the $x$-axis, and what is the sign of the discriminant then?

```sim
function-grapher
```

## Check yourself

1. Solve $x^2 + x - 20 = 0$ by factorising.
2. Solve $3x^2 - 5x - 2 = 0$ using the quadratic formula.
3. Without solving, how many real roots does $x^2 + 3x + 5 = 0$ have?

*Answers: 1) $(x + 5)(x - 4) = 0$, so $x = -5$ or $x = 4$ · 2) $b^2 - 4ac = 25 + 24 = 49$ and $x = \frac{5 \pm 7}{6}$, so $x = 2$ or $x = -\frac{1}{3}$ · 3) none, because $b^2 - 4ac = 9 - 20 = -11 < 0$*
