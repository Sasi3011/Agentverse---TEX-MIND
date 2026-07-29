from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MillState(BaseModel):
    batch_id: str
    created_at: datetime

    intake_result: Optional[dict] = None          # from Agent 1
    defect_result: Optional[dict] = None          # from Agent 2
    dye_recipe: Optional[dict] = None             # from Agent 3
    effluent_status: Optional[dict] = None        # from Agent 4 (latest snapshot)
    energy_status: Optional[dict] = None          # from Agent 5 (latest snapshot)
    maintenance_queue: Optional[List[dict]] = None # from Agent 6
    safety_status: Optional[dict] = None          # from Agent 7 (latest snapshot)
    demand_forecast: Optional[dict] = None        # from Agent 8
    traceability_record: Optional[dict] = None     # from Agent 9
    sustainability_report: Optional[dict] = None   # from Agent 10

    status: str = "in_progress"   # in_progress | completed | halted
    halted_reason: Optional[str] = None
