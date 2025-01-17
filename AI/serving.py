import re
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
import httpx
import asyncio
from typing import List, Optional
from datetime import datetime
import random
from functools import lru_cache
import logging
from contextlib import asynccontextmanager
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enhanced Pydantic models with validation


class Comment(BaseModel):
    text: str = Field(..., min_length=1, max_length=3000)
    rating: int = Field(..., ge=1, le=5)


class ProductReview(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    comments: List[Comment] = Field(..., min_items=1, max_items=3000)


class ProductResponse(BaseModel):
    product_name: str
    summary: str


class Settings:
    MAX_CONCURRENT_REQUESTS: int = int(
        os.getenv("MAX_CONCURRENT_REQUESTS", 10))
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", 3))
    CLIENT_TIMEOUT: float = float(os.getenv("CLIENT_TIMEOUT", 120.0))
    OLLAMA_SERVERS: List[str] = os.getenv(
        "OLLAMA_SERVERS", "http://localhost:11434/api/generate,https://319b-118-70-156-47.ngrok-free.app/api/generate").split(",")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3.2")


settings = Settings()


# Danh sách từ khóa spam cơ bản
SPAM_KEYWORDS = [  # Từ khóa liên quan đến quảng cáo
    "mua ngay", "ship cod", "liên hệ ngay", "hotline", "zalo", "facebook", "website",
    "đặt hàng", "thanh toán", "bán chạy", "hàng sale", "hàng giảm giá", "hàng thanh lý",

    # Từ khóa liên quan đến spam link
    "http://", "https://", "www.", ".com", ".vn", ".shop", ".online", "click vào đây", "truy cập link",
    "xem thêm tại", "đường dẫn", "liên kết", "fanpage", "trang chủ", "link giảm giá", "link mua hàng",

    # Từ khóa liên quan đến spam dịch vụ
    "dịch vụ seo", "dịch vụ marketing", "dịch vụ quảng cáo", "dịch vụ thiết kế", "dịch vụ vận chuyển",
    "dịch vụ ship hàng", "dịch vụ làm đẹp", "dịch vụ spa", "dịch vụ sửa chữa", "dịch vụ bảo hành",
    "dịch vụ gia công", "dịch vụ in ấn", "dịch vụ đăng ký", "dịch vụ tư vấn", "dịch vụ chăm sóc khách hàng",

    # Từ khóa liên quan đến spam lừa đảo
    "trúng thưởng", "trúng giải", "nhận quà", "quà tặng", "quà miễn phí", "quà khuyến mãi",
    "quà may mắn", "quà tri ân", "quà sinh nhật", "quà đặc biệt", "quà hấp dẫn", "quà giá trị",
    "quà cao cấp", "quà độc quyền", "quà duy nhất", "quà giới hạn",

    # Từ khóa liên quan đến spam số điện thoại
    "số điện thoại", "sđt", "call", "gọi ngay", "viber", "telegram", "whatsapp", "messenger",
    "skype", "line",

    # Từ khóa liên quan đến spam lặp lại
    "cảm ơn", "like", "share", "comment", "sub", "theo dõi", "ủng hộ", "đăng ký", "kênh",
    "video", "clip", "livestream", "stream", "live", "tiktok", "youtube", "instagram", "twitter",

    # Từ khóa liên quan đến spam cảm xúc quá mức
    "quá tuyệt vời", "quá hài lòng", "quá ấn tượng", "quá bất ngờ", "quá phấn khích", "quá thích thú",
    "quá mãn nguyện", "quá hạnh phúc", "quá vui mừng", "quá cảm động", "quá xúc động", "quá biết ơn",
    "quá cảm kích", "quá trân trọng", "quá yêu thích", "quá đam mê", "quá cuồng nhiệt", "quá nhiệt tình",
    "quá hào hứng", "quá kỳ vọng", "quá mong đợi", "quá chờ đợi", "quá hy vọng", "quá tin tưởng",
    "quá tự hào", "quá kiêu hãnh", "quá hãnh diện", "quá tự tin", "quá lạc quan", "quá tích cực",
    "quá năng động", "quá sáng tạo", "quá đổi mới", "quá cải tiến", "quá phát triển", "quá hoàn thiện",
    "quá hoàn hảo", "quá xuất sắc", "quá vượt trội", "quá đỉnh cao", "quá đẳng cấp", "quá sang trọng",
    "quá cao cấp", "quá độc đáo", "quá khác biệt", "quá ấn tượng", "quá nổi bật", "quá thu hút",
    "quá hấp dẫn", "quá lôi cuốn", "quá quyến rũ", "quá mê hoặc", "quá cuốn hút", "quá lôi kéo",
    "quá kích thích", "quá kích động", "quá phấn khích", "quá hưng phấn", "quá phấn chấn", "quá phấn khởi",
    "quá phấn đấu", "thời tiết"]


def is_spam(comment_text: str) -> bool:
    # Kiểm tra từ khóa spam trong comment
    if any(keyword.lower() in comment_text.lower() for keyword in SPAM_KEYWORDS):
        return True

    # Kiểm tra xem comment có chứa URL không
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    if re.search(url_pattern, comment_text):
        return True

    # Kiểm tra nếu có từ nào có độ dài > 8 ký tự
    if any(len(word) > 8 for word in comment_text.split()):
        return True

    # Có thể thêm các phương pháp khác như kiểm tra số lượng dấu câu hay mật độ từ khóa
    return False


def filter_valid_comments(comments: List[dict]) -> List[dict]:
    valid_comments = []
    for comment in comments:
        try:
            # Kiểm tra tính hợp lệ của comment bằng cách khởi tạo đối tượng Comment
            valid_comment = Comment(**comment)

            # Kiểm tra số từ trong comment (ít nhất 4 từ)
            if len(valid_comment.text.split()) >= 4:
                # Kiểm tra spam và từ dài hơn 8 ký tự
                if not is_spam(valid_comment.text):
                    valid_comments.append(comment)
        except:
            # Bỏ qua nếu comment không hợp lệ
            continue
    return valid_comments


# Connection manager for startup/shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    client_pool.clients = [
        httpx.AsyncClient(
            timeout=settings.CLIENT_TIMEOUT,
            limits=httpx.Limits(
                max_keepalive_connections=5, max_connections=10)
        )
        for _ in range(settings.MAX_CONCURRENT_REQUESTS)
    ]
    yield
    # Shutdown
    await asyncio.gather(*[client.aclose() for client in client_pool.clients])

