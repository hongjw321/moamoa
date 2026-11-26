const characters = [
  {id:"tori",name:"토리",emoji:"🐰",type:"토끼",rarity:"LEGENDARY",label:"전설",desc:"호기심이 많고 언제나 새로운 모험을 꿈꿔요.",color:"#ffe8f0"},
  {id:"mongi",name:"몽이",emoji:"🐻",type:"곰",rarity:"RARE",label:"희귀",desc:"포근한 마음으로 친구들을 꼭 안아줘요.",color:"#fff0dc"},
  {id:"paenggu",name:"팽구",emoji:"🐧",type:"펭귄",rarity:"COMMON",label:"일반",desc:"조금 느리지만 누구보다 성실한 친구예요.",color:"#eaf2ff"},
  {id:"nabi",name:"나비",emoji:"🐱",type:"고양이",rarity:"RARE",label:"희귀",desc:"새침해 보여도 사실은 애교쟁이랍니다.",color:"#f2eaff"},
  {id:"ppiyak",name:"삐약",emoji:"🐥",type:"병아리",rarity:"COMMON",label:"일반",desc:"작은 날개로 매일 장난을 치는 개구쟁이!",color:"#fff4d7"},
  {id:"mochi",name:"모찌",emoji:"🦦",type:"수달",rarity:"EPIC",label:"에픽",desc:"간식을 좋아하고 물놀이를 사랑해요.",color:"#e5f7f5"}
];
const STORAGE_KEY = "moamoa_demo_v1";
let state = loadState();
let pendingCharacter = null;
function loadState(){try{return JSON.parse(localStorage.getItem(STORAGE_KEY))||{owned:[],history:[],usedFree:false}}catch{return {owned:[],history:[],usedFree:false}}}
function save(){localStorage.setItem(STORAGE_KEY,JSON.stringify(state));updateUI()}
function updateUI(){
  const unique = new Set(state.owned);
  document.getElementById("ownedCount").textContent=`${unique.size} / ${characters.length}`;
  document.getElementById("collectionCount").textContent=`${unique.size} / ${characters.length} 수집`;
  document.getElementById("progressBar").style.width=`${unique.size/characters.length*100}%`;
  document.getElementById("ticketStatus").textContent=state.usedFree?"사용 완료":"1회 남음";
  document.getElementById("drawButton").disabled=state.usedFree;
  document.getElementById("drawButton").textContent=state.usedFree?"무료 체험을 완료했어요":"친구 뽑기 시작! ✨";
  document.getElementById("mypageStats").textContent=`수집한 친구 ${unique.size}명 · 무료 뽑기 ${state.history.length}회`;
  renderHistory();
}
function renderCharacters(){
  const grid=document.getElementById("characterGrid");
  grid.innerHTML=characters.map(c=>{
    const owned=state.owned.includes(c.id);
    return `<article class="character-card ${owned?"":"locked"}"><div class="character-art" style="background:${c.color}">${owned?c.emoji:"❔"}</div><h3>${owned?c.name:"???"}</h3><p>${owned?c.type+" 친구":"아직 만나지 못한 친구"}</p><span class="tag">${owned?c.label:"미획득"}</span><span class="owned-tag">${owned?"✓ 내 컬렉션":"🔒 잠김"}</span></article>`;
  }).join("");
}
function renderHistory(){
 const list=document.getElementById("historyList");
 if(!state.history.length){list.innerHTML='<li class="empty-history">아직 뽑기 기록이 없어요. 첫 친구를 만나볼까요?</li>';return}
 list.innerHTML=state.history.slice().reverse().map(h=>`<li>🎁 <strong>${h.name}</strong> 친구를 만났어요 <span style="float:right;color:#b69aa7">${h.date}</span></li>`).join("");
}
function showToast(message){const t=document.getElementById("toast");t.textContent=message;t.classList.add("show");setTimeout(()=>t.classList.remove("show"),2400)}
document.getElementById("drawButton").addEventListener("click",()=>{
 if(state.usedFree){showToast("무료 체험 뽑기를 이미 사용했어요.");return}
 const c=characters[Math.floor(Math.random()*characters.length)];
 pendingCharacter=c;
 state.usedFree=true;
 state.owned.push(c.id);
 state.history.push({id:c.id,name:c.name,date:new Date().toLocaleDateString("ko-KR")});
 save();renderCharacters();
 document.getElementById("resultEmoji").textContent=c.emoji;
 document.getElementById("resultName").textContent=c.name;
 document.getElementById("resultDescription").textContent=c.desc;
 document.getElementById("resultRarity").textContent=c.rarity;
 document.getElementById("resultPanel").hidden=false;
 document.getElementById("resultPanel").scrollIntoView({behavior:"smooth",block:"center"});
});
document.getElementById("closeResult").addEventListener("click",()=>{
 document.getElementById("resultPanel").hidden=true;
 showToast(`${pendingCharacter?.name||"친구"}가 컬렉션에 추가되었어요 💗`);
 document.getElementById("collection").scrollIntoView({behavior:"smooth"});
});
document.getElementById("menuToggle").addEventListener("click",()=>document.getElementById("mainNav").classList.toggle("open"));
document.querySelectorAll(".nav-link").forEach(a=>a.addEventListener("click",()=>{
 document.querySelectorAll(".nav-link").forEach(x=>x.classList.remove("active"));a.classList.add("active");
 document.getElementById("mainNav").classList.remove("open");
}));
renderCharacters();updateUI();
