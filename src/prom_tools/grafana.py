"""
Grafana API client with async support.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from .base import BaseAsyncClient
from .models import (
    GrafanaDashboard,
    GrafanaDatasource,
    GrafanaFolder,
)
from .exceptions import GrafanaError


class GrafanaClient(BaseAsyncClient):
    """Async Grafana API client."""

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        org_id: Optional[int] = None,
        **kwargs
    ) -> None:
        super().__init__(base_url=url, **kwargs)
        self.api_key = api_key
        self.username = username
        self.password = password
        self.org_id = org_id

    def _prepare_auth_headers(self) -> Dict[str, str]:
        """Prepare authentication headers."""
        headers = {}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.username and self.password:
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        if self.org_id:
            headers["X-Grafana-Org-Id"] = str(self.org_id)

        return headers

    # Dashboard API
    async def get_dashboard(
        self,
        uid: str,
    ) -> Dict[str, Any]:
        """Get a dashboard by UID."""
        try:
            return await self._request(
                "GET",
                f"api/dashboards/uid/{uid}",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get dashboard {uid}: {str(e)}")

    async def get_dashboard_by_id(
        self,
        dashboard_id: int,
    ) -> Dict[str, Any]:
        """Get a dashboard by ID."""
        try:
            return await self._request(
                "GET",
                f"api/dashboards/id/{dashboard_id}",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get dashboard {dashboard_id}: {str(e)}")

    async def create_dashboard(
        self,
        dashboard: Dict[str, Any],
        folder_id: Optional[int] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Create a new dashboard."""
        payload = {"dashboard": dashboard}

        if folder_id is not None:
            payload["folderId"] = folder_id

        if overwrite:
            payload["overwrite"] = True

        try:
            return await self._request(
                "POST",
                "api/dashboards/db",
                json_data=payload,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to create dashboard: {str(e)}")

    async def update_dashboard(
        self,
        dashboard: Dict[str, Any],
        overwrite: bool = True,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing dashboard."""
        payload = {"dashboard": dashboard, "overwrite": overwrite}

        if message:
            payload["message"] = message

        try:
            return await self._request(
                "POST",
                "api/dashboards/db",
                json_data=payload,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to update dashboard: {str(e)}")

    async def delete_dashboard(
        self,
        uid: str,
    ) -> Dict[str, Any]:
        """Delete a dashboard by UID."""
        try:
            return await self._request(
                "DELETE",
                f"api/dashboards/uid/{uid}",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to delete dashboard {uid}: {str(e)}")

    async def search_dashboards(
        self,
        query: Optional[str] = None,
        tag: Optional[List[str]] = None,
        type: Optional[str] = None,
        dashboard_ids: Optional[List[int]] = None,
        folder_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
        page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Search for dashboards."""
        params = {}

        if query:
            params["query"] = query
        if tag:
            params["tag"] = tag
        if type:
            params["type"] = type
        if dashboard_ids:
            params["dashboardIds"] = ",".join(map(str, dashboard_ids))
        if folder_ids:
            params["folderIds"] = ",".join(map(str, folder_ids))
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page

        try:
            return await self._request(
                "GET",
                "api/search",
                params=params,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to search dashboards: {str(e)}")

    async def get_home_dashboard(self) -> Dict[str, Any]:
        """Get the home dashboard."""
        try:
            return await self._request(
                "GET",
                "api/dashboards/home",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get home dashboard: {str(e)}")

    # Folder API
    async def get_folders(self) -> List[GrafanaFolder]:
        """Get all folders."""
        try:
            response = await self._request(
                "GET",
                "api/folders",
                headers=self._prepare_auth_headers(),
            )

            folders = []
            for folder_data in response:
                folders.append(GrafanaFolder(**folder_data))
            return folders
        except Exception as e:
            raise GrafanaError(f"Failed to get folders: {str(e)}")

    async def get_folder(self, uid: str) -> GrafanaFolder:
        """Get a folder by UID."""
        try:
            response = await self._request(
                "GET",
                f"api/folders/{uid}",
                headers=self._prepare_auth_headers(),
            )
            return GrafanaFolder(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to get folder {uid}: {str(e)}")

    async def create_folder(
        self,
        title: str,
        uid: Optional[str] = None,
    ) -> GrafanaFolder:
        """Create a new folder."""
        payload = {"title": title}

        if uid:
            payload["uid"] = uid

        try:
            response = await self._request(
                "POST",
                "api/folders",
                json_data=payload,
                headers=self._prepare_auth_headers(),
            )
            return GrafanaFolder(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to create folder: {str(e)}")

    async def update_folder(
        self,
        uid: str,
        title: str,
        version: Optional[int] = None,
    ) -> GrafanaFolder:
        """Update a folder."""
        payload = {"title": title}

        if version:
            payload["version"] = version

        try:
            response = await self._request(
                "PUT",
                f"api/folders/{uid}",
                json_data=payload,
                headers=self._prepare_auth_headers(),
            )
            return GrafanaFolder(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to update folder {uid}: {str(e)}")

    async def delete_folder(self, uid: str) -> Dict[str, Any]:
        """Delete a folder."""
        try:
            return await self._request(
                "DELETE",
                f"api/folders/{uid}",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to delete folder {uid}: {str(e)}")

    async def move_dashboard(
        self,
        dashboard_uid: str,
        folder_uid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Move a dashboard to a different folder."""
        payload = {"dashboardUid": dashboard_uid}

        if folder_uid:
            payload["folderUid"] = folder_uid

        try:
            return await self._request(
                "POST",
                "api/dashboards/belongsTo",
                json_data=payload,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to move dashboard: {str(e)}")

    # Datasource API
    async def get_datasources(self) -> List[GrafanaDatasource]:
        """Get all datasources."""
        try:
            response = await self._request(
                "GET",
                "api/datasources",
                headers=self._prepare_auth_headers(),
            )

            datasources = []
            for ds_data in response:
                datasources.append(GrafanaDatasource(**ds_data))
            return datasources
        except Exception as e:
            raise GrafanaError(f"Failed to get datasources: {str(e)}")

    async def get_datasource(self, datasource_id: int) -> GrafanaDatasource:
        """Get a datasource by ID."""
        try:
            response = await self._request(
                "GET",
                f"api/datasources/{datasource_id}",
                headers=self._prepare_auth_headers(),
            )
            return GrafanaDatasource(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to get datasource {datasource_id}: {str(e)}")

    async def get_datasource_by_uid(self, uid: str) -> GrafanaDatasource:
        """Get a datasource by UID."""
        try:
            response = await self._request(
                "GET",
                f"api/datasources/uid/{uid}",
                headers=self._prepare_auth_headers(),
            )
            return GrafanaDatasource(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to get datasource {uid}: {str(e)}")

    async def get_datasource_by_name(self, name: str) -> GrafanaDatasource:
        """Get a datasource by name."""
        try:
            response = await self._request(
                "GET",
                f"api/datasources/name/{name}",
                headers=self._prepare_auth_headers(),
            )
            return GrafanaDatasource(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to get datasource {name}: {str(e)}")

    async def create_datasource(
        self,
        datasource: Dict[str, Any],
    ) -> GrafanaDatasource:
        """Create a new datasource."""
        try:
            response = await self._request(
                "POST",
                "api/datasources",
                json_data=datasource,
                headers=self._prepare_auth_headers(),
            )
            return GrafanaDatasource(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to create datasource: {str(e)}")

    async def update_datasource(
        self,
        datasource: Dict[str, Any],
        datasource_id: Optional[int] = None,
        uid: Optional[str] = None,
    ) -> GrafanaDatasource:
        """Update an existing datasource."""
        if datasource_id:
            endpoint = f"api/datasources/{datasource_id}"
        elif uid:
            endpoint = f"api/datasources/uid/{uid}"
        else:
            raise GrafanaError("Either datasource_id or uid must be provided")

        try:
            response = await self._request(
                "PUT",
                endpoint,
                json_data=datasource,
                headers=self._prepare_auth_headers(),
            )
            return GrafanaDatasource(**response)
        except Exception as e:
            raise GrafanaError(f"Failed to update datasource: {str(e)}")

    async def delete_datasource(
        self,
        datasource_id: Optional[int] = None,
        uid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete a datasource."""
        if datasource_id:
            endpoint = f"api/datasources/{datasource_id}"
        elif uid:
            endpoint = f"api/datasources/uid/{uid}"
        else:
            raise GrafanaError("Either datasource_id or uid must be provided")

        try:
            return await self._request(
                "DELETE",
                endpoint,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to delete datasource: {str(e)}")

    # Alerting API
    async def get_alerts(
        self,
        dashboard_id: Optional[int] = None,
        panel_id: Optional[int] = None,
        query: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get alerts."""
        params = {}

        if dashboard_id:
            params["dashboardId"] = dashboard_id
        if panel_id:
            params["panelId"] = panel_id
        if query:
            params["query"] = query
        if state:
            params["state"] = state
        if limit:
            params["limit"] = limit

        try:
            return await self._request(
                "GET",
                "api/alerts",
                params=params,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get alerts: {str(e)}")

    async def pause_alert(
        self,
        alert_id: str,
        paused: bool = True,
    ) -> Dict[str, Any]:
        """Pause or unpause an alert."""
        try:
            return await self._request(
                "POST",
                f"api/alerts/{alert_id}/pause",
                json_data={"paused": paused},
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to pause alert {alert_id}: {str(e)}")

    # Notification Channels API
    async def get_notification_channels(self) -> List[Dict[str, Any]]:
        """Get all notification channels."""
        try:
            response = await self._request(
                "GET",
                "api/alert-notifications",
                headers=self._prepare_auth_headers(),
            )
            return response
        except Exception as e:
            raise GrafanaError(f"Failed to get notification channels: {str(e)}")

    async def create_notification_channel(
        self,
        channel_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a notification channel."""
        try:
            return await self._request(
                "POST",
                "api/alert-notifications",
                json_data=channel_data,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to create notification channel: {str(e)}")

    async def test_notification_channel(
        self,
        channel_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test a notification channel."""
        try:
            return await self._request(
                "POST",
                "api/alert-notifications/test",
                json_data=channel_data,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to test notification channel: {str(e)}")

    # Organization API
    async def get_current_organization(self) -> Dict[str, Any]:
        """Get current organization."""
        try:
            return await self._request(
                "GET",
                "api/org",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get current organization: {str(e)}")

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        try:
            response = await self._request(
                "GET",
                "api/users",
                headers=self._prepare_auth_headers(),
            )
            return response
        except Exception as e:
            raise GrafanaError(f"Failed to get users: {str(e)}")

    # Health and Status
    async def get_health(self) -> Dict[str, Any]:
        """Get Grafana health status."""
        try:
            return await self._request(
                "GET",
                "api/health",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get health status: {str(e)}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get Grafana statistics."""
        try:
            return await self._request(
                "GET",
                "api/stats",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get statistics: {str(e)}")

    # Admin API
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Get admin statistics."""
        try:
            return await self._request(
                "GET",
                "api/admin/stats",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise GrafanaError(f"Failed to get admin statistics: {str(e)}")

    async def get_global_users(self) -> List[Dict[str, Any]]:
        """Get global users (admin only)."""
        try:
            response = await self._request(
                "GET",
                "api/admin/users",
                headers=self._prepare_auth_headers(),
            )
            return response
        except Exception as e:
            raise GrafanaError(f"Failed to get global users: {str(e)}")

    # Concurrent operations
    async def get_multiple_dashboards(
        self,
        uids: List[str],
        max_concurrent: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get multiple dashboards concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def get_dashboard(uid: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.get_dashboard(uid)

        tasks = [get_dashboard(uid) for uid in uids]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def create_multiple_dashboards(
        self,
        dashboards: List[Dict[str, Any]],
        max_concurrent: int = 5,
    ) -> List[Dict[str, Any]]:
        """Create multiple dashboards concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def create_dashboard(dashboard: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.create_dashboard(dashboard)

        tasks = [create_dashboard(dashboard) for dashboard in dashboards]
        return await asyncio.gather(*tasks, return_exceptions=True)