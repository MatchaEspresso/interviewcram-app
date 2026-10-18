"""Check content in index.html: structure, and run each card's code against its tests.
Usage: python3 tools/check_content.py index.html [unit_id ...]

Executes predict/cloze/order/bug/compare cards against their `tests`, checks that options[0]
is right and that wrong options really fail. Exits 1 on any error."""
import json, re, signal, sys
PRELUDE = ("from bisect import bisect_left, bisect_right, insort\nfrom heapq import heappush, heappop, heapify, heapreplace, heappushpop, nlargest, nsmallest\n"
           "from itertools import accumulate, combinations, permutations, product\n"
           "from collections import defaultdict, Counter, deque, OrderedDict\nfrom functools import cache, lru_cache\nimport math\nfrom math import inf\n")
class TO(Exception): pass
def _alarm(*a): raise TO()
signal.signal(signal.SIGALRM, _alarm)

def run(src, expr=None):
    g = {}
    signal.alarm(2)
    try:
        exec(PRELUDE + src, g)
        return ("ok", eval(expr, g) if expr else None)
    except TO: return ("timeout", None)
    except AssertionError as e: return ("assert", e)
    except Exception as e: return ("error", f"{type(e).__name__}: {e}")
    finally: signal.alarm(0)

def fmt(v):
    return [repr(v), str(v)]

path, units = sys.argv[1], set(sys.argv[2:])
s = open(path).read()
C = json.loads(re.search(r'window\.IC_CONTENT = (\{.*?\});?\s*</script>', s, re.S).group(1))
cards = C["cards"]; errs = []; warns = []; checked = 0
ids_in_lessons = []
for u in C["units"]:
    for k in ("id", "title", "subtitle", "hue", "guide", "levels"): 
        if k not in u: errs.append(f"unit {u.get('id')} missing {k}")
    for k in ("intro", "template", "variants", "moves"):
        if k not in u["guide"]: errs.append(f"unit {u['id']} guide missing {k}")
    for lv in u["levels"]:
        for ls in lv["lessons"]:
            for cid in ls.get("cards", []):
                ids_in_lessons.append(cid)
                if cid not in cards: errs.append(f"{ls['id']}: missing card {cid}")
                elif cards[cid]["unit"] != u["id"]: errs.append(f"{cid}: unit mismatch")
dups = {x for x in ids_in_lessons if ids_in_lessons.count(x) > 1}
if dups: errs.append(f"cards in multiple lessons: {sorted(dups)}")
for cid, c in cards.items():
    if c.get("id") != cid: errs.append(f"{cid}: id field mismatch")
    if units and c["unit"] not in units: continue
    if cid not in ids_in_lessons: warns.append(f"{cid}: not in any lesson")
    t = c["type"]; setup = (c.get("setup") or "") + "\n"; tests = (c.get("tests") or "") + "\n" + (c.get("run") or "")
    need = {"teach": ["title", "body"], "mcq": ["prompt", "options", "explain"], "predict": ["prompt", "expr", "options", "explain"],
            "cloze": ["prompt", "code", "options", "explain"], "order": ["prompt", "lines", "distractors", "explain"],
            "bug": ["prompt", "lines", "line", "fix", "explain"], "compare": ["prompt", "a", "b", "answer", "explain"]}[t]
    for k in need:
        if k not in c: errs.append(f"{cid}: missing {k}")
    if "options" in c and len(set(c["options"])) != len(c["options"]): errs.append(f"{cid}: duplicate options")
    if t == "predict":
        st, v = run(setup + (c.get("code") or ""), c["expr"])
        if st != "ok": errs.append(f"{cid}: predict {st} {v}")
        elif c["options"][0] not in fmt(v): errs.append(f"{cid}: predict got {fmt(v)} but options[0]={c['options'][0]!r}")
        elif any(o in fmt(v) for o in c["options"][1:]): errs.append(f"{cid}: a wrong option equals the output")
        checked += 1
    elif t == "cloze":
        if c["code"].count("___") != 1: errs.append(f"{cid}: needs exactly one ___")
        if tests.strip():
            st, v = run(setup + c["code"].replace("___", c["options"][0]) + "\n" + tests)
            if st != "ok": errs.append(f"{cid}: cloze correct option fails: {st} {v}")
            for o in c["options"][1:]:
                if run(setup + c["code"].replace("___", o) + "\n" + tests)[0] == "ok": warns.append(f"{cid}: wrong option {o!r} also passes tests")
            checked += 1
    elif t == "order":
        allx = c["lines"] + c["distractors"]
        if any(not l.strip() for l in allx): errs.append(f"{cid}: blank line (renders as an empty chip, so Check never enables)")
        if len(set(allx)) != len(allx): errs.append(f"{cid}: duplicate lines (only one order is accepted)")
        if tests.strip():
            st, v = run(setup + "\n".join(c["lines"]) + "\n" + tests)
            if st != "ok": errs.append(f"{cid}: order fails: {st} {v}")
            checked += 1
    elif t == "bug":
        lines = list(c["lines"]); orig = lines[c["line"]]
        ind = orig[: len(orig) - len(orig.lstrip())]
        lines[c["line"]] = ind + c["fix"].strip()
        if tests.strip():
            st, v = run(setup + "\n".join(lines) + "\n" + tests)
            if st != "ok": errs.append(f"{cid}: fixed code fails: {st} {v}")
            if run(setup + "\n".join(c["lines"]) + "\n" + tests)[0] == "ok": errs.append(f"{cid}: buggy code passes tests")
            checked += 1
    elif t == "compare":
        if tests.strip():
            for k in "ab":
                st, v = run(setup + c[k] + "\n" + tests)
                if st != "ok": errs.append(f"{cid}: version {k} fails: {st} {v}")
            checked += 1
    if t not in ("teach",) and not (c.get("tests") or c.get("run")) and t in ("cloze", "order", "bug", "compare"):
        warns.append(f"{cid}: {t} card has no tests")
print(f"{len(cards)} cards, executed {checked}")
for w in warns: print("WARN", w)
for e in errs: print("ERR ", e)
sys.exit(1 if errs else 0)