app = FastAPI(lifespan=lifespan)


class LoadBalancer:
    def __init__(self, servers: List[str]):
        self.servers = servers
        self.current = 0
        self.lock = asyncio.Lock()
        self.server_health = {server: True for server in servers}
        self.health_check_interval = int(
            os.getenv("HEALTH_CHECK_INTERVAL", 60))  # seconds
        self.health_check_task = None

    async def start_health_check_loop(self):
        """Start the periodic health check loop"""
        while True:
            await self.health_check()
            await asyncio.sleep(self.health_check_interval)

    async def get_next_server(self) -> str:
        async with self.lock:
            # Skip unhealthy servers
            for _ in range(len(self.servers)):
                server = self.servers[self.current]
                self.current = (self.current + 1) % len(self.servers)
                if self.server_health[server]:
                    return server
            raise HTTPException(
                status_code=503, detail="No healthy servers available")

    async def mark_server_down(self, server: str):
        async with self.lock:
            self.server_health[server] = False
            logger.warning(f"Server marked as unhealthy: {server}")

    async def mark_server_up(self, server: str):
        async with self.lock:
            self.server_health[server] = True
            logger.info(f"Server marked as healthy: {server}")

    async def check_server_health(self, server: str, client: httpx.AsyncClient) -> bool:
        """Check health of a single server by accessing its root endpoint"""
        try:
            # Extract base URL from the full API endpoint
            base_url = server.split('/api/')[0]
            response = await client.get(base_url, timeout=5.0)

            if response.status_code in (200, 201, 202):
                await self.mark_server_up(server)
                logger.info(f"Health check passed for server: {server}")
                return True
            else:
                await self.mark_server_down(server)
                logger.warning(
                    f"Health check failed for server: {server} with status code: {response.status_code}")
                return False
        except Exception as e:
            await self.mark_server_down(server)
            logger.error(
                f"Health check failed for server: {server} with error: {str(e)}")
            return False

    async def health_check(self):
        """Check health of all servers"""
        logger.info("Starting periodic health check of all servers")
        async with httpx.AsyncClient() as client:
            # Create tasks for all server health checks
            tasks = [self.check_server_health(
                server, client) for server in self.servers]
            # Run all health checks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    client_pool.clients = [
        httpx.AsyncClient(
            timeout=settings.CLIENT_TIMEOUT,
            limits=httpx.Limits(
                max_keepalive_connections=5, max_connections=10)
        )
        for _ in range(settings.MAX_CONCURRENT_REQUESTS)
    ]

    # Start the health check loop
    load_balancer.health_check_task = asyncio.create_task(
        load_balancer.start_health_check_loop())
    logger.info("Started periodic health check task")

    yield

    # Shutdown
    if load_balancer.health_check_task:
        load_balancer.health_check_task.cancel()
        try:
            await load_balancer.health_check_task
        except asyncio.CancelledError:
            logger.info("Health check task cancelled")

    await asyncio.gather(*[client.aclose() for client in client_pool.clients])


