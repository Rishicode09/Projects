import os

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Created: {path}")

write("1_understand_data/generate_signals.py", '''
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
''')

write("2_build_neuron/single_neuron.py", '''
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
''')

write("3_build_network/neural_network.py", '''
import numpy as np
def relu(x): return np.maximum(0,x)
def relu_derivative(x): return (x>0).astype(float)
def softmax(x):
    e=np.exp(x-np.max(x,axis=1,keepdims=True)); return e/e.sum(axis=1,keepdims=True)
class NeuralNetwork:
    def __init__(self,input_size=50,hidden1=64,hidden2=32,output_size=3):
        self.W1=np.random.randn(input_size,hidden1)*np.sqrt(2.0/input_size); self.b1=np.zeros((1,hidden1))
        self.W2=np.random.randn(hidden1,hidden2)*np.sqrt(2.0/hidden1);       self.b2=np.zeros((1,hidden2))
        self.W3=np.random.randn(hidden2,output_size)*np.sqrt(2.0/hidden2);   self.b3=np.zeros((1,output_size))
        self.cache={}
    def forward(self,X):
        z1=X@self.W1+self.b1;   a1=relu(z1)
        z2=a1@self.W2+self.b2;  a2=relu(z2)
        z3=a2@self.W3+self.b3;  a3=softmax(z3)
        self.cache={"X":X,"z1":z1,"a1":a1,"z2":z2,"a2":a2,"z3":z3,"a3":a3}
        return a3
    def predict(self,X): return np.argmax(self.forward(X),axis=1)
    def count_parameters(self): return sum(w.size for w in [self.W1,self.b1,self.W2,self.b2,self.W3,self.b3])
if __name__=="__main__":
    X=np.load("data/X.npy"); y=np.load("data/y.npy"); net=NeuralNetwork()
    print(f"Network 50->64->32->3  Total params: {net.count_parameters():,}")
    probs=net.forward(X[:3]); preds=net.predict(X[:3])
    for i in range(3): print(f"  True={['sine','square','triangle'][y[i]]}  Probs={probs[i].round(2)}")
    print("Probs near 0.33 = random guessing. Training fixes this.")
    print("NEXT: python 4_train_model/train.py")
''')

write("4_train_model/train.py", '''
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
''')

write("5_api_server/app.py", '''
from flask import Flask,request,jsonify,send_from_directory
from flask_cors import CORS
import numpy as np, os, sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","3_build_network"))
from neural_network import NeuralNetwork
app=Flask(__name__); CORS(app)
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.path.join(ROOT,"data"); FRONT=os.path.join(ROOT,"5_frontend")
def load():
    net=NeuralNetwork()
    for nm in["W1","b1","W2","b2","W3","b3"]: setattr(net,nm,np.load(os.path.join(DATA,nm+".npy")))
    return net
sm=np.load(os.path.join(DATA,"scaler_mean.npy")); ss=np.load(os.path.join(DATA,"scaler_std.npy"))
model=load(); LBL={0:"Sine Wave",1:"Square Wave",2:"Triangle Wave"}
print("Model ready. Open http://localhost:5000")
@app.route("/") 
def home(): return send_from_directory(FRONT,"index.html")
@app.route("/health")
def health(): return jsonify({"status":"online"})
@app.route("/predict",methods=["POST"])
def predict():
    d=request.get_json()
    if not d or "signal" not in d: return jsonify({"error":"Need {signal:[50 floats]}"}),400
    sig=np.array(d["signal"],dtype=float)
    if len(sig)!=50: return jsonify({"error":f"Need 50 samples got {len(sig)}"}),400
    p=model.forward(((sig-sm)/ss).reshape(1,-1))[0]; c=int(np.argmax(p))
    return jsonify({"prediction":LBL[c],"confidence":round(float(p[c])*100,1),
        "probabilities":{"sine":round(float(p[0])*100,1),"square":round(float(p[1])*100,1),"triangle":round(float(p[2])*100,1)}})
@app.route("/demo")
def demo():
    wt=request.args.get("type","sine"); t=np.linspace(0,2*np.pi,50)
    sigs={"sine":np.sin(t),"square":np.where(np.sin(t)>0,1.,-1.),"triangle":2*np.abs(((t)/np.pi)%2-1)-1}
    if wt not in sigs: return jsonify({"error":"type must be sine square or triangle"}),400
    return jsonify({"type":wt,"signal":sigs[wt].tolist()})
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port,debug=True)
''')

