"""
URL preview utility functions
"""
import re
import aiohttp

async def get_url_preview(url):
    """Extract title and description from URL for preview"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Extract title
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else "No title"
                    
                    # Extract description from meta tags
                    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                    if not desc_match:
                        desc_match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                    
                    description = desc_match.group(1).strip() if desc_match else "No description"
                    
                    return {
                        "title": title[:100],  # Limit length
                        "description": description[:200],
                        "url": url
                    }
    except Exception:
        pass
    
    return {
        "title": "Link Preview",
        "description": "Unable to fetch preview",
        "url": url
    }
