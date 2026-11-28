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
  $('accountDanger').hidden=false;
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
 $('deleteAccount').addEventListener('click',async()=>{
  const api=cloud()&&cloud().client;
  const status=$('deleteMessage');
  if(!$('deleteConfirm').checked||$('deletePhrase').value.trim()!=='탈퇴'){status.textContent='확인 체크와 “탈퇴” 입력을 완료해 주세요.';status.className='profile-message error';return;}
  if(!confirm('정말 탈퇴할까요? 계정과 클라우드 기록은 삭제 후 복구할 수 없습니다.'))return;
  $('deleteAccount').disabled=true;status.textContent='계정과 개인정보를 삭제하고 있어요...';status.className='profile-message';
  try{
   const {data:{session},error:sessionError}=await api.auth.getSession();if(sessionError)throw sessionError;if(!session)throw new Error('로그인이 만료됐어요. 다시 로그인해 주세요.');
   const {data,error}=await api.functions.invoke('delete-account',{headers:{Authorization:'Bearer '+session.access_token},body:{confirmation:'DELETE_MY_ACCOUNT'}});
   if(error)throw error;if(!data||data.deleted!==true)throw new Error(data&&data.error?data.error:'계정 삭제 결과를 확인하지 못했어요.');
   localStorage.removeItem('moamoa_demo_v2');localStorage.removeItem('moamoa_cloud_owner');
   status.textContent='계정과 클라우드 개인정보가 삭제됐어요. 홈으로 이동합니다.';location.href='index.html';
  }catch(err){status.textContent=(err.message||'삭제 요청에 실패했어요.')+' Edge Function 배포 및 설정 여부를 확인해 주세요.';status.className='profile-message error';$('deleteAccount').disabled=false;}
 });
 $('profileLogout').addEventListener('click',async()=>{
  const api=cloud()&&cloud().client;if(!api)return;
  $('profileLogout').disabled=true;
  const {error}=await api.auth.signOut();
  if(error){message(error.message,true);$('profileLogout').disabled=false;return;}
  location.href='index.html';
 });
 document.addEventListener('moamoa:cloud-ready',e=>fill(e.detail.user));
 document.addEventListener('moamoa:signed-out',()=>{ $('profilePanel').hidden=true;$('accountDanger').hidden=true;$('accountAction').hidden=false;$('accountStatus').textContent='로그인하면 회원 정보와 수집 기록을 계정에 연결할 수 있어요.';});
 load();
})();