class ClientPool:
    def __init__(self):
        self.clients: List[httpx.AsyncClient] = []
        self.current = 0
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)

    async def get_client(self) -> httpx.AsyncClient:
        async with self.lock:
            client = self.clients[self.current]
            self.current = (self.current + 1) % len(self.clients)
            return client


# Initialize global instances
load_balancer = LoadBalancer(settings.OLLAMA_SERVERS)
client_pool = ClientPool()

# Cache prompt template


@lru_cache(maxsize=1)
def get_prompt_template() -> str:
    return """
    Định dạng trả lời:
    {{
        "product_name": "string",
        "summary": "string",
    }}
    "summary" :nội dung tóm tắt đến từ các comments tiêu cực và tích cực, hãy viết mạch lạc nhưng vẫn phải chi tiết, độ dài tối thiểu 30 từ.
    "comments" :các comment liên quan đến sản phẩm.
    Đây là các comment: {comments} về sản phẩm {product_name}.
    """


async def retry_with_backoff(func, max_retries: int = settings.RETRY_ATTEMPTS):
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries - 1:
                logger.error(f"Final retry attempt failed: {str(e)}")
                raise
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
    raise last_exception


async def generate_with_ollama(prompt: str) -> str:
    async with client_pool.semaphore:
        client = await client_pool.get_client()
        server_url = await load_balancer.get_next_server()

        async def make_request():
            payload = {
                "model": settings.MODEL_NAME,
                "prompt": prompt,
                "format": ProductResponse.model_json_schema(),
                "options": {
                    "temperature": 0.4
                },
                "stream": False
            }
            try:
                response = await client.post(server_url, json=payload)
                response.raise_for_status()
                await load_balancer.mark_server_up(server_url)
                print(response.json()["response"])
                return response.json()["response"]
            except httpx.HTTPError as e:
                await load_balancer.mark_server_down(server_url)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error communicating with Ollama server: {str(e)}"
                )

        return await retry_with_backoff(make_request)


@app.post("/review-product/")
async def review_product(review: ProductReview):
    start_time = datetime.now()
    logger.info(f"Processing review for product: {review.product_name}")
    logger.info(f"review: {review}")

    comments_text = "\n".join(
        f"Comment {i+1}: {comment.text} (Số sao: {comment.rating})"
        for i, comment in enumerate(filter_valid_comments(review.comments))
    )

    prompt = get_prompt_template().format(comments=comments_text,
                                          product_name=review.product_name)

    try:
        result = await generate_with_ollama(prompt)
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Review processed in {processing_time:.2f} seconds")
        return ProductResponse.model_validate_json(result)
    except Exception as e:
        logger.error(f"Error processing review: {str(e)}")
        raise


@app.get("/health")
async def health_check():
    await load_balancer.health_check()
    return {
        "status": "healthy",
        "server_health": load_balancer.server_health,
        "concurrent_requests": settings.MAX_CONCURRENT_REQUESTS - client_pool.semaphore._value,
        "health_check_interval": load_balancer.health_check_interval
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        workers=4,
        log_level="info"
    )
