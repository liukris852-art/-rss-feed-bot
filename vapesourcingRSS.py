import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import time

# 配置
URL = "https://vapesourcing.com/coming-soon.html"
HISTORY_FILE = "state.json"
RSS_FILE = "comingsoon.xml"
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# 浏览器模拟 headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://vapesourcing.com/",
    "Connection": "keep-alive",
}

# 请求网页，带重试
for attempt in range(1, MAX_RETRIES + 1):
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        break
    except requests.RequestException as e:
        print(f"请求失败（第 {attempt} 次）：{e}")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
        else:
            raise

# 解析页面
soup = BeautifulSoup(response.text, "html.parser")

# 提取产品信息
products = []
for product_li in soup.select("li.product-item"):
    name_tag = product_li.select_one(".product-name a")
    if not name_tag:
        continue
    name = name_tag.get_text(strip=True)
    link = name_tag['href']
    if not link.startswith("http"):
        link = "https://vapesourcing.com" + link

    img_tag = product_li.select_one(".product-image a img")
    img = img_tag.get("src") or img_tag.get("data-src") if img_tag else ""

    price_tag = product_li.select_one(".price")
    price = price_tag.get_text(strip=True) if price_tag else ""

    products.append({
        "name": name,
        "link": link,
        "img": img,
        "price": price
    })

# 读取历史数据
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history_links = set(json.load(f))
else:
    history_links = set()

# 筛选新增产品
new_products = [p for p in products if p['link'] not in history_links]

# 更新历史数据
all_links = list(history_links.union([p['link'] for p in new_products]))
with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(all_links, f, ensure_ascii=False, indent=2)

# 生成 RSS Feed
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")
ET.SubElement(channel, "title").text = "VapeSourcing Coming Soon"
ET.SubElement(channel, "link").text = URL
ET.SubElement(channel, "description").text = "Daily update of new coming soon products"

for p in new_products:
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = p['name']
    ET.SubElement(item, "link").text = p['link']
    desc_html = f'<img src="{p["img"]}" /><br/>Price: {p["price"]}'
    ET.SubElement(item, "description").text = desc_html
    ET.SubElement(item, "guid").text = p['link']
    ET.SubElement(item, "pubDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

# 保存 RSS 文件
tree = ET.ElementTree(rss)
tree.write(RSS_FILE, encoding="utf-8", xml_declaration=True)

print(f"抓取完成，新增产品 {len(new_products)} 条，RSS 文件已生成：{RSS_FILE}")
