// ── STORIES ───────────────────────────────────────────────────────────────────
const STORIES = {
  pigs: {
    title:'Three Little Pigs', author:'Traditional', icon:'🐷',
    text:`Once upon a time there were three little pigs who lived with their mother in a cosy cottage. One day their mother called them together and said it was time for them to go out into the world and build homes of their own. The first little pig was the laziest of all. He met a man carrying a bundle of straw and bought it on the spot. He threw up four walls and a roof in less than an hour and spent the rest of the day napping. The second little pig was a little more industrious. He found a man selling sticks and used them to build a tidy house with a proper door and two windows. The third little pig was the hardest worker of them all. He searched until he found a merchant selling bricks and spent many long days laying them one by one until his house stood strong and solid with a real fireplace and a chimney on top. One autumn evening a big bad wolf came prowling through the forest with his belly growling. He came to the house of straw and knocked on the door. Little pig, little pig, let me come in, he called. Not by the hair of my chinny chin chin, squealed the first pig. Then I will huff and I will puff and I will blow your house in, roared the wolf. And he huffed and he puffed and down came the house of straw. The first pig bolted to his brother's house of sticks. So the wolf huffed and he puffed and blew the house of sticks to pieces. Both pigs ran as fast as their little legs would carry them to their brother's house of bricks. The wolf arrived, furious and out of breath, and pounded on the solid door. He huffed and he puffed until his face turned red but the brick house did not move an inch. Enraged, the wolf decided to climb down the chimney. But the third little pig was clever. He had a great pot of boiling water bubbling in the fireplace. The wolf tumbled down the chimney and landed in the pot with a tremendous splash. He yelped, scrambled out the door, and was never seen in those parts again. The three little pigs lived safely ever after in the house of bricks.`
  },
  gatsby: {
    title:'The Great Gatsby', author:'F. Scott Fitzgerald, 1925', icon:'🥂',
    text:`In my younger and more vulnerable years my father gave me some advice that I have been turning over in my mind ever since. Whenever you feel like criticizing anyone, he told me, just remember that all the people in this world have not had the advantages that you have had. He did not say any more, but we have always been unusually communicative in a reserved way, and I understood that he meant a great deal more than that. In consequence, I am inclined to reserve all judgments, a habit that has opened up many curious natures to me and also made me the victim of not a few veteran bores. The abnormal mind is quick to detect and attach itself to this quality when it appears in a normal person, and so it came about that in college I was unjustly accused of being a politician, because I was privy to the secret griefs of wild, unknown men. Most of the confidences were unsought, and I have often feigned sleep or a hostile levity when I realized that an intimate revelation was quivering on the horizon. Reserving judgments is a matter of infinite hope. I was rather literary in college, and now I am going to write something very romantic and terrible at the same time.`
  },
  jekyll: {
    title:'Jekyll and Hyde', author:'R. L. Stevenson, 1886', icon:'🧪',
    text:`Mr Utterson the lawyer was a man of a rugged countenance that was never lighted by a smile. He was cold, scanty and embarrassed in discourse, backward in sentiment, lean, long, dusty and dreary. And yet somehow he was lovable. At friendly meetings, and when the wine was to his taste, something eminently human beaconed from his eye. Something of a kindly spirit glowed in his manner that never found its way into his talk. He was austere with himself, and drank gin when he was alone to mortify a taste for vintages. He had an approved tolerance for others, sometimes wondering, almost with envy, at the high pressure of spirits involved in their misdeeds. In this character it was frequently his fortune to be the last reputable acquaintance and the last good influence in the lives of downgoing men. It is the mark of a modest man to accept his friendly circle ready made from the hands of opportunity, and that was the lawyer's way. His friends were those of his own blood, or those whom he had known the longest. His affections, like ivy, were the growth of time.`
  },
  alice: {
    title:'Alice in Wonderland', author:'Lewis Carroll, 1865', icon:'🐇',
    text:`Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do. Once or twice she had peeped into the book her sister was reading, but it had no pictures or conversations in it. And what is the use of a book, thought Alice, without pictures or conversations? So she was considering in her own mind whether the pleasure of making a daisy chain would be worth the trouble of getting up and picking the daisies, when suddenly a white rabbit with pink eyes ran close by her. There was nothing so very remarkable in that. Nor did Alice think it so very much out of the way to hear the rabbit say to itself, oh dear, oh dear, I shall be too late. But when the rabbit actually took a watch out of its waistcoat pocket, and looked at it, and then hurried on, Alice started to her feet. Burning with curiosity, she ran across the field after it, and was just in time to see it pop down a large rabbit hole under the hedge. In another moment down went Alice after it, never once considering how in the world she was to get out again.`
  },
  holmes: {
    title:'Sherlock Holmes', author:'Arthur Conan Doyle, 1887', icon:'🔍',
    text:`In the year 1878 I took my degree of Doctor of Medicine of the University of London, and proceeded to go through the course prescribed for surgeons in the army. Having completed my studies there, I was duly attached to the Fifth Northumberland Fusiliers as assistant surgeon. The regiment had barely reached India before the second Afghan war broke out. I followed with many other officers who were in the same situation as myself, and succeeded in reaching Candahar in safety, where I found my regiment and at once entered upon my duties. The campaign brought honours and promotion to many, but for me it had nothing but misfortune and disaster. I was struck on the shoulder by a bullet which shattered the bone and grazed the artery. I should have fallen into the hands of the murderous enemy had it not been for the devotion and courage shown by Murray, my orderly, who threw me across a pack horse and succeeded in bringing me safely to the British lines. Worn with pain, and weak from the prolonged hardships which I had undergone, I was removed with a great train of wounded sufferers to the base hospital at Peshawar.`
  },
};

// ── WORD LISTS (FREE MODE) ──────────────────────────────────────────────────────
const EASY_WORDS = `the be to of and a in that have it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us`.split(' ');

const MEDIUM_WORDS = [
  ...EASY_WORDS.map((w,i)=>i%5===0?w[0].toUpperCase()+w.slice(1):w),
  ...'She said nothing but smiled slowly He walked away without looking back The door creaked open in the silence They found the answer hidden in plain sight Every morning brings a chance to begin Nothing moved except the curtains in the wind'.split(' ')
];

