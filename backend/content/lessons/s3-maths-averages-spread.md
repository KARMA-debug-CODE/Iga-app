---
slug: s3-maths-averages-spread
subject: mathematics
grade: S3
unit: 7
order: 1
title: Averages and spread
summary: Find the mean, median, mode, range and interquartile range of a data set, including data in a frequency table, and choose the best average for a situation.
minutes: 35
simulations:
---
## Why averages and spread?

A list of numbers is hard to understand at a glance. Statistics summarises data with two kinds of number:

- an **average** (a measure of central tendency), one value that represents the whole set;
- a **measure of spread** (dispersion), which shows how far the values are scattered.

Two moto taxi drivers can both earn 10,000 FRW a day on average, yet one earns almost the same every day while the other earns very different amounts. The average is the same, but the spread is not.

## The three averages

**Mean.** Add all the values and divide by how many there are:

$$\bar{x} = \frac{\sum x}{n}$$

**Median.** Arrange the values in order. The median is the middle value, in position $\frac{n + 1}{2}$. If $n$ is even, it is the mean of the two middle values.

**Mode.** The value that occurs most often. A set can have one mode, more than one, or none.

## Measures of spread

**Range** $=$ largest value $-$ smallest value.

**Interquartile range (IQR).** Arrange the data in order and split it into a lower half and an upper half. The **lower quartile** $Q_1$ is the median of the lower half and the **upper quartile** $Q_3$ is the median of the upper half. If $n$ is odd, leave the median itself out of both halves. Then

$$\text{IQR} = Q_3 - Q_1$$

The IQR measures the spread of the middle half of the data, so it is not affected by one very large or very small value.

### Worked example 1: a moto driver's week

A moto taxi driver in Kigali recorded his earnings (FRW) for one week:

8,000 · 12,500 · 6,000 · 9,500 · 15,000 · 11,000 · 8,000

- **Mean:** total $= 70\,000$, so $\bar{x} = \frac{70\,000}{7} = 10\,000$ FRW.
- **Median:** in order, 6,000 · 8,000 · 8,000 · **9,500** · 11,000 · 12,500 · 15,000. With $n = 7$, the median is the $\frac{7 + 1}{2} = 4$th value, 9,500 FRW.
- **Mode:** 8,000 FRW appears twice, so the mode is 8,000 FRW.
- **Range:** $15\,000 - 6\,000 = 9\,000$ FRW.

## Data in a frequency table

When values repeat, a frequency table saves writing. Multiply each value $x$ by its frequency $f$:

$$\bar{x} = \frac{\sum fx}{\sum f}$$

### Worked example 2: household sizes

A survey of 20 households in a village in Rwamagana recorded the number of people living in each.

| People per household, $x$ | 2 | 3 | 4 | 5 | 6 | Total |
|---|---|---|---|---|---|---|
| Frequency, $f$ | 3 | 5 | 6 | 4 | 2 | 20 |
| $fx$ | 6 | 15 | 24 | 20 | 12 | 77 |
| Cumulative frequency | 3 | 8 | 14 | 18 | 20 | |

- **Mean:** $\bar{x} = \frac{77}{20} = 3.85$ people. A mean does not have to be a whole number.
- **Median:** $n = 20$, so the median lies between the 10th and 11th values. The cumulative frequencies show that values 9 to 14 are all 4, so the median is 4.
- **Mode:** 4 has the highest frequency (6), so the mode is 4.
- **Range:** $6 - 2 = 4$.

### Worked example 3: when the mean misleads

Six people work at a small tailoring workshop in Kigali. Their monthly wages (FRW) are:

60,000 · 60,000 · 70,000 · 75,000 · 85,000 · 450,000 (the owner)

- **Mean:** total $= 800\,000$, so $\bar{x} = \frac{800\,000}{6} \approx 133\,333$ FRW.
- **Median:** $n = 6$ is even, so take the mean of the 3rd and 4th values: $\frac{70\,000 + 75\,000}{2} = 72\,500$ FRW.

Five of the six workers earn **less** than the mean, because the owner's large wage pulls it up. The median, 72,500 FRW, describes a typical wage much better.

### Worked example 4: quartiles of a maize harvest

Eight farmers in Nyagatare harvested these numbers of bags of maize, already in order:

12 · 15 · 18 · 20 · 22 · 25 · 27 · 35

- Median $= \frac{20 + 22}{2} = 21$ bags.
- Lower half: 12, 15, 18, 20, so $Q_1 = \frac{15 + 18}{2} = 16.5$.
- Upper half: 22, 25, 27, 35, so $Q_3 = \frac{25 + 27}{2} = 26$.
- $\text{IQR} = 26 - 16.5 = 9.5$ bags, while the range is $35 - 12 = 23$ bags. The single large harvest of 35 bags stretches the range but hardly changes the IQR.

## Choosing the right measure

| Measure | Strength | Weakness |
|---|---|---|
| Mean | uses every value | pulled by extreme values |
| Median | not affected by extreme values | ignores the size of most values |
| Mode | works for categories, such as the most popular crop | may not exist, or there may be several |
| Range | quick and simple | depends only on the two extreme values |
| IQR | ignores extreme values | takes longer to work out |

For example, a shopkeeper at Kimironko market who wants to know which shoe size to stock most of should use the **mode**.

## Class activity

Ask 15 classmates how many minutes they take to travel to school. Find the mean, median, mode and range of your data, and say which average best describes a typical journey and why.

## Check yourself

1. Find the mean, median, mode and range of 5, 10, 3, 10, 4, 16.
2. The mean of five numbers is 12. Four of them are 11, 14, 9 and 15. Find the fifth number.
3. Which average is best for the most popular school-uniform size sold in a shop, and why?

*Answers: 1) mean $= \frac{48}{6} = 8$; in order 3, 4, 5, 10, 10, 16, so median $= \frac{5 + 10}{2} = 7.5$; mode $= 10$; range $= 16 - 3 = 13$ · 2) total $= 5 \times 12 = 60$, and $60 - (11 + 14 + 9 + 15) = 60 - 49 = 11$ · 3) the mode, because sizes are categories and the shop wants the one that occurs most often*
