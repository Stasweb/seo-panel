import csv
import io
import logging
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import SEOPosition, AppLog
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

class ImportService:
    """
    Service for importing SEO data from CSV files.
    """
    async def import_gsc_csv(self, db: AsyncSession, site_id: int, csv_content: str) -> int:
        """
        Import Google Search Console 'Queries' CSV.
        Expects columns like 'Top queries', 'Clicks', 'Impressions', 'CTR', 'Position'.
        """
        f = io.StringIO(csv_content)
        try:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                logger.warning("CSV appears to be empty or has no headers.")
                return 0
        except Exception as e:
            logger.error(f"Failed to parse CSV: {e}")
            db.add(AppLog(level="ERROR", category="import", method=None, path=None, status_code=None, message=f"Failed to parse CSV: {e}", created_at=utcnow()))
            await db.commit()
            return 0

        imported_count = 0
        for i, row in enumerate(reader, start=1):
            try:
                # Map GSC columns (adjust based on GSC export format)
                keyword = row.get('Top queries') or row.get('Query') or row.get('query')
                position_str = row.get('Position') or row.get('position')

                if keyword and position_str:
                    try:
                        position = int(float(position_str))
                    except ValueError:
                        logger.warning(f"Invalid position '{position_str}' at line {i}. Skipping.")
                        continue

                    new_pos = SEOPosition(
                        site_id=site_id,
                        keyword=keyword.strip(),
                        position=position,
                        check_date=date.today(),
                        source="gsc"
                    )
                    db.add(new_pos)
                    imported_count += 1
            except Exception as e:
                logger.error(f"Error processing row {i}: {e}")
                db.add(AppLog(level="ERROR", category="import", method=None, path=None, status_code=None, message=f"Error processing row {i}: {e}", created_at=utcnow()))
                continue

        await db.commit()
        logger.info(f"Successfully imported {imported_count} GSC positions for site {site_id}.")
        return imported_count

    async def import_generic_csv(self, db: AsyncSession, site_id: int, csv_content: str) -> int:
        """
        Generic CSV import (Keyword, Position).
        """
        f = io.StringIO(csv_content)
        try:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                logger.warning("Generic CSV appears to be empty or has no headers.")
                return 0
        except Exception as e:
            logger.error(f"Failed to parse generic CSV: {e}")
            db.add(AppLog(level="ERROR", category="import", method=None, path=None, status_code=None, message=f"Failed to parse generic CSV: {e}", created_at=utcnow()))
            await db.commit()
            return 0

        imported_count = 0
        for i, row in enumerate(reader, start=1):
            # Try common column names
            keyword = row.get('keyword') or row.get('Keyword') or row.get('query')
            position_str = row.get('position') or row.get('Position')

            if keyword and position_str:
                try:
                    position = int(float(position_str))
                    new_pos = SEOPosition(
                        site_id=site_id,
                        keyword=keyword.strip(),
                        position=position,
                        check_date=date.today(),
                        source="manual"
                    )
                    db.add(new_pos)
                    imported_count += 1
                except ValueError:
                    logger.warning(f"Invalid position '{position_str}' at line {i}. Skipping.")
                    continue
            else:
                logger.debug(f"Row {i} missing keyword or position: {row}")

        await db.commit()
        logger.info(f"Successfully imported {imported_count} manual positions for site {site_id}.")
        return imported_count

import_service = ImportService()
