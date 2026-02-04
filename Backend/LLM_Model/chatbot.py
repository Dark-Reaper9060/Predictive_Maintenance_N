from ..LLM_Model import llm_config as llm
from ..Controller import Controller as ctrl
from ..Embedd import vector_query as vector

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages, MessagesState

from typing import TypedDict, Annotated, List, Optional, Literal
from pydantic import BaseModel, Field
import operator
from typing_extensions import TypedDict

from datetime import datetime
import json


class Equipment(BaseModel):
    serial: str
    name: Optional[str] = None
    type: Optional[str] = None
    maintenance_status: Literal["not_needed","pending","in_progress","completed","overdue"] = "none"

class MaintenanceLogBase(BaseModel):
    raised_by: str = "system_ai"
    equipment_serial: str
    issue_description: str
    severity: Literal["low", "medium", "high", "critical"]
    date_reported: datetime = Field(default_factory=datetime.now)
    date_predicted: datetime = None

class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: Optional[str]
    equipments: Optional[List[Equipment]]
    monitoring_logs: Optional[dict]
    maintenance_logs: Optional[dict]
    equipment_query: Optional[str]
    serial_number: Optional[str]
    query_type: Optional[str]
    has_specific_equipment: Optional[bool]
    batch_mode: Optional[bool]
    current_batch_index: Optional[int]
    batch_results: Optional[list]
    user_prompt: Optional[str]

# ============ IMPROVED INTENT CLASSIFIER ============
def classify_intent(state: State) -> dict:
    """Classify user intent to route to appropriate branch"""
    user_message = state["messages"][-1].content if state["messages"] else ""
    
    user_lower = user_message.lower()
    
    # Extract serial number if present
    import re
    # Look for serial number patterns
    serial_match = re.search(r'(?:serial|sn|#)\s*([A-Za-z0-9\-]+)', user_lower, re.IGNORECASE)
    if not serial_match:
        # Also check for "serial ABC123" pattern
        serial_match = re.search(r'\b([A-Z][A-Z0-9\-]{2,})\b', user_lower)
    
    serial_number = serial_match.group(1) if serial_match else None
    
    # Check for specific equipment queries
    has_specific_equipment = bool(serial_number)
    
    # Check for specific keywords in context
    list_keywords = ["list all", "show all", "get all", "fetch all", "display all", "all equipment", "equipments list"]
    maintenance_keywords = ["maintenance", "repair", "service", "fix", "issue", "maintain"]
    monitoring_keywords = ["monitor", "health", "status", "performance", "condition", "sensor", "temperature", "pressure", "vibration"]
    equipment_keywords = ["equipment", "device", "machine", "asset", "serial", "sn"]
    
    # Check for batch processing requests
    batch_phrases = [
        "details of all equipment",
        "all equipment details",
        "detailed report of all",
        "comprehensive details for all",
        "give me details of all equipment",
        "show details for all equipment"
    ]
    
    # Check for maintenance list
    maintenance_list_phrases = [
        "list all maintenance",
        "show all maintenance",
        "all maintenance logs",
        "maintenance list",
        "all maintenance records"
    ]
    
    # Check for monitoring list
    monitoring_list_phrases = [
        "list all monitoring",
        "show all monitoring",
        "all monitoring data",
        "monitoring list",
        "all monitoring records"
    ]
    
    # Determine intent
    if any(phrase in user_lower for phrase in batch_phrases):
        intent = "batch_equipment_details"
    elif any(phrase in user_lower for phrase in maintenance_list_phrases):
        intent = "list_all_maintenance"
    elif any(phrase in user_lower for phrase in monitoring_list_phrases):
        intent = "list_all_monitoring"
    elif any(keyword in user_lower for keyword in list_keywords):
        intent = "list_equipments"
    elif has_specific_equipment:
        # Check what type of query for specific equipment
        if any(keyword in user_lower for keyword in maintenance_keywords):
            intent = "maintenance_query"
        elif any(keyword in user_lower for keyword in monitoring_keywords):
            intent = "monitoring_query"
        else:
            # General equipment details query
            intent = "fetch_equipment_details_node"
    else:
        intent = "general_chat"
    
    return {
        "intent": intent,
        "serial_number": serial_number,
        "has_specific_equipment": has_specific_equipment,
        "query_type": "list" if intent == "list_equipments" else "details"
    }

# ============ NODE 1: INTENT CLASSIFICATION ============
def intent_classifier_node(state: State) -> dict:
    """Route based on user intent"""
    intent_info = classify_intent(state)
    return intent_info

