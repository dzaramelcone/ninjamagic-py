from pathlib import Path


def test_items_migration_exists():
    assert Path("migrations/003_items_inventories.sql").exists()
