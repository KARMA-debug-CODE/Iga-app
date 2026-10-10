---
slug: s6-cs-cpu-scheduling
language: fr
title: "La gestion des processus : l'ordonnancement du processeur avec FCFS, SJF et Round Robin"
summary: Ce qu'est un processus et les états par lesquels il passe, puis comment le système d'exploitation partage le processeur avec FCFS, SJF et Round Robin, à l'aide de diagrammes de Gantt, de temps d'attente et de temps de séjour.
reviewed: false
---
## Programmes et processus

Un **programme** est un fichier d'instructions enregistré sur un disque. Un **processus** est un programme en cours d'exécution : son code, ses données en mémoire, les valeurs des registres du processeur et l'adresse de la prochaine instruction, appelée le **compteur ordinal**. Lancez deux fois le même programme et vous obtenez deux processus : chacun a ses propres données et sa propre position dans le code.

Le système d'exploitation tient un **bloc de contrôle de processus (PCB)** pour chaque processus : son identifiant, son état, son compteur ordinal, ses registres, sa priorité, sa mémoire et ses fichiers ouverts. Pour faire passer le processeur d'un processus à un autre, il enregistre les registres de l'ancien processus dans son PCB et charge ceux du nouveau. Ce **changement de contexte** prend un peu de temps, pendant lequel aucun travail utile n'est fait.

## Les états d'un processus

Un processus passe par cinq **états**.

| État | Signification |
|---|---|
| Nouveau | le processus est en cours de création |
| Prêt | il attend son tour pour le processeur dans la **file des processus prêts** |
| En exécution | le processeur exécute ses instructions |
| En attente (bloqué) | il attend un événement, comme l'appui sur une touche ou la lecture d'un fichier |
| Terminé | il a fini, et le système d'exploitation libère ses ressources |

| Changement | Quand |
|---|---|
| Nouveau → Prêt | le processus est admis en mémoire |
| Prêt → En exécution | l'ordonnanceur le choisit |
| En exécution → Prêt | son temps est écoulé, ou il est interrompu |
| En exécution → En attente | il demande une entrée ou une sortie (E/S), ou attend un événement |
| En attente → Prêt | l'E/S ou l'événement est terminé |
| En exécution → Terminé | il a fini |

Pensez à une banque de Kigali qui n'a qu'un seul guichetier. Le guichetier est le processeur et la file de clients est la file des processus prêts. Un client qui doit aller chercher un document est en attente ; quand il revient, il se remet dans la file. De la même façon, un processus en attente ne repasse jamais directement en exécution.

## L'ordonnancement du processeur

Un cœur de processeur exécute un seul processus à la fois. L'**ordonnanceur**, une partie du système d'exploitation, choisit quel processus prêt s'exécute ensuite, à l'aide d'un **algorithme d'ordonnancement** ; le **répartiteur** (*dispatcher*) lui donne ensuite le processeur.

- Dans l'ordonnancement **non préemptif**, un processus en exécution garde le processeur jusqu'à ce qu'il ait fini ou qu'il doive attendre.
- Dans l'ordonnancement **préemptif**, le système d'exploitation peut arrêter un processus en exécution et le remettre dans la file des processus prêts.

Pour comparer les algorithmes, on utilise ces temps pour chaque processus. On garde les abréviations anglaises, que l'on trouve dans la plupart des livres.

| Terme | Signification |
|---|---|
| **Temps d'arrivée** (AT) | le moment où le processus entre dans la file des processus prêts |
| **Temps d'exécution** (BT, *burst time*) | le temps de processeur dont il a besoin |
| **Temps de fin** (CT) | le moment où il termine |
| **Temps de séjour** (TAT, *turnaround time*) | le temps total entre son arrivée et sa fin |
| **Temps d'attente** (WT) | le temps passé dans la file des processus prêts, sans s'exécuter |

$$
\begin{gathered}
\text{TAT} = \text{CT} - \text{AT} \\
\text{WT} = \text{TAT} - \text{BT}
\end{gathered}
$$

