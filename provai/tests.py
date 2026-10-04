import importlib

from rdflib import RDF, Graph, Literal, URIRef

from .config import PAI, PROV, RUNS
from .evaluate import PREFIXES, questions, span_format
from .graph import check, close, with_ontology


def run_dirs():
    return sorted(p for fw in RUNS.iterdir() if fw.is_dir() for p in fw.iterdir() if (p / "spans.jsonl").exists())


def convert(module, run_dir):
    return importlib.import_module(f"provai.converters.{module}").convert(run_dir).g


def copy(g):
    out = Graph()
    out += g
    return out


def ask(g, cq):
    query = next(q for name, _, _, q in questions() if name == cq)
    result = close(with_ontology(g)).query(PREFIXES + query)
    return [{str(v): r[v] for v in result.vars if r[v] is not None} for r in result]


def records():
    out = []
    for run_dir in run_dirs():
        fw = run_dir.parent.name
        for module in (span_format(run_dir), fw):
            ok, _ = check(convert(module, run_dir))
            out.append((f"{fw} record from {module} conforms", ok))
    return out


def shapes(base):
    model_call = next(base.subjects(RDF.type, PAI.ModelCall))
    entity = next(base.subjects(RDF.type, PROV.Entity))
    model = URIRef("urn:test:model")
    cases = {
        "dependence is inferred by the reasoner, never asserted": [(entity, PAI.dependsOn, URIRef("urn:test:x"))],
        "a model call names the one model it used": [(model_call, PAI.usedModel, model), (model, RDF.type, PAI.Model)],
        "a step ends in one known status": [(model_call, PAI.status, Literal("unknown"))],
    }
    out = []
    for message, triples in cases.items():
        g = copy(base)
        if message.startswith("a step"):
            g.remove((model_call, PAI.status, None))
        for t in triples:
            g.add(t)
        ok, messages = check(g)
        out.append((f"shape catches: {message}", not ok and message in messages))
    return out


def conflict(base):
    g = copy(base)
    record = next(g.subjects(RDF.type, PAI.MemoryRecord))
    memory = next(g.subjects(PROV.hadMember, record))
    run = next(g.subjects(RDF.type, PAI.Run))
    agent = next(g.subjects(RDF.type, PAI.Agent))
    for name in ("a", "b"):
        newer, write = URIRef(f"{record}-conflict-{name}"), URIRef(f"{run}/conflict-write-{name}")
        g.add((newer, RDF.type, PAI.MemoryRecord))
        g.add((memory, PROV.hadMember, newer))
        g.add((newer, PROV.wasRevisionOf, record))
        g.add((newer, PROV.wasGeneratedBy, write))
        g.add((write, RDF.type, PAI.MemoryAccess))
        g.add((write, PAI.partOf, run))
        g.add((write, PAI.status, Literal("completed")))
        g.add((write, PROV.wasAssociatedWith, agent))
    ok, messages = check(g)
    flagged = any("conflicting write" in m for m in messages)
    found = any(r.get("conflict") == record for r in ask(g, "CQ10"))
    return [("shape catches a conflicting write", not ok and flagged), ("CQ10 finds the conflicting write", found)]


def later_request(base):
    g = copy(base)
    record = next(g.subjects(RDF.type, PAI.MemoryRecord))
    later, read, reader = URIRef("urn:test:run2"), URIRef("urn:test:run2/read"), URIRef("urn:test:reader")
    g.add((later, RDF.type, PAI.Run))
    g.add((later, PAI.source, Literal("test")))
    g.add((reader, RDF.type, PAI.Agent))
    g.add((read, RDF.type, PAI.MemoryAccess))
    g.add((read, PAI.partOf, later))
    g.add((read, PAI.status, Literal("completed")))
    g.add((read, PROV.used, record))
    g.add((read, PROV.wasAssociatedWith, reader))
    ok, _ = check(g)
    found = any(r.get("reader") == reader for r in ask(g, "CQ5"))
    return [("a later request's memory read conforms", ok), ("CQ5 finds a read from a later request", found)]


def run_tests():
    base = convert("langgraph", next(p for p in run_dirs() if p.parent.name == "langgraph"))
    results = records() + shapes(base) + conflict(base) + later_request(base)
    return results
