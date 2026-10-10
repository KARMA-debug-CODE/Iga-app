---
slug: s4-cs-number-systems
subject: computer-science
grade: S4
unit: 5
order: 1
title: "Number systems: binary, octal, decimal and hexadecimal"
summary: Why computers use binary, how place value works in bases 2, 8, 10 and 16, and how to convert between them by repeated division and by grouping bits.
minutes: 45
simulations:
access: free
---
## Why computers use binary

A computer is built from millions of tiny electronic switches called **transistors**. Each switch is either off or on, so it has only two states. We write these two states as 0 and 1.

A single 0 or 1 is a **bit**, short for *binary digit*. A group of 8 bits is a **byte**. Every number, letter, photo, song and MoMo message on a phone is stored as a long row of bits.

Why only two states? They are easy to tell apart, even when the voltage is a little weak or noisy, so the computer rarely makes a mistake. Two-state switches are also small, cheap and fast. A machine with ten voltage levels, one for each decimal digit, would be much harder to build reliably.

## Number systems and place value

A **number system** is a way of writing numbers with a fixed set of digits. The number of digits it uses is its **base** (or radix).

| Number system | Base | Digits |
|---|---|---|
| Binary | 2 | 0 and 1 |
| Octal | 8 | 0 to 7 |
| Decimal | 10 | 0 to 9 |
| Hexadecimal | 16 | 0 to 9, then A to F |

In hexadecimal (hex for short), the letters stand for the values ten to fifteen: A = 10, B = 11, C = 12, D = 13, E = 14 and F = 15.

The same digits can mean different numbers in different bases, so we write the base as a small number after the digits: $11_{10}$ is eleven, but $11_2$ is three, $11_8$ is nine and $11_{16}$ is seventeen.

Every number system uses **place value**. In decimal, $3\,054 = 3 \times 1000 + 0 \times 100 + 5 \times 10 + 4 \times 1$. The place values are powers of 10: $10^0 = 1$, $10^1 = 10$, $10^2 = 100$, and so on. In base $b$, the place values are powers of $b$, starting with $b^0 = 1$ on the right.

Here are the place values, from right to left:

- base 2: 1, 2, 4, 8, 16, 32, 64, 128, …
- base 8: 1, 8, 64, 512, 4096, …
- base 16: 1, 16, 256, 4096, …

## Converting to decimal: use the place values

Write the place values above the digits, multiply each digit by its place value, and add.

### Worked example 1: to decimal

Convert (a) $101101_2$, (b) $157_8$ and (c) $\mathrm{1A3}_{16}$ to decimal.

(a) Write the binary place values (top row) above the bits (bottom row):

| 32 | 16 | 8 | 4 | 2 | 1 |
|---|---|---|---|---|---|
| 1 | 0 | 1 | 1 | 0 | 1 |

- A bit is 0 or 1, so just add the place values above the 1s: $32 + 8 + 4 + 1 = 45$.
- So $101101_2 = 45_{10}$.

(b) The octal place values are 64, 8 and 1.

- $1 \times 64 + 5 \times 8 + 7 \times 1 = 64 + 40 + 7 = 111$, so $157_8 = 111_{10}$.

(c) The hexadecimal place values are 256, 16 and 1, and A means 10.

- $1 \times 256 + 10 \times 16 + 3 \times 1 = 256 + 160 + 3 = 419$, so $\mathrm{1A3}_{16} = 419_{10}$.

## Converting from decimal: repeated division

To change a decimal number to base $b$, divide it by $b$ again and again, and write down each remainder, until the quotient is 0. The remainders, read **from the bottom up**, are the digits of the answer. The first remainder is the rightmost digit.

### Worked example 2: decimal to binary

Convert 156 to binary.

| Division | Quotient | Remainder |
|---|---|---|
| 156 ÷ 2 | 78 | 0 |
| 78 ÷ 2 | 39 | 0 |
| 39 ÷ 2 | 19 | 1 |
| 19 ÷ 2 | 9 | 1 |
| 9 ÷ 2 | 4 | 1 |
| 4 ÷ 2 | 2 | 0 |
| 2 ÷ 2 | 1 | 0 |
| 1 ÷ 2 | 0 | 1 |

- Read the remainders from the bottom up: $156 = 10011100_2$.
- Check: $128 + 16 + 8 + 4 = 156$. Correct.

### Worked example 3: decimal to hexadecimal and octal

Mount Karisimbi is 4,507 m high. Write 4,507 in hexadecimal and in octal.

| Division | Quotient | Remainder |
|---|---|---|
| 4507 ÷ 16 | 281 | 11 = B |
| 281 ÷ 16 | 17 | 9 |
| 17 ÷ 16 | 1 | 1 |
| 1 ÷ 16 | 0 | 1 |

- From the bottom up: $4507 = \mathrm{119B}_{16}$. A remainder of 11 is the single digit B.
- Check: $1 \times 4096 + 1 \times 256 + 9 \times 16 + 11 = 4096 + 256 + 144 + 11 = 4507$. Correct.
- For octal, divide by 8: $4507 \div 8 = 563$ remainder 3, $563 \div 8 = 70$ r 3, $70 \div 8 = 8$ r 6, $8 \div 8 = 1$ r 0, and $1 \div 8 = 0$ r 1.
- From the bottom up: $4507 = 10633_8$.
- Check: $1 \times 4096 + 0 \times 512 + 6 \times 64 + 3 \times 8 + 3 = 4096 + 384 + 24 + 3 = 4507$. Correct.

