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
import { useMaintenanceLogs } from "@/hooks/useMaintenanceLogs";


interface MaintenanceDialogProps {
    serialNumber: string | null;
    equipmentName: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const MaintenanceDialog = ({
    serialNumber,
    equipmentName,
    open,
    onOpenChange,
}: MaintenanceDialogProps) => {
    const { data: logs, isLoading, error } = useMaintenanceLogs(serialNumber);



    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-[800px] max-h-[80vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>Maintenance Logs: {equipmentName} ({serialNumber})</DialogTitle>
                    <DialogDescription>
                        Historical maintenance records and service reports
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
                    ) : !logs || logs.length === 0 ? (
                        <div className="p-4 text-center text-muted-foreground">
                            No maintenance history found for this equipment.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader className="sticky top-0 bg-background z-10">
                                <TableRow>
                                    <TableHead>Resolution Date</TableHead>
                                    <TableHead>Description</TableHead>
                                    <TableHead>Reported By</TableHead>
                                    <TableHead>Severity</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {logs.map((log) => (
                                    <TableRow key={log.id}>
                                        <TableCell>{log.date_resolved || "NA"}</TableCell>
                                        <TableCell className="max-w-[300px]">{log.issue_description}</TableCell>
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
