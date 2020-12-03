from allennlp.predictors.predictor import Predictor

con_parser = Predictor.from_path("https://s3-us-west-2.amazonaws.com/allennlp/models/elmo-constituency-parser-2018.03.1"
                                 + "4.tar.gz")


class TreeNode:
    def __init__(self, val):
        self.val = val
        self.children = []


def build_tree(tree):
    # Can either start with ' (' or just '('
    if tree[0] == ' ':
        j = 2
    else:
        j = 1
    # Get label
    label = ''
    while j < len(tree) and tree[j] != ' ':  # yay?
        label += tree[j]
        j += 1
    j += 1
    if label != '' and label[0] == '(':  # yay?
        label = label[1:]
    output = TreeNode(label)
    # At max recursion depth
    if '(' not in tree[j:]:
        output.children.append(tree[j:len(tree) - 1])
        return output
    # Find and recurse on subtrees
    parens = 0
    current = ''
    while j < len(tree) - 1:
        current += tree[j]
        if tree[j] == '(':
            parens += 1
        if tree[j] == ')':
            parens -= 1
            if parens == 0:
                output.children.append(build_tree(current))  # Modify
                current = ''
        j += 1
    return output


# Traverse to find a particular node.  Return -1 for fail.
# WARNING: currently returns FIRST instance for in order traversal if there are
# multiple instances


def find_nodes(tree, node_vals):
    try:
        for node_val in node_vals:
            if tree.val == node_val:
                return tree
        for child in tree.children:
            result = find_nodes(child, node_vals)
            if result != None:
                return result
    except AttributeError:
        return None


# WARNING: Due to problems with running files on colab, this is not working.
# Until I fix this, use the dictionary copied and pasted from Jupyter output.


def irreg_verb_table(file_path):
    file = open(file_path)
    table = {}
    for line in file:
        if line[len(line) - 1] == '\n':
            line = line[:-1]
        lookup = []
        for item in line.split('\t'):
            if '/' in item:
                lookup.append(item.split('/')[0])
            else:
                lookup.append(item)
        verb_forms = line.replace('/', '\t').split('\t')
        for verb in verb_forms:
            table[verb] = lookup
    file.close()
    return table


table = irreg_verb_table('irregular_verbs.txt')


def conjugate(verb, table, form):
    if verb[-1] == 's':
        verb = verb[:-1]
    index = {'present': 0, 'past': 1, 'past_part': 2}
    if verb in table:
        return table[verb][index[form]]
    else:
        if form == 'present':
            if verb[-1] == 'd':
                return verb[:-2]
            else:
                return verb
        else:
            if verb[-1] == 'd':
                return verb
            elif verb[-1] == 'e':
                return verb + 'd'
            else:
                return verb + 'ed'


# CORE PART - used to actually construct triples from sentence trees
# MOST IMPORTANT

def find_adjective(np):  # TO-DO input may not be an NP - revise?!?!
    adjectives = ['JJ', 'JR', 'JS']
    adj = find_nodes(np, adjectives)
    if adj is not None:
        return adj.children[0]
    else:
        return None


def find_noun(np):
    nouns = ['NN', 'NNS', 'NNP', 'NNPS', 'PRP', 'EX']
    # Allowing return values of possessive pronouns leads
    # these replacing the true objects in the triples obtained.
    noun = find_nodes(np, nouns)
    if noun is not None:
        return noun.children[0]
    else:
        return find_adjective(np)


def find_verb(vp):
    verbs = ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']
    verb = find_nodes(vp, verbs)
    if verb is not None:
        return verb.children[0]
    else:
        return None


def process_pp(pp):  # yay? MODIFIED
    prep = find_nodes(pp, ['IN'])
    if prep:
        if len(prep.children) != 0:
            prep = prep.children[0]
            ob = find_noun(pp)
            return [[prep, ob]]
    return []


def infinitive(vp):  # TODO misleading name since may include a following noun?!
    s_node = None
    for child in vp.children:
        if child.val == 'S':
            s_node = child
            break
    if s_node is None:
        return None
    verb = find_verb(s_node)
    if find_nodes(s_node, ['TO']) is None or verb is None:
        return None  # No infinitive present
    noun = find_noun(s_node)  # Might be None
    if noun is not None:
        return 'to_' + verb + '_' + noun
    else:
        return 'to_' + verb


