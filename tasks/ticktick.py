import httpx, logging, os
log = logging.getLogger("ticktick")

class TickTick:
    def __init__(self, base, client_id, client_secret, access, refresh):
        self.base = base.rstrip("/")
        self.client_id = client_id; self.client_secret = client_secret
        self.access = access; self.refresh = refresh

    async def _refresh(self):
        if not (self.client_id and self.client_secret and self.refresh):
            raise RuntimeError("ticktick: missing refresh credentials")
        async with httpx.AsyncClient(timeout=8.0) as cx:
            r = await cx.post(f"{self.base}/oauth/token", data={
                "grant_type":"refresh_token",
                "refresh_token": self.refresh,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            })
            r.raise_for_status()
            j = r.json()
            self.access = j["access_token"]; self.refresh = j.get("refresh_token", self.refresh)
            log.info("ticktick: token refreshed")

    async def create_task(self, title, project_id=None):
        if not self.access:
            raise RuntimeError("ticktick: missing access token")
        payload = {"title": title}
        if project_id: payload["projectId"] = project_id
        async with httpx.AsyncClient(timeout=8.0) as cx:
            r = await cx.post(f"{self.base}/open/v1/task", json=payload,
                              headers={"Authorization": f"Bearer {self.access}"})
            if r.status_code == 401:
                await self._refresh()
                r = await cx.post(f"{self.base}/open/v1/task", json=payload,
                                  headers={"Authorization": f"Bearer {self.access}"})
            r.raise_for_status()
            return r.json()