---
slug: s4-physics-projectile-motion
subject: physics
grade: S4
unit: 1
order: 1
title: Projectile motion
summary: Split the motion into horizontal and vertical parts to find the time of flight, maximum height, range and velocity of an object thrown at an angle or sideways.
minutes: 45
simulations: projectile-lab, phet-projectile-motion
---
## The big idea

A **projectile** is any object that is thrown, kicked or launched into the air and then moves under gravity alone. A football kicked on a school pitch in Huye, a stone thrown into Lake Kivu and water from a hosepipe are all projectiles. In this lesson we ignore air resistance.

The path of a projectile is called its **trajectory**. Without air resistance, the trajectory is a curve called a **parabola**. The object rises, slows down, turns over at the top and comes back down.

The key trick of this lesson is simple: treat the **horizontal** motion and the **vertical** motion **separately**. They happen at the same time, but they do not affect each other.

- Horizontally, no force acts on the ball. So the horizontal velocity stays **constant**.
- Vertically, gravity pulls the ball down. So there is a constant downward acceleration $g = 9.8\ \text{m/s}^2$.

The two motions share only one thing: **time**. The ball spends the same number of seconds moving sideways as it does moving up and down.

> **Tip:** Drop one stone and throw another sideways from the same height at the same moment. They hit flat ground together. The sideways speed does not change how fast a stone falls.

## Resolving the launch velocity

Suppose a ball is launched at speed $u$ and angle $\theta$ above the horizontal. We split, or **resolve**, this velocity into two **components**: one horizontal and one vertical.

$$u_x = u\cos\theta \qquad u_y = u\sin\theta$$

Here is a football kicked at $u = 20$ m/s and $\theta = 30^\circ$:

```text
                  /|
    u = 20 m/s  /  |
              /    | u_y = 20 sin 30°
            /      |     = 10 m/s
          /  30°   |
         +---------+
   u_x = 20 cos 30° = 17.3 m/s
```

The two components and $u$ form a right-angled triangle, so Pythagoras checks them: $\sqrt{17.32^2 + 10^2} = \sqrt{300 + 100} = 20$ m/s ✓.

> Make sure your calculator is in **degrees** mode (it shows D or DEG). Test it: $\sin 30^\circ$ must give $0.5$.

## The equations of motion, with signs

For motion in a straight line with a constant acceleration $a$, three standard equations link the starting velocity $u$, the velocity $v$ after a time $t$, and the **displacement** $s$ (how far the object is from its start, with a sign):

$$v = u + at \qquad s = ut + \tfrac{1}{2}at^2 \qquad v^2 = u^2 + 2as$$

A projectile moves in two directions at once, so we use these equations twice: once horizontally and once vertically.

First we need a **sign convention**: a rule for which direction counts as positive. In this lesson, **up is positive** and down is negative. Gravity points down, so the vertical acceleration is $a = -g = -9.8\ \text{m/s}^2$. We measure the positions $x$ and $y$ from the launch point.

| | Horizontal ($x$) | Vertical ($y$, up is +) |
|---|---|---|
| Acceleration | $0$ | $-g$ |
| Velocity at time $t$ | $v_x = u_x$ (constant) | $v_y = u_y - gt$ |
| Position at time $t$ | $x = u_x t$ | $y = u_y t - \tfrac{1}{2} g t^2$ |
| Without $t$ | — | $v_y^2 = u_y^2 - 2gy$ |

For example, the vertical position comes from $s = ut + \tfrac{1}{2}at^2$ with $s = y$, $u = u_y$ and $a = -g$. Everything in this lesson comes from this table.

## Three formulas for level ground

When the ball lands at the same height it started from, we can build three useful formulas. Let us derive each one step by step.

**Time of flight $T$.** This is the total time in the air. The ball is back at its starting height when $y = 0$. Put $y = 0$ and $u_y = u\sin\theta$ into $y = u_y t - \tfrac{1}{2} g t^2$:

$$u\sin\theta \, t - \tfrac{1}{2} g t^2 = 0$$

Take out the common factor $t$:

$$t\left(u\sin\theta - \tfrac{1}{2} g t\right) = 0$$

So either $t = 0$, which is the moment of launch, or $u\sin\theta = \tfrac{1}{2} g t$, which is the landing. Solve the second one for $t$: multiply both sides by 2, then divide both sides by $g$:

$$T = \frac{2u\sin\theta}{g}$$

