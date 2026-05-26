from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SyllabusRequest(BaseModel):
    query: str

@app.post("/scrape-syllabus")
def scrape_syllabus(request: SyllabusRequest):
    root_url = "https://syllabus.ritsumei.ac.jp/syllabus/s/?language=ja"

    try:
        with sync_playwright() as p:
            # 🚀 変更点1：slow_mo（わざと遅くする設定）を削除し、フルスピードで動かす
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 🚀 変更点2：超高速化の要！画像、CSS、フォントなどの無駄な通信をすべて遮断する
            page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())

            page.set_default_timeout(30000) # タイムアウトも短めに設定

            print(f"\n[STEP 1] 爆速モードでアクセス中...")
            # 🚀 変更点3：ネットワークが完全に静かになるまで待たず、HTMLが出た瞬間に次へ進む
            page.goto(root_url, wait_until="domcontentloaded")
            
            # 1. 検索窓に入力
            search_box = page.wait_for_selector('input.slds-input', state="visible")
            search_box.fill(request.query)
            page.keyboard.press("Enter")

            # 2. 検索実行
            search_btn = page.get_by_role("button", name="検索").first
            search_btn.click(force=True)

            # 3. リンクスキャン
            print("[STEP 2] 検索結果をスキャン中...")
            # 🚀 変更点4：無駄な3秒待機（wait_for_timeout）を消去し、結果リストが出るまで「賢く」待つ
            page.wait_for_selector('a[href*="/syllabus/s/sfsites/c/"]', state="visible", timeout=10000)
            
            target_link = None
            course_name_memory = "授業名取得失敗" 
            detail_url_memory = "URL取得失敗"

            links = page.get_by_role("link").all()
            for link in links:
                text = link.inner_text().strip()
                if request.query in text:
                    target_link = link
                    course_name_memory = text 
                    raw_href = link.get_attribute("href")
                    if raw_href:
                        if raw_href.startswith("http"):
                            detail_url_memory = raw_href
                        else:
                            detail_url_memory = f"https://syllabus.ritsumei.ac.jp{raw_href}"
                    break

            if not target_link:
                raise Exception("検索結果に該当する授業が見つかりませんでした。")

            # 4. 詳細ページへ移動
            print(f"[STEP 3] {course_name_memory} の詳細へ移動中...")
            target_link.scroll_into_view_if_needed()
            target_link.dispatch_event("click")

            # 5. 詳細データの抽出
            print("[STEP 4] データを抽出中...")
            page.wait_for_selector('td[data-label*="担当"]', state="visible")

            def get_text_by_label(label_name):
                try:
                    selector = f'td[data-label*="{label_name}"]'
                    element = page.locator(selector).first
                    return element.inner_text().strip()
                except:
                    return None

            teacher_res = get_text_by_label("担当教員") or get_text_by_label("担当") or "不明"
            time_res = get_text_by_label("曜日") or get_text_by_label("時限") or "不明"
            room_res = get_text_by_label("施設") or get_text_by_label("教室") or "不明"

            browser.close()

        print(f"🎉 取得成功: {course_name_memory}")

        return {
            "status": "success",
            "data": {
                "id": str(int(time.time())),
                "course": course_name_memory,
                "teacher": teacher_res,
                "time_slot": time_res,
                "room": room_res,
                "url": detail_url_memory 
            }
        }

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        try: browser.close()
        except: pass
        return {"status": "error", "message": str(e)}