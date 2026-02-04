import { useQuery } from "@tanstack/react-query";
import { Equipment } from "../types/equipment";

export const useEquipments = () => {
    return useQuery({
        queryKey: ["equipments"],
        queryFn: async (): Promise<Equipment[]> => {
            const response = await fetch("/equipments/list_all");
            if (!response.ok) {
                throw new Error("Failed to fetch equipments");
            }
            const data = await response.json();
            console.log("Full Equipments API response:", data);

            if (Array.isArray(data)) {
                return data;
            }

            // Handle wrapped responses like { data: [...] } or { equipments: [...] }
            if (data && typeof data === "object") {
                if (Array.isArray(data.data)) return data.data;
                if (Array.isArray(data.equipments)) return data.equipments;
                if (Array.isArray(data.items)) return data.items;
                // If the object itself looks like a dictionary of equipments, logic might be needed here
            }

            console.error("Unexpected API response structure:", data);
            return [];
        },
    });
};
