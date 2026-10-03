---
slug: s3-maths-sets-venn-diagrams
subject: mathematics
grade: S3
unit: 3
order: 1
title: Sets and Venn diagrams
summary: Use set notation, find unions, intersections and complements, and solve counting problems with Venn diagrams.
minutes: 30
simulations:
---
## What is a set?

A **set** is a well-defined collection of objects. The objects are called **elements** (or members). We name sets with capital letters and list their elements inside curly brackets.

- $V = \{a, e, i, o, u\}$ is the set of vowels in the English alphabet.
- $E = \{x : x \text{ is an even number}, 1 \le x \le 10\} = \{2, 4, 6, 8, 10\}$. Read the colon as "such that".

"Well-defined" means we can always decide whether something belongs. "The set of tall students" is **not** well-defined, because "tall" is a matter of opinion. "The set of students taller than 160 cm" is well-defined.

## Key words and symbols

| Term | Symbol | Meaning | Example |
|---|---|---|---|
| is an element of | $\in$ | belongs to the set | $e \in V$ |
| is not an element of | $\notin$ | does not belong | $b \notin V$ |
| number of elements | $n(A)$ | how many elements $A$ has | $n(V) = 5$ |
| empty set | $\varnothing$ or $\{\ \}$ | a set with no elements | months with 32 days |
| universal set | $\xi$ or $U$ | all the elements under discussion | $\xi = \{1, 2, \dots, 12\}$ |
| subset | $A \subseteq B$ | every element of $A$ is also in $B$ | $\{2, 4\} \subseteq E$ |

The empty set is a subset of every set, and every set is a subset of itself. A set with $n$ elements has $2^n$ subsets. For example, $\{a, b\}$ has $2^2 = 4$ subsets: $\varnothing$, $\{a\}$, $\{b\}$ and $\{a, b\}$.

## Combining sets

- **Union** $A \cup B$: the elements in $A$ **or** $B$ **or both**.
- **Intersection** $A \cap B$: the elements in **both** $A$ and $B$.
- **Complement** $A'$: the elements of $\xi$ that are **not** in $A$.
- Two sets are **disjoint** if they have no elements in common, that is $A \cap B = \varnothing$.

### Worked example 1

Let $\xi = \{1, 2, 3, \dots, 12\}$, $A = \{\text{even numbers}\}$ and $B = \{\text{multiples of } 3\}$.

- $A = \{2, 4, 6, 8, 10, 12\}$ and $B = \{3, 6, 9, 12\}$.
- $A \cap B = \{6, 12\}$, the numbers in both lists.
- $A \cup B = \{2, 3, 4, 6, 8, 9, 10, 12\}$. Write $6$ and $12$ only once, so $n(A \cup B) = 8$.
- $A' = \{1, 3, 5, 7, 9, 11\}$.
- $(A \cup B)' = \{1, 5, 7, 11\}$, so $n\big((A \cup B)'\big) = 12 - 8 = 4$.

## Venn diagrams

A **Venn diagram** shows sets as pictures. A rectangle stands for the universal set $\xi$ and each set is a circle inside it. Overlapping circles share elements. Two overlapping circles split the rectangle into four regions:

| Region | In words | Notation | Worked example 1 |
|---|---|---|---|
| in $A$ but not in $B$ | only $A$ | $A \cap B'$ | $\{2, 4, 8, 10\}$ |
| in the overlap | both $A$ and $B$ | $A \cap B$ | $\{6, 12\}$ |
| in $B$ but not in $A$ | only $B$ | $A' \cap B$ | $\{3, 9\}$ |
| outside both circles | neither | $(A \cup B)'$ | $\{1, 5, 7, 11\}$ |

Every element of $\xi$ sits in exactly one region, so the four regions together hold all 12 numbers: $4 + 2 + 2 + 4 = 12$ ✓.

## Counting with a Venn diagram

When we add $n(A)$ and $n(B)$, the elements in the overlap are counted **twice**. Subtract them once:

$$n(A \cup B) = n(A) + n(B) - n(A \cap B)$$

Check with worked example 1: $6 + 4 - 2 = 8$ ✓.

**Tip:** when filling in a Venn diagram, always start with the **overlap** and work outwards.

### Worked example 2

In an S3 class of 40 students at a school in Huye, 25 play football ($F$), 18 play volleyball ($V$) and 7 play neither. How many play both?

- Students who play at least one sport: $n(F \cup V) = 40 - 7 = 33$.
- Use the formula: $33 = 25 + 18 - n(F \cap V)$, so $n(F \cap V) = 43 - 33 = 10$.
- Fill the diagram from the middle: both $= 10$, football only $= 25 - 10 = 15$, volleyball only $= 18 - 10 = 8$, neither $= 7$.
- Check: $15 + 10 + 8 + 7 = 40$ ✓.

### Worked example 3: using an unknown

A survey of 60 households in a village in Rwamagana found that 35 keep cows, 30 keep goats and 5 keep neither. Let $x$ be the number that keep both.

- Cows only $= 35 - x$, both $= x$, goats only $= 30 - x$, neither $= 5$.
- The four regions add up to 60: $(35 - x) + x + (30 - x) + 5 = 60$.
- Simplify: $70 - x = 60$, so $x = 10$.
- So 10 households keep both, 25 keep cows only and 20 keep goats only. Check: $25 + 10 + 20 + 5 = 60$ ✓.

## Common mistakes

- Listing a shared element twice in a union. Each element is written once.
- Putting the full $n(A)$ in the "only $A$" region. Subtract the overlap first.
- Forgetting the region outside the circles. "Neither" is part of $\xi$ too.

## Check yourself

1. $\xi = \{1, 2, \dots, 10\}$, $P = \{\text{prime numbers}\}$ and $Q = \{\text{odd numbers}\}$. List $P \cap Q$ and find $n(P \cup Q)$.
2. $n(A) = 14$, $n(B) = 9$ and $n(A \cup B) = 19$. Find $n(A \cap B)$.
3. How many subsets does $\{x, y, z\}$ have?

*Answers: 1) $P = \{2, 3, 5, 7\}$ and $Q = \{1, 3, 5, 7, 9\}$, so $P \cap Q = \{3, 5, 7\}$ and $n(P \cup Q) = 4 + 5 - 3 = 6$ · 2) $14 + 9 - 19 = 4$ · 3) $2^3 = 8$*