# ============ NODE 2: GENERAL CHAT ============
def general_chat_node(state: State) -> dict:
    """Handle general conversation"""
    
    retrieved_context = vector.ask_question(state["user_prompt"])
    print("Response_Type: ", retrieved_context)
    
    system_prompt = f"""You are a helpful assistant for equipment management system. 
    
    IMPORTANT RULES:
    1. For equipment-related queries, ALWAYS ask for the serial number first if not provided
    2. NEVER make up equipment details, serial numbers, maintenance logs, or monitoring data
    3. Only provide information that exists in the system
    4. If asked about specific equipment data, guide the user to provide a serial number
    5. You cannot generate any documents or reports (if user askes then only tell this else dont mention about exporting any documents.)
    
    This is Optional here is the extra context this can be empty, Retrieved Context: ( {retrieved_context} )
    Very Strictly if the Retrieved Context is related to the user prompt then only involve the retrieved context in the response.
    
    You can help with:
    - Listing all equipment
    - Showing equipment details (need serial number)
    - Showing maintenance history (need serial number)
    - Showing monitoring data (need serial number)
    - Listing all maintenance logs
    - Listing all monitoring data
    - Getting detailed report of all equipment
    
    For unrelated topics, politely say: "I can only assist with equipment management queries.""
    
    Example responses:
    - "I need the equipment serial number to check its details. Could you provide the serial number?"
    - "To check maintenance history, please provide the equipment serial number."
    - "I can help you with equipment management. What would you like to know?"""
    
    bot_response = llm.llm_model.invoke([
        {
            "role": "system",
            "content": system_prompt
        },
        *state["messages"]
    ])
    
    return {"messages": [bot_response]}

# ============ NODE 3: LIST EQUIPMENTS ============
def list_equipments_node(state: State) -> dict:
    """Fetch and list all equipments"""
    try:
        ctrl_response = ctrl.fetch_all_equipments()
        equipments_data = ctrl_response.get("equipments", [])
        
        if not equipments_data:
            system_prompt = "There are no equipments in the system. Please inform the user that no equipment data is currently available."
            bot_response = llm.llm_model.invoke([
                {
                    "role": "system",
                    "content": system_prompt
                },
                *state["messages"][-1:]
            ])
            return {"messages": [bot_response]}
        
        # Format equipment list for display
        equipment_list = []
        for eq in equipments_data:
            serial = eq.get('serial', 'Unknown')
            name = eq.get('name', 'N/A')
            eq_type = eq.get('type', 'N/A')
            status = eq.get('maintenance_status', 'N/A')
            equipment_list.append(f"• Serial: {serial}, Name: {name}, Type: {eq_type}, Status: {status}")
        
        equipment_summary = f"Found {len(equipments_data)} equipment(s) in the system:\n\n" + "\n".join(equipment_list)
        
        # Add suggestion for batch processing
        equipment_summary += "\n\nYou can ask for 'details of all equipment' to get comprehensive information about each equipment including monitoring and maintenance data."
        
        system_prompt = f"""EQUIPMENT LIST:
{equipment_summary}

Please provide this information to the user in a helpful way.
IMPORTANT: Only mention equipment from this list. Do not add, modify, or invent any equipment data."""
        
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        
        equipments = [
            Equipment(
                serial=eq.get("serial", ""),
                name=eq.get("name"),
                type=eq.get("type"),
                maintenance_status=eq.get("maintenance_status", "not_needed")
            ) for eq in equipments_data
        ]
        
        return {
            "messages": [bot_response],
            "equipments": equipments,
            "summaries": [f"Listed {len(equipments)} equipments"]
        }
        
    except Exception as e:
        print(f"Error in list_equipments_node: {str(e)}")
        system_prompt = "I encountered an issue while fetching the equipment list. Please try again later."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response], "errors": [str(e)]}

