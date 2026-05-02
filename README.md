# Belief Revision Engine

This project is a belief revision agent for symbolic propositional logic.
I kept the syntax keyboard-friendly so it’s easier to type formulas without needing special symbols everywhere.

Supported operators:

* negation: `!`
* conjunction: `&`
* disjunction: `|`
* implication: `->`
* biconditional: `<->`

You can also type the word versions (`not`, `and`, `or`, `implies`, `iff`) if that feels more natural.

The main logic lives in `app.py`, and there’s a tiny browser UI in `index.html`.

The whole thing is built around the assignment scenario where Bob already has some beliefs, then receives a new piece of information from a trusted source and updates his belief set accordingly.

On the inside, the implementation roughly follows this flow from the course material:

1. Store beliefs as prioritized propositional formulas.
2. Check entailment using a homemade CNF conversion + resolution setup (didn’t want to rely on external logic libraries here).
3. Contract the belief base using a priority-based partial meet contraction approach.
4. Expand the belief base with the incoming belief.
5. Perform revision using the Levi Identity:

   `K * phi = (K - !phi) + phi`
---
## Running the front-end

Start the server with:

```bash
python3 app.py
```

Then open:

```text
http://localhost:8000
```

The page is intentionally pretty simple. You just enter:

* the current belief base (one belief per line)
* the new formula Bob learns

A couple implementation details worth mentioning:

* priorities are still used internally during contraction
* you don’t manually enter priorities though
* earlier beliefs are treated as slightly more important
* the incoming belief automatically gets priority `10`

If there’s a syntax mistake in one of the beliefs, the app tries to point out which line caused the issue instead of failing silently (spent too much time debugging malformed formulas earlier lol).

The result is displayed as a belief set like this:

```text
Cn({p, ¬q})
```

Example belief syntax:

```text
p
p -> q
!q
```

So if Bob’s starting belief set is:

```text
Cn({p, q, r})
```

you would type:

```text
p
q
r
```

And if Bob later learns:

```text
!(q | r)
```

then that becomes the revision formula.

The updated output would look something like:

```text
Cn({p, ¬(q ∨ r)})
```
---
## Running tests

```bash
python3 -m unittest discover -s tests
```
The tests cover a few important things:

* resolution-based entailment
* consistency checking
* some AGM-style revision properties

including:

* Success
* Inclusion / Vacuity (when there’s no conflict)
* Consistency
* Extensionality

I tried to keep the tests focused on behavior instead of implementation details so refactoring the internals later shouldn’t completely break everything.