**Maximum height $H$.** At the highest point, the ball stops going up for an instant, so $v_y = 0$. Put $v_y = 0$, $y = H$ and $u_y^2 = u^2\sin^2\theta$ into $v_y^2 = u_y^2 - 2gy$:

$$0 = u^2\sin^2\theta - 2gH$$

Add $2gH$ to both sides, so $2gH = u^2\sin^2\theta$. Then divide both sides by $2g$:

$$H = \frac{u^2 \sin^2\theta}{2g}$$

The time to reach the top comes from $v_y = u_y - gt$ with $v_y = 0$. This gives $0 = u\sin\theta - gt$, so $t_{\text{top}} = \dfrac{u\sin\theta}{g}$. This is exactly **half** of $T$: the way up takes as long as the way down.

**Range $R$.** The **range** is the horizontal distance travelled. The horizontal speed is constant, so distance = speed × time:

$$R = u_x \times T = u\cos\theta \times \frac{2u\sin\theta}{g} = \frac{u^2 \times 2\sin\theta\cos\theta}{g}$$

A trigonometry identity says $2\sin\theta\cos\theta = \sin 2\theta$. Check it with $\theta = 30^\circ$: $2 \times 0.5 \times 0.866 = 0.866$, and $\sin 60^\circ = 0.866$ ✓. So

$$R = \frac{u^2 \sin 2\theta}{g}$$

> These three formulas work **only** when the launch and the landing are at the same height. For a cliff or a table, go back to the table of equations.

### Worked example 1: a football kick in Huye

A footballer kicks a ball at 20 m/s at 30° above the ground. Find the time of flight, the maximum height and the range. Take $g = 9.8\ \text{m/s}^2$.

1. Components: $u_x = 20\cos 30^\circ = 17.32$ m/s and $u_y = 20\sin 30^\circ = 10$ m/s.
2. Time of flight: $T = \dfrac{2 \times 10}{9.8} = \dfrac{20}{9.8} \approx 2.04$ s.
3. Maximum height: $H = \dfrac{20^2 \times 0.5^2}{2 \times 9.8} = \dfrac{100}{19.6} \approx 5.10$ m.
4. Range: $R = \dfrac{20^2 \times \sin 60^\circ}{9.8} = \dfrac{400 \times 0.866}{9.8} \approx 35.3$ m.
5. Check: the range should also equal $u_x \times T = 17.32 \times 2.04 \approx 35.3$ m ✓.

## Which angle goes furthest?

The value of $\sin 2\theta$ can never be bigger than 1. It equals 1 when $2\theta = 90^\circ$. So the **maximum range on level ground is at 45°**.

Also, two angles that add up to 90° give the **same range**. Examples are 30° and 60°, or 25° and 65°. Such angles are called **complementary angles**. The kick at the bigger angle flies higher and stays in the air longer, but it lands in the same place.

### Worked example 2: the same kick at 60°

The footballer kicks again at 20 m/s, but this time at 60°. Compare the results with Worked example 1.

1. Components: $u_x = 20\cos 60^\circ = 10$ m/s and $u_y = 20\sin 60^\circ = 17.32$ m/s.
2. Time of flight: $T = \dfrac{2 \times 17.32}{9.8} \approx 3.53$ s, longer than 2.04 s.
3. Maximum height: $H = \dfrac{17.32^2}{2 \times 9.8} = \dfrac{300}{19.6} \approx 15.3$ m, three times higher.
4. Range: $R = \dfrac{400 \times \sin 120^\circ}{9.8} = \dfrac{400 \times 0.866}{9.8} \approx 35.3$ m.
5. Check: the range is the same as at 30°, because $30^\circ + 60^\circ = 90^\circ$ ✓.

## Velocity and position at any moment

**Velocity** means speed together with direction. At any time $t$, the velocity has two components: $v_x = u_x$, which never changes, and $v_y = u_y - gt$. To get the actual velocity, combine them with Pythagoras:

$$v = \sqrt{v_x^2 + v_y^2} \qquad \tan\alpha = \frac{|v_y|}{v_x}$$

Here $v$ is the speed and $\alpha$ is the angle between the velocity and the horizontal. The bars in $|v_y|$ mean "the size of $v_y$ without its sign". If $v_y$ is positive, the ball is still rising. If $v_y$ is negative, the ball is falling. To get the angle from $\tan\alpha$, use the $\tan^{-1}$ key on your calculator (often SHIFT then tan).

