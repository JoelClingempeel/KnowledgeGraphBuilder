import json
import os
import sys

from paragraph_keywords import get_keywords
from extract_triples import text_to_triples


class Graph:
    def __init__(self):
        self.graph = {'nodes': {}, 'relations': {}, 'paragraphs': {}}

    def _one_way_edge(self, node1, node2):
        if node1 in self.graph['nodes']:
            if node2 not in self.graph['nodes'][node1]:
                self.graph['nodes'][node1].append(node2)
        else:
            self.graph['nodes'][node1] = [node2]
        if node2 not in self.graph['nodes']:
            self.graph['nodes'][node2] = []

    def add_edge(self, node1, node2, rel=''):
        self._one_way_edge(node1, node2)
        # self._one_way_edge(node2, node1)
        if rel != '':
            self.graph['relations'][node1 + "/" + node2] = rel

    def serialize(self):
        return json.dumps(self.graph)

    def add_paragraph_links(self, paragraph_vectors):
        for cluster in paragraph_vectors:
            for j in range(len(cluster)):
                for i in range(j):
                    self.add_edge(str(cluster[i]), str(cluster[j]))

    def add_keywords(self, raw_keyword_data, return_keywords=False):
        keywords = raw_keyword_data
        for k in range(len(keywords)):
            for pair in keywords[k]:
                self.add_edge(pair[0], str(k))
                self.graph['relations'][pair[0] + '/' + str(k)] = str(pair[1])
        if return_keywords:
            return [word for sublist in keywords for word in sublist]

    def add_triples(self, text, keywords):
        node_set = set([pair[0] for pair in keywords])
        triples = text_to_triples(text)
        for triple in triples:
            if (triple[0] in node_set or triple[2] in keywords) and triple[0] != triple[2]:
                self.add_edge(triple[0], triple[2])
                self.graph['relations'][triple[0] + '/' + triple[2]] = triple[1]

    def add_paragraphs(self, paragraphs):
        for i in range(len(paragraphs)):
            self.graph['paragraphs'][i] = paragraphs[i]

    def add_text_to_graph(self, text):
        paragraphs = [paragraph for paragraph in text.replace('\r', '').split("\n\n") if paragraph != '']
        raw_keyword_data = get_keywords(paragraphs)
        keywords = self.add_keywords(raw_keyword_data, return_keywords=True)
        self.add_triples(text, keywords)
        self.add_paragraphs(paragraphs)

