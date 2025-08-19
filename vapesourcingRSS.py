import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from xml.sax.saxutils import escape
import os
import time

# 文件路径
RSS_FILE = "comingsoon.xml"
STATE_FILE = "state.json"

LIST_URL = "https://vapesourcing.com/coming-soon.html"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 获取列表页
resp = requests.get(LIST_URL, headers=HEADERS)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

# 解析列表页产品
products = []
for item in soup.select("li.product-item"):
    name_tag = item.select_one(".product-name a")
    img_tag = item.select_one(".product-image img")
    price_tag = item.select_one(".price-box .price")
    if not name_tag:
        continue
    name = name_tag.get_text(strip=True)
    link = "https://vapesourcing.com" + name_tag['href']
    img = img_tag['data-src'] if img_tag and img_tag.get('data-src') else ""
    price = price_tag.get_text(strip=True) if price_tag else ""
    products.append({
        "name": name,
        "link": link,
        "img": img,
        "price": price,
        "added_date": datetime.utcnow().strftime("%Y-%m-%d")
    })

# 加载历史数据
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
else:
    history = []

history_names = {p["name"] for p in history}
new_products = [p for p in products if p["name"] not in history_names]

# 抓取详情页（仅新增产品）
for p in new_products:
    try:
        resp_detail = requests.get(p['link'], headers=HEADERS)
        resp_detail.raise_for_status()
        soup_detail = BeautifulSoup(resp_detail.text, "html.parser")
        detail_div = soup_detail.select_one(".product-detail-main .new-product-msg")
        features_texts = []
        if detail_div:
            # 删除折叠按钮
            for span in detail_div.select("span.open"):
                span.decompose()
            # 只抓 Features 后面的 <p>
            features_start = False
            for tag in detail_div.find_all(['p', 'div']):
                text = tag.get_text(strip=True)
                if not text:
                    continue
                if 'Features' in text:
                    features_start = True
                    continue
                if features_start:
                    features_texts.append(text)
            # 每条用 <p> 包裹
            description_html = ""
            if p['img']:
                description_html += f'<p><img src="{p["img"]}" alt="{escape(p["name"])}" /></p>'
            for ft in features_texts:
                description_html += f'<p>{escape(ft)}</p>'
            # 添加原网页链接
            description_html += f'<p><a href="{p["link"]}">Click here for full details</a></p>'
            p['description'] = description_html
        else:
            p['description'] = ""
        time.sleep(1)
    except Exception as e:
        print(f"抓取详情页失败: {p['name']}, {e}")
        p['description'] = ""

# 更新历史
history.extend(new_products)
history.sort(key=lambda x: x.get("added_date", ""), reverse=True)

# 保存历史状态
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

# 生成 RSS
rss_items = []
for p in history:
    item = f"""
    <item>
      <title>{escape(p.get('name',''))}</title>
      <link>{p.get('link','')}</link>
      <description><![CDATA[{p.get('description','')}]]></description>
      <pubDate>{p.get('added_date','')}</pubDate>
    </item>
    """
    rss_items.append(item.strip())

rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>VapeSourcing Coming Soon</title>
  <link>{LIST_URL}</link>
  <description>Latest VapeSourcing Coming Soon Products</description>
  {"".join(rss_items)}
</channel>
</rss>
"""

with open(RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"RSS 文件生成成功：{RSS_FILE}, 新增 {len(new_products)} 个产品")