# ============ NODE 4: FETCH EQUIPMENT DETAILS ============
def fetch_equipment_details_node(state: State) -> dict:
    """Fetch comprehensive equipment details for a specific equipment"""
    serial_number = state.get("serial_number")
    
    if not serial_number:
        return general_chat_node(state)
    
    try:
        # First, check if equipment exists
        equipment_response = ctrl.fetch_equipment_by_serial(serial_number)
        equipment_data = equipment_response.get("equipment", {})
        
        if not equipment_data:
            system_prompt = f"Equipment with serial number '{serial_number}' was not found in the system. Please inform the user that this equipment does not exist."
            bot_response = llm.llm_model.invoke([
                {
                    "role": "system",
                    "content": system_prompt
                },
                *state["messages"][-1:]
            ])
            return {"messages": [bot_response]}
        
        # Equipment exists, now fetch additional data
        monitoring_data = {}
        maintenance_logs = []
        
        try:
            monitoring_response = ctrl.fetch_monitoring_log(serial_number)
            monitoring_data = monitoring_response.get("monitoring_data", {})
        except Exception as e:
            print(f"Error fetching monitoring data for {serial_number}: {e}")
            monitoring_data = {}
        
        try:
            maintenance_response = ctrl.fetch_equipment_maintenance_logs(serial_number)
            maintenance_logs = maintenance_response.get("maintenance_logs", [])
        except Exception as e:
            print(f"Error fetching maintenance logs for {serial_number}: {e}")
            maintenance_logs = []
        
        # Prepare comprehensive equipment information
        equipment_info = f"""EQUIPMENT DETAILS for {serial_number}:

        BASIC INFORMATION:
        • Serial Number: {equipment_data.get('serial', 'N/A')}
        • Name: {equipment_data.get('name', 'N/A')}
        • Type: {equipment_data.get('type', 'N/A')}
        • Maintenance Status: {equipment_data.get('maintenance_status', 'N/A')}"""
                
        # Add monitoring data if available
        if monitoring_data:
            equipment_info += "\n\nMONITORING DATA:"
            if monitoring_data.get('timestamp'):
                equipment_info += f"\n• Last Updated: {monitoring_data.get('timestamp')}"
            if monitoring_data.get('health_score') is not None:
                equipment_info += f"\n• Health Score: {monitoring_data.get('health_score')}"
            if monitoring_data.get('temperature') is not None:
                equipment_info += f"\n• Temperature: {monitoring_data.get('temperature')}°C"
            if monitoring_data.get('pressure') is not None:
                equipment_info += f"\n• Pressure: {monitoring_data.get('pressure')} psi"
            if monitoring_data.get('vibration') is not None:
                equipment_info += f"\n• Vibration: {monitoring_data.get('vibration')} mm/s"
            if monitoring_data.get('status'):
                equipment_info += f"\n• Overall Status: {monitoring_data.get('status')}"
        else:
            equipment_info += "\n\nMONITORING DATA: No monitoring data available"
        
        # Add maintenance logs if available
        if maintenance_logs:
            equipment_info += f"\n\nMAINTENANCE HISTORY ({len(maintenance_logs)} records):"
            for i, log in enumerate(maintenance_logs[:5], 1):
                date = log.get('date_reported', 'Unknown date')
                issue = log.get('issue_description', 'No description')
                severity = log.get('severity', 'Unknown')
                equipment_info += f"\n{i}. Date: {date}, Issue: {issue[:50]}..., Severity: {severity}"
            if len(maintenance_logs) > 5:
                equipment_info += f"\n... and {len(maintenance_logs) - 5} more records"
        else:
            equipment_info += "\n\nMAINTENANCE HISTORY: No maintenance records found"
        
        system_prompt = f"""{equipment_info}

        Based on the above information, provide a comprehensive summary of the equipment.
        IMPORTANT: 
        1. Mention ALL available information shown above
        2. If something is marked as "not available" or "no records", mention that fact
        3. Do not invent or assume any additional information
        4. Provide the information in a clear, helpful manner"""
                
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        
        # Create Equipment object
        equipment_obj = Equipment(
            serial=equipment_data.get("serial", ""),
            name=equipment_data.get("name"),
            type=equipment_data.get("type"),
            maintenance_status=equipment_data.get("maintenance_status", "not_needed")
        )
        
        return {
            "messages": [bot_response],
            "equipments": [equipment_obj],
            "monitoring_logs": {serial_number: monitoring_data} if monitoring_data else {},
            "maintenance_logs": {serial_number: maintenance_logs} if maintenance_logs else {},
            "serial_number": serial_number
        }
        
    except Exception as e:
        print(f"Error in fetch_equipment_details_node: {str(e)}")
        system_prompt = f"I encountered an issue while fetching details for equipment {serial_number}. Please try again."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response], "errors": [str(e)]}

