import sys
from datetime import datetime, timezone
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QLineEdit, QMessageBox, QTextEdit,
    QFormLayout, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QInputDialog)
from services import SettingsStore, SupabaseService, GitHubService, AdminUsersService

PINK = "#E66D98"
DARK = "#493443"
MUTED = "#8C7885"

class Worker(QThread):
    done = Signal(object, object)
    def __init__(self, fn):
        super().__init__(); self.fn = fn
    def run(self):
        try: self.done.emit(self.fn(), None)
        except Exception as exc: self.done.emit(None, str(exc))

class Card(QFrame):
    def __init__(self, title, value="확인 전", subtitle=""):
        super().__init__(); self.setObjectName("card")
        lay=QVBoxLayout(self); lay.setContentsMargins(18,16,18,16)
        self.title=QLabel(title); self.title.setObjectName("muted")
        self.value=QLabel(value); self.value.setObjectName("cardValue")
        self.sub=QLabel(subtitle); self.sub.setObjectName("muted")
        lay.addWidget(self.title); lay.addWidget(self.value); lay.addWidget(self.sub)
    def set_value(self, value, subtitle=None):
        self.value.setText(str(value))
        if subtitle is not None: self.sub.setText(subtitle)

class Manager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOAMOA MANAGER")
        self.resize(1180, 760); self.setMinimumSize(900, 620)
        self.store=SettingsStore(); self.cfg=self.store.load()
        self.github=GitHubService(self.store); self.supabase=SupabaseService(self.cfg); self.admin_users=AdminUsersService(self.cfg,self.store)
        self.workers=[]
        # Create shared widgets before page builders reference them.
        self.log=QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(95)
        self.log.setPlaceholderText("작업 기록이 여기에 표시됩니다.")
        root=QWidget(); self.setCentralWidget(root)
        outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        side=QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(225)
        sl=QVBoxLayout(side); sl.setContentsMargins(18,24,18,20); sl.setSpacing(9)
        brand=QLabel("MOAMOA"); brand.setObjectName("brand")
        sl.addWidget(brand); sl.addWidget(QLabel("MANAGER  ·  ADMIN DESK"))
        sl.addSpacing(22)
        self.stack=QStackedWidget()
        self.pages=[]
        for label, page in [("대시보드",self.dashboard_page()),("회원 관리",self.members_page()),("데이터 관리",self.data_page()),("GitHub 배포",self.github_page()),("환경 설정",self.settings_page())]:
            b=QPushButton(label); b.setObjectName("nav"); b.setCheckable(True)
            b.clicked.connect(lambda checked=False, i=len(self.pages): self.go(i))
            sl.addWidget(b); self.pages.append((b,page)); self.stack.addWidget(page)
        sl.addStretch()
        note=QLabel("안전한 운영을 위한\nMOAMOA 관리 도구"); note.setObjectName("sideNote"); sl.addWidget(note)
        outer.addWidget(side); content=QWidget(); cl=QVBoxLayout(content); cl.setContentsMargins(28,24,28,24)
        self.header=QLabel("대시보드"); self.header.setObjectName("pageTitle"); cl.addWidget(self.header)
        self.status=QLabel("설정에서 Supabase와 GitHub를 연결해 주세요."); self.status.setObjectName("muted"); cl.addWidget(self.status)
        cl.addSpacing(16); cl.addWidget(self.stack); outer.addWidget(content,1)
        self.go(0); self.refresh_dashboard()

    def title_block(self, title, desc):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,12)
        t=QLabel(title); t.setObjectName("sectionTitle"); d=QLabel(desc); d.setObjectName("muted")
        l.addWidget(t); l.addWidget(d); return w
    def button(self, text, fn, primary=False):
        b=QPushButton(text); b.setObjectName("primary" if primary else "action"); b.clicked.connect(fn); return b
    def go(self, i):
        self.stack.setCurrentIndex(i); self.header.setText(["대시보드","회원 관리","데이터 관리","GitHub 배포","환경 설정"][i])
        for n,(b,_) in enumerate(self.pages): b.setChecked(n==i)
    def run_async(self, fn, callback):
        w=Worker(fn); self.workers.append(w)
        w.done.connect(lambda result,error: (callback(result,error), self.workers.remove(w) if w in self.workers else None))
        w.start()
    def log_line(self, text):
        self.log.append(text); self.status.setText(text)
    def dashboard_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(self.title_block("운영 현황","모아모아 홈페이지와 외부 서비스 연결 상태를 확인합니다."))
        row=QHBoxLayout()
        self.sup_card=Card("SUPABASE 연결"); self.gh_card=Card("GITHUB 저장소"); self.pages_card=Card("최근 배포")
        for c in (self.sup_card,self.gh_card,self.pages_card): row.addWidget(c)
        l.addLayout(row)
        l.addWidget(self.button("전체 연결 상태 확인",self.refresh_dashboard,True))
        l.addWidget(QLabel("최근 작업")); l.addWidget(self.log)
        l.addStretch(); return w
    def refresh_dashboard(self):
        self.sup_card.set_value("확인 중...")
        self.gh_card.set_value("확인 중...")
        self.run_async(self.supabase.health, lambda r,e: self.sup_card.set_value("연결 정상" if r else "연결 실패", "Supabase Auth API 응답" if r else (e or "주소와 공개 키를 확인하세요.")))
        def gh():
            info=self.github.repo_info()
            runs=self.github.latest_runs()
            return info,runs
        def done(result,error):
            if error:
                self.gh_card.set_value("연결 실패",error); self.pages_card.set_value("확인 불가"); self.log_line("GitHub: "+error); return
            info,runs=result
            self.gh_card.set_value(info.get("full_name","연결됨"),"기본 브랜치: "+info.get("default_branch","-"))
            if runs:
                run=runs[0]; self.pages_card.set_value(run.get("conclusion") or run.get("status"),run.get("name","GitHub Actions"))
            else: self.pages_card.set_value("기록 없음","Actions 실행 내역 없음")
            self.log_line("GitHub 저장소 연결 확인 완료")
        self.run_async(gh,done)
    def members_page(self):
        w=QWidget(); l=QVBoxLayout(w)
        l.addWidget(self.title_block("회원 관리","관리자 계정으로 인증한 뒤 실제 Supabase 회원 정보를 조회하고 관리합니다."))
        auth=QGroupBox("관리자 로그인"); form=QFormLayout(auth)
        self.admin_email=QLineEdit(); self.admin_email.setPlaceholderText("관리자 이메일")
        self.admin_password=QLineEdit(); self.admin_password.setEchoMode(QLineEdit.Password); self.admin_password.setPlaceholderText("Supabase 로그인 비밀번호")
        session=self.store.admin_session()
        if session.get("email"): self.admin_email.setText(session["email"])
        form.addRow("이메일",self.admin_email); form.addRow("비밀번호",self.admin_password)
        authrow=QHBoxLayout()
        authrow.addWidget(self.button("관리자 로그인",self.admin_login,True))
        authrow.addWidget(self.button("로그아웃",self.admin_logout))
        authrow.addStretch(); form.addRow(authrow); l.addWidget(auth)
        self.member_status=QLabel("관리자 로그인 후 회원 목록을 불러올 수 있습니다."); self.member_status.setObjectName("muted"); l.addWidget(self.member_status)
        tools=QHBoxLayout()
        self.member_search=QLineEdit(); self.member_search.setPlaceholderText("이메일 / 이름 / 닉네임 검색")
        self.member_search.returnPressed.connect(self.load_members)
        tools.addWidget(self.member_search,1)
        tools.addWidget(self.button("검색 및 새로고침",self.load_members,True))
        tools.addWidget(self.button("회원 정보 수정",self.edit_member))
        tools.addWidget(self.button("회원 삭제",self.delete_member))
        l.addLayout(tools)
        self.members_table=QTableWidget(0,8)
        self.members_table.setHorizontalHeaderLabels(["이메일","이름","닉네임","휴대폰","이메일 인증","계정 상태","가입일","최근 로그인"])
        self.members_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._member_map={}
        self.members_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.members_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.members_table.setAlternatingRowColors(True)
        l.addWidget(self.members_table,1)
        l.addWidget(QLabel("보안: 관리자 이메일 허용 목록(MOAMOA_ADMIN_EMAILS)에 등록된 계정만 접근할 수 있습니다. service_role 키는 서버에만 보관됩니다."))
        return w
    def admin_login(self):
        email=self.admin_email.text().strip(); password=self.admin_password.text()
        if not email or not password:
            QMessageBox.warning(self,"입력 확인","관리자 이메일과 비밀번호를 입력해 주세요."); return
        self.member_status.setText("로그인 확인 중...")
        def work():
            user=self.supabase.admin_login(email,password,self.store)
            return self.admin_users.request({"action":"list","page":1,"perPage":1})
        def done(result,error):
            self.admin_password.clear()
            if error:
                self.store.clear_admin_session(); self.member_status.setText("로그인 실패: "+error); return
            self.member_status.setText("관리자 인증 완료 · "+email)
            self.log_line("관리자 인증 완료")
            self.load_members()
        self.run_async(work,done)
        self.admin_password.clear()
    def admin_logout(self):
        self.store.clear_admin_session(); self.members_table.setRowCount(0)
        self.member_status.setText("로그아웃했습니다."); self.log_line("관리자 로그아웃")
    def load_members(self):
        session=self.store.admin_session()
        if not session.get("access_token"):
            self.member_status.setText("먼저 관리자 로그인을 해주세요."); return
        query=self.member_search.text()
        self.member_status.setText("회원 목록을 불러오는 중...")
        def done(users,error):
            if error:
                self.member_status.setText("조회 실패: "+error); return
            self.members_table.setRowCount(len(users))
            self._member_map={u.get('id'):u for u in users}
            for i,u in enumerate(users):
                meta=u.get("user_metadata") or {}
                confirmed=bool(u.get("email_confirmed_at") or u.get("confirmed_at"))
                banned_until=u.get("banned_until")
                account_status="정상"
                if banned_until:
                    try:
                        expiry=datetime.fromisoformat(str(banned_until).replace("Z","+00:00"))
                        if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
                        if expiry > datetime.now(timezone.utc): account_status="차단 중"
                    except Exception:
                        account_status="차단 설정 확인 필요"
                vals=[u.get("email",""),meta.get("full_name",""),meta.get("nickname",""),meta.get("phone",""),"인증 완료" if confirmed else "미인증",account_status,u.get("created_at","")[:10],(u.get("last_sign_in_at") or "-")[:10]]
                for j,v in enumerate(vals):
                    item=QTableWidgetItem(str(v))
                    if j==0: item.setData(Qt.UserRole,u.get("id"))
                    self.members_table.setItem(i,j,item)
            self.member_status.setText(f"회원 {len(users)}명 표시 중 (최대 100명 조회). 인증 여부와 현재 차단 상태를 확인할 수 있습니다.")
            self.log_line(f"회원 목록 {len(users)}명 조회")
        self.run_async(lambda:self.admin_users.list_users(query),done)
    def selected_member(self):
        row=self.members_table.currentRow()
        if row<0: return None
        item=self.members_table.item(row,0)
        if not item: return None
        user_id=item.data(Qt.UserRole)
        return next((u for u in getattr(self,"_member_cache",[]) if u.get("id")==user_id),{"id":user_id,"email":item.text(),"user_metadata":{}})
    def edit_member(self):
        row=self.members_table.currentRow()
        if row<0:
            QMessageBox.information(self,"회원 선택","수정할 회원을 먼저 선택해 주세요."); return
        email=self.members_table.item(row,0).text()
        user_id=self.members_table.item(row,0).data(Qt.UserRole)
        current=getattr(self,"_member_map",{}).get(user_id,{})
        meta=current.get("user_metadata") or {}
        fields=[("이름","full_name"),("닉네임","nickname"),("휴대폰","phone"),("주소","address")]
        profile={}
        for label,key in fields:
            value,ok=QInputDialog.getText(self,"회원 정보 수정",label,text=str(meta.get(key,"")))
            if not ok: return
            profile[key]=value.strip()
        if not profile["full_name"] or not profile["nickname"]:
            QMessageBox.warning(self,"입력 확인","이름과 닉네임은 필수입니다."); return
        self.member_status.setText("회원 정보를 저장하는 중...")
        def done(result,error):
            if error: self.member_status.setText("수정 실패: "+error); return
            self.member_status.setText(email+" 회원 정보 수정 완료"); self.load_members()
        self.run_async(lambda:self.admin_users.update_profile(user_id,profile),done)
    def delete_member(self):
        row=self.members_table.currentRow()
        if row<0:
            QMessageBox.information(self,"회원 선택","삭제할 회원을 먼저 선택해 주세요."); return
        email=self.members_table.item(row,0).text()
        user_id=self.members_table.item(row,0).data(Qt.UserRole)
        if QMessageBox.question(self,"회원 계정 영구 삭제",f"{email} 계정을 영구 삭제할까요?\\n연결된 user_data도 함께 삭제되며 복구할 수 없습니다.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return
        self.member_status.setText("회원 계정을 삭제하는 중...")
        def done(result,error):
            if error: self.member_status.setText("삭제 실패: "+error); return
            self.member_status.setText(email+" 회원 계정 삭제 완료"); self.log_line("회원 계정 삭제: "+email); self.load_members()
        self.run_async(lambda:self.admin_users.delete_user(user_id),done)
    def data_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(self.title_block("데이터 관리","회원별 저장 데이터의 조회·백업·복구 도구를 준비하는 공간입니다."))
        box=QGroupBox("현재 지원 범위"); bl=QVBoxLayout(box)
        for s in ["회원별 데이터 테이블: user_data","접근 제어: Supabase Row Level Security","자동 백업·대량 수정·데이터 삭제: 아직 미구현"]:
            bl.addWidget(QLabel("• "+s))
        l.addWidget(box)
        l.addWidget(self.button("Supabase Table Editor 열기",lambda: QDesktopServices.openUrl(QUrl("https://supabase.com/dashboard/project/gugyczralmtvowfhulqe/editor")),True))
        l.addStretch(); return w
    def github_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(self.title_block("GitHub 배포","저장소 정보와 GitHub Actions 배포 기록을 확인합니다."))
        self.repo_label=QLabel("저장소: hongjw321/moamoa"); self.run_table=QTableWidget(0,4); self.run_table.setHorizontalHeaderLabels(["워크플로","상태","결과","실행 시각"])
        self.run_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        l.addWidget(self.repo_label); l.addWidget(self.run_table)
        row=QHBoxLayout(); row.addWidget(self.button("저장소 열기",lambda: QDesktopServices.openUrl(QUrl("https://github.com/hongjw321/moamoa"))))
        row.addWidget(self.button("Actions 열기",lambda: QDesktopServices.openUrl(QUrl("https://github.com/hongjw321/moamoa/actions"))))
        row.addWidget(self.button("배포 기록 새로고침",self.load_runs,True)); l.addLayout(row); l.addStretch(); return w
    def load_runs(self):
        self.run_async(self.github.latest_runs, self.show_runs)
    def show_runs(self,runs,error):
        if error: self.log_line("Actions 조회 실패: "+error); return
        self.run_table.setRowCount(len(runs))
        for i,x in enumerate(runs):
            vals=[x.get("name",""),x.get("status",""),x.get("conclusion") or "-",x.get("created_at","")]
            for j,v in enumerate(vals): self.run_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.log_line(f"GitHub Actions {len(runs)}건을 불러왔습니다.")
    def settings_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(self.title_block("환경 설정","연결 정보는 이 PC에만 저장됩니다. GitHub 토큰은 Windows 자격 증명 저장소에 보관합니다."))
        form=QFormLayout(); self.url=QLineEdit(self.cfg.get("supabase_url","")); self.url.setPlaceholderText("https://xxxx.supabase.co")
        self.anon=QLineEdit(self.cfg.get("supabase_anon_key","")); self.anon.setEchoMode(QLineEdit.Password); self.anon.setPlaceholderText("Supabase publishable / anon key")
        self.repo=QLineEdit(self.cfg.get("github_repo","hongjw321/moamoa"))
        self.token=QLineEdit(); self.token.setEchoMode(QLineEdit.Password); self.token.setPlaceholderText("GitHub Fine-grained PAT (선택)")
        form.addRow("Supabase URL",self.url); form.addRow("Supabase 공개 키",self.anon); form.addRow("GitHub 저장소",self.repo); form.addRow("GitHub 토큰",self.token)
        l.addLayout(form)
        l.addWidget(QLabel("Supabase service_role / secret 키는 이 프로그램에 입력하지 마세요. GitHub 토큰은 repo 읽기와 Actions 읽기 권한부터 최소 권한으로 발급하세요."))
        l.addWidget(self.button("설정 저장",self.save_settings,True)); l.addWidget(self.button("연결 테스트",self.test_settings))
        l.addStretch(); return w
    def save_settings(self):
        cfg={"supabase_url":self.url.text().strip().rstrip("/"),"supabase_anon_key":self.anon.text().strip(),"github_repo":self.repo.text().strip()}
        self.store.save(cfg)
        if self.token.text().strip(): self.store.save_github_token(self.token.text().strip())
        self.token.clear(); self.cfg=cfg; self.supabase=SupabaseService(cfg); self.github=GitHubService(self.store)
        QMessageBox.information(self,"저장 완료","설정을 이 PC에 저장했습니다. GitHub 토큰은 Windows 자격 증명 저장소에 저장했습니다.")
        self.log_line("설정 저장 완료")
    def test_settings(self):
        self.save_settings(); self.refresh_dashboard()
    def closeEvent(self,event):
        event.accept()

def main():
    app=QApplication(sys.argv); app.setStyle("Fusion")
    app.setStyleSheet("""
    QWidget{font-family:'Malgun Gothic';font-size:13px;color:#493443;background:#FFF9FC}
    #sidebar{background:#FFF0F6;border-right:1px solid #F4D9E4}
    #brand{font-size:25px;font-weight:900;color:#D85F8B}
    #sideNote{color:#A27F91;font-size:11px}
    #pageTitle{font-size:25px;font-weight:800;color:#493443}
    #sectionTitle{font-size:20px;font-weight:800}
    #muted{color:#9B8792;font-size:12px}
    #card{background:white;border:1px solid #F3DDE6;border-radius:16px}
    #cardValue{font-size:19px;font-weight:800;color:#D85F8B}
    QPushButton{border:1px solid #F0D5E0;border-radius:10px;padding:10px 14px;background:white}
    QPushButton:hover{background:#FFF0F6}
    QPushButton#nav{border:0;text-align:left;padding:12px;color:#765D6B;background:transparent}
    QPushButton#nav:checked{background:#F8DCE8;color:#B94470;font-weight:800}
    QPushButton#primary{background:#D85F8B;color:white;border:0;font-weight:700}
    QLineEdit{background:white;border:1px solid #EBD4DE;border-radius:9px;padding:10px}
    QGroupBox{border:1px solid #F0D8E2;border-radius:12px;margin-top:12px;padding:14px;font-weight:700}
    QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px}
    QTableWidget{background:white;border:1px solid #F0D8E2;border-radius:10px;gridline-color:#F7E8EE}
    """)
    win=Manager(); win.show(); sys.exit(app.exec())

if __name__=="__main__": main()
