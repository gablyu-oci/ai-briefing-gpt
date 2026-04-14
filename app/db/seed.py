"""
seed.py — Seed the database with RSS sources from config.
"""

from app.db.models import Source, get_engine, get_session, init_db
from config.sources import RSS_SOURCES


def seed_sources(session=None):
    """Insert or update all configured RSS sources into the DB."""
    own_session = session is None
    if own_session:
        engine = init_db()
        session = get_session(engine)

    try:
        for src in RSS_SOURCES:
            existing = session.query(Source).filter_by(domain=src["domain"]).first()
            if existing:
                existing.display_name = src["name"]
                existing.tier = src["tier"]
                existing.credibility_score = src["credibility_score"]
                existing.rss_url = src["url"]
                existing.crawl_freq_mins = src["crawl_freq_mins"]
            else:
                session.add(Source(
                    domain=src["domain"],
                    display_name=src["name"],
                    tier=src["tier"],
                    credibility_score=src["credibility_score"],
                    rss_url=src["url"],
                    crawl_freq_mins=src["crawl_freq_mins"],
                    active=True,
                ))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    seed_sources()
    print("Sources seeded successfully.")