# ============ NODE 5: BATCH EQUIPMENT DETAILS ============
def batch_equipment_details_node(state: State) -> dict:
    """Fetch comprehensive details for all equipment in batch mode"""
    try:
        # First, get all equipment
        ctrl_response = ctrl.fetch_all_equipments()
        all_equipments_data = ctrl_response.get("equipments", [])
        
        if not all_equipments_data:
            system_prompt = "There are no equipments in the system to generate a detailed report."
            bot_response = llm.llm_model.invoke([
                {
                    "role": "system",
                    "content": system_prompt
                },
                *state["messages"][-1:]
            ])
            return {"messages": [bot_response]}
        
        # Process each equipment
        detailed_reports = []
        total_equipments = len(all_equipments_data)
        
        for idx, eq_data in enumerate(all_equipments_data, 1):
            serial_number = eq_data.get('serial', f"Unknown-{idx}")
            
            # Prepare equipment summary
            equipment_report = f"\n{'='*60}\nEQUIPMENT {idx} of {total_equipments}: {serial_number}\n{'='*60}\n"
            
            # Basic info
            equipment_report += f"Name: {eq_data.get('name', 'N/A')}\n"
            equipment_report += f"Type: {eq_data.get('type', 'N/A')}\n"
            equipment_report += f"Maintenance Status: {eq_data.get('maintenance_status', 'N/A')}\n"
            
            # Fetch monitoring data
            try:
                monitoring_response = ctrl.fetch_monitoring_log(serial_number)
                monitoring_data = monitoring_response.get("monitoring_data", {})
                
                if monitoring_data:
                    equipment_report += "\nMONITORING DATA:\n"
                    if monitoring_data.get('health_score') is not None:
                        equipment_report += f"  • Health Score: {monitoring_data.get('health_score')}/100\n"
                    if monitoring_data.get('temperature') is not None:
                        equipment_report += f"  • Temperature: {monitoring_data.get('temperature')}°C\n"
                    if monitoring_data.get('status'):
                        equipment_report += f"  • Status: {monitoring_data.get('status')}\n"
                    if monitoring_data.get('timestamp'):
                        equipment_report += f"  • Last Updated: {monitoring_data.get('timestamp')}\n"
                else:
                    equipment_report += "\nMONITORING DATA: Not available\n"
            except Exception as e:
                equipment_report += "\nMONITORING DATA: Error fetching data\n"
            
            # Fetch maintenance logs
            try:
                maintenance_response = ctrl.fetch_equipment_maintenance_logs(serial_number)
                maintenance_logs = maintenance_response.get("maintenance_logs", [])
                
                if maintenance_logs:
                    equipment_report += f"\nMAINTENANCE HISTORY ({len(maintenance_logs)} records):\n"
                    # Show only the latest 3 for brevity in batch mode
                    for i, log in enumerate(maintenance_logs[:3], 1):
                        date = log.get('date_reported', 'Unknown')
                        issue = log.get('issue_description', 'No description')[:40]
                        severity = log.get('severity', 'Unknown')
                        equipment_report += f"  {i}. Date: {date}, Issue: {issue}..., Severity: {severity}\n"
                else:
                    equipment_report += "\nMAINTENANCE HISTORY: No records found\n"
            except Exception as e:
                equipment_report += "\nMAINTENANCE HISTORY: Error fetching data\n"
            
            detailed_reports.append(equipment_report)
        
        # Compile final report
        full_report = f"COMPREHENSIVE EQUIPMENT DETAILS REPORT\n{'='*70}\n"
        full_report += f"Total Equipment: {total_equipments}\n"
        full_report += f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        full_report += "=" * 70
        
        for report in detailed_reports:
            full_report += report
        
        full_report += f"\n{'='*60}\nEND OF REPORT\n{'='*60}"
        
        # Create summary statistics
        equipment_with_monitoring = 0
        equipment_with_maintenance = 0
        
        for eq in all_equipments_data:
            serial = eq.get('serial')
            # Quick checks (simplified for batch mode)
            try:
                monitoring_response = ctrl.fetch_monitoring_log(serial)
                if monitoring_response.get("monitoring_data"):
                    equipment_with_monitoring += 1
            except:
                pass
            
            try:
                maintenance_response = ctrl.fetch_equipment_maintenance_logs(serial)
                if maintenance_response.get("maintenance_logs"):
                    equipment_with_maintenance += 1
            except:
                pass
        
        summary = f"\nSUMMARY STATISTICS:\n"
        summary += f"• Total Equipment: {total_equipments}\n"
        summary += f"• Equipment with Monitoring Data: {equipment_with_monitoring}\n"
        summary += f"• Equipment with Maintenance Records: {equipment_with_maintenance}\n"
        
        system_prompt = f"""{full_report}{summary}

        Please provide a comprehensive summary of all equipment based on the detailed report above.
        Focus on:
        1. Overall equipment status
        2. Key findings from monitoring data
        3. Maintenance status across all equipment
        4. Any equipment that needs attention

        IMPORTANT: Only reference data from the report above. Do not invent any information."""
        
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        
        # Store equipment objects
        equipments = [
            Equipment(
                serial=eq.get("serial", ""),
                name=eq.get("name"),
                type=eq.get("type"),
                maintenance_status=eq.get("maintenance_status", "not_needed")
            ) for eq in all_equipments_data
        ]
        
        return {
            "messages": [bot_response],
            "equipments": equipments,
            "summaries": [f"Generated detailed report for {total_equipments} equipment"],
            "batch_mode": True,
            "batch_results": detailed_reports
        }
        
    except Exception as e:
        print(f"Error in batch_equipment_details_node: {str(e)}")
        system_prompt = "I encountered an issue while generating the comprehensive equipment report. Please try again later."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response], "errors": [str(e)]}

