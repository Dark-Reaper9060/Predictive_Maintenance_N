from ..LLM_Model import llm_config as llm

from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages, MessagesState

from typing import Annotated, List
from typing_extensions import TypedDict
from pydantic import BaseModel
import operator

from ..Controller import Controller as ctrl

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, END
import operator
from datetime import datetime
import json
import re

# ============ PYDANTIC MODELS ============
from pydantic import BaseModel, Field
from typing import Literal

class Equipment(BaseModel):
    serial: str
    name: Optional[str] = None
    type: Optional[str] = None
    maintenance_status: Literal["open", "closed", "in_progress", "none"] = "none"

class MaintenanceDecision(BaseModel):
    equipment_serial: str
    needs_maintenance: bool
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    date_decided: datetime = Field(default_factory=datetime.now)
    date_predicted: datetime = None

class MaintenanceLogBase(BaseModel):
    raised_by: str = "system_ai"
    equipment_serial: str
    issue_description: str
    severity: Literal["low", "medium", "high", "critical"]
    date_reported: datetime = Field(default_factory=datetime.now)
    date_predicted: datetime = None
    


# ============ STATE DEFINITION ============
class State(TypedDict):
    # Core data flow
    equipments: List[Equipment]  # Will be replaced each time
    monitoring_logs: dict  # {serial: logs_data}
    maintenance_logs: dict  # {serial: logs_data}
    
    # Auto-accumulating lists
    summaries: Annotated[List[str], operator.add]
    maintenance_decisions: Annotated[List[MaintenanceDecision], operator.add]
    created_logs: Annotated[List[dict], operator.add]  
    
    # Control flow
    current_step: str
    errors: Annotated[List[str], operator.add]
    processed_count: int

