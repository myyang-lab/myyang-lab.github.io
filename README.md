# Moon Young Yang Research Group 홈페이지 관리

DGIST Multiscale Computational Science Lab의 정적 GitHub Pages 사이트입니다. 기존 URL, 사진, 콘텐츠와 디자인을 유지합니다. **수정 원본은 `src/`와 `data/`이며, 루트 HTML·`papers.bib`·해시가 붙은 CSS/JS는 생성 결과입니다.**

## 실행과 수정

Python 3.12 이상이 필요하며, 빌드용 외부 패키지는 없습니다. 저장소 루트에서 실행합니다.

```sh
python3 scripts/build.py
python3 -m http.server 8000 --bind 127.0.0.1
```

서버 실행 후 브라우저에서 사이트를 확인합니다. 원본을 수정할 때마다 빌드를 다시 실행합니다. 루트 HTML을 직접 수정하면 다음 빌드에서 덮어써집니다.

```text
src/
  pages/          페이지별 HTML 템플릿
  partials/       공통 header.html, footer.html
  styles/         site.css와 범위가 제한된 페이지 전용 CSS
  site.js         모바일 메뉴 동작
data/
  gallery.json       사진 목록
  publications.json  논문 원본 → Publications HTML과 papers.bib 동시 생성
  research-papers.json  Research에 소개할 논문 번호와 짧은 소개 제목
  news.json          뉴스 원본 → News 전체 목록과 Home 최신 항목 동시 생성
  site.json          이메일·전화·연구실 위치·저작권 연도
scripts/build.py     결정적 정적 빌드
tests/              데이터·링크·캐시 무효화·브라우저 검증
```

## Gallery 사진 추가

1. `assets/images/gallery/`에 사진을 추가합니다. 새 파일명은 `YYYY-MM-DD_description.webp`처럼 공백 없이 작성합니다. 기존 사진 경로는 외부 링크 보존을 위해 그대로 유지합니다.
2. `data/gallery.json` 배열에 다음 형태의 항목을 추가합니다. `width`, `height`에는 실제 이미지의 픽셀 크기를 입력합니다.

```json
{
  "date": "2026-11-05",
  "image": "assets/images/gallery/2026-11-05_group.webp",
  "alt": "연구실 구성원들의 단체 사진",
  "caption": "First group photo at DGIST.",
  "width": 1600,
  "height": 1200
}
```

3. 빌드하면 날짜 역순으로 기존 카드 디자인에 표시됩니다. 큰 원본을 따로 제공하려면 선택 항목 `"original": "assets/images/gallery/원본파일.webp"`를 추가합니다. `image`는 카드용 이미지, `original`은 클릭 시 여는 이미지입니다. 원본이 없으면 `image`를 엽니다. HTML 조각을 복사할 필요가 없습니다.

이미지는 WebP 등으로 적절히 압축하고, `alt`에는 사진의 의미를 설명합니다. 빌드는 누락 파일·잘못된 날짜·빈 설명·크기 누락을 검사합니다. 리사이즈나 압축 자체는 수행하지 않습니다.

## Publications 논문 추가

`data/publications.json`이 단일 원본입니다. **HTML과 BibTeX를 따로 수정하지 않습니다.** 새 항목에 아직 사용하지 않은 `number`와 고유한 BibTeX `key`를 지정합니다. 기존 번호는 유지합니다.

```json
{
  "number": 64,
  "key": "yangNewAcceptedPaper",
  "title": "Paper title",
  "authors": [
    {"name": "Moon Young Yang", "equal": true},
    {"name": "Coauthor Name", "equal": true, "corresponding": true}
  ],
  "journal": "Journal name",
  "year": null,
  "status": "Accepted"
}
```

- Accepted 논문은 연도와 DOI 없이도 추가할 수 있으며, Accepted 섹션에 표시됩니다.
- 출판되면 `status`를 제거하고 `year`, `volume`, `issue`(선택), `pages`, `doi`(있는 경우)를 입력합니다. DOI는 `https://doi.org/`를 제외한 값입니다.
- `pages`는 범위나 논문 번호를 문자열로 입력합니다. 예: `"2073–2093"`, `"e2617489123"`.
- `equal: true`는 †, `corresponding: true`는 *를 표시합니다. Moon Young Yang 이름은 자동으로 굵게 표시합니다.
- 선택 항목 `note`는 표지 논문 등 부가 설명입니다.
- 제목·저자명에는 HTML 태그 대신 일반 텍스트와 Unicode 화학식·문자를 사용합니다. 출력 시 안전하게 이스케이프합니다.
- `research-papers.json`은 Research의 기존 짧은 소개 제목을 보존하는 편집 목록입니다. `number`로 논문을 연결하며 연도는 논문 원본에서 가져옵니다. 목록 항목에 해당하는 `{{ research_paper_번호 }}`를 Research 템플릿에 배치합니다. 링크는 Publications의 안정적인 `#paper-번호`로 연결됩니다.

