"""
Belief Revision Engine

Run:
    python app.py

Then open:
    http://localhost:8000

keeping everything in one file for now because this project is already
long enough honestly
"""

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import parse_qs
from html import escape
import re


# ---------------------------------
# logic form objects
# ---------------------------------


@dataclass(frozen=True)
class Form:
    op:str
    left:object=None
    right:object=None

    def __str__(self):
        if self.op=="var":
            return str(self.left)
        if self.op=="!":
            return "!"+str(self.left)

        return "(" + str(self.left) + " " + self.op + " " + str(self.right) + ")"


@dataclass(frozen=True,order=True)
class Lit:
    name:str
    negated:bool=False

    def opposite(self):
        return Lit(self.name,not self.negated)


def make_var(name):
    return Form("var",name)


def negate(item):
    return Form("!",item)


def make_binary(op,left,right):
    return Form(op,left,right)


# ---------------------------------
# parser stuff
# ---------------------------------

# lets users type easier keyboard versions
symbol_shortcuts={
    "!":"!",
    "~":"!",
    "not":"!",

    "&":"&",
    "and":"&",

    "|":"|",
    "or":"|",

    "->":"->",
    "=>":"->",

    "<->":"<->",
    "<=>":"<->"
}

token_pattern=re.compile(r"\s*(<->|<=>|->|=>|[()!~&|]|[A-Za-z][A-Za-z0-9_]*)")


class Parser:

    def __init__(self,text):
        self.tokens=[]
        self.index=0
        i=0
        while i<len(text):
            match=token_pattern.match(text,i)
            if not match:
                raise ValueError("bad token near "+text[i:])
            token=match.group(1)
            token=symbol_shortcuts.get(token.lower(),token)
            self.tokens.append(token)
            i=match.end()

    def current(self):
        if self.index>=len(self.tokens):
            return None
        return self.tokens[self.index]
    def eat(self,token):
        if self.current()==token:
            self.index+=1
            return True
        return False
    def parse(self):
        # start from weakest precedence operator
        result=self.parse_iff()
        if self.current() is not None:
            raise ValueError("extra token "+str(self.current()))
        return result
    def parse_iff(self):
        # biconditional has lowest precedence
        # p <-> q means both imply each other
        left=self.parse_imp()
        while self.eat("<->"):
            right=self.parse_imp()
            left=make_binary("<->",left,right)
        return left
    def parse_imp(self):
        # implication is right associative
        # p -> q -> r becomes p -> (q -> r)
        left=self.parse_or()
        if self.eat("->"):
            right=self.parse_imp()
            return make_binary("->",left,right)
        return left
    def parse_or(self):
        left=self.parse_and()
        while self.eat("|"):
            right=self.parse_and()
            left=make_binary("|",left,right)
        return left
    def parse_and(self):
        left=self.parse_not()
        while self.eat("&"):
            right=self.parse_not()
            left=make_binary("&",left,right)
        return left
    def parse_not(self):
        # negation binds strongest
        if self.eat("!"):
            return negate(self.parse_not())
        return self.parse_atom()
    def parse_atom(self):
        token=self.current()
        if token=="(":
            self.index+=1
            inside=self.parse_iff()
            if not self.eat(")"):
                raise ValueError("missing )")
            return inside
        if token and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*",token):
            self.index+=1
            return make_var(token)
        raise ValueError("expected variable")


def read_form(text):
    return Parser(text).parse()


# ---------------------------------
# CNF conversion
# ---------------------------------

# resolution works best in conjunctive normal form (CNF)
# so we convert everything first


def remove_implications(f):
    if f.op=="var":
        return f
    if f.op=="!":
        return negate(remove_implications(f.left))
    left=remove_implications(f.left)
    right=remove_implications(f.right)
    # implication law:
    # p -> q === !p OR q

    if f.op=="->":
        return make_binary("|",negate(left),right)
    # biconditional law:
    # p <-> q === (p -> q) AND (q -> p)

    if f.op=="<->":
        a=make_binary("|",negate(left),right)
        b=make_binary("|",negate(right),left)
        return make_binary("&",a,b)
    return make_binary(f.op,left,right)


