import { useQuery } from "@tanstack/react-query";
import { MaintenanceLog, MaintenanceResponse } from "../types/maintenance";

export const useOpenMaintenanceLogs = () => {
    return useQuery({
        queryKey: ["openMaintenanceLogs"],
        queryFn: async (): Promise<MaintenanceLog[]> => {
            const response = await fetch("/maintenance/logs/open");
            if (!response.ok) {
                throw new Error("Failed to fetch open maintenance logs");
            }
            const data: MaintenanceResponse = await response.json();
            return data.maintenance_logs || [];
        },
    });
};
