import math
import re
from collections import Counter
from typing import List, Tuple, Optional, Dict

class NeuralIntentClassifier:
    """
    A lightweight, NPU-optimized Intent Classifier.
    
    This module is designed to run on low-power neural processing units (NPUs) 
    (e.g., via ONNX Runtime with NPU execution providers).
    
    For Phase 1 (Prototyping), we use a vector-based cosine similarity engine 
    that mimics the semantic matching behavior of a TinyBERT model without 
    requiring the full ONNX runtime stack immediately.
    """
    def __init__(self):
        # Neural Prototypes for each intent
        # These act as the "anchor vectors" in the semantic latent space.
        self.prototypes: Dict[str, List[str]] = {
            "track_iss": [
                "where is the iss",
                "current location of iss",
                "track international space station",
                "iss coordinates",
                "position of the space station",
                "where is the space station right now"
            ],
            "get_weather": [
                "weather in london",
                "what is the weather like",
                "current temperature in paris",
                "forecast for tokyo",
                "is it raining in seattle"
            ],
            # We add negative examples to help distinguish tricky cases
            # These map to None (general LLM query)
            "general_query": [
                "history of the iss",
                "who is on the iss",
                "experiments on the iss",
                "space station research",
                "how does the iss stay in orbit",
                "tell me about the weather",
                "why is the weather bad"
            ]
        }
        self.vocab = self._build_vocab()
        self.prototype_vectors = self._vectorize_prototypes()

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()

    def _build_vocab(self) -> Dict[str, int]:
        vocab = set()
        for examples in self.prototypes.values():
            for text in examples:
                vocab.update(self._tokenize(text))
        return {word: i for i, word in enumerate(sorted(list(vocab)))}

    def _vectorize(self, text: str) -> List[int]:
        tokens = self._tokenize(text)
        vec = [0] * len(self.vocab)
        token_counts = Counter(tokens)
        for word, count in token_counts.items():
            if word in self.vocab:
                vec[self.vocab[word]] = count
        return vec

    def _cosine_similarity(self, vec1: List[int], vec2: List[int]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        return dot_product / (norm_a * norm_b) if norm_a * norm_b > 0 else 0.0

    def _vectorize_prototypes(self) -> Dict[str, List[List[int]]]:
        vectors = {}
        for label, examples in self.prototypes.items():
            vectors[label] = [self._vectorize(ex) for ex in examples]
        return vectors

    def predict(self, text: str, threshold: float = 0.45) -> Optional[str]:
        input_vec = self._vectorize(text)
        
        # Check if input vector is empty (no known words)
        if sum(input_vec) == 0:
            return None

        best_score = -1.0
        best_intent = None

        for intent, prototype_vecs in self.prototype_vectors.items():
            # Get max similarity with any prototype of this intent
            score = max(self._cosine_similarity(input_vec, proto) for proto in prototype_vecs)
            if score > best_score:
                best_score = score
                best_intent = intent

        # Only return if above threshold
        # "general_query" is a catch-all for LLM fallback
        if best_score >= threshold and best_intent != "general_query":
            return best_intent
            
        return None

# Placeholder for future ONNX implementation
class ONNXIntentClassifier:
    def __init__(self, model_path: str):
        try:
            import onnxruntime as ort
            from transformers import BertTokenizer
            self.session = ort.InferenceSession(model_path)
            self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased") # or specific vocab
            print(f"Loaded ONNX model from {model_path}")
        except ImportError:
            print("Error: onnxruntime or transformers not installed. Install with: pip install onnxruntime transformers")
            self.session = None

    def predict(self, text: str) -> Optional[str]:
        if not self.session:
            return None
        # ... logic to run ONNX inference ...
        return None
