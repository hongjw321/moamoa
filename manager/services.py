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

class SupabaseService:
    def __init__(self,cfg): self.cfg=cfg
    def health(self):
        url=self.cfg.get("supabase_url","").rstrip("/")
        key=self.cfg.get("supabase_anon_key","")
        if not url or not key: raise RuntimeError("설정 화면에서 Supabase URL과 공개 키를 먼저 저장하세요.")
        r=requests.get(url+"/auth/v1/health",headers={"apikey":key},timeout=12)
        if r.status_code>=400: raise RuntimeError(f"Supabase 응답 오류: HTTP {r.status_code}")
        return True

class GitHubService:
    def __init__(self,store): self.store=store
    def _get(self,path):
        repo=SettingsStore().load().get("github_repo","hongjw321/moamoa")
        if not repo or "/" not in repo: raise RuntimeError("GitHub 저장소 형식은 owner/repo 입니다.")
        token=self.store.github_token()
        headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
        if token: headers["Authorization"]="Bearer "+token
        r=requests.get("https://api.github.com/repos/"+repo+"/"+path,headers=headers,timeout=15)
        if r.status_code>=400: raise RuntimeError(f"GitHub API 오류 HTTP {r.status_code}: {r.text[:240]}")
        return r.json()
    def repo_info(self): return self._get("")
    def latest_runs(self): return self._get("actions/runs?per_page=8").get("workflow_runs",[])
