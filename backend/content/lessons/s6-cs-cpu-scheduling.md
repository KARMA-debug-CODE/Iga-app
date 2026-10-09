---
slug: s6-cs-cpu-scheduling
subject: computer-science
grade: S6
unit: 7
order: 1
title: "Process management: CPU scheduling with FCFS, SJF and Round Robin"
summary: What a process is and the states it moves through, then how the operating system shares the CPU using FCFS, SJF and Round Robin, with Gantt charts, waiting times and turnaround times.
minutes: 50
simulations:
---
## Programs and processes

A **program** is a file of instructions stored on a disk. A **process** is a program in execution: its code, its data in memory, the values in the CPU registers and the address of the next instruction, called the **program counter**. Run the same program twice and you get two processes: each has its own data and its own place in the code.

The operating system keeps a **process control block (PCB)** for every process: its ID, state, program counter, registers, priority, memory and open files. To move the CPU from one process to another, it saves the registers of the old process in its PCB and loads those of the new one. This **context switch** takes a little time, during which no useful work is done.

## Process states

A process moves through five **states**.

| State | Meaning |
|---|---|
| New | the process is being created |
| Ready | it waits in the **ready queue** for its turn on the CPU |
| Running | the CPU is carrying out its instructions |
| Waiting (blocked) | it waits for an event, such as a key press or a file being read |
| Terminated | it has finished, and the operating system frees its resources |

| Change of state | When it happens |
|---|---|
| New → Ready | the process is admitted into memory |
| Ready → Running | the scheduler picks it |
| Running → Ready | its time is up, or it is interrupted |
| Running → Waiting | it asks for input or output (I/O), or waits for an event |
| Waiting → Ready | the I/O or the event is complete |
| Running → Terminated | it finishes |

Think of a bank in Kigali with one teller. The teller is the CPU and the queue is the ready queue. A customer who must go and fetch a document is waiting; when they come back, they join the queue again. In the same way, a waiting process never goes straight back to Running.

## CPU scheduling

A CPU core runs one process at a time. The **scheduler**, part of the operating system, chooses which ready process runs next, using a **scheduling algorithm**; the **dispatcher** then gives it the CPU.

- In **non-preemptive** scheduling, a running process keeps the CPU until it finishes or has to wait.
- In **preemptive** scheduling, the operating system can stop a running process and put it back in the ready queue.

To compare algorithms, we use these times for each process.

| Term | Meaning |
|---|---|
| **Arrival time** (AT) | when the process enters the ready queue |
| **Burst time** (BT) | how much CPU time it needs |
| **Completion time** (CT) | when it finishes |
| **Turnaround time** (TAT) | the total time from arrival to completion |
| **Waiting time** (WT) | the time spent in the ready queue, not running |

$$\text{TAT} = \text{CT} - \text{AT} \qquad \text{WT} = \text{TAT} - \text{BT}$$

An average is the sum divided by the number of processes; a good algorithm gives small averages. A **Gantt chart** is a bar showing which process uses the CPU and when, with the times under the edges of the boxes. Times here are in milliseconds (ms).

## First Come, First Served (FCFS)

**FCFS** runs the processes in their order of arrival, like passengers queueing for a bus at Nyabugogo. It is non-preemptive and easy to build, but one long process can make many short ones wait behind it. This is called the **convoy effect**.

### Worked example 1: the convoy effect

Three processes arrive at time 0 in the order P1, P2, P3, with burst times 24, 3 and 3 ms. Find the average waiting time with FCFS. Then find it for the order P2, P3, P1.

```text
| P1 | P2 | P3 |
0    24   27   30
```

- All three arrive at 0, so each waiting time is the start time: 0, 24 and 27 ms.
- Average WT $= \dfrac{0 + 24 + 27}{3} = \dfrac{51}{3} = 17$ ms.
- In the order P2, P3, P1, the chart is P2 0–3, P3 3–6 and P1 6–30, so the waiting times are 0, 3 and 6 ms.
- Average WT $= \dfrac{0 + 3 + 6}{3} = 3$ ms. Same work, but 3 ms instead of 17 ms: short jobs should not queue behind long ones.

