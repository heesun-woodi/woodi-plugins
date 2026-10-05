# 참고 법령·기관

| 번호 | 구분 | 이름 | URL |
|---|---|---|---|
| 1 | 법령 | 건설기계관리법 | 상세(사람용): https://www.law.go.kr/법령/건설기계관리법 · API: `https://www.law.go.kr/DRF/lawService.do?OC=test&target=law&LM=건설기계관리법&type=XML` |
| 2 | 법령 | 건설기계관리법 시행규칙 | 상세(사람용): https://www.law.go.kr/법령/건설기계관리법시행규칙 · API: `https://www.law.go.kr/DRF/lawService.do?OC=test&target=law&LM=건설기계관리법시행규칙&type=XML` |
| 3 | 기관 | 국토교통부 | https://www.molit.go.kr |
| 4 | 기관 | 한국산업인력공단 | https://www.hrdkorea.or.kr |
| 5 | 기관 | 고용노동부 | https://www.moel.go.kr |
| 6 | 기관 | 고용24 | https://www.work24.go.kr |
| 7 | 기관 | 국민신문고 | https://www.epeople.go.kr |
| 8 | 기관 | 큐넷 | https://www.q-net.or.kr (지게차운전기능사 종목코드 `jmCd=7875`, 아래 접근성 기록 참고) |

## 주장 유형 → 확인 출처

| 주장 유형 | 확인 출처 |
|---|---|
| 시험 일정·접수·수수료 | 큐넷(q-net.or.kr) |
| 응시 자격·면허 종류·톤수 기준·갱신 | 건설기계관리법·시행규칙(law.go.kr DRF API: `https://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=<법령명>` → `https://www.law.go.kr/DRF/lawService.do?OC=test&target=law&MST=<법령일련번호>&type=XML`) + 국토교통부 |
| 국비·내일배움카드 | 고용24(work24.go.kr)·한국산업인력공단(hrdkorea.or.kr)·고용노동부 |
| 민원·불만 사례 | 국민신문고 |

## 접근성 기록

확인 일자: 2026-10-06 (Task 4). 방법: `curl -sL -A "Mozilla/5.0" --max-time 20`. 상태 정의 - 본문 가능: curl 응답에 필요한 텍스트·표가 들어 있음 / 껍데기만: 200이지만 JS가 채우는 빈 틀 / 차단: 4xx·루프.

### 법령 API 호출 방법 (law.go.kr DRF, `OC=test`)

| 용도 | URL 템플릿 | 비고 |
|---|---|---|
| 법령 검색 | `https://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=<법령명>` | `<법령일련번호>`(MST), `<시행일자>`, `<현행연혁코드>` 반환 |
| 법령 본문 (이름으로) | `https://www.law.go.kr/DRF/lawService.do?OC=test&target=law&LM=<법령명>&type=XML` | MST 없이 현행 본문. 조문은 `<조문단위>`/`<조문내용>` |
| 법령 본문 (MST로) | `https://www.law.go.kr/DRF/lawService.do?OC=test&target=law&MST=<법령일련번호>&type=XML` | 특정 시점 판본 고정 시 |

실측: 검색 `query=건설기계관리법` → `totalCnt` 3건: 건설기계관리법 MST 283763(시행 2026-08-28), 건설기계관리법 시행령 MST 284659, 건설기계관리법 시행규칙 MST 285023(시행 2026-03-24). 본문 응답 크기: 법 263,697바이트·`<조문단위>` 94개, 시행규칙 1,580,610바이트·`<조문단위>` 153개. 시행령도 같은 방식이다. 응답은 `text/xml;charset=UTF-8`이고 `OC=test`가 그대로 통했다. 주의: MST와 시행일은 개정되면 바뀐다. 글에 법령을 인용할 때는 검색 응답의 `시행일자`를 같이 적는다.

### 출처별 접근성

