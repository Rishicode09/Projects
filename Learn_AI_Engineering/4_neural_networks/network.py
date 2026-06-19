"""
The NeuralNetwork class (shared between train.py and the API).
Built from scratch using only NumPy.
"""
import numpy as np

def relu(x):          return np.maximum(0, x)
def relu_grad(x):     return (x > 0).astype(float)
def softmax(x):
    e = np.exp(x - np.max(x, axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)

class NeuralNetwork:
    """
    3-layer MLP: input_size → hidden1 → hidden2 → output_size
    Fixed from EE_AI_From_Scratch: larger network, cleaner data.
    """
    def __init__(self, input_size=50, hidden1=128, hidden2=64, output_size=3):
        self.W1 = np.random.randn(input_size, hidden1) * np.sqrt(2.0 / input_size)
        self.b1 = np.zeros((1, hidden1))
        self.W2 = np.random.randn(hidden1, hidden2) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros((1, hidden2))
        self.W3 = np.random.randn(hidden2, output_size) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros((1, output_size))
        self.cache = {}

    def forward(self, X):
        z1 = X @ self.W1 + self.b1;  a1 = relu(z1)
        z2 = a1 @ self.W2 + self.b2; a2 = relu(z2)
        z3 = a2 @ self.W3 + self.b3; a3 = softmax(z3)
        self.cache = dict(X=X, z1=z1, a1=a1, z2=z2, a2=a2, z3=z3, a3=a3)
        return a3

    def predict(self, X):
        return np.argmax(self.forward(X), axis=1)

    def param_count(self):
        return sum(w.size for w in [self.W1,self.b1,self.W2,self.b2,self.W3,self.b3])
