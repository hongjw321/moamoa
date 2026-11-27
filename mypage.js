(function(){
 const $=id=>document.getElementById(id);
 const cloud=()=>window.MOAMOA_CLOUD;
 function message(text,error=false){$('profileMessage').textContent=text;$('profileMessage').className='profile-message'+(error?' error':'');}
 function fill(user){
  const meta=user.user_metadata||{};
  $('profileName').value=meta.full_name||'';
  $('profileNickname').value=meta.nickname||'';
  $('profilePhone').value=meta.phone||'';
  $('profileAddress').value=meta.address||'';
  $('profileEmail').value=user.email||'';
  $('myDisplayName').textContent=(meta.nickname||meta.full_name||'모아러버')+'님';
  $('profilePanel').hidden=false;
  $('accountAction').hidden=true;
  $('accountStatus').textContent='로그인됨 · 계정 정보와 수집 기록을 관리할 수 있어요.';
 }
 async function load(){
  const api=cloud()&&cloud().client;
  if(!api){$('accountStatus').textContent='클라우드 연결을 확인할 수 없어요. 잠시 후 새로고침하거나 계정 설정을 확인해 주세요.';return;}
  const {data,error}=await api.auth.getUser();
  if(error||!data.user){$('profilePanel').hidden=true;$('accountAction').hidden=false;$('accountStatus').textContent='로그인하면 회원 정보와 수집 기록을 계정에 연결할 수 있어요.';return;}
  fill(data.user);
 }
 $('profileForm').addEventListener('submit',async e=>{
  e.preventDefault();const api=cloud()&&cloud().client;if(!api)return message('클라우드 연결을 확인할 수 없어요.',true);
  const full_name=$('profileName').value.trim(),nickname=$('profileNickname').value.trim();
  if(!full_name||!nickname)return message('이름과 닉네임을 입력해 주세요.',true);
  $('profileSave').disabled=true;message('저장하고 있어요...');
  try{
   const {data,error}=await api.auth.updateUser({data:{full_name,nickname,phone:$('profilePhone').value.trim(),address:$('profileAddress').value.trim()}});
   if(error)throw error;fill(data.user);message('회원 정보가 안전하게 업데이트됐어요.');
  }catch(err){message(err.message||'저장하지 못했어요. 다시 시도해 주세요.',true);}
  finally{$('profileSave').disabled=false;}
 });
 $('profileLogout').addEventListener('click',async()=>{
  const api=cloud()&&cloud().client;if(!api)return;
  $('profileLogout').disabled=true;
  const {error}=await api.auth.signOut();
  if(error){message(error.message,true);$('profileLogout').disabled=false;return;}
  location.href='index.html';
 });
 document.addEventListener('moamoa:cloud-ready',e=>fill(e.detail.user));
 document.addEventListener('moamoa:signed-out',()=>{ $('profilePanel').hidden=true;$('accountAction').hidden=false;$('accountStatus').textContent='로그인하면 회원 정보와 수집 기록을 계정에 연결할 수 있어요.';});
 load();
})();