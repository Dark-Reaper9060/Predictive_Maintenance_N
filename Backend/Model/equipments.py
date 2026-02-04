import sqlalchemy as sql
from datetime import datetime

DB_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/maintenance_equipments"

engine = sql.create_engine(DB_URL)

connection = engine.connect()

metadata = sql.MetaData()

equipment_table = sql.Table(
    "equipments",
    metadata,
    sql.Column("id", sql.Integer, primary_key = True),
    sql.Column("name", sql.String, nullable = False),
    sql.Column("manufacturer", sql.String, nullable = False),
    sql.Column("model", sql.String,nullable=False),
    sql.Column("serial", sql.String,nullable=False, unique=True),
    sql.Column("installation_date", sql.Date, nullable = False),
    sql.Column("location", sql.String, nullable=False),
    sql.Column("status", sql.Enum("operating","under_maintenance","out_of_service", name="status_enum"), default="operating"),
    sql.Column("maintenance_status", sql.Enum("not_needed","pending","in_progress","completed","overdue", name="maintenance_status_enum"), default="not_needed")   
)

def insert_equipments(name,manufacturer,model,serial,installation_date,location):
    
    metadata.create_all(engine)
    
    if isinstance(installation_date, str):
        installation_date = datetime.strptime(installation_date, '%Y-%m-%d').date()
    
    insert_query = equipment_table.insert().values(
        name=name,
        manufacturer=manufacturer,
        model=model,
        serial=serial,
        installation_date=installation_date,
        location=location
    )
    res = connection.execute(insert_query)
    connection.commit()
    
    
def list_equipments():
    
    metadata.create_all(engine)
    
    select_query = sql.select(equipment_table)
    result = connection.execute(select_query).fetchall()
    return result

def select_equipment(serial):
    
    metadata.create_all(engine)
    
    select_query = sql.select(equipment_table).where(equipment_table.c.serial == serial)
    result = connection.execute(select_query).fetchone()
    return result

def update_equipment_status(serial, status, maintenance_status):
    
    metadata.create_all(engine)
    
    update_query = sql.update(equipment_table).where(equipment_table.c.serial == serial).values(
        status=status,
        maintenance_status=maintenance_status
    )
    connection.execute(update_query)
    connection.commit()
    
    
equipment_monitoring_table = sql.Table(
    "monitoring",
    metadata,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("equipment_serial", sql.String, sql.ForeignKey("equipments.serial"), nullable=False),
    sql.Column("timestamp", sql.DateTime, default=datetime.utcnow, nullable=False),
    sql.Column("status", sql.Enum("normal", "warning", "critical", name="monitoring_status_enum"), nullable=False, default="normal"),  # "normal", "warning", "critical"
    sql.Column("reading_type", sql.String(50), nullable=False),  # "vibration", "temperature", "pressure", etc.
    sql.Column("value", sql.Float, nullable=False),
    sql.Column("unit", sql.String(20)),  # "°C", "mm/s", "bar", "A", etc.
    sql.Column("location", sql.String(50)),
    sql.Column("threshold_min", sql.Float),
    sql.Column("threshold_max", sql.Float),
    sql.UniqueConstraint("equipment_serial", "timestamp", "reading_type", "location", name="unique_monitoring_entry")
)

def insert_monitoring_data(equipment_serial: str,reading_type: str,value: float,unit: str = None,location: str = None,status: str = "normal",timestamp: datetime = None,threshold_min: float = None,threshold_max: float = None):

    metadata.create_all(engine)

    print(f"Inserting monitoring data for equipment {equipment_serial}")

    if timestamp is None:
        timestamp = datetime.utcnow()
    
    insert_query = equipment_monitoring_table.insert().values(
        equipment_serial=equipment_serial,
        timestamp=timestamp,
        status=status,
        reading_type=reading_type,
        value=value,
        unit=unit,
        location=location,
        threshold_min=threshold_min,
        threshold_max=threshold_max
    )
    
    connection.execute(insert_query)
    connection.commit()
    

def list_all_monitoring_data():
    
    metadata.create_all(engine)
    
    select_query = sql.select(equipment_monitoring_table).order_by(
        equipment_monitoring_table.c.timestamp.desc()
    )
    result = connection.execute(select_query).fetchall()
    return result

def list_equipment_monitoring_data(equipment_serial: str):
    
    metadata.create_all(engine)
    
    select_query = sql.select(equipment_monitoring_table).where(
        equipment_monitoring_table.c.equipment_serial == equipment_serial
    ).order_by(
        equipment_monitoring_table.c.timestamp.desc()
    )
    result = connection.execute(select_query).fetchall()
    return result



maintenance_log_table = sql.Table(
    "maintenance",
    metadata,
    sql.Column("id", sql.Integer, primary_key = True),
    sql.Column("raised_by", sql.String, nullable = False),
    sql.Column("equipment_serial", sql.String, sql.ForeignKey("equipments.serial"), nullable = False),
    sql.Column("issue_description", sql.String, nullable = False),
    sql.Column("date_reported", sql.Date, nullable = False),
    sql.Column("severity", sql.Enum("low","medium","high","critical", name="severity_enum"), default="low"),
    sql.Column("status", sql.Enum("open","in_progress","resolved","closed", name="log_status_enum"), default="open"),
    sql.Column("date_resolved", sql.Date, nullable = True),
    sql.Column("date_predicted", sql.Date, nullable = True),
    sql.UniqueConstraint("equipment_serial", "status", name="unique_maintenance_log")
)

def list_maintenance_logs():
    
    metadata.create_all(engine)
    
    select_query = sql.select(maintenance_log_table)
    result = connection.execute(select_query).fetchall()
    return result

def list_maintenance_logs_open():
    
    metadata.create_all(engine)
    
    select_query = sql.select(maintenance_log_table).where(maintenance_log_table.c.status == "open")
    result = connection.execute(select_query).fetchall()
    return result

def select_maintenance_log(id):
    
    metadata.create_all(engine)
    
    select_query = sql.select(maintenance_log_table).where(maintenance_log_table.c.id == id)
    result = connection.execute(select_query).fetchone()
    return result

def list_equipment_maintenance_logs(equipment_serial):
    
    metadata.create_all(engine)
    
    select_query = sql.select(maintenance_log_table).where(maintenance_log_table.c.equipment_serial == equipment_serial)
    result = connection.execute(select_query).fetchall()
    return result

def insert_maintenance_log(raised_by,equipment_serial,issue_description,severity,date_reported=None,date_resolved=None,status="open",date_predicted=None):
    
    metadata.create_all(engine)
    
    if isinstance(date_reported, str):
        date_reported = datetime.strptime(date_reported, '%Y-%m-%d').date()
    if isinstance(date_resolved, str):
        date_resolved = datetime.strptime(date_resolved, '%Y-%m-%d').date()
    
    if (raised_by == None) or (raised_by.strip() == ""):
        raised_by = "AI Gen"
    
    insert_query = maintenance_log_table.insert().values(
        raised_by=raised_by,
        equipment_serial=equipment_serial,
        issue_description=issue_description,
        severity=severity,
        date_reported=date_reported,
        date_resolved=date_resolved,
        status=status,
        date_predicted=date_predicted
    )
    res = connection.execute(insert_query)
    connection.commit()
    