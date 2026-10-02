---
slug: s4-maths-quadratic-functions
subject: mathematics
grade: S4
unit: 3
order: 1
title: Quadratic functions and their parabolas
summary: The shape of y = ax² + bx + c, finding the vertex, the axis of symmetry and the roots.
minutes: 30
simulations: function-grapher, phet-graphing-quadratics, geogebra-graphing
---
## The general form

A **quadratic function** has the form

$$f(x) = ax^2 + bx + c, \qquad a \neq 0$$

Its graph is a **parabola**.

- If $a > 0$ the parabola opens **upwards** (a "smile") and has a **minimum**.
- If $a < 0$ it opens **downwards** (a "frown") and has a **maximum**.

## Axis of symmetry and vertex

The parabola is symmetric about the vertical line

$$x = -\frac{b}{2a}$$

The **vertex** lies on this line. Substitute $x = -\frac{b}{2a}$ into $f$ to find its $y$-coordinate.

**Example.** For $f(x) = x^2 - 4x + 3$: $a = 1$, $b = -4$, so the axis is $x = 2$ and $f(2) = 4 - 8 + 3 = -1$. The vertex is $(2, -1)$, a minimum.

## Roots (x-intercepts)

The roots solve $ax^2 + bx + c = 0$. Use the **quadratic formula**:

$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

The **discriminant** $\Delta = b^2 - 4ac$ tells you how many roots there are:

| $\Delta$ | roots | graph |
|---|---|---|
| $\Delta > 0$ | two different real roots | crosses the $x$-axis twice |
| $\Delta = 0$ | one repeated root | touches the $x$-axis at the vertex |
| $\Delta < 0$ | no real roots | never meets the $x$-axis |

For $x^2 - 4x + 3$: $\Delta = 16 - 12 = 4 > 0$, and $x = \frac{4 \pm 2}{2}$, so $x = 1$ or $x = 3$.

## Explore

Select **Quadratic** below. Keep $b = 0$, $c = 0$ and change $a$; then change $c$ alone; then $b$ alone. Describe in your notebook what each coefficient does.

```sim
function-grapher
```

## Vertex form

Completing the square gives $f(x) = a(x - h)^2 + k$, where $(h, k)$ is the vertex.

$$x^2 - 4x + 3 = (x - 2)^2 - 1$$

## Check yourself

1. Does $y = -2x^2 + 8x - 5$ have a maximum or a minimum? Find the vertex.
2. How many real roots has $x^2 + 2x + 5 = 0$?
3. Write $x^2 + 6x + 1$ in vertex form.

*Answers: 1) maximum at $(2, 3)$ · 2) none ($\Delta = -16$) · 3) $(x+3)^2 - 8$*
