"""
Ekantipur scraper skeleton (async Playwright).

Selectors, URLs, and output shape: see notes.md

"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, Locator, Page, async_playwright

# --- URLs (from notes.md) ---
ENTERTAINMENT_URL = "https://ekantipur.com/entertainment"

# --- Selectors (from notes.md) — use with page.locator(...) ---
# Entertainment: category once for all cards
SEL_CATEGORY = ".category-name p a"
# Entertainment: article cards
SEL_CARD = ".category-inner-wrapper"
SEL_CARD_TITLE = ".category-description h2 a"
SEL_CARD_IMAGE = ".category-image a figure img"  # prefer data-src, fallback src
SEL_CARD_AUTHOR = ".author-name p a"  # multiple <a> possible per card


OUTPUT_PATH = Path(__file__).resolve().parent / "output.json"
TOP_N_ENTERTAINMENT = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_output_skeleton() -> dict[str, Any]:
    """Shape expected by notes.md (fill lists/dicts in scrapers)."""
    return {
        "entertainment_news": [],
        "cartoon_of_the_day": {
            "title": None,
            "image_url": None,
            "author": None,
        },
    }


async def get_page_category(page: Page) -> str | None:
    """
    Page-level category: .category-name p a (extract once for all articles).
    Return None if missing or on error.
    """
    try:
        locator = page.locator(SEL_CATEGORY).first
        if await locator.count()>0:
            return (await locator.inner_text()).strip() or None
        return None
    except Exception as exc:  # noqa: BLE001 — skeleton: log and continue
        logger.warning("get_page_category failed: %s", exc)
        return None


async def extract_entertainment_card(
    card_locator: Locator,
    page_category: str | None,
) -> dict[str, Any] | None:
    """
    One article dict: title, image_url, category, author.

    - Use card_locator.locator(...) for nested fields (not query_selector).
    - Image: lazy load — check data-src then src; consider scroll/wait before read.
    - Authors: multiple .author-name p a — join (e.g. comma) or first-only per your spec.
    - Return None if the card is unusable; never raise.
    """
    try:
        # Title
        title_el = card_locator.locator(SEL_CARD_TITLE)
        if await title_el.count() == 0:
            return None
        title = (await title_el.inner_text()).strip()
  

        #image
        image_el = card_locator.locator(SEL_CARD_IMAGE)
        if await image_el.count() == 0:
            return None
        image = await image_el.get_attribute("src") or await image_el.get_attribute("data-src")
        print(f"Image: {image}")

  
      # Author might have 0, 1, or 2 matches
        author_el = card_locator.locator(SEL_CARD_AUTHOR)
        if await author_el.count() > 0:
            all_authors = await author_el.all()
            author = [await a.inner_text() for a in all_authors]
        else:
            author = None

        return {
            "title": title,
            "image_url": image,
            "category": page_category,
            "author": author,
        }
    except Exception as exc:
        logger.warning("extract_entertainment_card failed: %s", exc)
        return None


async def scrape_entertainment_articles(page: Page, limit: int = TOP_N_ENTERTAINMENT) -> list[dict[str, Any]]:
    """
    Top N articles from ENTERTAINMENT_URL.

    - Navigate, wait for network/content as needed.
    - Scroll if cards/images lazy-load.
    - Collect up to `limit` valid cards from .category-inner-wrapper.
    """
    articles: list[dict[str, Any]] = []
    try:
        await page.goto(ENTERTAINMENT_URL, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        page_category = await get_page_category(page)
        cards = page.locator(SEL_CARD)
        count = await cards.count()
        for i in range(min(count, limit)):
            try:
                card = cards.nth(i)
                item = await extract_entertainment_card(card, page_category)
                if item:
                    articles.append(item)
            except Exception as exc:
                logger.warning("entertainment card %s skipped: %s", i, exc)
    except Exception as exc:
        logger.exception("scrape_entertainment_articles failed: %s", exc)
    return articles



async def scrape_cartoon_of_the_day(page: Page) -> dict[str, Any] | None:
    """
    From cartoon page (notes.md): first .cartoon-wrapper = today's cartoon.

    - Title: img alt inside .cartoon-image figure.
    - image_url: img data-src or src inside .cartoon-image figure (lazy).
    - Author: .cartoon-description p text; split on \" - \" to derive author name.
    """
    cartoon_url = "https://ekantipur.com/cartoon"
    sel_wrapper = ".cartoon-wrapper"
    sel_figure_img = ".cartoon-image figure img"
    sel_description = ".cartoon-description p"

    try:
        await page.goto(cartoon_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        wrapper = page.locator(sel_wrapper).first
        if await wrapper.count() == 0:
            return None

        try:
            await wrapper.scroll_into_view_if_needed()
        except Exception as exc:
            logger.warning("cartoon wrapper scroll_into_view_if_needed: %s", exc)

        img = wrapper.locator(sel_figure_img).first
        title: str | None = None
        image_url: str | None = None
        if await img.count() > 0:
            try:
                title_raw = await img.get_attribute("alt")
                title = (title_raw or "").strip() or None
            except Exception as exc:
                logger.warning("cartoon img alt: %s", exc)
            try:
                image_url = await img.get_attribute("data-src") or await img.get_attribute("src")
                if image_url is not None:
                    image_url = image_url.strip() or None
            except Exception as exc:
                logger.warning("cartoon img src/data-src: %s", exc)

        author: str | None = None
        desc = wrapper.locator(sel_description).first
        if await desc.count() > 0:
            try:
                desc_text = (await desc.inner_text()).strip()
                if desc_text:
                    if " - " in desc_text:
                       author_part = desc_text.rsplit(" - ", 1)[-1].strip()
                       author = author_part if author_part else None
                    else:
                        author = None
            except Exception as exc:
                logger.warning("cartoon description text: %s", exc)

        return {
            "title": title,
            "image_url": image_url,
            "author": author,
        }
    except Exception as exc:
        logger.warning("scrape_cartoon_of_the_day failed: %s", exc)
        return None


def save_output(data: dict[str, Any], path: Path = OUTPUT_PATH) -> None:
    """Write JSON with Nepali text preserved (ensure_ascii=False)."""
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Wrote %s", path)
    except Exception as exc:
        logger.exception("save_output failed: %s", exc)


async def run_scraper(browser: Browser) -> dict[str, Any]:
    """Open a context/page, run both flows, assemble output."""
    output = build_output_skeleton()
    context = await browser.new_context(
        locale="ne-NP",
        # optional: user_agent if the site blocks headless patterns
    )
    try:
        page = await context.new_page()
        output["entertainment_news"] = await scrape_entertainment_articles(page)
        cartoon = await scrape_cartoon_of_the_day(page)
        if cartoon is not None:
            output["cartoon_of_the_day"] = cartoon
    finally:
        await context.close()
    return output


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        try:
            data = await run_scraper(browser)
            save_output(data)
        finally:
            await browser.close()



if __name__ == "__main__":
    asyncio.run(main())
