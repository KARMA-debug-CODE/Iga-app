---
slug: s6-physics-radioactivity
subject: physics
grade: S6
unit: 3
order: 1
title: Radioactivity and nuclear decay
summary: Why some nuclei are unstable, the properties of alpha, beta and gamma radiation, decay equations, and the exponential decay law with half-life.
minutes: 45
simulations: phet-build-an-atom, phet-build-a-nucleus, phet-rutherford-scattering
---
## The nucleus

Every atom has a tiny, dense **nucleus** made of protons and neutrons, together called **nucleons**. A nuclide is written

$${}^{A}_{Z}\text{X}$$

- $Z$ = **proton number** (atomic number), which fixes the element;
- $A$ = **nucleon number** (mass number) = protons + neutrons;
- number of neutrons $N = A - Z$.

**Isotopes** are atoms of the same element with different numbers of neutrons, for example ${}^{12}_{6}\text{C}$ (6 neutrons) and ${}^{14}_{6}\text{C}$ (8 neutrons).

The **strong nuclear force** holds the nucleons together against the electrical repulsion of the protons. A nucleus with too many or too few neutrons for its number of protons is **unstable**. All very large nuclei, with more than 82 protons, are unstable too.

Build some nuclei in the simulation. Keep the number of protons fixed and add or remove neutrons: when does the sim label the nucleus unstable?

```sim
phet-build-an-atom
```

## Radioactivity

An unstable nucleus becomes more stable by emitting radiation. This is **radioactive decay**. It is:

- **spontaneous**: it is not affected by temperature, pressure or chemical combination;
- **random**: we cannot predict when a particular nucleus will decay, only the fraction of a large number that will decay in a given time.

## Alpha, beta and gamma radiation

| Property | Alpha (α) | Beta-minus (β⁻) | Gamma (γ) |
|---|---|---|---|
| Nature | helium nucleus, ${}^{4}_{2}\text{He}$ | fast electron, ${}^{0}_{-1}e$ | electromagnetic wave (photon) |
| Charge | $+2e$ | $-e$ | 0 |
| Ionising power | strong | moderate | weak |
| Stopped by | a sheet of paper or a few cm of air | a few mm of aluminium | intensity reduced by several cm of lead or thick concrete |
| Deflected by electric and magnetic fields? | yes | yes, the opposite way and more strongly | no |

## Decay equations

In every nuclear equation, **nucleon number** and **proton number** (charge) are both conserved: the totals of $A$ and of $Z$ are the same on both sides.

**Alpha decay:** $A$ falls by 4 and $Z$ falls by 2.

$${}^{238}_{92}\text{U} \rightarrow {}^{234}_{90}\text{Th} + {}^{4}_{2}\text{He}$$

**Beta-minus decay:** a neutron in the nucleus changes into a proton, an electron and an antineutrino, ${}^{1}_{0}n \rightarrow {}^{1}_{1}p + {}^{0}_{-1}e + \bar{\nu}$. So $A$ is unchanged and $Z$ rises by 1.

$${}^{14}_{6}\text{C} \rightarrow {}^{14}_{7}\text{N} + {}^{0}_{-1}e + \bar{\nu}$$

**Gamma emission:** the nucleus loses extra energy. $A$ and $Z$ do not change. Gamma rays often follow alpha or beta decay.

### Worked example 1: a decay series

Thorium-232 (${}^{232}_{90}\text{Th}$) decays to stable lead-208 (${}^{208}_{82}\text{Pb}$) through a series of alpha and beta-minus decays. How many of each?

- Only alpha decay changes $A$. Fall in $A = 232 - 208 = 24$, so the number of alphas $= \dfrac{24}{4} = 6$.
- Six alphas lower $Z$ by $6 \times 2 = 12$, giving $90 - 12 = 78$.
- But lead has $Z = 82$. Each beta-minus raises $Z$ by 1, so the number of betas $= 82 - 78 = 4$.

**Answer: 6 alpha and 4 beta-minus decays.**

## Activity and the decay law

The **activity** $A$ of a sample is the number of nuclei decaying per second, measured in **becquerels** (1 Bq = 1 decay per second). It is proportional to the number $N$ of undecayed nuclei (do not confuse this activity $A$ with the nucleon number $A$):

$$A = \lambda N$$

