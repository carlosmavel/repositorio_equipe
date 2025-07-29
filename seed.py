try:
    from . import seed_demonstration
except ImportError:  # pragma: no cover - fallback for direct execution
    import seed_demonstration


def run():
    """Execute os scripts de seed de exemplo."""
    seed_demonstration.run()



if __name__ == "__main__":
    run()