const HARD_WORDS = [
  'acquiesce','ambiguous','anachronism','anecdote','annihilate',
  'anonymous','antithesis','apparatus','arbitrary','archipelago',
  'arduous','aristocratic','assiduous','atrocious','audacious',
  'belligerent','benevolent','bibliography','bureaucracy','cacophony',
  'camaraderie','catastrophic','charismatic','circumlocution','clandestine',
  'colloquial','colossal','commemorate','compassionate','conscientious',
  'conspicuous','contemptuous','contentious','controversial','convivial',
  'corroborate','cumbersome','deferential','deleterious','demagogue',
  'desiccated','despondent','dilapidated','diligent','discernible',
  'dissonance','duplicitous','eccentric','eloquent','embellishment',
  'ephemeral','equivocal','exacerbate','exasperated','exuberant',
  'facetious','fallacious','fastidious','ferocious','flabbergasted',
  'flourishing','fortuitous','fraudulent','gregarious','grotesque',
  'harrowing','heinous','hierarchy','hypocritical','idiosyncratic',
  'ignominious','illusory','immaculate','impeccable','imperceptible',
  'implausible','incorrigible','indisputable','ineffable','inevitable',
  'inquisitive','inscrutable','insidious','insurmountable','integrity',
  'intermittent','labyrinthine','lachrymose','languorous','lethargic',
  'liaison','lugubrious','magnanimous','malevolent','malicious',
  'melancholy','meticulous','millennium','miscellaneous','mnemonic',
  'munificent','mysterious','nefarious','obstreperous','ominous',
  'onomatopoeia','oppressive','ostentatious','overwhelmed','painstaking',
  'pandemonium','paradoxical','passionate','pejorative','pernicious',
  'perseverance','perspicacious','philanthropy','picturesque','preposterous',
  'pretentious','procrastinate','prodigious','proficient','prophecy',
  'punctilious','quarrelsome','querulous','quintessential','rambunctious',
  'rapturous','recalcitrant','relentless','reminiscent','reprehensible',
  'resilient','righteous','scrupulous','serendipitous','silhouette',
  'simultaneous','soliloquy','sophisticated','spontaneous','supercilious',
  'surreptitious','susceptible','temperamental','treacherous','tumultuous',
  'ubiquitous','unconscionable','unequivocal','unprecedented','vacillate',
  'vehement','venomous','vicarious','vivacious','vulnerability','whimsical','zealous',
];

function getWordList(diff) {
  return diff==='easy'?EASY_WORDS:diff==='medium'?MEDIUM_WORDS:HARD_WORDS;
}

// ── STATE ─────────────────────────────────────────────────────────────────────
const S = {
  screen:'menu', gameMode:'free', storyId:'pigs',
  duration:15, difficulty:'easy',
  soundOn:true, theme:'dark',
  useNumbers:false, usePunctuation:false, stopOnError:false,

  started:false, finished:false,
  timeLeft:15, timerId:null,
  words:[], wordIndex:0, charIndex:0,
  typedChars:[], submittedWords:[],
  correctChars:0, rawChars:0, totalTyped:0,
  combo:0, maxCombo:0, score:0,
  wpmSamples:[], perKeyErrors:{},
  afkTimer:null, afkPaused:false,

  // story mode
  fullText:'', pos:0, elapsed:0, startTime:0, pauseAt:0,
  raceIdx:{}, raceTime:0, _curEl:null, _lastSample:0,

  // persisted
  xp:0, level:1, bests:{}, achievements:{}, totalRuns:0,
  history:[], // [{wpm,acc,ts}] last 20 runs
};

function loadPersisted() {
  try {
    const d = JSON.parse(localStorage.getItem('typerush2')||'{}');
    'xp level bests achievements totalRuns history soundOn theme useNumbers usePunctuation stopOnError'
      .split(' ').forEach(k=>{ if(d[k]!==undefined) S[k]=d[k]; });
    if(!S.history) S.history=[];
  } catch(e){}
}
function savePersisted() {
  try {
    localStorage.setItem('typerush2', JSON.stringify({
      xp:S.xp, level:S.level, bests:S.bests,
      achievements:S.achievements, totalRuns:S.totalRuns, history:S.history,
      soundOn:S.soundOn, theme:S.theme,
      useNumbers:S.useNumbers, usePunctuation:S.usePunctuation, stopOnError:S.stopOnError,
    }));
  } catch(e){}
}

// ── AUDIO ─────────────────────────────────────────────────────────────────────
let _actx=null;
function actx(){if(!_actx)_actx=new(window.AudioContext||window.webkitAudioContext)();return _actx;}
function playClick(type='key'){
  if(!S.soundOn) return;
  try{
    if(type==='levelup'){
      [500,650,820].forEach((f,i)=>{
        const o=actx().createOscillator(),g=actx().createGain();
        o.connect(g);g.connect(actx().destination);
        o.frequency.value=f; o.start(actx().currentTime+i*.1); o.stop(actx().currentTime+i*.1+.15);
        g.gain.setValueAtTime(.07,actx().currentTime+i*.1);
        g.gain.exponentialRampToValueAtTime(.001,actx().currentTime+i*.1+.15);
      }); return;
    }
    const o=actx().createOscillator(),g=actx().createGain();
    o.connect(g);g.connect(actx().destination);
    const c={key:{f:580,t:'sine',v:.05,d:.05},error:{f:200,t:'sawtooth',v:.07,d:.1},word:{f:880,t:'sine',v:.04,d:.07}}[type]||{f:580,t:'sine',v:.05,d:.05};
    o.frequency.value=c.f;o.type=c.t;
    g.gain.setValueAtTime(c.v,actx().currentTime);
    g.gain.exponentialRampToValueAtTime(.001,actx().currentTime+c.d);
    o.start(actx().currentTime);o.stop(actx().currentTime+c.d);
  }catch(e){}
}

// ── BG ORBS ───────────────────────────────────────────────────────────────────
const bgC=document.getElementById('bg-canvas'),bgX=bgC.getContext('2d');
let orbs=[];
function resizeBg(){bgC.width=innerWidth;bgC.height=innerHeight;}
window.addEventListener('resize',resizeBg);resizeBg();
function initOrbs(){orbs=Array.from({length:18},()=>({x:Math.random()*innerWidth,y:Math.random()*innerHeight,vx:(Math.random()-.5)*.4,vy:(Math.random()-.5)*.4,r:80+Math.random()*130,op:.05+Math.random()*.09,ci:Math.floor(Math.random()*3),ph:Math.random()*Math.PI*2,ps:.005+Math.random()*.01}));}
initOrbs();
function drawOrbs(){
  bgX.clearRect(0,0,bgC.width,bgC.height);
  const dk=document.body.dataset.theme==='dark';
  const cl=dk?['168,124,255','255,107,157','78,204,163']:['96,64,176','208,64,128','26,154,112'];
  orbs.forEach(o=>{
    o.x+=o.vx;o.y+=o.vy;o.ph+=o.ps;
    if(o.x<-o.r)o.x=bgC.width+o.r;if(o.x>bgC.width+o.r)o.x=-o.r;
    if(o.y<-o.r)o.y=bgC.height+o.r;if(o.y>bgC.height+o.r)o.y=-o.r;
    const r=o.r*(1+.12*Math.sin(o.ph));
    const g=bgX.createRadialGradient(o.x,o.y,0,o.x,o.y,r);
    g.addColorStop(0,`rgba(${cl[o.ci]},${o.op})`);g.addColorStop(1,`rgba(${cl[o.ci]},0)`);
    bgX.beginPath();bgX.arc(o.x,o.y,r,0,Math.PI*2);bgX.fillStyle=g;bgX.fill();
  });
}