Une moyenne est la somme divisée par le nombre de processus ; un bon algorithme donne de petites moyennes. Un **diagramme de Gantt** est une barre qui montre quel processus utilise le processeur et à quel moment, avec les temps sous les bords des cases. Ici, les temps sont en millisecondes (ms).

## Premier arrivé, premier servi (FCFS)

**FCFS** (*First Come, First Served*) exécute les processus dans leur ordre d'arrivée, comme des passagers qui font la queue pour un bus à Nyabugogo. Il est non préemptif et facile à réaliser, mais un seul long processus peut faire attendre beaucoup de processus courts derrière lui. C'est ce qu'on appelle l'**effet de convoi**.

### Exemple corrigé 1 : l'effet de convoi

Trois processus arrivent au temps 0 dans l'ordre P1, P2, P3, avec des temps d'exécution de 24, 3 et 3 ms. Trouvez le temps d'attente moyen avec FCFS. Trouvez-le ensuite pour l'ordre P2, P3, P1.

```text
| P1 | P2 | P3 |
0    24   27   30
```

- Les trois arrivent à 0 : le temps d'attente de chacun est donc son heure de début, soit 0, 24 et 27 ms.
- WT moyen $= (0 + 24 + 27) \div 3 = 51 \div 3 = 17$ ms.
- Dans l'ordre P2, P3, P1, le diagramme donne P2 de 0 à 3, P3 de 3 à 6 et P1 de 6 à 30 : les temps d'attente sont donc 0, 3 et 6 ms.
- WT moyen $= (0 + 3 + 6) \div 3 = 3$ ms. Le même travail, mais 3 ms au lieu de 17 ms : les tâches courtes ne devraient pas faire la queue derrière les longues.

Les trois exemples suivants utilisent ces quatre processus, pour que vous puissiez comparer les algorithmes.

| Processus | Arrivée (ms) | Exécution (ms) |
|---|---|---|
| P1 | 0 | 7 |
| P2 | 2 | 4 |
| P3 | 4 | 1 |
| P4 | 5 | 4 |

### Exemple corrigé 2 : FCFS avec des temps d'arrivée

- Les processus s'exécutent dans leur ordre d'arrivée : P1, P2, P3, puis P4.

```text
| P1 | P2 | P3 | P4 |
0    7    11   12   16
```

| Processus | AT | BT | CT | TAT | WT |
|---|---|---|---|---|---|
| P1 | 0 | 7 | 7 | 7 | 0 |
| P2 | 2 | 4 | 11 | 9 | 5 |
| P3 | 4 | 1 | 12 | 8 | 7 |
| P4 | 5 | 4 | 16 | 11 | 7 |

- Pour P2 : TAT $= 11 - 2 = 9$ et WT $= 9 - 4 = 5$. Les autres lignes se calculent de la même façon.
- TAT moyen $= (7 + 9 + 8 + 11) \div 4 = 35 \div 4 = 8{,}75$ ms.
- WT moyen $= (0 + 5 + 7 + 7) \div 4 = 19 \div 4 = 4{,}75$ ms.

## Le plus court d'abord (SJF)

**SJF** (*Shortest Job First*) choisit, parmi les processus **déjà arrivés**, celui qui a le plus petit temps d'exécution ; à temps égaux, le premier arrivé passe d'abord. Dans la version non préemptive, un processus en exécution n'est jamais arrêté. Quand tous les processus attendent en même temps, SJF donne le plus petit temps d'attente moyen possible. Mais le système d'exploitation doit deviner les temps d'exécution, et un long processus peut attendre indéfiniment si des processus courts continuent d'arriver. C'est ce qu'on appelle la **famine**.

### Exemple corrigé 3 : SJF (non préemptif)

