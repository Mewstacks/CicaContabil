from __future__ import annotations


class SharedKnowledgeRouter:
    """Hard database boundary: shared corpus has no relations to tenant tables."""

    route_app_label = "knowledge"

    def db_for_read(self, model, **hints):  # type: ignore[no-untyped-def]
        return "knowledge" if model._meta.app_label == self.route_app_label else None

    def db_for_write(self, model, **hints):  # type: ignore[no-untyped-def]
        return "knowledge" if model._meta.app_label == self.route_app_label else None

    def allow_relation(self, obj1, obj2, **hints):  # type: ignore[no-untyped-def]
        in_shared_one = obj1._meta.app_label == self.route_app_label
        in_shared_two = obj2._meta.app_label == self.route_app_label
        if in_shared_one or in_shared_two:
            return in_shared_one and in_shared_two
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):  # type: ignore[no-untyped-def]
        if app_label == self.route_app_label:
            return db == "knowledge"
        if db == "knowledge":
            return False
        return None
