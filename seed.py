from seed_funcoes import run as seed_funcoes
from seed_organizacao import run as seed_organizacao
from seed_users import run as seed_users
from seed_artigos import run as seed_artigos


def run():
    seed_funcoes()
    seed_organizacao()
    seed_users()
    seed_artigos()


if __name__ == "__main__":
    run()
