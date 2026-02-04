import { useQuery } from "@tanstack/react-query";
import { MaintenanceLog, MaintenanceResponse } from "../types/maintenance";

export const useMaintenanceLogs = (serialNumber: string | null) => {
    return useQuery({
        queryKey: ["maintenanceLogs", serialNumber],
        queryFn: async (): Promise<MaintenanceLog[]> => {
            if (!serialNumber) return [];

            const response = await fetch(`/maintenance/logs/${serialNumber}`, {
                method: "POST",
            });
            if (!response.ok) {
                throw new Error("Failed to fetch maintenance logs");
            }

            const data: MaintenanceResponse = await response.json();
            const logs = data.maintenance_logs || [];

            return logs.sort((a, b) => {
                const dateA = a.date_resolved ? new Date(a.date_resolved).getTime() : 0;
                const dateB = b.date_resolved ? new Date(b.date_resolved).getTime() : 0;
                return dateB - dateA;
            });
        },
        enabled: !!serialNumber,
    });
};