At the very top, $v_y = 0$, but $v_x$ is not zero. So the velocity at the top is $u\cos\theta$, pointing horizontally. It is **not** zero.

### Worked example 3: the football after 1.5 seconds

Use the kick from Worked example 1 (20 m/s at 30°). Find the ball's velocity 1.5 s after the kick.

1. Horizontal: $v_x = u_x = 17.32$ m/s.
2. Vertical: $v_y = 10 - 9.8 \times 1.5 = 10 - 14.7 = -4.7$ m/s. The minus sign means the ball is moving **down**.
3. Speed: $v = \sqrt{17.32^2 + 4.7^2} = \sqrt{300 + 22.09} = \sqrt{322.09} \approx 17.9$ m/s.
4. Direction: $\tan\alpha = \dfrac{4.7}{17.32} \approx 0.271$, so $\alpha = \tan^{-1} 0.271 \approx 15.2^\circ$ below the horizontal.
5. Check: the ball reaches the top at $t_{\text{top}} = \dfrac{10}{9.8} \approx 1.02$ s. At 1.5 s it is past the top, so it should be falling, and $v_y$ is indeed negative ✓.

### Worked example 4: does it clear the crossbar?

The same ball (20 m/s at 30°) is kicked towards a goal 30 m away. The crossbar is 2.44 m high. Does the ball go over the bar?

1. Find when the ball reaches the goal line. Horizontally $x = u_x t$, so $t = \dfrac{30}{17.32} \approx 1.732$ s.
2. Find its height at that moment, using $\tfrac{1}{2} g = \tfrac{1}{2} \times 9.8 = 4.9$: $y = u_y t - \tfrac{1}{2} g t^2 = 10 \times 1.732 - 4.9 \times 1.732^2$.
3. Since $1.732^2 = 3.00$, we get $y = 17.32 - 14.70 = 2.62$ m.
4. Compare: 2.62 m is more than 2.44 m, so the ball passes about 0.18 m (18 cm) **over** the crossbar.
5. Check: 1.732 s is less than $T = 2.04$ s, so the ball really is still in the air when it reaches the goal ✓.

## Horizontal launch

Many objects start moving **horizontally** from a height. Think of a ball rolling off a table, or a stone thrown sideways from a cliff. You will meet this type of question often.

For a horizontal launch, $\theta = 0^\circ$, so:

- $u_x = u$, because all of the speed is horizontal;
- $u_y = 0$, because there is no starting vertical speed.

The object falls exactly like a dropped stone while it moves sideways at a constant speed. If it falls a height $h$, then $y = -h$ (down is negative). The vertical equation gives

$$-h = 0 - \tfrac{1}{2} g t^2$$

Multiply both sides by $-2$ and divide by $g$ to get $t^2 = \dfrac{2h}{g}$. Then take the square root:

$$t = \sqrt{\frac{2h}{g}}$$

Once you know $t$, the horizontal distance is $x = ut$.

The landing point is lower than the launch point, so do **not** use the level-ground formulas for $T$, $H$ and $R$ here.

### Worked example 5: a stone thrown from a cliff by Lake Kivu

A student stands on a cliff 20 m above the water of Lake Kivu. She throws a stone horizontally at 12 m/s. Find (a) the time until it hits the water, (b) how far from the cliff it lands, and (c) its velocity as it hits the water.

1. What we know: $u_x = 12$ m/s, $u_y = 0$, $y = -20$ m and $g = 9.8\ \text{m/s}^2$.
2. (a) Time: put $u_y = 0$ and $y = -20$ into $y = u_y t - \tfrac{1}{2} g t^2$. This gives $-20 = -4.9t^2$, so $t^2 = \dfrac{20}{4.9} \approx 4.08$ and $t = \sqrt{4.08} \approx 2.02$ s.
3. (b) Distance: $x = u_x t = 12 \times 2.02 \approx 24.2$ m.
4. (c) Vertical velocity: $v_y = 0 - 9.8 \times 2.02 \approx -19.8$ m/s, downward. The horizontal velocity is still 12 m/s.
5. Speed: $v = \sqrt{12^2 + 19.8^2} = \sqrt{144 + 392} = \sqrt{536} \approx 23.2$ m/s.
6. Direction: $\tan\alpha = \dfrac{19.8}{12} = 1.65$, so $\alpha = \tan^{-1} 1.65 \approx 58.8^\circ$ below the horizontal.
7. Check with the "without $t$" equation: $v_y^2 = 0 - 2 \times 9.8 \times (-20) = 392$, and $\sqrt{392} \approx 19.8$ ✓.

