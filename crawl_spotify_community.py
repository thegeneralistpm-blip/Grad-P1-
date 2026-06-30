"""
crawl_spotify_community.py
─────────────────────────────────────────────────────────────────────────────
Spotify Community Forum Scrapy Spider
Crawls the Idea Submissions board deeply, follows post details,
and saves the normalized reviews to live_reviews.db.

Run simply via: python crawl_spotify_community.py
─────────────────────────────────────────────────────────────────────────────
"""

import sqlite3
import sys
import time
from datetime import datetime, timezone
import scrapy
from scrapy.crawler import CrawlerProcess

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DB_PATH = "live_reviews.db"

# Scrapy Item Pipeline to write directly to SQLite database
class SQLitePipeline:
    def open_spider(self, spider):
        self.conn = sqlite3.connect(DB_PATH)
        self.cur = self.conn.cursor()
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_reviews (
                review_id TEXT PRIMARY KEY,
                source_platform TEXT,
                source_url TEXT,
                review_text TEXT,
                rating INTEGER,
                upvotes INTEGER,
                published_at TEXT,
                processing_status TEXT DEFAULT 'pending'
            );
            """
        )
        self.conn.commit()
        self.new_records = 0

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()
        print(f"\n======================================================")
        print(" SPOTIFY COMMUNITY CRAWL COMPLETE!")
        print(f" New records saved to DB: {self.new_records}")
        print("======================================================")

    def process_item(self, item, spider):
        try:
            self.cur.execute(
                """
                INSERT OR IGNORE INTO raw_reviews 
                (review_id, source_platform, source_url, review_text, rating, upvotes, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    item["review_id"],
                    "spotify_community",
                    item["source_url"],
                    item["review_text"],
                    None,
                    item["upvotes"],
                    item["published_at"]
                )
            )
            if self.cur.rowcount > 0:
                self.new_records += 1
        except Exception as exc:
            spider.logger.error(f"Error saving to DB: {exc}")
        return item


class SpotifyCommunitySpider(scrapy.Spider):
    name = "spotify_community"
    allowed_domains = ["community.spotify.com"]
    start_urls = [
        "https://community.spotify.com/t5/Live-Ideas/idb-p/ideas_live/tab/most-kudoed"
    ]
    
    custom_settings = {
        "ITEM_PIPELINES": {
            "__main__.SQLitePipeline": 300,
        },
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 1.5, # Respectful delay between requests
        "LOG_LEVEL": "INFO"
    }

    def __init__(self, max_pages=3, *args, **kwargs):
        super(SpotifyCommunitySpider, self).__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.page_count = 1

    def parse(self, response):
        self.logger.info(f"Parsing index page: {response.url}")
        
        # Select individual post links containing /idi-p/
        post_links = response.css("a[href*='/idi-p/']")
            
        for link in post_links:
            href = link.attrib.get("href")
            if href:
                # Follow thread details
                yield response.follow(href, callback=self.parse_post_details)
                
        # Handle pagination
        if self.page_count < self.max_pages:
            self.page_count += 1
            next_url = f"https://community.spotify.com/t5/Live-Ideas/idb-p/ideas_live/page/{self.page_count}"
            yield response.follow(next_url, callback=self.parse)

    def parse_post_details(self, response):
        # Extract title
        title_el = response.css("h1.lia-message-subject, .page-header h1::text").get()
        title = title_el.strip() if title_el else ""
        
        # Extract post body
        body_el = response.css(".lia-message-body-content, .post-body")
        body_text = "".join(body_el.css("::text").getall()).strip()
        
        if not body_text:
            return
            
        # Combine title and body
        full_text = f"Community Idea: {title}. {body_text}" if title else body_text
        
        # Extract kudos (upvotes)
        kudos_text = response.css(".kudo-count::text, .KudoCountWrapper::text, .lia-kudos-count::text").get()
        kudos = 0
        if kudos_text:
            try:
                kudos = int(kudos_text.strip().replace(",", ""))
            except ValueError:
                kudos = 0
                
        # Extract ID from URL
        post_id = response.url.split("/td-p/")[-1].split("/")[0] if "/td-p/" in response.url else response.url
        
        # Extract date
        date_el = response.css("time.local-date::attr(datetime), .post-date time::attr(datetime)").get()
        published_at = date_el if date_el else datetime.now(timezone.utc).isoformat()
        
        yield {
            "review_id": f"spot_comm_{post_id}",
            "source_url": response.url,
            "review_text": full_text,
            "upvotes": kudos,
            "published_at": published_at
        }


def main():
    print("======================================================")
    print("         SPOTIFY COMMUNITY CRAWLER (SCRAPY)")
    print("======================================================")
    process = CrawlerProcess()
    process.crawl(SpotifyCommunitySpider, max_pages=5)
    process.start()

if __name__ == "__main__":
    main()