## Counting in binary

Counting in binary works like the distance counter on a moto. When a digit passes its biggest value, it goes back to 0 and carries 1 to the left. In binary the biggest digit is 1, so $1 + 1 = 10_2$, and $111_2 + 1 = 1000_2$.

| Decimal | Binary | Octal | Hex |
|---|---|---|---|
| 0 | 0000 | 0 | 0 |
| 1 | 0001 | 1 | 1 |
| 2 | 0010 | 2 | 2 |
| 3 | 0011 | 3 | 3 |
| 4 | 0100 | 4 | 4 |
| 5 | 0101 | 5 | 5 |
| 6 | 0110 | 6 | 6 |
| 7 | 0111 | 7 | 7 |
| 8 | 1000 | 10 | 8 |
| 9 | 1001 | 11 | 9 |
| 10 | 1010 | 12 | A |
| 11 | 1011 | 13 | B |
| 12 | 1100 | 14 | C |
| 13 | 1101 | 15 | D |
| 14 | 1110 | 16 | E |
| 15 | 1111 | 17 | F |

With $n$ bits you can write $2^n$ different numbers, from 0 to $2^n - 1$. Four bits give 16 numbers, 0 to 15. One byte (8 bits) gives $2^8 = 256$ numbers, 0 to 255, and $255 = 11111111_2 = \mathrm{FF}_{16}$.

### Worked example 4: how many bits?

Rwanda has 30 districts. A program gives each district its own binary code. What is the smallest number of bits each code needs?

- 4 bits give $2^4 = 16$ codes. That is not enough for 30 districts.
- 5 bits give $2^5 = 32$ codes. That is enough, with 2 codes to spare.
- So each code needs 5 bits.

## Binary to octal and hexadecimal: grouping bits

Because $8 = 2^3$, one octal digit stands for exactly 3 bits. Because $16 = 2^4$, one hexadecimal digit stands for exactly 4 bits. So you can convert without going through decimal: split the bits into groups **from the right**, and change each group into one digit using the table above.

### Worked example 5: grouping bits

(a) Convert $11010111_2$ to hexadecimal and to octal. (b) Convert $\mathrm{B4}_{16}$ to binary.

- (a) Groups of 4 from the right: 1101 | 0111. Since 1101 = D and 0111 = 7, $11010111_2 = \mathrm{D7}_{16}$.
- Groups of 3 from the right: 11 | 010 | 111. The left group has only 2 bits, so put a 0 in front: 011 | 010 | 111 = 3 | 2 | 7. So $11010111_2 = 327_8$.
- Check through decimal: $11010111_2 = 128 + 64 + 16 + 4 + 2 + 1 = 215$, $\mathrm{D7}_{16} = 13 \times 16 + 7 = 215$ and $327_8 = 3 \times 64 + 2 \times 8 + 7 = 215$. All three are correct.
- (b) Write each hex digit as 4 bits: B = 1011 and 4 = 0100. So $\mathrm{B4}_{16} = 10110100_2$.

Programmers like hexadecimal because it is short: one byte is always two hex digits, from 00 to FF. You meet it in web colours (the sky blue of Rwanda's flag is often written `#00A1DE`: red 00 = 0, green A1 = 161 and blue DE = 222), in memory addresses and in the address of a network card.

## Check your answers with the calculator

The [Calculator](/calculator) has a **Programmer** mode that shows one number in HEX, DEC, OCT and BIN at the same time. Open it, choose **Programmer** in its menu, pick DEC, type 4507, and compare the HEX and OCT lines with Worked example 3. Use it to check your work, but learn the methods: in an exam you must show every step.

## Common mistakes

- **Reading the remainders from the top down.** The first remainder is the rightmost digit: 156 is $10011100_2$, not $00111001_2$.
- **Grouping bits from the left.** Always start from the right, and add zeros on the left of the last group: $11010111_2$ becomes 011 | 010 | 111.
- **Writing a remainder of 10 to 15 as two digits.** In hexadecimal, a remainder of 11 is the single digit B: 4507 is $\mathrm{119B}_{16}$, not "11911".
- **Using a digit that does not exist in the base.** Binary uses only 0 and 1, and octal only 0 to 7, so "1092" cannot be an octal number.
- **Forgetting the base.** "10" can mean ten, two, eight or sixteen. Write $10_2$, $10_8$ or $10_{16}$.
- **Starting the place values at 2.** The rightmost place value is always $b^0 = 1$.

## Check yourself

1. Convert $110011_2$ to decimal.
2. Convert 100 to binary.
3. Convert $\mathrm{7C}_{16}$ to decimal and to binary.
4. Convert $1011101_2$ to octal and to hexadecimal.
5. What is the largest number you can write with 6 bits? Give it in binary and in decimal.
6. Which of these is not an octal number: 725, 1080 or 17? Why?
7. You are counting in binary. Which number comes just after $1011_2$?

*Answers: 1) $32 + 16 + 2 + 1 = 51$ · 2) $1100100_2$, because $64 + 32 + 4 = 100$ · 3) $7 \times 16 + 12 = 124$, and 0111 | 1100 gives $1111100_2$ · 4) 1 | 011 | 101 gives $135_8$, and 101 | 1101 gives $\mathrm{5D}_{16}$ (both are 93) · 5) $111111_2 = 2^6 - 1 = 63$ · 6) 1080, because 8 is not an octal digit · 7) $1100_2$, because $11 + 1 = 12$*
