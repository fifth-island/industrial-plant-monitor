"""Event broadcasting system for real-time dashboard updates."""

import asyncio
from uuid import UUID
from typing import Dict


class FacilityEventBroadcaster:
    """Manages event broadcasting for facility-specific data updates."""
    
    def __init__(self):
        # Map of facility_id -> asyncio.Condition for that facility's subscribers
        self._facility_conditions: Dict[UUID, asyncio.Condition] = {}
        self._lock = asyncio.Lock()
    
    async def _get_condition(self, facility_id: UUID) -> asyncio.Condition:
        """Get or create a Condition for the given facility."""
        async with self._lock:
            if facility_id not in self._facility_conditions:
                self._facility_conditions[facility_id] = asyncio.Condition()
            return self._facility_conditions[facility_id]
    
    async def broadcast_update(self, facility_id: UUID):
        """Notify all subscribers that facility data has been updated."""
        condition = await self._get_condition(facility_id)
        async with condition:
            condition.notify_all()
    
    async def wait_for_update(self, facility_id: UUID, timeout: float = 15.0) -> bool:
        """
        Wait for a facility update event.
        
        Returns:
            True if update event received, False if timeout occurred
        """
        condition = await self._get_condition(facility_id)
        async with condition:
            try:
                await asyncio.wait_for(condition.wait(), timeout=timeout)
                return True
            except asyncio.TimeoutError:
                return False


# Global broadcaster instance
broadcaster = FacilityEventBroadcaster()
