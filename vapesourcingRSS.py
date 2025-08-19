import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime

RSS_FILE = "feed.xml"
BASE_URL = "https://www.vapesourcing.com"

def fetch_new_products():
    url = f"{BASE_URL}/new-arrivals.html"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text

def parse_products(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for item in soup.select(".item"):
        title_tag = item.select_one(".product-name a")
        link_tag = item.select_one(".product-name a")
        img_tag = item.select_one("img")
        price_tag = item.select_one(".price")

        if not (title_tag and link_tag and img_tag):
            continue

        title = title_tag.get_text(strip=True)
        link = link_tag["href"]
        image_url = img_tag["src"].replace("/250/", "/800/")  # 高清图
        price = price_tag.get_text(strip=True) if price_tag else "Price: N/A"

        # 抓取详情页 Features 部分
        detail_html = requests.get(link, timeout=10).text
        detail_soup = BeautifulSoup(detail_html, "html.parser")

        features_section = detail_soup.find(string=lambda t: "Features" in t)
        features_content = []
        if features_section:
            parent = features_section.find_parent()
            for tag in parent.find_all_next(["p", "ul"], limit=5):
                features_content.append(tag.get_text(" ", strip=True))

        # 分段 <p>
        description_parts = []
        description_parts.append(f'<img src="{image_url}" alt="{title}" />')
        description_parts.append(f"<p><b>{price}</b></p>")
        for para in features_content:
            description_parts.append(f"<p>{para}</p>")
        description_parts.append(f'<p><a href="{link}">View Product</a></p>')

        description = "\n".join(description_parts)

        products.append({
            "title": title,
            "link": link,
            "description": description
        })
    return products

def build_rss(products):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "Vape New Products Feed"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Latest vape products from vapesourcing"

    for p in products:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = p["title"]
        ET.SubElement(item, "link").text = p["link"]
        ET.SubElement(item, "description").text = f"<![CDATA[{p['description']}]]>"
        ET.SubElement(item, "pubDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    tree = ET.ElementTree(rss)
    tree.write(RSS_FILE, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    html = fetch_new_products()
    products = parse_products(html)
    build_rss(products)
    print(f"✅ RSS 已更新，包含价格 (写入 {RSS_FILE})")