# ============ NODE 6: LIST ALL MAINTENANCE ============
def list_all_maintenance_node(state: State) -> dict:
    """List all maintenance logs across all equipment"""
    try:
        # Fetch all maintenance logs
        maintenance_response = ctrl.fetch_maintenance_logs()
        all_maintenance_logs = maintenance_response.get("maintenance_logs", [])
        
        if not all_maintenance_logs:
            system_prompt = "There are no maintenance logs in the system. Please inform the user that no maintenance records are currently available."
            bot_response = llm.llm_model.invoke([
                {
                    "role": "system",
                    "content": system_prompt
                },
                *state["messages"][-1:]
            ])
            return {"messages": [bot_response]}
        
        # Organize by equipment
        maintenance_by_equipment = {}
        for log in all_maintenance_logs:
            serial = log.get('equipment_serial', 'Unknown')
            if serial not in maintenance_by_equipment:
                maintenance_by_equipment[serial] = []
            maintenance_by_equipment[serial].append(log)
        
        # Prepare maintenance report
        maintenance_report = f"ALL MAINTENANCE LOGS REPORT\n{'='*70}\n"
        maintenance_report += f"Total Maintenance Records: {len(all_maintenance_logs)}\n"
        maintenance_report += f"Equipment with Maintenance: {len(maintenance_by_equipment)}\n"
        maintenance_report += "=" * 70 + "\n"
        
        for idx, (serial, logs) in enumerate(maintenance_by_equipment.items(), 1):
            # Try to get equipment name
            equipment_name = "Unknown"
            try:
                eq_response = ctrl.fetch_equipment_by_serial(serial)
                if eq_response.get("equipment"):
                    equipment_name = eq_response["equipment"].get('name', 'Unknown')
            except:
                pass
            
            maintenance_report += f"\n{'='*60}\nEQUIPMENT {idx}: {serial} ({equipment_name})\n"
            maintenance_report += f"Total Records: {len(logs)}\n"
            maintenance_report += "-" * 40 + "\n"
            
            # Show latest logs for this equipment
            for i, log in enumerate(logs[:5], 1):
                date = log.get('date_reported', 'Unknown date')
                issue = log.get('issue_description', 'No description')[:60]
                severity = log.get('severity', 'Unknown')
                status = log.get('status', 'Unknown')
                maintenance_report += f"{i}. Date: {date}\n   Issue: {issue}\n   Severity: {severity}, Status: {status}\n\n"
            
            if len(logs) > 5:
                maintenance_report += f"... and {len(logs) - 5} more records\n"
        
        maintenance_report += f"\n{'='*60}\nEND OF MAINTENANCE REPORT\n{'='*60}"
        
        system_prompt = f"""{maintenance_report}

Please provide a summary of all maintenance logs.
Focus on:
1. Total maintenance records
2. Equipment with most maintenance
3. Recent maintenance activities
4. Any patterns or observations

IMPORTANT: Only reference data from the report above. Do not invent any information."""
        
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        
        return {
            "messages": [bot_response],
            "maintenance_logs": maintenance_by_equipment,
            "summaries": [f"Listed {len(all_maintenance_logs)} maintenance logs across {len(maintenance_by_equipment)} equipment"]
        }
        
    except Exception as e:
        print(f"Error in list_all_maintenance_node: {str(e)}")
        system_prompt = "I encountered an issue while fetching all maintenance logs. Please try again later."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response], "errors": [str(e)]}

