import { useQuery } from "@tanstack/react-query";
import { MaintenanceLog, MaintenanceResponse } from "../types/maintenance";

export const useMaintenanceList = () => {
    return useQuery({
        queryKey: ["maintenanceList"],
        queryFn: async (): Promise<MaintenanceLog[]> => {
            const response = await fetch("/maintenance/logs");
            if (!response.ok) {
                throw new Error("Failed to fetch maintenance list");
            }
            const data: MaintenanceResponse = await response.json();
            console.log("Maintenance List Data:", data);
            return data.maintenance_logs || [];
        },
    });
};
