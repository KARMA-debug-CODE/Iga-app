---
slug: s2-physics-ohms-law
subject: physics
grade: S2
unit: 4
order: 1
title: Current, voltage and Ohm's law
summary: What charge, current and voltage are, how resistance limits current, how to use V = IR with mA and kΩ, and how to find resistance from a table or a graph.
minutes: 40
simulations: ohms-law-lab, phet-ohms-law, phet-circuit-construction-kit-dc
---
## Electric charge and current

Everything around you contains tiny particles that carry **electric charge**. In a metal wire, some of these particles, called **electrons**, are free to move. When they all drift the same way along the wire, we have an electric current.

Charge is measured in **coulombs** (C). One coulomb is a lot of charge: it is the charge of about six billion billion electrons.

**Current** is the amount of charge that passes a point in the circuit every second. Its symbol is $I$ and its unit is the **ampere** (A), often called the "amp". A current of 1 A means that 1 coulomb passes each second.

$$I = \frac{Q}{t} \qquad \text{or} \qquad Q = It$$

Here $Q$ is the charge in coulombs and $t$ is the time in **seconds**.

We measure current with an **ammeter**. It goes **in series**: we break the circuit and put the ammeter in the gap, so that all the current flows through it.

### Worked example 1: a torch left on

A torch bulb carries a current of 0.5 A for 2 minutes. How much charge passes through the bulb?

1. Write what you know: $I = 0.5$ A and $t = 2$ minutes.
2. Change the time to seconds: $t = 2 \times 60 = 120$ s.
3. Use $Q = It$: $Q = 0.5 \times 120 = 60$ C.
4. Check: $\dfrac{60\ \text{C}}{120\ \text{s}} = 0.5$ A, which is the current we started with ✓.

## Voltage: energy for each coulomb

A battery does not make charge. The charge is already in the wires. The battery gives **energy** to the charge and pushes it around the circuit. The charge then gives this energy to the bulb, the radio or the fan.

**Voltage**, also called **potential difference** (p.d.), tells you how much energy each coulomb carries. Energy is measured in **joules** (J). Voltage is measured in **volts** (V):

$$1\ \text{V} = 1\ \text{joule for each coulomb}$$

So a 12 V battery gives 12 J of energy to every coulomb that passes through it. If 60 C flow through it, it gives out $12 \times 60 = 720$ J.

We measure voltage with a **voltmeter**. It goes **in parallel**: its two wires are connected to the two ends of the component, one on each side. It compares the energy of the charge before and after the component.

## Resistance and Ohm's law

**Resistance** tells you how hard it is for current to flow through a component. Its symbol is $R$ and its unit is the **ohm** ($\Omega$). A large resistance lets only a small current through.

Here are the three quantities side by side:

| Quantity | Symbol | Unit | Measured with | Think of it as… |
|---|---|---|---|---|
| Current | $I$ | ampere (A) | ammeter (in **series**) | how much charge flows each second |
| Voltage (p.d.) | $V$ | volt (V) | voltmeter (in **parallel**) | the energy given to each coulomb |
| Resistance | $R$ | ohm ($\Omega$) | ohmmeter | how hard it is for charge to flow |

A water analogy helps. Voltage is like the height of a water tank, current is the flow of water in the pipe, and resistance is a narrow section of pipe.

In the 1820s, the German scientist Georg Ohm found a simple rule. For a metal wire kept at a **constant temperature**, the current is **directly proportional** to the voltage. This means that if you double the voltage, the current doubles too. If you triple it, the current triples. This rule is **Ohm's law**:

$$V = IR$$

Here $V$ is in volts, $I$ in amperes and $R$ in ohms. A component that obeys Ohm's law is called **ohmic**.

## Rearranging V = IR

You can find any one of the three quantities if you know the other two. Use algebra:

- To find $I$, divide both sides of $V = IR$ by $R$: $I = \dfrac{V}{R}$.
- To find $R$, divide both sides of $V = IR$ by $I$: $R = \dfrac{V}{I}$.

Some students use a **formula triangle**. Cover the letter you want, and the other two show you what to do.

```text
        /\
       /  \
      / V  \
     /------\
    / I | R  \
   /____|_____\
```

Cover $V$ and you see $I \times R$. Cover $I$ and you see $\dfrac{V}{R}$. Cover $R$ and you see $\dfrac{V}{I}$.

> **Careful:** the triangle only works when $V$ is at the top. If you put the letters in the wrong places, you will get answers like $R = \dfrac{I}{V}$, which is wrong. Learn the algebra too, and always check your answer by putting it back into $V = IR$.

### Worked example 2: a solar home system in Nyagatare

A family in Nyagatare district has a solar home system with a 12 V battery.

(a) When it is lit normally, their lamp takes a current of 0.5 A. Find its resistance.

