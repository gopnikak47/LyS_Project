from app.models import ExportJob, ImportJob
from app.repositories.base import TenantRepository


class ImportRepository(TenantRepository[ImportJob]):
    model = ImportJob


class ExportRepository(TenantRepository[ExportJob]):
    model = ExportJob