// ── PARTICLES ─────────────────────────────────────────────────────────────────
const pC=document.getElementById('particle-canvas'),pX=pC.getContext('2d');
let parts=[];
function resizeP(){pC.width=innerWidth;pC.height=innerHeight;}
window.addEventListener('resize',resizeP);resizeP();
function spawnParts(x,y,col){
  for(let i=0;i<12;i++){const a=Math.random()*Math.PI*2,s=2+Math.random()*4;parts.push({x,y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,life:1,decay:.03+Math.random()*.04,r:3+Math.random()*3,col});}
}
function frame(){
  drawOrbs();
  pX.clearRect(0,0,pC.width,pC.height);
  parts=parts.filter(p=>p.life>0);
  parts.forEach(p=>{p.x+=p.vx;p.y+=p.vy;p.vy+=.15;p.life-=p.decay;pX.globalAlpha=p.life;pX.fillStyle=p.col;pX.beginPath();pX.arc(p.x,p.y,p.r*p.life,0,Math.PI*2);pX.fill();});
  pX.globalAlpha=1;
  requestAnimationFrame(frame);
}
frame();

// ── TOASTS ────────────────────────────────────────────────────────────────────
const toastArea=document.getElementById('toast-area');
function toast(icon,title,sub=''){
  const el=document.createElement('div');el.className='toast';
  el.innerHTML=`<span class="toast-icon">${icon}</span><div><div class="toast-title">${title}</div>${sub?`<div class="toast-sub">${sub}</div>`:''}</div>`;
  toastArea.appendChild(el);setTimeout(()=>el.remove(),3200);
}

// ── SCREENS ───────────────────────────────────────────────────────────────────
function showScreen(name){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  document.getElementById(name+'-screen').classList.add('active');
  S.screen=name;
}
function quitToMenu(){
  clearInterval(S.timerId);S.timerId=null;
  clearTimeout(S.afkTimer);
  S.afkPaused=false;
  showScreen('menu');refreshMenu();
}

// ── LEVEL / XP ────────────────────────────────────────────────────────────────
function xpFor(lvl){return lvl*200;}
function awardXP(n){
  S.xp+=n;let up=false;
  while(S.xp>=xpFor(S.level)){S.xp-=xpFor(S.level);S.level++;up=true;}
  if(up){
    playClick('levelup');
    toast('⚡',`Level Up! Now Level ${S.level}`,'Keep going!');
    const f=document.getElementById('levelup-flash');
    f.classList.add('show');setTimeout(()=>f.classList.remove('show'),600);
  }
  updateLevelBar();savePersisted();
}
function updateLevelBar(){
  const n=xpFor(S.level);
  document.getElementById('level-label').textContent=`Lvl ${S.level}`;
  document.getElementById('level-fill').style.width=Math.min(100,(S.xp/n)*100)+'%';
  document.getElementById('xp-label').textContent=`${S.xp}/${n} XP`;
}

// ── ACHIEVEMENTS ──────────────────────────────────────────────────────────────
const ACHIEVEMENTS=[
  {id:'first_run',icon:'🚀',title:'First Run!',sub:'Completed your first test.',check:(s,r)=>s.totalRuns===1},
  {id:'wpm40',icon:'🏃',title:'40 WPM Club',sub:'Hit 40+ WPM.',check:(s,r)=>r.wpm>=40},
  {id:'wpm60',icon:'💨',title:'60 WPM Speedster',sub:'Hit 60+ WPM.',check:(s,r)=>r.wpm>=60},
  {id:'wpm80',icon:'🚀',title:'80 WPM Blazer',sub:'Hit 80+ WPM.',check:(s,r)=>r.wpm>=80},
  {id:'wpm100',icon:'⚡',title:'100 WPM Legend',sub:'Hit 100+ WPM.',check:(s,r)=>r.wpm>=100},
  {id:'perfect',icon:'💎',title:'Perfect Accuracy',sub:'100% accuracy run.',check:(s,r)=>r.accuracy===100},
  {id:'combo25',icon:'🔥',title:'On Fire! 25×',sub:'25 in a row.',check:(s,r)=>r.maxCombo>=25},
  {id:'combo50',icon:'🌋',title:'Unstoppable! 50×',sub:'50 in a row.',check:(s,r)=>r.maxCombo>=50},
  {id:'story1',icon:'📖',title:'Storyteller',sub:'Finished a story passage.',check:(s,r)=>r.isStory},
  {id:'runs10',icon:'🎯',title:'10 Runs Done',sub:'10 tests completed.',check:(s,r)=>s.totalRuns>=10},
  {id:'runs50',icon:'🏆',title:'50 Runs Veteran',sub:'50 tests completed.',check:(s,r)=>s.totalRuns>=50},
];
function checkAchievements(results){
  ACHIEVEMENTS.forEach(a=>{
    if(!S.achievements[a.id]&&a.check(S,results)){
      S.achievements[a.id]=true;
      setTimeout(()=>toast(a.icon,a.title,a.sub),700);
    }
  });
}

// ── WORD GENERATION (FREE MODE) ─────────────────────────────────────────────────
function generateWords(count,recentSeed=[]){
  const list=getWordList(S.difficulty);
  const words=[],ws=Math.min(8,Math.floor(list.length/2));
  const recent=recentSeed.slice(-ws);
  for(let i=0;i<count;i++){
    let base,att=0;
    do{base=list[Math.floor(Math.random()*list.length)];att++;}
    while(recent.includes(base)&&att<30);
    let word=base;
    if(S.useNumbers&&Math.random()<.12) word=String(Math.floor(Math.random()*900)+100);
    else if(S.usePunctuation&&Math.random()<.28) word=base+(Math.random()<.6?',':'.');
    words.push(word);recent.push(base);if(recent.length>ws)recent.shift();
  }
  return words;
}

// ── STORY RACES (TYPERACER STYLE) ───────────────────────────────────────────────
// Split a story into sentence-complete excerpts (~260 chars) so each race
// reads as grammatically complete, coherent prose.
const ABBREV=/\b(Mr|Mrs|Ms|Dr|St|Jr|Sr|vs|etc)\.$/;
function splitSentences(text){
  const raw=text.match(/[^.!?]+[.!?]+(?:\s|$)/g)||[text];
  const out=[];
  raw.forEach(s=>{
    s=s.trim();if(!s)return;
    if(out.length&&ABBREV.test(out[out.length-1])) out[out.length-1]+=' '+s;
    else out.push(s);
  });
  return out;
}
function getStoryRaces(id){
  const st=STORIES[id];
  if(st._races) return st._races;
  const sents=splitSentences(st.text);
  const races=[];let cur='';
  sents.forEach(s=>{
    if(cur && (cur.length+1+s.length)>260){races.push(cur);cur=s;}
    else cur=cur?cur+' '+s:s;
  });
  if(cur)races.push(cur);
  st._races=races;return races;
}
function getStoryRace(id){
  const races=getStoryRaces(id);
  const i=(S.raceIdx[id]||0)%races.length;
  S.raceIdx[id]=i+1;
  return races[i];
}

