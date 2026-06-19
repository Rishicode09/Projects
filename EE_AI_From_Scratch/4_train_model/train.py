
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","3_build_network"))
from neural_network import NeuralNetwork, relu_derivative
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
X=np.load("data/X.npy"); y=np.load("data/y.npy")
sc=StandardScaler(); X=sc.fit_transform(X)
Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)
def one_hot(y,n=3):
    r=np.zeros((len(y),n)); r[np.arange(len(y)),y]=1; return r
Ytr=one_hot(ytr); Yte=one_hot(yte)
def loss(p,t): return -np.mean(np.sum(t*np.log(p+1e-15),axis=1))
def backward(net,Yt,lr):
    m=Yt.shape[0]; X,z1,a1,z2,a2,a3=(net.cache[k] for k in["X","z1","a1","z2","a2","a3"])
    dz3=a3-Yt; dW3=a2.T@dz3/m; db3=np.mean(dz3,axis=0,keepdims=True)
    dz2=(dz3@net.W3.T)*relu_derivative(net.cache["z2"]); dW2=a1.T@dz2/m; db2=np.mean(dz2,axis=0,keepdims=True)
    dz1=(dz2@net.W2.T)*relu_derivative(z1); dW1=X.T@dz1/m; db1=np.mean(dz1,axis=0,keepdims=True)
    for p,g in [(net.W3,dW3),(net.b3,db3),(net.W2,dW2),(net.b2,db2),(net.W1,dW1),(net.b1,db1)]: p-=lr*g
def acc(net,X,y): return np.mean(net.predict(X)==y)
net=NeuralNetwork(); losses=[]; accs=[]
print(f"{'Epoch':<8}{'Loss':<12}{'TrainAcc':<14}{'TestAcc'}")
for ep in range(500):
    idx=np.random.permutation(len(Xtr)); ls=0; nb=0
    for s in range(0,len(Xtr),32):
        Xb=Xtr[idx[s:s+32]]; Yb=Ytr[idx[s:s+32]]
        ls+=loss(net.forward(Xb),Yb); nb+=1; backward(net,Yb,0.005)
    avg=ls/nb; va=acc(net,Xte,yte); losses.append(avg); accs.append(va)
    if ep%50==0 or ep==499: print(f"{ep:<8}{avg:<12.4f}{acc(net,Xtr,ytr):<14.1%}{va:.1%}")
print(f"FINAL TEST ACCURACY: {acc(net,Xte,yte):.1%}")
for nm,w in[("W1",net.W1),("b1",net.b1),("W2",net.W2),("b2",net.b2),("W3",net.W3),("b3",net.b3)]:
    np.save(f"data/{nm}.npy",w)
np.save("data/scaler_mean.npy",sc.mean_); np.save("data/scaler_std.npy",sc.scale_)
print("Weights saved. NEXT: python 5_api_server/app.py")