def move_negations(f):
    if f.op=="var":
        return f
    if f.op!="!":
        return make_binary(
            f.op,
            move_negations(f.left),
            move_negations(f.right)
        )
    inside=f.left
    if inside.op=="var":
        return f
    # double negation law:
    # !!p === p
    if inside.op=="!":
        return move_negations(inside.left)
    # De Morgan's Law:
    # !(p AND q) === !p OR !q
    if inside.op=="&":
        return make_binary(
            "|",
            move_negations(negate(inside.left)),
            move_negations(negate(inside.right))
        )
    # De Morgan's Law:
    # !(p OR q) === !p AND !q
    if inside.op=="|":
        return make_binary(
            "&",
            move_negations(negate(inside.left)),
            move_negations(negate(inside.right))
        )
    raise Exception("negation issue")


def spread_or(f):
    # distributive law step
    # needed for full CNF conversion
    if f.op in ["var","!"]:
        return f
    left=spread_or(f.left)
    right=spread_or(f.right)
    if f.op=="&":
        return make_binary("&",left,right)
    # distributive law:
    # p OR (q AND r)
    # becomes:
    # (p OR q) AND (p OR r)
    if f.op=="|" and left.op=="&":
        a=spread_or(make_binary("|",left.left,right))
        b=spread_or(make_binary("|",left.right,right))
        return make_binary("&",a,b)
    if f.op=="|" and right.op=="&":
        a=spread_or(make_binary("|",left,right.left))
        b=spread_or(make_binary("|",left,right.right))
        return make_binary("&",a,b)
    return make_binary("|",left,right)


def to_cnf(f):
    no_implications=remove_implications(f)
    pushed_negations=move_negations(no_implications)
    return spread_or(pushed_negations)


# ---------------------------------
# clause generation
# ---------------------------------

# resolution uses clauses instead of tree formulas


def make_clause(f):
    clause=set()
    def walk(part):
        if part.op=="|":
            walk(part.left)
            walk(part.right)
        elif part.op=="var":
            clause.add(Lit(part.left))
        elif part.op=="!" and part.left.op=="var":
            clause.add(Lit(part.left.left,True))
        else:
            raise ValueError("bad cnf clause")
    walk(f)
    return frozenset(clause)


def clause_is_tautology(clause):
    # p OR !p is always true
    # tautologies give no useful information in resolution
    for item in clause:
        if item.opposite() in clause:
            return True
    return False


def make_clauses(f):
    clauses=set()
    def collect(piece):
        # split conjunctions into separate clauses
        if piece.op=="&":
            collect(piece.left)
            collect(piece.right)
        else:
            c=make_clause(piece)
            if not clause_is_tautology(c):
                clauses.add(c)
    collect(to_cnf(f))
    return clauses


def clauses_from_forms(forms):
    all_clauses=set()
    for form in forms:
        for c in make_clauses(form):
            all_clauses.add(c)
    return all_clauses


# ---------------------------------
# resolution algorithm
# ---------------------------------


def resolve(c1,c2):
    results=set()
    for lit in c1:
        # resolution rule:
        # (p OR A) and (!p OR B)
        # produce:
        # (A OR B)
        if lit.opposite() in c2:
            left1=set(c1)
            left2=set(c2)
            left1.remove(lit)
            left2.remove(lit.opposite())
            merged=left1.union(left2)
            final=frozenset(merged)
            if not clause_is_tautology(final):
                results.add(final)
    return results


def contradiction_exists(clauses):
    clauses=set(clauses)
    while True:
        generated=set()
        current=list(clauses)
        for i in range(len(current)):
            for j in range(i+1,len(current)):
                c1=current[i]
                c2=current[j]
                new_clauses=resolve(c1,c2)
                for clause in new_clauses:
                    # empty clause means contradiction
                    # basically means false was derived
                    if len(clause)==0:
                        return True
                    generated.add(clause)
        # if no new clauses appear then resolution is done
        if generated.issubset(clauses):
            return False
        clauses=clauses.union(generated)
        # not ideal but prevents infinite explosion
        if len(clauses)>5000:
            break
    return False


# ---------------------------------
# bob belief revision
# ---------------------------------

# this section models Bob's beliefs
# priorities matter because weaker beliefs get removed first


