import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Literal, Annotated
from typing_extensions import TypedDict
import operator
from pydantic import BaseModel, Field

# Import your existing modules
from ..LLM_Model import llm_config as llm
from ..Controller import Controller as ctrl


# ============ PYDANTIC MODELS ============

class MaintenanceLog(BaseModel):
    """Open maintenance log from human input"""
    log_id: str
    equipment_serial: str
    description: str
    reported_by: str
    severity: Literal["low", "medium", "high", "critical"]
    status: str = "open"
    created_at: datetime


class EquipmentDetails(BaseModel):
    """Equipment information"""
    serial: str
    name: Optional[str] = None
    type: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None
    last_maintenance: Optional[str] = None


class ValidationResult(BaseModel):
    """AI validation result for maintenance log"""
    log_id: str
    equipment_serial: str
    human_description: str
    ai_summary: str
    validation_feedback: str
    is_correct: bool
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: str
    timestamp: datetime = Field(default_factory=datetime.now)


# ============ STATE DEFINITION ============

class ValidationState(TypedDict):
    """Workflow state"""
    # Input
    open_logs: List[MaintenanceLog]
    
    # Fetched data - FIXED: No operator.add for dictionaries
    equipment_data: Dict[str, EquipmentDetails]
    monitoring_data: Dict[str, List[Dict]]
    maintenance_history: Dict[str, List[Dict]]
    
    # Results
    validation_results: Annotated[List[ValidationResult], operator.add]
    final_output: Annotated[List[Dict[str, Any]], operator.add]
    
    # Control
    current_step: str
    errors: Annotated[List[str], operator.add]
    processed_count: int


# ============ HELPER FUNCTIONS ============

