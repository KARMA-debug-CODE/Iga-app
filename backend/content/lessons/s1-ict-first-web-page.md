---
slug: s1-ict-first-web-page
subject: ict
grade: S1
unit: 5
order: 1
title: Your first web page with HTML
summary: Build a real web page using HTML tags for headings, paragraphs, lists, links and images, and see the result live.
minutes: 30
simulations:
access: free
---
## What is HTML?

**HTML** (HyperText Markup Language) describes the *structure* of a web page. You wrap content in **tags**:

```html
<p>This is a paragraph.</p>
```

- `<p>` is the **opening tag**, `</p>` the **closing tag**.
- Everything between them is the **content**.
- Tag + content = an **element**.

## The skeleton of every page

```html
<!DOCTYPE html>
<html>
  <head>
    <title>My page</title>
  </head>
  <body>
    <!-- everything you see goes here -->
  </body>
</html>
```

## Common tags

| Tag | Meaning |
|---|---|
| `<h1>` … `<h6>` | headings, biggest to smallest |
| `<p>` | paragraph |
| `<ul>` / `<ol>` with `<li>` | bulleted / numbered list |
| `<a href="...">` | link |
| `<img src="..." alt="...">` | image (no closing tag) |
| `<strong>`, `<em>` | important, emphasised text |

## Try it yourself

Edit the code on the left and press **Run**. Change the heading to your name, add a third item to the list, and add a link to your favourite website.

```playground html
<!DOCTYPE html>
<html>
  <body>
    <h1>Muraho! I am Aline</h1>
    <p>I am a <strong>Senior 1</strong> student and I love science.</p>

    <h2>My favourite subjects</h2>
    <ul>
      <li>Mathematics</li>
      <li>ICT</li>
    </ul>

    <p>Visit the <a href="https://www.reb.gov.rw">Rwanda Basic Education Board</a>.</p>
  </body>
</html>
```

## Attributes

Extra information goes inside the opening tag as an **attribute**: `href` tells a link where to go; `alt` describes an image for people who cannot see it — always include it.

## Good habits

- Indent nested elements so your code is easy to read.
- Close every tag you open (except "empty" ones like `<img>` and `<br>`).
- Use headings in order: one `<h1>`, then `<h2>`s, and so on.

## Check yourself

1. Which tag makes the largest heading?
2. Write the HTML for a link to `https://www.geogebra.org` with the text "GeoGebra".
3. Why should every image have an `alt` attribute?