// ── WORD DOM (FREE MODE) ────────────────────────────────────────────────────────
const wContainer=document.getElementById('words-container');
const wordArea=document.getElementById('word-area');
const storyArea=document.getElementById('story-area');
const storyTextEl=document.getElementById('story-text');
const hiddenInput=document.getElementById('hidden-input');

function makeWordEl(word,wi){
  const el=document.createElement('span');el.className='word';el.dataset.wi=wi;
  word.split('').forEach(ch=>{const s=document.createElement('span');s.className='char';s.textContent=ch;el.appendChild(s);});
  return el;
}
function buildWordDom(){
  wContainer.innerHTML='';
  S.words.forEach((w,i)=>wContainer.appendChild(makeWordEl(w,i)));
  // Keep the smooth caret INSIDE the words container so its coordinates are
  // measured against the same (transformed) box and it scrolls with the words.
  const sc=document.getElementById('smooth-caret');
  if(sc) wContainer.appendChild(sc);
}
function getWordEl(wi){return wContainer.querySelector(`.word[data-wi="${wi}"]`);}

// ── 3-ROW SCROLL (FREE MODE) ────────────────────────────────────────────────────
function getRowH(){
  for(const w of wContainer.querySelectorAll('.word')){if(w.offsetTop>0)return w.offsetTop;}
  return null;
}
function scrollWords(){
  const el=getWordEl(S.wordIndex);if(!el)return;
  const lh=getRowH();if(!lh)return;
  const row=Math.round(el.offsetTop/lh);
  const scroll=Math.max(0,row-1)*lh;
  wContainer.style.transform=`translateY(-${scroll}px)`;
  updateRowHighlight(row,lh,scroll);
}
function updateRowHighlight(currentRow,lineH,scrolled){
  const hl=document.getElementById('row-highlight');
  if(!hl||!lineH)return;
  const visRow=(currentRow===undefined)?0:currentRow-Math.max(0,currentRow-1);
  const pad=20;
  hl.style.top=(pad+visRow*lineH)+'px';
  hl.style.height=lineH+'px';
}

// ── SMOOTH CARET (FREE MODE) ─────────────────────────────────────────────────────
function updateCaret(){
  const caret=document.getElementById('smooth-caret');
  if(!caret||S.screen!=='game'||S.gameMode!=='free') return;
  const wordEl=getWordEl(S.wordIndex);
  if(!wordEl){caret.style.opacity='0';return;}
  const chars=wordEl.querySelectorAll('.char');
  const target=chars[S.charIndex]||(chars.length?chars[chars.length-1]:null);
  if(!target){caret.style.opacity='0';return;}
  caret.style.opacity='1';
  const cr=wContainer.getBoundingClientRect();
  const tr=target.getBoundingClientRect();
  const leftOff=chars[S.charIndex]?0:tr.width;
  caret.style.left=(tr.left-cr.left+leftOff)+'px';
  caret.style.top=(tr.top-cr.top)+'px';
  caret.style.height=tr.height+'px';
}

// ── STORY DOM (STORY MODE) ───────────────────────────────────────────────────────
let storyCharEls=[];
function buildStoryDom(){
  storyTextEl.innerHTML='';
  storyCharEls=[];
  const frag=document.createDocumentFragment();
  for(const ch of S.fullText){
    const sp=document.createElement('span');sp.className='char';sp.textContent=ch;
    frag.appendChild(sp);storyCharEls.push(sp);
  }
  storyTextEl.appendChild(frag);
  storyTextEl.scrollTop=0;
}
function setStoryCurrent(){
  if(S._curEl)S._curEl.classList.remove('current');
  const el=storyCharEls[S.pos];
  if(el){el.classList.add('current');S._curEl=el;scrollStory(el);}
  else S._curEl=null;
}
function scrollStory(el){
  const top=el.offsetTop;
  if(top<storyTextEl.scrollTop+20 || top>storyTextEl.scrollTop+storyTextEl.clientHeight-44){
    storyTextEl.scrollTop=Math.max(0,top-storyTextEl.clientHeight/2+el.offsetHeight/2);
  }
}
function updateProgress(){
  const len=S.fullText?S.fullText.length:1;
  const frac=Math.min(1,S.pos/len);
  document.getElementById('story-progress-fill').style.width=(frac*100)+'%';
  document.getElementById('story-progress-pct').textContent=Math.round(frac*100)+'%';
  setProgressRing(frac);
}

// ── AFK ───────────────────────────────────────────────────────────────────────
function resetAfk(){
  clearTimeout(S.afkTimer);
  if(S.afkPaused){resumeAfk();return;}
  if(S.started&&!S.finished){
    S.afkTimer=setTimeout(()=>{
      S.afkPaused=true;
      if(S.gameMode==='story') S.pauseAt=performance.now();
      else clearInterval(S.timerId);
      showOverlay('💤','AFK — click to resume');
    },6000);
  }
}
function resumeAfk(){
  if(!S.afkPaused)return;
  S.afkPaused=false;hideOverlay();
  if(S.gameMode==='story') S.startTime+=performance.now()-S.pauseAt;
  else S.timerId=setInterval(timerTick,1000);
}
function showOverlay(icon,text){
  document.querySelectorAll('.fo-icon').forEach(e=>e.textContent=icon);
  document.querySelectorAll('.fo-text').forEach(e=>e.textContent=text);
  document.querySelectorAll('.focus-overlay').forEach(e=>e.classList.add('visible'));
}
function hideOverlay(){document.querySelectorAll('.focus-overlay').forEach(e=>e.classList.remove('visible'));}

// ── GAME FLOW ─────────────────────────────────────────────────────────────────
function initGame(){
  S.started=false;S.finished=false;
  S.wordIndex=0;S.charIndex=0;S.pos=0;
  S.typedChars=Array(2000).fill('');
  S.submittedWords=[];
  S.correctChars=0;S.rawChars=0;S.totalTyped=0;
  S.combo=0;S.maxCombo=0;S.score=0;
  S.wpmSamples=[];S.perKeyErrors={};
  S.elapsed=0;S._curEl=null;S._lastSample=0;
  S.afkPaused=false;clearTimeout(S.afkTimer);
  clearInterval(S.timerId);S.timerId=null;

  const comboArea=document.getElementById('combo-area');
  document.getElementById('caps-notice').classList.remove('visible');

  if(S.gameMode==='story'){
    S.fullText=getStoryRace(S.storyId);
    buildStoryDom();
    wordArea.classList.remove('active');
    storyArea.classList.add('active');
    comboArea.style.display='none';
    document.getElementById('strict-notice').classList.remove('visible');
    const st=STORIES[S.storyId];
    document.getElementById('story-name').textContent=`${st.icon} ${st.title} — ${st.author}`;
    document.getElementById('timer-label').textContent='elapsed';
    updateProgress();
    document.getElementById('timer-text').textContent='0';
    setStoryCurrent();
    updateStoryHUD();
  } else {
    S.timeLeft=S.duration;
    S.words=generateWords(200);
    buildWordDom();
    wContainer.style.transform='';
    storyArea.classList.remove('active');
    wordArea.classList.add('active');
    comboArea.style.display='';
    document.getElementById('timer-label').textContent='time left';
    setTimeout(()=>{const lh=getRowH();updateRowHighlight(1,lh||40,0);},50);
    updateHUD();updateCombo();
    setTimerRing(S.duration,S.duration);
    document.getElementById('timer-text').textContent=S.duration;
    document.getElementById('strict-notice').classList.toggle('visible',S.stopOnError);
    const caret=document.getElementById('smooth-caret');
    if(caret){caret.classList.add('instant');caret.style.opacity='0';setTimeout(()=>caret.classList.remove('instant'),50);}
  }

  const live=document.getElementById('game-live');
  const res=document.getElementById('game-results');
  live.classList.remove('fading');live.style.display='';
  res.classList.remove('show');
  document.querySelectorAll('.word.strict-error').forEach(e=>e.classList.remove('strict-error'));

  hiddenInput.value='';hiddenInput.focus();
  wordArea.classList.remove('glow','shake');
  storyTextEl.classList.remove('shake');
  hideOverlay();
}

