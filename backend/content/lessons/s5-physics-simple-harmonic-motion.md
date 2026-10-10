---
slug: s5-physics-simple-harmonic-motion
subject: physics
grade: S5
unit: 1
order: 1
title: Simple harmonic motion
summary: Define SHM by a = −ω²x, then find the period, speed and energy of a mass on a spring and a simple pendulum.
minutes: 40
simulations: phet-pendulum-lab, phet-hookes-law, phet-masses-and-springs
---
## Oscillations around us

A child on a swing in a Kigali playground, a moto taxi bouncing on its springs along a murram road, and a guitar string all **oscillate**: they move back and forth about a fixed **equilibrium position**.

The simplest and most important type of oscillation is **simple harmonic motion (SHM)**.

## Definition

> A body moves with simple harmonic motion when its acceleration is **directly proportional** to its displacement from a fixed point and is always **directed towards** that point.

$$a = -\omega^2 x$$

- $x$ is the displacement from equilibrium (m).
- $\omega$ is the **angular frequency** (rad/s), a constant for the motion.
- The minus sign shows that the acceleration always points **back towards** equilibrium.

The angular frequency is related to the frequency $f$ and the period $T$ by

$$\omega = 2\pi f = \frac{2\pi}{T}$$

## Displacement, velocity and acceleration

If timing starts when the body is released from rest at its **amplitude** $A$ (the maximum displacement), then

$$x = A\cos\omega t$$

The speed at any displacement $x$ is

$$v = \pm\,\omega\sqrt{A^2 - x^2}$$

From these results:

- maximum speed $v_{\max} = \omega A$, at the equilibrium position ($x = 0$);
- maximum acceleration $a_{\max} = \omega^2 A$, at the extreme positions ($x = \pm A$).

| Position | Displacement | Speed | Acceleration | Kinetic energy | Potential energy |
|---|---|---|---|---|---|
| Equilibrium | 0 | maximum, $\omega A$ | 0 | maximum | minimum |
| Extremes | $\pm A$ | 0 | maximum, $\omega^2 A$ | 0 | maximum |

## Two important oscillators

### Mass on a spring

A spring obeys Hooke's law, so when a mass $m$ is displaced by $x$ the restoring force is $F = -kx$, where $k$ is the spring constant (N/m). Using Newton's second law:

$$ma = -kx \quad\Rightarrow\quad a = -\frac{k}{m}x$$

This has the form $a = -\omega^2 x$, so the motion is SHM with $\omega^2 = \dfrac{k}{m}$ and

$$T = 2\pi\sqrt{\frac{m}{k}}$$

### Simple pendulum

A small bob of mass $m$ hangs on a light string of length $L$. For small angles (less than about 10°), the restoring force is approximately $-\dfrac{mg}{L}x$, so $a = -\dfrac{g}{L}x$. This is SHM with $\omega^2 = \dfrac{g}{L}$ and

$$T = 2\pi\sqrt{\frac{L}{g}}$$

The period of a pendulum does **not** depend on the mass of the bob or (for small swings) on the amplitude. A pendulum clock carried to the top of Mount Karisimbi (4507 m) would run slightly slow, because $g$ is a little smaller there and so $T$ is a little longer.

| | Mass on a spring | Simple pendulum |
|---|---|---|
| Restoring force | $-kx$ | $-\frac{mg}{L}x$ (small angles) |
| $\omega^2$ | $\frac{k}{m}$ | $\frac{g}{L}$ |
| Period | $2\pi\sqrt{m/k}$ | $2\pi\sqrt{L/g}$ |
| Depends on mass? | yes | no |

## Energy in SHM

With no friction, the total energy stays constant. It changes back and forth between kinetic energy (KE) and potential energy (PE):

$$E = \tfrac{1}{2}kA^2 = \tfrac{1}{2}m\omega^2 A^2$$

$$\text{PE} = \tfrac{1}{2}kx^2 \qquad \text{KE} = \tfrac{1}{2}k\left(A^2 - x^2\right)$$

## Worked example 1: a mass on a spring

A 0.50 kg mass hangs on a spring with $k = 200$ N/m. It is pulled down 4.0 cm and released.

**Angular frequency:** $\omega = \sqrt{\dfrac{k}{m}} = \sqrt{\dfrac{200}{0.50}} = \sqrt{400} = 20$ rad/s

**Period:** $T = \dfrac{2\pi}{\omega} = \dfrac{2\pi}{20} \approx 0.314$ s, so $f = \dfrac{1}{0.314} \approx 3.18$ Hz

**Maximum speed:** $v_{\max} = \omega A = 20 \times 0.040 = 0.80$ m/s

**Maximum acceleration:** $a_{\max} = \omega^2 A = 400 \times 0.040 = 16$ m/s²

**Total energy:** $E = \tfrac{1}{2}kA^2 = 0.5 \times 200 \times 0.040^2 = 0.16$ J

Check: $\tfrac{1}{2}mv_{\max}^2 = 0.5 \times 0.50 \times 0.80^2 = 0.16$ J. Correct.

**Speed when $x = 2.0$ cm:**

$$v = 20\sqrt{0.040^2 - 0.020^2} = 20\sqrt{0.0012} \approx 20 \times 0.0346 \approx 0.69\ \text{m/s}$$

At this point PE $= 0.5 \times 200 \times 0.020^2 = 0.04$ J and KE $= 0.16 - 0.04 = 0.12$ J.

## Worked example 2: measuring g in Musanze

A student in Musanze sets up a pendulum of length 0.80 m. She times 20 complete oscillations and gets 36.0 s.

**Period:** $T = \dfrac{36.0}{20} = 1.80$ s

**Rearrange** $T = 2\pi\sqrt{L/g}$ to get $g = \dfrac{4\pi^2 L}{T^2}$:

$$g = \frac{4\pi^2 \times 0.80}{1.80^2} = \frac{31.58}{3.24} \approx 9.75\ \text{m/s}^2$$

Timing 20 oscillations instead of one reduces the effect of human reaction time. For a better result, repeat for several lengths, plot $T^2$ against $L$, and use $g = \dfrac{4\pi^2}{\text{gradient}}$.

## Damping and resonance

In real life, friction and air resistance remove energy, so the amplitude slowly decreases. This is **damping**. Shock absorbers on buses and moto taxis are designed to damp the bouncing of the springs quickly on bumpy roads.

If a system is pushed at its own natural frequency, the amplitude grows very large. This is **resonance**. You use it when you push a swing at just the right moments.

## Investigate

Use the pendulum lab. Change the mass, then the length, then the amplitude, and record the period each time. Which change affects the period?

```sim
phet-pendulum-lab
```

## Safety in the laboratory

- Clamp the retort stand firmly to the bench, or put a heavy weight on its base, so it cannot topple.
- Do not stretch springs beyond their elastic limit; an overstretched spring can snap back. Wear eye protection when loading springs.
- Keep your feet away from hanging masses, and keep pendulum swings small so the bob does not hit anyone.

## Check yourself

1. Find the period of a 2.0 kg mass oscillating on a spring with $k = 50$ N/m.
2. A pendulum's length is made 4 times longer. What happens to its period?
3. Where in an SHM oscillation is the speed greatest and the acceleration zero?

*Answers: 1) $T = 2\pi\sqrt{2.0/50} = 2\pi \times 0.2 \approx 1.26$ s · 2) it doubles, because $T \propto \sqrt{L}$ and $\sqrt{4} = 2$ · 3) at the equilibrium position ($x = 0$)*
