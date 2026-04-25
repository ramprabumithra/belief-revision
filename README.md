# Belief Revision Engine

This project implements a simple belief revision agent for symbolic propositional logic.
It uses keyboard-friendly symbols:

- negation: `!`
- conjunction: `&`
- disjunction: `|`
- implication: `->`
- biconditional: `<->`

Words like `not`, `and`, `or`, `implies`, and `iff` also work.

The main Python code is in `app.py`, and the small browser page is in `index.html`.
The code is written around the assignment story: Bob has a belief set, then learns a new formula from a reliable source.

The implementation follows the course pipeline:

1. Represent a belief base as prioritized propositional formulae.
2. Check entailment with a self-contained CNF conversion and resolution procedure.
3. Contract a belief base using priority-based partial meet contraction.
4. Expand by adding the new belief.
5. Revise by Levi identity: `K * phi = (K - !phi) + phi`.

## Run the small screen

```bash
python3 app.py
```

Then open this in your browser:

```text
http://localhost:8000
```

The page lets you enter:

- the belief base, one belief per line
- the formula to revise by

The app still uses priorities internally for contraction, but you do not type them.
Earlier beliefs are treated as slightly more important, and the new formula gets priority `10`.
If a typed belief has a syntax problem, the app points to the line that caused it.
The output is shown as a belief set, for example:

```text
Cn({p, ¬q})
```

Beliefs use this format:

```text
p
p -> q
!q
```

So Bob's belief set `Cn({p, q, r})` can be entered as:

```text
p
q
r
```

If Bob then learns `!(q | r)`, enter that as the new formula. The output is:

```text
Cn({p, ¬(q ∨ r)})
```

## Test

```bash
python3 -m unittest discover -s tests
```

The tests cover resolution entailment, consistency, and AGM-oriented properties: Success,
Inclusion/Vacuity in the non-conflicting case, Consistency, and Extensionality.
