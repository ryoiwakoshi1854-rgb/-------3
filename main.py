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
            
            # 画像やデザインの通信を遮断（スピードアップ）
            page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())

            page.set_default_timeout(30000)

            print(f"\n[STEP 1] アクセス中...")
            page.goto(root_url, wait_until="networkidle")
            
            # 1. 検索窓に入力
            search_box = page.locator('input.slds-input')
            search_box.wait_for(state="visible")
            search_box.fill(request.query)

            # 2. 検索実行
            # 🌟 修正ポイント：隠れボタンを無視し、「見えている」検索ボタンだけを確実にJSでクリック
            search_btn = page.locator('button.slds-button_brand:has-text("検索") >> visible=true').first
            search_btn.evaluate("node => node.click()")

            print("[STEP 2] 検索結果をスキャン中...")
            
            target_text = None
            detail_url_memory = "URL取得失敗"

            for _ in range(30):
                found_link = page.evaluate('''(q) => {
                    const links = Array.from(document.querySelectorAll('a'));
                    for (let a of links) {
                        const text = (a.innerText || a.textContent || "").trim();
                        if (text.includes(q) && a.getAttribute('href')) {
                            return { text: text, href: a.getAttribute('href') };
                        }
                    }
                    return null;
                }''', request.query)

                if found_link:
                    target_text = found_link['text']
                    raw_href = found_link['href']
                    if raw_href.startswith("http"):
                        detail_url_memory = raw_href
                    else:
                        detail_url_memory = f"https://syllabus.ritsumei.ac.jp{raw_href}"
                    break
                
                page.wait_for_timeout(500)

            if not target_text:
                raise Exception("検索結果に該当する授業が見つかりませんでした。（15秒タイムアウト）")

            # 4. 詳細ページへ移動
            print(f"[STEP 3] {target_text} の詳細へ移動中...")
            # 🌟 修正ポイント：リンクのクリックもフリーズ回避のためJS強制クリックに変更
            target_link = page.locator(f'a:has-text("{target_text}") >> visible=true').first
            target_link.evaluate("node => node.click()")

            # 5. 詳細データの抽出
            print("[STEP 4] データを抽出中...")
            page.wait_for_selector('td[data-label*="担当"]', state="visible")

            def get_text_by_label(label_name):
                try:
                    selector = f'td[data-label*="{label_name}"]'
                    element = page.locator(selector).first
                    text = element.text_content()
                    return text.strip() if text else None
                except:
                    return None

            teacher_res = get_text_by_label("担当教員") or get_text_by_label("担当") or "不明"
            time_res = get_text_by_label("曜日") or get_text_by_label("時限") or "不明"
            room_res = get_text_by_label("施設") or get_text_by_label("教室") or "不明"

            browser.close()

        print(f"🎉 取得成功: {target_text}")

        return {
            "status": "success",
            "data": {
                "id": str(int(time.time())),
                "course": target_text,
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