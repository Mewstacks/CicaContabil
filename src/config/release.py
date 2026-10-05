from __future__ import annotations

import os


def main() -> None:
    """Run schema migrations through direct Neon endpoints before a Fly release."""

    default_direct_url = os.environ.get("DATABASE_URL_UNPOOLED")
    knowledge_direct_url = os.environ.get("KNOWLEDGE_DATABASE_URL_UNPOOLED")
    if default_direct_url:
        os.environ["DATABASE_URL"] = default_direct_url
    if knowledge_direct_url:
        os.environ["KNOWLEDGE_DATABASE_URL"] = knowledge_direct_url
    os.environ["DB_PGBOUNCER"] = "false"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", database="default", interactive=False)
    call_command("migrate", database="knowledge", interactive=False)


if __name__ == "__main__":
    main()
