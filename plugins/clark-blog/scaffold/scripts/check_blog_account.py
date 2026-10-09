"""check_blog_account.py — 세션의 로그인 계정이 대상 블로그에 글을 쓸 수 있는지 확인 (글은 쓰지 않는다).

사용 (naver-blog-cli 가 깔린 uv tool 의 python 으로, 작업 폴더에서):
    "$(uv tool dir)/naver-blog-cli/bin/python" scripts/check_blog_account.py <blogId>

naver-blog-cli check-session 은 글쓰기 화면에서 iframe(#mainFrame)이 붙는지만 본다.
다른 계정으로 로그인돼 있으면 https://blog.naver.com/<blogId>?Redirect=Write 가
로그인 계정의 블로그 홈(https://blog.naver.com/<그 계정>)으로 리다이렉트되는데,
블로그 홈에도 #mainFrame 이 있어서 "글쓰기 가능"으로 통과한다 (2026-10-09 실측).
여기서는 글쓰기 화면을 연 뒤 URL 의 블로그 주인이 <blogId> 인지 보고, 통과는 에디터 제목 영역이
실제로 보일 때만 준다(리다이렉트가 늦게 일어나는 경우 "아직 안 바뀐 URL" 로 통과하지 않게).
팝업 닫기 클릭(goto_editor 의 dismiss_popups)도 하지 않는다 — 화면을 열고 보기만 한다.

종료 코드 (stdout 첫 줄이 사람용 문구):
    0  글쓰기 화면이 <blogId> 로 열림
    20 세션 파일 없음/만료 (로그인 페이지로 이동)
    21 로그인한 계정이 <blogId> 블로그에 글을 쓸 수 없음 (다른 사람 블로그로 이동)
    22 그 밖의 확인 실패 (블로그가 아닌 곳으로 이동·에디터 미표시·브라우저 실행·네트워크 등)
    2  사용 오류
"""
import asyncio
import os
import sys
from urllib.parse import parse_qs, urlsplit

LOGIN_HOST = "nid.naver.com"


def blog_owner(url):
    """blog.naver.com URL 에서 블로그 아이디를 뽑는다. 못 뽑으면 None.

    https://blog.naver.com/pajuclark?Redirect=Write  -> pajuclark
    https://blog.naver.com/PostList.naver?blogId=x  -> x
    """
    parts = urlsplit(url or "")
    if not parts.netloc.endswith("blog.naver.com"):
        return None
    q = parse_qs(parts.query)
    for key in ("blogId", "blogid"):
        if q.get(key):
            return q[key][0]
    seg = parts.path.strip("/").split("/")[0]
    if seg and "." not in seg:   # PostList.naver, MyBlog.naver 같은 페이지 이름은 아이디가 아니다
        return seg
    return None


def judge(blog_id, page_url, frame_url=""):
    """(코드, 사유) — 0 일치 | 20 로그인 페이지 | 21 다른 블로그 | 22 블로그 주인을 알 수 없는 곳."""
    if LOGIN_HOST in (page_url or "") or LOGIN_HOST in (frame_url or ""):
        return 20, f"로그인 페이지로 이동 ({page_url})"
    owner = blog_owner(page_url)
    if owner is None:   # 오류·점검·보안 확인 페이지 등 — 계정 문제라고 단정하지 않는다
        return 22, f"글쓰기 화면이 아닌 곳으로 이동 ({page_url})"
    if owner.lower() != blog_id.lower():
        return 21, f"글쓰기 화면이 {page_url} 로 이동 (로그인 계정의 블로그: {owner})"
    frame_owner = blog_owner(frame_url)   # 에디터 iframe 의 blogId= 가 있으면 그것도 맞아야 한다
    if frame_owner and frame_owner.lower() != blog_id.lower():
        return 21, f"에디터가 {frame_owner} 블로그로 열림 ({frame_url})"
    return 0, f"글쓰기 화면 {page_url}"


async def check(blog_id):
    from naver_blog_cli import selectors as S
    from naver_blog_cli.editor import get_editor_frame, wait_for_editor
    from naver_blog_cli.session import STATE, Session

    os.environ.pop("NAVER_KEEP_OPEN", None)   # 헤드리스 창을 붙잡고 최대 10분 기다리지 않게
    if not STATE.exists():
        return 20, f"세션 파일 없음: {STATE}"
    try:
        async with Session(headless=True) as ctx:
            page = await ctx.new_page()
            await page.goto(S.WRITE_URL.format(blog_id=blog_id), wait_until="domcontentloaded")
            frame_url, wait_err, title = "", None, None
            if LOGIN_HOST not in page.url:
                try:
                    await wait_for_editor(page)
                    frame = await get_editor_frame(page)
                    title = await S.first(frame, S.TITLE, timeout=10000)   # 보기만 한다 (클릭 없음)
                    frame_url = frame.url or ""
                except Exception as e:  # noqa: BLE001 - 아래에서 URL 로 다시 판정한다
                    wait_err = e
            code, why = judge(blog_id, page.url, frame_url)   # 제목 영역을 기다린 뒤의 URL 로 판정
            if code == 0 and wait_err is not None:
                return 22, f"에디터가 뜨지 않음 — {type(wait_err).__name__}: {wait_err}"
            if code == 0 and title is None:
                return 22, f"에디터 제목 영역이 보이지 않음 ({page.url})"
            return code, why
    except Exception as e:  # noqa: BLE001
        return 22, f"{type(e).__name__}: {e}"


def main(argv):
    if len(argv) != 2 or not argv[1].strip():
        print("사용: check_blog_account.py <blogId>")
        return 2
    blog_id = argv[1].strip()
    code, why = asyncio.run(check(blog_id))
    head = {
        0: f"계정 확인: {blog_id} 블로그 글쓰기 가능",
        20: "세션 없음/만료",
        21: f"로그인한 계정이 {blog_id} 블로그에 글을 쓸 수 없음",
        22: "계정 확인 실패",
    }[code]
    print(f"{head} — {why}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
