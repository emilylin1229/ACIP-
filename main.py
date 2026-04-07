import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import time
import google.generativeai as genai

# 配置
CDC_URL = 'https://www.cdc.gov.tw/Category/MPage/FWEo643r7uqDO3-xM-zQ_g'
BASE_URL = 'https://www.cdc.gov.tw'
HISTORY_FILE = 'history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def fetch_new_records(history):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(CDC_URL, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    new_records = []
    # 查找所有包含 /File/Get/ 的 PDF 下載連結 (使用 reversed 讓最舊的先處理，確保順序正確)
    links = soup.find_all('a', href=lambda href: href and '/File/Get/' in href)
    links.reverse()
    
    for a in links:
        href = a.get('href')
        title = a.get_text(strip=True)
        if not title:
            title = "未知 CDC 檔案"
            
        full_url = urllib.parse.urljoin(BASE_URL, href)
        
        if full_url not in history:
            new_records.append({
                'title': title,
                'url': full_url
            })
    return new_records

def summarize_pdf_with_gemini(viewer_url):
    print(f"Fetching viewer page from {viewer_url}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 1. 取得實際的 PDF 下載連結 (CDC 外面那層是一頁 HTML Viewer)
    viewer_res = requests.get(viewer_url, headers=headers)
    viewer_soup = BeautifulSoup(viewer_res.text, 'html.parser')
    real_pdf_a = viewer_soup.find('a', class_='viewer-button')
    if not real_pdf_a:
        raise Exception("無法在 Viewer 頁面中找到實際的 PDF 下載連結")
    
    real_pdf_url = urllib.parse.urljoin(BASE_URL, real_pdf_a.get('href'))
    print(f"Downloading actual PDF from {real_pdf_url}...")
    
    pdf_path = '/tmp/temp_cdc_record.pdf'
    r = requests.get(real_pdf_url, headers=headers)
    with open(pdf_path, 'wb') as f:
        f.write(r.content)
    
    print("Uploading PDF to Gemini...")
    sample_file = genai.upload_file(path=pdf_path, display_name="CDC Record")
    
    print("Generating summary...")
    # 使用 gemini-1.5-flash 因為它更便宜且速度更快，處理一般 PDF 文件已經非常足夠
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    prompt = """
    這是一份台灣衛生福利部疾病管制署 (CDC) 的會議紀錄或新聞稿 PDF。
    請幫我閱讀內容並整理出這份文件的「重點摘要報告」，內容請包含：
    1. 會議/文件主旨
    2. 疾病或疫苗相關重點 (如病徵、防範措施、適用年齡等)
    3. 任何關鍵數據或決議事項
    請用繁體中文，排版美觀，以條理分明的 Bullet points 呈現，讓一般大眾能快速看懂。
    """
    response = model.generate_content([sample_file, prompt])
    
    # 刪除上傳的檔案以節省空間
    genai.delete_file(sample_file.name)
    os.remove(pdf_path)
    
    return response.text

def send_email(subject, body, recipient, gmail_user, gmail_password):
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = recipient
    msg['Subject'] = subject

    # 將 Markdown 的換行符號轉為 HTML 的 <br> 讓版面在 Email 裡好看
    html_body = body.replace("\n", "<br>")
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)
    server.send_message(msg)
    server.quit()

def main():
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_password = os.environ.get('GMAIL_PASSWORD')
    recipient = os.environ.get('EMAIL_RECIPIENT', 'rain1229o3@gmail.com')
    
    if not all([gemini_api_key, gmail_user, gmail_password]):
        print("Missing environment variables. Please check GEMINI_API_KEY, GMAIL_USER, GMAIL_PASSWORD.")
        return

    genai.configure(api_key=gemini_api_key)
    
    history = load_history()
    print(f"Loaded {len(history)} records from history.")
    
    new_records = fetch_new_records(history)
    print(f"Found {len(new_records)} new records.")
    
    for record in new_records:
        print(f"\nProcessing: {record['title']}")
        try:
            summary = summarize_pdf_with_gemini(record['url'])
            
            email_subject = f"【CDC AI 監控】發現新紀錄：{record['title']}"
            email_body = f"""
<h2>{record['title']}</h2>
<p><strong>原始文件連結：</strong> <a href="{record['url']}">{record['url']}</a></p>
<hr>
<h3>🤖 AI 重點摘要報告：</h3>
<div style="font-family: sans-serif; line-height: 1.6;">
{summary}
</div>
"""
            
            print(f"Sending email to {recipient}...")
            send_email(email_subject, email_body, recipient, gmail_user, gmail_password)
            
            history.append(record['url'])
            save_history(history)
            print("Successfully processed and saved to history.")
            
            # API 呼叫緩衝
            time.sleep(3)
            
        except Exception as e:
            print(f"Error processing {record['title']}: {e}")

if __name__ == "__main__":
    main()