1. We want $R$, so use $R = \dfrac{V}{I}$.
2. $R = \dfrac{12}{0.5} = 24\ \Omega$.
3. Check: $V = IR = 0.5 \times 24 = 12$ V ✓.

(b) A 48 Ω resistor is connected to the same battery. What current flows?

1. We want $I$, so use $I = \dfrac{V}{R}$.
2. $I = \dfrac{12}{48} = 0.25$ A.
3. Check: $0.25 \times 48 = 12$ V ✓. Twice the resistance gives half the current.

## Small and large units: mA and kΩ

Real circuits often use very small currents and very large resistances. So we use **prefixes**:

- **milli** (m) means one thousandth. $1\ \text{mA} = 0.001$ A, so 1 A = 1000 mA.
- **kilo** (k) means one thousand. $1\ \text{k}\Omega = 1000\ \Omega$.

| To change | Do this | Example |
|---|---|---|
| mA to A | divide by 1000 | 250 mA = 0.25 A |
| A to mA | multiply by 1000 | 0.004 A = 4 mA |
| kΩ to Ω | multiply by 1000 | 2.2 kΩ = 2200 Ω |

> **Rule:** before you use $V = IR$, change every value to volts, amperes and ohms.

### Worked example 3: a 9 V battery and a 2.2 kΩ resistor

A 9 V battery is connected to a 2.2 kΩ resistor. Find the current in mA.

1. Change the resistance to ohms: $2.2\ \text{k}\Omega = 2.2 \times 1000 = 2200\ \Omega$.
2. Use $I = \dfrac{V}{R}$: $I = \dfrac{9}{2200} \approx 0.0041$ A.
3. Change to mA: $0.0041 \times 1000 = 4.1$ mA.
4. Check: $V = IR = 0.0041 \times 2200 \approx 9$ V ✓.

If you forget step 1, you get $\dfrac{9}{2.2} \approx 4.1$ A. That is 1000 times too big!

## Finding resistance from a table or a graph

In the lab, we change the voltage, read the current each time, and write the results in a table. Then we work out $R = \dfrac{V}{I}$ for each row.

### Worked example 4: testing a resistor

A student in Huye tests a resistor and gets these readings. Is it ohmic, and what is its resistance?

| $V$ (V) | 1.5 | 3.0 | 4.5 | 6.0 |
|---|---|---|---|---|
| $I$ (A) | 0.10 | 0.20 | 0.30 | 0.40 |

1. Work out $R = \dfrac{V}{I}$ for each column: $\dfrac{1.5}{0.10} = 15$, $\dfrac{3.0}{0.20} = 15$, $\dfrac{4.5}{0.30} = 15$ and $\dfrac{6.0}{0.40} = 15\ \Omega$.
2. $R$ is the same every time, so the resistor is ohmic: $R = 15\ \Omega$.
3. Plot $V$ (up) against $I$ (across). The points lie on a **straight line through the origin**:

```text
 V (V)
  6.0 |                       x
  4.5 |                 x
  3.0 |           x
  1.5 |     x
    0 +-----+-----+-----+-----+--> I (A)
      0   0.10  0.20  0.30  0.40
```

4. The **gradient** (steepness) of the line is rise ÷ run $= \dfrac{6.0 - 0}{0.40 - 0} = 15\ \Omega$. On a graph of $V$ against $I$, the gradient equals the resistance.
5. Check: doubling $V$ from 3.0 V to 6.0 V doubled $I$ from 0.20 A to 0.40 A, as Ohm's law says ✓.

## A lamp does not obey Ohm's law

A filament lamp has a thin metal wire, the **filament**, inside it. As more current flows, the filament gets very hot and glows. Does it still obey Ohm's law?

### Worked example 5: testing a torch lamp

| $V$ (V) | 1 | 2 | 4 | 6 |
|---|---|---|---|---|
| $I$ (A) | 0.10 | 0.16 | 0.24 | 0.30 |

1. Work out $R = \dfrac{V}{I}$ for each column: $\dfrac{1}{0.10} = 10\ \Omega$, $\dfrac{2}{0.16} = 12.5\ \Omega$, $\dfrac{4}{0.24} \approx 16.7\ \Omega$ and $\dfrac{6}{0.30} = 20\ \Omega$.
2. The resistance **rises** as the voltage rises. The filament gets hotter, and a hotter metal has a higher resistance.
3. So the lamp is **non-ohmic**. On a graph of $V$ against $I$, its points lie on a **curve** that gets steeper, not on a straight line.
4. Check: from 2 V to 4 V the voltage doubles, but the current only goes from 0.16 A to 0.24 A. It does not double ✓.

Ohm's law needs a constant temperature. The lamp breaks this condition, and that is why it does not obey the law.

## What does resistance depend on?

The resistance of a wire depends on four things:

