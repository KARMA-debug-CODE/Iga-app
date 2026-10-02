---
slug: s2-physics-ohms-law
subject: physics
grade: S2
unit: 4
order: 1
title: Current, voltage and Ohm's law
summary: What current and voltage are, how resistance limits current, and how to use V = IR.
minutes: 25
simulations: ohms-law-lab, phet-ohms-law, phet-circuit-construction-kit-dc
---
## Three quantities

| Quantity | Symbol | Unit | Measured with | Think of it as… |
|---|---|---|---|---|
| Current | $I$ | ampere (A) | ammeter (in **series**) | how much charge flows each second |
| Voltage (p.d.) | $V$ | volt (V) | voltmeter (in **parallel**) | the "push" given to the charges |
| Resistance | $R$ | ohm ($\Omega$) | ohmmeter | how hard it is for charge to flow |

A water analogy helps: voltage is like the height of a water tank, current is the flow of water in the pipe, and resistance is a narrow section of pipe.

## Ohm's law

For a metal conductor at constant temperature, the current is **directly proportional** to the voltage:

$$V = IR$$

Rearranged: $I = \dfrac{V}{R}$ and $R = \dfrac{V}{I}$.

**Example 1.** A 6 V battery drives current through a 3 Ω resistor. $I = \frac{6}{3} = 2$ A.

**Example 2.** A lamp draws 0.5 A from a 12 V supply. $R = \frac{12}{0.5} = 24\ \Omega$.

## Try it

Increase the voltage: what happens to the current? Now keep the voltage fixed and increase the resistance.

```sim
ohms-law-lab
```

## The V–I graph

Plotting $V$ against $I$ for a resistor gives a **straight line through the origin**. The gradient equals the resistance. A filament lamp gives a *curve*, because its resistance rises as it gets hot — so a lamp does **not** obey Ohm's law.

## Safety

Mains electricity in Rwanda is 230 V. Even a small current through the body can be dangerous. Never touch bare wires, and never put metal objects into sockets.

## Check yourself

1. Find the current through a 10 Ω resistor connected to a 5 V supply.
2. What voltage is needed to push 3 A through 4 Ω?
3. Why is an ammeter connected in series?

*Answers: 1) 0.5 A · 2) 12 V · 3) so that all the current in that part of the circuit passes through it*
