# MOAMOA | 모아모아

귀여운 3D 피규어 감성의 캐릭터 수집형 가챠 플랫폼 초기 MVP입니다.

## 현재 구현된 기능
- 반응형 메인 페이지
- 무료 체험 뽑기 1회
- 6종 캐릭터 도감
- 획득 캐릭터 및 뽑기 기록 저장 (`localStorage`)
- 마이페이지 수집 현황
- 굿즈 샵/시즌 이벤트 UI (현재 준비 중 표시)

## 실행 방법
1. ZIP 압축을 해제합니다.
2. `index.html`을 브라우저에서 열면 됩니다.
3. GitHub Pages로 배포하려면 저장소 루트에 `index.html`, `styles.css`, `app.js`, `assets/`를 업로드합니다.
4. GitHub 저장소의 **Settings → Pages → Deploy from a branch → main / root**를 선택합니다.

## 중요: 현재 버전의 한계
이 버전은 디자인·기능 검증용 프론트엔드 데모입니다.
- 뽑기 결과와 보유 데이터는 현재 브라우저의 `localStorage`에만 저장됩니다.
- 브라우저/기기 변경, 사이트 데이터 삭제 시 기록이 사라질 수 있습니다.
- 이용자 간 데이터 공유, 회원가입, 관리자 기능, 결제, 서버 검증은 아직 연결되지 않았습니다.
- 실제 유료 랜덤 뽑기를 시작하기 전에는 관련 법률·확률 공개·청약철회 및 환불 정책 검토가 필요합니다.

## 다음 개발 단계 권장
1. Supabase Auth로 회원가입/로그인 구현
2. Supabase DB에 회원별 캐릭터 보유·뽑기 기록 저장
3. Cloudflare Workers에서 서버측 뽑기 결과 생성 및 중복 지급 방지
4. 관리자 캐릭터 등록/확률 관리 화면
5. 국내 PG 결제와 주문 관리
6. POD 제작·배송 업체 연동

## 파일 구조
```text
moamoa/
├── index.html
├── styles.css
├── app.js
├── README.md
└── assets/
    └── moamoa-design-reference.png
```
