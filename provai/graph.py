from functools import lru_cache

import owlrl
from pyshacl import validate
from rdflib import RDF, Graph, Namespace

from .config import ONTOLOGY, PAI, PROVO, SHAPES

SH = Namespace("http://www.w3.org/ns/shacl#")


@lru_cache
def parsed(src):
    return Graph().parse(src, format="xml" if src.endswith(".owl") else None)


def load(*sources):
    g = Graph()
    g.bind("provai", PAI)
    for src in sources:
        g += src if isinstance(src, Graph) else parsed(str(src))
    return g


def close(g):
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    return g


def with_ontology(*sources):
    return load(PROVO, ONTOLOGY, *sources)


def check(*sources):
    ok, report, _ = validate(load(*sources), shacl_graph=load(SHAPES), ont_graph=load(PROVO, ONTOLOGY),
                             inference="none", advanced=True)
    messages = [str(report.value(r, SH.resultMessage)) for r in report.subjects(RDF.type, SH.ValidationResult)]
    return ok, messages
