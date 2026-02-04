from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import date, datetime, timedelta
from typing import Optional
import re
import json
import os
from dotenv import load_dotenv

from ..LLM_Model import llm_config as llm
from ..LLM_Model import chatbot as cb
from ..LLM_Model import agents as agt
from ..LLM_Model import validate_maintenance as mval
from ..Model import equipments as eq
from ..Embedd import vecor_embedd as embedd
from ..Embedd import vector_query as vector

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Equipment name")
    manufacturer: str = Field(..., min_length=1, max_length=100, description="Manufacturer name")
    model: str = Field(..., min_length=1, max_length=50, description="Model number")
    serial: str = Field(..., min_length=1, max_length=50, description="Serial number")
    installation_date: date = Field(..., description="Date when equipment was installed")
    location: str = Field(..., min_length=1, max_length=200, description="Location of equipment")
    status: str = Field(..., pattern="^(operating|under_maintenance|out_of_service)$", description="Status of the equipment")
    maintenance_status: str = Field(..., pattern="^(not_needed|pending|in_progress|completed|overdue)$", description="Maintenance status of the equipment")

class MaintenanceLogBase(BaseModel):
    raised_by: str = Field(..., min_length=1, max_length=100, description="Name of the person who raised the log")
    equipment_serial: str = Field(..., min_length=1, max_length=50, description="Serial number of the equipment")
    issue_description: str = Field(..., min_length=1, description="Description of the issue")
    date_reported: date = Field(..., description="Date when the issue was reported")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$", description="Severity of the issue")
    date_predicted: Optional[date] = Field(None, description="Predicted date of resolution")
    
class MonitoringLogsBase(BaseModel):
    equipment_serial: str = Field(..., min_length=1, max_length=50, description="Serial number of the equipment")
    timestamp: Optional[date] = Field(None, description="Timestamp of the monitoring data")
    status: str = Field(..., min_length=1, max_length=50, description="Status of the equipment")
    reading_type: str = Field(..., min_length=1, max_length=100, description="Type of reading")
    value: float = Field(..., description="Value of the reading")
    unit: str = Field(..., min_length=1, max_length=20, description="Unit of the reading")
    location: str = Field(..., min_length=1, max_length=200, description="Location of the equipment")
    threshold_min: Optional[float] = Field(None, description="Minimum threshold value")
    threshold_max: Optional[float] = Field(None, description="Maximum threshold value")

@app.get("/")
def root():
    return {
        "message": "Help"
    }

@app.post("/response", tags=["AI_Analysis"])
def response(input : str):
    user_prompt = input
    out_res = cb.chat_model(user_prompt)
    
    return {
        "message": out_res
    }
    
@app.get("/equipments/list_all", tags=["Equipments"])
def fetch_all_equipments():
    result = eq.list_equipments()
    equipments_list = []
    for row in result:
        equipment = {
            "id": row.id,
            "name": row.name,
            "manufacturer": row.manufacturer,
            "model": row.model,
            "serial": row.serial,
            "installation_date": str(row.installation_date),
            "location": row.location,
            "status": row.status,
            "maintenance_status": row.maintenance_status
        }
        equipments_list.append(equipment)
    return {
        "equipments": equipments_list
    }

@app.patch("/equipments/update_status/{serial_number}", tags=["Equipments"])
def update_equipment_status(serial_number: str, status: Optional[str], maintenance_status:Optional[str]):
    try:
        eq.update_equipment_status(serial_number, status, maintenance_status)
        return {
            "message": f"Equipment status updated to {status} successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/equipments/serial/{serial_number}", tags=["Equipments"])
def fetch_equipment_by_serial(serial_number: str):
    row = eq.select_equipment(serial_number)
    if row is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    equipment = {
        "id": row.id,
        "name": row.name,
        "manufacturer": row.manufacturer,
        "model": row.model,
        "serial": row.serial,
        "installation_date": str(row.installation_date),
        "location": row.location,
        "status": row.status,
        "maintenance_status": row.maintenance_status
    }
    return {
        "equipment": equipment
    }
    
