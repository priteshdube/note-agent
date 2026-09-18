import httpx
from models import LectureNotes
from config import settings

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

async def get_notion_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=NOTION_BASE_URL,
        headers={
            "Authorization": f"Bearer {settings.notion_token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )

async def find_or_create_topic_page(topic_name: str) -> str:
    """
    Find a page under the root page with the given topic_name, or create it.
    Returns the page ID.
    """
    async with await get_notion_client() as client:
        # First, try to find a page with the given title under the root page
        query_data = {
            "filter": {
                "property": "title",
                "title": {
                    "equals": topic_name
                }
            }
        }
        # We'll search in the root page's children? Actually, we can use the search API to search for a page by title.
        # But we want to limit to the root page's children. We can use the search API with a filter on the parent.
        # Alternatively, we can list the children of the root page and look for a page with the title.
        # Let's do the latter for simplicity (since the root page might not have too many children).
        resp = await client.get(
            f"/blocks/{settings.notion_root_page_id}/children",
            params={"page_size": 100}  # adjust if needed
        )
        resp.raise_for_status()
        data = resp.json()
        for block in data.get("results", []):
            if block.get("type") == "child_page" and block.get("child_page", {}).get("title") == topic_name:
                return block["id"]

        # If not found, create a new child page under the root page
        create_data = {
            "parent": {"page_id": settings.notion_root_page_id},
            "properties": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": topic_name
                        }
                    }
                ]
            }
        }
        resp = await client.post("/pages", json=create_data)
        resp.raise_for_status()
        data = resp.json()
        return data["id"]

async def create_lecture_page(topic_page_id: str, notes: LectureNotes) -> str:
    """
    Create a lecture sub-page under the given topic page.
    Returns the created page ID.
    """
    # We'll build the children blocks for the lecture page from the notes.
    children = []

    # Add title as a heading
    children.append({
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": notes.title}}]
        }
    })

    for section in notes.sections:
        # Add section heading
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": section.heading}}]
            }
        })
        # Add bullets as a bulleted list item for each bullet
        for bullet in section.bullets:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": bullet}}]
                }
            })

    # Add key terms as a toggle list or a bulleted list? Let's use a bulleted list under a heading.
    if notes.key_terms:
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Key Terms"}}]
            }
        })
        for kt in notes.key_terms:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"{kt.term}: {kt.definition}"}}]
                }
            })

    # Notion API allows up to 100 blocks per call. If we exceed, we need to do multiple calls.
    # We'll split the children into chunks of 100.
    chunk_size = 100
    chunks = [children[i:i + chunk_size] for i in range(0, len(children), chunk_size)]

    async with await get_notion_client() as client:
        # Create the page with the first chunk of children (if any)
        if chunks:
            first_chunk = chunks[0]
            create_data = {
                "parent": {"page_id": topic_page_id},
                "properties": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": notes.title
                            }
                        }
                    ]
                },
                "children": first_chunk
            }
        else:
            create_data = {
                "parent": {"page_id": topic_page_id},
                "properties": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": notes.title
                            }
                        }
                    ]
                }
            }
        resp = await client.post("/pages", json=create_data)
        resp.raise_for_status()
        data = resp.json()
        lecture_page_id = data["id"]

        # Now, append the remaining children in chunks of 100
        for chunk in chunks[1:]:
            await client.patch(
                f"/blocks/{lecture_page_id}/children",
                json={"children": chunk}
            )

        return lecture_page_id