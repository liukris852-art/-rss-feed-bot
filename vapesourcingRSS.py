import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import datetime

# 文件路径
rss_file = Path("comingsoon.xml")
state_file = Path("state.json")

# 1. 加载历史数据
if state_file.exists():
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        # 只保留字典元素，防止报错
        history = [h for h in history if isinstance(h, dict)]
    except Exception:
        history = []
else:
    history = []

# 2. 抓取页面
url = "https://vapesourcing.com/coming-soon.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
resp = requests.get(url, headers=headers)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")
products_list = soup.select("li.product-item")

new_products = []
today_str = datetime.date.today().isoformat()

for li in products_list:
    name_tag = li.select_one(".product-name a")
    link_tag = li.select_one(".product-name a")
    img_tag = li.select_one(".product-image img")
    price_tag = li.select_one(".price-box .price")

    if name_tag and link_tag:
        product = {
            "name": name_tag.get_text(strip=True),
            "link": "https://vapesourcing.com" + link_tag.get("href", ""),
            "image": img_tag.get("data-src") or img_tag.get("src") or "",
            "price": price_tag.get_text(strip=True) if price_tag else "N/A",
            "added_date": today_str
        }
        # 只添加历史中不存在的产品
        if not any(h["link"] == product["link"] for h in history):
            history.append(product)
            new_products.append(product)

# 3. 按日期排序（最新在前）
history.sort(key=lambda x: x.get("added_date", ""), reverse=True)

# 4. 保存 state.json
with open(state_file, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

# 5. 生成 RSS 文件
def generate_rss(products, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<rss version="2.0"><channel>\n')
        f.write('<title>VapeSourcing Coming Soon</title>\n')
        f.write('<link>https://vapesourcing.com/coming-soon.html</link>\n')
        f.write('<description>Latest VapeSourcing Coming Soon Products</description>\n')
        for p in products:
            f.write(f"<item>\n")
            f.write(f"<title>{p['name']} ({p['added_date']})</title>\n")
            f.write(f"<link>{p['link']}</link>\n")
            f.write(f"<description>Price: {p.get('price','N/A')}<br><img src='{p.get('image','')}'/></description>\n")
            f.write(f"</item>\n")
        f.write("</channel></rss>\n")

generate_rss(history, rss_file)

print(f"抓取完成！新增 {len(new_products)} 个产品，RSS 文件已生成。")
