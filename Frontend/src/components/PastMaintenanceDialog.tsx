import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Loader2 } from "lucide-react";
import { useMaintenanceList } from "@/hooks/useMaintenanceList";

interface PastMaintenanceDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    getEquipmentName: (serial: string) => string;
}

export const PastMaintenanceDialog = ({
    open,
    onOpenChange,
    getEquipmentName,
}: PastMaintenanceDialogProps) => {
    const { data: allLogs, isLoading, error } = useMaintenanceList();

    // Filter for closed logs (have date_resolved) and sort by date_resolved descending
    const closedLogs = Array.isArray(allLogs)
        ? allLogs
            .filter((log) => log.date_resolved)
            .sort((a, b) => {
                const dateA = a.date_resolved ? new Date(a.date_resolved).getTime() : 0;
                const dateB = b.date_resolved ? new Date(b.date_resolved).getTime() : 0;
                return dateB - dateA;
            })
        : [];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-[900px] max-h-[80vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>Maintenance History</DialogTitle>
                    <DialogDescription>
                        Completed maintenance records across all equipment
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto min-h-0">
                    {isLoading ? (
                        <div className="flex justify-center p-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : error ? (
                        <div className="p-4 text-center text-error">
                            Failed to load maintenance logs. Please try again.
                        </div>
                    ) : closedLogs.length === 0 ? (
                        <div className="p-4 text-center text-muted-foreground">
                            No past maintenance records found.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader className="sticky top-0 bg-background z-10">
                                <TableRow>
                                    <TableHead>Equipment Name</TableHead>
                                    <TableHead>Resolution Date</TableHead>
                                    <TableHead>Description</TableHead>
                                    <TableHead>Reported By</TableHead>
                                    <TableHead>Severity</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {closedLogs.map((log) => (
                                    <TableRow key={log.id}>
                                        <TableCell className="font-medium">
                                            {getEquipmentName(log.equipment_serial)}
                                            <div className="text-xs text-muted-foreground">{log.equipment_serial}</div>
                                        </TableCell>
                                        <TableCell>{log.date_resolved}</TableCell>
                                        <TableCell className="max-w-[250px]">{log.issue_description}</TableCell>
                                        <TableCell>{log.raised_by}</TableCell>
                                        <TableCell>
                                            <span
                                                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${["critical", "high"].includes(log.severity.toLowerCase())
                                                    ? "bg-error/10 text-error"
                                                    : log.severity.toLowerCase() === "medium"
                                                        ? "bg-amber-100 text-amber-700 border-amber-200"
                                                        : "bg-yellow-100 text-yellow-700 border-yellow-200"
                                                    }`}
                                            >
                                                {log.severity}
                                            </span>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};
