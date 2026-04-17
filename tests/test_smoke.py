import os
import tempfile
import unittest
import urllib.parse

from passlib.context import CryptContext


ctx = CryptContext(schemes=["pbkdf2_sha256"])

tmp_db = tempfile.NamedTemporaryFile(prefix="seo_studio_test_", suffix=".db", delete=False)
tmp_db.close()
tmp_db_path = tmp_db.name

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_db_path}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD_HASH", ctx.hash("admin"))
os.environ.setdefault("TESTING", "1")


from app.main import app  # noqa: E402
from app.core.database import engine  # noqa: E402

import httpx  # noqa: E402
import inspect  # noqa: E402
import io  # noqa: E402
import warnings  # noqa: E402
import logging  # noqa: E402

warnings.filterwarnings("ignore", message="Executing <_ThreadSafeHandle.*took .* seconds", category=Warning)
warnings.filterwarnings("ignore", message="Executing <Task pending.*took .* seconds", category=Warning)
logging.getLogger("asyncio").setLevel(logging.ERROR)


class SmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        for fn in list(getattr(app.router, "on_startup", []) or []):
            r = fn()
            if inspect.isawaitable(r):
                await r
        self.transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        for fn in list(getattr(app.router, "on_shutdown", []) or []):
            r = fn()
            if inspect.isawaitable(r):
                await r
        await engine.dispose()
        try:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)
        except Exception:
            pass

    async def test_login_sites_keywords_logs(self):
        r = await self.client.post("/api/auth/login", data={"username": "admin", "password": "admin"})
        self.assertEqual(r.status_code, 200, r.text)

        for path in ["/", "/sites", "/links", "/purchased-links", "/users", "/notes", "/keywords", "/logs", "/competitors"]:
            r = await self.client.get(path)
            self.assertEqual(r.status_code, 200, f"{path}: {r.status_code} {r.text[:200]}")

        r = await self.client.get("/api/dashboard")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/dashboard/positions-history")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/dashboard/tasks-stats")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/dashboard/errors-stats")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get("/api/sites/")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/tasks")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/content-plans")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/tasks/?status=todo&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/tasks/?q=%D0%90%D1%83%D0%B4%D0%B8%D1%82&sort=priority_desc&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/content-plans/?status=idea&limit=10")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.post("/api/sites/", json={"domain": "example.com"})
        self.assertEqual(r.status_code, 201, r.text)
        site = r.json()
        self.assertIn("id", site)

        r = await self.client.post(f"/api/sites/{site['id']}/scan")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("task_id", r.json())
        r = await self.client.get(f"/api/sites/{site['id']}/scan-history")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(f"/api/sites/{site['id']}/scan-history/clear?confirm=DELETE")
        self.assertIn(r.status_code, (200, 403), r.text)
        r = await self.client.post(f"/api/sites/{site['id']}/robots-check")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(f"/api/sites/{site['id']}/sitemap-check")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(f"/api/sites/{site['id']}/auto-tasks/run")
        self.assertIn(r.status_code, (200, 403), r.text)
        r = await self.client.post(f"/api/sites/{site['id']}/tech-audit")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("task_id", r.json())
        r = await self.client.post("/api/sites/scan-all")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post("/api/scans/cleanup?hours=1")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.post("/api/keywords", json={"site_id": site["id"], "keyword": "test keyword", "position": 10, "url": "https://example.com/", "frequency": 100})
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get(f"/api/keywords?site_id={site['id']}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(isinstance(r.json(), list))

        r = await self.client.get(f"/api/keywords/history?site_id={site['id']}&days=30")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get(f"/api/keywords/cannibalization?site_id={site['id']}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("items", r.json())
        r = await self.client.get(f"/api/keywords/changes?site_id={site['id']}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("items", r.json())

        r = await self.client.get("/api/keywords/suggest?query=seo%20panel&engines=google,yandex,bing,ddg&lang=ru&mode=expanded&max_variants=10&max_per_engine=10")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("items", r.json())

        csv_bytes = io.BytesIO(b"keyword,position,url,frequency\nk1,10,https://example.com/a,100\nk2,3,https://example.com/b,200\n")
        files = {"file": ("keywords.csv", csv_bytes, "text/csv")}
        r = await self.client.post(f"/api/keywords/import-csv?site_id={site['id']}", files=files)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("imported", r.json())

        r = await self.client.get("/api/logs?hours=24&limit=50")
        self.assertEqual(r.status_code, 200, r.text)
        logs24 = r.json()
        self.assertTrue(isinstance(logs24, list))
        self.assertGreaterEqual(len(logs24), 1)

        r = await self.client.get("/api/dashboard/keyword-deltas?limit=5")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("items", r.json())

        r = await self.client.get("/api/dashboard/recent-errors?limit=5")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("items", r.json())

        r = await self.client.get("/api/dashboard/ip")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("ok"))
        r = await self.client.get("/api/dashboard/ip-history?limit=5")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("ok"))
        r = await self.client.get("/api/dashboard/system")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("ok"))

        r = await self.client.get(f"/api/dashboard/positions-history?site_id={site['id']}")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/dashboard/tasks-stats?site_id={site['id']}")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/dashboard/keyword-deltas?site_id={site['id']}&limit=5")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get(f"/api/sites/{site['id']}/metric-history?metric_type=robots&limit=50")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/sites/{site['id']}/metric-history?metric_type=sitemap&limit=50")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/sites/{site['id']}/metric-history?metric_type=tech_audit&limit=50")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.post(f"/api/links/analyze?site_id={site['id']}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("task_id", r.json())
        r = await self.client.post(f"/api/links/refresh?site_id={site['id']}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("task_id", r.json())

        links_csv = io.BytesIO(
            b"source_url,target_url,anchor,type\nhttps://donor.com/a,https://example.com/,brand,dofollow\nhttps://donor.com/b,https://example.com/about,about,nofollow\n"
        )
        r = await self.client.post(f"/api/links/import-csv?site_id={site['id']}", files={"file": ("links.csv", links_csv, "text/csv")})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(
            f"/api/links/import-text?site_id={site['id']}",
            json={"text": "https://donor.com/c, https://example.com/contact, contact, dofollow, 42\n"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(
            f"/api/links/add?site_id={site['id']}",
            json={"source_url": "https://donor.com/d", "target_url": "https://example.com/", "anchor": "brand", "link_type": "nofollow", "domain_score": 10},
        )
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.post(
            f"/api/purchased-links/add?site_id={site['id']}",
            json={"source_url": "https://donor.com/p1", "target_url": "https://example.com/", "anchor": "buy", "link_type": "dofollow", "domain_score": 55},
        )
        self.assertEqual(r.status_code, 200, r.text)
        pid = int(r.json().get("id"))
        r = await self.client.post(f"/api/purchased-links/monitor?site_id={site['id']}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/purchased-links/history?backlink_id={pid}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(isinstance(r.json().get("items"), list))
        r = await self.client.post(f"/api/links/clear?site_id={site['id']}&mode=import&confirm=DELETE")
        self.assertIn(r.status_code, (200, 403), r.text)


        r = await self.client.get(f"/api/links?site_id={site['id']}&limit=50")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(isinstance(r.json(), list))

        r = await self.client.get(f"/api/links/stats?site_id={site['id']}&days=30")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/links/anchors?site_id={site['id']}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/links/ahrefs-history?site_id={site['id']}&limit=50")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/links/top-pages?site_id={site['id']}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/links/broken?site_id={site['id']}&limit=10")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/links/anchor-suggestions?site_id={site['id']}")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get(f"/api/links/last-analyzed?site_id={site['id']}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("last_analyzed_at", r.json())

        r = await self.client.get("/api/logs?level=ERROR&hours=1&limit=50")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get("/api/integrations")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(f"/api/integrations/{site['id']}/ahrefs-save", json={"enabled": True, "api_key": "test"})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/integrations/{site['id']}/ahrefs")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(f"/api/links/refresh-ahrefs?site_id={site['id']}&limit=20")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.post("/api/notes", json={"title": "n1", "content": "c", "status": "todo", "color": "gray"})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/notes")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get(f"/api/recommendations/{site['id']}")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get("/api/notifications/recent")
        self.assertEqual(r.status_code, 200, r.text)
        notif = r.json()
        self.assertTrue("items" in notif or isinstance(notif, list))

        r = await self.client.post("/api/ai/meta", json={"content": "hello world", "max_length": 160})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post("/api/ai/keywords", json={"text": "alpha beta beta gamma"})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post("/api/ai/title-check", json={"title": "a" * 80})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post("/api/seo/audit", json={"url": "example.com", "ua": None, "custom_ua": None})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post(
            "/api/seo/deep-audit",
            json={"url": "example.com", "ua": None, "custom_ua": None, "suggest_mode": "expanded", "suggest_variants": 10, "target_keyword": "test keyword"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        payload = r.json()
        self.assertIn("spam_score", payload)
        self.assertIn("target_keyword_stats", payload)
        final_url = payload.get("final_url") or payload.get("url")
        self.assertTrue(final_url)
        r = await self.client.get(f"/api/seo/deep-audit/history?url={urllib.parse.quote(str(final_url))}&limit=5")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("items", r.json())
        r = await self.client.get(f"/api/seo/deep-audit/diff?url={urllib.parse.quote(str(final_url))}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("diff", r.json())
        r = await self.client.post("/api/seo/deep-audit/create-tasks", json={"url": str(final_url)})
        self.assertIn(r.status_code, (200, 403), r.text)
        if r.status_code == 200:
            task_ids = r.json().get("task_ids") or []
            if task_ids:
                r0 = await self.client.get(f"/api/tasks/{int(task_ids[0])}")
                self.assertEqual(r0.status_code, 200, r0.text)
                report_id = r0.json().get("deep_audit_report_id")
                if report_id:
                    r1 = await self.client.get(f"/api/seo/deep-audit/report/{int(report_id)}")
                    self.assertEqual(r1.status_code, 200, r1.text)
                r2 = await self.client.patch(f"/api/tasks/{int(task_ids[0])}", json={"status": "in_progress"})
                self.assertEqual(r2.status_code, 200, r2.text)
        r = await self.client.post("/api/seo/meta", json={"content": "Текст для meta description", "max_length": 160})
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get("/health")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.get("/api/competitors/analyze?domain=example.com")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("ok"))
        r = await self.client.post("/api/competitors/saved", json={"domain": "example.com", "site_id": 1})
        self.assertIn(r.status_code, (200, 403), r.text)
        r = await self.client.get("/api/competitors/saved")
        self.assertEqual(r.status_code, 200, r.text)
        items = r.json().get("items") or []
        if items:
            cid = int(items[0]["id"])
            r = await self.client.post(f"/api/competitors/saved/{cid}/refresh?site_id=1")
            self.assertEqual(r.status_code, 200, r.text)
            r = await self.client.get(f"/api/competitors/saved/{cid}/history?limit=5")
            self.assertEqual(r.status_code, 200, r.text)
        csv_bytes = io.BytesIO(b"source_url,target_url,anchor,type,dr\nhttps://donor.example/a,https://example.com/,test,dofollow,55\n")
        files = {"file": ("c.csv", csv_bytes, "text/csv")}
        r = await self.client.post("/api/competitors/backlinks/import?domain=example.com", files=files)
        self.assertIn(r.status_code, (200, 403), r.text)
        r = await self.client.get("/api/competitors/backlinks/stats?domain=example.com&limit=5")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/competitors/backlinks/donor?domain=example.com&donor=donor.example&limit=50")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get("/api/competitors/backlinks/gap/export?domain=example.com&site_id=1")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post("/api/competitors/backlinks/gap/create-tasks?domain=example.com&site_id=1&limit=5")
        self.assertIn(r.status_code, (200, 403), r.text)
        r = await self.client.post("/api/competitors/backlinks/donor/create-task?domain=example.com&site_id=1&donor=donor.example")
        self.assertIn(r.status_code, (200, 403), r.text)

        r = await self.client.get(f"/api/sites/tasks/{site['id']}")
        self.assertIn(r.status_code, (200, 404))

        r = await self.client.get(f"/api/domain-analysis/{site['domain']}")
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.get(f"/api/domain-analysis/{site['domain']}/internal-links")
        self.assertEqual(r.status_code, 200, r.text)

        r = await self.client.post("/api/logs/cleanup?period=1h")
        self.assertEqual(r.status_code, 200, r.text)


if __name__ == "__main__":
    unittest.main()
