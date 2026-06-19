
import numpy as np, matplotlib, os
matplotlib.use("Agg")
import matplotlib.pyplot as plt
NUM_SAMPLES=50; NUM_WAVEFORMS=300; NOISE=0.1
t = np.linspace(0, 2*np.pi, NUM_SAMPLES)
def gen_sine(n):
    return np.array([np.random.uniform(0.8,1.2)*np.sin(t+np.random.uniform(0,np.pi))+np.random.normal(0,NOISE,NUM_SAMPLES) for _ in range(n)])
def gen_square(n):
    return np.array([np.where(np.sin(t)>np.cos(np.random.uniform(0.3,0.7)),1.0,-1.0)+np.random.normal(0,NOISE,NUM_SAMPLES) for _ in range(n)])
def gen_triangle(n):
    return np.array([2*np.abs(((t+np.random.uniform(0,np.pi))/np.pi)%2-1)-1+np.random.normal(0,NOISE,NUM_SAMPLES) for _ in range(n)])
Xs=gen_sine(NUM_WAVEFORMS); Xq=gen_square(NUM_WAVEFORMS); Xt=gen_triangle(NUM_WAVEFORMS)
X=np.vstack([Xs,Xq,Xt]); y=np.array([0]*NUM_WAVEFORMS+[1]*NUM_WAVEFORMS+[2]*NUM_WAVEFORMS)
os.makedirs("data",exist_ok=True); np.save("data/X.npy",X); np.save("data/y.npy",y)
print(f"Dataset: {X.shape} saved. Labels: 0=sine 1=square 2=triangle")
fig,ax=plt.subplots(1,3,figsize=(14,4))
for i,(s,n,c) in enumerate(zip([Xs[0],Xq[0],Xt[0]],["Sine","Square","Triangle"],["blue","red","green"])):
    ax[i].plot(s,color=c,linewidth=2); ax[i].set_title(n); ax[i].grid(True,alpha=0.3)
plt.tight_layout(); plt.savefig("data/step1_signals.png",dpi=120)
print("Plot: data/step1_signals.png")
print("NEXT: python 2_build_neuron/single_neuron.py")