def assemble_triples(subj, verb, dobj, iobj, pp_list):
    triples = []
    # subj - verb - dobj
    triples.append([subj, verb, dobj])
    # subj - verb - iobj
    if iobj is not None:
        triples.append([dobj, conjugate(verb, table, 'past_part') + '_to', iobj])
    # prepositional phrases
    for pp in pp_list:
        triples.append([subj, verb + '_' + pp[0], pp[1]])
    return triples
    # return [subj, verb, dobj, iobj, pp_list]


def find_objects(vp):
    objects = []
    pp_list = []
    for child in vp.children:
        if child.val == 'NP':
            objects.append(find_noun(child))
        elif child.val == 'ADJP':
            objects.append(find_adjective(child))
        elif child.val == 'PP':
            pp_list += process_pp(child)  # yay?
    dobj = None
    iobj = None
    if len(objects) == 1:
        dobj = objects[0]  # subj + dobj
    elif len(objects) > 1:  # Should never be > 2 I don't think
        dobj = objects[1]  # subj + dobj + iobj
        iobj = objects[0]
    else:  # Infinitive as object?
        dobj = infinitive(vp)  # possibly None
    return [dobj, iobj, pp_list]


def process_S_node(tree):  # TO-DO Consider splitting up into several functions.
    np = None
    vp = None
    adjp = None
    for child in tree.children:
        if child.val == 'NP':
            np = child
        elif child.val == 'VP':
            vp = child
        elif child.val == 'ADJP':
            adjp = child
    if np is None and adjp is not None:
        np = adjp
    subj = find_noun(np)
    verb = find_verb(vp)
    if subj == None or verb == None:  # I can either both or neither are present.
        return []
    dobj, iobj, pp_list = find_objects(vp)
    return assemble_triples(subj, verb, dobj, iobj, pp_list)


def process_NP_node(tree):
    nouns = ['NN', 'NNS', 'NNP', 'NNPS', 'PRP']
    count = len(tree.children)
    triples = []
    for j in range(count - 1):
        if tree.children[j].val == 'JJ':
            if tree.children[j + 1].val in nouns:
                adj = tree.children[j].children[0]
                noun = find_noun(tree.children[j + 1])
                triple = [noun, 'is', adj]
                triples.append(triple)
        if tree.children[j].val == 'NP' and j + 3 < count:
            if (tree.children[j + 1].val == ',' and tree.children[j + 3].val
                    == ',' and tree.children[j + 2].val == 'NP'):
                noun1 = find_noun(tree.children[j])
                noun2 = find_noun(tree.children[j + 2])
                triple = [noun1, 'is', noun2]
                triples.append(triple)
    return triples


def process_tree(tree):  # Should never be given leaves to process
    if len(tree.children) == 0 or type(tree.children[0]) is str:  # Bottom of recursion  yay?
        return []
    triples = []
    if tree.val == 'S':
        triples += process_S_node(tree)
    if tree.val == 'NP':  # NOTE: OMIT THIS AND NEXT LINE IF PROBLEMATIC
        triples += process_NP_node(tree)
    for subtree in tree.children:
        triples += process_tree(subtree)
    return triples


def clean_triple(triple):
    ob1 = triple[0].lower()
    rel = triple[1].lower()
    ob2 = triple[2]
    if ob2 is None:
        ob2 = 'empty_node'
    else:
        ob2 = ob2.lower()
    return [ob1, rel, ob2]


def filter_triples(triples):
    prohibited = {'he', 'his', 'him', 'she', 'her', 'hers', 'they', 'them',
                  'their', 'it', 'its'}
    filtered = []
    for triple in triples:
        if triple[2] is None:  # Take out to use the empty_node feature.
            continue
        if (triple[0] not in prohibited and triple[1] not in prohibited and
                triple[2] not in prohibited):
            filtered.append(clean_triple(triple))
    return filtered


def sentence_to_triples(text):
    if text == '':
        return []
    raw = con_parser.predict(text)['trees']
    if raw[:3] != '(S ':  # Not a complete sentence
        return []
    tree = build_tree(raw)
    triples = process_tree(tree)
    return filter_triples(triples)


def make_sentences(text):
    sentences = []
    sentence = ''
    for j in range(len(text)):
        sentence += text[j]
        if text[j] in ['.', '?', '!']:
            sentences.append(sentence)
            sentence = ''
        j += 1
    return sentences


def text_to_triples(text):
    sentences = make_sentences(text)
    output = []
    for sentence in sentences:
        output += sentence_to_triples(sentence)
    return output


def file_to_triples(input_file):
    return text_to_triples(input_file.read())

# TODO add testing code
