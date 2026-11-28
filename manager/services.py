import json, os, hashlib
from pathlib import Path
import requests
import keyring

APP_NAME="MOAMOA_MANAGER"
def config_path():
    base=Path(os.getenv("APPDATA",Path.home()))/"MOAMOA Manager"
    base.mkdir(parents=True,exist_ok=True)
    return base/"settings.json"

class SettingsStore:
    def backup_dir(self):
        folder=config_path().parent/"Backups"
        folder.mkdir(parents=True,exist_ok=True)
        return folder
    def load_backup_history(self):
        path=config_path().parent/"backup-history.json"
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data,list) else []
        except Exception:
            return []
    def record_backup(self,path,record_count,label="수동 백업"):
        from datetime import datetime
        history=self.load_backup_history()
        history.insert(0,{"path":str(path),"record_count":int(record_count),
                          "label":str(label),"created_at":datetime.now().astimezone().isoformat()})
        history=history[:100]
        (config_path().parent/"backup-history.json").write_text(
            json.dumps(history,ensure_ascii=False,indent=2),encoding="utf-8")
        return history
    def create_local_backup(self,records,label="자동 안전 백업"):
        from datetime import datetime, timezone
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        path=self.backup_dir()/f"MOAMOA_backup_{stamp}.json"
        canonical=json.dumps(records,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
        backup={"format":"MOAMOA_DATA_BACKUP","version":1,
                "created_at":datetime.now(timezone.utc).isoformat(),"records":records,
                "sha256":hashlib.sha256(canonical).hexdigest()}
        path.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding="utf-8")
        self.record_backup(path,len(records),label)
        return str(path)
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
    def load_security_events(self):
        path=config_path().parent/"security-events.json"
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data,list) else []
        except Exception: return []
    def record_security_event(self,email,result,reason=""):
        from datetime import datetime
        rows=self.load_security_events()
        rows.insert(0,{"created_at":datetime.now().astimezone().isoformat(),
                       "email":str(email or "")[:254],"result":str(result)[:20],
                       "reason":str(reason or "")[:300]})
        path=config_path().parent/"security-events.json"
        path.write_text(json.dumps(rows[:300],ensure_ascii=False,indent=2),encoding="utf-8")
        return rows[:300]
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
    def get_admin_info(self):
        return self.request({"action":"get_admin_info"})
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
        if r.status_code==401:
            self.store.clear_admin_session()
            raise RuntimeError(data.get("error") or "로그인 세션이 만료되었습니다. 다시 로그인해 주세요.")
        if r.status_code>=400:
            raise RuntimeError(data.get("error") or f"관리자 API 오류 HTTP {r.status_code}")
        return data
    def list_users_page(self,page=1,per_page=100,search=""):
        q=search.strip()
        if q:
            data=self.request({"action":"search","query":q,"page":int(page),"perPage":int(per_page)})
        else:
            data=self.request({"action":"list","page":int(page),"perPage":int(per_page)})
        return {"users":data.get("users",[]),"page":data.get("page",page),
                "per_page":data.get("perPage",per_page),"total":data.get("total"),
                "search_limited":data.get("search_limited",False)}
    def list_users(self,search=""):
        return self.list_users_page(1,100,search).get("users",[])
    def list_all_users(self):
        all_users=[]
        page=1
        while page<=10000:
            result=self.list_users_page(page,100,"")
            users=result.get("users",[])
            all_users.extend(users)
            total=result.get("total")
            if total is not None and page*100>=int(total):
                break
            if len(users)<100:
                break
            page+=1
        return all_users
    def update_profile(self,user_id,profile):
        return self.request({"action":"update_profile","user_id":user_id,"profile":profile})
    def delete_user(self,user_id):
        return self.request({"action":"delete_user","user_id":user_id,"confirmation":"DELETE_MEMBER"})
    def ban_user(self,user_id,duration):
        return self.request({"action":"ban_user","user_id":user_id,"duration":duration})
    def unban_user(self,user_id):
        return self.request({"action":"unban_user","user_id":user_id})
    def batch_member_action(self,user_ids,operation,duration="24h"):
        return self.request({"action":"batch_member_action","user_ids":user_ids,
                             "operation":operation,"duration":duration})
    def list_data(self):
        data=self.request({"action":"list_data"})
        return data.get("records",[])
    def restore_data(self,records):
        return self.request({"action":"restore_data","records":records})
    def list_announcements(self):
        return self.request({"action":"list_announcements"}).get("announcements",[])
    def save_announcement(self,announcement_id,title,body,is_published):
        return self.request({"action":"save_announcement","id":announcement_id,"title":title,
                             "body":body,"is_published":is_published})
    def delete_announcement(self,announcement_id):
        return self.request({"action":"delete_announcement","id":announcement_id})
    def list_activity_logs(self):
        return self.request({"action":"list_activity_logs"}).get("logs",[])
    def list_activity_analytics(self,days=365):
        data=self.request({"action":"list_activity_logs","days":int(days),"analytics":True})
        return data.get("logs",[])
    def list_error_logs(self):
        return self.request({"action":"list_error_logs"}).get("logs",[])
    def list_admin_accounts(self):
        return self.request({"action":"list_admin_accounts"}).get("admins",[])
    def list_admin_activity_logs(self):
        return self.request({"action":"list_admin_activity_logs"}).get("logs",[])
    def add_admin_account(self,email):
        return self.request({"action":"add_admin_account","email":email})
    def set_admin_capabilities(self,email,capabilities):
        return self.request({"action":"set_admin_capabilities","email":email,"capabilities":capabilities})
    def set_admin_active(self,email,is_active):
        return self.request({"action":"set_admin_active","email":email,"is_active":is_active})
    def report_error(self,source,message):
        return self.request({"action":"report_error","source":source,"message":message})

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
