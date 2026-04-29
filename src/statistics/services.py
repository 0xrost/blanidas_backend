import datetime
import math
from io import BytesIO
from typing import Any

import pandas
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette.responses import StreamingResponse

from src.equipment.schemas import Equipment, EquipmentStatus
from src.equipment_category.schemas import EquipmentCategory
from src.equipment_model.schemas import EquipmentModel
from src.failure_type.schemas import FailureType, FailureTypeRepairRequest
from src.institution.schemas import Institution
from src.manufacturer.schemas import Manufacturer
from src.repair_request.schemas import RepairRequest, UsedSparePart, Urgency, RepairRequestStatus
from src.spare_part.schemas import SparePart, StockStatus, Location
from src.spare_part_category.schemas import SparePartCategory
from src.statistics.models import StatisticsResponse, EquipmentBreakdownItem, CategoricalChartDataItem, TimelinePoint, StatisticsFilters

class StatisticsServices:
    @staticmethod
    async def get_institution(database: AsyncSession, data: StatisticsFilters, limit: int) -> list[CategoricalChartDataItem]:
        query = (
            select(Institution.name, func.count(RepairRequest.id).label("breakdown_count"))
            .select_from(Institution)
            .join(Equipment, Equipment.institution_id == Institution.id)
            .join(RepairRequest, RepairRequest.equipment_id == Equipment.id)
        )

        from_date = func.date_trunc(data.time_frame.step, data.time_frame.from_date)
        to_date = func.date_trunc(data.time_frame.step, data.time_frame.to_date)
        filters = [func.date_trunc(data.time_frame.step, RepairRequest.created_at).between(from_date, to_date)]

        if data.institution_ids:
            filters.append(Institution.id.in_(data.institution_ids))

        if data.equipment_model_ids:
            query = query.join(EquipmentModel, Equipment.equipment_model_id == EquipmentModel.id)
            filters.append(EquipmentModel.id.in_(data.equipment_model_ids))

        if data.failure_type_ids:
            query = query.join(FailureTypeRepairRequest, RepairRequest.id == FailureTypeRepairRequest.repair_request_id)
            query = query.join(FailureType, FailureTypeRepairRequest.failure_type_id == FailureType.id)
            filters.append(FailureType.id.in_(data.failure_type_ids))

        query = query.where(*filters)
        query = query.group_by(Institution.id).order_by(desc("breakdown_count")).limit(limit)
        query_institution = await database.execute(query)

        return [CategoricalChartDataItem(label=row[0], value=row[1]) for row in query_institution.all()]

    @staticmethod
    async def get_failure_types(database: AsyncSession, data: StatisticsFilters, limit: int) -> list[CategoricalChartDataItem]:
        query = (
            select(FailureType.name, func.count(RepairRequest.id).label("count"))
            .select_from(FailureType)
            .join(FailureTypeRepairRequest, FailureType.id == FailureTypeRepairRequest.failure_type_id)
            .join(RepairRequest, FailureTypeRepairRequest.repair_request_id == RepairRequest.id)
        )

        from_date = func.date_trunc(data.time_frame.step, data.time_frame.from_date)
        to_date = func.date_trunc(data.time_frame.step, data.time_frame.to_date)
        filters = [func.date_trunc(data.time_frame.step, RepairRequest.created_at).between(from_date, to_date)]

        if data.institution_ids or data.equipment_model_ids:
            query = query.join(Equipment, Equipment.id == RepairRequest.equipment_id)

        if data.institution_ids:
            query = query.join(Institution, Institution.id == Equipment.institution_id)
            filters.append(Institution.id.in_(data.institution_ids))

        if data.equipment_model_ids:
            query = query.join(EquipmentModel, Equipment.equipment_model_id == EquipmentModel.id)
            filters.append(EquipmentModel.id.in_(data.equipment_model_ids))

        if data.failure_type_ids:
            filters.append(FailureType.id.in_(data.failure_type_ids))

        query = query.where(*filters)
        query = query.group_by(FailureType.id).order_by(desc("count")).limit(limit)
        query_failure_types = await database.execute(query)

        return [CategoricalChartDataItem(label=row[0], value=row[1]) for row in query_failure_types.all()]

    @staticmethod
    async def get_equipment_models(database: AsyncSession, data: StatisticsFilters, limit: int) -> list[CategoricalChartDataItem]:
        query = (
            select(EquipmentModel.name, func.count(RepairRequest.id).label("count"))
            .select_from(EquipmentModel)
            .join(Equipment, EquipmentModel.id == Equipment.equipment_model_id)
            .join(RepairRequest, Equipment.id == RepairRequest.equipment_id)
        )

        from_date = func.date_trunc(data.time_frame.step, data.time_frame.from_date)
        to_date = func.date_trunc(data.time_frame.step, data.time_frame.to_date)
        filters = [func.date_trunc(data.time_frame.step, RepairRequest.created_at).between(from_date, to_date)]

        if data.institution_ids:
            query = query.join(Institution, Institution.id == Equipment.institution_id)
            filters.append(Institution.id.in_(data.institution_ids))

        if data.equipment_model_ids:
            filters.append(EquipmentModel.id.in_(data.equipment_model_ids))

        if data.failure_type_ids:
            query = query.join(FailureTypeRepairRequest, RepairRequest.id == FailureTypeRepairRequest.repair_request_id)
            query = query.join(FailureType, FailureTypeRepairRequest.failure_type_id == FailureType.id)
            filters.append(FailureType.id.in_(data.failure_type_ids))

        query = query.where(*filters)
        query = query.group_by(EquipmentModel.id).order_by(desc("count")).limit(limit)
        query_equipment_models = await database.execute(query)

        return [CategoricalChartDataItem(label=row[0], value=row[1]) for row in query_equipment_models.all()]

    @staticmethod
    async def get_used_spare_parts(database: AsyncSession, data: StatisticsFilters, limit: int) -> list[CategoricalChartDataItem]:
        query = (
            select(SparePart.name, func.sum(UsedSparePart.quantity).label("count"))
            .select_from(SparePart)
            .join(UsedSparePart, UsedSparePart.spare_part_id == SparePart.id)
            .join(RepairRequest, UsedSparePart.repair_request_id == RepairRequest.id)
        )

        from_date = func.date_trunc(data.time_frame.step, data.time_frame.from_date)
        to_date = func.date_trunc(data.time_frame.step, data.time_frame.to_date)
        filters = [func.date_trunc(data.time_frame.step, RepairRequest.created_at).between(from_date, to_date)]

        if data.institution_ids or data.equipment_model_ids:
            query = query.join(Equipment, Equipment.id == RepairRequest.equipment_id)

        if data.institution_ids:
            query = query.join(Institution, Institution.id == Equipment.institution_id)
            filters.append(Institution.id.in_(data.institution_ids))

        if data.equipment_model_ids:
            query = query.join(EquipmentModel, Equipment.equipment_model_id == EquipmentModel.id)
            filters.append(EquipmentModel.id.in_(data.equipment_model_ids))

        if data.failure_type_ids:
            query = query.join(FailureTypeRepairRequest, RepairRequest.id == FailureTypeRepairRequest.repair_request_id)
            query = query.join(FailureType, FailureTypeRepairRequest.failure_type_id == FailureType.id)
            filters.append(FailureType.id.in_(data.failure_type_ids))

        query = query.where(*filters)
        query = query.group_by(SparePart.name).order_by(desc("count")).limit(limit)
        query_used_spare_parts = await database.execute(query)

        return [CategoricalChartDataItem(label=row[0], value=row[1]) for row in query_used_spare_parts]

    @staticmethod
    async def get_time_dynamic(database: AsyncSession, data: StatisticsFilters, limit: int) -> list[TimelinePoint]:
        time_col = func.date_trunc(data.time_frame.step, RepairRequest.created_at)
        query = (select(time_col.label("time_slot"), func.count(RepairRequest.id)))

        from_date = func.date_trunc(data.time_frame.step, data.time_frame.from_date)
        to_date = func.date_trunc(data.time_frame.step, data.time_frame.to_date)
        filters = [func.date_trunc(data.time_frame.step, RepairRequest.created_at).between(from_date, to_date)]

        if data.institution_ids or data.equipment_model_ids:
            query = query.join(Equipment, Equipment.id == RepairRequest.equipment_id)

        if data.institution_ids:
            query = query.join(Institution, Institution.id == Equipment.institution_id)
            filters.append(Institution.id.in_(data.institution_ids))

        if data.equipment_model_ids:
            query = query.join(EquipmentModel, Equipment.equipment_model_id == EquipmentModel.id)
            filters.append(EquipmentModel.id.in_(data.equipment_model_ids))

        if data.failure_type_ids:
            query = query.join(FailureTypeRepairRequest, RepairRequest.id == FailureTypeRepairRequest.repair_request_id)
            query = query.join(FailureType, FailureTypeRepairRequest.failure_type_id == FailureType.id)
            filters.append(FailureType.id.in_(data.failure_type_ids))

        query = query.where(*filters)
        query = query.group_by("time_slot").order_by("time_slot")
        query_time = await database.execute(query)

        return [TimelinePoint(period=row[0], count=row[1]) for row in query_time.all()]

    @staticmethod
    async def get_average_repair_time(database: AsyncSession, data: StatisticsFilters, limit: int) -> list[CategoricalChartDataItem]:
        query = (
            select(
                Institution.name,
                func.avg(RepairRequest.completed_at - RepairRequest.created_at).label("average")
            )
            .select_from(Institution)
            .join(Equipment, Equipment.institution_id == Institution.id)
            .join(RepairRequest, RepairRequest.equipment_id == Equipment.id)
        )

        from_date = func.date_trunc(data.time_frame.step, data.time_frame.from_date)
        to_date = func.date_trunc(data.time_frame.step, data.time_frame.to_date)

        filters = [
            func.date_trunc(data.time_frame.step, RepairRequest.created_at).between(from_date, to_date),
            RepairRequest.completed_at.is_not(None)
        ]

        if data.institution_ids:
            filters.append(Institution.id.in_(data.institution_ids))

        if data.equipment_model_ids:
            query = query.join(EquipmentModel, Equipment.equipment_model_id == EquipmentModel.id)
            filters.append(EquipmentModel.id.in_(data.equipment_model_ids))

        if data.failure_type_ids:
            query = query.join(FailureTypeRepairRequest, RepairRequest.id == FailureTypeRepairRequest.repair_request_id)
            query = query.join(FailureType, FailureTypeRepairRequest.failure_type_id == FailureType.id)
            filters.append(FailureType.id.in_(data.failure_type_ids))

        query = query.where(*filters)
        query = query.group_by(Institution.name).order_by(desc("average")).limit(limit)
        result = await database.execute(query)
        return [CategoricalChartDataItem(label=row[0], value=row[1].total_seconds()) for row in result.all()]

    @staticmethod
    async def get_equipment_breakdowns(database: AsyncSession, data: StatisticsFilters, limit: int) -> list[EquipmentBreakdownItem]:
        query = (
            select(
                Equipment.serial_number,
                EquipmentModel.name,
                Institution.name,
                func.count(RepairRequest.id).label("breakdown_count"),
                func.coalesce(func.avg(RepairRequest.completed_at - RepairRequest.created_at).label("avg_repair"), datetime.timedelta())
            )
            .select_from(Equipment)
            .join(EquipmentModel, EquipmentModel.id == Equipment.equipment_model_id)
            .join(Institution, Institution.id == Equipment.institution_id)
            .join(RepairRequest, RepairRequest.equipment_id == Equipment.id)
        )

        from_date = func.date_trunc(data.time_frame.step, data.time_frame.from_date)
        to_date = func.date_trunc(data.time_frame.step, data.time_frame.to_date)
        filters = [func.date_trunc(data.time_frame.step, RepairRequest.created_at).between(from_date, to_date)]

        if data.institution_ids:
            filters.append(Institution.id.in_(data.institution_ids))

        if data.equipment_model_ids:
            filters.append(EquipmentModel.id.in_(data.equipment_model_ids))

        if data.failure_type_ids:
            query = query.join(FailureTypeRepairRequest, RepairRequest.id == FailureTypeRepairRequest.repair_request_id)
            query = query.join(FailureType, FailureTypeRepairRequest.failure_type_id == FailureType.id)
            filters.append(FailureType.id.in_(data.failure_type_ids))

        query = query.where(*filters)
        query = query.group_by(Equipment.id, Equipment.serial_number, EquipmentModel.name, Institution.name).order_by(desc("breakdown_count")).limit(limit)
        result = await database.execute(query)
        return [
            EquipmentBreakdownItem(
                serial_number=row[0],
                model_name=row[1],
                institution_name=row[2],
                breakdown_count=row[3],
                average_repair_seconds=row[4].total_seconds(),
            )
            for row in result.all()
        ]

    @staticmethod
    async def get_dashboard(database: AsyncSession, data: StatisticsFilters, limit: int = 7) -> StatisticsResponse:
        return StatisticsResponse(
            institution_breakdown=await StatisticsServices.get_institution(database, data, limit),
            failure_types=await StatisticsServices.get_failure_types(database, data, limit),
            used_spare_parts=await StatisticsServices.get_used_spare_parts(database, data, limit),
            model_breakdowns=await StatisticsServices.get_equipment_models(database, data, limit),
            time_dynamics=await StatisticsServices.get_time_dynamic(database, data, limit),
            average_repair_time=await StatisticsServices.get_average_repair_time(database, data, limit),
            equipment_breakdowns=await StatisticsServices.get_equipment_breakdowns(database, data, limit),
            time_frame=data.time_frame,
        )

    @staticmethod
    async def generate_repair_request_sheet(database: AsyncSession) -> Any:
        query = (
            select(
                RepairRequest.id,
                RepairRequest.urgency,
                RepairRequest.created_at,
                RepairRequest.completed_at,
                RepairRequest.last_status,
                EquipmentModel.name,
                Institution.name,
                Equipment.location,
                Equipment.serial_number,
            )
            .join(Equipment, Equipment.id == RepairRequest.equipment_id)
            .join(EquipmentModel, EquipmentModel.id == Equipment.equipment_model_id)
            .join(Institution, Institution.id == Equipment.institution_id)
            .order_by(RepairRequest.created_at.desc())
        )

        repair_requests = (await database.execute(query)).all()

        status_map = {
            RepairRequestStatus.not_taken.value: "Новий",
            RepairRequestStatus.in_progress.value: "У роботі",
            RepairRequestStatus.waiting_spare_parts.value: "Очікує запчастини",
            RepairRequestStatus.finished.value: "Виконано"
        }

        return [
            {
                "ID": item[0],
                "Модель обладнання": item[5],
                "Серійний номер": item[8],
                "Заклад": item[6],
                "Локація": item[7],
                "Пріоритет": "Звичайний" if item[1] == Urgency.non_critical.value else "Критичний",
                "Статус": status_map.get(item[4], "Невідомо"),
                "Дата створення": item[2].replace(tzinfo=None),
                "Дата завершення": item[3].replace(tzinfo=None) if item[3] else None,
                "Час ремонту (сек)": (
                    math.floor((item[3] - item[2]).total_seconds())
                    if item[2] and item[3]
                    else None
                )
            } for item in repair_requests
        ]

    @staticmethod
    async def generate_spare_part_sheet(database: AsyncSession) -> Any:
        query = (
            select(
                SparePart.id,
                SparePart.name,
                SparePartCategory.name,

                SparePart.total_quantity,
                SparePart.min_quantity,
                SparePart.stock_status
            )
            .select_from(SparePart)
            .join(SparePartCategory, SparePartCategory.id == SparePart.spare_part_category_id, isouter=True)
            .order_by(SparePart.name)
        )

        items = await database.execute(query)

        stock_status_map = {
            StockStatus.in_stock.value: "Є в наявності",
            StockStatus.low_stock.value: "Мало",
            StockStatus.out_of_stock.value: "Немає",
        }

        return [{
            "ID": item[0],
            "Назва запчастини": item[1],
            "Категорія": item[2],
            "Загальна кількість": item[3],
            "Мінімальна кількість": item[4],
            "Статус складу": stock_status_map.get(item[5], "Невідомо"),
        } for item in items.all()]

    @staticmethod
    async def generate_spare_part_locations_sheet(database: AsyncSession) -> Any:
        query = (
            select(
                SparePart.name,
                Location.quantity,
                Location.restored_quantity,
                Institution.name,
            )
            .join(Location, Location.spare_part_id == SparePart.id)
            .join(Institution, Institution.id == Location.institution_id)
            .order_by(SparePart.name, Location.quantity.desc())
        )

        items = await database.execute(query)
        return [{
            "Запчастина": item[0],
            "Заклад": item[3],
            "Кількість нових": item[1],
            "Кількість відновлених": item[2],
        } for item in items.all()]

    @staticmethod
    async def generate_equipment_sheet(database: AsyncSession) -> Any:
        query = (
            select(
                Equipment.id,
                EquipmentModel.name,
                Equipment.serial_number,
                EquipmentCategory.name,
                Manufacturer.name,
                Institution.name,
                Equipment.location,
                Equipment.status,
            )
            .join(EquipmentCategory, EquipmentCategory.id == Equipment.equipment_category_id, isouter=True)
            .join(EquipmentModel, EquipmentModel.id == Equipment.equipment_model_id, isouter=True)
            .join(Manufacturer, Manufacturer.id == Equipment.manufacturer_id, isouter=True)
            .join(Institution, Institution.id == Equipment.institution_id, isouter=True)
            .order_by(EquipmentModel.name)
        )

        items = await database.execute(query)

        equipment_status_map = {
            EquipmentStatus.working.value: "Робоче",
            EquipmentStatus.under_maintenance.value: "На обслуговуванні",
            EquipmentStatus.not_working.value: "Не працює",
        }

        return [{
            "ID": item[0],
            "Модель": item[1],
            "Серійний номер": item[2],
            "Категорія": item[3],
            "Виробник": item[4],
            "Заклад": item[5],
            "Локація": item[6],
            "Статус": equipment_status_map.get(item[7], "Невідомий")
        } for item in items]

    @staticmethod
    async def export_statistics_excel(database: AsyncSession, filters: StatisticsFilters) -> StreamingResponse:
        dashboard = await StatisticsServices.get_dashboard(database, filters, limit=100)

        sheets = {
            "Заявки": await StatisticsServices.generate_repair_request_sheet(database),
            "Запчастини": await StatisticsServices.generate_spare_part_sheet(database),
            "Запчастини розміщення": await StatisticsServices.generate_spare_part_locations_sheet(database),
            "Обладнання": await StatisticsServices.generate_equipment_sheet(database),
        }

        output = BytesIO()

        with pandas.ExcelWriter(output, engine="openpyxl") as writer:
            for sheet_name, data in sheets.items():
                df = pandas.DataFrame(data)

                for col in df.columns:
                    if pandas.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].dt.tz_localize(None)

                df.to_excel(writer, sheet_name=sheet_name, index=False)

                worksheet = writer.sheets[sheet_name]
                for i, col in enumerate(df.columns):
                    max_len = max(df[col].astype(str).map(len).max(), len(col))
                    worksheet.column_dimensions[worksheet.cell(row=1, column=i + 1).column_letter].width = max_len + 2

        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=statistics.xlsx"}
        )
