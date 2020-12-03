import numpy as np
import sys
import json

STOP_WORDS = ["", "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself",
              "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself",
              "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these",
              "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do",
              "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while",
              "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before",
              "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
              "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
              "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
              "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]


def strip_word(word):
    return ''.join(char for char in word if char.isalpha()).lower()


def strip_sentences(paragraph):
    sentences = []
    current = []
    for word in paragraph.split(" "):
        if word != '':
            stripped_word = strip_word(word)
            if stripped_word not in STOP_WORDS:
                current.append(stripped_word)
            if word[-1] in ".?!":
                sentences.append(current)
                current = []
    return sentences


class TextRanker:
    def __init__(self, paragraph):
        self.paragraph = paragraph
        # Hyperparamaters for executing TextRank (in the score method)
        self.window_size = 4
        self.d = .85  # Better name?  It's called this in the paper.
        self.max_epochs = 10
        self.convergence_threshold = 1e-5

    def preprocess(self):  # TO-DO maybe have a list of sentences as input?!
        vocab = {}
        vocab_size = 0
        word_list = []
        sentences = strip_sentences(self.paragraph)
        for sentence in sentences:
            for word in sentence:
                if word not in vocab:
                    vocab[word] = vocab_size
                    vocab_size += 1
                    word_list.append(word)
        return vocab, vocab_size, sentences, word_list

    def make_pairs(self, sentences):
        pairs = []
        for sentence in sentences:
            for i in range(len(sentence)):
                for j in range(i + 1, min(i + self.window_size, len(sentence))):
                    pairs.append([sentence[i], sentence[j]])
        return pairs

    def get_matrix(self, vocab, pairs):
        mat = np.zeros((len(vocab), len(vocab)), dtype='float')
        for word1, word2 in pairs:
            mat[vocab[word1]][vocab[word2]] = 1
        mat = mat + mat.T - np.diag(mat.diagonal())  # Symmetrize
        col_norms = np.sum(mat, axis=0)
        mat = np.divide(mat, col_norms, where=col_norms != 0)  # Normalize
        return mat

    def score_vector(self, vocab_size, pairs, mat):
        ranks = np.array([1] * vocab_size)
        prev_sum = 0
        for epoch in range(self.max_epochs):
            ranks = (1 - self.d) + self.d * np.dot(mat, ranks)
            if abs(prev_sum - sum(ranks)) < self.convergence_threshold:
                break
            else:
                prev_sum = sum(ranks)
        return ranks

    def word_scores(self):
        # Basic pipeline
        vocab, vocab_size, sentences, word_list = self.preprocess()
        pairs = self.make_pairs(sentences)
        mat = self.get_matrix(vocab, pairs)
        ranks = self.score_vector(vocab_size, pairs, mat)
        # Compute word scores
        word_scores = {}
        for i in range(vocab_size):
            word_scores[word_list[i]] = ranks[i]
        return word_scores

    def keywords(self, num_keywords):
        word_scores = self.word_scores()
        scores = list(word_scores.values())
        scores.sort(reverse=True)
        top_scores = set(scores[:num_keywords])
        keywords = []
        for word in word_scores:
            if word_scores[word] in top_scores:
                keywords.append([word, word_scores[word]])
        return keywords


def get_keywords(paragraphs, keywords_per_paragraph=5):
    output = [TextRanker(paragraph).keywords(keywords_per_paragraph) for paragraph in paragraphs]
    return output


def test_run():
    input_file = open(sys.argv[1], 'r')
    output_file = open(sys.argv[2], 'w')
    paragraphs = [paragraph for paragraph in input_file.read().split("\n\n") if paragraph != '']
    input_file.close()
    output_file.write(json.dumps([TextRanker(paragraph).keywords(2) for paragraph in paragraphs]))
    output_file.close()


if __name__ == '__main__':
    test_run()
