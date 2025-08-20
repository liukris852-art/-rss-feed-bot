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

# 抓取详情页 Product Details + Features
def extract_tabs(soup):
    content_html = ""
    tab_section = soup.select_one(".product-detail-main")
    if not tab_section:
        return content_html

    # Product Details + Features
    h_tags = tab_section.find_all(["h2", "h3"])
    for h in h_tags:
        content_html += f"<{h.name}>{escape(h.get_text(strip=True))}</{h.name}>\n"
        for sibling in h.find_next_siblings():
            if sibling.name in ["h2", "h3"]:
                break
            content_html += str(sibling)
    return content_html

for p in new_products:
    try:
        resp_detail = requests.get(p['link'], headers=HEADERS)
        resp_detail.raise_for_status()
        soup_detail = BeautifulSoup(resp_detail.text, "html.parser")

        p['description'] = extract_tabs(soup_detail)

        # === 新增：从详情页抓取价格（覆盖列表页的 price）===
        price_text = ""
        # 常见价格位置（先拿带金额属性的）
        price_tag = soup_detail.select_one(".price-box .price, .special-price .price, span.price, .price")
        if price_tag:
            # 优先 data-price-amount
            if price_tag.has_attr("data-price-amount") and price_tag.get("data-price-amount"):
                price_text = price_tag.get("data-price-amount").strip()
            # 其次可见文本（含 $ 等符号）
            text_val = price_tag.get_text(strip=True)
            if text_val:
                price_text = text_val

        # 兜底：meta 里
        if not price_text:
            meta_tag = soup_detail.select_one('meta[itemprop="price"], meta[property="product:price:amount"]')
            if meta_tag and meta_tag.get("content"):
                price_text = meta_tag.get("content").strip()

        # 兜底：JSON-LD 里（有些页把价格放到 offers.price）
        if not price_text:
            for sc in soup_detail.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(sc.string or "")
                    def find_price(obj):
                        if isinstance(obj, dict):
                            if "price" in obj and obj["price"]:
                                return str(obj["price"])
                            if "offers" in obj:
                                off = obj["offers"]
                                if isinstance(off, dict) and "price" in off and off["price"]:
                                    return str(off["price"])
                                if isinstance(off, list):
                                    for o in off:
                                        if isinstance(o, dict) and "price" in o and o["price"]:
                                            return str(o["price"])
                            for v in obj.values():
                                r = find_price(v)
                                if r: return r
                        elif isinstance(obj, list):
                            for v in obj:
                                r = find_price(v)
                                if r: return r
                        return None
                    jp = find_price(data)
                    if jp:
                        price_text = jp
                        break
                except Exception:
                    pass

        if price_text:
            p['price'] = price_text
        # === 新增结束 ===

        time.sleep(1)  # 防止访问太快触发反爬虫
    except Exception as e:
        print(f"抓取详情页失败: {p['name']}, {e}")
        p['description'] = ""

# 更新历史
history.extend(new_products)
history.sort(key=lambda x: x.get("added_date", ""), reverse=True)

# 保存历史状态
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

# 生成合法 RSS
rss_items = []
for p in history:
    img_url = p.get('img','')
    description_text = f''
    if img_url:
        # 高清图片（保留你原来的写法）
        hd_img_url = img_url.replace("/250/", "/600/")  # 替换成更高清的尺寸
        description_text += f'<img src="{hd_img_url}" alt="{escape(p.get("name",""))}" /><br>'
    description_text += f'{p.get("description","")}<br>'
    description_text += f'Price: {escape(p.get("price",""))}'

    item = f"""
    <item>
      <title>{escape(p.get('name',''))}</title>
      <link>{p.get('link','')}</link>
      <description><![CDATA[{description_text}]]></description>
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
