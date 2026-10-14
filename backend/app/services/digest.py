"""Digest generation service"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import feedparser
from sqlalchemy.orm import Session

from app.db.models import Article, Digest, Source
from app.integrations.groq import GroqClient
from app.services.source import SourceService

logger = logging.getLogger(__name__)


class DigestService:
    @staticmethod
    def fetch_articles_from_sources(
        db: Session, source_ids: list[int], max_articles: int = 20, max_age_hours: int = 24
    ) -> list[Article]:
        """Fetch articles from specified sources"""
        articles = []
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

        for source_id in source_ids:
            try:
                source = db.query(Source).filter(Source.id == source_id).first()
                if not source:
                    continue

                feed_result = SourceService.test_feed(source.url)
                if not feed_result.valid:
                    logger.warning(f"Feed {source.name} is invalid: {feed_result.error}")
                    continue

                # Parse feed and create articles
                feed = feedparser.parse(source.url)

                for entry in feed.entries[:15]:
                    # Skip articles without publication date
                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    if not published:
                        logger.warning(
                            "Article from %s has no publication date, skipping: %s",
                            source.name,
                            entry.get("title", "Unknown")[:50],
                        )
                        continue

                    pub_dt = datetime(*published[:6]).replace(tzinfo=UTC)
                    if pub_dt < cutoff:
                        continue

                    # Check if article already exists
                    external_id = entry.get("id", entry.get("link", ""))
                    url = entry.get("link", "")

                    existing = (
                        db.query(Article)
                        .filter((Article.url == url) | (Article.external_id == external_id))
                        .first()
                    )

                    if existing:
                        articles.append(existing)
                        continue

                    # Create new article
                    article = Article(
                        source_id=source.id,
                        external_id=external_id,
                        title=entry.get("title", "No Title")[:500],
                        summary=entry.get("summary", "")[:1000],
                        url=url,
                        published_at=pub_dt,
                    )
                    db.add(article)
                    articles.append(article)

                db.commit()

            except Exception as e:
                logger.error(f"Error fetching from source {source_id}: {e}")
                continue

        logger.info(f"Fetched {len(articles)} articles from {len(source_ids)} sources")
        return articles[:max_articles]

    @staticmethod
    def deduplicate_articles(articles: list[Article]) -> list[Article]:
        """Remove duplicate articles based on title similarity"""
        if not articles:
            return []

        unique = []
        seen_hashes = set()
        seen_titles: list[set[str]] = []

        for article in articles:
            # Quick hash-based deduplication
            title_hash = hashlib.md5(f"{article.title}:{article.source_id}".encode()).hexdigest()
            if title_hash in seen_hashes:
                continue

            # Word overlap deduplication
            title_words = set(article.title.lower().split())
            is_duplicate = False

            for seen in seen_titles:
                overlap = len(title_words & seen) / max(len(title_words | seen), 1)
                if overlap > 0.7:  # Increased threshold from 0.6 for better accuracy
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(article)
                seen_hashes.add(title_hash)
                seen_titles.append(title_words)

        removed = len(articles) - len(unique)
        if removed > 0:
            logger.info(f"Removed {removed} duplicates")

        return unique

    @staticmethod
    def generate_digest(
        articles: list[Article],
        profile: str = "Technology and AI news",
        language: str = "English",
        max_articles: int = 5,
        schedule_name: str | None = None,
        source_names: list[str] | None = None,
    ) -> str:
        """Generate digest using Groq API"""
        if not articles:
            return "No articles available to generate digest."

        try:
            groq = GroqClient()
        except ValueError as e:
            logger.error(f"Groq not configured: {e}")
            return DigestService._fallback_digest(
                articles, schedule_name=schedule_name, source_names=source_names
            )

        # Format articles for Groq
        articles_text = "\n\n".join(
            f"[{article.source.name}] {article.title}\n{article.summary}\nURL: <{article.url}>"
            for article in articles
        )

        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # Build sources list for header
        sources_text = ""
        if source_names:
            sources_text = f"Durchsuchte Quellen: {', '.join(source_names)}\n"

        schedule_text = ""
        if schedule_name:
            schedule_text = f"Schedule: {schedule_name}\n"

        prompt = f"""You are a personal news curator. Today is {today}.

My Interest Profile: {profile}

{schedule_text}{sources_text}
Here are today's articles from various sources:

{articles_text}

---
TASK:
1. Select the {max_articles} most relevant articles for my profile
2. Summarize each article in 2-3 sentences in {language}
3. Explain in one sentence why the article is relevant to me
4. Include the original link

FORMAT:
Create a well-structured daily digest.
- Begin with: "Hallo, ich bin Ihr persönlicher Nachrichtenkurator. Heute ist der {today}."
- If schedule name exists, add: "Das ist der Digest für die Schedule '{schedule_name}'."
- If sources exist, add: "Durchsucht wurden folgende Quellen: {', '.join(source_names or [])}"
- Add the topic: "Gesucht nach Themen in: {profile}"
- Use **bold** for article titles.
- Use --- as separator between articles.
- End with a brief summary of the most important trend today."""

        try:
            digest = groq.create_completion(
                messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=2048
            )
            return digest
        except Exception as e:
            logger.error(f"Error generating digest with Groq: {e}")
            return DigestService._fallback_digest(articles)

    @staticmethod
    def _fallback_digest(
        articles: list[Article], schedule_name: str | None = None, source_names: list[str] | None = None
    ) -> str:
        """Fallback digest generation when Groq is unavailable"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        lines = [f"Hallo, ich bin Ihr persönlicher Nachrichtenkurator. Heute ist der {today}.\n"]

        if schedule_name:
            lines.append(f"Das ist der Digest für die Schedule '{schedule_name}'.")

        if source_names:
            lines.append(f"Durchsuchte Quellen: {', '.join(source_names)}")

        lines.append("=" * 50)

        if not articles:
            lines.append("\n⚠️ Keine Artikel verfügbar für diesen Digest.")
            lines.append("\nBitte überprüfen Sie, dass Ihre Quellen aktiv sind und aktuelle Inhalte haben.")
        else:
            for article in articles[:5]:
                lines.append(f"\n**{article.title}**")
                lines.append(f"Quelle: {article.source.name}")
                if article.summary:
                    lines.append(article.summary[:300])
                else:
                    lines.append("(Keine Zusammenfassung verfügbar)")
                if article.url:
                    lines.append(f"Mehr lesen: {article.url}")
                lines.append("---")

        digest_text = "\n".join(lines)
        return digest_text if digest_text.strip() else "Daily News Digest Generated"

    @staticmethod
    def save_digest(db: Session, schedule_id: int, content: str, content_format: str = "markdown") -> Digest:
        """Save generated digest to database

        Args:
            content_format: "text", "markdown", or "html"
                - text/markdown stored in content_text
                - html stored in content_html
        """
        digest = Digest(
            schedule_id=schedule_id,
            content_text=content if content_format != "html" else None,
            content_html=content if content_format == "html" else None,
            status="generated",
        )
        db.add(digest)
        db.commit()
        db.refresh(digest)
        return digest
