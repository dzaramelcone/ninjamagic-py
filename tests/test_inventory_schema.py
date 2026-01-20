from pathlib import Path


def test_items_migration_exists():
    assert Path("migrations/003_items_inventories.sql").exists()


def test_inventory_owner_constraint_migration_exists():
    assert Path("migrations/004_inventory_owner_constraint.sql").exists()