- **Length:** a longer wire has more resistance.
- **Thickness:** a thicker wire has less resistance, because there is more room for the charge to flow.
- **Material:** copper has a very low resistance, so connecting wires are made of copper. Some alloys, such as nichrome, have a much higher resistance.
- **Temperature:** for a metal, a hotter wire has more resistance, as we saw with the lamp.

## Resistors in series

When components are joined one after another in a single loop, they are **in series**.

```text
     +------| |------+
     |      12 V     |
     |               |
     +--[4 Ω]--[6 Ω]-+
```

In a series circuit:

- the **same current** flows through every component, because there is only one path;
- the **total resistance** is the sum: $R = R_1 + R_2$;
- the voltages across the components **add up** to the battery voltage.

### Worked example 6: two resistors on a 12 V battery

A 4 Ω resistor and a 6 Ω resistor are connected in series to a 12 V battery, as in the diagram. Find the current and the voltage across each resistor.

1. Total resistance: $R = 4 + 6 = 10\ \Omega$.
2. Current: $I = \dfrac{V}{R} = \dfrac{12}{10} = 1.2$ A. This current flows through both resistors.
3. Voltage across the 4 Ω resistor: $V_1 = IR_1 = 1.2 \times 4 = 4.8$ V.
4. Voltage across the 6 Ω resistor: $V_2 = IR_2 = 1.2 \times 6 = 7.2$ V.
5. Check: $4.8 + 7.2 = 12$ V, the battery voltage ✓.

Build this circuit yourself in the PhET kit. Add an ammeter and a voltmeter and check the numbers.

```sim
phet-circuit-construction-kit-dc
```

## Try it

Use the lab below to repeat Worked example 4.

1. Set the resistance to 15 Ω.
2. Set the voltage to 1.5 V, 3 V, 4.5 V and 6 V in turn. Press **Record reading** each time.
3. Check that the current goes 0.10 A, 0.20 A, 0.30 A, 0.40 A.
4. Now change the resistance to 30 Ω and keep the voltage at 6 V. Predict the current first, then check it.

```sim
ohms-law-lab
```

## Safety

Mains electricity in Rwanda is 230 V. Even a small current through the body can be dangerous. Never touch bare wires, and never put metal objects into sockets.

Do your experiments only with cells, batteries or a low-voltage supply from your teacher. Never connect an ammeter straight across a battery: it has a very small resistance, so a large current flows and can damage the meter.

## Common mistakes

- **Forgetting to change mA to A or kΩ to Ω.** Always use volts, amperes and ohms in $V = IR$.
- **Leaving time in minutes in $Q = It$.** Change minutes to seconds first.
- **Connecting the meters the wrong way.** The ammeter goes in series. The voltmeter goes in parallel, across the component.
- **Using a lamp's resistance at one voltage to predict the current at another voltage.** $R = \dfrac{V}{I}$ gives the lamp's resistance only at that moment. Its resistance changes as it heats up.
- **Writing the formula upside down,** for example $R = \dfrac{I}{V}$. Check by putting your answer back into $V = IR$.
- **Thinking current is used up.** In a series circuit, the current is the same all the way round. It is the **energy** that is given to the components, not the charge.

## Check yourself

1. Find the current through a 10 Ω resistor connected to a 5 V supply.
2. What voltage is needed to push 3 A through 4 Ω?
3. Why is an ammeter connected in series?
4. A current of 0.25 A flows from a 12 V battery for 5 minutes. (a) How much charge passes? (b) How much energy does the battery give to this charge?
5. Change 80 mA to amperes and 4.7 kΩ to ohms.
6. A 6 V battery is connected to a 1.5 kΩ resistor. Find the current in mA.
7. A student gets these readings for a component: 2.0 V and 0.25 A, 4.0 V and 0.50 A, 6.0 V and 0.75 A. Is the component ohmic? What is its resistance?
8. A 3 Ω resistor and a 9 Ω resistor are connected in series to a 6 V battery. Find the current and the voltage across each resistor.

*Answers: 1) $I = \frac{5}{10} = 0.5$ A · 2) $V = 3 \times 4 = 12$ V · 3) so that all the current in that part of the circuit passes through it · 4) (a) $t = 5 \times 60 = 300$ s, so $Q = 0.25 \times 300 = 75$ C; (b) each coulomb gets 12 J, so $12 \times 75 = 900$ J · 5) 0.08 A and 4700 Ω · 6) $I = \frac{6}{1500} = 0.004$ A = 4 mA · 7) yes, it is ohmic: $\frac{2.0}{0.25} = \frac{4.0}{0.50} = \frac{6.0}{0.75} = 8\ \Omega$ every time · 8) $R = 3 + 9 = 12\ \Omega$ and $I = \frac{6}{12} = 0.5$ A; the voltages are $0.5 \times 3 = 1.5$ V and $0.5 \times 9 = 4.5$ V (check: $1.5 + 4.5 = 6$ V)*
