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
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 🎨 画像やデザインの読み込みをブロック（スピードアップ用）
            page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())

            page.set_default_timeout(30000)

            print(f"\n[STEP 1] アクセス中...")
            page.goto(root_url, wait_until="networkidle")
            
            # 1. 検索窓に入力
            search_box = page.locator('input.slds-input')
            search_box.wait_for(state="visible")
            search_box.fill(request.query)
            page.keyboard.press("Enter")

            # 2. 検索実行
            search_btn = page.locator('button:has-text("検索")').first
            search_btn.click(force=True)

            # 3. リンクスキャン
            print("[STEP 2] 検索結果をスキャン中...")
            
            target_link = None
            course_name_memory = "授業名取得失敗" 
            detail_url_memory = "URL取得失敗"

            # 🌟 変更点：厳しい条件での待機をやめ、「目的のリンクが出るまで0.5秒おきに最大30回（15秒）探す」ループに変更
            for _ in range(30):
                links = page.get_by_role("link").all()
                for link in links:
                    text = link.inner_text().strip()
                    # もしリンクの中に検索キーワードが含まれていたら確保！
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
                
                # 見つかったらループを抜け出して次のステップへ
                if target_link:
                    break
                
                # まだ見つからなければ、0.5秒だけ待ってからもう一度画面を探す
                page.wait_for_timeout(500)

            if not target_link:
                raise Exception("検索結果に該当する授業が見つかりませんでした。（15秒タイムアウト）")

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