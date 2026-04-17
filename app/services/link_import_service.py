from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.link_service import link_service
from app.models.models import AppLog, Site
from app.utils.time import utcnow


class LinkImportService:
    async def import_text(
        self,
        db: AsyncSession,
        *,
        site_id: int,
        text: str,
        max_lines: int = 20000,
    ) -> Dict[str, object]:
        now = utcnow()
        imported = 0
        errors: List[str] = []
        missing_count = 0
        missing_samples: List[int] = []

        site = await db.get(Site, int(site_id))
        default_target = f"https://{site.domain.strip().rstrip('/')}/" if site and site.domain else ""

        lines = (text or "").splitlines()
        if len(lines) > max_lines:
            lines = lines[:max_lines]

        for idx, line in enumerate(lines, start=1):
            raw = (line or "").strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                parts: List[str]
                if "," in raw:
                    parts = [p.strip() for p in next(csv.reader([raw]))]
                elif "\t" in raw:
                    parts = [p.strip() for p in raw.split("\t")]
                else:
                    parts = [p.strip() for p in raw.split()]

                source_url = parts[0] if len(parts) > 0 else ""
                target_url = parts[1] if len(parts) > 1 else ""
                anchor = parts[2] if len(parts) > 2 else ""
                link_type = parts[3] if len(parts) > 3 else ""
                dr_raw = parts[4] if len(parts) > 4 else ""
                domain_score: Optional[int] = None
                if dr_raw:
                    try:
                        domain_score = int(float(dr_raw))
                    except Exception:
                        domain_score = None

                if source_url and not target_url and default_target:
                    target_url = default_target

                if not source_url or not target_url:
                    errors.append(f"Строка {idx}: пустой source_url или target_url")
                    missing_count += 1
                    if len(missing_samples) < 10:
                        missing_samples.append(int(idx))
                    continue

                await link_service.upsert(
                    db,
                    site_id=site_id,
                    source_url=source_url,
                    target_url=target_url,
                    anchor=anchor or None,
                    link_type=link_type or None,
                    domain_score=domain_score,
                    source="import",
                    now=now,
                )
                imported += 1
            except Exception:
                errors.append(f"Строка {idx}: ошибка обработки")
                db.add(
                    AppLog(
                        level="ERROR",
                        category="import",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links text: processing error at line {idx}",
                        created_at=utcnow(),
                    )
                )

        if missing_count:
            samp = ",".join(str(i) for i in missing_samples)
            db.add(
                AppLog(
                    level="WARNING",
                    category="import",
                    method=None,
                    path=None,
                    status_code=None,
                    message=f"links text: missing url lines={missing_count} samples=[{samp}]",
                    created_at=utcnow(),
                )
            )

        db.add(
            AppLog(
                level="INFO",
                category="import",
                method=None,
                path=None,
                status_code=None,
                message=f"links text imported site_id={site_id} imported={imported} errors={len(errors)}",
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {"imported_count": imported, "errors": errors[:50]}

    async def import_csv(
        self,
        db: AsyncSession,
        *,
        site_id: int,
        content_bytes: bytes,
        encoding: str = "utf-8",
    ) -> Dict[str, object]:
        text = content_bytes.decode(encoding, errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        now = utcnow()

        imported = 0
        errors: List[str] = []
        missing_count = 0
        missing_samples: List[int] = []

        site = await db.get(Site, int(site_id))
        default_target = f"https://{site.domain.strip().rstrip('/')}/" if site and site.domain else ""

        for idx, row in enumerate(reader, start=2):
            try:
                source_url = (row.get("source_url") or "").strip()
                target_url = (row.get("target_url") or "").strip()
                anchor = (row.get("anchor") or "").strip() or None
                lt = (row.get("type") or row.get("link_type") or "").strip().lower() or "dofollow"
                dr_raw = (row.get("dr") or row.get("domain_score") or "").strip()
                domain_score: Optional[int] = None
                if dr_raw:
                    try:
                        domain_score = int(float(dr_raw))
                    except Exception:
                        domain_score = None

                if source_url and not target_url and default_target:
                    target_url = default_target

                if not source_url or not target_url:
                    errors.append(f"Строка {idx}: пустой source_url или target_url")
                    missing_count += 1
                    if len(missing_samples) < 10:
                        missing_samples.append(int(idx))
                    continue

                await link_service.upsert(
                    db,
                    site_id=site_id,
                    source_url=source_url,
                    target_url=target_url,
                    anchor=anchor,
                    link_type=lt,
                    domain_score=domain_score,
                    source="import",
                    now=now,
                )
                imported += 1
            except Exception:
                errors.append(f"Строка {idx}: ошибка обработки")
                db.add(
                    AppLog(
                        level="ERROR",
                        category="import",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links csv: processing error at line {idx}",
                        created_at=utcnow(),
                    )
                )

        if missing_count:
            samp = ",".join(str(i) for i in missing_samples)
            db.add(
                AppLog(
                    level="WARNING",
                    category="import",
                    method=None,
                    path=None,
                    status_code=None,
                    message=f"links csv: missing url lines={missing_count} samples=[{samp}]",
                    created_at=utcnow(),
                )
            )

        db.add(
            AppLog(
                level="INFO",
                category="import",
                method=None,
                path=None,
                status_code=None,
                message=f"links csv imported site_id={site_id} imported={imported} errors={len(errors)}",
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {"imported_count": imported, "errors": errors[:50]}


link_import_service = LinkImportService()