// FREE MODE countdown
function timerTick(){
  S.timeLeft--;
  updateHUD();
  setTimerRing(S.timeLeft,S.duration);
  if(S.timeLeft>0){
    const el=S.duration-S.timeLeft;
    const wpm=Math.round((S.correctChars/5)/(el/60));
    S.wpmSamples.push({t:el,wpm});
  }
  if(S.timeLeft<=0)endGame();
}
function startTimer(){
  S.started=true;
  S.timerId=setInterval(timerTick,1000);
  resetAfk();
}

// STORY MODE count-up
function startStoryTimer(){
  S.started=true;
  S.startTime=performance.now();
  S._lastSample=0;
  S.timerId=setInterval(()=>{
    if(S.afkPaused)return;
    S.elapsed=(performance.now()-S.startTime)/1000;
    updateStoryHUD();
    if(S.elapsed-S._lastSample>=1){
      S._lastSample=S.elapsed;
      const wpm=Math.round((S.correctChars/5)/(S.elapsed/60))||0;
      S.wpmSamples.push({t:S.elapsed,wpm});
    }
  },150);
  resetAfk();
}

function endGame(){
  if(S.finished)return;
  clearInterval(S.timerId);S.timerId=null;
  clearTimeout(S.afkTimer);
  S.finished=true;
  const isStory=S.gameMode==='story';
  const elapsed=isStory?Math.max(S.elapsed,0.001):S.duration;
  const min=elapsed/60;
  const wpm=Math.round((S.correctChars/5)/min);
  const rawWpm=Math.round((S.rawChars/5)/min);
  const accuracy=S.totalTyped>0?Math.round((S.correctChars/S.totalTyped)*100):100;
  const bestKey=isStory?`story-${S.storyId}`:`${S.duration}-${S.difficulty}`;
  const isNew=!S.bests[bestKey]||wpm>S.bests[bestKey].wpm;
  if(isNew) S.bests[bestKey]={wpm,acc:accuracy,score:S.score};
  S.totalRuns++;
  S.history.unshift({wpm,acc:accuracy,ts:Date.now()});
  if(S.history.length>20)S.history.pop();
  S.raceTime=elapsed;
  const xpGained=Math.round(S.score/10)+wpm*2;
  awardXP(xpGained);
  checkAchievements({wpm,accuracy,maxCombo:S.maxCombo,isStory});
  savePersisted();
  showResultsInline({wpm,rawWpm,accuracy,isNew,xpGained,elapsed,isStory});
}

// ── INPUT ─────────────────────────────────────────────────────────────────────
hiddenInput.addEventListener('keydown',e=>{
  if(S.finished)return;
  if(e.key==='Tab'){e.preventDefault();initGame();return;}
  if(e.key==='Escape'){e.preventDefault();quitToMenu();return;}

  // Caps lock badge
  const caps=e.getModifierState&&e.getModifierState('CapsLock');
  document.getElementById('caps-notice').classList.toggle('visible',!!caps);

  if(S.gameMode==='story'){handleStoryKey(e);return;}

  // FREE MODE: once a word is submitted it's locked — block backspacing into a
  // previous word (you can still fix the word you're currently typing).
  if(e.key==='Backspace'&&hiddenInput.value===''&&S.started){
    e.preventDefault();
    return;
  }

  if(!S.started&&e.key.length===1){startTimer();}
  resetAfk();
});

// STORY MODE key handling — TypeRacer-style char-by-char with forced correction
function handleStoryKey(e){
  if(e.key==='Backspace'){
    e.preventDefault();
    // Only allow fixing the current word — can't backspace over a space into a
    // completed word and rewrite the whole sentence.
    if(S.pos>0 && S.fullText[S.pos-1]!==' '){
      S.pos--;
      const el=storyCharEls[S.pos];
      if(el.classList.contains('correct')){S.correctChars--;S.totalTyped=Math.max(0,S.totalTyped-1);}
      el.classList.remove('correct','wrong','flash');
      setStoryCurrent();updateStoryHUD();updateProgress();
    }
    resetAfk();return;
  }
  if(e.key.length!==1)return;          // ignore Shift, arrows, etc.
  e.preventDefault();
  if(!S.started)startStoryTimer();
  const expected=S.fullText[S.pos];
  const el=storyCharEls[S.pos];
  if(!el)return;
  S.rawChars++;
  if(e.key===expected){
    S.totalTyped++;S.correctChars++;
    el.classList.remove('wrong','flash');el.classList.add('correct');
    S.combo++;if(S.combo>S.maxCombo)S.maxCombo=S.combo;
    S.score+=Math.round(comboMult()*5);
    if(expected===' '){const r=el.getBoundingClientRect();spawnParts(r.left,r.top+r.height/2,'#4ecca3');}
    playClick(expected===' '?'word':'key');
    S.pos++;
    setStoryCurrent();updateStoryHUD();updateProgress();
    if(S.pos>=S.fullText.length){endGame();return;}
  } else {
    // forced correction: don't advance, flag the error
    S.totalTyped++;
    S.perKeyErrors[expected]=(S.perKeyErrors[expected]||0)+1;
    S.combo=Math.floor(S.combo/2);
    el.classList.add('flash');setTimeout(()=>el.classList.remove('flash'),180);
    storyTextEl.classList.add('shake');setTimeout(()=>storyTextEl.classList.remove('shake'),250);
    playClick('error');
    updateStoryHUD();
  }
  resetAfk();
}

