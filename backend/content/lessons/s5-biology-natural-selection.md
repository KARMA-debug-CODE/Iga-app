---
slug: s5-biology-natural-selection
subject: biology
grade: S5
unit: 2
order: 1
title: Evolution by natural selection
summary: How variation, competition and inheritance change the alleles of a population over generations, with allele frequencies, types of selection, speciation and the evidence for evolution.
minutes: 45
simulations: phet-natural-selection
---
## Darwin's idea

**Evolution** is a change in how common the alleles of a population are, over many generations. An **allele** is one version of a gene. A **population** is a group of one species living in one area and breeding together.

In 1858 Charles Darwin and Alfred Russel Wallace proposed that evolution happens by **natural selection**. The argument has four steps.

1. **Variation.** Individuals differ in size, colour, resistance to disease and more. Much of this variation is caused by alleles, so it can be inherited.
2. **Over-production and competition.** More offspring are born than can survive. They compete for food, space and mates.
3. **Survival of the best adapted.** Individuals with helpful features, called **adaptations**, are more likely to survive and reproduce. This success at leaving offspring is called **fitness**.
4. **Inheritance.** The survivors pass their helpful alleles to their offspring. Over many generations, those alleles become more common.

Anything that affects which individuals survive, such as predators, disease, drought or medicines, is a **selection pressure**.

> Natural selection does not create new features. It only acts on variation that already exists.

## Where does variation come from?

- **Mutation** is a random change in the DNA. It is the original source of all new alleles. Most mutations are harmful or have no effect; a few are useful.
- **Sexual reproduction** makes new combinations of existing alleles. In meiosis, **crossing over** swaps pieces between the two chromosomes of a pair, and **independent assortment** shares each pair out to the gametes separately from the other pairs. Then **random fertilisation** joins any sperm with any egg.

Differences caused by the environment, such as a well-fed calf growing bigger, are not inherited. So they do not lead to evolution.

## The gene pool and allele frequency

The **gene pool** is all the alleles in a population. The **allele frequency** is the fraction of the gene pool made up by one allele of a gene. It is a number between 0 and 1, and the frequencies of all the alleles of one gene add up to 1. Remember that each individual carries two alleles of each gene.

### Worked example 1: field mice in Bugesera

Imagine 500 field mice in a sorghum field. Allele **F** gives brown fur and allele **f** gives white fur. F is dominant, so FF and Ff mice are brown and ff mice are white. There are 200 FF, 200 Ff and 100 ff mice. Find the frequency of each allele.

1. Total alleles: $500 \times 2 = 1000$.
2. F alleles: each FF mouse has 2 and each Ff mouse has 1, so $(200 \times 2) + 200 = 600$.
3. f alleles: each Ff mouse has 1 and each ff mouse has 2, so $200 + (100 \times 2) = 400$.
4. Frequency of F $= \dfrac{600}{1000} = 0.6$. Frequency of f $= \dfrac{400}{1000} = 0.4$.
5. Check: $0.6 + 0.4 = 1$. Correct.

Now suppose owls catch white mice more easily. A few generations later there are 250 FF, 200 Ff and 50 ff mice. The frequency of F is now $\dfrac{500 + 200}{1000} = 0.7$. The allele frequency has changed, so the population has **evolved**. Yet no single mouse changed its own alleles. Populations evolve; individuals do not.

## Natural selection in action

### Worked example 2: how an antibiotic selects resistant bacteria

An infection contains $10^9$ (one thousand million) bacteria. A mutation has made 1,000 of them resistant to an antibiotic. The antibiotic kills 99.99% of the non-resistant bacteria, but none of the resistant ones. How common are resistant bacteria among the survivors?