현재 데이터는 기존 HTML을 기준으로 옮겼습니다. 60번은 **2073–2093**, 62번은 **Mingyang Liu 포함**, 63번은 **Accepted·연도 미지정**입니다. DOI와 기존 BibTeX 키는 유지했습니다. 논문 사실관계는 외부 자료로 임의 수정하지 않았습니다.

## 뉴스·공통 정보·디자인 수정

- `data/news.json`: 날짜(`YYYY-MM-DD`), 분류(`category`), 제목(`title`), 본문(`text`)을 추가합니다. 전체 뉴스는 날짜 역순이며 Home에는 최신 1건을 표시합니다. 월 단위 날짜 표시를 유지하므로 일자가 알려지지 않은 소식은 정렬용 날짜를 정합니다.
- `data/site.json`: 공통 이메일·전화·사무실·연구실 위치를 수정합니다. `phone_uri`는 전화 링크용 국제번호, `phone`은 화면 표시용입니다.
- Header/Footer: `src/partials/`에서 한 번 수정하면 주요 페이지 8개에 반영됩니다. PI 상세 페이지에서는 People 메뉴가 활성화됩니다.
- 공통 CSS: `src/styles/site.css`. People·Publications·PI의 기존 제목·카드 디자인은 각 페이지 이름의 CSS에 보존했습니다. 페이지 전용 선택자는 `:where(body.page-페이지명)` 범위 안에서 작성합니다. 공통 Header/Footer를 페이지별 CSS에서 재정의하지 않습니다.
- CSS 결합 순서는 페이지 CSS → 공통 CSS이며, 기존 적용 순서를 유지합니다. 반응형 메뉴 기준은 **730px 이하**로 통일했습니다.

## CSS 캐시와 배포

빌드마다 CSS/JS **내용의 SHA-256 해시**로 `assets/site.<hash>.css`, `assets/site.<hash>.js`를 생성하고 모든 HTML의 참조를 함께 갱신합니다. 내용이 같으면 파일명도 같습니다. 이미지 내용만 교체하는 경우는 이 해시의 대상이 아니므로 새 이미지 파일명을 사용하고 데이터 경로를 바꿉니다.

루트 HTML과 해시 자산을 **같은 커밋**에 포함합니다. 오래 열린 탭이나 오래 캐시된 HTML은 갱신 전까지 이전 화면을 유지할 수 있습니다. 해시는 새 HTML이 새 CSS를 요청하도록 보장하며, HTML 자체의 CDN 캐시·배포 지연을 없애지는 않습니다.

현재 Pages의 배포 소스 설정은 변경하지 않았습니다.

- 기존 방식이 브랜치 루트 배포라면: 원본과 빌드 결과를 함께 커밋하면 기존 배포 경로를 유지합니다. `.nojekyll`로 별도 Jekyll 처리를 막습니다.
- 별도 배포 산출물이 필요하면: `python3 scripts/build.py --output _site`를 사용합니다. `_site/`에는 페이지, 이미지, 생성 CSS/JS와 BibTeX만 들어갑니다.
- GitHub Actions의 `Validate static site`는 생성 결과·테스트를 확인하고 `_site` 아티팩트를 보관합니다. **사이트를 자동 게시하거나 Pages 설정을 바꾸지는 않습니다.** 데이터만 수정하고 빌드를 빠뜨리면 검사에서 알려줍니다.

이전 `README_*.txt`는 당시 배포 기록입니다. 현재 수정 방법은 이 README를 따릅니다. 이전 `site.css`, `site-v5.css`, `site-v6.css`는 더 이상 사용하지 않습니다.

## 검증

기본 검사에는 외부 패키지가 필요 없습니다.

```sh
python3 scripts/build.py --check
python3 -m unittest discover -s tests -v
node --check src/site.js
```

브라우저 검증은 선택 개발 도구인 Playwright 1.62.0과 Chromium이 필요합니다. 시스템 `chromium`이 있으면 재사용하며, 없으면 Playwright 브라우저를 사용합니다. 설치가 필요한 경우:

```sh
python3 -m pip install playwright==1.62.0
python3 -m playwright install chromium
python3 tests/browser_smoke.py
```

검증은 자체 임시 로컬 서버를 실행합니다. 8개 페이지의 11개 화면 폭(320~1440px), 메뉴 클릭·키보드·화면 크기 전환, 가로 넘침, 이미지 로딩, 논문 표시, 기존 Join 주소 이동을 확인합니다. 실행 환경이 로컬 소켓을 제한하면 해당 환경의 지원되는 권한 실행 방법을 사용합니다.
