---
slug: s6-biology-populations-ecology
subject: biology
grade: S6
unit: 2
order: 1
title: Populations and ecology
summary: Estimating population size, modelling exponential and logistic growth, and explaining how density-dependent and density-independent factors regulate populations.
minutes: 40
simulations: phet-natural-selection
---
## Key terms

- **Population**: all the organisms of one species living in the same area at the same time, able to interbreed.
- **Community**: all the populations of different species living and interacting in an area.
- **Ecosystem**: a community together with its abiotic (non-living) environment, such as soil, water and climate.
- **Habitat**: the place where an organism lives.
- **Niche**: the role of a species in its ecosystem: what it eats, what eats it, where and when it is active.
- **Population density**: number of individuals per unit area (or volume), e.g. plants m⁻².

The size of a population changes as

$$\Delta N = (\text{births} + \text{immigration}) - (\text{deaths} + \text{emigration})$$

## Estimating population size

We can rarely count every individual, so we **sample**.

### Quadrats (plants and slow-moving animals)

Place quadrats at **random** positions (using random-number coordinates, to avoid bias), count the individuals in each, and scale up:

$$\text{estimated population} = \text{mean number per quadrat} \times \frac{\text{total area}}{\text{area of one quadrat}}$$

#### Worked example 1

A student estimates the number of black-jack weeds (*Bidens pilosa*) in a 50 m × 40 m pasture in Nyagatare. Ten 1 m² quadrats give:

3, 5, 0, 2, 4, 6, 1, 3, 2, 4

1. Total: $3 + 5 + 0 + 2 + 4 + 6 + 1 + 3 + 2 + 4 = 30$
2. Mean per quadrat: $\dfrac{30}{10} = 3.0$, so the density is 3.0 plants m⁻²
3. Area of pasture: $50 \times 40 = 2000\ \text{m}^2$
4. Estimate: $3.0 \times \dfrac{2000}{1} = 6000$ plants

### Capture–mark–release–recapture (mobile animals)

Catch a sample, mark each animal harmlessly, release them, and catch a second sample later. The **Lincoln index** gives

$$N = \frac{n_1 \times n_2}{m_2}$$

where $n_1$ = number marked in the first sample, $n_2$ = number caught in the second sample, and $m_2$ = number of marked animals in the second sample.

#### Worked example 2

A fish-farming cooperative in Rwamagana wants to know how many tilapia are in its pond. They net and fin-clip 120 fish, then release them. A week later they net 150 fish, of which 24 are marked.

$$N = \frac{120 \times 150}{24} = \frac{18\,000}{24} = 750 \text{ tilapia}$$

The method assumes that:

- marked animals mix randomly with the rest of the population
- marks do not fall off or make animals easier for predators to catch
- there are no significant births, deaths, immigration or emigration between samples
- marked and unmarked animals are equally likely to be caught

## Population growth

### Exponential growth

With unlimited food and space and no predators or disease, a population grows **exponentially**: the larger it is, the faster it grows.

$$\frac{dN}{dt} = rN$$

where $r$ is the intrinsic rate of natural increase. A graph of $N$ against time is **J-shaped**.

Bacteria that divide every 20 minutes show this. Starting from 500 cells, 2 hours is $\frac{120}{20} = 6$ generations, so

$$N = 500 \times 2^6 = 500 \times 64 = 32\,000 \text{ cells}$$

Invasive water hyacinth, which can spread rapidly across lakes in the Eastern Province, and pests such as fall armyworm in maize fields also grow almost exponentially when first established.

### Logistic (sigmoid) growth

In real environments resources run short. Growth slows and the population levels off at the **carrying capacity**, $K$: the maximum population an environment can support in the long term.

$$\frac{dN}{dt} = rN\left(\frac{K - N}{K}\right)$$

| Phase | What happens | Why |
|---|---|---|
| Lag | Slow growth | Few breeding individuals; organisms adjusting to the habitat |
| Exponential (log) | Rapid growth | Resources plentiful; births far exceed deaths |
| Deceleration | Growth slows | Competition for food and space increases; more predation and disease |
| Stationary | $N$ fluctuates around $K$ | Births roughly equal deaths |

In a closed flask of yeast, a **decline phase** follows, as sugar runs out and toxic ethanol builds up.

#### Worked example 3

A population of antelope has $r = 0.4$ per year and a carrying capacity $K = 1000$. Find the growth rate when $N = 200$.

$$\frac{dN}{dt} = 0.4 \times 200 \times \frac{1000 - 200}{1000} = 80 \times 0.8 = 64 \text{ antelope per year}$$

When $N = 500 = \frac{K}{2}$: $0.4 \times 500 \times 0.5 = 100$ per year, the fastest growth. When $N = K = 1000$, the bracket is zero, so growth stops.

## What limits populations?

| Density-dependent factors | Density-independent factors |
|---|---|
| Effect increases as the population becomes more crowded | Effect is the same whatever the density |
| Competition for food, water, space and mates | Drought, floods and landslides |
| Predation | Fire |
| Disease and parasites (spread faster in crowds) | Frost, extreme heat |
| Build-up of toxic waste | Volcanic eruptions |

Density-dependent factors **regulate** a population around $K$ by negative feedback.

**Competition** may be **intraspecific** (within one species, the most intense because individuals share the same niche) or **interspecific** (between species). If two species occupy exactly the same niche, one eventually excludes the other: the **competitive exclusion principle**.

### Predator–prey cycles

When prey are plentiful, predators survive and breed well, so predator numbers rise. More predators eat more prey, so prey numbers fall. With less food, predators then decline, and the prey recover. Predator peaks usually **lag behind** prey peaks. In Akagera National Park, where lions were reintroduced in 2015, ecologists monitor how predators and herbivores such as impala affect each other.

## Conservation in Rwanda

Protection, anti-poaching patrols and community tourism helped the world's mountain gorilla population, including the groups in Volcanoes National Park, grow to just over 1,000 by 2018. On Lake Kivu, *sambaza* fish, introduced from Lake Tanganyika in the late 1950s, support many fishing families. Rules on mesh size and fishing seasons aim to keep the catch below the rate at which the population can replace itself.

## Explore

Run the simulation with limited food and then add wolves. Sketch the population graph. Can you identify exponential growth, a levelling off and predator effects?

```sim
phet-natural-selection
```

## Safety in fieldwork

- Work in groups, tell your teacher where you are going and stay away from deep water at lake shores.
- Wear closed shoes, long trousers and a hat; watch for snakes, stinging nettles and biting ants.
- Handle captured animals gently and briefly, and use harmless marks; return them where they were caught.
- Wash your hands after handling soil, water samples or animals.

## Check yourself

1. 60 beetles are marked and released. In a second sample of 50 beetles, 12 are marked. Estimate the population.
2. Give one density-dependent and one density-independent factor that could affect sambaza in Lake Kivu.
3. For a population with $r = 0.2$ per year, $K = 800$ and $N = 400$, calculate $\frac{dN}{dt}$.

*Answers: 1) $N = \frac{60 \times 50}{12} = 250$ beetles · 2) Density-dependent: competition for plankton, predation, disease; density-independent: a sudden change in water temperature or a pollution event · 3) $0.2 \times 400 \times \frac{800 - 400}{800} = 80 \times 0.5 = 40$ per year*