// FREE MODE typing via input event
hiddenInput.addEventListener('input',()=>{
  if(S.finished)return;
  if(S.gameMode==='story'){hiddenInput.value='';return;}
  let val=hiddenInput.value;
  const curWord=S.words[S.wordIndex];
  if(!curWord)return;

  // Cap overflow: allow at most 4 letters past the word's length so a runaway
  // string can't pile up and confuse the typist (space still submits).
  if(!val.endsWith(' ') && val.length > curWord.length + 4){
    val = val.slice(0, curWord.length + 4);
    hiddenInput.value = val;
  }

  const prevLen=(S.typedChars[S.wordIndex]||'').length;
  const newLen=val.endsWith(' ')?val.length-1:val.length;
  if(newLen>prevLen) S.rawChars+=(newLen-prevLen);

  if(val.endsWith(' ')){
    const typed=val.trimEnd();
    if(S.stopOnError&&typed!==curWord){
      hiddenInput.value=typed;
      wordArea.classList.add('shake');playClick('error');
      const we=getWordEl(S.wordIndex);
      if(we)we.classList.add('strict-error');
      setTimeout(()=>wordArea.classList.remove('shake'),300);
      return;
    }
    const we=getWordEl(S.wordIndex);
    if(we)we.classList.remove('strict-error');
    submitWord(typed);
    hiddenInput.value='';
    return;
  }

  S.typedChars[S.wordIndex]=val;S.charIndex=val.length;
  const we=getWordEl(S.wordIndex);
  if(!we)return;
  we.querySelectorAll('.char').forEach((ch,ci)=>{
    ch.classList.remove('correct','wrong');
    if(ci<val.length){
      const ok=val[ci]===curWord[ci];
      ch.classList.add(ok?'correct':'wrong');
      if(!ok&&val[ci]!==undefined) S.perKeyErrors[curWord[ci]]=(S.perKeyErrors[curWord[ci]]||0)+1;
    }
  });
  updateCaret();playClick('key');resetAfk();
});

// ── SUBMIT WORD (FREE MODE) ──────────────────────────────────────────────────────
function submitWord(typed){
  const expected=S.words[S.wordIndex];
  const isCorrect=typed===expected;
  S.totalTyped+=typed.length;
  S.submittedWords.push({typed,expected,correct:isCorrect});

  if(isCorrect){
    S.correctChars+=expected.length+1;
    S.combo++;
    if(S.combo>S.maxCombo)S.maxCombo=S.combo;
    const mult=comboMult();
    S.score+=expected.length*mult*10;
    playClick('word');
    const we=getWordEl(S.wordIndex);
    if(we){const r=we.getBoundingClientRect();spawnParts(r.left+r.width/2,r.top+r.height/2,'#4ecca3');spawnParts(r.left+r.width/2,r.top+r.height/2,'#a87cff');}
    if([10,25,50,100].includes(S.combo)){
      wordArea.classList.add('glow');document.body.classList.add('milestone');
      toast('🔥',`${S.combo}× Combo!`,`Multiplier ×${mult.toFixed(1)}`);
      setTimeout(()=>{wordArea.classList.remove('glow');document.body.classList.remove('milestone');},1000);
    }
  } else {
    for(let i=0;i<expected.length;i++)
      if((typed[i]||'')!==expected[i]) S.perKeyErrors[expected[i]]=(S.perKeyErrors[expected[i]]||0)+1;
    S.combo=Math.floor(S.combo/2);
    wordArea.classList.add('shake');setTimeout(()=>wordArea.classList.remove('shake'),300);
    playClick('error');
  }

  const we=getWordEl(S.wordIndex);
  if(we) we.querySelectorAll('.char').forEach((ch,ci)=>{
    ch.classList.remove('correct','wrong');
    if(ci<typed.length) ch.classList.add(typed[ci]===expected[ci]?'correct':'wrong');
  });

  S.wordIndex++;S.charIndex=0;

  if(S.wordIndex+20>S.words.length){
    const extra=generateWords(50,S.words.slice(-8));
    const base=S.words.length;S.words.push(...extra);
    extra.forEach((w,i)=>wContainer.appendChild(makeWordEl(w,base+i)));
  }

  updateCaret();updateHUD();updateCombo();scrollWords();
}

function comboMult(){
  if(S.combo>=50)return 4;if(S.combo>=25)return 3;
  if(S.combo>=10)return 2;if(S.combo>=5)return 1.5;return 1;
}

// ── HUD ───────────────────────────────────────────────────────────────────────
function updateHUD(){
  const el=S.duration-S.timeLeft;
  const warmup=el<3;
  const wpm=(!warmup&&el>0)?Math.round((S.correctChars/5)/(el/60)):null;
  const raw=(!warmup&&el>0)?Math.round((S.rawChars/5)/(el/60)):null;
  const acc=S.totalTyped>0?Math.round((S.correctChars/S.totalTyped)*100):null;
  document.getElementById('wpm-val').textContent=wpm!==null?wpm:'---';
  document.getElementById('raw-wpm-sub').textContent=raw!==null?`raw ${raw}`:'raw ---';
  document.getElementById('acc-val').textContent=acc!==null?acc:'---';
  document.getElementById('timer-text').textContent=S.timeLeft;
  document.getElementById('score-val').textContent=S.score;
  document.getElementById('chars-val').textContent=S.correctChars;
}

function updateStoryHUD(){
  const min=S.elapsed/60;
  const warmup=S.elapsed<2;
  const wpm=(!warmup&&min>0)?Math.round((S.correctChars/5)/min):null;
  const raw=(!warmup&&min>0)?Math.round((S.rawChars/5)/min):null;
  const acc=S.totalTyped>0?Math.round((S.correctChars/S.totalTyped)*100):null;
  document.getElementById('wpm-val').textContent=wpm!==null?wpm:'---';
  document.getElementById('raw-wpm-sub').textContent=raw!==null?`raw ${raw}`:'raw ---';
  document.getElementById('acc-val').textContent=acc!==null?acc:'---';
  document.getElementById('timer-text').textContent=Math.floor(S.elapsed);
  document.getElementById('score-val').textContent=S.score;
  document.getElementById('chars-val').textContent=S.correctChars;
}

const ARC=2*Math.PI*31;
function setTimerRing(left,total){
  const arc=document.getElementById('timer-arc'),pct=left/total;
  arc.style.strokeDashoffset=ARC*(1-pct);
  arc.style.stroke=pct<.25?'var(--accent3)':pct<.5?'#ffa84c':'var(--accent2)';
}
function setProgressRing(frac){
  const arc=document.getElementById('timer-arc');
  arc.style.strokeDashoffset=ARC*(1-frac);
  arc.style.stroke=frac>=1?'var(--correct)':'var(--accent2)';
}
function updateCombo(){
  const el=document.getElementById('combo-val');
  el.textContent=`×${comboMult().toFixed(1)}`;
  el.classList.remove('pop');void el.offsetWidth;el.classList.add('pop');
  document.getElementById('combo-bar-fill').style.width=Math.min(100,(S.combo/50)*100)+'%';
}

