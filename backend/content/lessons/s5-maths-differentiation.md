---
slug: s5-maths-differentiation
subject: mathematics
grade: S5
unit: 2
order: 1
title: Differentiation: gradients and rates of change
summary: The derivative measures how fast a function changes; learn the rules and use them for tangents, rates of change and maximum or minimum values.
minutes: 40
simulations: geogebra-graphing, function-grapher
---
## What is a derivative?

On a straight line the gradient is the same everywhere. On a curve the gradient changes from point to point. The **gradient of a curve at a point** is the gradient of the **tangent** there: the straight line that just touches the curve at that point.

The **derivative** of $f(x)$, written $f'(x)$ or $\dfrac{dy}{dx}$, is a new function that gives this gradient for every value of $x$. It is also the **rate of change** of $y$ with respect to $x$. Finding it is called **differentiation**.

## Differentiation from first principles

Take two points on the curve, $P\big(x, f(x)\big)$ and $Q\big(x+h, f(x+h)\big)$. The gradient of the chord $PQ$ is $\dfrac{f(x+h)-f(x)}{h}$. As $Q$ slides towards $P$, $h \to 0$ and the chord becomes the tangent. So

$$f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$$

This uses the limits you met in Unit 1.

### Worked example 1: first principles

Find $f'(x)$ for $f(x) = x^2 + 3x$.

1. $f(x+h) = (x+h)^2 + 3(x+h) = x^2 + 2xh + h^2 + 3x + 3h$
2. $f(x+h) - f(x) = 2xh + h^2 + 3h$
3. Divide by $h$: $\dfrac{2xh + h^2 + 3h}{h} = 2x + h + 3$
4. Let $h \to 0$: $f'(x) = 2x + 3$

So at $x = 1$ the gradient of the curve is $2(1) + 3 = 5$.

## Rules of differentiation

First principles always works but is slow. These rules all come from it:

| Function $y$ | Derivative $\dfrac{dy}{dx}$ |
|---|---|
| $c$ (a constant) | $0$ |
| $x^n$ | $nx^{n-1}$ |
| $k\,f(x)$ | $k\,f'(x)$ |
| $f(x) + g(x)$ | $f'(x) + g'(x)$ |
| $\sin x$ | $\cos x$ |
| $\cos x$ | $-\sin x$ |

For $\sin x$ and $\cos x$, the angle $x$ must be in **radians**.

For products, quotients and "functions of a function" use:

- **Product rule:** $\dfrac{d}{dx}(uv) = u'v + uv'$
- **Quotient rule:** $\dfrac{d}{dx}\left(\dfrac{u}{v}\right) = \dfrac{u'v - uv'}{v^2}$
- **Chain rule:** if $y = f(u)$ and $u = g(x)$, then $\dfrac{dy}{dx} = \dfrac{dy}{du} \times \dfrac{du}{dx}$

Quick examples:

- $y = (2x+1)(x^2 - 3)$: $\;y' = 2(x^2-3) + (2x+1)(2x) = 2x^2 - 6 + 4x^2 + 2x = 6x^2 + 2x - 6$
- $y = \dfrac{x+1}{x-1}$: $\;y' = \dfrac{(1)(x-1) - (x+1)(1)}{(x-1)^2} = \dfrac{-2}{(x-1)^2}$
- $y = (3x^2+1)^4$: let $u = 3x^2 + 1$, then $y' = 4u^3 \times 6x = 24x(3x^2+1)^3$

### Worked example 2: gradient and tangent

Find the equation of the tangent to $y = 4x^3 - 5x^2 + 7x - 2$ at $x = 1$.

1. Differentiate term by term: $\dfrac{dy}{dx} = 12x^2 - 10x + 7$
2. Gradient at $x = 1$: $m = 12 - 10 + 7 = 9$
3. Point on the curve: $y = 4 - 5 + 7 - 2 = 4$, so the point is $(1, 4)$
4. Tangent: $y - 4 = 9(x - 1)$, which gives $y = 9x - 5$

## Rates of change

If $s$ is distance in metres and $t$ is time in seconds, then $\dfrac{ds}{dt}$ is the **velocity**. A moto passes a stage in Nyabugogo and speeds up, so that $t$ seconds later its distance from the stage is $s = t^2 + 4t$. Its velocity is

$$v = \frac{ds}{dt} = 2t + 4$$

so it passes the stage at $v = 4$ m/s, and 3 seconds later $v = 2(3) + 4 = 10$ m/s, which is 36 km/h.

## Stationary points

At a **stationary point** the tangent is horizontal, so $f'(x) = 0$. The **second derivative** $f''(x)$ tells us what kind of point it is:

- $f''(x) > 0$: a **minimum** point (the curve bends upwards)
- $f''(x) < 0$: a **maximum** point (the curve bends downwards)
- $f''(x) = 0$: test further (it may be a point of inflection)

For $f(x) = x^3 - 3x^2 - 9x + 5$:

- $f'(x) = 3x^2 - 6x - 9 = 3(x-3)(x+1)$, so $x = 3$ or $x = -1$
- $f''(x) = 6x - 6$
- $f''(3) = 12 > 0$ and $f(3) = 27 - 27 - 27 + 5 = -22$: minimum at $(3, -22)$
- $f''(-1) = -12 < 0$ and $f(-1) = -1 - 3 + 9 + 5 = 10$: maximum at $(-1, 10)$

### Worked example 3: the biggest enclosure

A farmer in Nyagatare has 120 m of fencing to build a rectangular enclosure for cows against a long straight wall, so only three sides need fencing. What dimensions give the largest area?

1. Let each side at right angles to the wall be $x$ m. The side parallel to the wall is $120 - 2x$ m.
2. Area: $A = x(120 - 2x) = 120x - 2x^2$
3. $\dfrac{dA}{dx} = 120 - 4x = 0$ gives $x = 30$
4. $\dfrac{d^2A}{dx^2} = -4 < 0$, so this is a maximum.
5. Dimensions: 30 m by $120 - 2(30) = 60$ m. Largest area $= 30 \times 60 = 1800$ m².

Optimisation problems like this help farmers, builders and businesses get the most from limited materials or money.

## Explore

In GeoGebra, type `f(x) = x^3 - 3x^2 - 9x + 5` and then `Derivative(f)` to draw $f'(x)$ on the same axes. Where does the graph of $f'$ cross the x-axis? Compare these $x$-values with the turning points of $f$.

```sim
geogebra-graphing
```

## Check yourself

1. Differentiate $y = 5x^4 - 2x + 8$.
2. Find the gradient of $y = x^2 - 6x$ at the point where $x = 4$.
3. Find the stationary point of $y = x^2 - 8x + 3$ and say whether it is a maximum or a minimum.

*Answers: 1) $\frac{dy}{dx} = 20x^3 - 2$ · 2) $\frac{dy}{dx} = 2x - 6$, so the gradient is $2(4) - 6 = 2$ · 3) $\frac{dy}{dx} = 2x - 8 = 0$ gives $x = 4$ and $y = 16 - 32 + 3 = -13$; $\frac{d^2y}{dx^2} = 2 > 0$, so $(4, -13)$ is a minimum*