# ============ NODE 7: LIST ALL MONITORING ============
def list_all_monitoring_node(state: State) -> dict:
    """List all monitoring data across all equipment"""
    try:
        # First get all equipment
        equipment_response = ctrl.fetch_all_equipments()
        all_equipments = equipment_response.get("equipments", [])
        
        if not all_equipments:
            system_prompt = "There are no equipments in the system, so no monitoring data is available."
            bot_response = llm.llm_model.invoke([
                {
                    "role": "system",
                    "content": system_prompt
                },
                *state["messages"][-1:]
            ])
            return {"messages": [bot_response]}
        
        # Collect monitoring data for each equipment
        monitoring_report = f"ALL MONITORING DATA REPORT\n{'='*70}\n"
        monitoring_report += f"Total Equipment: {len(all_equipments)}\n"
        monitoring_report += "=" * 70 + "\n"
        
        equipment_with_data = 0
        monitoring_by_equipment = {}
        
        for idx, equipment in enumerate(all_equipments, 1):
            serial = equipment.get('serial', f"Unknown-{idx}")
            name = equipment.get('name', 'Unknown')
            
            try:
                monitoring_response = ctrl.fetch_monitoring_log(serial)
                monitoring_data = monitoring_response.get("monitoring_data", {})
                
                if monitoring_data:
                    equipment_with_data += 1
                    monitoring_by_equipment[serial] = monitoring_data
                    
                    monitoring_report += f"\n{'='*60}\nEQUIPMENT {idx}: {serial} ({name})\n"
                    
                    if monitoring_data.get('timestamp'):
                        monitoring_report += f"Last Updated: {monitoring_data.get('timestamp')}\n"
                    
                    if monitoring_data.get('health_score') is not None:
                        health_score = monitoring_data.get('health_score')
                        status_indicator = "✅" if health_score >= 80 else "⚠️" if health_score >= 60 else "❌"
                        monitoring_report += f"Health Score: {health_score}/100 {status_indicator}\n"
                    
                    if monitoring_data.get('temperature') is not None:
                        monitoring_report += f"Temperature: {monitoring_data.get('temperature')}°C\n"
                    
                    if monitoring_data.get('pressure') is not None:
                        monitoring_report += f"Pressure: {monitoring_data.get('pressure')} psi\n"
                    
                    if monitoring_data.get('status'):
                        monitoring_report += f"Status: {monitoring_data.get('status')}\n"
                else:
                    monitoring_report += f"\n{'='*60}\nEQUIPMENT {idx}: {serial} ({name})\n"
                    monitoring_report += "Monitoring Data: Not available\n"
                    
            except Exception as e:
                monitoring_report += f"\n{'='*60}\nEQUIPMENT {idx}: {serial} ({name})\n"
                monitoring_report += f"Monitoring Data: Error fetching data\n"
        
        monitoring_report += f"\n{'='*60}\nSUMMARY\n{'='*60}\n"
        monitoring_report += f"Equipment with Monitoring Data: {equipment_with_data} of {len(all_equipments)}\n"
        monitoring_report += f"Equipment without Data: {len(all_equipments) - equipment_with_data}\n"
        monitoring_report += f"\n{'='*60}\nEND OF MONITORING REPORT\n{'='*60}"
        
        system_prompt = f"""{monitoring_report}

Please provide a summary of all monitoring data.
Focus on:
1. Overall health status of equipment
2. Equipment that needs attention (low health scores)
3. Data availability across equipment
4. Any concerning patterns in temperature/pressure

IMPORTANT: Only reference data from the report above. Do not invent any information."""
        
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        
        return {
            "messages": [bot_response],
            "monitoring_logs": monitoring_by_equipment,
            "summaries": [f"Listed monitoring data for {equipment_with_data} of {len(all_equipments)} equipment"]
        }
        
    except Exception as e:
        print(f"Error in list_all_monitoring_node: {str(e)}")
        system_prompt = "I encountered an issue while fetching all monitoring data. Please try again later."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response], "errors": [str(e)]}