where $\lambda$ is the **decay constant** (s⁻¹), the probability per second that a nucleus decays. Because $\dfrac{dN}{dt} = -\lambda N$, the number falls **exponentially**:

$$N = N_0 e^{-\lambda t} \qquad A = A_0 e^{-\lambda t}$$

The **half-life** $T_{1/2}$ is the time taken for half of the radioactive nuclei in a sample to decay, so that the number of undecayed nuclei (and the activity) falls to half its starting value:

$$T_{1/2} = \frac{\ln 2}{\lambda} \approx \frac{0.693}{\lambda} \qquad N = N_0\left(\tfrac{1}{2}\right)^{t/T_{1/2}}$$

| Nuclide | Half-life | Use |
|---|---|---|
| Iodine-131 | 8 days | treating thyroid disease |
| Phosphorus-32 | 14.3 days | tracer in plant and fertiliser studies |
| Cobalt-60 | 5.3 years | radiotherapy, sterilising medical equipment |
| Americium-241 | 432 years | smoke detectors |
| Carbon-14 | 5730 years | dating old organic material |

### Worked example 2: a hospital delivery

A hospital in Kigali receives an iodine-131 sample with an activity of 640 MBq. Its half-life is 8 days. What is the activity after 24 days?

Number of half-lives $= \dfrac{24}{8} = 3$.

$$640 \rightarrow 320 \rightarrow 160 \rightarrow 80\ \text{MBq}$$

Check: $640 \times \left(\tfrac{1}{2}\right)^3 = \dfrac{640}{8} = 80$ MBq.

### Worked example 3: decay constant and activity

Radon-222 has a half-life of 3.82 days. Find its decay constant, and the activity of a sample containing $1.0 \times 10^{10}$ radon nuclei.

Half-life in seconds: $3.82 \times 24 \times 3600 = 330\,048 \approx 3.30 \times 10^{5}$ s

$$\lambda = \frac{0.693}{3.30 \times 10^{5}} = 2.10 \times 10^{-6}\ \text{s}^{-1}$$

$$A = \lambda N = 2.10 \times 10^{-6} \times 1.0 \times 10^{10} = 2.1 \times 10^{4}\ \text{Bq}$$

### Worked example 4: carbon dating

Living things keep a constant proportion of carbon-14. After death, the carbon-14 decays. A piece of ancient charcoal found in a cave has 30% of the carbon-14 activity of fresh wood. How old is it?

$$0.30 = e^{-\lambda t} \quad\Rightarrow\quad t = \frac{\ln(1/0.30)}{\lambda} = T_{1/2} \times \frac{\ln(1/0.30)}{\ln 2}$$

$$t = 5730 \times \frac{1.2040}{0.6931} = 5730 \times 1.737 \approx 9950\ \text{years}$$

## Uses and background radiation

Radioisotopes are used to treat cancer, to sterilise syringes, and as **tracers**: agricultural researchers can add a little phosphorus-32 to fertiliser and measure how quickly bean plants in Musanze take it up.

We are all exposed to low-level **background radiation** from rocks and soil, radon gas, food, medical X-rays and cosmic rays. Cosmic radiation is stronger at high altitude, so a climber on Mount Karisimbi (4507 m) receives more cosmic radiation than a fisherman on Lake Kivu (about 1460 m).

## Safety

Ionising radiation can damage living cells and DNA. In a school laboratory:

- only the teacher handles sealed sources, always with long **tongs**, holding them at arm's length and never pointing them at anyone;
- keep sources in their **lead-lined box** when not in use;
- follow the three rules: **minimise time**, **maximise distance**, use **shielding**;
- never eat or drink in the laboratory, and wash your hands after the practical.

## Check yourself

1. A radioisotope has a half-life of 6 hours. What fraction of it remains after one day?
2. Complete the equation ${}^{210}_{84}\text{Po} \rightarrow \text{Pb} + {}^{4}_{2}\text{He}$ by giving $A$ and $Z$ for lead.
3. Which radiation is the most penetrating, and what is used to absorb it?

*Answers: 1) 24 h is 4 half-lives, so $\left(\tfrac{1}{2}\right)^4 = \tfrac{1}{16}$ · 2) ${}^{206}_{82}\text{Pb}$ ($210 - 4 = 206$, $84 - 2 = 82$) · 3) gamma; it is reduced by thick lead or concrete*