1. Resistant fraction at the start: $\dfrac{1000}{10^9} = 0.000001$, which is $0.0001\%$.
2. If 99.99% of the non-resistant bacteria die, then $100\% - 99.99\% = 0.01\%$ survive. As a decimal, $0.01\% = 0.0001$.
3. Non-resistant survivors: $0.0001 \times 10^9 = 100\,000$. (There are really $10^9 - 1000$ non-resistant bacteria, but taking away 1,000 makes almost no difference.)
4. Survivors in total: about $100\,000 + 1000 = 101\,000$.
5. Resistant fraction now: $\dfrac{1000}{101\,000} \approx 0.0099$, which is about $1\%$.
6. Compare: $\dfrac{1\%}{0.0001\%} = 10\,000$. Resistant bacteria are now about 10,000 times more common.

Check: $0.0099 \times 101\,000 \approx 1000$ resistant bacteria. Correct.

The antibiotic did not create the resistance. It only killed the other bacteria, so a rare allele became common. The survivors multiply. The infection can come back with far more resistant bacteria, and these can spread to other people.

Every use of an antibiotic is a selection pressure, so take antibiotics only when a health worker prescribes them. Then **finish the course**, even when you feel better. Some bacteria are only **partly resistant**: they survive a few days of the drug but die after a full course. If you stop early, they survive, multiply and pass on their alleles, and the next infection is harder to treat.

**Malaria.** The malaria parasite, *Plasmodium*, has evolved resistance to some drugs. Chloroquine stopped working well in much of Africa, so treatment changed to newer drugs. Researchers have also reported parasites in Rwanda with mutations linked to partial resistance to artemisinin-type drugs, so health workers keep checking how well treatments work.

**The peppered moth.** In industrial England in the 1800s, soot blackened tree trunks. Dark moths were better hidden from birds there, so they became common. After clean-air laws in the 1950s, the trunks became lighter again, and pale moths became common again.

## Run the experiment

In the simulation, choose the brown environment (the equator), add a mate and add the **brown fur** mutation. After a generation or two, add **wolves**. Copy the table into your notebook and fill it in every generation. Then repeat the run in the snowy environment (the arctic).

```sim
phet-natural-selection
```

| Generation | Brown | White | Total | % brown |
|---|---|---|---|---|
| 1 | 2 | 18 | 20 | 10% |
| 2 | 10 | 30 | 40 | 25% |
| 3 | 24 | 26 | 50 | 48% |
| 4 | 40 | 15 | 55 | ? |
| 5 | 52 | 8 | 60 | 87% |

These are example results from one run. Your numbers will be different, but the pattern should be similar.

### Worked example 3: reading the bunny results

1. Percentage brown $= \dfrac{\text{brown}}{\text{total}} \times 100$. Generation 4: $\dfrac{40}{55} \times 100 = 72.7\ldots$, about $73\%$.
2. Trend: brown bunnies rise from 10% to 87% in five generations.
3. **Variation:** the mutation gives two fur colours.
4. **Selection pressure:** wolves catch the bunnies they see easily, and white bunnies stand out on brown ground.
5. **Survival and inheritance:** brown bunnies more often live to breed and pass on the brown allele, so its frequency rises.
6. Prediction: on snow, white bunnies are better hidden, so white fur should increase instead.

Check: $40 + 15 = 55$. Correct.

## Three types of selection

Features such as birth mass or beak size show **continuous variation**: a graph of how many individuals have each value is bell-shaped. Selection can change this curve in three ways. In each sketch, taller marks mean more individuals.

```text
STABILISING (human birth mass)
before:  ..::|||::..
after:     .:|||:.
         low --------> high

DIRECTIONAL (peppered moth colour)
before:  ..::|||::..
after:         ..::|||::..
         pale ---------> dark

DISRUPTIVE (finch beak size)
before:  ..::|||::..
after:   .:|.   .|:.
         small ------> large
```

- **Stabilising selection** removes both extremes, so the curve narrows but its middle stays in place. Babies of very low or very high birth mass have had lower survival than babies of medium mass. It acts when the environment is stable.
- **Directional selection** favours one extreme, so the curve moves. Examples: dark peppered moths, antibiotic resistance, the brown bunnies. It acts when the environment changes.
- **Disruptive selection** favours both extremes. In one African seed-eating finch, small beaks suit soft seeds and large beaks crack hard seeds, while medium beaks do neither job well. The curve can split into two peaks, which can help to form two species.

