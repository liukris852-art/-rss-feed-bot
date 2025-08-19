import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET

def fetch_new_products():
    url = "https://www.vapesourcing.com/new-arrivals.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.vapesourcing.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.text

def parse_products(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for product in soup.select(".item"):  
        title = product.select_one(".product-name a")
        link = title["href"] if title else None
        name = title.get_text(strip=True) if title else "No Title"

        img = product.select_one(".product-image img")
        image = img["src"] if img else None

        price = product.select_one(".price")
        price_text = price.get_text(strip=True) if price else "Price N/A"

        # Features 只抓后面的部分
        features_block = product.select_one(".desc")
        features = []
        if features_block:
            text_parts = features_block.get_text(separator="\n").split("\n")
            features = [line.strip() for line in text_parts if line.strip().startswith("·")]

        products.append({
            "title": name,
            "link": link,
            "image": image,
            "price": price_text,
            "features": features
        })
    return products

def generate_rss(products):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Vapesourcing New Arrivals"
    ET.SubElement(channel, "link").text = "https://www.vapesourcing.com/new-arrivals.html"
    ET.SubElement(channel, "description").text = "Latest products from Vapesourcing"
    ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    for product in products:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = product["title"]
        ET.SubElement(item, "link").text = product["link"]

        desc_parts = []
        if product["image"]:
            desc_parts.append(f'<img src="{product["image"]}" alt="{product["title"]}" /><br>')
        desc_parts.append(f"<p><strong>Price:</strong> {product['price']}</p>")
        for f in product["features"]:
            desc_parts.append(f"<p>{f}</p>")
        ET.SubElement(item, "description").text = "".join(desc_parts)

    return ET.tostring(rss, encoding="utf-8", method="xml").decode("utf-8")


if __name__ == "__main__":
    html = fetch_new_products()
    products = parse_products(html)
    rss_feed = generate_rss(products)
    with open("vapesourcing.xml", "w", encoding="utf-8") as f:
        f.write(rss_feed)