def parse_ai_response(text: str) -> Dict[str, Any]:
    """Parse AI response into structured data"""
    text = text.strip()
    
    # Try to extract JSON
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    match = re.search(json_pattern, text, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            # Try to clean up common JSON issues
            cleaned = match.group()
            cleaned = cleaned.replace('\n', ' ').replace('\t', ' ')
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            try:
                return json.loads(cleaned)
            except:
                pass
    
    # Fallback: simple keyword parsing
    result = {
        "ai_summary": "Unable to parse AI response",
        "validation_feedback": "Requires manual review",
        "is_correct": False,
        "confidence": 0.5,
        "recommended_action": "Investigate manually",
        "needs_maintenance": True,
        "priority": "medium"
    }
    
    text_lower = text.lower()
    
    # Check for validation keywords
    if "correct" in text_lower or "accurate" in text_lower or "valid" in text_lower or "true" in text_lower:
        result["is_correct"] = True
    if "incorrect" in text_lower or "wrong" in text_lower or "invalid" in text_lower or "false" in text_lower:
        result["is_correct"] = False
    
    # Check for priority
    if "critical" in text_lower:
        result["priority"] = "critical"
    elif "high" in text_lower:
        result["priority"] = "high"
    elif "low" in text_lower:
        result["priority"] = "low"
    
    # Extract summary if possible
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        # Find a line that looks like a summary (not too short, not JSON)
        for line in lines:
            if len(line) > 20 and not line.startswith('{') and not line.startswith('['):
                result["ai_summary"] = line[:200]
                break
    
    return result


def format_data_for_ai(monitoring_data: List[Dict], history: List[Dict]) -> str:
    """Format data for AI analysis"""
    # Get recent monitoring
    recent_monitoring = monitoring_data[-10:] if len(monitoring_data) > 10 else monitoring_data
    
    formatted = "Recent Monitoring Data:\n"
    if recent_monitoring:
        for i, entry in enumerate(recent_monitoring, 1):
            timestamp = entry.get('timestamp', 'No timestamp')
            if isinstance(timestamp, str) and len(timestamp) > 20:
                timestamp = timestamp[:20] + "..."
            
            parameter = str(entry.get('parameter', 'Unknown'))[:30]
            value = str(entry.get('value', 'N/A'))[:30]
            unit = str(entry.get('unit', ''))[:10]
            
            formatted += f"{i}. {timestamp}: {parameter} = {value} {unit}\n"
    else:
        formatted += "No monitoring data available\n"
    
    formatted += "\nMaintenance History:\n"
    if history:
        for i, record in enumerate(history[-5:], 1):
            date = str(record.get('date', 'Unknown'))[:20]
            action = str(record.get('action', 'Maintenance'))[:50]
            status = str(record.get('status', 'completed'))[:20]
            
            formatted += f"{i}. {date}: {action} - {status}\n"
    else:
        formatted += "No previous maintenance records\n"
    
    return formatted


# ============ WORKFLOW NODES ============

def fetch_open_logs_node(state: ValidationState) -> Dict[str, Any]:
    """Fetch open maintenance logs"""
    try:
        response = ctrl.fetch_maintenance_logs()
        logs = response.get("maintenance_logs", [])
        
        # Filter out AI-generated logs
        # print("Logs: ", logs)
        logs = [log for log in logs if log.get("raised_by", "").lower() != "ai system"]
        print("Logs: ", logs)
        
        
        open_logs = []
        for log in logs:
            print(log)
            print(log.get("status"))
            if log.get("status", "").lower() in ["open"]:
                # Parse datetime if it exists
                created_at = datetime.now()
                if "created_at" in log:
                    try:
                        created_at_str = log["created_at"]
                        if 'Z' in created_at_str:
                            created_at_str = created_at_str.replace('Z', '+00:00')
                        elif '.' in created_at_str and '+' not in created_at_str and 'Z' not in created_at_str:
                            # Handle datetime without timezone
                            created_at_str = created_at_str.split('.')[0]
                        created_at = datetime.fromisoformat(created_at_str)
                    except Exception as e:
                        # If parsing fails, use current time
                        pass
                
                open_logs.append(MaintenanceLog(
                    log_id=str(log.get("id", "")),
                    equipment_serial=str(log.get("equipment_serial", "")),
                    description=str(log.get("description", "")),
                    reported_by=str(log.get("raised_by", "unknown")),
                    severity=log.get("severity", "medium"),
                    status=log.get("status", "open"),
                    created_at=created_at
                ))
                print("OpenLogs: ", open_logs)
        
        return {
            "open_logs": open_logs,
            "current_step": "logs_fetched",
            "processed_count": 0,
            "errors": []
        }
        
    except Exception as e:
        return {
            "open_logs": [],
            "current_step": "error",
            "errors": [f"Failed to fetch logs: {str(e)}"]
        }


def fetch_equipment_data_node(state: ValidationState) -> Dict[str, Any]:
    """Fetch equipment and monitoring data"""
    if not state.get("open_logs"):
        return {
            "current_step": "error",
            "errors": ["No open logs to process"]
        }
    
    equipment_data = {}
    monitoring_data = {}
    maintenance_history = {}
    errors = []
    
    # Get unique serials
    serials = list(set([log.equipment_serial for log in state["open_logs"]]))
    
    for serial in serials:
        try:
            # Fetch equipment details
            eq_response = ctrl.fetch_equipment_by_serial(serial)
            if eq_response and isinstance(eq_response, dict) and "equipment" in eq_response:
                eq = eq_response["equipment"]
                equipment_data[serial] = EquipmentDetails(
                    serial=serial,
                    name=eq.get("name"),
                    type=eq.get("type"),
                    model=eq.get("model"),
                    status=eq.get("status"),
                    last_maintenance=eq.get("last_maintenance")
                )
            elif eq_response and isinstance(eq_response, dict):
                # Handle case where response is the equipment dict directly
                equipment_data[serial] = EquipmentDetails(
                    serial=serial,
                    name=eq_response.get("name"),
                    type=eq_response.get("type"),
                    model=eq_response.get("model"),
                    status=eq_response.get("status"),
                    last_maintenance=eq_response.get("last_maintenance")
                )
            else:
                equipment_data[serial] = EquipmentDetails(serial=serial)
            
            # Fetch monitoring logs
            mon_response = ctrl.fetch_monitoring_log(serial)
            if mon_response and isinstance(mon_response, dict):
                monitoring_data[serial] = mon_response.get("logs", [])
            else:
                monitoring_data[serial] = []
            
            # Fetch maintenance history
            hist_response = ctrl.fetch_equipment_maintenance_logs(serial)
            if hist_response and isinstance(hist_response, dict):
                maintenance_history[serial] = hist_response.get("maintenance_logs", [])
            else:
                maintenance_history[serial] = []
            
        except Exception as e:
            errors.append(f"Failed to fetch data for {serial}: {str(e)}")
            equipment_data[serial] = EquipmentDetails(serial=serial)
            monitoring_data[serial] = []
            maintenance_history[serial] = []
    
    return {
        "equipment_data": equipment_data,  # Just return the dict, no addition
        "monitoring_data": monitoring_data,
        "maintenance_history": maintenance_history,
        "current_step": "data_fetched",
        "errors": errors
    }


def analyze_and_validate_node(state: ValidationState) -> Dict[str, Any]:
    """Analyze each log and validate against data"""
    if not all([
        state.get("open_logs"),
        state.get("equipment_data"),
        state.get("monitoring_data")
    ]):
        return {
            "current_step": "error",
            "errors": ["Missing required data for analysis"]
        }
    
    validation_results = []
    errors = state.get("errors", [])
    
    for log in state["open_logs"]:
        serial = log.equipment_serial
        
        # Get data
        equipment = state["equipment_data"].get(serial)
        monitoring = state["monitoring_data"].get(serial, [])
        history = state["maintenance_history"].get(serial, [])
        
        # Prepare AI prompt
        prompt = f"""
        Analyze this maintenance log against equipment data:
        
        MAINTENANCE LOG:
        - Equipment: {equipment.name if equipment and equipment.name else serial}
        - Reported Issue: {log.description}
        - Reported Severity: {log.severity}
        - Reported By: {log.reported_by}
        
        EQUIPMENT INFO:
        - Type: {equipment.type if equipment else 'Unknown'}
        - Model: {equipment.model if equipment else 'Unknown'}
        - Status: {equipment.status if equipment else 'Unknown'}
        - Last Maintenance: {equipment.last_maintenance if equipment else 'Unknown'}
        
        DATA ANALYSIS:
        {format_data_for_ai(monitoring, history)}
        
        VALIDATION TASK:
        1. Is the reported issue correct based on monitoring data?
        2. Provide a brief AI summary of equipment condition
        3. Give validation feedback on provided report accuracy
        4. Recommend if maintenance is needed
        5. Suggest priority level
        
        Return JSON format:
        {{
            "ai_summary": "2-3 sentence summary",
            "validation_feedback": "Is provided report accurate?",
            "is_correct": true/false,
            "confidence": 0.0-1.0,
            "recommended_action": "what to do",
            "needs_maintenance": true/false,
            "priority": "low/medium/high/critical"
        }}
        """
        
        try:
            # Get AI analysis
            ai_response = llm.llm_model.invoke(prompt)
            result = parse_ai_response(ai_response.content)
            
            # Create validation result
            validation = ValidationResult(
                log_id=log.log_id,
                equipment_serial=serial,
                human_description=log.description[:500],  # Limit length
                ai_summary=result.get("ai_summary", "No analysis")[:1000],
                validation_feedback=result.get("validation_feedback", "No feedback")[:500],
                is_correct=result.get("is_correct", False),
                confidence=min(max(result.get("confidence", 0.5), 0.0), 1.0),  # Clamp to 0-1
                recommended_action=result.get("recommended_action", "Review manually")[:500]
            )
            validation_results.append(validation)
            
        except Exception as e:
            error_msg = f"Analysis failed for log {log.log_id}: {str(e)}"
            errors.append(error_msg)
            
            # Create error result
            validation_results.append(ValidationResult(
                log_id=log.log_id,
                equipment_serial=serial,
                human_description=log.description[:500],
                ai_summary=f"Analysis error: {str(e)[:200]}",
                validation_feedback="Failed to analyze",
                is_correct=False,
                confidence=0.0,
                recommended_action="Manual review required"
            ))
    
    return {
        "validation_results": validation_results,
        "current_step": "analysis_complete",
        "processed_count": len(validation_results),
        "errors": errors
    }


def generate_final_output_node(state: ValidationState) -> Dict[str, Any]:
    """Generate final concise output"""
    if not state.get("validation_results"):
        return {
            "current_step": "error",
            "errors": ["No validation results"],
            "final_output": []
        }
    
    final_output = []
    errors = state.get("errors", [])
    
    # Group by equipment
    equipment_groups = {}
    for result in state["validation_results"]:
        serial = result.equipment_serial
        if serial not in equipment_groups:
            equipment_groups[serial] = []
        equipment_groups[serial].append(result)
    
    # Create output for each equipment
    for serial, results in equipment_groups.items():
        equipment = state["equipment_data"].get(serial)
        
        # Get the most recent/latest validation
        latest_result = max(results, key=lambda x: x.timestamp) if results else None
        
        if not latest_result:
            continue
            
        # Calculate overall metrics
        correct_count = sum(1 for r in results if r.is_correct)
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0
        
        # Parse AI responses to determine needs_maintenance and priority
        needs_maintenance_list = []
        priority_list = []
        
        for result in results:
            parsed = parse_ai_response(result.ai_summary)
            needs_maintenance_list.append(parsed.get("needs_maintenance", True))
            priority_list.append(parsed.get("priority", "medium"))
        
        # Determine overall needs_maintenance (if any says True, then True)
        needs_maintenance = any(needs_maintenance_list)
        
        # Determine highest priority
        priority_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        highest_priority = "medium"
        highest_score = 2
        
        for priority in priority_list:
            score = priority_map.get(priority.lower(), 2)
            if score > highest_score:
                highest_score = score
                highest_priority = priority.lower()
        
        # Create concise equipment analysis
        equipment_dict = {
            "serial": serial,
            "name": equipment.name if equipment and equipment.name else "Unknown",
            "type": equipment.type if equipment and equipment.type else "Unknown",
            "model": equipment.model if equipment and equipment.model else "Unknown",
            "status": equipment.status if equipment and equipment.status else "Unknown",
            "last_maintenance": equipment.last_maintenance if equipment else "Unknown"
        }
        
        # Create summary text
        ai_summary = f"AI Analysis for {equipment_dict['name']} ({serial}):\n"
        ai_summary += f"- {latest_result.ai_summary}\n"
        ai_summary += f"- Overall Confidence: {avg_confidence:.1%}\n"
        ai_summary += f"- Accurate Reports: {correct_count}/{len(results)}"
        
        # Create validation feedback
        validation_feedback = f"Validation Results:\n"
        validation_feedback += f"- Latest Assessment: {latest_result.validation_feedback}\n"
        if correct_count == len(results):
            validation_feedback += "- ✓ All reports are accurate"
        elif correct_count == 0:
            validation_feedback += "- ✗ All reports need review"
        else:
            validation_feedback += f"- ⚠ {correct_count} accurate, {len(results)-correct_count} need review"
        
        # Add to final output
        final_output.append({
            "equipment_details": equipment_dict,
            "ai_summary": ai_summary,
            "validation_feedback": validation_feedback,
            "needs_maintenance": needs_maintenance,
            "priority": highest_priority,
            "total_logs": len(results),
            "accuracy_rate": f"{correct_count}/{len(results)}",
            "avg_confidence": f"{avg_confidence:.1%}"
        })
    
    return {
        "final_output": final_output,
        "current_step": "complete",
        "errors": errors
    }


# ============ WORKFLOW GRAPH ============

from langgraph.graph import StateGraph, END

def build_validation_workflow():
    """Build and compile the workflow graph"""
    
    workflow = StateGraph(ValidationState)
    
    # Add nodes
    workflow.add_node("fetch_logs", fetch_open_logs_node)
    workflow.add_node("fetch_data", fetch_equipment_data_node)
    workflow.add_node("analyze", analyze_and_validate_node)
    workflow.add_node("generate_output", generate_final_output_node)
    
    # Define flow
    workflow.set_entry_point("fetch_logs")
    workflow.add_edge("fetch_logs", "fetch_data")
    workflow.add_edge("fetch_data", "analyze")
    workflow.add_edge("analyze", "generate_output")
    workflow.add_edge("generate_output", END)
    
    # Compile
    app = workflow.compile()
    
    return app


# ============ MAIN EXECUTION FUNCTION ============

validation_app = build_validation_workflow()

def execute_maintenance_validation():
    """
    Execute the maintenance validation workflow.
    Call this function from your button click handler.
    Returns: List of dictionaries with equipment details, AI summary, and validation feedback
    """
    
    initial_state = {
        "open_logs": [],
        "equipment_data": {},
        "monitoring_data": {},
        "maintenance_history": {},
        "validation_results": [],
        "final_output": [],
        "current_step": "started",
        "errors": [],
        "processed_count": 0
    }
    
    try:
        print("Starting maintenance validation...")
        
        # Run workflow
        final_state = validation_app.invoke(initial_state)
        
        # Check for errors
        if final_state.get("errors"):
            print(f"Errors encountered: {final_state['errors']}")
        
        # Get the final output
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "analysis_report": final_state.get("final_output", []),
            "total_processed": final_state.get("processed_count", 0),
            "errors": final_state.get("errors", []),
            "execution_time": final_state.get("current_step", "")
        }
        
        # Print summary
        print(f"Validation complete. Processed {result['total_processed']} maintenance logs.")
        print(f"Generated {len(result['analysis_report'])} equipment analyses.")
        
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "analysis_report": [],
            "total_processed": 0,
            "errors": [str(e)]
        }
        print(f"Validation failed: {str(e)}")
        return error_result


# ============ UTILITY FUNCTION FOR API ============

def get_validation_results():
    """Simple wrapper for API calls"""
    return execute_maintenance_validation()