The next three examples use these four processes, so that you can compare the algorithms.

| Process | Arrival time (ms) | Burst time (ms) |
|---|---|---|
| P1 | 0 | 7 |
| P2 | 2 | 4 |
| P3 | 4 | 1 |
| P4 | 5 | 4 |

### Worked example 2: FCFS with arrival times

- The processes run in order of arrival: P1, P2, P3, then P4.

```text
| P1 | P2 | P3 | P4 |
0    7    11   12   16
```

| Process | AT | BT | CT | TAT | WT |
|---|---|---|---|---|---|
| P1 | 0 | 7 | 7 | 7 | 0 |
| P2 | 2 | 4 | 11 | 9 | 5 |
| P3 | 4 | 1 | 12 | 8 | 7 |
| P4 | 5 | 4 | 16 | 11 | 7 |

- For P2: TAT $= 11 - 2 = 9$ and WT $= 9 - 4 = 5$. The other rows work the same way.
- Average TAT $= \dfrac{7 + 9 + 8 + 11}{4} = \dfrac{35}{4} = 8.75$ ms. Average WT $= \dfrac{0 + 5 + 7 + 7}{4} = \dfrac{19}{4} = 4.75$ ms.

## Shortest Job First (SJF)

**SJF** chooses, among the processes that have **already arrived**, the one with the shortest burst time; for equal bursts, the earlier arrival goes first. In the non-preemptive version, a running process is never stopped. When all the processes wait at the same time, SJF gives the smallest possible average waiting time. But the operating system must guess burst times, and a long process can wait forever if short ones keep arriving. This is called **starvation**.

### Worked example 3: SJF (non-preemptive)

- At time 0 only P1 has arrived, so it runs from 0 to 7, even though shorter jobs arrive meanwhile.
- At time 7, P2 (4 ms), P3 (1 ms) and P4 (4 ms) are waiting. P3 is the shortest: it runs from 7 to 8.
- P2 and P4 both need 4 ms, and P2 arrived first: P2 runs from 8 to 12, then P4 from 12 to 16.

```text
| P1 | P3 | P2 | P4 |
0    7    8    12   16
```

| Process | AT | BT | CT | TAT | WT |
|---|---|---|---|---|---|
| P1 | 0 | 7 | 7 | 7 | 0 |
| P2 | 2 | 4 | 12 | 10 | 6 |
| P3 | 4 | 1 | 8 | 4 | 3 |
| P4 | 5 | 4 | 16 | 11 | 7 |

- Average TAT $= \dfrac{32}{4} = 8$ ms. Average WT $= \dfrac{16}{4} = 4$ ms.

## Round Robin (RR)

**Round Robin** is preemptive. Each process runs for at most one **time quantum** (or time slice), for example 2 ms. If it has not finished, it goes to the back of the ready queue and the next process runs; if it finishes early, the next one starts at once. Round Robin is fair: every process gets the CPU often. In this lesson, a process that arrives just as a quantum ends joins the queue first.

### Worked example 4: Round Robin with a quantum of 2 ms

Follow the ready queue after each slice (its front is on the left).

| Time | Runs | What happens | Ready queue |
|---|---|---|---|
| 0–2 | P1 | P2 arrives at 2; P1 has 5 ms left | P2, P1 |
| 2–4 | P2 | P3 arrives at 4; P2 has 2 ms left | P1, P3, P2 |
| 4–6 | P1 | P4 arrives at 5; P1 has 3 ms left | P3, P2, P4, P1 |
| 6–7 | P3 | P3 finishes after 1 ms | P2, P4, P1 |
| 7–9 | P2 | P2 finishes | P4, P1 |
| 9–11 | P4 | P4 has 2 ms left | P1, P4 |
| 11–13 | P1 | P1 has 1 ms left | P4, P1 |
| 13–15 | P4 | P4 finishes | P1 |
| 15–16 | P1 | P1 finishes | empty |

```text
| P1 | P2 | P1 | P3 | P2 |
0    2    4    6    7    9
| P4 | P1 | P4 | P1 |
9    11   13   15   16
```