@app.post("/equipments/add", tags=["Equipments"])
def add_equipments(equipment: EquipmentBase):
    
    try:
        eq.insert_equipments(equipment.name, equipment.manufacturer, equipment.model, equipment.serial, str(equipment.installation_date), equipment.location)
        return{
            "messages": equipment
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/list_all", tags=["Monitoring"])
def fetch_all_monitoring_data():
    result = eq.list_all_monitoring_data()
    print("hlo")
    monitoring_list = []
    for row in result:
        monitoring = {
            "id": row.id,
            "equipment_serial": row.equipment_serial,
            "timestamp": str(row.timestamp),
            "status": row.status,
            "reading_type": row.reading_type,
            "value": row.value,
            "unit": row.unit,
            "location": row.location,
            "threshold_min": row.threshold_min,
            "threshold_max": row.threshold_max
        }
        monitoring_list.append(monitoring)
    return {
        "monitoring_data": monitoring_list
    }

@app.post("/monitoring/{equipment_serial}", tags=["Monitoring"])
def fetch_monitoring_log(equipment_serial: str):
    result = eq.list_equipment_monitoring_data(equipment_serial)
    monitoring_list = []
    for row in result:
        monitoring = {
            "id": row.id,
            "equipment_serial": row.equipment_serial,
            "timestamp": str(row.timestamp),
            "status": row.status,
            "reading_type": row.reading_type,
            "value": row.value,
            "unit": row.unit,
            "location": row.location,
            "threshold_min": row.threshold_min,
            "threshold_max": row.threshold_max
        }
        monitoring_list.append(monitoring)
    return {
        "monitoring_data": monitoring_list
    }
    
@app.put("/monitoring/add", tags=["Monitoring"])
def add_monitoring_logs(monitoring: MonitoringLogsBase):
    
    print("hi")
    
    try:
        base_time = datetime.utcnow()
        
        eq.insert_monitoring_data(
            monitoring.equipment_serial,
            monitoring.reading_type,
            monitoring.value,
            monitoring.unit,
            monitoring.location,
            monitoring.status,
            str(monitoring.timestamp) if monitoring.timestamp else None,
            monitoring.threshold_min,
            monitoring.threshold_max
        )
        
        
        return {
            "message": "Monitoring data added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/maintenance/logs", tags=["Maintenance"])
def fetch_maintenance_logs():
    result = eq.list_maintenance_logs()
    maintenance_list = []
    for row in result:
        maintenance = {
            "id": row.id,
            "raised_by": row.raised_by,
            "equipment_serial": row.equipment_serial,
            "issue_description": row.issue_description,
            "date_reported": str(row.date_reported),
            "severity": row.severity,
            "date_resolved": str(row.date_resolved) if row.date_resolved else None,
            "date_predicted": str(row.date_predicted) if row.date_predicted else None,
            "status": row.status
        }
        maintenance_list.append(maintenance)
    return {
        "maintenance_logs": maintenance_list
    }
    
@app.get("/maintenance/logs/open", tags=["Maintenance"])
def fetch_maintenance_logs_open():
    result = eq.list_maintenance_logs_open()
    maintenance_list = []
    for row in result:
        maintenance = {
            "id": row.id,
            "raised_by": row.raised_by,
            "equipment_serial": row.equipment_serial,
            "issue_description": row.issue_description,
            "date_reported": str(row.date_reported),
            "severity": row.severity,
            "date_resolved": str(row.date_resolved) if row.date_resolved else None,
            "date_predicted": str(row.date_predicted) if row.date_predicted else None
        }
        maintenance_list.append(maintenance)
    return {
        "maintenance_logs": maintenance_list
    }

@app.post("/maintenance/log/{id}", tags=["Maintenance"])
def fetch_maintenance_log(id: int): 
    row = eq.select_maintenance_log(id)
    if row is None:
        raise HTTPException(status_code=404, detail="Maintenance log not found")
    maintenance = {
        "id": row.id,
        "raised_by": row.raised_by,
        "equipment_serial": row.equipment_serial,
        "issue_description": row.issue_description,
        "date_reported": str(row.date_reported),
        "severity": row.severity,
        "date_predicted": str(row.date_predicted) if row.date_predicted else None
    }
    return {
        "maintenance_log": maintenance
    }

@app.post("/maintenance/logs/{equipment_serial}", tags=["Maintenance"])
def fetch_equipment_maintenance_logs(equipment_serial: str):
    result = eq.list_equipment_maintenance_logs(equipment_serial)
    maintenance_list = []
    for row in result:
        maintenance = {
            "id": row.id,
            "raised_by": row.raised_by,
            "equipment_serial": row.equipment_serial,
            "issue_description": row.issue_description,
            "date_reported": str(row.date_reported),
            "date_resolved": str(row.date_resolved) if row.date_resolved else None,
            "severity": row.severity,
            "date_predicted": str(row.date_predicted) if row.date_predicted else None
        }
        maintenance_list.append(maintenance)
    return {
        "maintenance_logs": maintenance_list
    }
    
@app.put("/maintenance/logs/add", tags=["Maintenance"])
def add_maintenance_log(log: MaintenanceLogBase):
    

    # eq.insert_maintenance_log(
    #     raised_by="Installation Team",
    #     equipment_serial="AC2022-34567",
    #     issue_description="Initial installation of screw compressor system. Complete assembly, electrical connections, and pressure testing.",
    #     severity="low",
    #     date_reported="2022-01-10",
    #     date_resolved="2022-01-15",  # 5 days interval
    #     status="closed"
    # )

    # # 2. Oil Separator Replacement - 8 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Pressure Monitoring System",
    #     equipment_serial="AC2022-34567",
    #     issue_description="Oil separator clogging detected. Pressure differential increased to 1.1 bar (normal: 0.5 bar). Reduced efficiency and oil carry-over.",
    #     severity="high",
    #     date_reported="2023-06-20",
    #     date_resolved="2023-06-28",  # 8 days interval
    #     status="closed"
    # )

    # # 3. Belt and Bearing Maintenance - 12 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Preventive Maintenance Schedule",
    #     equipment_serial="AC2022-34567",
    #     issue_description="Scheduled belt tension adjustment and bearing inspection. Belt wear detected, bearing lubrication required.",
    #     severity="medium",
    #     date_reported="2023-10-01",
    #     date_resolved="2023-10-13",  # 12 days interval
    #     status="closed"
    # )

    # # 4. Air Filter Replacement - 6 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Air Flow Monitoring",
    #     equipment_serial="AC2022-34567",
    #     issue_description="Air filter pressure drop at 350 Pa (warning: 500 Pa). Reduced airflow affecting compressor efficiency.",
    #     severity="medium",
    #     date_reported="2023-03-10",
    #     date_resolved="2023-03-16",  # 6 days interval
    #     status="closed"
    # )

    # # 5. Current Bearing Issue - Open for 18 days
    # eq.insert_maintenance_log(
    #     raised_by="Vibration Analysis System",
    #     equipment_serial="AC2022-34567",
    #     issue_description="Motor NDE bearing vibration at 4.2 mm/s (warning level: 4.0 mm/s). Temperature rising trend observed. Requires bearing inspection and possible replacement.",
    #     severity="high",
    #     date_reported="2024-01-10",
    #     date_resolved="2024-01-28",  # 18 days interval
    #     status="closed"
    # )          
            
    #         # 1. Initial Commissioning - 7 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Commissioning Team",
    #     equipment_serial="BAC2021-78901",
    #     issue_description="Initial commissioning of cooling tower system. Water flow testing, fan alignment, and control system calibration.",
    #     severity="low",
    #     date_reported="2021-04-05",
    #     date_resolved="2021-04-12",  # 7 days interval
    #     status="closed"
    # )

    # # 2. Fan Bearing Replacement - 15 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Vibration Monitoring",
    #     equipment_serial="BAC2021-78901",
    #     issue_description="Fan shaft bearing vibration at 4.5 mm/s (warning level). Bearing wear detected during inspection. Complete bearing replacement required.",
    #     severity="critical",
    #     date_reported="2023-05-15",
    #     date_resolved="2023-05-30",  # 15 days interval
    #     status="closed"
    # )

    # # 3. Gearbox Oil Service - 10 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Temperature Monitoring",
    #     equipment_serial="BAC2021-78901",
    #     issue_description="Gearbox oil temperature at 68°C (above normal range). Oil analysis shows contamination. Oil change and filter replacement required.",
    #     severity="high",
    #     date_reported="2023-02-10",
    #     date_resolved="2023-02-20",  # 10 days interval
    #     status="closed"
    # )

    # # 4. Water Treatment System - 25 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Water Quality Analysis",
    #     equipment_serial="BAC2021-78901",
    #     issue_description="Water chemistry imbalance detected. High biological activity at 8×10⁴ cfu/ml. Requires chemical treatment and system cleaning.",
    #     severity="medium",
    #     date_reported="2023-09-15",
    #     date_resolved="2023-10-10",  # 25 days interval
    #     status="closed"
    # )

    # # 5. Fill Material Inspection - 20 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Annual Inspection",
    #     equipment_serial="BAC2021-78901",
    #     issue_description="Fill material degradation detected. Current thickness at 0.6 mm (from 0.8 mm new). Reduced cooling efficiency observed.",
    #     severity="medium",
    #     date_reported="2024-01-15",
    #     date_resolved="2024-02-04",  # 20 days interval
    #     status="closed"
    # )

    # # 1. Initial Installation - 6 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Installation Team",
    #     equipment_serial="TR2020-45678",
    #     issue_description="Initial installation and commissioning of centrifugal chiller. Refrigerant charging, electrical connections, and system testing.",
    #     severity="low",
    #     date_reported="2020-08-20",
    #     date_resolved="2020-08-26",  # 6 days interval
    #     status="closed"
    # )

    # # 2. Compressor Bearing Issue - 18 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Vibration Analysis System",
    #     equipment_serial="TR2020-45678",
    #     issue_description="Compressor NDE bearing vibration at 4.1 mm/s (warning level). Bearing wear detected, requires inspection and possible replacement.",
    #     severity="high",
    #     date_reported="2024-01-10",
    #     date_resolved="2024-01-28",  # 18 days interval
    #     status="closed"
    # )

    # # 3. Starter Contact Replacement - 12 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Electrical Inspection",
    #     equipment_serial="TR2020-45678",
    #     issue_description="Starter contacts showing signs of arcing and wear. Motor starting issues observed during operation.",
    #     severity="medium",
    #     date_reported="2023-07-05",
    #     date_resolved="2023-07-17",  # 12 days interval
    #     status="closed"
    # )

    # # 4. Water Tube Cleaning - 15 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Performance Monitoring",
    #     equipment_serial="TR2020-45678",
    #     issue_description="Reduced heat transfer efficiency. Condenser approach temperature increased to 2.8°C (design: 2°C). Requires tube cleaning.",
    #     severity="medium",
    #     date_reported="2023-10-15",
    #     date_resolved="2023-10-30",  # 15 days interval
    #     status="closed"
    # )

    # # 5. Oil System Service - 9 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Oil Analysis Report",
    #     equipment_serial="TR2020-45678",
    #     issue_description="Oil analysis shows iron content at 8 ppm (warning: 5 ppm). Oil filter pressure differential at 1.2 bar. Requires oil change and filter replacement.",
    #     severity="medium",
    #     date_reported="2023-04-10",
    #     date_resolved="2023-04-19",  # 9 days interval
    #     status="closed"
    # )

    # # 1. Initial Setup - 8 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Installation Team",
    #     equipment_serial="CM2019-23456",
    #     issue_description="Initial installation and setup of diesel generator. Fuel system connection, electrical wiring, and load testing.",
    #     severity="low",
    #     date_reported="2019-11-12",
    #     date_resolved="2019-11-20",  # 8 days interval
    #     status="closed"
    # )

    # # 2. Engine Bearing Vibration - 22 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Monthly Inspection",
    #     equipment_serial="CM2019-23456",
    #     issue_description="Front engine bearing vibration at 4.8 mm/s (warning level). Engine mount inspection required.",
    #     severity="medium",
    #     date_reported="2024-01-05",
    #     date_resolved="2024-01-27",  # 22 days interval
    #     status="closed"
    # )

    # # 3. Starter Motor Replacement - 14 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Load Test Report",
    #     equipment_serial="CM2019-23456",
    #     issue_description="Starter motor failure during monthly load test. Extended starting time observed.",
    #     severity="high",
    #     date_reported="2023-05-15",
    #     date_resolved="2023-05-29",  # 14 days interval
    #     status="closed"
    # )

    # # 4. Battery System Issue - 11 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Battery Monitoring",
    #     equipment_serial="CM2019-23456",
    #     issue_description="Battery voltage dropping below minimum during start tests. Battery health at 65% of original capacity.",
    #     severity="critical",
    #     date_reported="2024-01-10",
    #     date_resolved="2024-01-21",  # 11 days interval
    #     status="closed"
    # )

    # # 5. Cooling System Maintenance - 17 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Preventive Maintenance",
    #     equipment_serial="CM2019-23456",
    #     issue_description="Coolant system flush and replacement. Thermostat inspection and belt tension adjustment.",
    #     severity="low",
    #     date_reported="2023-08-10",
    #     date_resolved="2023-08-27",  # 17 days interval
    #     status="closed"
    # )

    # # 1. Initial Commissioning - 10 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Commissioning Team",
    #     equipment_serial="CB2021-34567",
    #     issue_description="Initial commissioning of boiler system. Pressure testing, burner calibration, and safety valve setting.",
    #     severity="low",
    #     date_reported="2021-02-18",
    #     date_resolved="2021-02-28",  # 10 days interval
    #     status="closed"
    # )

    # # 2. Feed Pump Bearing Issue - 16 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Vibration Monitoring",
    #     equipment_serial="CB2021-34567",
    #     issue_description="Feed pump bearing vibration at 4.2 mm/s (warning level). Pump efficiency decreasing, requires bearing inspection.",
    #     severity="high",
    #     date_reported="2024-01-15",
    #     date_resolved="2024-01-31",  # 16 days interval
    #     status="closed"
    # )

    # # 3. Burner Nozzle Replacement - 13 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Operational Efficiency Report",
    #     equipment_serial="CB2021-34567",
    #     issue_description="Burner nozzle wear affecting combustion efficiency. Increased fuel consumption observed.",
    #     severity="medium",
    #     date_reported="2023-06-20",
    #     date_resolved="2023-07-03",  # 13 days interval
    #     status="closed"
    # )

    # # 4. Safety Valve Testing - 7 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Annual Safety Inspection",
    #     equipment_serial="CB2021-34567",
    #     issue_description="Routine safety valve testing and calibration. All valves tested within specifications.",
    #     severity="low",
    #     date_reported="2023-03-08",
    #     date_resolved="2023-03-15",  # 7 days interval
    #     status="closed"
    # )

    # # 5. Tube Inspection & Cleaning - 21 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Preventive Maintenance",
    #     equipment_serial="CB2021-34567",
    #     issue_description="Annual tube inspection and cleaning. Minor scaling detected, chemical cleaning required.",
    #     severity="medium",
    #     date_reported="2023-10-05",
    #     date_resolved="2023-10-26",  # 21 days interval
    #     status="closed"
    # )

    # # 1. Initial Delivery & Setup - 5 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Delivery Team",
    #     equipment_serial="TOY2022-84521",
    #     issue_description="Initial delivery and setup of electric forklift. Battery installation, system check, and operator training.",
    #     severity="low",
    #     date_reported="2022-06-01",
    #     date_resolved="2022-06-06",  # 5 days interval
    #     status="closed"
    # )

    # # 2. Hydraulic System Overheating - 14 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Operator Report",
    #     equipment_serial="TOY2022-84521",
    #     issue_description="Hydraulic oil temperature at 52°C (above normal range). Cooling system inspection required.",
    #     severity="medium",
    #     date_reported="2024-01-20",
    #     date_resolved="2024-02-03",  # 14 days interval
    #     status="closed"
    # )

    # # 3. Drive Motor Brush Replacement - 9 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Scheduled Maintenance",
    #     equipment_serial="TOY2022-84521",
    #     issue_description="Drive motor brush wear at 60% remaining life. Preventive replacement scheduled.",
    #     severity="low",
    #     date_reported="2023-03-15",
    #     date_resolved="2023-03-24",  # 9 days interval
    #     status="closed"
    # )

    # # 4. Tire Replacement - 12 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Wear Inspection",
    #     equipment_serial="TOY2022-84521",
    #     issue_description="Tire wear beyond safety limits. Tread depth at 5mm (minimum: 5mm). All four tires require replacement.",
    #     severity="medium",
    #     date_reported="2023-07-05",
    #     date_resolved="2023-07-17",  # 12 days interval
    #     status="closed"
    # )

    # # 5. Battery Health Check - 18 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Battery Monitoring System",
    #     equipment_serial="TOY2022-84521",
    #     issue_description="Battery State of Health at 82%. Requires equalization charging and cell balancing.",
    #     severity="low",
    #     date_reported="2023-11-10",
    #     date_resolved="2023-11-28",  # 18 days interval
    #     status="closed"
    # )

    # # 1. Initial Installation - 8 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Installation Team",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Initial installation and commissioning of conveyor system. Alignment, tensioning, and speed calibration.",
    #     severity="low",
    #     date_reported="2021-09-15",
    #     date_resolved="2021-09-23",  # 8 days interval
    #     status="closed"
    # )

    # # 2. Drive Motor Bearing Replacement - 16 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Vibration Analysis",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Drive motor bearing vibration at warning level. Bearing wear detected during inspection.",
    #     severity="high",
    #     date_reported="2023-12-01",
    #     date_resolved="2023-12-17",  # 16 days interval
    #     status="closed"
    # )

    # # 3. Roller Replacement - 11 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Routine Inspection",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Multiple rollers failed (8 units). Reduced rotation affecting belt tracking and load capacity.",
    #     severity="medium",
    #     date_reported="2023-04-20",
    #     date_resolved="2023-05-01",  # 11 days interval
    #     status="closed"
    # )

    # # 4. Gearbox Oil Service - 7 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Scheduled Maintenance",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Gearbox oil change and filter replacement. Oil analysis shows normal wear.",
    #     severity="low",
    #     date_reported="2023-08-10",
    #     date_resolved="2023-08-17",  # 7 days interval
    #     status="closed"
    # )

    # # 5. Belt Tracking Adjustment - 5 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Operational Monitoring",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Belt tracking deviation detected. Minor adjustment required to prevent edge wear.",
    #     severity="low",
    #     date_reported="2024-01-15",
    #     date_resolved="2024-01-20",  # 5 days interval
    #     status="closed"
    # )

    # # 1. Initial Installation - 8 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Installation Team",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Initial installation and commissioning of conveyor system. Alignment, tensioning, and speed calibration.",
    #     severity="low",
    #     date_reported="2021-09-15",
    #     date_resolved="2021-09-23",  # 8 days interval
    #     status="closed"
    # )

    # # 2. Drive Motor Bearing Replacement - 16 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Vibration Analysis",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Drive motor bearing vibration at warning level. Bearing wear detected during inspection.",
    #     severity="high",
    #     date_reported="2023-12-01",
    #     date_resolved="2023-12-17",  # 16 days interval
    #     status="closed"
    # )

    # # 3. Roller Replacement - 11 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Routine Inspection",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Multiple rollers failed (8 units). Reduced rotation affecting belt tracking and load capacity.",
    #     severity="medium",
    #     date_reported="2023-04-20",
    #     date_resolved="2023-05-01",  # 11 days interval
    #     status="closed"
    # )

    # # 4. Gearbox Oil Service - 7 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Scheduled Maintenance",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Gearbox oil change and filter replacement. Oil analysis shows normal wear.",
    #     severity="low",
    #     date_reported="2023-08-10",
    #     date_resolved="2023-08-17",  # 7 days interval
    #     status="closed"
    # )

    # # 5. Belt Tracking Adjustment - 5 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Operational Monitoring",
    #     equipment_serial="INT2021-95623",
    #     issue_description="Belt tracking deviation detected. Minor adjustment required to prevent edge wear.",
    #     severity="low",
    #     date_reported="2024-01-15",
    #     date_resolved="2024-01-20",  # 5 days interval
    #     status="closed"
    # )

    # # 1. Initial Setup - 6 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Implementation Team",
    #     equipment_serial="DEM2023-14785",
    #     issue_description="Initial AGV setup and mapping. Path programming, sensor calibration, and system integration.",
    #     severity="low",
    #     date_reported="2023-01-25",
    #     date_resolved="2023-01-31",  # 6 days interval
    #     status="closed"
    # )

    # # 2. LiDAR Calibration - 13 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Navigation Diagnostics",
    #     equipment_serial="DEM2023-14785",
    #     issue_description="Navigation accuracy drift detected. Requires LiDAR sensor calibration and mapping update.",
    #     severity="medium",
    #     date_reported="2023-12-05",
    #     date_resolved="2023-12-18",  # 13 days interval
    #     status="closed"
    # )

    # # 3. Drive Wheel Replacement - 10 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Wear Inspection",
    #     equipment_serial="DEM2023-14785",
    #     issue_description="Drive wheel wear beyond tolerance. Diameter reduced to 196mm (from 200mm new).",
    #     severity="medium",
    #     date_reported="2023-05-15",
    #     date_resolved="2023-05-25",  # 10 days interval
    #     status="closed"
    # )

    # # 4. Software Update - 4 days interval
    # eq.insert_maintenance_log(
    #     raised_by="IT Department",
    #     equipment_serial="DEM2023-14785",
    #     issue_description="AGV control software update. New features and bug fixes implementation.",
    #     severity="low",
    #     date_reported="2023-03-10",
    #     date_resolved="2023-03-14",  # 4 days interval
    #     status="closed"
    # )

    # # 5. Battery System Check - 15 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Preventive Maintenance",
    #     equipment_serial="DEM2023-14785",
    #     issue_description="Battery health check and charging system calibration. State of Health at 85%.",
    #     severity="low",
    #     date_reported="2023-09-05",
    #     date_resolved="2023-09-20",  # 15 days interval
    #     status="closed"
    # )

    # # 1. Initial Assembly - 12 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Assembly Team",
    #     equipment_serial="SK2020-63214",
    #     issue_description="Initial assembly of pallet racking system. Leveling, anchoring, and safety clip installation.",
    #     severity="low",
    #     date_reported="2020-03-10",
    #     date_resolved="2020-03-22",  # 12 days interval
    #     status="closed"
    # )

    # # 2. Structural Inspection - 21 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Quarterly Inspection",
    #     equipment_serial="SK2020-63214",
    #     issue_description="Comprehensive structural inspection. Minor forklift impact damage detected on beam level 3.",
    #     severity="critical",
    #     date_reported="2024-01-05",
    #     date_resolved="2024-01-26",  # 21 days interval
    #     status="closed"
    # )

    # # 3. Beam Replacement - 14 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Damage Assessment",
    #     equipment_serial="SK2020-63214",
    #     issue_description="Forklift impact damage on beam. Structural integrity compromised, requires beam replacement.",
    #     severity="high",
    #     date_reported="2023-05-15",
    #     date_resolved="2023-05-29",  # 14 days interval
    #     status="closed"
    # )

    # # 4. Anchor Bolt Re-torque - 9 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Safety Inspection",
    #     equipment_serial="SK2020-63214",
    #     issue_description="Anchor bolt torque check and re-torquing. Some bolts below specified torque values.",
    #     severity="medium",
    #     date_reported="2023-08-05",
    #     date_resolved="2023-08-14",  # 9 days interval
    #     status="closed"
    # )

    # # 5. Safety Clip Replacement - 7 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Routine Maintenance",
    #     equipment_serial="SK2020-63214",
    #     issue_description="Safety clip replacement due to wear and damage. 12 clips replaced across the system.",
    #     severity="low",
    #     date_reported="2023-11-10",
    #     date_resolved="2023-11-17",  # 7 days interval
    #     status="closed"
    # )

    # # 1. Initial Installation - 14 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Installation Team",
    #     equipment_serial="KR2022-87412",
    #     issue_description="Initial installation and commissioning of ASRS system. Mechanical assembly, electrical wiring, and software configuration.",
    #     severity="low",
    #     date_reported="2022-11-05",
    #     date_resolved="2022-11-19",  # 14 days interval
    #     status="closed"
    # )

    # # 2. Belt Tension Adjustment - 9 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Preventive Maintenance",
    #     equipment_serial="KR2022-87412",
    #     issue_description="Belt elongation at 1.5% (warning: 2%). Requires tension adjustment to maintain positioning accuracy.",
    #     severity="medium",
    #     date_reported="2024-01-15",
    #     date_resolved="2024-01-24",  # 9 days interval
    #     status="closed"
    # )

    # # 3. Encoder Replacement - 12 days interval
    # eq.insert_maintenance_log(
    #     raised_by="System Diagnostics",
    #     equipment_serial="KR2022-87412",
    #     issue_description="Positioning encoder failure. Signal quality dropped below 95%, affecting retrieval accuracy.",
    #     severity="high",
    #     date_reported="2023-05-15",
    #     date_resolved="2023-05-27",  # 12 days interval
    #     status="closed"
    # )

    # # 4. Guide Rail Maintenance - 18 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Vibration Analysis",
    #     equipment_serial="KR2022-87412",
    #     issue_description="Guide rail wear detected. Wear depth at 0.2mm, requires cleaning and alignment adjustment.",
    #     severity="medium",
    #     date_reported="2023-08-01",
    #     date_resolved="2023-08-19",  # 18 days interval
    #     status="closed"
    # )

    # # 5. Electrical System Check - 7 days interval
    # eq.insert_maintenance_log(
    #     raised_by="Scheduled Maintenance",
    #     equipment_serial="KR2022-87412",
    #     issue_description="Comprehensive electrical system inspection. Cable connections, sensors, and control system verification.",
    #     severity="low",
    #     date_reported="2023-11-01",
    #     date_resolved="2023-11-08",  # 7 days interval
    #     status="closed"
    # )


    
    try:
        print("hi: ", log.date_predicted)
        eq.insert_maintenance_log(
            log.raised_by,
            log.equipment_serial,
            log.issue_description,
            log.severity,
            log.date_reported if log.date_reported is not None else datetime.utcnow(),
            date_predicted = log.date_predicted if log.date_predicted is not None else None
        )
        
        return {
            "message": "Maintenance log added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Agentic Mamla

@app.get("/ai_analysis", tags=["AI_Analysis"])
def trigger_ai_analysis():
    
    response = agt.execute_maintenance_workflow()
    
    
    return {
        "message": "AI Analysis triggered successfully",
        "status": response
    }

@app.get("/ai_validation", tags=["AI_Analysis"])
def trigger_ai_validation():
    
    response = mval.get_validation_results()
    
    
    return {
        "message": "AI Validation triggered successfully",
        "status": response
    }

@app.get("/testing/agentlist", tags=["Agent Monitoring"])
def list_out_agents():
    
    agents = [
        {
            "name": "Predict Maintenance",
            "description": "An agent that predicts maintenance needs for equipment based on monitoring data and historical maintenance logs.",
            "endpoint": "http://127.0.0.1:8448/ai_analysis"
        },
        {
            "name": "Validate Maintenance",
            "description": "An agent that validates maintenance predictions and ensures accuracy.",
            "endpoint": "http://127.0.0.1:8448/ai_validation"
        },
        {
            "name": "Predictive Maintenance Chat Agent",
            "description": "An agent that provides chat-based predictive maintenance support.",
            "endpoint": "http://127.0.0.1:8448/response"
        }
    ]
    
    return {
        "agents": agents
    }
    

@app.get("/embedd_docs")
def embedd_safety_docs():
    
    try:
        embedd.save_vectors()
        
        return{
            "response":"vector embedded created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/retrieve_docs")
def retrieve(input:str):
    try:
        response = vector.ask_question(input)
        
        return{
            "response" : response
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class ChunkInput(BaseModel):
    input: str = Field(..., min_length=1, description="User Input")
    
    
@app.post("/retrieve_chunks", tags=["Embedds"])
def retrieve_chunk(user_input:ChunkInput):
    try:
    
        response = vector.get_retrieved_chunk(user_input.input)
        
        return{
            "response" : response
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))