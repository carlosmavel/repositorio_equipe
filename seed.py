try:
    from . import seed_demo, seed_articles
except ImportError:  # pragma: no cover - fallback for direct execution
    import seed_demo, seed_articles


def run():
    """Execute os scripts de seed de exemplo."""
    seed_demo.run()
    seed_articles.run()


if __name__ == "__main__":
    run()