# ============ HELPER FUNCTIONS ============
def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response text."""
    # Clean the text
    text = text.strip()
    
    # Try to extract JSON with regex
    json_pattern = r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}'  
    match = re.search(json_pattern, text, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    # Fallback: try to parse as key-value pairs
    result = {
        "needs_maintenance": False,
        "reason": "Could not parse LLM response",
        "confidence": 0.0
    }
    
    # Simple keyword extraction
    if "true" in text.lower() or "yes" in text.lower() or "required" in text.lower():
        result["needs_maintenance"] = True
    if "false" in text.lower() or "no" in text.lower() or "not required" in text.lower():
        result["needs_maintenance"] = False
    
    return result

def determine_severity(reason: str, confidence: float) -> str:
    """Determine severity based on reason and confidence."""
    reason_lower = reason.lower()
    
    if confidence >= 0.8:
        if any(word in reason_lower for word in ["critical", "urgent", "immediate", "failure", "broken"]):
            return "critical"
        elif any(word in reason_lower for word in ["high", "severe", "serious", "danger"]):
            return "high"
        elif any(word in reason_lower for word in ["medium", "moderate", "degraded"]):
            return "medium"
        else:
            return "low"
    else:
        return "low"  # Low confidence = low severity

# ============ NODE 1: FETCH EQUIPMENTS ============
def fetch_equipments_node(state: State) -> dict:
    """Node 1: Fetch all equipments from database"""
    try:
        # Assuming you have a controller module 'ctrl'
        ctrl_response = ctrl.fetch_all_equipments()
        
        equipments = [
            Equipment(
                serial=eq["serial"],
                name=eq.get("name"),
                type=eq.get("type")
            ) for eq in ctrl_response.get("equipments", [])
        ]
        
        return {
            "equipments": equipments,
            "current_step": "equipments_fetched",
            "processed_count": 0,
            "summaries": [f"Fetched {len(equipments)} equipments from database"]
        }
        
    except Exception as e:
        return {
            "equipments": [],
            "current_step": "error",
            "errors": [f"Failed to fetch equipments: {str(e)}"]
        }

# ============ NODE 2: FETCH MONITORING LOGS ============
def fetch_monitoring_node(state: State) -> dict:
    """Node 2: Fetch monitoring logs for each equipment"""
    if not state.get("equipments"):
        return {
            "current_step": "error",
            "errors": ["No equipments to process"]
        }
    
    monitoring_logs = {}
    maintenance_logs = {}
    errors = []
    
    for equipment in state["equipments"]:
        try:
            ctrl_response = ctrl.fetch_monitoring_log(equipment.serial)
            monitoring_logs[equipment.serial] = ctrl_response.get("monitoring_data", {})
            
            ctrl_response = ctrl.fetch_equipment_maintenance_logs(equipment.serial)
            maintenance_logs[equipment.serial] = ctrl_response.get("maintenance_logs", {})
        except Exception as e:
            errors.append(f"Failed to fetch logs for {equipment.serial}: {str(e)}")
            monitoring_logs[equipment.serial] = {"error": str(e)}
            
            errors.append(f"Failed to fetch logs for {equipment.serial}: {str(e)}")
            maintenance_logs[equipment.serial] = {"error": str(e)}
    
    # print("Monitoring Logs Fetched:", monitoring_logs)
    
    return {
        "monitoring_logs": monitoring_logs,
        "maintenance_logs": maintenance_logs,
        "current_step": "monitoring_fetched",
        "errors": errors,
        "summaries": [f"Fetched monitoring data for {len(monitoring_logs)} equipments"]
    }

# ============ NODE 3: ANALYZE & DECIDE ============
def analyze_and_decide_node(state: State) -> dict:
    """Node 3: Analyze logs and decide if maintenance is needed"""
    if not state.get("monitoring_logs"):
        return {
            "current_step": "error",
            "errors": ["No monitoring data to analyze"]
        }
    
    decisions = []
    summaries = []
    
    for equipment in state["equipments"]:
        serial = equipment.serial
        monitoring_logs = state["monitoring_logs"].get(serial, {})
        maintenance_logs = state["maintenance_logs"].get(serial, {})
        
        # 1. Create summary
        summary_prompt = f"""
        Equipment: {equipment.name or 'Unknown'} ({serial})
        Type: {equipment.type or 'Unknown'}
        Monitoring Data: {monitoring_logs}
        Maintenance Data: {maintenance_logs}
        
        Provide a brief 1-2 sentence summary of this equipment's current status.
        """
        
        try:
            summary_response = llm.llm_model.invoke(summary_prompt)
            summaries.append(f"{serial}: {summary_response.content.strip()}")
        except Exception as e:
            summaries.append(f"{serial}: Error generating summary: {str(e)}")
        
        # 2. Maintenance decision
        decision_prompt = f"""
        Based on this monitoring data and Maintenance Log decide if maintenance is required in future and when from today which is {datetime.utcnow().date()}. Strictly predict the date and date should be in this DD-MM-YYYY format.:
        Strictly if the equipment is already under maintenance or open state then do not suggest maintenance.
        Equipment: {equipment.name or 'Unknown'} ({serial})
        Monitoring Data: {monitoring_logs}
        Maintenance Data: {maintenance_logs}
        
        Return a JSON object with this exact structure:
        {{
            "needs_maintenance": true/false,
            "reason": "brief explanation here",
            "confidence": decimal between 0.0 and 1.0,
            "date_predicted": "DD-MM-YYYY"
        }}
        
        Only return the JSON object, nothing else.
        """
        
        try:
            decision_response = llm.llm_model.invoke(decision_prompt)
            decision_data = parse_json_response(decision_response.content)
            
            # Ensure all required fields are present
            decision = MaintenanceDecision(
                equipment_serial=serial,
                needs_maintenance=decision_data.get("needs_maintenance", False),
                reason=decision_data.get("reason", "No analysis provided"),
                confidence=decision_data.get("confidence", 0.0),
                date_predicted=datetime.strptime(decision_data.get("date_predicted", datetime.utcnow().strftime("%d-%m-%Y")), "%d-%m-%Y")
            )
            decisions.append(decision)
            
        except Exception as e:
            # Fallback decision
            decisions.append(MaintenanceDecision(
                equipment_serial=serial,
                needs_maintenance=False,
                reason=f"Analysis failed: {str(e)}",
                confidence=0.0,
                date_predicted=None
            ))
    
    return {
        "maintenance_decisions": decisions,
        "summaries": summaries,
        "current_step": "analysis_complete",
        "processed_count": len(decisions)
    }

# ============ NODE 4: CREATE MAINTENANCE LOGS ============
def create_maintenance_logs_node(state: State) -> dict:
    """Node 4: Create maintenance logs for equipment needing maintenance"""
    if not state.get("maintenance_decisions"):
        return {
            "current_step": "error",
            "errors": ["No decisions to process"]
        }
    
    created_logs = []
    errors = []
    
    # Filter decisions that need maintenance
    maintenance_needed = [
        decision for decision in state["maintenance_decisions"] 
        if decision.needs_maintenance
    ]
    
    for decision in maintenance_needed:
        try:
            # Determine severity
            severity = determine_severity(decision.reason, decision.confidence)
            
            # Create maintenance log
            maintenance_log = MaintenanceLogBase(
                raised_by="AI System",
                equipment_serial=decision.equipment_serial,
                issue_description=f"AI-detected issue: {decision.reason}",
                severity=severity,
                date_predicted=decision.date_predicted
            )
            
            # Call your external function
            # result = eq.insert_maintenance_log(
            #     maintenance_log.raised_by,
            #     maintenance_log.equipment_serial,
            #     maintenance_log.issue_description,
            #     maintenance_log.severity,
            #     str(maintenance_log.date_reported)
            # )

            result = ctrl.add_maintenance_log(maintenance_log)
            
            if(result):
                ctrl.update_equipment_status(decision.equipment_serial,status="under_maintenance" ,maintenance_status = "pending")
            
            print("Maintenance Log Date:", maintenance_log.date_predicted)
            
            created_logs.append({
                "equipment_serial": decision.equipment_serial,
                "log_created": True,
                "severity": severity,
                "message": result.get("message", "Log created"),
                "date_predicted": str(maintenance_log.date_predicted) if maintenance_log.date_predicted else None,
                "timestamp": str(maintenance_log.date_reported),
            })
            
        except Exception as e:
            errors.append(f"Failed to create log for {decision.equipment_serial}: {str(e)}")
            created_logs.append({
                "equipment_serial": decision.equipment_serial,
                "log_created": False,
                "error": str(e)
            })
    
    return {
        "created_logs": created_logs,
        "current_step": "logs_created",
        "errors": errors,
        "summaries": [f"Created maintenance logs for {len(created_logs)} equipments"]
    }

# ============ NODE 5: FINAL REPORT ============
def final_report_node(state: State) -> dict:
    """Node 5: Generate final report"""
    summary_stats = {
        "total_equipments": len(state.get("equipments", [])),
        "needs_maintenance": len([d for d in state.get("maintenance_decisions", []) if d.needs_maintenance]),
        "logs_created": len(state.get("created_logs", [])),
        "errors": len(state.get("errors", [])),
        "confidence_avg": (
            sum(d.confidence for d in state.get("maintenance_decisions", [])) / 
            max(len(state.get("maintenance_decisions", [])), 1)
        )
    }
    
    report = f"""
    === MAINTENANCE WORKFLOW COMPLETE ===
    
    Statistics:
    - Total equipments processed: {summary_stats['total_equipments']}
    - Require maintenance: {summary_stats['needs_maintenance']}
    - Maintenance logs created: {summary_stats['logs_created']}
    - Errors encountered: {summary_stats['errors']}
    - Average confidence: {summary_stats['confidence_avg']:.2f}
    
    Details:
    """
    
    for decision in state.get("maintenance_decisions", []):
        report += f"\n- {decision.equipment_serial}: "
        report += f"Maintenance {'NEEDED' if decision.needs_maintenance else 'not needed'}"
        report += f" (Confidence: {decision.confidence:.2f})"
        report += f" - Reason: {decision.reason}"
    
    if state.get("errors"):
        report += "\n\nErrors encountered:"
        for error in state["errors"]:
            report += f"\n- {error}"
    
    return {
        "current_step": "complete",
        "summaries": [report]
    }

# ============ GRAPH CONSTRUCTION ============
# Build the graph
workflow = StateGraph(State)

# Add nodes
workflow.add_node("fetch_equipments", fetch_equipments_node)
workflow.add_node("fetch_monitoring", fetch_monitoring_node)
workflow.add_node("analyze_and_decide", analyze_and_decide_node)
workflow.add_node("create_maintenance_logs", create_maintenance_logs_node)
workflow.add_node("final_report", final_report_node)

# Define flow
workflow.set_entry_point("fetch_equipments")
workflow.add_edge("fetch_equipments", "fetch_monitoring")
workflow.add_edge("fetch_monitoring", "analyze_and_decide")
workflow.add_edge("analyze_and_decide", "create_maintenance_logs")
workflow.add_edge("create_maintenance_logs", "final_report")
workflow.add_edge("final_report", END)

# Compile the app
app = workflow.compile()

# ============ EXECUTION FUNCTION ============
def execute_maintenance_workflow():
    """Execute the entire workflow (call this on button click)"""
    
    # Initial state
    initial_state = {
        "equipments": [],
        "monitoring_logs": {},
        "summaries": [],
        "maintenance_decisions": [],
        "created_logs": [],
        "current_step": "started",
        "errors": [],
        "processed_count": 0
    }
    
    try:
        # Execute the graph
        final_state = app.invoke(initial_state)
        
        # Return structured result
        return {
            "success": True,
            "summary": final_state.get("summaries", [])[-1] if final_state.get("summaries") else "No summary",
            "statistics": {
                "equipments_processed": len(final_state.get("equipments", [])),
                "maintenance_decisions": len(final_state.get("maintenance_decisions", [])),
                "logs_created": len(final_state.get("created_logs", [])),
                "errors": len(final_state.get("errors", [])),
                "final_step": final_state.get("current_step", "unknown")
            },
            "decisions": [
                {
                    "equipment_serial": d.equipment_serial,
                    "needs_maintenance": d.needs_maintenance,
                    "reason": d.reason,
                    "confidence": d.confidence
                }
                for d in final_state.get("maintenance_decisions", [])
            ],
            "created_logs": final_state.get("created_logs", []),
            "errors": final_state.get("errors", [])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "statistics": {
                "equipments_processed": 0,
                "maintenance_decisions": 0,
                "logs_created": 0,
                "errors": 1,
                "final_step": "failed"
            }
        }
        
        
        
        