## Real balls and air resistance

Our formulas ignore **air resistance** (also called **drag**), which is the push of the air against a moving object. Real balls do feel it. It slows them down, so a real football usually lands **shorter** than $R$ predicts and does not rise quite as high.

The real path is not a perfect parabola either: it comes down more steeply than it went up. With air resistance, the best angle for a long throw is often a little less than 45°.

For a small, heavy object such as a stone, our formulas give a good estimate. For a light object such as a paper ball, air resistance matters a lot, and the formulas do not work well.

## Experiment

Open the lab below and choose Earth gravity.

1. Set the angle to 30° and the speed to 20 m/s. Press **Launch**. Compare the time of flight, maximum height and range with Worked example 1 (2.04 s, 5.10 m and 35.3 m).
2. Change the angle to 60° and launch again. Is the range the same? Is the path higher?
3. Try 40°, 45° and 50°. Which angle lands furthest?
4. Go back to 30° and double the speed to 40 m/s. Before you launch, look at $u^2$ in the range formula and predict: does the range double?

```sim
projectile-lab
```

The PhET projectile lab, listed after the lesson under "Try it in the lab", also lets you add air resistance and compare the paths.

## Common mistakes

- **Using $u$ instead of a component.** In the vertical equations, use $u_y = u\sin\theta$. In the horizontal ones, use $u_x = u\cos\theta$. Never put the full $u$ into either.
- **Mixing up the time to the top and the total time.** $t_{\text{top}} = \dfrac{u\sin\theta}{g}$ is only half of $T = \dfrac{2u\sin\theta}{g}$.
- **Giving $g$ the wrong sign.** With up as positive, the vertical acceleration is $-9.8\ \text{m/s}^2$. A falling ball has a negative $v_y$, and a point below the launch has a negative $y$.
- **Leaving the calculator in radians.** In radians mode, $\sin 30$ gives $-0.988$ instead of $0.5$, and every answer after that is wrong.
- **Saying the velocity is zero at the top.** Only the vertical part is zero. The ball still moves sideways at $u\cos\theta$.
- **Using $T$, $H$ and $R$ for a cliff or a table.** Those formulas need the launch and the landing at the same height.

## Check yourself

1. A stone is thrown at 15 m/s at 45°. Find its range ($g = 9.8$).
2. Which launch angle gives the same range as 20°?
3. What is the vertical velocity of a projectile at its highest point? What is its horizontal velocity there?
4. A ball is thrown at 14 m/s at 30° on level ground. Find (a) its time of flight and (b) its maximum height.
5. For the ball in question 4, find its speed and direction 1.0 s after it is thrown.
6. A boy throws a ball horizontally at 5 m/s from a window 4.9 m above the ground. How long does the ball take to land, and how far from the wall does it land?
7. A ball kicked at 20 m/s at 30° has a range of about 35.3 m. What is the range if it is kicked at 40 m/s at the same angle?

*Answers: 1) $R = \frac{15^2 \times \sin 90^\circ}{9.8} = \frac{225}{9.8} \approx 23.0$ m · 2) 70°, because $20^\circ + 70^\circ = 90^\circ$ · 3) the vertical velocity is zero; the horizontal velocity is still $u\cos\theta$, so the ball is not at rest · 4) $u_y = 14 \sin 30^\circ = 7$ m/s, so (a) $T = \frac{2 \times 7}{9.8} \approx 1.43$ s and (b) $H = \frac{7^2}{2 \times 9.8} = \frac{49}{19.6} = 2.5$ m · 5) $v_x = 14\cos 30^\circ \approx 12.1$ m/s and $v_y = 7 - 9.8 \times 1.0 = -2.8$ m/s, so $v = \sqrt{12.1^2 + 2.8^2} \approx 12.4$ m/s at about 13.0° below the horizontal · 6) $t = \sqrt{\frac{2 \times 4.9}{9.8}} = 1.0$ s and $x = 5 \times 1.0 = 5.0$ m · 7) about 141 m: doubling the speed makes the range four times bigger, because $R$ depends on $u^2$, so $R \approx 4 \times 35.3 \approx 141$ m*