| 출처 | URL | 상태 | 비고 (쓸 수 있는 주장 유형 / 안 될 때 대안) |
|---|---|---|---|
| law.go.kr DRF API | `https://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=건설기계관리법` , `…/lawService.do?OC=test&target=law&LM=건설기계관리법&type=XML` | 본문 가능 | 응시 자격·면허 종류·톤수 기준·갱신 등 조문 인용 전부. 시행규칙도 가능 |
| law.go.kr 상세 페이지 | `https://www.law.go.kr/법령/건설기계관리법` | 껍데기만 (200, 1,279바이트, JS 렌더링) | 독자에게 보여줄 링크로만 쓰고, 사실 확인은 위 API로 한다 |
| 큐넷 종목 상세 - 껍데기 페이지 | `https://www.q-net.or.kr/crf005.do?id=crf00503&gSite=Q&gId=&jmCd=7875` | 껍데기만 (200, 약 227KB지만 본문 텍스트는 메뉴뿐, 종목명도 JS가 채움) | 이 URL 자체로는 사실 확인 불가. 아래 탭 조각 URL을 쓴다 |
| 큐넷 종목 탭: 검정현황 | `https://www.q-net.or.kr/crf005.do?id=crf00503s01&gSite=Q&gId=&jmCd=7875` | 본문 가능 (7,816바이트) | 연도별 필기·실기 응시·합격·합격률(예: 2025 필기 응시 110,316 합격 73.6%, 실기 응시 126,757 합격 47.9%). 합격률 주장에 사용 |
| 큐넷 종목 탭: 시험일정·수수료 | `https://www.q-net.or.kr/crf005.do?id=crf00503s02&gSite=Q&gId=&jmCd=7875` | 본문 가능 (5,389바이트). 단 지게차는 정기 일정 표가 비어 `시험 일정이 없습니다` | 수수료(필기 14,500원, 실기 25,200원)와 출제기준 적용기간(2025.1.1~2027.12.31)은 확인됨. 정기 일정이 비어 있는 것은 상시 시행 여부와 연결될 수 있으나 이 응답만으로는 단정할 수 없으므로 "접수·일정은 큐넷 공지 확인" 문구 또는 이랑 확인으로 처리 |
| 큐넷 월간 시험일정 | `https://www.q-net.or.kr/crf021.do?id=crf02103&gSite=Q&gId=&scheType=01` | 본문 가능 (월 달력 표 텍스트까지 옴, 245KB) | 해당 월의 기능사 필기·실기 접수·발표 일정 (예: 2026-10 `기능사 제4회 실기시험 원서접수 10.12~10.15`). 연간 일정은 `crf021.do?id=crf02101&scheType=01` 계열이나 응답은 껍데기에 가까움 |
| 큐넷 메인 | `https://www.q-net.or.kr/` | 껍데기만 (359바이트, `/index.jsp`로 meta refresh) | 직접 쓰지 않음 |
| 고용24 메인 | `https://www.work24.go.kr/` | 본문 가능 (200, 약 369KB, 메뉴·검색 문구) | 국민내일배움카드 제도 설명 문구는 메인에 없음. 메뉴에 `국민내일배움카드 훈련과정`(`/hr/a/a/1100/trnnCrsInfPost.do`)이 있음 |
| 고용24 훈련 통합검색 | `https://www.work24.go.kr/hr/a/a/1100/trnnCrsInf.do` | 본문 가능 (200, 약 605KB, 검색 UI) | 개별 훈련과정 목록·지원 조건은 이 curl 응답에 없다(검색 후 AJAX 결과로 추정, 미확인). 내일배움카드 지원 대상·금액 주장은 "고용24 확인 필요"로 강등하거나 이랑이 확인 |
| 한국산업인력공단 | `https://www.hrdkorea.or.kr/` | 본문 가능 (200, euc-kr 인코딩, 메뉴 텍스트) | 읽을 때 `euc-kr`로 디코딩해야 함. 사업 소개 수준의 기관 확인용 |
| 국토교통부 | `https://www.molit.go.kr/` | 쿠키 필요 (루트가 307 리다이렉트 루프, 쿠키 저장 후 `/portal.do`는 200·126KB 본문) | `curl -c cj -b cj`로 쿠키 유지 필요. 공지·보도자료 인용은 가능하나 이랑 확인 권장 |
| 고용노동부 | `https://www.moel.go.kr/` | 본문 가능 (루트는 JS로 `/index.do`로 이동, `https://www.moel.go.kr/index.do`는 200·약 284KB) | 루트 대신 `/index.do`로 직접 요청 |
| 국민신문고 | `https://www.epeople.go.kr/` | 본문 가능 (루트는 meta refresh, `https://www.epeople.go.kr/index.jsp`는 200·약 161KB) | 루트 대신 `/index.jsp`로 직접 요청. 민원 사례 본문은 확인하지 않음 |

### 주장 유형별 결론

- 법령 조문·톤수 기준·면허 종류: law.go.kr DRF API로 자동 확인 가능(가장 신뢰).
- 시험 수수료·합격률·출제기준 기간: 큐넷 종목 탭 조각 URL(`crf00503s01`, `crf00503s02`)로 확인 가능. 종목코드는 지게차운전기능사 `7875` (주의: 요청서의 `7910`은 한식조리기능사, `7785`는 3D프린터운용기능사였다).
- 시험 접수·일정: 월간 일정 페이지로 월 단위 확인은 가능하나 지게차 종목 탭에는 정기 일정이 비어 있다. 일정 단정 금지, "큐넷에서 최신 일정 확인" 문구 + 시점 명시, 필요하면 이랑 확인.
- 국비·내일배움카드: 고용24·HRD-Net은 제도 상세가 curl로 안 보이므로 "시점확인+이랑 확인"으로 강등.
- 웹 팬/WebFetch에서 막히는 곳이 있어도 위 URL은 curl 기준 결과다. fact-checker가 WebFetch를 쓸 때 실패하면 curl(Bash)로 재시도한다.
