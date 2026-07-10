import sys
from playwright.sync_api import sync_playwright

def take_screenshot(url, output_path="screenshot.png"):
    print(f"正在連線至: {url} ...")
    
    # 啟動 Playwright 並開啟 Chromium 瀏覽器
    with sync_playwright() as p:
        # headless=True 代表在背景執行，不會彈出瀏覽器視窗
        browser = p.chromium.launch(headless=True)
        
        # 建立一個新的瀏覽器頁面
        page = browser.new_page()
        
        # 設定模擬的視窗大小（可依需求調整）
        page.set_viewport_size({"width": 1280, "height": 800})
        
        try:
            # 前往指定的 URL，wait_until="networkidle" 會等待網路活動停止（網頁載入完成）
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 執行截圖。full_page=True 會抓取整張網頁（包含滾動條下方的內容）
            # 如果只想抓目前視窗看得到的範圍，把 full_page=True 刪除即可
            page.screenshot(path=output_path, full_page=True)
            print(f" 截圖成功！已儲存至: {output_path}")
            
        except Exception as e:
            print(f" 截圖失敗，錯誤訊息: {e}")
            
        finally:
            # 確保瀏覽器一定會關閉
            browser.close()

if __name__ == "__main__":
    # 讓使用者在終端機輸入網址
    target_url = input("請輸入想要截圖的網址 (例如 https://google.com): ").strip()
    
    if not target_url.startswith(("http://", "https://")):
        # 如果使用者沒輸入 http，自動幫忙補上 https
        target_url = "https://" + target_url
        
    take_screenshot(target_url)