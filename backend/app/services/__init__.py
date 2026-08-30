"""Service layer: business rules and transaction boundaries.

Routers call services; services call repositories. Services own ``commit`` /
``rollback`` and translate domain problems into :class:`app.api.errors.AppError`
subclasses.
"""
