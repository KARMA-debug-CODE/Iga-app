---
slug: s3-maths-trigonometric-ratios
subject: mathematics
grade: S3
unit: 4
order: 1
title: Sine, cosine and tangent
summary: Use the sine, cosine and tangent ratios in right-angled triangles to find missing sides and angles, including angles of elevation and depression.
minutes: 40
simulations: phet-trig-tour, geogebra-geometry
---
## Naming the sides

**Trigonometry** links the angles of a triangle to the lengths of its sides. In this unit we work with **right-angled triangles**. Choose one of the two acute angles and call it $\theta$ (theta). The three sides are then named **relative to $\theta$**:

- **Hypotenuse (H):** the longest side, opposite the right angle.
- **Opposite (O):** the side facing $\theta$.
- **Adjacent (A):** the side next to $\theta$ that is not the hypotenuse.

```text
            P
            |\
            | \
            |  \
  opposite  |   \  hypotenuse
            |    \
            |_    \
            |_|__θ_\
            Q       R
             adjacent
```

If you choose the other acute angle instead, the opposite and adjacent sides swap. The hypotenuse never changes.

## The three ratios

$$\sin\theta = \frac{\text{opposite}}{\text{hypotenuse}} \qquad \cos\theta = \frac{\text{adjacent}}{\text{hypotenuse}} \qquad \tan\theta = \frac{\text{opposite}}{\text{adjacent}}$$

A memory aid: **SOH CAH TOA**.

The ratios depend only on the angle, not on the size of the triangle, because similar triangles have sides in the same proportion. The hypotenuse is the longest side, so for an acute angle $\sin\theta$ and $\cos\theta$ always lie between 0 and 1. $\tan\theta$ can be any positive number.

### Worked example 1: writing the ratios

A right-angled triangle has sides 5 cm, 12 cm and 13 cm, and $\theta$ is the angle opposite the 5 cm side.

- Hypotenuse $= 13$ (the longest side), opposite $= 5$, adjacent $= 12$.
- $\sin\theta = \frac{5}{13} \approx 0.385$, $\cos\theta = \frac{12}{13} \approx 0.923$ and $\tan\theta = \frac{5}{12} \approx 0.417$.

## Special angles

These exact values come from half of an equilateral triangle (30° and 60°) and from half of a square (45°).

| | $30^\circ$ | $45^\circ$ | $60^\circ$ |
|---|---|---|---|
| $\sin\theta$ | $\frac{1}{2}$ | $\frac{\sqrt{2}}{2}$ | $\frac{\sqrt{3}}{2}$ |
| $\cos\theta$ | $\frac{\sqrt{3}}{2}$ | $\frac{\sqrt{2}}{2}$ | $\frac{1}{2}$ |
| $\tan\theta$ | $\frac{\sqrt{3}}{3}$ | $1$ | $\sqrt{3}$ |

Notice that $\sin 30^\circ = \cos 60^\circ$. In general $\sin\theta = \cos(90^\circ - \theta)$.

## Finding a missing side

1. Label the sides O, A and H from the given angle.
2. Choose the ratio that uses the side you know and the side you want.
3. Substitute and solve. First check that your calculator is in **degree mode** (DEG).

### Worked example 2: a ladder

A 6 m ladder leans against the wall of a house, making an angle of $70^\circ$ with the ground. How high up the wall does it reach, and how far is its foot from the wall?

- The ladder is the hypotenuse, $H = 6$. The height is opposite the $70^\circ$ angle and the distance along the ground is adjacent.
- Height: $\sin 70^\circ = \frac{h}{6}$, so $h = 6\sin 70^\circ \approx 6 \times 0.9397 \approx 5.64$ m.
- Foot: $\cos 70^\circ = \frac{d}{6}$, so $d = 6\cos 70^\circ \approx 6 \times 0.3420 \approx 2.05$ m.
- Check with Pythagoras: $5.64^2 + 2.05^2 \approx 31.81 + 4.20 = 36.01 \approx 6^2$. Correct.

### Worked example 3: the unknown on the bottom

