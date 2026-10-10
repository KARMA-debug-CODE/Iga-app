---
slug: s2-ict-css-basics
subject: ict
grade: S2
unit: 5
order: 1
title: Styling web pages with CSS
summary: Use CSS selectors, colours, fonts, spacing and the box model to make HTML look great.
minutes: 30
simulations:
---
## HTML is structure, CSS is style

**CSS** (Cascading Style Sheets) controls how HTML looks: colours, fonts, sizes, spacing and layout.

A CSS **rule** has a **selector** and **declarations**:

```css
h1 {
  color: #00A1DE;
  font-size: 32px;
}
```

- `h1` is the selector (which elements to style).
- `color: #00A1DE;` is a declaration: a **property** and a **value**.

## Three kinds of selector

| Selector | Example | Selects |
|---|---|---|
| element | `p { }` | every `<p>` |
| class | `.card { }` | every element with `class="card"` |
| id | `#header { }` | the one element with `id="header"` |

## The box model

Every element is a box made of four layers, from the inside out:

**content → padding → border → margin**

```css
.card {
  padding: 16px;          /* space inside the border */
  border: 2px solid #20603D;
  margin: 12px;           /* space outside the border */
  border-radius: 12px;    /* rounded corners */
}
```

## Try it

The page below uses Rwanda's flag colours. Change the colours, make the cards rounder, and add a hover effect.

```playground html
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: system-ui, sans-serif; background: #f5f7fb; padding: 20px; }
  h1 { color: #00A1DE; }
  .card {
    background: white;
    border-left: 6px solid #FAD201;
    padding: 16px;
    margin-bottom: 12px;
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,.08);
  }
  .card:hover { border-left-color: #20603D; }
  .tag { background: #20603D; color: white; padding: 2px 8px; border-radius: 999px; font-size: 12px; }
</style>
</head>
<body>
  <h1>Study plan</h1>
  <div class="card"><span class="tag">Maths</span> Practise straight-line graphs</div>
  <div class="card"><span class="tag">Physics</span> Revise Ohm's law</div>
</body>
</html>
```

## Colours

You can write colours as names (`red`), hex codes (`#FAD201`) or `rgb(250, 210, 1)`.

## Check yourself

1. Write a rule that makes every paragraph grey and 18 px.
2. What is the difference between padding and margin?
3. How do you select all elements with `class="note"`?