def bob_would_have_to_believe(known_forms,target):
    # proof by contradiction:
    # if adding NOT target creates contradiction,
    # then target must logically follow
    clauses=clauses_from_forms(known_forms)
    opposite=make_clauses(negate(target))
    clauses=clauses.union(opposite)
    return contradiction_exists(clauses)


def bob_is_consistent(forms):
    return not contradiction_exists(clauses_from_forms(forms))


def forms_without_priorities(beliefs):
    forms=[]
    for item in beliefs:
        forms.append(item[0])
    return forms


def read_bobs_beliefs(text):
    beliefs=[]
    lines=text.splitlines()
    priority=len(lines)
    # earlier beliefs get slightly higher priority
    for line in lines:
        line=line.strip()
        if line=="":
            continue
        parsed=read_form(line)
        beliefs.append((parsed,priority))
        priority-=1
    return beliefs


def weakest_belief_index(beliefs):
    weakest=0
    for i in range(len(beliefs)):
        if beliefs[i][1]<beliefs[weakest][1]:
            weakest=i
    return weakest


def remove_support_for(beliefs,formula):
    current=beliefs.copy()
    while bob_would_have_to_believe(
        forms_without_priorities(current),
        formula
    ):
        if len(current)==0:
            break
        weakest=weakest_belief_index(current)
        # remove weakest belief first
        current.pop(weakest)
    return current


def revise_bobs_beliefs(beliefs,new_form):
    # Levi Identity:
    # revise(B,p)=contract(B,!p)+p
    smaller=remove_support_for(
        beliefs,
        negate(new_form)
    )
    # might already believe new_form, but add it with high priority just in case
    smaller.append((new_form,10))
    return smaller


# ---------------------------------
# displaying logic
# ---------------------------------


def show_form(f):
    if f.op=="var":
        return str(f.left)
    if f.op=="!":
        return "¬"+show_form(f.left)
    op=f.op
    if op=="&":
        op="∧"
    elif op=="|":
        op="∨"
    elif op=="->":
        op="→"
    elif op=="<->":
        op="↔"
    return "(" + show_form(f.left) + " " + op + " " + show_form(f.right) + ")"


def show_bobs_belief_set(beliefs):
    text=[]
    for item in beliefs:
        text.append(show_form(item[0]))
    return "Cn({" + ", ".join(text) + "})"


# ---------------------------------
# webpage
# ---------------------------------


DEFAULT_BELIEFS="p\nq\nr"
DEFAULT_NEW="!(q | r)"

HTML_FILE="index.html"


def make_page(base=DEFAULT_BELIEFS,new=DEFAULT_NEW,result=""):
    with open(HTML_FILE,"r",encoding="utf-8") as f:
        html=f.read()
    html=html.replace("{{base_text}}",escape(base))
    html=html.replace("{{new_text}}",escape(new))
    html=html.replace("{{result}}",escape(result))
    return html


class WebPage(BaseHTTPRequestHandler):

    def send_html(self,html):
        encoded=html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        self.send_html(make_page())

    def do_POST(self):
        length=int(self.headers.get("Content-Length",0))
        raw=self.rfile.read(length).decode("utf-8")
        data=parse_qs(raw)
        base=data.get("base",[""])[0]
        new=data.get("new",[""])[0]
        try:
            beliefs=read_bobs_beliefs(base)
            if not bob_is_consistent(
                forms_without_priorities(beliefs)
            ):
                output="Bob's beliefs are inconsistent\n\n"
                output+=show_bobs_belief_set(beliefs)
            else:
                revised=revise_bobs_beliefs(
                    beliefs,
                    read_form(new)
                )
                output="Bob's revised beliefs:\n\n"
                output+=show_bobs_belief_set(revised)
                output+="\n\nconsistent: "
                output+=str(
                    bob_is_consistent(
                        forms_without_priorities(revised)
                    )
                )
        except Exception as e:
            # maybe add traceback logging later
            output="error: "+str(e)
        self.send_html(make_page(base,new,output))


if __name__=="__main__":
    print("starting server...")
    print("open http://localhost:8000")
    server=HTTPServer(("localhost",8000),WebPage)

    server.serve_forever()