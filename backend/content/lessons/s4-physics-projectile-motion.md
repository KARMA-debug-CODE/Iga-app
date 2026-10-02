---
slug: s4-physics-projectile-motion
subject: physics
grade: S4
unit: 1
order: 1
title: Projectile motion
summary: Split the motion into horizontal and vertical parts to find time of flight, maximum height and range.
minutes: 35
simulations: projectile-lab, phet-projectile-motion
---
## The big idea

A **projectile** is any object thrown into the air that then moves under gravity alone (we ignore air resistance). Its path is a **parabola**.

The key trick: treat the **horizontal** and **vertical** motions **separately**.

- Horizontally there is no force, so the velocity is **constant**.
- Vertically there is a constant downward acceleration $g \approx 9.8\ \text{m/s}^2$.

## Resolving the launch velocity

A ball launched at speed $u$ and angle $\theta$ above the horizontal has

$$u_x = u\cos\theta \qquad u_y = u\sin\theta$$

## The equations (launch and landing at the same height)

**Time of flight:** the ball goes up and comes back down when $u_y t - \tfrac{1}{2} g t^2 = 0$:

$$T = \frac{2u\sin\theta}{g}$$

**Maximum height:** at the top the vertical velocity is zero:

$$H = \frac{u^2 \sin^2\theta}{2g}$$

**Range:** horizontal distance $= u_x \times T$:

$$R = \frac{u^2 \sin 2\theta}{g}$$

Because $\sin 2\theta$ is largest when $2\theta = 90^\circ$, the **maximum range is at 45°**. Angles that add up to 90° (for example 30° and 60°) give the **same range**.

## Worked example

A football is kicked at 20 m/s at 30° to the ground. Take $g = 9.8\ \text{m/s}^2$.

- $T = \dfrac{2 \times 20 \times \sin 30^\circ}{9.8} = \dfrac{20}{9.8} \approx 2.04$ s
- $H = \dfrac{20^2 \times 0.5^2}{2 \times 9.8} = \dfrac{100}{19.6} \approx 5.10$ m
- $R = \dfrac{20^2 \times \sin 60^\circ}{9.8} \approx \dfrac{400 \times 0.866}{9.8} \approx 35.3$ m

## Experiment

Use the lab to check the worked example, then answer: which angle gives the greatest range? Does doubling the speed double the range?

```sim
projectile-lab
```

## Check yourself

1. A stone is thrown at 15 m/s at 45°. Find its range ($g = 9.8$).
2. Which launch angle gives the same range as 20°?
3. What is the vertical velocity of a projectile at its highest point?

*Answers: 1) about 23.0 m · 2) 70° · 3) zero*
