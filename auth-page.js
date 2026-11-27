(function(){
 const $=id=>document.getElementById(id);
 let mode="login";
 const notice=$("cloudNotice"),form=$("authForm"),submit=$("authSubmit"),message=$("authMessage");
 function showMessage(text,isError=false){message.textContent=text;message.className="auth-message "+(isError?"error":"");}
 function client(){return window.MOAMOA_CLOUD&&window.MOAMOA_CLOUD.client;}
 function setMode(next){mode=next;document.querySelectorAll(".auth-tab").forEach(b=>b.classList.toggle("active",b.dataset.mode===mode));$("password").autocomplete=mode==="login"?"current-password":"new-password";submit.textContent=mode==="login"?"로그인":"회원가입";$("resetPassword").hidden=mode!=="login";showMessage("");}
 document.querySelectorAll(".auth-tab").forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.mode)));
 if(!window.MOAMOA_CLOUD||!window.MOAMOA_CLOUD.configured){notice.textContent="아직 클라우드 연결 설정이 필요해요. supabase-config.js에 프로젝트 URL과 anon key를 입력하면 사용할 수 있어요.";notice.classList.add("warning");form.querySelectorAll("input,button").forEach(x=>x.disabled=true);$("resetPassword").disabled=true;}
 else{notice.textContent="클라우드 서비스 연결 준비 완료";notice.classList.add("connected");}
 form.addEventListener("submit",async e=>{
  e.preventDefault();const api=client();if(!api){showMessage("Supabase 설정을 먼저 완료해주세요.",true);return;}
  const email=$("email").value.trim(),password=$("password").value;const redirectUrl="https://hongjw321.github.io/moamoa/auth.html";submit.disabled=true;showMessage("처리 중이에요...");
  try{
   if(mode==="signup"){
    const {data,error}=await api.auth.signUp({email,password,options:{emailRedirectTo:redirectUrl}});if(error)throw error;
    showMessage(data.session?"회원가입이 완료됐어요.":"인증 메일을 확인한 뒤 로그인해주세요.");
   }else{
    const {error}=await api.auth.signInWithPassword({email,password});if(error)throw error;
    showMessage("로그인 성공! 내 컬렉션을 불러오고 있어요.");
    setTimeout(()=>location.href="mypage.html",900);
   }
  }catch(err){showMessage(err.message||"요청을 처리하지 못했어요.",true);}
  finally{submit.disabled=false;}
 });
 $("resendConfirmation").addEventListener("click",async()=>{
  const api=client(),email=$("email").value.trim();if(!api)return showMessage("Supabase 설정이 필요해요.",true);if(!email)return showMessage("인증 메일을 받을 이메일을 먼저 입력해주세요.",true);
  try{const {error}=await api.auth.resend({type:"signup",email,options:{emailRedirectTo:"https://hongjw321.github.io/moamoa/auth.html"}});if(error)throw error;showMessage("인증 메일을 다시 보냈어요. 새 메일의 링크를 눌러주세요.");}catch(err){showMessage(err.message||"인증 메일을 다시 보내지 못했어요.",true);}
 });
 $("resetPassword").addEventListener("click",async()=>{
  const api=client(),email=$("email").value.trim();if(!api)return showMessage("Supabase 설정이 필요해요.",true);if(!email)return showMessage("비밀번호 재설정 메일을 받을 이메일을 입력해주세요.",true);
  try{const {error}=await api.auth.resetPasswordForEmail(email,{redirectTo:"https://hongjw321.github.io/moamoa/auth.html"});if(error)throw error;showMessage("비밀번호 재설정 메일을 보냈어요.");}catch(err){showMessage(err.message,true);}
 });
 $("signOut").addEventListener("click",async()=>{const api=client();if(api){const {error}=await api.auth.signOut();if(error)showMessage(error.message,true);else location.reload();}});
 document.addEventListener("moamoa:cloud-ready",e=>{$("authForms").hidden=true;$("signedInPanel").hidden=false;$("signedInEmail").textContent=e.detail.user.email||"로그인 완료";notice.textContent="클라우드 동기화 연결됨";notice.classList.add("connected");});
 document.addEventListener("moamoa:signed-out",()=>{$("authForms").hidden=false;$("signedInPanel").hidden=true;});
 if(client())client().auth.getSession().then(({data})=>{if(data.session){$("authForms").hidden=true;$("signedInPanel").hidden=false;$("signedInEmail").textContent=data.session.user.email||"로그인 완료";}});
})();
