
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
def sigmoid(x): return 1/(1+np.exp(-x))
def relu(x): return np.maximum(0,x)
def tanh_fn(x): return np.tanh(x)
class Neuron:
    def __init__(self,n): self.w=np.random.randn(n)*0.01; self.b=0.0
    def forward(self,x): z=np.dot(self.w,x)+self.b; return sigmoid(z),z
X=np.load("data/X.npy"); n=Neuron(len(X[0])); out,z=n.forward(X[0])
print(f"Weighted sum: {z:.4f}  After sigmoid: {out:.4f}")
print("Random now - training will make this meaningful.")
xr=np.linspace(-6,6,200); fig,axes=plt.subplots(1,3,figsize=(14,4))
for ax,(nm,fn,c) in zip(axes,[("Sigmoid",sigmoid,"blue"),("ReLU",relu,"red"),("Tanh",tanh_fn,"green")]):
    ax.plot(xr,fn(xr),color=c,linewidth=2.5); ax.set_title(nm); ax.grid(True,alpha=0.3)
plt.tight_layout(); plt.savefig("data/step2_activations.png",dpi=120)
print("Plot: data/step2_activations.png")
print("NEXT: python 3_build_network/neural_network.py")
