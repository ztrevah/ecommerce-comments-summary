import asyncio
import httpx
from pydantic import BaseModel, Field, ValidationError, validator
from faker import Faker
import random
from tqdm.asyncio import tqdm
import json
import re
from typing import List
from datetime import datetime

# Enhanced models with validation


class Comment(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    rating: int = Field(..., ge=1, le=5)

    @validator('text')
    def validate_text(cls, v):
        # Remove excessive whitespace
        v = ' '.join(v.split())
        # Ensure text doesn't contain invalid characters
        if not re.match(r'^[\w\s.,!?()-]+$', v):
            v = re.sub(r'[^\w\s.,!?()-]', '', v)
        return v[:1000]  # Ensure max length


class ProductReview(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    comments: List[Comment] = Field(..., min_items=1, max_items=100)

    @validator('product_name')
    def validate_product_name(cls, v):
        # Remove excessive whitespace and special characters
        v = ' '.join(v.split())
        v = re.sub(r'[^\w\s-]', '', v)
        return v[:200]  # Ensure max length


class TestResultStats(BaseModel):
    total_requests: int
    successful_responses: int
    error_responses: int
    exceptions: int
    validation_errors: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    timestamp: datetime


# Initialize faker with consistent seed for reproducibility
fake = Faker()
Faker.seed(12345)


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Sanitize text input to ensure it meets our requirements."""
    # Remove excessive whitespace
    text = ' '.join(text.split())
    # Remove potentially problematic characters
    text = re.sub(r'[^\w\s.,!?()-]', '', text)
    return text[:max_length]


def generate_review(num_comments=10) -> ProductReview:
    """Generate a valid ProductReview with sanitized data."""
    try:
        product_name = sanitize_text(fake.company(), 200)
        comments = []

        for _ in range(min(num_comments, 100)):  # Ensure max 100 comments
            # Generate and sanitize fake text
            text = sanitize_text(fake.paragraph())
            rating = random.randint(1, 5)

            comment = Comment(text=text, rating=rating)
            comments.append(comment)

        review = ProductReview(product_name=product_name, comments=comments)
        # Validate the entire object
        review.dict()  # This will raise ValidationError if invalid
        return review

    except ValidationError as e:
        logger.error(f"Validation error in generate_review: {e}")
        raise


async def send_request(client: httpx.AsyncClient, review: ProductReview) -> dict:
    """Send a request with validated data and return the result."""
    try:
        # Validate and convert to dict
        review_dict = review.dict()

        start_time = asyncio.get_event_loop().time()
        response = await client.post('http://localhost:8000/review-product/',
                                     json=review_dict,
                                     timeout=120.0)
        end_time = asyncio.get_event_loop().time()
        response_time = end_time - start_time

        result = {
            'status': 'success' if response.status_code == 200 else 'error',
            'response_time': response_time,
            'request_data': review_dict,
        }

        try:
            result['response_content'] = response.json()
        except json.JSONDecodeError:
            result['response_content'] = response.text

        if response.status_code != 200:
            result['response_code'] = response.status_code

        return result

    except ValidationError as e:
        return {
            'status': 'validation_error',
            'error': str(e),
            'request_data': review_dict if 'review_dict' in locals() else None
        }
    except httpx.HTTPError as e:
        return {
            'status': 'exception',
            'exception': str(e),
            # 'request_data': review_dict if 'review_dict' in locals() else None
        }


async def send_multiple_requests(num_requests: int, num_comments: int = 10) -> List[dict]:
    """Send multiple requests with progress tracking."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        for _ in range(num_requests):
            try:
                review = generate_review(num_comments)
                task = asyncio.ensure_future(send_request(client, review))
                tasks.append(task)
            except ValidationError as e:
                logger.error(f"Failed to generate valid review: {e}")
                continue

        responses = await tqdm.gather(*tasks, desc="Sending requests")
        return responses


def analyze_results(responses: List[dict]) -> TestResultStats:
    """Analyze test results and return statistics."""
    success_count = sum(1 for resp in responses if resp['status'] == 'success')
    error_count = sum(1 for resp in responses if resp['status'] == 'error')
    exception_count = sum(
        1 for resp in responses if resp['status'] == 'exception')
    validation_error_count = sum(
        1 for resp in responses if resp['status'] == 'validation_error')

    response_times = [resp['response_time']
                      for resp in responses if resp['status'] == 'success']

    return TestResultStats(
        total_requests=len(responses),
        successful_responses=success_count,
        error_responses=error_count,
        exceptions=exception_count,
        validation_errors=validation_error_count,
        avg_response_time=sum(response_times) /
        len(response_times) if response_times else 0,
        max_response_time=max(response_times) if response_times else 0,
        min_response_time=min(response_times) if response_times else 0,
        timestamp=datetime.now()
    )


async def main():
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    global logger
    logger = logging.getLogger(__name__)

    num_requests = 20
    num_comments = 10

    logger.info(f"Starting load test with {num_requests} requests...")

    try:
        responses = await send_multiple_requests(num_requests, num_comments)
        stats = analyze_results(responses)

        print("\nTest Results:")
        print(f"Total requests: {stats.total_requests}")
        # print(f"Successful responses: {stats.successful_responses}")
        print(f"Error responses: {stats.error_responses}")
        print(f"Exceptions: {stats.exceptions}")
        print(f"Validation errors: {stats.validation_errors}")
        print(f"Average response time: {stats.avg_response_time:.2f} seconds")
        print(f"Max response time: {stats.max_response_time:.2f} seconds")
        print(f"Min response time: {stats.min_response_time:.2f} seconds")

        # Log detailed responses for debugging
        for i, resp in enumerate(responses, 1):
            if resp['status'] != 'success':
                logger.warning(f"Request {i} failed:")
                logger.warning(f"Status: {resp['status']}")
                logger.warning(f"Details: {json.dumps(resp, indent=2)}")

    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