# ============ NODE 8: MAINTENANCE QUERY ============
def maintenance_query_node(state: State) -> dict:
    """Handle maintenance-specific queries for specific equipment"""
    serial_number = state.get("serial_number")
    
    if not serial_number:
        system_prompt = "To check maintenance records, I need the equipment serial number. Please provide the serial number (e.g., 'What is the maintenance history for serial ABC123?')."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response]}
    
    try:
        # First check if equipment exists
        equipment_response = ctrl.fetch_equipment_by_serial(serial_number)
        equipment_data = equipment_response.get("equipment", {})
        
        if not equipment_data:
            system_prompt = f"Equipment with serial number '{serial_number}' was not found in the system. Please inform the user that this equipment does not exist."
            bot_response = llm.llm_model.invoke([
                {
                    "role": "system",
                    "content": system_prompt
                },
                *state["messages"][-1:]
            ])
            return {"messages": [bot_response]}
        
        # Equipment exists, fetch maintenance logs
        maintenance_response = ctrl.fetch_equipment_maintenance_logs(serial_number)
        maintenance_logs = maintenance_response.get("maintenance_logs", [])
        
        equipment_name = equipment_data.get('name', serial_number)
        
        if not maintenance_logs:
            system_prompt = f"No maintenance records found for equipment '{equipment_name}' (Serial: {serial_number}). Please inform the user that there are no maintenance records available for this equipment."
        else:
            # Format maintenance information
            maintenance_info = f"MAINTENANCE RECORDS for {equipment_name} (Serial: {serial_number}):\n\n"
            maintenance_info += f"Total records: {len(maintenance_logs)}\n\n"
            
            for i, log in enumerate(maintenance_logs[:10], 1):
                date = log.get('date_reported', 'Unknown date')
                issue = log.get('issue_description', 'No description')
                severity = log.get('severity', 'Unknown')
                status = log.get('status', 'Unknown')
                maintenance_info += f"{i}. Date: {date}\n   Issue: {issue}\n   Severity: {severity}\n   Status: {status}\n\n"
            
            if len(maintenance_logs) > 10:
                maintenance_info += f"... and {len(maintenance_logs) - 10} more records"
            
            system_prompt = f"""{maintenance_info}

Provide this maintenance information to the user. 
IMPORTANT: Only mention what's in the data above. Do not invent or assume any additional maintenance records."""
        
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        
        return {"messages": [bot_response]}
        
    except Exception as e:
        print(f"Error in maintenance_query_node: {str(e)}")
        system_prompt = f"Unable to retrieve maintenance data for equipment {serial_number}. Please inform the user that maintenance data is currently unavailable."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response]}

# ============ NODE 9: MONITORING QUERY ============
def monitoring_query_node(state: State) -> dict:
    """Handle monitoring-specific queries for specific equipment"""
    serial_number = state.get("serial_number")
    
    if not serial_number:
        system_prompt = "To check monitoring data, I need the equipment serial number. Please provide the serial number (e.g., 'What is the health status for serial ABC123?')."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response]}
    
    try:
        # First check if equipment exists
        equipment_response = ctrl.fetch_equipment_by_serial(serial_number)
        equipment_data = equipment_response.get("equipment", {})
        
        if not equipment_data:
            system_prompt = f"Equipment with serial number '{serial_number}' was not found in the system. Please inform the user that this equipment does not exist."
            bot_response = llm.llm_model.invoke([
                {
                    "role": "system",
                    "content": system_prompt
                },
                *state["messages"][-1:]
            ])
            return {"messages": [bot_response]}
        
        # Equipment exists, fetch monitoring data
        monitoring_response = ctrl.fetch_monitoring_log(serial_number)
        monitoring_data = monitoring_response.get("monitoring_data", {})
        
        equipment_name = equipment_data.get('name', serial_number)
        
        if not monitoring_data:
            system_prompt = f"No monitoring data available for equipment '{equipment_name}' (Serial: {serial_number}). Please inform the user that monitoring data is not currently available for this equipment."
        else:
            # Format monitoring information
            monitoring_info = f"MONITORING DATA for {equipment_name} (Serial: {serial_number}):\n\n"
            
            if monitoring_data.get('timestamp'):
                monitoring_info += f"• Last Updated: {monitoring_data.get('timestamp')}\n"
            if monitoring_data.get('health_score') is not None:
                monitoring_info += f"• Health Score: {monitoring_data.get('health_score')}/100\n"
            if monitoring_data.get('temperature') is not None:
                monitoring_info += f"• Temperature: {monitoring_data.get('temperature')}°C\n"
            if monitoring_data.get('pressure') is not None:
                monitoring_info += f"• Pressure: {monitoring_data.get('pressure')} psi\n"
            if monitoring_data.get('vibration') is not None:
                monitoring_info += f"• Vibration: {monitoring_data.get('vibration')} mm/s\n"
            if monitoring_data.get('status'):
                monitoring_info += f"• Overall Status: {monitoring_data.get('status')}\n"
            
            system_prompt = f"""{monitoring_info}

Provide this monitoring information to the user.
IMPORTANT: Only mention what's in the data above. Do not invent or assume any additional monitoring data."""
        
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        
        return {"messages": [bot_response]}
        
    except Exception as e:
        print(f"Error in monitoring_query_node: {str(e)}")
        system_prompt = f"Unable to retrieve monitoring data for equipment {serial_number}. Please inform the user that monitoring data is currently unavailable."
        bot_response = llm.llm_model.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            *state["messages"][-1:]
        ])
        return {"messages": [bot_response]}

