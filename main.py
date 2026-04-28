from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import time

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class SyllabusRequest(BaseModel):
    query: str

@app.post("/scrape-syllabus")
def scrape_syllabus(request: SyllabusRequest):
    root_url = "https://syllabus.ritsumei.ac.jp/syllabus/s/?language=ja"

    try:
        with sync_playwright() as p:
            # ブラウザを表示して実行（安定したらheadless=Trueに変更可能です）
            browser = p.chromium.launch(headless=False, slow_mo=800)
            page = browser.new_page()
            page.set_default_timeout(60000)

            print(f"\n[STEP 1] サイトにアクセス中...")
            page.goto(root_url, wait_until="networkidle")
            
            # 1. 検索窓に入力
            search_box = page.wait_for_selector('input.slds-input', state="visible")
            search_box.fill(request.query)
            page.keyboard.press("Enter")

            # 2. 検索実行
            search_btn = page.get_by_role("button", name="検索").first
            search_btn.click(force=True)

            # 3. リンクスキャン
            print("[STEP 4] 検索結果から授業を探しています...")
            page.wait_for_timeout(3000)
            page.mouse.wheel(0, 500)

            target_link = None
            course_name_memory = "授業名取得失敗" 
            detail_url_memory = "URL取得失敗" # 🌟 URLを暗記する変数を追加

            for i in range(10):
                links = page.get_by_role("link").all()
                for link in links:
                    text = link.inner_text().strip()
                    
                    # 入力したキーワードが含まれるリンクを探す
                    if request.query in text:
                        target_link = link
                        course_name_memory = text 
                        
                        # 🌟 超重要：クリックする前に、リンクの裏に隠れたURL(href)を引っこ抜く！
                        raw_href = link.get_attribute("href")
                        if raw_href:
                            # 相対URL（/syllabus/s/...）の場合は、ドメインをくっつけて完全なURLにする
                            if raw_href.startswith("http"):
                                detail_url_memory = raw_href
                            else:
                                detail_url_memory = f"https://syllabus.ritsumei.ac.jp{raw_href}"
                        
                        print(f"✅ ターゲット発見: {course_name_memory}")
                        print(f"🔗 確保したURL: {detail_url_memory}")
                        break
                        
                if target_link: break
                page.mouse.wheel(0, 200)
                page.wait_for_timeout(1000)

            if not target_link:
                raise Exception("検索結果に該当する授業が見つかりませんでした。")

            # 4. 詳細ページへ移動
            print("[STEP 5] 詳細ページへ移動中...")
            target_link.scroll_into_view_if_needed()
            target_link.dispatch_event("click")

            # 5. 詳細データの抽出
            print("[STEP 6] データを抽出しています...")
            # 担当という文字が出るまで待機
            page.wait_for_selector('td[data-label*="担当"]', state="visible", timeout=30000)

            def get_text_by_label(label_name):
                try:
                    selector = f'td[data-label*="{label_name}"]'
                    element = page.locator(selector).first
                    element.wait_for(state="visible", timeout=2000)
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
                "url": detail_url_memory # 🌟 クリック前に暗記しておいた本物のURLを返す
            }
        }

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        try: browser.close()
        except: pass
        return {"status": "error", "message": str(e)}