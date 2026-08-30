"""Repository layer: all SQLAlchemy access lives here.

Repositories add rows to the session and run queries. They do NOT commit —
transaction boundaries belong to the service layer.
"""
