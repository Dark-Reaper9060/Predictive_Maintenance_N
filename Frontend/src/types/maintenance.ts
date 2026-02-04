export interface MaintenanceLog {
    id: number;
    raised_by: string;
    equipment_serial: string;
    issue_description: string;
    date_reported: string;
    date_predicted?: string;
    date_resolved?: string;
    status?: string;
    severity: "low" | "medium" | "high" | "critical";
}

export interface MaintenanceResponse {
    maintenance_logs: MaintenanceLog[];
}