| Process | AT | BT | CT | TAT | WT |
|---|---|---|---|---|---|
| P1 | 0 | 7 | 16 | 16 | 9 |
| P2 | 2 | 4 | 9 | 7 | 3 |
| P3 | 4 | 1 | 7 | 3 | 2 |
| P4 | 5 | 4 | 15 | 10 | 6 |

- Average TAT $= \dfrac{36}{4} = 9$ ms. Average WT $= \dfrac{20}{4} = 5$ ms.

The quantum matters. If it is longer than every burst, no process is ever stopped and Round Robin becomes FCFS. If it is very short, the CPU spends much of its time on context switches.

### Worked example 5: which algorithm is best?

Compare the results. Also look at the **response time**: the time from arrival until a process first gets the CPU. With Round Robin, the response times are 0, 0, 2 and 4 ms. With FCFS and SJF, which never stop a process, they equal the waiting times.

| Algorithm | Average TAT (ms) | Average WT (ms) | Average response time (ms) |
|---|---|---|---|
| FCFS | 8.75 | 4.75 | 4.75 |
| SJF | 8 | 4 | 4 |
| RR, quantum 2 ms | 9 | 5 | 1.5 |

- SJF has the smallest average waiting and turnaround times here.
- Round Robin has the largest averages, but the smallest response time: every process starts within 4 ms of arriving. For someone typing, a quick response matters more.
- FCFS is the simplest, but P3, which needs only 1 ms, waits 7 ms.

There is no single best algorithm: each operating system chooses what fits its goals, and real systems often combine several ideas.

## Common mistakes

- **Using CT as the TAT.** TAT = CT − AT; they are equal only when the process arrives at time 0.
- **Writing WT = CT − BT.** This forgets the arrival time. Use WT = TAT − BT.
- **Running a process before it arrives.** Choose only among processes that have arrived. If none has arrived, the CPU is **idle**: show an idle block in the Gantt chart.
- **Stopping the running process in non-preemptive SJF.** A shorter job that arrives waits until the running process finishes. (Preemptive SJF, Shortest Remaining Time First, is a different algorithm.)
- **Giving a full quantum to a process that needs less.** A process with 1 ms left runs for 1 ms only.
- **Losing track of the Round Robin queue.** Write the queue after every slice, as in Worked example 4.
- **Dividing by the wrong number.** Divide by the number of processes, not by the total time.

## Check yourself

Questions 2 to 4 use three processes (times in ms): A arrives at 0 with a burst of 5, B at 1 with a burst of 3, and C at 2 with a burst of 1.

1. Name the five process states. Which state is a process in while it waits for the user to press a key?
2. Draw the FCFS Gantt chart and find the average waiting time.
3. Draw the SJF (non-preemptive) Gantt chart and find the average turnaround time.
4. Draw the Round Robin Gantt chart with a quantum of 2 ms and find the average waiting time.
5. With FCFS, P1 arrives at 0 with a burst of 3 and P2 arrives at 5 with a burst of 2. What does the CPU do from 3 to 5? What is P2's waiting time?
6. What does Round Robin become when the quantum is longer than every burst time?
7. What is the difference between preemptive and non-preemptive scheduling?

*Answers: 1) new, ready, running, waiting (blocked) and terminated; it is waiting · 2) A 0–5, B 5–8, C 8–9; WT = 0, 4 and 6, average $\frac{10}{3} \approx 3.33$ ms · 3) A 0–5, C 5–6, B 6–9; TAT = 5, 8 and 4, average $\frac{17}{3} \approx 5.67$ ms · 4) A 0–2, B 2–4, C 4–5, A 5–7, B 7–8, A 8–9; WT = 4, 4 and 2, average $\frac{10}{3} \approx 3.33$ ms · 5) the CPU is idle; P2 starts as soon as it arrives, so it waits 0 ms · 6) FCFS · 7) a preemptive scheduler can stop a running process and put it back in the ready queue; a non-preemptive one lets it run until it finishes or waits*
