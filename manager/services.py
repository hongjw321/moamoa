import json, os
from pathlib import Path
import requests
import keyring

APP_NAME="MOAMOA_MANAGER"
def config_path():
    base=Path(os.getenv("APPDATA",Path.home()))/"MOAMOA Manager"
    base.mkdir(parents=True,exist_ok=True)
    return base/"settings.json"

class SettingsStore:
    def load(self):
        p=config_path()
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except Exception: pass
        return {"supabase_url":"https://gugyczralmtvowfhulqe.supabase.co","supabase_anon_key":"","github_repo":"hongjw321/moamoa"}
    def save(self,cfg):
        config_path().write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
    def save_github_token(self,token):
        keyring.set_password(APP_NAME,"github_token",token)
    def github_token(self):
        try: return keyring.get_password(APP_NAME,"github_token")
        except Exception: return None
    def save_admin_session(self,access_token,email):
        keyring.set_password(APP_NAME,"admin_access_token",access_token)
        keyring.set_password(APP_NAME,"admin_email",email)
    def admin_session(self):
        try:
            return {"access_token":keyring.get_password(APP_NAME,"admin_access_token"),
                    "email":keyring.get_password(APP_NAME,"admin_email")}
        except Exception: return {"access_token":None,"email":None}
    def clear_admin_session(self):
        for key in ("admin_access_token","admin_email"):
            try: keyring.delete_password(APP_NAME,key)
            except Exception: pass

class SupabaseService:
    def __init__(self,cfg): self.cfg=cfg
    def health(self):
        url=self.cfg.get("supabase_url","").rstrip("/")
        key=self.cfg.get("supabase_anon_key","")
        if not url or not key: raise RuntimeError("설정 화면에서 Supabase URL과 공개 키를 먼저 저장하세요.")
        r=requests.get(url+"/auth/v1/health",headers={"apikey":key},timeout=12)
        if r.status_code>=400: raise RuntimeError(f"Supabase 응답 오류: HTTP {r.status_code}")
        return True
    def admin_login(self,email,password,store):
        url=self.cfg.get("supabase_url","").rstrip("/")
        key=self.cfg.get("supabase_anon_key","")
        if not url or not key: raise RuntimeError("환경 설정에서 Supabase URL과 공개 키를 먼저 저장하세요.")
        r=requests.post(url+"/auth/v1/token?grant_type=password",
            headers={"apikey":key,"Content-Type":"application/json"},
            json={"email":email.strip(),"password":password},timeout=20)
        if r.status_code>=400:
            try: msg=r.json().get("msg") or r.json().get("message") or r.json().get("error_description")
            except Exception: msg=None
            raise RuntimeError(msg or "로그인에 실패했습니다. 이메일과 비밀번호를 확인하세요.")
        data=r.json()
        if not data.get("access_token"): raise RuntimeError("로그인 세션을 받지 못했습니다.")
        store.save_admin_session(data["access_token"],data.get("user",{}).get("email",email.strip()))
        return data.get("user",{})

class AdminUsersService:
    def __init__(self,cfg,store):
        self.cfg=cfg; self.store=store
    def request(self,payload):
        url=self.cfg.get("supabase_url","").rstrip("/")
        key=self.cfg.get("supabase_anon_key","")
        session=self.store.admin_session()
        token=session.get("access_token")
        if not url or not key: raise RuntimeError("Supabase 연결 설정이 필요합니다.")
        if not token: raise RuntimeError("먼저 관리자 로그인을 해주세요.")
        r=requests.post(url+"/functions/v1/admin-users",
            headers={"apikey":key,"Authorization":"Bearer "+token,"Content-Type":"application/json"},
            json=payload,timeout=30)
        try: data=r.json()
        except Exception: data={}
        if r.status_code>=400:
            raise RuntimeError(data.get("error") or f"관리자 API 오류 HTTP {r.status_code}")
        return data
    def list_users(self,search=""):
        data=self.request({"action":"list","page":1,"perPage":100})
        users=data.get("users",[])
        q=search.strip().lower()
        if q:
            users=[u for u in users if q in (u.get("email","")+" "+u.get("user_metadata",{}).get("full_name","")+" "+u.get("user_metadata",{}).get("nickname","")).lower()]
        return users
    def update_profile(self,user_id,profile):
        return self.request({"action":"update_profile","user_id":user_id,"profile":profile})
    def delete_user(self,user_id):
        return self.request({"action":"delete_user","user_id":user_id,"confirmation":"DELETE_MEMBER"})
    def ban_user(self,user_id,duration):
        return self.request({"action":"ban_user","user_id":user_id,"duration":duration})
    def unban_user(self,user_id):
        return self.request({"action":"unban_user","user_id":user_id})
    def list_data(self):
        data=self.request({"action":"list_data"})
        return data.get("records",[])
    def restore_data(self,records):
        return self.request({"action":"restore_data","records":records})

class GitHubService:
    def __init__(self,store): self.store=store
    def _get(self,path):
        repo=self.store.load().get("github_repo","hongjw321/moamoa")
        if not repo or "/" not in repo: raise RuntimeError("GitHub 저장소 형식은 owner/repo 입니다.")
        token=self.store.github_token()
        headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
        if token: headers["Authorization"]="Bearer "+token
        endpoint="https://api.github.com/repos/"+repo
        if path: endpoint+="/"+path.lstrip("/")
        r=requests.get(endpoint,headers=headers,timeout=15)
        if r.status_code>=400: raise RuntimeError(f"GitHub API 오류 HTTP {r.status_code}: {r.text[:240]}")
        return r.json()
    def repo_info(self): return self._get("")
    def latest_runs(self): return self._get("actions/runs?per_page=8").get("workflow_runs",[])
