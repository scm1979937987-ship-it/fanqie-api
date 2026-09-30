import os
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fanqie-api")

app = FastAPI(title="Fanqie Novel API on Render", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMMON_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; ProjectTitan Build/QP1A.190711.020)",
    "Accept-Encoding": "gzip",
}

WEB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://fanqienovel.com/",
}

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Fanqie Novel API on Render",
        "endpoints": [
            "/search?query={key}",
            "/catolog?bookid={book_id}",
            "/detail?bookid={book_id}",
            "/content?item_id={item_id}"
        ]
    }

@app.get("/search")
def search(query: str = Query(..., description="搜索关键词"), offset: int = 0, tab_type: int = 3):
    url = f"https://novel.snssdk.com/api/novel/channel/homepage/search/search/v2/?device_platform=android&parent_enterfrom=novel_channel_search.tab.&offset={offset}&aid=1967&q={query}"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=8)
        data = resp.json()
        raw_list = data.get("data", {}).get("ret_data", [])
        
        book_list = []
        for item in raw_list:
            book_list.append({
                "book_id": item.get("book_id", ""),
                "book_name": item.get("title", item.get("book_name", "")),
                "author": item.get("author", ""),
                "thumb_url": item.get("thumb_url", ""),
                "abstract": item.get("abstract", ""),
                "creation_status": item.get("creation_status", 1),
                "score": item.get("score", "9.0"),
                "category": item.get("category", ""),
                "word_number": item.get("word_number", 0)
            })
            
        return {"code": 0, "book_data": book_list}
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"code": -1, "message": str(e), "book_data": []}

@app.get("/catolog")
@app.get("/catalog")
def get_catalog(bookid: str = Query(..., description="书籍ID")):
    url = f"https://fanqienovel.com/api/reader/directory/detail?bookId={bookid}"
    try:
        resp = requests.get(url, headers=WEB_HEADERS, timeout=8)
        data = resp.json()
        raw_volumes = data.get("data", {}).get("chapterListWithVolume", [])
        
        item_list = []
        for vol in raw_volumes:
            for item in vol:
                item_list.append({
                    "item_id": item.get("itemId", ""),
                    "title": item.get("title", "").replace("版权信息页", "").strip(),
                    "volume_name": item.get("volume_name", ""),
                    "chapter_word_number": item.get("word_count", 0),
                    "first_pass_time": item.get("firstPassTime", 0)
                })
                
        return {
            "code": 0,
            "data": {
                "item_data_list": item_list
            }
        }
    except Exception as e:
        logger.error(f"Catalog error: {e}")
        return {"code": -1, "message": str(e), "data": {"item_data_list": []}}

@app.get("/detail")
def get_detail(bookid: str = Query(..., description="书籍ID")):
    url = f"https://api5-normal-lf.fqnovel.com/reading/bookapi/multi-detail/v/?aid=1967&book_id={bookid}"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=8)
        data = resp.json()
        book_info = data.get("data", [])
        if book_info:
            return {"code": 0, "data": book_info[0]}
        return {"code": -1, "message": "Book not found"}
    except Exception as e:
        logger.error(f"Detail error: {e}")
        return {"code": -1, "message": str(e)}

@app.get("/multi-detail")
def get_multi_detail(book_id: str = Query(..., description="多个书籍ID")):
    url = f"https://api5-normal-lf.fqnovel.com/reading/bookapi/multi-detail/v/?aid=1967&book_id={book_id}"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=8)
        return resp.json()
    except Exception as e:
        return {"code": -1, "message": str(e), "data": []}

@app.get("/content")
def get_content(item_id: str = Query(..., description="章节ID"), type: str = "novel"):
    url = f"https://novel.snssdk.com/api/novel/book/reader/full/v1/?item_id={item_id}&aid=1967"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=8)
        res_data = resp.json()
        content = res_data.get("data", {}).get("content", "")
        if content:
            return {"content": content}
    except Exception as e:
        logger.error(f"Content fetch error: {e}")
        
    url_backup = f"https://fanqienovel.com/api/reader/full?itemId={item_id}"
    try:
        resp2 = requests.get(url_backup, headers=WEB_HEADERS, timeout=8)
        res_data2 = resp2.json()
        content2 = res_data2.get("data", {}).get("content", "")
        if content2:
            return {"content": content2}
    except Exception as e:
        logger.error(f"Backup content fetch error: {e}")

    return {"content": "该章节未能直接解密，请检查账号状态或稍后重试。"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