## Genetic drift and the founder effect

**Genetic drift** is a change in allele frequency caused by **chance**. Imagine 10 beetles, 2 of which carry a rare allele. If a cow happens to step on those 2, the allele is lost, although it was not harmful. Drift matters most in small populations.

In the **founder effect**, a few individuals start a new population. The new gene pool holds only the alleles they happened to carry. For example, in 2015 seven lions from South Africa were brought to Akagera National Park, where lions had disappeared. Every cub born there had parents from those seven, so in 2017 two more males were brought in to add new alleles.

In a **bottleneck**, disease or hunting leaves a few survivors, and much variation is lost.

## How new species form

A **species** is a group of organisms that can interbreed to produce **fertile** offspring (offspring that can breed too). A horse and a donkey can mate, but their mule is almost always sterile, so they are separate species.

New species often form by **geographical isolation**, also called **allopatric speciation**:

1. One population lives in one area and shares one gene pool.
2. A barrier, such as a river changing course or a lava flow, splits it in two.
3. The two groups can no longer meet, so their alleles no longer mix.
4. Each group gets different mutations, faces different selection pressures and drifts in its own way.
5. Over many generations, the two gene pools become very different.
6. Even if the barrier disappears, the groups can no longer produce fertile offspring together. This is **reproductive isolation**: they are now two species.

Darwin's finches on the Galápagos Islands evolved different beak shapes on different islands in this way.

## Evidence for evolution

- **Fossils** in rock layers of different ages show organisms changing gradually, including in-between forms such as early birds with teeth and feathers.
- **Homologous structures.** A human arm, a bat wing, a whale flipper and a dog's front leg share the same bone plan, the **pentadactyl limb**, though they do different jobs. This points to a shared ancestor.
- **DNA comparisons.** The more similar the DNA of two species, the more recently they shared an ancestor. Human DNA is far closer to chimpanzee DNA than to fish DNA.
- **Direct observation.** We have watched bacteria become resistant to antibiotics and mosquitoes become resistant to some insecticides.

## Common mistakes

- **"The bacteria became resistant because they needed to."** Organisms do not choose. The resistance allele already existed; the antibiotic only killed the others.
- **"A giraffe that stretches its neck has long-necked young."** Changes during an organism's life are not inherited.
- **"An individual evolves."** Only populations evolve, as their allele frequencies change.
- **"Fittest means strongest."** Fitness means surviving **and** leaving offspring. A small, well-hidden moth can be fitter than a big one.
- **"Humans evolved from chimpanzees."** Both are living species that share a common ancestor.

## Check yourself

1. Why is variation essential for natural selection?
2. Explain, in four steps, how a population of bacteria becomes resistant to an antibiotic.
3. Is an individual organism able to evolve? Explain.
4. A population of 250 bean plants has 40 RR, 120 Rr and 90 rr. Calculate the frequencies of alleles R and r.
5. Name the type of selection: (a) mosquitoes in an area become more and more resistant to an insecticide; (b) in a forest that does not change, medium-sized lizards survive best.
6. A river divides a population of frogs for thousands of years. Explain how this could lead to two species.

*Answers: 1) Selection acts on differences; if all individuals were identical, none would survive better, so allele frequencies could not change · 2) A mutation gives some bacteria a resistance allele (variation); the antibiotic kills the others (selection pressure); resistant bacteria survive and reproduce; they pass on the allele, so its frequency rises over generations · 3) No; an individual's alleles do not change, and evolution is a change in allele frequency in a population over generations · 4) R $= \frac{(40 \times 2) + 120}{500} = 0.4$ and r $= \frac{120 + (90 \times 2)}{500} = 0.6$ · 5) (a) directional, (b) stabilising · 6) The groups stop interbreeding; different mutations, selection pressures and drift change each gene pool until they cannot produce fertile offspring together (reproductive isolation)*