// ── INLINE RESULTS ────────────────────────────────────────────────────────────
function showResultsInline({wpm,rawWpm,accuracy,isNew,xpGained,elapsed,isStory}){
  const live=document.getElementById('game-live');
  const res=document.getElementById('game-results');
  live.classList.add('fading');
  setTimeout(()=>{
    live.style.display='none';
    if(isNew)toast('🏆','New Personal Best!',`${wpm} WPM`);
    document.getElementById('results-headline').textContent=isNew?'🏆 New Personal Best!':(isStory?'📖 Passage Complete!':'Results');
    const con=calcConsistency();
    const grid=document.getElementById('results-grid');grid.innerHTML='';
    const cards=[
      {label:'WPM',val:wpm,unit:'words/min',hi:true},
      {label:'Raw WPM',val:rawWpm,unit:'incl. errors'},
      {label:'Accuracy',val:accuracy,unit:'%'},
      {label:'Consistency',val:con,unit:'%'},
    ];
    if(isStory) cards.push({label:'Time',val:Math.round(elapsed),unit:'seconds'});
    cards.push({label:'Score',val:S.score,unit:'pts'});
    cards.push({label:isStory?'Best Streak':'Best Combo',val:S.maxCombo,unit:isStory?'chars':'words'});
    cards.push({label:'XP Gained',val:xpGained,unit:'xp'});
    cards.forEach(s=>{
      const c=document.createElement('div');
      c.className='result-card'+(s.hi?' highlight':'');
      c.innerHTML=`<div class="r-label">${s.label}</div><div class="r-val" data-target="${s.val}">0</div><div class="r-unit">${s.unit}</div>`;
      grid.appendChild(c);
    });
    grid.querySelectorAll('.r-val[data-target]').forEach(el=>{
      const t=parseInt(el.dataset.target);if(isNaN(t))return;
      let st=null;
      const step=ts=>{if(!st)st=ts;const p=Math.min((ts-st)/800,1);el.textContent=Math.round(t*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(step);};
      requestAnimationFrame(step);
    });
    drawChart();renderTroubleKeys();
    document.getElementById('share-btn').onclick=()=>shareScore(wpm,accuracy);
    res.classList.add('show');
  },320);
}

function calcConsistency(){
  if(S.wpmSamples.length<2)return 100;
  const v=S.wpmSamples.map(s=>s.wpm),avg=v.reduce((a,b)=>a+b,0)/v.length;
  const sd=Math.sqrt(v.reduce((a,b)=>a+(b-avg)**2,0)/v.length);
  return Math.max(0,Math.round(100-(sd/(avg||1))*100));
}

function drawChart(){
  const canvas=document.getElementById('chart-canvas');
  const dpr=window.devicePixelRatio||1,W=canvas.offsetWidth,H=150;
  canvas.width=W*dpr;canvas.height=H*dpr;
  const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);
  const s=S.wpmSamples,pad={t:14,r:14,b:26,l:40},cw=W-pad.l-pad.r,ch=H-pad.t-pad.b;
  const dk=document.body.dataset.theme==='dark';
  const T=S.raceTime||S.duration||1;
  ctx.fillStyle=dk?'#1f1f2e':'#e8e8f8';ctx.roundRect(0,0,W,H,10);ctx.fill();
  if(s.length<2){ctx.fillStyle=dk?'#6b6b8a':'#7070a0';ctx.font='12px JetBrains Mono,monospace';ctx.textAlign='center';ctx.fillText('Not enough data',W/2,H/2);return;}
  const mx=Math.max(...s.map(x=>x.wpm),1),mn=Math.max(0,Math.min(...s.map(x=>x.wpm))-5);
  const tx=t=>pad.l+(t/T)*cw,ty=w=>pad.t+ch-((w-mn)/(mx-mn+1))*ch;
  ctx.strokeStyle=dk?'#2d2d45':'#c0c0e0';ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const y=pad.t+(ch/4)*i;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(pad.l+cw,y);ctx.stroke();ctx.fillStyle=dk?'#6b6b8a':'#7070a0';ctx.font='9px JetBrains Mono,monospace';ctx.textAlign='right';ctx.fillText(Math.round(mx-(mx-mn)*(i/4)),pad.l-5,y+3);}
  [0,T/2,T].forEach(t=>{ctx.fillStyle=dk?'#6b6b8a':'#7070a0';ctx.font='9px JetBrains Mono,monospace';ctx.textAlign='center';ctx.fillText(Math.round(t)+'s',tx(t),H-7);});
  const g=ctx.createLinearGradient(0,pad.t,0,pad.t+ch);g.addColorStop(0,'rgba(168,124,255,.4)');g.addColorStop(1,'rgba(168,124,255,0)');
  ctx.beginPath();ctx.moveTo(tx(s[0].t),ty(s[0].wpm));s.forEach(x=>ctx.lineTo(tx(x.t),ty(x.wpm)));ctx.lineTo(tx(s.at(-1).t),pad.t+ch);ctx.lineTo(tx(s[0].t),pad.t+ch);ctx.closePath();ctx.fillStyle=g;ctx.fill();
  ctx.beginPath();ctx.moveTo(tx(s[0].t),ty(s[0].wpm));s.forEach(x=>ctx.lineTo(tx(x.t),ty(x.wpm)));ctx.strokeStyle='#a87cff';ctx.lineWidth=2.5;ctx.lineJoin='round';ctx.stroke();
  s.forEach(x=>{ctx.beginPath();ctx.arc(tx(x.t),ty(x.wpm),3,0,Math.PI*2);ctx.fillStyle='#a87cff';ctx.fill();});
}

function renderTroubleKeys(){
  const cont=document.getElementById('trouble-keys');cont.innerHTML='';
  const sorted=Object.entries(S.perKeyErrors).sort((a,b)=>b[1]-a[1]).slice(0,8);
  if(!sorted.length){cont.innerHTML='<span class="tk-clear">No trouble keys — great job!</span>';return;}
  sorted.forEach(([ch,n])=>{const el=document.createElement('div');el.className='tkey';el.innerHTML=`<div class="tk-char">${ch===' '?'␣':ch}</div><div class="tk-count">${n}×</div>`;cont.appendChild(el);});
}

// ── SHARE ─────────────────────────────────────────────────────────────────────
function shareScore(wpm,accuracy){
  const mode=S.gameMode==='story'?STORIES[S.storyId]?.title:`${S.duration}s ${S.difficulty}`;
  const text=`I typed ${wpm} WPM with ${accuracy}% accuracy on TypeRush! (${mode}) 🚀`;
  navigator.clipboard?.writeText(text).then(()=>toast('📋','Copied to clipboard!',text)).catch(()=>toast('📋','Your score:',text));
}

