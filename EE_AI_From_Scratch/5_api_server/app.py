
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
