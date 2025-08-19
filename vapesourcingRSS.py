import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from xml.sax.saxutils import escape
import os

# 文件路径
RSS_FILE = "comingsoon.xml"
STATE_FILE = "state.json"

URL = "https://vapesourcing.com/coming-soon.html"

# 获取页面内容
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(URL, headers=headers)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

# 解析产品列表
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

# 找出新增产品
history_names = {p["name"] for p in history}
new_products = [p for p in products if p["name"] not in history_names]

# 更新历史
history.extend(new_products)
# 按日期倒序排列
history.sort(key=lambda x: x.get("added_date", ""), reverse=True)

# 保存历史状态
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

# 生成合法 RSS
rss_items = []
for p in history:
    description_text = f"Price: {p.get('price','')}"
    description_text = escape(description_text)  # 转义特殊字符
    img_url = p.get('img','')  # 避免 KeyError
    item = f"""
    <item>
      <title>{escape(p.get('name',''))}</title>
      <link>{p.get('link','')}</link>
      <description>{description_text}</description>
      <pubDate>{p.get('added_date','')}</pubDate>
      {f'<enclosure url="{img_url}" type="image/jpeg" />' if img_url else ''}
    </item>
    """
    rss_items.append(item.strip())

rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>VapeSourcing Coming Soon</title>
  <link>{URL}</link>
  <description>Latest VapeSourcing Coming Soon Products</description>
  {"".join(rss_items)}
</channel>
</rss>
"""

with open(RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"RSS 文件生成成功：{RSS_FILE}, 新增 {len(new_products)} 个产品")


