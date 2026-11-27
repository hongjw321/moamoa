(function(){
  const cfg=window.MOAMOA_SUPABASE_CONFIG||{};
  const configured=cfg.url&&cfg.anonKey&&!cfg.url.includes("YOUR_")&&!cfg.anonKey.includes("YOUR_");
  window.MOAMOA_CLOUD={configured,user:null,client:null,ready:false};
  const accountStatus=document.getElementById("accountStatus");
  if(!configured||!window.supabase){
    if(accountStatus)accountStatus.textContent="현재는 이 브라우저에만 저장 중이에요. Supabase 연결 후 계정 동기화를 사용할 수 있어요.";
    console.info("MOAMOA cloud sync is waiting for Supabase project settings.");return;
  }
  const client=window.supabase.createClient(cfg.url,cfg.anonKey);
  window.MOAMOA_CLOUD.client=client;
  let saving=false,saveQueued=false,mergeInProgress=false;
  const storageKey="moamoa_demo_v2";
  const ownerKey="moamoa_cloud_owner";
  const readLocal=()=>{try{return JSON.parse(localStorage.getItem(storageKey))||{used:false,owned:[],history:[],attendance:[],cart:[]}}catch{return {used:false,owned:[],history:[],attendance:[],cart:[]}}};
  function mergeData(local,remote){
    const a=local||{},b=remote||{};
    const history=[...(b.history||[]),...(a.history||[])];
    const seen=new Set();
    const mergedHistory=history.filter(x=>{const k=[x.id,x.date,x.name].join("|");if(seen.has(k))return false;seen.add(k);return true;});
    const cartMap=new Map();
    [...(b.cart||[]),...(a.cart||[])].forEach(x=>{const old=cartMap.get(x.id);cartMap.set(x.id,{id:x.id,qty:Math.max(Number(old&&old.qty)||0,Number(x.qty)||0)});});
    return {used:!!(a.used||b.used),owned:[...new Set([...(b.owned||[]),...(a.owned||[])])],history:mergedHistory,attendance:[...new Set([...(b.attendance||[]),...(a.attendance||[])])].sort(),cart:[...cartMap.values()]};
  }
  async function saveCloud(){
    if(!window.MOAMOA_CLOUD.user||saving)return;
    saving=true;saveQueued=false;
    try{
      const payload=readLocal();
      const {error}=await client.from("user_data").upsert({user_id:window.MOAMOA_CLOUD.user.id,payload,updated_at:new Date().toISOString()},{onConflict:"user_id"});
      if(error)throw error;
      document.dispatchEvent(new CustomEvent("moamoa:cloud-saved"));
    }catch(error){console.error("MOAMOA cloud save failed:",error);document.dispatchEvent(new CustomEvent("moamoa:cloud-error",{detail:error.message}));}
    finally{saving=false;if(saveQueued){saveQueued=false;setTimeout(saveCloud,300);}}
  }
  function queueSave(){if(!window.MOAMOA_CLOUD.user)return;saveQueued=true;setTimeout(()=>{if(!saving)saveCloud();},500);}
  async function loadUser(user){
    window.MOAMOA_CLOUD.user=user;
    if(accountStatus)accountStatus.textContent="계정 연결됨 · 컬렉션과 기록을 동기화하고 있어요.";
    mergeInProgress=true;
    try{
      const previousOwner=localStorage.getItem(ownerKey);
      const {data:row,error}=await client.from("user_data").select("payload").eq("user_id",user.id).maybeSingle();
      if(error)throw error;
      // Never import an unowned browser cache into an account: it may belong to a different person on a shared device.
      const local=previousOwner===user.id?readLocal():null;
      const merged=mergeData(local,row&&row.payload);
      localStorage.setItem(storageKey,JSON.stringify(merged));
      localStorage.setItem(ownerKey,user.id);
      if(typeof refresh==="function")refresh();
      if(typeof renderAttendance==="function")renderAttendance();
      window.MOAMOA_CLOUD.ready=true;
      if(accountStatus)accountStatus.textContent="클라우드 동기화 연결됨 · 다른 기기에서도 이어서 사용할 수 있어요.";
      document.dispatchEvent(new CustomEvent("moamoa:cloud-ready",{detail:{user}}));
      await saveCloud();
    }catch(error){console.error("MOAMOA cloud load failed:",error);document.dispatchEvent(new CustomEvent("moamoa:cloud-error",{detail:error.message}));}
    finally{mergeInProgress=false;}
  }
  if(typeof persist==="function"){
    const originalPersist=persist;
    persist=function(){originalPersist();if(!mergeInProgress)queueSave();};
  }
  client.auth.onAuthStateChange((event,session)=>{
    if(session&&session.user){setTimeout(()=>loadUser(session.user),0);}
    else{const hadUser=!!window.MOAMOA_CLOUD.user;window.MOAMOA_CLOUD.user=null;window.MOAMOA_CLOUD.ready=false;if(event==="SIGNED_OUT"&&hadUser){localStorage.removeItem(storageKey);localStorage.removeItem(ownerKey);if(typeof refresh==="function")refresh();if(typeof renderAttendance==="function")renderAttendance();}if(accountStatus)accountStatus.textContent="로그인하면 컬렉션과 출석 기록을 계정에 보관할 수 있어요.";document.dispatchEvent(new CustomEvent("moamoa:signed-out"));}
  });
  client.auth.getSession().then(({data,error})=>{
    if(error)console.error(error);
    if(data.session&&data.session.user)loadUser(data.session.user);
  });
  window.MOAMOA_CLOUD.signOut=()=>client.auth.signOut();
})();