// ── SPARKLINE ─────────────────────────────────────────────────────────────────
function drawSparkline(){
  const wrap=document.getElementById('history-wrap');
  const h=S.history.filter(x=>x.wpm>0);
  if(h.length<2){wrap.style.display='none';return;}
  wrap.style.display='block';
  const canvas=document.getElementById('sparkline-canvas');
  const dpr=window.devicePixelRatio||1,W=canvas.offsetWidth||700,H=48;
  canvas.width=W*dpr;canvas.height=H*dpr;
  const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);
  const rev=[...h].reverse();
  const vals=rev.map(x=>x.wpm);
  const mx=Math.max(...vals),mn=Math.max(0,Math.min(...vals)-5);
  const tx=i=>(i/(rev.length-1))*W;
  const ty=v=>H-4-((v-mn)/(mx-mn+1))*(H-8);
  const dk=document.body.dataset.theme==='dark';
  const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,'rgba(168,124,255,.3)');g.addColorStop(1,'rgba(168,124,255,0)');
  ctx.beginPath();ctx.moveTo(tx(0),ty(vals[0]));vals.forEach((v,i)=>ctx.lineTo(tx(i),ty(v)));ctx.lineTo(tx(vals.length-1),H);ctx.lineTo(0,H);ctx.closePath();ctx.fillStyle=g;ctx.fill();
  ctx.beginPath();ctx.moveTo(tx(0),ty(vals[0]));vals.forEach((v,i)=>ctx.lineTo(tx(i),ty(v)));ctx.strokeStyle='#a87cff';ctx.lineWidth=2;ctx.lineJoin='round';ctx.stroke();
  ctx.fillStyle=dk?'#a87cff':'#8060d0';ctx.font='bold 10px JetBrains Mono,monospace';ctx.textAlign='left';ctx.fillText(vals[0]+' WPM',4,12);
  ctx.textAlign='right';ctx.fillText(vals[vals.length-1]+' WPM',W-4,12);
}

// ── MENU ──────────────────────────────────────────────────────────────────────
function buildStoryGrid(){
  const grid=document.getElementById('story-grid');grid.innerHTML='';
  Object.entries(STORIES).forEach(([id,story])=>{
    const card=document.createElement('div');
    card.className='story-card'+(S.storyId===id?' selected':'');
    card.innerHTML=`<div class="story-icon">${story.icon}</div><div class="story-title">${story.title}</div><div class="story-author">${story.author}</div>`;
    card.addEventListener('click',()=>{
      S.storyId=id;
      document.querySelectorAll('.story-card').forEach(c=>c.classList.remove('selected'));
      card.classList.add('selected');
    });
    grid.appendChild(card);
  });
}

function refreshMenu(){
  const grid=document.getElementById('scores-grid');grid.innerHTML='';
  const keys=[
    ...['easy','medium','hard'].flatMap(d=>[15,30,60].map(t=>`${t}-${d}`)),
    ...Object.keys(STORIES).map(id=>`story-${id}`),
  ];
  keys.forEach(k=>{
    const b=S.bests[k];if(!b)return;
    let label;
    if(k.startsWith('story-')){label=STORIES[k.slice(6)]?.title||k;}
    else{const [dur,diff]=k.split('-');label=`${dur}s · ${diff}`;}
    const c=document.createElement('div');c.className='score-card';
    c.innerHTML=`<div class="sc-label">${label}</div><div class="sc-val">${b.wpm}</div><div class="sc-sub">WPM · ${b.acc}% acc</div>`;
    grid.appendChild(c);
  });
  if(!grid.children.length) grid.innerHTML='<p class="empty-msg">No records yet — play a game!</p>';
  drawSparkline();
}

// ── EVENTS ────────────────────────────────────────────────────────────────────
document.querySelectorAll('.mode-tab').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.mode-tab').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    S.gameMode=btn.dataset.mode;
    document.getElementById('words-panel').classList.toggle('hidden',S.gameMode==='story');
    document.getElementById('story-panel').classList.toggle('visible',S.gameMode==='story');
  });
});

document.getElementById('duration-opts').addEventListener('click',e=>{
  const b=e.target.closest('.opt-btn');if(!b)return;
  document.querySelectorAll('#duration-opts .opt-btn').forEach(x=>x.classList.remove('selected'));
  b.classList.add('selected');S.duration=parseInt(b.dataset.val);
});
document.getElementById('difficulty-opts').addEventListener('click',e=>{
  const b=e.target.closest('.opt-btn');if(!b)return;
  document.querySelectorAll('#difficulty-opts .opt-btn').forEach(x=>x.classList.remove('selected'));
  b.classList.add('selected');S.difficulty=b.dataset.val;
});
function setupToggle(id,key){
  const b=document.getElementById(id);
  b.addEventListener('click',()=>{S[key]=!S[key];b.classList.toggle('on',S[key]);savePersisted();});
  b.classList.toggle('on',S[key]);
}
setupToggle('numbers-btn','useNumbers');
setupToggle('punct-btn','usePunctuation');
setupToggle('strict-btn','stopOnError');

document.getElementById('play-btn').addEventListener('click',()=>{showScreen('game');initGame();});
document.getElementById('retry-btn').addEventListener('click',()=>initGame());
document.getElementById('menu-btn').addEventListener('click',()=>quitToMenu());
document.getElementById('restart-btn').addEventListener('click',()=>initGame());
document.querySelectorAll('.focus-overlay').forEach(o=>o.addEventListener('click',()=>{
  if(S.afkPaused){resumeAfk();}else{hideOverlay();}
  hiddenInput.focus();
}));

document.addEventListener('keydown',e=>{
  if(S.screen==='game'&&S.finished){
    if(e.key==='Tab'||e.key==='Enter'){e.preventDefault();initGame();}
    if(e.key==='Escape'){quitToMenu();}
  }
  if(S.screen==='game'&&document.activeElement!==hiddenInput&&!S.finished){
    hiddenInput.focus();
  }
});
wordArea.addEventListener('click',()=>hiddenInput.focus());
storyArea.addEventListener('click',()=>hiddenInput.focus());

hiddenInput.addEventListener('blur',()=>{
  if(S.started&&!S.finished&&!S.afkPaused){
    setTimeout(()=>{
      if(document.activeElement!==hiddenInput&&S.started&&!S.finished){
        showOverlay('⌨️','Click to focus');
      }
    },200);
  }
});
hiddenInput.addEventListener('focus',()=>{
  if(!S.afkPaused)hideOverlay();
});

document.getElementById('theme-btn').addEventListener('click',()=>{
  S.theme=S.theme==='dark'?'light':'dark';
  document.body.dataset.theme=S.theme;
  document.getElementById('theme-btn').textContent=S.theme==='dark'?'☀️':'🌙';
  savePersisted();
});
document.getElementById('sound-btn').addEventListener('click',()=>{
  S.soundOn=!S.soundOn;
  const b=document.getElementById('sound-btn');
  b.textContent=S.soundOn?'🔊':'🔇';b.classList.toggle('active',S.soundOn);
  savePersisted();
});

// ── INIT ──────────────────────────────────────────────────────────────────────
loadPersisted();
updateLevelBar();
document.body.dataset.theme=S.theme;
document.getElementById('theme-btn').textContent=S.theme==='dark'?'☀️':'🌙';
document.getElementById('sound-btn').textContent=S.soundOn?'🔊':'🔇';
document.getElementById('sound-btn').classList.toggle('active',S.soundOn);
['numbers-btn','punct-btn','strict-btn'].forEach(id=>{
  const key=id==='numbers-btn'?'useNumbers':id==='punct-btn'?'usePunctuation':'stopOnError';
  document.getElementById(id).classList.toggle('on',S[key]);
});
buildStoryGrid();
refreshMenu();