# ============ ROUTING LOGIC ============
def route_after_intent(state: State) -> str:
    """Determine which node to go to based on intent"""
    intent = state.get("intent", "general_chat")
    
    # Map intent to node names
    routing = {
        "general_chat": "general_chat_node",
        "list_equipments": "list_equipments_node",
        "fetch_equipment_details_node": "fetch_equipment_details_node",
        "maintenance_query": "maintenance_query_node",
        "monitoring_query": "monitoring_query_node",
        "batch_equipment_details": "batch_equipment_details_node",
        "list_all_maintenance": "list_all_maintenance_node",
        "list_all_monitoring": "list_all_monitoring_node"
    }
    
    return routing.get(intent, "general_chat_node")

# ============ BUILD THE GRAPH ============
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("intent_classifier", intent_classifier_node)
graph_builder.add_node("general_chat_node", general_chat_node)
graph_builder.add_node("list_equipments_node", list_equipments_node)
graph_builder.add_node("fetch_equipment_details_node", fetch_equipment_details_node)
graph_builder.add_node("maintenance_query_node", maintenance_query_node)
graph_builder.add_node("monitoring_query_node", monitoring_query_node)
graph_builder.add_node("batch_equipment_details_node", batch_equipment_details_node)
graph_builder.add_node("list_all_maintenance_node", list_all_maintenance_node)
graph_builder.add_node("list_all_monitoring_node", list_all_monitoring_node)

# Add edges
graph_builder.add_edge(START, "intent_classifier")
graph_builder.add_conditional_edges(
    "intent_classifier",
    route_after_intent,
    {
        "general_chat_node": "general_chat_node",
        "list_equipments_node": "list_equipments_node",
        "fetch_equipment_details_node": "fetch_equipment_details_node",
        "maintenance_query_node": "maintenance_query_node",
        "monitoring_query_node": "monitoring_query_node",
        "batch_equipment_details_node": "batch_equipment_details_node",
        "list_all_maintenance_node": "list_all_maintenance_node",
        "list_all_monitoring_node": "list_all_monitoring_node"
    }
)

# All nodes end here
graph_builder.add_edge("general_chat_node", END)
graph_builder.add_edge("list_equipments_node", END)
graph_builder.add_edge("fetch_equipment_details_node", END)
graph_builder.add_edge("maintenance_query_node", END)
graph_builder.add_edge("monitoring_query_node", END)
graph_builder.add_edge("batch_equipment_details_node", END)
graph_builder.add_edge("list_all_maintenance_node", END)
graph_builder.add_edge("list_all_monitoring_node", END)

graph = graph_builder.compile()

# ============ CHAT INTERFACE ============
state = {
    "messages": [],
    "intent": None,
    "equipments": None,
    "monitoring_logs": None,
    "maintenance_logs": None,
    "equipment_query": None,
    "serial_number": None,
    "query_type": None,
    "has_specific_equipment": False,
    "batch_mode": False,
    "current_batch_index": 0,
    "batch_results": []
}

def chat_model(message: str):
    global state
    
    state["user_prompt"] = message
    
    # Add user message
    user_message = {"role": "user", "content": message}
    if "messages" not in state:
        state["messages"] = []
    state["messages"].append(user_message)
    
    # Invoke the graph
    result = graph.invoke(state)
    
    # Update state with result (but keep message history)
    if "messages" in result:
        # Add bot response to messages
        state["messages"].append(result["messages"][-1])
    else:
        # Update other fields
        for key, value in result.items():
            if key != "messages":
                state[key] = value
    
    # Get the last message (bot response)
    if state.get("messages"):
        last_message = state["messages"][-1]
        if hasattr(last_message, 'model_dump'):
            out_res = last_message.model_dump()
        else:
            out_res = last_message
        
        response = out_res.get("content", "") if isinstance(out_res, dict) else str(out_res)
    else:
        response = "I apologize, but I couldn't generate a response."
    
    return response