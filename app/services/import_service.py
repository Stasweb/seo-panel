import csv
import io
from typing import List, Dict, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import SEOPosition
from app.schemas.schemas import SEOPositionCreate

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
        reader = csv.DictReader(f)
        
        imported_count = 0
        for row in reader:
            try:
                # Map GSC columns (adjust based on GSC export format)
                keyword = row.get('Top queries') or row.get('Query')
                position_str = row.get('Position')
                
                if keyword and position_str:
                    position = int(float(position_str))
                    
                    new_pos = SEOPosition(
                        site_id=site_id,
                        keyword=keyword,
                        position=position,
                        check_date=date.today(),
                        source="gsc"
                    )
                    db.add(new_pos)
                    imported_count += 1
            except (ValueError, KeyError) as e:
                continue
                
        await db.commit()
        return imported_count

    async def import_generic_csv(self, db: AsyncSession, site_id: int, csv_content: str) -> int:
        """
        Generic CSV import (Keyword, Position).
        """
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        
        imported_count = 0
        for row in reader:
            # Try common column names
            keyword = row.get('keyword') or row.get('Keyword') or row.get('query')
            position = row.get('position') or row.get('Position')
            
            if keyword and position:
                try:
                    new_pos = SEOPosition(
                        site_id=site_id,
                        keyword=keyword,
                        position=int(float(position)),
                        check_date=date.today(),
                        source="manual"
                    )
                    db.add(new_pos)
                    imported_count += 1
                except ValueError:
                    continue
                    
        await db.commit()
        return imported_count

import_service = ImportService()
