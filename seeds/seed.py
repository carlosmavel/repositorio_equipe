import os
import sys

# Garante que o diretório raiz do projeto esteja no PYTHONPATH quando executado diretamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from . import seed_demonstration, seed_processos
except ImportError:  # pragma: no cover - fallback para execução direta
    import seed_demonstration
    import seed_processos


def run():
    """Execute os scripts de seed de exemplo."""
    seed_demonstration.run()
    try:
        seed_processos.run()
    except Exception as e:
        print(f"Seed processos falhou: {e}")



if __name__ == "__main__":
    run()
