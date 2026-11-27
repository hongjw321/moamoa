const people=[
{id:'tori',name:'토리',animal:'토끼',emoji:'🐰',desc:'호기심이 많고 언제나 새로운 모험을 꿈꿔요.',rarity:'전설',img:'assets/tori.jpg'},
{id:'mongi',name:'몽이',animal:'곰',emoji:'🐻',desc:'포근한 마음으로 친구들을 꼭 안아줘요.',rarity:'희귀',img:'assets/mongi.jpg'},
{id:'paenggu',name:'팽구',animal:'펭귄',emoji:'🐧',desc:'조금 느리지만 누구보다 성실한 친구예요.',rarity:'일반',img:'assets/paenggu.jpg'},
{id:'nabi',name:'나비',animal:'고양이',emoji:'🐱',desc:'새침해 보여도 사실은 애교쟁이랍니다.',rarity:'희귀',img:'assets/tori.jpg'},
{id:'ppiyak',name:'삐약',animal:'병아리',emoji:'🐥',desc:'작은 날개로 매일 장난을 치는 개구쟁이!',rarity:'일반',img:'assets/paenggu.jpg'},
{id:'mochi',name:'모찌',animal:'수달',emoji:'🦦',desc:'간식을 좋아하고 물놀이를 사랑해요.',rarity:'에픽',img:'assets/mongi.jpg'}];
const KEY='moamoa_demo_v2';let data;try{data=JSON.parse(localStorage.getItem(KEY))||{used:false,owned:[],history:[]}}catch{data={used:false,owned:[],history:[]}}
let selected=null;const $=id=>document.getElementById(id);
function persist(){localStorage.setItem(KEY,JSON.stringify(data));refresh()}
function refresh(){const n=new Set(data.owned).size;$('ticket').textContent=data.used?'사용 완료':'1회 남음';$('draw').disabled=data.used;$('draw').textContent=data.used?'무료 체험 완료':'친구 뽑기 시작! ✨';$('count').textContent=`${n} / 6 수집`;$('stats').textContent=`수집한 친구 ${n}명 · 무료 뽑기 ${data.history.length}회`;$('history').innerHTML=data.history.length?data.history.slice().reverse().map(x=>`<li>${x.date} · ${x.name} 친구를 만났어요</li>`).join(''):'<li>아직 뽑기 기록이 없어요.</li>';render()}
function render(){$('characters').innerHTML=people.map(p=>{let own=data.owned.includes(p.id);return `<article class="character ${own?'':'locked'}"><img src="${p.img}" alt="${p.name}"><h3>${own?p.name:'???'}</h3><p>${own?p.animal+' 친구':'아직 만나지 못한 친구'}</p><span class="chip">${own?p.rarity:'미획득'}</span><small>${own?'✓ 내 컬렉션':'🔒 잠김'}</small></article>`}).join('')}
$('draw').addEventListener('click',()=>{if(data.used)return;selected=people[Math.floor(Math.random()*people.length)];data.used=true;data.owned.push(selected.id);data.history.push({id:selected.id,name:selected.name,date:new Date().toLocaleDateString('ko-KR')});persist();$('resultImage').innerHTML=`<img src="${selected.img}" alt="${selected.name}">`;$('resultName').textContent=selected.name;$('resultDesc').textContent=selected.desc;$('result').hidden=false;$('result').scrollIntoView({behavior:'smooth',block:'center'})});
$('close').addEventListener('click',()=>{$('result').hidden=true;$('collection').scrollIntoView({behavior:'smooth'});});
$('hamb').addEventListener('click',()=>$('nav').classList.toggle('open'));document.querySelectorAll('#nav a').forEach(a=>a.addEventListener('click',()=>$('nav').classList.remove('open')));
refresh();