- Au temps 0, seul P1 est arrivé : il s'exécute donc de 0 à 7, même si des tâches plus courtes arrivent entre-temps.
- Au temps 7, P2 (4 ms), P3 (1 ms) et P4 (4 ms) attendent. P3 est le plus court : il s'exécute de 7 à 8.
- P2 et P4 ont tous deux besoin de 4 ms, et P2 est arrivé le premier : P2 s'exécute de 8 à 12, puis P4 de 12 à 16.

```text
| P1 | P3 | P2 | P4 |
0    7    8    12   16
```

| Processus | AT | BT | CT | TAT | WT |
|---|---|---|---|---|---|
| P1 | 0 | 7 | 7 | 7 | 0 |
| P2 | 2 | 4 | 12 | 10 | 6 |
| P3 | 4 | 1 | 8 | 4 | 3 |
| P4 | 5 | 4 | 16 | 11 | 7 |

- TAT moyen $= 32 \div 4 = 8$ ms.
- WT moyen $= 16 \div 4 = 4$ ms.

## Le tourniquet (Round Robin, RR)

**Round Robin**, ou tourniquet, est préemptif. Chaque processus s'exécute pendant au plus un **quantum de temps** (ou tranche de temps), par exemple 2 ms. S'il n'a pas fini, il retourne au bout de la file des processus prêts et le processus suivant s'exécute ; s'il finit plus tôt, le suivant démarre aussitôt. Round Robin est équitable : chaque processus obtient souvent le processeur. Dans cette leçon, un processus qui arrive juste au moment où un quantum se termine entre dans la file en premier.

### Exemple corrigé 4 : Round Robin avec un quantum de 2 ms

Suivez la file des processus prêts après chaque tranche (sa tête est à gauche).

| Temps | S'exécute | Ce qui se passe | File des prêts |
|---|---|---|---|
| 0–2 | P1 | P2 arrive à 2 ; il reste 5 ms à P1 | P2, P1 |
| 2–4 | P2 | P3 arrive à 4 ; il reste 2 ms à P2 | P1, P3, P2 |
| 4–6 | P1 | P4 arrive à 5 ; il reste 3 ms à P1 | P3, P2, P4, P1 |
| 6–7 | P3 | P3 finit au bout de 1 ms | P2, P4, P1 |
| 7–9 | P2 | P2 finit | P4, P1 |
| 9–11 | P4 | il reste 2 ms à P4 | P1, P4 |
| 11–13 | P1 | il reste 1 ms à P1 | P4, P1 |
| 13–15 | P4 | P4 finit | P1 |
| 15–16 | P1 | P1 finit | vide |

```text
| P1 | P2 | P1 | P3 | P2 |
0    2    4    6    7    9
| P4 | P1 | P4 | P1 |
9    11   13   15   16
```

| Processus | AT | BT | CT | TAT | WT |
|---|---|---|---|---|---|
| P1 | 0 | 7 | 16 | 16 | 9 |
| P2 | 2 | 4 | 9 | 7 | 3 |
| P3 | 4 | 1 | 7 | 3 | 2 |
| P4 | 5 | 4 | 15 | 10 | 6 |

- TAT moyen $= 36 \div 4 = 9$ ms.
- WT moyen $= 20 \div 4 = 5$ ms.

Le quantum compte. S'il est plus long que tous les temps d'exécution, aucun processus n'est jamais arrêté et Round Robin devient FCFS. S'il est très court, le processeur passe une grande partie de son temps en changements de contexte.

### Exemple corrigé 5 : quel algorithme est le meilleur ?

Comparez les résultats. Regardez aussi le **temps de réponse** : le temps entre l'arrivée d'un processus et le moment où il obtient le processeur pour la première fois. Avec Round Robin, les temps de réponse sont 0, 0, 2 et 4 ms. Avec FCFS et SJF, qui n'arrêtent jamais un processus, ils sont égaux aux temps d'attente. Voici les moyennes (RR utilise un quantum de 2 ms).

| Moyenne (ms) | FCFS | SJF | RR |
|---|---|---|---|
| TAT | 8,75 | 8 | 9 |
| WT | 4,75 | 4 | 5 |
| Temps de réponse | 4,75 | 4 | 1,5 |

