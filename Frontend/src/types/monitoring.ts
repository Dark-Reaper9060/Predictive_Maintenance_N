export interface MonitoringLog {
    id: number;
    equipment_serial: string;
    timestamp: string;
    status: string;
    reading_type: string;
    value: number;
    unit: string;
    location: string;
    threshold_min: number;
    threshold_max: number;
}

export interface MonitoringResponse {
    monitoring_data: MonitoringLog[];
}
