import sys
import json
import csv
from datetime import datetime, timezone, timedelta
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QLineEdit, QMessageBox, QTextEdit,
    QFormLayout, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QInputDialog, QFileDialog, QScrollArea, QGridLayout, QSizePolicy, QTabWidget, QCheckBox)
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
        lay=QVBoxLayout(self); lay.setContentsMargins(12,10,12,10); lay.setSpacing(5)
        self.title=QLabel(title); self.title.setObjectName("muted"); self.title.setWordWrap(True)
        self.value=QLabel(value); self.value.setObjectName("cardValue"); self.value.setWordWrap(True)
        self.sub=QLabel(subtitle); self.sub.setObjectName("muted"); self.sub.setWordWrap(True)
        lay.addWidget(self.title); lay.addWidget(self.value); lay.addWidget(self.sub)
        self.setMinimumHeight(112); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        for label in (self.title, self.value, self.sub):
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
            label.setMinimumWidth(0)
    def set_value(self, value, subtitle=None):
        self.value.setText(str(value))
        if subtitle is not None: self.sub.setText(subtitle)

class Manager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOAMOA MANAGER")
        self.resize(1180, 760); self.setMinimumSize(680, 500)
        self.store=SettingsStore(); self.cfg=self.store.load()
        self.github=GitHubService(self.store); self.supabase=SupabaseService(self.cfg); self.admin_users=AdminUsersService(self.cfg,self.store)
        self.workers=[]
        # Create shared widgets before page builders reference them.
        self.log=QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(95)
        self.log.setPlaceholderText("작업 기록이 여기에 표시됩니다.")
        root=QWidget(); self.setCentralWidget(root)
        outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        side=QFrame(); side.setObjectName("sidebar"); side.setMinimumWidth(145); side.setMaximumWidth(185)
        sl=QVBoxLayout(side); sl.setContentsMargins(12,20,12,16); sl.setSpacing(8)
        brand=QLabel("MOAMOA"); brand.setObjectName("brand")
        sl.addWidget(brand); sl.addWidget(QLabel("MANAGER  ·  ADMIN DESK"))
        sl.addSpacing(22)
        self.stack=QStackedWidget()
        self.pages=[]
        for label, page in [("대시보드",self.dashboard_page()),("회원 관리",self.members_page()),("데이터 관리",self.data_page()),("운영 관리",self.operations_page()),("관리자 계정",self.admin_accounts_page()),("GitHub 배포",self.github_page()),("환경 설정",self.settings_page())]:
            b=QPushButton(label); b.setObjectName("nav"); b.setCheckable(True)
            b.clicked.connect(lambda checked=False, i=len(self.pages): self.go(i))
            sl.addWidget(b); self.pages.append((b,page)); self.stack.addWidget(page)
        sl.addStretch()
        note=QLabel("안전한 운영을 위한\nMOAMOA 관리 도구"); note.setObjectName("sideNote"); sl.addWidget(note)
        outer.addWidget(side); content=QWidget(); cl=QVBoxLayout(content); cl.setContentsMargins(12,12,12,12)
        self.header=QLabel("대시보드"); self.header.setObjectName("pageTitle"); self.header.setWordWrap(True); cl.addWidget(self.header)
        self.status=QLabel("설정에서 Supabase와 GitHub를 연결해 주세요."); self.status.setObjectName("muted"); self.status.setWordWrap(True); cl.addWidget(self.status)
        self.global_role_status=QLabel("권한: 로그인 필요"); self.global_role_status.setObjectName("roleStatus"); self.global_role_status.setWordWrap(True); cl.addWidget(self.global_role_status)
        cl.addSpacing(16); cl.addWidget(self.stack); outer.addWidget(content,1)
        self.go(0); self.refresh_dashboard()

    def title_block(self, title, desc):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,12)
        t=QLabel(title); t.setObjectName("sectionTitle"); t.setWordWrap(True); d=QLabel(desc); d.setObjectName("muted"); d.setWordWrap(True)
        l.addWidget(t); l.addWidget(d); return w
    def button(self, text, fn, primary=False):
        b=QPushButton(text); b.setObjectName("primary" if primary else "action"); b.clicked.connect(fn); return b
    def go(self, i):
        self.stack.setCurrentIndex(i); self.header.setText(["대시보드","회원 관리","데이터 관리","운영 관리","관리자 계정","GitHub 배포","환경 설정"][i])
        for n,(b,_) in enumerate(self.pages): b.setChecked(n==i)
    def run_async(self, fn, callback):
        w=Worker(fn); self.workers.append(w)
        def completed(result,error):
            if error: self.capture_error(error)
            callback(result,error)
            if w in self.workers: self.workers.remove(w)
        w.done.connect(completed)
        w.start()
    def capture_error(self, message):
        if not self.store.admin_session().get("access_token"): return
        w=Worker(lambda:self.admin_users.report_error("manager",str(message)))
        self.workers.append(w)
        w.done.connect(lambda result,error: self.workers.remove(w) if w in self.workers else None)
        w.start()
    def log_line(self, text):
        self.log.append(text); self.status.setText(text)
    def dashboard_page(self):
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(4,4,4,12); l.setSpacing(10)
        l.addWidget(self.title_block("운영 현황","모아모아 홈페이지와 외부 서비스 연결 상태를 확인합니다."))
        service_grid=QGridLayout(); service_grid.setSpacing(8)
        self.sup_card=Card("SUPABASE 연결"); self.gh_card=Card("GITHUB 저장소"); self.pages_card=Card("최근 배포")
        for i,c in enumerate((self.sup_card,self.gh_card,self.pages_card)):
            service_grid.addWidget(c,i//2,i%2)
        l.addLayout(service_grid)
        l.addWidget(self.title_block("서비스 통계","회원 및 서비스 데이터 기준 · 관리자 로그인 필요"))
        self.stat_users=Card("전체 가입 회원","-","최대 100명 조회 기준")
        self.stat_today=Card("오늘 신규 가입","-","조회된 회원 기준")
        self.stat_verified=Card("이메일 인증 완료","-","조회된 회원 기준")
        self.stat_banned=Card("현재 차단 회원","-","조회된 회원 기준")
        self.stat_owned=Card("보유 캐릭터 합계","-","user_data 최대 500건 기준")
        self.stat_draws=Card("뽑기 기록 합계","-","user_data 최대 500건 기준")
        self.stat_attendance=Card("출석 기록 합계","-","user_data 최대 500건 기준")
        self.stat_cart=Card("장바구니 항목 합계","-","user_data 최대 500건 기준")
        stats_grid=QGridLayout(); stats_grid.setSpacing(8)
        stat_cards=(self.stat_users,self.stat_today,self.stat_verified,self.stat_banned,
                    self.stat_owned,self.stat_draws,self.stat_attendance,self.stat_cart)
        for i,c in enumerate(stat_cards):
            stats_grid.addWidget(c,i//2,i%2)
        l.addLayout(stats_grid)
        l.addWidget(self.button("회원·서비스 통계 새로고침",self.refresh_dashboard_stats,True))
        l.addWidget(self.title_block("기간별 운영 분석","최근 회원 활동 로그 기준 · 최대 200건 · 전체 기간 통계가 아닌 조회된 기록의 집계입니다."))
        analytics_tools=QHBoxLayout()
        self.analytics_days=7
        analytics_tools.addWidget(QLabel("조회 기간"))
        for days,label in ((7,"최근 7일"),(30,"최근 30일"),(90,"최근 90일"),(365,"최근 1년")):
            analytics_tools.addWidget(self.button(label,lambda checked=False,d=days:self.set_analytics_period(d),days==7))
        analytics_tools.addStretch()
        analytics_tools.addWidget(self.button("CSV 내보내기",self.export_activity_analytics_csv))
        analytics_tools.addWidget(self.button("분석 새로고침",self.refresh_activity_analytics))
        l.addLayout(analytics_tools)
        analytics_cards=QGridLayout(); analytics_cards.setSpacing(8)
        self.analytics_total=Card("기간 내 활동 기록","-","최근 활동 로그 기준")
        self.analytics_signups=Card("회원가입 기록","-","활동 로그에 남은 가입")
        self.analytics_logins=Card("로그인 기록","-","활동 로그에 남은 로그인")
        for i,card in enumerate((self.analytics_total,self.analytics_signups,self.analytics_logins)):
            analytics_cards.addWidget(card,0,i)
        l.addLayout(analytics_cards)
        self.analytics_table=QTableWidget(0,4)
        self.analytics_table.setHorizontalHeaderLabels(["날짜","회원가입","로그인","기타 활동"])
        self.analytics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.analytics_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.analytics_table.setAlternatingRowColors(True)
        self.analytics_table.setMaximumHeight(250)
        l.addWidget(self.analytics_table)
        l.addWidget(QLabel("최근 가입 회원"))
        self.recent_members=QTableWidget(0,4)
        self.recent_members.setHorizontalHeaderLabels(["이메일","이름","닉네임","가입일"])
        self.recent_members.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recent_members.setWordWrap(True)
        self.recent_members.verticalHeader().setDefaultSectionSize(34)
        self.recent_members.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_members.setMaximumHeight(190)
        l.addWidget(self.recent_members)
        l.addWidget(self.button("전체 연결 상태 확인",self.refresh_dashboard))
        l.addWidget(QLabel("최근 작업")); l.addWidget(self.log)
        l.addStretch()
        scroll.setWidget(w)
        return scroll
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
        self.refresh_dashboard_stats()
    def set_analytics_period(self, days):
        self.analytics_days=days
        self.refresh_activity_analytics()

    def refresh_activity_analytics(self):
        if not self.store.admin_session().get("access_token"):
            self.analytics_total.set_value("로그인 필요","회원 관리에서 관리자 로그인")
            self.analytics_signups.set_value("로그인 필요")
            self.analytics_logins.set_value("로그인 필요")
            self.analytics_table.setRowCount(0)
            return
        self.analytics_total.set_value("조회 중...")
        self.analytics_signups.set_value("조회 중...")
        self.analytics_logins.set_value("조회 중...")
        self.run_async(self.admin_users.list_activity_logs,self.render_activity_analytics)

    def render_activity_analytics(self, rows, error):
        if error:
            for card in (self.analytics_total,self.analytics_signups,self.analytics_logins):
                card.set_value("조회 실패",error)
            self.analytics_table.setRowCount(0)
            return
        from collections import defaultdict
        days=self.analytics_days
        today=datetime.now().astimezone().date()
        start=today-timedelta(days=days-1)
        daily=defaultdict(lambda:{"signup":0,"login":0,"other":0})
        total=signups=logins=0
        for row in (rows or []):
            stamp=row.get("created_at") or ""
            try:
                day=datetime.fromisoformat(stamp.replace("Z","+00:00")).astimezone().date()
            except Exception:
                continue
            if day<start or day>today:
                continue
            action=str(row.get("action") or "")
            bucket="signup" if "회원가입" in action else ("login" if "로그인" in action else "other")
            daily[day][bucket]+=1
            total+=1
            if bucket=="signup": signups+=1
            elif bucket=="login": logins+=1
        self.analytics_total.set_value(f"{total:,}건",f"최근 {days}일 · 조회된 최대 200건")
        self.analytics_signups.set_value(f"{signups:,}건","회원가입 활동 로그")
        self.analytics_logins.set_value(f"{logins:,}건","로그인 활동 로그")
        self.analytics_table.setRowCount(days)
        for index in range(days):
            day=start+timedelta(days=index)
            values=[day.isoformat(),daily[day]["signup"],daily[day]["login"],daily[day]["other"]]
            for col,value in enumerate(values):
                self.analytics_table.setItem(index,col,QTableWidgetItem(str(value)))
        self.analytics_table.scrollToBottom()
        self.log_line(f"기간별 운영 분석 갱신 완료 · 최근 {days}일 · 활동 {total}건")

    def export_activity_analytics_csv(self):
        if self.analytics_table.rowCount()==0:
            QMessageBox.information(self,"내보내기","먼저 운영 분석을 새로고침해 주세요.")
            return
        path,_=QFileDialog.getSaveFileName(self,"운영 분석 CSV 저장",
            f"MOAMOA_운영분석_{self.analytics_days}일.csv","CSV 파일 (*.csv)")
        if not path:
            return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as file:
                writer=csv.writer(file)
                writer.writerow(["날짜","회원가입","로그인","기타 활동"])
                for row in range(self.analytics_table.rowCount()):
                    writer.writerow([
                        self.analytics_table.item(row,col).text() if self.analytics_table.item(row,col) else ""
                        for col in range(self.analytics_table.columnCount())
                    ])
            QMessageBox.information(self,"내보내기 완료",f"운영 분석 데이터를 저장했습니다.\\n{path}")
            self.log_line(f"운영 분석 CSV 내보내기 완료 · 최근 {self.analytics_days}일")
        except Exception as exc:
            QMessageBox.critical(self,"내보내기 실패",str(exc))

    def refresh_dashboard_stats(self):
        session=self.store.admin_session()
        if not session.get("access_token"):
            for card in (self.stat_users,self.stat_today,self.stat_verified,self.stat_banned,
                         self.stat_owned,self.stat_draws,self.stat_attendance,self.stat_cart):
                card.set_value("로그인 필요","회원 관리에서 관리자 로그인")
            self.recent_members.setRowCount(0)
            return
        for card in (self.stat_users,self.stat_today,self.stat_verified,self.stat_banned,
                     self.stat_owned,self.stat_draws,self.stat_attendance,self.stat_cart):
            card.set_value("조회 중...")
        self.refresh_activity_analytics()
        def work():
            users=self.admin_users.list_users("")
            records=self.admin_users.list_data()
            return users,records
        def done(result,error):
            if error:
                for card in (self.stat_users,self.stat_today,self.stat_verified,self.stat_banned,
                             self.stat_owned,self.stat_draws,self.stat_attendance,self.stat_cart):
                    card.set_value("조회 실패",error)
                self.log_line("대시보드 통계 조회 실패: "+error)
                return
            users,records=result
            today=datetime.now().date()
            today_count=0; verified=0; banned=0
            for u in users:
                created=u.get("created_at") or ""
                try:
                    if datetime.fromisoformat(created.replace("Z","+00:00")).astimezone().date()==today:
                        today_count+=1
                except Exception: pass
                if u.get("email_confirmed_at"): verified+=1
                until=u.get("banned_until") or ""
                try:
                    expiry=datetime.fromisoformat(until.replace("Z","+00:00"))
                    if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
                    if expiry>datetime.now(timezone.utc): banned+=1
                except Exception: pass
            self.stat_users.set_value(f"{len(users):,}명","최대 100명 조회 기준")
            self.stat_today.set_value(f"{today_count:,}명","오늘 가입 · 조회된 회원 기준")
            self.stat_verified.set_value(f"{verified:,}명","조회된 회원 기준")
            self.stat_banned.set_value(f"{banned:,}명","현재 차단 중 · 조회된 회원 기준")
            totals={"owned":0,"history":0,"attendance":0,"cart":0}
            for record in records:
                payload=record.get("payload") or {}
                for key in totals:
                    value=payload.get(key) or []
                    if isinstance(value,list): totals[key]+=len(value)
            self.stat_owned.set_value(f"{totals['owned']:,}개","최대 500건 조회 기준")
            self.stat_draws.set_value(f"{totals['history']:,}건","최대 500건 조회 기준")
            self.stat_attendance.set_value(f"{totals['attendance']:,}건","최대 500건 조회 기준")
            self.stat_cart.set_value(f"{totals['cart']:,}개","최대 500건 조회 기준")
            recent=sorted(users,key=lambda u:u.get("created_at") or "",reverse=True)[:5]
            self.recent_members.setRowCount(len(recent))
            for i,u in enumerate(recent):
                meta=u.get("user_metadata") or {}
                vals=[u.get("email",""),meta.get("full_name",""),meta.get("nickname",""),(u.get("created_at") or "-")[:10]]
                for j,value in enumerate(vals): self.recent_members.setItem(i,j,QTableWidgetItem(str(value)))
            self.log_line(f"대시보드 통계 갱신 완료 · 회원 {len(users)}명 / 데이터 {len(records)}건")
        self.run_async(work,done)
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
        self.admin_role_status=QLabel("권한: 로그인 필요"); self.admin_role_status.setObjectName("muted"); l.addWidget(self.admin_role_status)
        tools=QHBoxLayout()
        self.member_search=QLineEdit(); self.member_search.setPlaceholderText("이메일 / 이름 / 닉네임 검색")
        self.member_search.returnPressed.connect(self.load_members)
        tools.addWidget(self.member_search,1)
        tools.addWidget(self.button("검색 및 새로고침",self.load_members,True))
        tools.addWidget(self.button("회원 CSV 내보내기",self.export_members_csv))
        tools.addWidget(self.button("회원 정보 수정",self.edit_member))
        tools.addWidget(self.button("회원 삭제",self.delete_member))
        tools.addWidget(self.button("회원 차단",self.ban_member))
        tools.addWidget(self.button("차단 해제",self.unban_member))
        l.addLayout(tools)
        page_tools=QHBoxLayout()
        self.member_page=1
        self.member_page_status=QLabel("페이지 정보 대기 중")
        page_tools.addWidget(self.member_page_status)
        page_tools.addStretch()
        page_tools.addWidget(self.button("이전 페이지",self.previous_member_page))
        page_tools.addWidget(self.button("다음 페이지",self.next_member_page))
        l.addLayout(page_tools)
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
            self.supabase.admin_login(email,password,self.store)
            info=self.admin_users.get_admin_info()
            self.admin_users.request({"action":"list","page":1,"perPage":1})
            return info
        def done(result,error):
            self.admin_password.clear()
            if error:
                self.store.clear_admin_session(); self.member_status.setText("로그인 실패: "+error)
                self.admin_role_status.setText("권한: 확인 실패")
                self.global_role_status.setText("권한: 확인 실패")
                return
            role=result.get("role","admin")
            role_label="최고 관리자" if role=="super_admin" else "일반 관리자"
            self.member_status.setText("관리자 인증 완료 · "+email)
            self.admin_role_status.setText(f"권한: {role_label} · 서버에서 권한을 검증합니다.")
            self.global_role_status.setText(f"권한: {role_label} · 서버 검증")
            self.log_line("관리자 인증 완료 · "+role_label)
            self.load_members()
            self.refresh_dashboard_stats()
        self.run_async(work,done)
        self.admin_password.clear()
    def admin_logout(self):
        self.store.clear_admin_session(); self.members_table.setRowCount(0)
        self.member_status.setText("로그아웃했습니다.")
        self.admin_role_status.setText("권한: 로그인 필요")
        self.global_role_status.setText("권한: 로그인 필요")
        self.log_line("관리자 로그아웃")
    def previous_member_page(self):
        if self.member_page>1:
            self.member_page-=1
            self.load_members()

    def next_member_page(self):
        total=getattr(self,"_member_total",None)
        per_page=100
        if total is not None and self.member_page*per_page>=total:
            return
        self.member_page+=1
        self.load_members()

    def load_members(self):
        session=self.store.admin_session()
        if not session.get("access_token"):
            self.member_status.setText("먼저 관리자 로그인을 해주세요."); return
        query=self.member_search.text()
        if query != getattr(self,"_member_last_query",""):
            self.member_page=1
            self._member_last_query=query
        self.member_status.setText(f"{self.member_page}페이지 회원 목록을 불러오는 중...")
        def done(result,error):
            if error:
                self.member_status.setText("조회 실패: "+error); return
            users=result.get("users",[])
            self._member_total=result.get("total")
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
            total_text=f"{self._member_total:,}명" if self._member_total is not None else "전체 인원 확인 불가"
            self.member_page_status.setText(f"{self.member_page}페이지 · {len(users)}명 표시 · 전체 {total_text}")
            self.member_status.setText(f"회원 {len(users)}명 표시 중 · 페이지당 최대 100명. 검색은 현재 페이지에서 적용됩니다.")
            self.log_line(f"회원 목록 {self.member_page}페이지 · {len(users)}명 조회")
        self.run_async(lambda:self.admin_users.list_users_page(self.member_page,100,query),done)
    def export_members_csv(self):
        if self.members_table.rowCount()==0:
            QMessageBox.information(self,"내보낼 회원 없음","먼저 회원 목록을 조회해 주세요.")
            return
        path,_=QFileDialog.getSaveFileName(self,"회원 목록 CSV 저장","MOAMOA_회원목록.csv","CSV 파일 (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as file:
                writer=csv.writer(file)
                writer.writerow(["이메일","이름","닉네임","휴대폰","이메일 인증","계정 상태","가입일","최근 로그인"])
                for row in range(self.members_table.rowCount()):
                    writer.writerow([
                        self.members_table.item(row,col).text() if self.members_table.item(row,col) else ""
                        for col in range(self.members_table.columnCount())
                    ])
            self.member_status.setText(f"회원 목록 CSV 저장 완료 · {self.members_table.rowCount()}명")
            QMessageBox.information(self,"내보내기 완료",f"회원 {self.members_table.rowCount()}명의 목록을 저장했습니다.\\n{path}")
            self.log_line(f"회원 목록 CSV 내보내기 완료 · {self.members_table.rowCount()}명")
        except Exception as exc:
            QMessageBox.warning(self,"내보내기 실패",str(exc))

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
    def ban_member(self):
        row=self.members_table.currentRow()
        if row<0:
            QMessageBox.information(self,"회원 선택","차단할 회원을 먼저 선택해 주세요."); return
        user_id=self.members_table.item(row,0).data(Qt.UserRole)
        email=self.members_table.item(row,0).text()
        current=getattr(self,"_member_map",{}).get(user_id,{})
        banned_until=current.get("banned_until") or ""
        if banned_until:
            try:
                expiry=datetime.fromisoformat(str(banned_until).replace("Z","+00:00"))
                if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
                if expiry > datetime.now(timezone.utc):
                    QMessageBox.information(self,"이미 차단된 회원","이 회원은 이미 차단 중입니다. 먼저 차단 해제를 진행해 주세요."); return
            except Exception:
                pass
        choices=["24시간","7일","30일","장기 차단(약 100년)"]
        choice,ok=QInputDialog.getItem(self,"회원 차단",f"{email} 회원의 차단 기간을 선택하세요.",choices,0,False)
        if not ok: return
        duration={"24시간":"24h","7일":"168h","30일":"720h","장기 차단(약 100년)":"876000h"}[choice]
        if QMessageBox.question(self,"회원 차단 확인",f"{email} 회원을 {choice} 동안 차단할까요?\n차단 중에는 해당 회원의 로그인 및 인증된 세션 이용이 제한됩니다.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return
        self.member_status.setText("회원 차단을 적용하는 중...")
        def done(result,error):
            if error: self.member_status.setText("차단 실패: "+error); QMessageBox.warning(self,"차단 실패",error); return
            self.log_line(f"회원 차단 적용: {email} ({choice})")
            self.load_members()
        self.run_async(lambda:self.admin_users.ban_user(user_id,duration),done)
    def unban_member(self):
        row=self.members_table.currentRow()
        if row<0:
            QMessageBox.information(self,"회원 선택","차단 해제할 회원을 먼저 선택해 주세요."); return
        user_id=self.members_table.item(row,0).data(Qt.UserRole)
        email=self.members_table.item(row,0).text()
        current=getattr(self,"_member_map",{}).get(user_id,{})
        banned_until=current.get("banned_until") or ""
        active=False
        try:
            expiry=datetime.fromisoformat(str(banned_until).replace("Z","+00:00"))
            if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
            active=expiry > datetime.now(timezone.utc)
        except Exception:
            pass
        if not active:
            QMessageBox.information(self,"차단 상태","선택한 회원은 현재 차단 중이 아닙니다."); return
        if QMessageBox.question(self,"차단 해제 확인",f"{email} 회원의 차단을 해제할까요?",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return
        self.member_status.setText("차단을 해제하는 중...")
        def done(result,error):
            if error: self.member_status.setText("차단 해제 실패: "+error); QMessageBox.warning(self,"차단 해제 실패",error); return
            self.log_line("회원 차단 해제: "+email)
            self.load_members()
        self.run_async(lambda:self.admin_users.unban_user(user_id),done)
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
        w=QWidget(); l=QVBoxLayout(w)
        l.addWidget(self.title_block("데이터 관리","회원별 보유 캐릭터·뽑기·출석 데이터를 조회하고 JSON 파일로 백업하거나 복구합니다."))
        info=QLabel("안내: 백업 파일에는 회원별 서비스 데이터가 포함됩니다. 안전한 장소에 보관하고 외부에 공유하지 마세요.")
        info.setObjectName("muted"); l.addWidget(info)
        self.data_status=QLabel("관리자 로그인 후 데이터 목록을 불러올 수 있습니다.")
        self.data_status.setObjectName("muted"); l.addWidget(self.data_status)
        tools=QHBoxLayout()
        tools.addWidget(self.button("데이터 새로고침",self.load_data,True))
        tools.addWidget(self.button("선택 회원 백업",lambda:self.export_data(True)))
        tools.addWidget(self.button("전체 데이터 백업",lambda:self.export_data(False)))
        tools.addWidget(self.button("백업 파일 복구",self.import_data))
        l.addLayout(tools)
        self.data_table=QTableWidget(0,7)
        self.data_table.setHorizontalHeaderLabels(["회원 ID","사용 여부","보유 캐릭터","뽑기 기록","출석 기록","장바구니","최근 수정"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setAlternatingRowColors(True)
        l.addWidget(self.data_table,1)
        l.addWidget(self.button("Supabase Table Editor 열기",lambda: QDesktopServices.openUrl(QUrl("https://supabase.com/dashboard/project/gugyczralmtvowfhulqe/editor"))))
        self._data_records=[]
        return w
    def load_data(self):
        session=self.store.admin_session()
        if not session.get("access_token"):
            self.data_status.setText("먼저 회원 관리 페이지에서 관리자 로그인을 해주세요."); return
        self.data_status.setText("회원 데이터를 불러오는 중...")
        def done(records,error):
            if error:
                self.data_status.setText("데이터 조회 실패: "+error); return
            self._data_records=records
            self.data_table.setRowCount(len(records))
            for i,record in enumerate(records):
                payload=record.get("payload") or {}
                vals=[record.get("user_id",""),"사용함" if payload.get("used") else "미사용",
                    len(payload.get("owned") or []),len(payload.get("history") or []),
                    len(payload.get("attendance") or []),len(payload.get("cart") or []),
                    str(record.get("updated_at") or "-")[:19].replace("T"," ")]
                for j,value in enumerate(vals):
                    item=QTableWidgetItem(str(value))
                    if j==0: item.setData(Qt.UserRole,record.get("user_id"))
                    self.data_table.setItem(i,j,item)
            self.data_status.setText(f"회원 데이터 {len(records)}건 조회 완료 (한 번에 최대 500건).")
            self.log_line(f"회원 데이터 {len(records)}건 조회")
        self.run_async(self.admin_users.list_data,done)
    def export_data(self,selected_only=False):
        records=self._data_records
        if selected_only:
            row=self.data_table.currentRow()
            if row<0:
                QMessageBox.information(self,"회원 선택","백업할 회원의 행을 먼저 선택해 주세요."); return
            user_id=self.data_table.item(row,0).data(Qt.UserRole)
            records=[r for r in records if r.get("user_id")==user_id]
        if not records:
            QMessageBox.information(self,"백업할 데이터 없음","먼저 데이터 새로고침을 눌러 데이터를 불러와 주세요."); return
        path,_=QFileDialog.getSaveFileName(self,"MOAMOA 데이터 백업 저장","moamoa-backup.json","JSON 파일 (*.json)")
        if not path: return
        backup={"format":"MOAMOA_DATA_BACKUP","version":1,"created_at":datetime.now(timezone.utc).isoformat(),"records":records}
        try:
            with open(path,"w",encoding="utf-8") as f: json.dump(backup,f,ensure_ascii=False,indent=2)
            self.data_status.setText(f"백업 저장 완료: {len(records)}건")
            self.log_line(f"회원 데이터 백업 저장: {len(records)}건")
            QMessageBox.information(self,"백업 완료",f"{len(records)}건의 데이터를 백업했습니다.\n{path}")
        except Exception as exc:
            QMessageBox.warning(self,"백업 실패",str(exc))
    def import_data(self):
        path,_=QFileDialog.getOpenFileName(self,"MOAMOA 백업 파일 선택","","JSON 파일 (*.json)")
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f: backup=json.load(f)
            if backup.get("format")!="MOAMOA_DATA_BACKUP" or backup.get("version")!=1 or not isinstance(backup.get("records"),list):
                raise ValueError("MOAMOA 백업 파일 형식이 올바르지 않습니다.")
            records=backup["records"]
            if not records or len(records)>500: raise ValueError("복구 가능한 데이터는 1~500건입니다.")
            for item in records:
                if not isinstance(item,dict) or not item.get("user_id") or not isinstance(item.get("payload"),dict):
                    raise ValueError("백업 파일의 회원 ID 또는 payload 형식이 올바르지 않습니다.")
        except Exception as exc:
            QMessageBox.warning(self,"백업 파일 확인",str(exc)); return
        answer=QMessageBox.question(self,"데이터 복구 확인",
            f"{len(records)}건의 회원 데이터를 복구할까요?\n같은 회원의 기존 데이터는 백업 파일 내용으로 덮어씁니다.\n복구 전에 현재 데이터를 먼저 백업하는 것을 권장합니다.",
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if answer!=QMessageBox.Yes: return
        self.data_status.setText("데이터를 복구하는 중...")
        def done(result,error):
            if error:
                self.data_status.setText("복구 실패: "+error); QMessageBox.warning(self,"복구 실패",error); return
            self.data_status.setText(f"데이터 복구 완료: {result.get('restored',0)}건")
            self.log_line(f"회원 데이터 복구 완료: {result.get('restored',0)}건")
            self.load_data()
            QMessageBox.information(self,"복구 완료",f"{result.get('restored',0)}건의 데이터를 복구했습니다.")
        self.run_async(lambda:self.admin_users.restore_data(records),done)
    def operations_page(self):
        w=QWidget(); outer=QVBoxLayout(w)
        outer.addWidget(self.title_block("운영 관리","공지사항을 게시하고 회원 활동 및 시스템 오류 이력을 확인합니다."))
        self.ops_tabs=QTabWidget()
        ann=QWidget(); al=QVBoxLayout(ann)
        self.announcement_status=QLabel("관리자 로그인 후 공지사항을 관리할 수 있습니다."); self.announcement_status.setObjectName("muted")
        al.addWidget(self.announcement_status)
        self.announcement_table=QTableWidget(0,3)
        self.announcement_table.setHorizontalHeaderLabels(["제목","게시 상태","작성일"])
        self.announcement_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.announcement_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.announcement_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.announcement_table.itemSelectionChanged.connect(self.select_announcement)
        al.addWidget(self.announcement_table,1)
        form=QFormLayout()
        self.announcement_title=QLineEdit(); self.announcement_title.setPlaceholderText("공지사항 제목 (최대 120자)")
        self.announcement_body=QTextEdit(); self.announcement_body.setPlaceholderText("공지사항 내용을 입력하세요."); self.announcement_body.setMinimumHeight(100)
        self.announcement_published=QCheckBox("홈페이지에 게시")
        form.addRow("제목",self.announcement_title); form.addRow("내용",self.announcement_body); form.addRow("",self.announcement_published)
        al.addLayout(form)
        ann_buttons=QHBoxLayout()
        ann_buttons.addWidget(self.button("새 공지 작성",self.new_announcement))
        ann_buttons.addWidget(self.button("선택 공지 저장",self.save_announcement,True))
        ann_buttons.addWidget(self.button("선택 공지 삭제",self.delete_announcement))
        ann_buttons.addWidget(self.button("목록 새로고침",self.load_announcements))
        al.addLayout(ann_buttons)
        self.ops_tabs.addTab(ann,"공지사항")
        activity=QWidget(); vl=QVBoxLayout(activity)
        self.activity_status=QLabel("회원가입·로그인·프로필 변경 및 관리자 작업 이력을 표시합니다."); self.activity_status.setObjectName("muted")
        vl.addWidget(self.activity_status)
        activity_tools=QHBoxLayout()
        self.activity_search=QLineEdit(); self.activity_search.setPlaceholderText("이메일 / 활동 / 회원 ID 검색")
        self.activity_search.textChanged.connect(self.filter_activity_logs)
        activity_tools.addWidget(self.activity_search,1)
        activity_tools.addWidget(self.button("CSV 내보내기",self.export_activity_logs))
        vl.addLayout(activity_tools)
        self.activity_table=QTableWidget(0,5)
        self.activity_table.setHorizontalHeaderLabels(["발생 시각","이메일","활동","회원 ID","상세 정보"])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers); self.activity_table.setAlternatingRowColors(True)
        vl.addWidget(self.activity_table,1)
        vl.addWidget(self.button("회원 활동 이력 새로고침",self.load_activity_logs,True))
        self.ops_tabs.addTab(activity,"회원 활동 로그")
        errors=QWidget(); el=QVBoxLayout(errors)
        self.error_status=QLabel("관리자 API 및 관리자 프로그램에서 기록한 오류를 표시합니다."); self.error_status.setObjectName("muted")
        el.addWidget(self.error_status)
        error_tools=QHBoxLayout()
        self.error_search=QLineEdit(); self.error_search.setPlaceholderText("발생 위치 / 오류 내용 검색")
        self.error_search.textChanged.connect(self.filter_error_logs)
        error_tools.addWidget(self.error_search,1)
        error_tools.addWidget(self.button("CSV 내보내기",self.export_error_logs))
        el.addLayout(error_tools)
        self.error_table=QTableWidget(0,4)
        self.error_table.setHorizontalHeaderLabels(["발생 시각","발생 위치","오류 내용","상세 정보"])
        self.error_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.error_table.setEditTriggers(QTableWidget.NoEditTriggers); self.error_table.setAlternatingRowColors(True)
        el.addWidget(self.error_table,1)
        el.addWidget(self.button("오류 로그 새로고침",self.load_error_logs,True))
        self.ops_tabs.addTab(errors,"오류 로그")
        outer.addWidget(self.ops_tabs,1)
        self._announcements=[]
        return w
    def require_ops_login(self,label):
        if not self.store.admin_session().get("access_token"):
            label.setText("먼저 회원 관리 페이지에서 관리자 로그인을 해주세요.")
            return False
        return True
    def load_announcements(self):
        if not self.require_ops_login(self.announcement_status): return
        self.announcement_status.setText("공지사항을 불러오는 중...")
        def done(rows,error):
            if error:
                self.announcement_status.setText("조회 실패: "+error); return
            self._announcements=rows; self.announcement_table.setRowCount(len(rows))
            for i,row in enumerate(rows):
                vals=[row.get("title",""),"게시 중" if row.get("is_published") else "비공개",str(row.get("created_at") or "-")[:19].replace("T"," ")]
                for j,value in enumerate(vals):
                    item=QTableWidgetItem(str(value))
                    if j==0: item.setData(Qt.UserRole,row.get("id"))
                    self.announcement_table.setItem(i,j,item)
            self.announcement_status.setText(f"공지사항 {len(rows)}건 조회 완료")
        self.run_async(self.admin_users.list_announcements,done)
    def select_announcement(self):
        row=self.announcement_table.currentRow()
        if row<0: return
        item=self.announcement_table.item(row,0)
        if not item: return
        announcement=next((x for x in self._announcements if x.get("id")==item.data(Qt.UserRole)),None)
        if not announcement: return
        self.announcement_title.setText(announcement.get("title",""))
        self.announcement_body.setPlainText(announcement.get("body",""))
        self.announcement_published.setChecked(bool(announcement.get("is_published")))
    def new_announcement(self):
        self.announcement_table.clearSelection()
        self.announcement_title.clear(); self.announcement_body.clear(); self.announcement_published.setChecked(False)
        self.announcement_title.setFocus()
    def save_announcement(self):
        if not self.require_ops_login(self.announcement_status): return
        title=self.announcement_title.text().strip(); body=self.announcement_body.toPlainText().strip()
        if not title or not body:
            QMessageBox.warning(self,"입력 확인","공지사항 제목과 내용을 입력해 주세요."); return
        row=self.announcement_table.currentRow()
        announcement_id=self.announcement_table.item(row,0).data(Qt.UserRole) if row>=0 and self.announcement_table.item(row,0) else None
        self.announcement_status.setText("공지사항을 저장하는 중...")
        def done(result,error):
            if error:
                self.announcement_status.setText("저장 실패: "+error); QMessageBox.warning(self,"저장 실패",error); return
            self.announcement_status.setText("공지사항 저장 완료")
            self.load_announcements()
        self.run_async(lambda:self.admin_users.save_announcement(announcement_id,title,body,self.announcement_published.isChecked()),done)
    def delete_announcement(self):
        row=self.announcement_table.currentRow()
        if row<0:
            QMessageBox.information(self,"공지 선택","삭제할 공지사항을 먼저 선택해 주세요."); return
        item=self.announcement_table.item(row,0); announcement_id=item.data(Qt.UserRole)
        if QMessageBox.question(self,"공지사항 삭제","선택한 공지사항을 삭제할까요?",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return
        def done(result,error):
            if error:
                self.announcement_status.setText("삭제 실패: "+error); QMessageBox.warning(self,"삭제 실패",error); return
            self.new_announcement(); self.load_announcements()
        self.run_async(lambda:self.admin_users.delete_announcement(announcement_id),done)
    def load_activity_logs(self):
        if not self.require_ops_login(self.activity_status): return
        self.activity_status.setText("회원 활동 이력을 불러오는 중...")
        def done(rows,error):
            if error:
                self.activity_status.setText("조회 실패: "+error); return
            self._activity_rows=rows or []
            self.filter_activity_logs()
        self.run_async(self.admin_users.list_activity_logs,done)

    def filter_activity_logs(self):
        rows=getattr(self,"_activity_rows",[])
        query=self.activity_search.text().strip().lower()
        if query:
            rows=[row for row in rows if query in " ".join([
                str(row.get("email") or ""),str(row.get("action") or ""),
                str(row.get("user_id") or ""),json.dumps(row.get("details") or {},ensure_ascii=False)
            ]).lower()]
        self.activity_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            details=json.dumps(row.get("details") or {},ensure_ascii=False)
            vals=[str(row.get("created_at") or "-")[:19].replace("T"," "),row.get("email") or "-",row.get("action") or "-",row.get("user_id") or "-",details[:500]]
            for j,value in enumerate(vals): self.activity_table.setItem(i,j,QTableWidgetItem(str(value)))
        self.activity_status.setText(f"검색 결과 {len(rows)}건 / 전체 {len(getattr(self,'_activity_rows',[]))}건 · 최근 최대 200건")

    def export_activity_logs(self):
        rows=getattr(self,"_activity_rows",[])
        query=self.activity_search.text().strip().lower()
        if query:
            rows=[row for row in rows if query in " ".join([
                str(row.get("email") or ""),str(row.get("action") or ""),
                str(row.get("user_id") or ""),json.dumps(row.get("details") or {},ensure_ascii=False)
            ]).lower()]
        self.export_log_csv(rows,"moamoa-member-activity.csv","회원 활동 내역",
            ["발생 시각","이메일","활동","회원 ID","상세 정보"],
            lambda row:[row.get("created_at") or "",row.get("email") or "",row.get("action") or "",row.get("user_id") or "",json.dumps(row.get("details") or {},ensure_ascii=False)])

    def load_error_logs(self):
        if not self.require_ops_login(self.error_status): return
        self.error_status.setText("오류 로그를 불러오는 중...")
        def done(rows,error):
            if error:
                self.error_status.setText("조회 실패: "+error); return
            self._error_rows=rows or []
            self.filter_error_logs()
        self.run_async(self.admin_users.list_error_logs,done)

    def filter_error_logs(self):
        rows=getattr(self,"_error_rows",[])
        query=self.error_search.text().strip().lower()
        if query:
            rows=[row for row in rows if query in " ".join([
                str(row.get("source") or ""),str(row.get("message") or ""),
                json.dumps(row.get("details") or {},ensure_ascii=False)
            ]).lower()]
        self.error_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            details=json.dumps(row.get("details") or {},ensure_ascii=False)
            vals=[str(row.get("created_at") or "-")[:19].replace("T"," "),row.get("source") or "-",row.get("message") or "-",details[:500]]
            for j,value in enumerate(vals): self.error_table.setItem(i,j,QTableWidgetItem(str(value)))
        self.error_status.setText(f"검색 결과 {len(rows)}건 / 전체 {len(getattr(self,'_error_rows',[]))}건 · 최근 최대 200건")

    def export_error_logs(self):
        rows=getattr(self,"_error_rows",[])
        query=self.error_search.text().strip().lower()
        if query:
            rows=[row for row in rows if query in " ".join([
                str(row.get("source") or ""),str(row.get("message") or ""),
                json.dumps(row.get("details") or {},ensure_ascii=False)
            ]).lower()]
        self.export_log_csv(rows,"moamoa-error-logs.csv","오류 로그",
            ["발생 시각","발생 위치","오류 내용","상세 정보"],
            lambda row:[row.get("created_at") or "",row.get("source") or "",row.get("message") or "",json.dumps(row.get("details") or {},ensure_ascii=False)])

    def export_log_csv(self,rows,default_name,title,headers,row_values):
        if not rows:
            QMessageBox.information(self,"내보낼 기록 없음","먼저 로그를 새로고침하거나 검색 조건을 확인해 주세요.")
            return
        path,_=QFileDialog.getSaveFileName(self,title+" CSV 저장",default_name,"CSV 파일 (*.csv)")
        if not path: return
        if not path.lower().endswith(".csv"): path += ".csv"
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                writer=csv.writer(f); writer.writerow(headers)
                for row in rows: writer.writerow(row_values(row))
            QMessageBox.information(self,"내보내기 완료",f"{title} {len(rows)}건을 저장했습니다.\\n{path}")
        except Exception as exc:
            QMessageBox.warning(self,"내보내기 실패",str(exc))
    def admin_accounts_page(self):
        w=QWidget(); l=QVBoxLayout(w)
        l.addWidget(self.title_block("관리자 계정 관리","최고 관리자 전용 · 관리자 등록과 일반 관리자 접근 활성화/비활성화를 관리합니다."))
        note=QLabel("등록할 이메일은 먼저 MOAMOA 홈페이지에 회원가입되어 있어야 합니다. 최고 관리자 권한은 Supabase 보안 설정에서만 지정할 수 있습니다.")
        note.setObjectName("muted"); note.setWordWrap(True); l.addWidget(note)
        addrow=QHBoxLayout()
        self.new_admin_email=QLineEdit(); self.new_admin_email.setPlaceholderText("추가할 관리자 이메일")
        addrow.addWidget(self.new_admin_email,1)
        addrow.addWidget(self.button("일반 관리자 등록",self.add_admin_account,True))
        addrow.addWidget(self.button("목록 새로고침",self.load_admin_accounts))
        l.addLayout(addrow)
        self.admin_accounts_table=QTableWidget(0,4)
        self.admin_accounts_table.setHorizontalHeaderLabels(["이메일","권한","상태","등록일"])
        self.admin_accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.admin_accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.admin_accounts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.admin_accounts_table.setAlternatingRowColors(True)
        l.addWidget(self.admin_accounts_table,1)
        actions=QHBoxLayout()
        actions.addWidget(self.button("선택 관리자 비활성화",lambda:self.change_admin_active(False)))
        actions.addWidget(self.button("선택 관리자 다시 활성화",lambda:self.change_admin_active(True)))
        actions.addStretch(); l.addLayout(actions)
        self.admin_accounts_status=QLabel("최고 관리자 로그인 후 목록을 불러올 수 있습니다.")
        self.admin_accounts_status.setObjectName("muted"); l.addWidget(self.admin_accounts_status)
        l.addWidget(QLabel("관리자 활동 내역"))
        self.admin_activity_status=QLabel("관리자 로그인 및 관리자 작업 이력을 확인합니다. 최근 500건까지 표시됩니다.")
        self.admin_activity_status.setObjectName("muted"); l.addWidget(self.admin_activity_status)
        activity_tools=QHBoxLayout()
        self.admin_activity_search=QLineEdit()
        self.admin_activity_search.setPlaceholderText("관리자 이메일 또는 활동 내용 검색")
        self.admin_activity_search.textChanged.connect(self.filter_admin_activity_logs)
        activity_tools.addWidget(self.admin_activity_search,1)
        activity_tools.addWidget(self.button("CSV 내보내기",self.export_admin_activity_logs))
        l.addLayout(activity_tools)
        self.admin_activity_table=QTableWidget(0,5)
        self.admin_activity_table.setHorizontalHeaderLabels(["발생 시각","관리자 이메일","권한","활동","상세 정보"])
        self.admin_activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.admin_activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.admin_activity_table.setAlternatingRowColors(True)
        self.admin_activity_table.setMaximumHeight(220)
        l.addWidget(self.admin_activity_table)
        l.addWidget(self.button("관리자 활동 내역 새로고침",self.load_admin_activity_logs,True))
        return w

    def load_admin_activity_logs(self):
        if not self.store.admin_session().get("access_token"):
            self.admin_activity_status.setText("먼저 최고 관리자 계정으로 로그인해 주세요."); return
        self.admin_activity_status.setText("관리자 활동 내역을 불러오는 중...")
        def done(rows,error):
            if error:
                self.admin_activity_status.setText("조회 실패: "+error); return
            self._admin_activity_rows=rows or []
            self.filter_admin_activity_logs()
        self.run_async(self.admin_users.list_admin_activity_logs,done)

    def filtered_admin_activity_rows(self):
        rows=getattr(self,"_admin_activity_rows",[])
        query=self.admin_activity_search.text().strip().lower() if hasattr(self,"admin_activity_search") else ""
        if not query: return rows
        matched=[]
        for row in rows:
            details=row.get("details") or {}
            searchable=" ".join([
                str(row.get("email") or details.get("actor_email") or ""),
                str(row.get("action") or ""),
                str(details.get("admin_role") or ""),
                json.dumps(details,ensure_ascii=False)
            ]).lower()
            if query in searchable: matched.append(row)
        return matched

    def filter_admin_activity_logs(self):
        rows=self.filtered_admin_activity_rows()
        self.admin_activity_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            details=row.get("details") or {}
            detail_text=json.dumps(details,ensure_ascii=False)
            vals=[str(row.get("created_at") or "-")[:19].replace("T"," "),
                  row.get("email") or details.get("actor_email") or "-",
                  details.get("admin_role") or "-",
                  row.get("action") or "-",
                  detail_text[:500]]
            for j,value in enumerate(vals):
                self.admin_activity_table.setItem(i,j,QTableWidgetItem(str(value)))
        total=len(getattr(self,"_admin_activity_rows",[]))
        self.admin_activity_status.setText(f"검색 결과 {len(rows)}건 / 전체 {total}건 · 최근 최대 500건")

    def export_admin_activity_logs(self):
        rows=self.filtered_admin_activity_rows()
        if not rows:
            QMessageBox.information(self,"내보낼 기록 없음","먼저 관리자 활동 내역을 새로고침하거나 검색 조건을 확인해 주세요.")
            return
        path,_=QFileDialog.getSaveFileName(self,"관리자 활동 내역 CSV 저장","moamoa-admin-activity.csv","CSV 파일 (*.csv)")
        if not path: return
        if not path.lower().endswith(".csv"): path += ".csv"
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                writer=csv.writer(f)
                writer.writerow(["발생 시각","관리자 이메일","권한","활동","상세 정보"])
                for row in rows:
                    details=row.get("details") or {}
                    writer.writerow([
                        row.get("created_at") or "",
                        row.get("email") or details.get("actor_email") or "",
                        details.get("admin_role") or "",
                        row.get("action") or "",
                        json.dumps(details,ensure_ascii=False)
                    ])
            self.admin_activity_status.setText(f"CSV 저장 완료 · {len(rows)}건")
            QMessageBox.information(self,"내보내기 완료",f"관리자 활동 내역 {len(rows)}건을 저장했습니다.\n{path}")
        except Exception as exc:
            QMessageBox.warning(self,"내보내기 실패",str(exc))

    def load_admin_accounts(self):
        if not self.store.admin_session().get("access_token"):
            self.admin_accounts_status.setText("먼저 최고 관리자 계정으로 로그인해 주세요."); return
        self.admin_accounts_status.setText("관리자 목록을 불러오는 중...")
        def done(rows,error):
            if error:
                self.admin_accounts_status.setText("조회 실패: "+error); return
            self.admin_accounts_table.setRowCount(len(rows))
            self._admin_account_rows={}
            for i,row in enumerate(rows):
                email=row.get("email","")
                self._admin_account_rows[i]=row
                vals=[email,"최고 관리자" if row.get("role")=="super_admin" else "일반 관리자",
                      "활성" if row.get("is_active") else "비활성",
                      (row.get("created_at") or "-")[:10]]
                for j,value in enumerate(vals):
                    item=QTableWidgetItem(str(value)); self.admin_accounts_table.setItem(i,j,item)
            self.admin_accounts_status.setText(f"관리자 {len(rows)}개 계정 · 최고 관리자 계정은 여기서 비활성화할 수 없습니다.")
        self.run_async(self.admin_users.list_admin_accounts,done)

    def add_admin_account(self):
        email=self.new_admin_email.text().strip().lower()
        if not email:
            QMessageBox.warning(self,"입력 확인","등록할 이메일을 입력해 주세요."); return
        if QMessageBox.question(self,"관리자 등록",f"{email} 계정을 일반 관리자로 등록할까요?")!=QMessageBox.Yes:
            return
        def done(result,error):
            if error:
                QMessageBox.warning(self,"등록 실패",error); return
            self.new_admin_email.clear(); self.admin_accounts_status.setText("일반 관리자 등록 완료")
            self.load_admin_accounts()
        self.run_async(lambda:self.admin_users.add_admin_account(email),done)

    def change_admin_active(self,active):
        row=self.admin_accounts_table.currentRow()
        if row<0 or row not in getattr(self,"_admin_account_rows",{}):
            QMessageBox.information(self,"계정 선택","상태를 변경할 관리자 계정을 선택해 주세요."); return
        account=self._admin_account_rows[row]
        if account.get("role")=="super_admin":
            QMessageBox.warning(self,"변경 불가","최고 관리자 계정은 여기서 변경할 수 없습니다."); return
        email=account.get("email","")
        action="활성화" if active else "비활성화"
        if QMessageBox.question(self,"관리자 계정 변경",f"{email} 계정을 {action}할까요?")!=QMessageBox.Yes:
            return
        def done(result,error):
            if error:
                QMessageBox.warning(self,"변경 실패",error); return
            self.admin_accounts_status.setText(f"{email} 계정 {action} 완료")
            self.load_admin_accounts()
        self.run_async(lambda:self.admin_users.set_admin_active(email,active),done)

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
    #pageTitle{font-size:22px;font-weight:800;color:#493443}
    #sectionTitle{font-size:18px;font-weight:800}
    #muted{color:#9B8792;font-size:12px}
    #card{background:white;border:1px solid #F3DDE6;border-radius:16px}
    #cardValue{font-size:17px;font-weight:800;color:#D85F8B}
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