- Ici, SJF donne les plus petits temps d'attente et de séjour moyens.
- Round Robin donne les plus grandes moyennes, mais le plus petit temps de réponse : chaque processus démarre au plus 4 ms après son arrivée. Pour quelqu'un qui tape au clavier, une réponse rapide compte davantage.
- FCFS est le plus simple, mais P3, qui n'a besoin que de 1 ms, attend 7 ms.

Il n'existe pas un seul meilleur algorithme : chaque système d'exploitation choisit ce qui convient à ses objectifs, et les vrais systèmes combinent souvent plusieurs idées.

## Erreurs fréquentes

- **Prendre CT pour le TAT.** TAT = CT − AT ; ils ne sont égaux que lorsque le processus arrive au temps 0.
- **Écrire WT = CT − BT.** Cette formule oublie le temps d'arrivée. Utilisez WT = TAT − BT.
- **Exécuter un processus avant son arrivée.** Choisissez seulement parmi les processus déjà arrivés. Si aucun n'est arrivé, le processeur est **inactif** : montrez un bloc d'inactivité dans le diagramme de Gantt.
- **Arrêter le processus en exécution en SJF non préemptif.** Une tâche plus courte qui arrive attend que le processus en exécution ait fini. (Le SJF préemptif, *Shortest Remaining Time First*, est un autre algorithme.)
- **Donner un quantum entier à un processus qui a besoin de moins.** Un processus à qui il reste 1 ms ne s'exécute que pendant 1 ms.
- **Perdre le fil de la file du Round Robin.** Écrivez la file après chaque tranche, comme dans l'exemple corrigé 4.
- **Diviser par le mauvais nombre.** Divisez par le nombre de processus, et non par le temps total.

## Testez-vous

Les questions 2 à 4 utilisent trois processus (temps en ms) : A arrive à 0 avec un temps d'exécution de 5, B à 1 avec un temps d'exécution de 3, et C à 2 avec un temps d'exécution de 1.

1. Nommez les cinq états d'un processus. Dans quel état est un processus pendant qu'il attend que l'utilisateur appuie sur une touche ?
2. Dessinez le diagramme de Gantt de FCFS et trouvez le temps d'attente moyen.
3. Dessinez le diagramme de Gantt de SJF (non préemptif) et trouvez le temps de séjour moyen.
4. Dessinez le diagramme de Gantt de Round Robin avec un quantum de 2 ms et trouvez le temps d'attente moyen.
5. Avec FCFS, P1 arrive à 0 avec un temps d'exécution de 3 et P2 arrive à 5 avec un temps d'exécution de 2. Que fait le processeur de 3 à 5 ? Quel est le temps d'attente de P2 ?
6. Que devient Round Robin quand le quantum est plus long que tous les temps d'exécution ?
7. Quelle est la différence entre l'ordonnancement préemptif et l'ordonnancement non préemptif ?

*Réponses : 1) nouveau, prêt, en exécution, en attente (bloqué) et terminé ; il est en attente · 2) A 0–5, B 5–8, C 8–9 ; WT = 0, 4 et 6, moyenne $\frac{10}{3} \approx 3{,}33$ ms · 3) A 0–5, C 5–6, B 6–9 ; TAT = 5, 8 et 4, moyenne $\frac{17}{3} \approx 5{,}67$ ms · 4) A 0–2, B 2–4, C 4–5, A 5–7, B 7–8, A 8–9 ; WT = 4, 4 et 2, moyenne $\frac{10}{3} \approx 3{,}33$ ms · 5) le processeur est inactif ; P2 démarre dès son arrivée, il attend donc 0 ms · 6) FCFS · 7) un ordonnanceur préemptif peut arrêter un processus en exécution et le remettre dans la file des processus prêts ; un ordonnanceur non préemptif le laisse s'exécuter jusqu'à ce qu'il ait fini ou qu'il doive attendre*