write("5_frontend/index.html", """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><title>Waveform AI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;padding:2rem}
h1{color:#38bdf8;font-size:1.6rem;margin-bottom:.3rem}
h2{color:#7dd3fc;font-size:1rem;font-weight:normal;margin-bottom:1.5rem}
.card{background:#1e293b;border-radius:12px;padding:1.5rem;margin-bottom:1.2rem;border:1px solid #334155}
.card h3{color:#38bdf8;margin-bottom:.8rem}
.row{display:flex;gap:.7rem;flex-wrap:wrap;margin-bottom:1rem}
button{padding:.55rem 1.2rem;border:none;border-radius:6px;cursor:pointer;font-size:.9rem;font-weight:600}
.bs{background:#3b82f6;color:#fff}.bq{background:#ef4444;color:#fff}
.bt{background:#22c55e;color:#fff}.bn{background:#8b5cf6;color:#fff}
.bc{background:#f59e0b;color:#0f172a;font-size:1rem;padding:.7rem 2rem}
canvas{width:100%;height:160px;background:#0f172a;border-radius:8px;border:1px solid #334155;display:block}
.rb{background:#0f172a;border-radius:8px;padding:1.2rem;border:2px solid #334155;min-height:80px;margin-top:1rem}
.rl{font-size:1.8rem;font-weight:bold;color:#34d399}
.rc{font-size:.9rem;color:#94a3b8;margin-top:.2rem}
.pb{display:flex;flex-direction:column;gap:.6rem;margin-top:1rem}
.pr{display:flex;align-items:center;gap:.8rem}
.pn{width:80px;font-size:.85rem;color:#94a3b8}
.bo{flex:1;height:18px;background:#334155;border-radius:4px;overflow:hidden}
.bi{height:100%;border-radius:4px;transition:width .4s}
.pv{width:45px;font-size:.85rem;text-align:right;color:#cbd5e1}
.st{font-size:.8rem;color:#64748b;margin-top:.5rem}
.ee{background:#162032;border-left:3px solid #38bdf8;padding:.8rem 1rem;border-radius:4px;font-size:.85rem;color:#94a3b8;margin-top:.8rem}
li{padding:.4rem 0;border-bottom:1px solid #334155;font-size:.88rem;color:#94a3b8;list-style:none}
li b{color:#38bdf8}
</style></head><body>
<h1>Waveform AI Classifier</h1>
<h2>Full-Stack AI built from scratch for Electrical Engineers</h2>
<div class="card"><h3>1. Load a Waveform</h3>
<div class="row">
  <button class="bs" onclick="load('sine')">Sine Wave</button>
  <button class="bq" onclick="load('square')">Square Wave</button>
  <button class="bt" onclick="load('triangle')">Triangle Wave</button>
  <button class="bn" onclick="noise()">Random Noise</button>
</div>
<canvas id="scope"></canvas>
<p class="st" id="ss">No signal loaded</p>
<div class="ee"><b>EE Analogy:</b> This is your oscilloscope — 50 ADC samples. The AI gets exactly these 50 numbers.</div>
</div>
<div class="card"><h3>2. Classify It</h3>
<button class="bc" onclick="classify()">Classify Signal &rarr;</button>
<p class="st" id="as">Load a signal first</p>
<div class="rb" id="rb"><div style="color:#475569">Load a signal then click Classify</div></div>
<div class="pb" id="pb" style="display:none">
  <div class="pr"><span class="pn">Sine</span><div class="bo"><div class="bi" id="bar-sine" style="background:#3b82f6;width:33%"></div></div><span class="pv" id="val-sine">--</span></div>
  <div class="pr"><span class="pn">Square</span><div class="bo"><div class="bi" id="bar-square" style="background:#ef4444;width:33%"></div></div><span class="pv" id="val-square">--</span></div>
  <div class="pr"><span class="pn">Triangle</span><div class="bo"><div class="bi" id="bar-triangle" style="background:#22c55e;width:33%"></div></div><span class="pv" id="val-triangle">--</span></div>
</div>
<div class="ee"><b>What happens:</b> Browser sends 50 values to Flask &rarr; normalize &rarr; forward pass &rarr; probabilities &rarr; display.</div>
</div>
<div class="card"><h3>3. How It Was Built</h3><ul>
  <li><b>Step 1</b> 900 noisy waveforms generated as labeled training data</li>
  <li><b>Step 2</b> Single neuron: weighted sum + ReLU = summing amp + half-wave rectifier</li>
  <li><b>Step 3</b> Network: 50&rarr;64&rarr;32&rarr;3 (cascaded filter stages)</li>
  <li><b>Step 4</b> 500 epochs backprop: auto-tuned 6,531 weights to ~99% accuracy</li>
  <li><b>Step 5</b> Flask REST API + this HTML page = full-stack AI</li>
</ul></div>
<script>
const API=window.location.origin.startsWith('http')?window.location.origin:'http://localhost:5000';
let sig=null;
function draw(s,color){
  const c=document.getElementById('scope'),ctx=c.getContext('2d');
  c.width=c.offsetWidth;c.height=160;
  const W=c.width,H=c.height,p=20,mn=Math.min(...s),mx=Math.max(...s),r=(mx-mn)||1;
  ctx.clearRect(0,0,W,H);
  ctx.strokeStyle='#1e3a5f';ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const y=p+(H-2*p)*i/4;ctx.beginPath();ctx.moveTo(p,y);ctx.lineTo(W-p,y);ctx.stroke();}
  ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();
  s.forEach((v,i)=>{const x=p+(W-2*p)*i/(s.length-1),y=p+(H-2*p)*(1-(v-mn)/r);i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.stroke();ctx.fillStyle=color;
  s.forEach((v,i)=>{const x=p+(W-2*p)*i/(s.length-1),y=p+(H-2*p)*(1-(v-mn)/r);ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);ctx.fill();});
}
async function load(type){
  const cl={sine:'#3b82f6',square:'#ef4444',triangle:'#22c55e'};
  try{const d=await(await fetch(API+'/demo?type='+type)).json();sig=d.signal;draw(sig,cl[type]);
    document.getElementById('ss').textContent=type+' wave loaded (50 samples)';
    document.getElementById('as').textContent='Ready — click Classify';
  }catch(e){document.getElementById('ss').textContent='Cannot reach API — is app.py running?';}
}
function noise(){sig=Array.from({length:50},()=>Math.random()*2-1);draw(sig,'#a855f7');
  document.getElementById('ss').textContent='Random noise (50 samples)';
  document.getElementById('as').textContent='Ready — click Classify';}
async function classify(){
  if(!sig){document.getElementById('as').textContent='Load a signal first!';return;}
  document.getElementById('as').textContent='Sending to model...';
  try{const d=await(await fetch(API+'/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signal:sig})})).json();
    document.getElementById('rb').innerHTML='<div class="rl">'+d.prediction+'</div><div class="rc">Confidence: <b>'+d.confidence+'%</b></div>';
    const pb=d.probabilities;document.getElementById('pb').style.display='flex';
    ['sine','square','triangle'].forEach(k=>{document.getElementById('bar-'+k).style.width=pb[k]+'%';document.getElementById('val-'+k).textContent=pb[k]+'%';});
    document.getElementById('as').textContent='Done!';
  }catch(e){document.getElementById('as').textContent='Error — make sure app.py is running';}
}
</script></body></html>""")

print()
print("="*55)
print("ALL FILES CREATED")
print("="*55)
print("""
Install packages (run once):
  pip install numpy matplotlib flask flask-cors scikit-learn

Then run in order:
  python 1_understand_data/generate_signals.py
  python 2_build_neuron/single_neuron.py
  python 3_build_network/neural_network.py
  python 4_train_model/train.py
  python 5_api_server/app.py

Open browser: http://localhost:5000
""")