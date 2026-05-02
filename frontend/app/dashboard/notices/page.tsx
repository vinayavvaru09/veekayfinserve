"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { noticesApi, providersApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/page-header";
import { Table, Thead, Tbody, Th, Td } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Modal } from "@/components/ui/modal";
import { formatDate, getStatusLabel, getStatusStyle, POLICY_TYPES } from "@/lib/utils";
import type { RenewalNotice, Provider } from "@/types";
import { Download, Upload, RefreshCw } from "lucide-react";

const PAGE_SIZE = 20;

export default function NoticesPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    expiry_date_from: "",
    expiry_date_to: "",
    insurance_provider_id: "",
    type_of_policy: "",
    notice_status: "",
  });
  const [uploadModal, setUploadModal] = useState<{ open: boolean; noticeId: string | null }>({
    open: false,
    noticeId: null,
  });
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const params = {
    page,
    page_size: PAGE_SIZE,
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "")),
  };

  const { data, isLoading } = useQuery({
    queryKey: ["notices", params],
    queryFn: () => noticesApi.list(params),
  });

  const { data: providersData } = useQuery({
    queryKey: ["providers"],
    queryFn: () => providersApi.list(),
  });

  const providers: Provider[] = providersData?.items ?? [];

  const regenerateMutation = useMutation({
    mutationFn: (id: string) => noticesApi.regenerate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notices"] }),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => noticesApi.uploadDocument(id, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notices"] });
      setUploadModal({ open: false, noticeId: null });
      setUploadFile(null);
    },
  });

  const handleDownload = useCallback(async (notice: RenewalNotice) => {
    const blob = await noticesApi.downloadDocument(notice.id);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = notice.document_filename ?? `renewal_${notice.policy_number}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const setFilter = (key: string, value: string) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };

  const notices: RenewalNotice[] = data?.items ?? [];
  const total: number = data?.total ?? 0;

  return (
    <div>
      <PageHeader
        title="Renewal Notices"
        description="Track and manage all insurance renewal notices"
      />

      {/* Filters */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <Input
          type="date"
          label="Expiry from"
          value={filters.expiry_date_from}
          onChange={(e) => setFilter("expiry_date_from", e.target.value)}
        />
        <Input
          type="date"
          label="Expiry to"
          value={filters.expiry_date_to}
          onChange={(e) => setFilter("expiry_date_to", e.target.value)}
        />
        <Select
          label="Provider"
          value={filters.insurance_provider_id}
          onChange={(e) => setFilter("insurance_provider_id", e.target.value)}
          placeholder="All providers"
          options={providers.map((p) => ({ value: p.id, label: p.provider_name }))}
        />
        <Select
          label="Policy type"
          value={filters.type_of_policy}
          onChange={(e) => setFilter("type_of_policy", e.target.value)}
          placeholder="All types"
          options={POLICY_TYPES.map((t) => ({ value: t, label: t }))}
        />
        <Select
          label="Status"
          value={filters.notice_status}
          onChange={(e) => setFilter("notice_status", e.target.value)}
          placeholder="All statuses"
          options={[
            { value: "pending_automation", label: "Pending Automation" },
            { value: "pending_manual_upload", label: "Needs Upload" },
            { value: "completed", label: "Completed" },
            { value: "failed", label: "Failed" },
          ]}
        />
      </div>

      <Table>
        <Thead>
          <tr>
            <Th>Customer</Th>
            <Th>Policy No.</Th>
            <Th>Expiry Date</Th>
            <Th>Provider</Th>
            <Th>Type</Th>
            <Th>Status</Th>
            <Th>Actions</Th>
          </tr>
        </Thead>
        <Tbody>
          {isLoading ? (
            <tr>
              <Td className="text-center text-gray-400 py-8" colSpan={7}>
                Loading…
              </Td>
            </tr>
          ) : notices.length === 0 ? (
            <tr>
              <Td className="text-center text-gray-400 py-8" colSpan={7}>
                No notices found
              </Td>
            </tr>
          ) : (
            notices.map((n) => (
              <tr key={n.id} className="hover:bg-gray-50">
                <Td className="font-medium">{n.customer_name}</Td>
                <Td className="font-mono text-xs">{n.policy_number}</Td>
                <Td>{formatDate(n.policy_expiry_date)}</Td>
                <Td>{n.provider_name ?? "—"}</Td>
                <Td>
                  <Badge className="bg-blue-50 text-blue-700">{n.type_of_policy}</Badge>
                </Td>
                <Td>
                  <Badge className={getStatusStyle(n.status)}>{getStatusLabel(n.status)}</Badge>
                </Td>
                <Td>
                  <div className="flex items-center gap-2">
                    {n.has_document && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(n)}
                        title="Download document"
                      >
                        <Download size={15} />
                      </Button>
                    )}
                    {n.status === "pending_manual_upload" && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setUploadModal({ open: true, noticeId: n.id })}
                        title="Upload document"
                      >
                        <Upload size={15} />
                        Upload
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={regenerateMutation.isPending && regenerateMutation.variables === n.id}
                      onClick={() => regenerateMutation.mutate(n.id)}
                      title="Regenerate via portal"
                    >
                      <RefreshCw size={15} />
                    </Button>
                  </div>
                </Td>
              </tr>
            ))
          )}
        </Tbody>
      </Table>

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />

      {/* Upload modal */}
      <Modal
        open={uploadModal.open}
        onClose={() => { setUploadModal({ open: false, noticeId: null }); setUploadFile(null); }}
        title="Upload Renewal Document"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Select the PDF renewal notice downloaded from the insurer portal.
          </p>
          <input
            type="file"
            accept="application/pdf"
            className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
            onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setUploadModal({ open: false, noticeId: null })}>
              Cancel
            </Button>
            <Button
              disabled={!uploadFile}
              loading={uploadMutation.isPending}
              onClick={() => {
                if (uploadModal.noticeId && uploadFile) {
                  uploadMutation.mutate({ id: uploadModal.noticeId, file: uploadFile });
                }
              }}
            >
              Upload
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
