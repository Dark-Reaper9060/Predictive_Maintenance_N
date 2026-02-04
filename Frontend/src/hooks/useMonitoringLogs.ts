import { useQuery } from "@tanstack/react-query";
import { MonitoringLog, MonitoringResponse } from "../types/monitoring";

export const useMonitoringLogs = (serialNumber: string | null) => {
    return useQuery({
        queryKey: ["monitoringLogs", serialNumber],
        queryFn: async (): Promise<MonitoringLog[]> => {
            if (!serialNumber) return [];

            const response = await fetch(`/monitoring/${serialNumber}`, {
                method: "POST",
            });
            if (!response.ok) {
                throw new Error("Failed to fetch monitoring logs");
            }

            const data: MonitoringResponse = await response.json();
            const logs = data.monitoring_data || [];

            // Sort by timestamp descending
            return logs.sort((a, b) =>
                new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
            );
        },
        enabled: !!serialNumber, // Only fetch when serialNumber is available
    });
};
