"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { policiesApi, providersApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/page-header";
import { Table, Thead, Tbody, Th, Td } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Modal } from "@/components/ui/modal";
import { formatDate, POLICY_TYPES } from "@/lib/utils";
import type { Policy, Provider } from "@/types";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";

const PAGE_SIZE = 20;

type PolicyFormData = {
  customer_name: string;
  policy_number: string;
  date_of_birth: string;
  phone_number: string;
  email: string;
  type_of_policy: string;
  insurance_provider_id: string;
  policy_expiry_date: string;
  hold_date: string;
  renewed_date: string;
};

function PolicyForm({
  defaultValues,
  providers,
  onSubmit,
  loading,
}: {
  defaultValues?: Partial<PolicyFormData>;
  providers: Provider[];
  onSubmit: (data: PolicyFormData) => void;
  loading: boolean;
}) {
  const { register, handleSubmit, formState: { errors } } = useForm<PolicyFormData>({ defaultValues });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Input label="Customer Name" error={errors.customer_name?.message} {...register("customer_name", { required: "Required" })} />
        <Input label="Policy Number" error={errors.policy_number?.message} {...register("policy_number", { required: "Required" })} />
        <Input label="Date of Birth" type="date" {...register("date_of_birth")} />
        <Input label="Phone Number" {...register("phone_number")} />
        <Input label="Email" type="email" {...register("email")} />
        <Select
          label="Policy Type"
          options={POLICY_TYPES.map((t) => ({ value: t, label: t }))}
          placeholder="Select type"
          error={errors.type_of_policy?.message}
          {...register("type_of_policy", { required: "Required" })}
        />
        <Select
          label="Insurance Provider"
          options={providers.map((p) => ({ value: p.id, label: p.provider_name }))}
          placeholder="Select provider"
          error={errors.insurance_provider_id?.message}
          {...register("insurance_provider_id", { required: "Required" })}
        />
        <Input label="Policy Expiry Date" type="date" error={errors.policy_expiry_date?.message} {...register("policy_expiry_date", { required: "Required" })} />
        <Input label="Hold Date" type="date" {...register("hold_date")} />
        <Input label="Renewed Date" type="date" {...register("renewed_date")} />
      </div>
      <div className="flex justify-end pt-2">
        <Button type="submit" loading={loading}>Save Policy</Button>
      </div>
    </form>
  );
}

export default function PoliciesPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterProvider, setFilterProvider] = useState("");
  const [modal, setModal] = useState<{ open: boolean; policy: Policy | null }>({ open: false, policy: null });
  const [deleteConfirm, setDeleteConfirm] = useState<Policy | null>(null);

  const params = {
    page,
    page_size: PAGE_SIZE,
    ...(search && { search }),
    ...(filterType && { type_of_policy: filterType }),
    ...(filterProvider && { insurance_provider_id: filterProvider }),
  };

  const { data, isLoading } = useQuery({
    queryKey: ["policies", params],
    queryFn: () => policiesApi.list(params),
  });

  const { data: providersData } = useQuery({
    queryKey: ["providers"],
    queryFn: () => providersApi.list(),
  });

  const providers: Provider[] = providersData?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (d: PolicyFormData) => policiesApi.create(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["policies"] }); setModal({ open: false, policy: null }); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PolicyFormData }) => policiesApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["policies"] }); setModal({ open: false, policy: null }); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => policiesApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["policies"] }); setDeleteConfirm(null); },
  });

  const policies: Policy[] = data?.items ?? [];
  const total: number = data?.total ?? 0;

  return (
    <div>
      <PageHeader
        title="Policies"
        description="Manage all insurance policies"
        action={
          <Button onClick={() => setModal({ open: true, policy: null })}>
            <Plus size={16} /> Add Policy
          </Button>
        }
      />

      {/* Filters */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <Input placeholder="Search by name or policy no." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        <Select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
          placeholder="All policy types"
          options={POLICY_TYPES.map((t) => ({ value: t, label: t }))}
        />
        <Select
          value={filterProvider}
          onChange={(e) => { setFilterProvider(e.target.value); setPage(1); }}
          placeholder="All providers"
          options={providers.map((p) => ({ value: p.id, label: p.provider_name }))}
        />
      </div>

      <Table>
        <Thead>
          <tr>
            <Th>Customer</Th>
            <Th>Policy No.</Th>
            <Th>Type</Th>
            <Th>Provider</Th>
            <Th>Expiry Date</Th>
            <Th>Hold Date</Th>
            <Th>Renewed</Th>
            <Th>Actions</Th>
          </tr>
        </Thead>
        <Tbody>
          {isLoading ? (
            <tr><Td className="text-center text-gray-400 py-8" colSpan={8}>Loading…</Td></tr>
          ) : policies.length === 0 ? (
            <tr><Td className="text-center text-gray-400 py-8" colSpan={8}>No policies found</Td></tr>
          ) : (
            policies.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <Td className="font-medium">{p.customer_name}</Td>
                <Td className="font-mono text-xs">{p.policy_number}</Td>
                <Td><Badge className="bg-blue-50 text-blue-700">{p.type_of_policy}</Badge></Td>
                <Td>{p.provider_name ?? "—"}</Td>
                <Td>{formatDate(p.policy_expiry_date)}</Td>
                <Td>{formatDate(p.hold_date)}</Td>
                <Td>{formatDate(p.renewed_date)}</Td>
                <Td>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setModal({ open: true, policy: p })}>
                      <Pencil size={14} />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setDeleteConfirm(p)}>
                      <Trash2 size={14} className="text-red-500" />
                    </Button>
                  </div>
                </Td>
              </tr>
            ))
          )}
        </Tbody>
      </Table>

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />

      {/* Create / Edit modal */}
      <Modal
        open={modal.open}
        onClose={() => setModal({ open: false, policy: null })}
        title={modal.policy ? "Edit Policy" : "Add Policy"}
        className="max-w-2xl"
      >
        <PolicyForm
          providers={providers}
          defaultValues={modal.policy ? {
            ...modal.policy,
            date_of_birth: modal.policy.date_of_birth ?? "",
            phone_number: modal.policy.phone_number ?? "",
            email: modal.policy.email ?? "",
            hold_date: modal.policy.hold_date ?? "",
            renewed_date: modal.policy.renewed_date ?? "",
          } : undefined}
          loading={createMutation.isPending || updateMutation.isPending}
          onSubmit={(formData) => {
            const clean = Object.fromEntries(
              Object.entries(formData).map(([k, v]) => [k, v === "" ? null : v])
            ) as PolicyFormData;
            if (modal.policy) {
              updateMutation.mutate({ id: modal.policy.id, data: clean });
            } else {
              createMutation.mutate(clean);
            }
          }}
        />
      </Modal>

      {/* Delete confirm */}
      <Modal
        open={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        title="Delete Policy"
      >
        <p className="text-sm text-gray-600 mb-6">
          Delete policy <strong>{deleteConfirm?.policy_number}</strong> for{" "}
          <strong>{deleteConfirm?.customer_name}</strong>? This cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm.id)}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
