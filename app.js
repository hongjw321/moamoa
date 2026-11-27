const people=[
{id:'tori',name:'토리',animal:'토끼',desc:'호기심이 많고 언제나 새로운 모험을 꿈꿔요.',personality:'호기심 가득한 모험가',story:'모아모아 마을의 새로운 장소를 발견하는 것을 가장 좋아해요. 반짝이는 것을 보면 눈을 떼지 못하고, 친구들을 모험으로 이끌어요.',favorite:'별 모양 쿠키',color:'코튼 핑크',rarity:'전설',img:'assets/tori.jpg'},
{id:'mongi',name:'몽이',animal:'곰',desc:'포근한 마음으로 친구들을 꼭 안아줘요.',personality:'다정하고 포근한 마음',story:'친구가 힘들어 보이면 먼저 다가가 꼭 안아주는 따뜻한 친구예요. 조용한 오후와 포근한 담요를 좋아해요.',favorite:'꿀 우유',color:'밀크 브라운',rarity:'희귀',img:'assets/mongi.jpg'},
{id:'paenggu',name:'팽구',animal:'펭귄',desc:'조금 느리지만 누구보다 성실한 친구예요.',personality:'차분하고 성실한 노력가',story:'무슨 일이든 서두르지 않고 자기만의 속도로 해내요. 작은 약속도 소중하게 지키는 믿음직한 친구랍니다.',favorite:'차가운 레몬 소다',color:'아이스 블루',rarity:'일반',img:'assets/paenggu.jpg'},
{id:'nabi',name:'나비',animal:'고양이',desc:'새침해 보여도 사실은 애교쟁이랍니다.',personality:'새침한 매력의 애교쟁이',story:'처음에는 조금 도도해 보이지만 친해지면 누구보다 살갑게 다가와요. 햇살이 드는 창가에서 낮잠 자는 걸 좋아해요.',favorite:'참치 모양 쿠키',color:'라벤더',rarity:'희귀',img:'assets/tori.jpg'},
{id:'ppiyak',name:'삐약',animal:'병아리',desc:'작은 날개로 매일 장난을 치는 개구쟁이!',personality:'장난꾸러기 분위기 메이커',story:'작은 날개로 여기저기 바쁘게 돌아다니며 친구들에게 웃음을 선물해요. 새로운 놀이를 생각해 내는 데 천재랍니다.',favorite:'폭신한 옥수수빵',color:'버터 옐로',rarity:'일반',img:'assets/paenggu.jpg'},
{id:'mochi',name:'모찌',animal:'수달',desc:'간식을 좋아하고 물놀이를 사랑해요.',personality:'간식과 물놀이를 사랑하는 친구',story:'물가에서 조약돌을 모으고 맛있는 간식을 나누는 걸 좋아해요. 반짝이는 조약돌은 소중한 보물 상자에 보관해요.',favorite:'조개 모양 젤리',color:'민트 크림',rarity:'에픽',img:'assets/mongi.jpg'}];
const KEY='moamoa_demo_v2';let data;try{data=JSON.parse(localStorage.getItem(KEY))||{used:false,owned:[],history:[]}}catch{data={used:false,owned:[],history:[]}};data.attendance=Array.isArray(data.attendance)?data.attendance:[];let selected=null;const $=id=>document.getElementById(id);
function persist(){localStorage.setItem(KEY,JSON.stringify(data));refresh()}
function refresh(){const n=new Set(data.owned).size;if($('ticket')){$('ticket').textContent=data.used?'사용 완료':'1회 남음';$('draw').disabled=data.used;$('draw').textContent=data.used?'무료 체험 완료':'친구 뽑기 시작'}if($('count'))$('count').textContent=`${n} / 6 수집`;if($('stats'))$('stats').textContent=`수집한 친구 ${n}명 · 무료 뽑기 ${data.history.length}회`;if($('history'))$('history').innerHTML=data.history.length?data.history.slice().reverse().map(x=>`<li>${x.date} · ${x.name} 친구를 만났어요</li>`).join(''):'<li>아직 뽑기 기록이 없어요.</li>';if($('characters'))$('characters').innerHTML=people.map(p=>{let own=data.owned.includes(p.id);return `<a class="character character-link ${own?'':'locked'}" href="character.html?id=${p.id}"><img src="${p.img}" alt="${p.name}"><h3>${own?p.name:'???'}</h3><p>${own?p.animal+' 친구':'아직 만나지 못한 친구'}</p><span class="chip">${own?p.rarity:'미획득'}</span><small>${own?'상세 프로필 보기':'프로필 미리보기'}</small></a>`}).join('')}
if($('draw'))$('draw').addEventListener('click',()=>{if(data.used)return;selected=people[Math.floor(Math.random()*people.length)];data.used=true;data.owned.push(selected.id);data.history.push({id:selected.id,name:selected.name,date:new Date().toLocaleDateString('ko-KR')});persist();$('resultImage').innerHTML=`<img src="${selected.img}" alt="${selected.name}">`;$('resultName').textContent=selected.name;$('resultDesc').textContent=selected.desc;$('result').hidden=false});
const hamburger=$('hamb');if(hamburger)hamburger.addEventListener('click',()=>$('nav').classList.toggle('open'));refresh();

function localDateKey(date=new Date()){const y=date.getFullYear(),m=String(date.getMonth()+1).padStart(2,'0'),d=String(date.getDate()).padStart(2,'0');return y+'-'+m+'-'+d}
function attendanceStreak(){const days=new Set(data.attendance);let cursor=new Date();let key=localDateKey(cursor);if(!days.has(key)){cursor.setDate(cursor.getDate()-1);key=localDateKey(cursor);if(!days.has(key))return 0}let count=0;while(days.has(key)){count++;cursor.setDate(cursor.getDate()-1);key=localDateKey(cursor)}return count}
function renderAttendance(){
 const today=localDateKey(),done=data.attendance.includes(today),streak=attendanceStreak();
 if($('attendanceBtn')){$('attendanceBtn').disabled=done;$('attendanceBtn').textContent=done?'오늘 출석 완료':'오늘 출석 체크하기'}
 if($('attendanceStatus'))$('attendanceStatus').textContent=done?'오늘의 출석 도장을 찍었어요! 내일 또 만나요.':'오늘도 모아모아에 놀러와줘서 고마워요!';
 if($('attendanceStreak'))$('attendanceStreak').textContent=streak+'일';
 if($('attendanceTotal'))$('attendanceTotal').textContent=data.attendance.length+'일';
 if($('attendanceGrid')){$('attendanceGrid').innerHTML=Array.from({length:7},(_,i)=>{const d=new Date();d.setDate(d.getDate()-(6-i));const key=localDateKey(d),marked=data.attendance.includes(key);return '<div class="attendance-day '+(marked?'marked':'')+'"><b>'+['일','월','화','수','목','금','토'][d.getDay()]+'</b><span>'+d.getDate()+'</span><small>'+(marked?'완료':'대기')+'</small></div>'}).join('')}
}
if($('attendanceBtn'))$('attendanceBtn').addEventListener('click',()=>{const today=localDateKey();if(data.attendance.includes(today))return;data.attendance.push(today);persist();renderAttendance()});

renderAttendance();