A steel cable supports a telecom mast. It is fixed to the mast 15 m above the ground and makes an angle of $58^\circ$ with the ground. How long is the cable?

- The cable is the hypotenuse $L$, and 15 m is opposite the $58^\circ$ angle, so use sine.
- $\sin 58^\circ = \frac{15}{L}$, so $L = \frac{15}{\sin 58^\circ} \approx \frac{15}{0.8480} \approx 17.69$ m.

## Finding a missing angle

When you know two sides, work out the ratio and then use the **inverse** function on your calculator: $\sin^{-1}$, $\cos^{-1}$ or $\tan^{-1}$ (usually SHIFT then sin, cos or tan).

### Worked example 4: a steep road

A straight section of road climbing a hill near Kigali rises 120 m vertically over a horizontal distance of 1,500 m. Find the angle between the road and the horizontal.

- 120 m is opposite $\theta$ and 1,500 m is adjacent, so use tangent.
- $\tan\theta = \frac{120}{1\,500} = 0.08$
- $\theta = \tan^{-1}(0.08) \approx 4.6^\circ$

## Angles of elevation and depression

- The **angle of elevation** is measured **up** from the horizontal to an object above you.
- The **angle of depression** is measured **down** from the horizontal to an object below you.

The angle of depression from a point P down to a point Q equals the angle of elevation from Q up to P, because they are alternate angles between parallel horizontal lines.

### Worked example 5: the height of a tree

A student stands 25 m from the foot of a eucalyptus tree on level ground. Holding a clinometer at eye level, 1.5 m above the ground, she measures the angle of elevation of the top as $52^\circ$. How tall is the tree?

- Height above her eyes: $\tan 52^\circ = \frac{x}{25}$, so $x = 25\tan 52^\circ \approx 25 \times 1.2799 \approx 32.0$ m.
- Add her eye height: $32.0 + 1.5 = 33.5$ m.

### Worked example 6: a boat on Lake Kivu

From a hotel balcony on the shore at Rubavu, 20 m above the surface of Lake Kivu, the angle of depression of a fishing boat is $12^\circ$. How far is the boat from the point at the water's edge directly below the balcony?

- The angle of elevation from the boat to the balcony is also $12^\circ$. The 20 m height is opposite and the distance $d$ is adjacent.
- $\tan 12^\circ = \frac{20}{d}$, so $d = \frac{20}{\tan 12^\circ} \approx \frac{20}{0.2126} \approx 94.1$ m.

## Practical activity: make a clinometer

Tape a drinking straw along the straight edge of a protractor and hang a small stone on a thread from its centre hole. When the straw is level, the thread hangs at $90^\circ$. Look at the top of a tree or the school flagpole through the straw: the angle of elevation is the difference between $90^\circ$ and the reading on the thread. Pace out your distance from the foot of the object, then calculate its height as in worked example 5.

> **Safety:** never look at the sun through the straw, as it can damage your eyes. Work in pairs on the school grounds, away from roads and moto traffic, and do not climb trees or walls to take measurements. Watch your footing on slopes and drainage ditches while you pace out distances.

## Explore

In Trig Tour, drag the point around the circle and watch how the values of sine, cosine and tangent change. For which angle between $0^\circ$ and $90^\circ$ are $\sin\theta$ and $\cos\theta$ equal?

```sim
phet-trig-tour
```

## Check yourself

1. In a right-angled triangle the hypotenuse is 20 cm and one angle is $30^\circ$. Find the side opposite the $30^\circ$ angle.
2. The opposite and adjacent sides of an angle $\theta$ are both 7 cm. Find $\theta$.
3. From a point 40 m from the foot of a building on level ground, the angle of elevation of the top is $35^\circ$. Find the height of the building to 1 decimal place.

*Answers: 1) $20\sin 30^\circ = 20 \times 0.5 = 10$ cm · 2) $\tan\theta = \frac{7}{7} = 1$, so $\theta = 45^\circ$ · 3) $40\tan 35^\circ \approx 40 \times 0.7002 \approx 28.0$ m*
