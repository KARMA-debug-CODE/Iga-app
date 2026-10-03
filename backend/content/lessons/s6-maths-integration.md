---
slug: s6-maths-integration
subject: mathematics
grade: S6
unit: 1
order: 1
title: Integration and its applications
summary: Integration reverses differentiation; use it to find antiderivatives, evaluate definite integrals, and calculate areas, distances and volumes.
minutes: 45
simulations: geogebra-graphing
---
## Reversing differentiation

If $F'(x) = f(x)$, then $F(x)$ is an **antiderivative** (or primitive) of $f(x)$. For example, $\dfrac{d}{dx}(x^3) = 3x^2$, so $x^3$ is an antiderivative of $3x^2$. But so are $x^3 + 5$ and $x^3 - 100$, because a constant differentiates to zero. We therefore write the **indefinite integral** as

$$\int f(x)\,dx = F(x) + C$$

where $C$ is the **constant of integration**. Finding an antiderivative is called **integration**.

## Standard integrals

| $f(x)$ | $\int f(x)\,dx$ |
|---|---|
| $k$ (a constant) | $kx + C$ |
| $x^n$, where $n \neq -1$ | $\dfrac{x^{n+1}}{n+1} + C$ |
| $\dfrac{1}{x}$ | $\ln \lvert x \rvert + C$ |
| $e^x$ | $e^x + C$ |
| $\cos x$ | $\sin x + C$ |
| $\sin x$ | $-\cos x + C$ |

Integration is **linear**: the integral of a sum is the sum of the integrals, and a constant multiple comes outside, $\int k\,f(x)\,dx = k\int f(x)\,dx$.

### Worked example 1: an indefinite integral

Find $\int (6x^2 - 4x + 5)\,dx$.

1. Raise each power by one and divide by the new power: $\dfrac{6x^3}{3} - \dfrac{4x^2}{2} + 5x$
2. Simplify and add the constant: $2x^3 - 2x^2 + 5x + C$
3. Check by differentiating: $6x^2 - 4x + 5$ ✓

## Integration by substitution

When the integrand contains a function and (a multiple of) its derivative, substitute a new variable. For $\int 2x(x^2+3)^4\,dx$, let $u = x^2 + 3$, so $\dfrac{du}{dx} = 2x$ and $du = 2x\,dx$:

$$\int 2x(x^2+3)^4\,dx = \int u^4\,du = \frac{u^5}{5} + C = \frac{(x^2+3)^5}{5} + C$$

## Definite integrals

The **fundamental theorem of calculus** says that if $F$ is any antiderivative of $f$, then

$$\int_a^b f(x)\,dx = \Big[F(x)\Big]_a^b = F(b) - F(a)$$

The constant $C$ cancels when we subtract, so we leave it out. The numbers $a$ and $b$ are the **limits** of integration.

## Area under a curve

If $f(x) \ge 0$ for $a \le x \le b$, then $\int_a^b f(x)\,dx$ is the area enclosed by the curve, the x-axis and the lines $x = a$ and $x = b$.

### Worked example 2: area under a curve

Find the area between $y = x^2 + 1$, the x-axis, $x = 0$ and $x = 3$.

$$\int_0^3 (x^2 + 1)\,dx = \left[\frac{x^3}{3} + x\right]_0^3 = \left(\frac{27}{3} + 3\right) - (0 + 0) = 9 + 3 = 12$$

The area is **12 square units**.

### Watch out: regions below the axis

Where a curve lies **below** the x-axis, the definite integral is **negative**. For $y = x^2 - 4x$ between $x = 0$ and $x = 4$:

$$\int_0^4 (x^2 - 4x)\,dx = \left[\frac{x^3}{3} - 2x^2\right]_0^4 = \frac{64}{3} - 32 = -\frac{32}{3}$$

The area is the positive value, $\dfrac{32}{3} \approx 10.67$ square units. If a region lies partly above and partly below the axis, integrate each part separately and add the sizes of the areas.

The area **between two curves**, where $f(x) \ge g(x)$ on $[a, b]$, is $\int_a^b \big(f(x) - g(x)\big)\,dx$.

## Distance from velocity

Velocity is the derivative of displacement, so displacement is the integral of velocity:

$$s = \int_{t_1}^{t_2} v\,dt$$

### Worked example 3: a moto leaving the lights

A moto taxi pulls away from traffic lights in Kicukiro. For the first 5 seconds its velocity is $v = 3t - 0.3t^2$ m/s. How far does it travel in that time?

$$s = \int_0^5 (3t - 0.3t^2)\,dt = \Big[1.5t^2 - 0.1t^3\Big]_0^5 = 1.5(25) - 0.1(125) = 37.5 - 12.5 = 25$$

It travels **25 m**. Its speed at $t = 5$ is $v = 3(5) - 0.3(25) = 15 - 7.5 = 7.5$ m/s, which is 27 km/h.

## Volumes of revolution

Rotating the region under $y = f(x)$ from $x = a$ to $x = b$ through $360^\circ$ about the x-axis makes a solid with volume

$$V = \pi \int_a^b y^2\,dx$$

For example, rotating $y = \sqrt{x}$ from $x = 0$ to $x = 4$ gives a solid **paraboloid**, the same curved shape as a satellite dish. Here $y^2 = x$:

$$V = \pi \int_0^4 x\,dx = \pi \left[\frac{x^2}{2}\right]_0^4 = \pi \times \frac{16}{2} = 8\pi \approx 25.13 \text{ cubic units}$$

Engineers use the same idea to find the capacity of curved water tanks and the amount of concrete in a curved pillar.

## Explore

In GeoGebra, type `Integral(x^2 + 1, 0, 3)` to shade the area in Worked example 2 and check that it equals 12. Then try `Integral(x^2 - 4x, 0, 4)` and notice that the value is negative.

```sim
geogebra-graphing
```

## Check yourself

1. Find $\int (3x^2 + 2)\,dx$.
2. Evaluate $\int_1^2 4x^3\,dx$.
3. Find the area between $y = 2x$, the x-axis and the lines $x = 0$ and $x = 5$.

*Answers: 1) $x^3 + 2x + C$ · 2) $\big[x^4\big]_1^2 = 16 - 1 = 15$ · 3) $\big[x^2\big]_0^5 = 25 - 0 = 25$ square units (check with the triangle: $\frac{1}{2} \times 5 \times 10 = 25$)*
