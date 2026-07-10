import requests
import time

# 修改這個 URL 為你要調用的實際 URL
URL = "http://example.com/api/endpoint"
SECONDS = 1

def call_url():
    try:
        response = requests.get(URL, timeout=5)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: {response.status_code}")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")

if __name__ == "__main__":
    print(f"開始每{SECONDS}秒調用 URL: {URL}")
    print("按 Ctrl+C 停止\n")

    try:
        while True:
            call_url()
            time.sleep(SECONDS)
    except KeyboardInterrupt:
        print("\n\n程式已停止")
