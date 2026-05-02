"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { providersApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/page-header";
import { Table, Thead, Tbody, Th, Td } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import type { Provider } from "@/types";
import { Plus, Pencil, Trash2, ExternalLink } from "lucide-react";
import { useForm } from "react-hook-form";

type ProviderFormData = {
  provider_name: string;
  portal_url: string;
  username: string;
  password: string;
  additional_notes: string;
};

function ProviderForm({
  defaultValues,
  onSubmit,
  loading,
  isEdit,
}: {
  defaultValues?: Partial<ProviderFormData>;
  onSubmit: (data: ProviderFormData) => void;
  loading: boolean;
  isEdit: boolean;
}) {
  const { register, handleSubmit, formState: { errors } } = useForm<ProviderFormData>({ defaultValues });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input label="Provider Name" error={errors.provider_name?.message} {...register("provider_name", { required: "Required" })} />
      <Input label="Portal URL" type="url" error={errors.portal_url?.message} {...register("portal_url", { required: "Required" })} />
      <div className="border-t pt-4">
        <p className="text-xs font-semibold text-gray-500 uppercase mb-3">
          Login Credentials {isEdit && <span className="font-normal normal-case text-gray-400">(leave blank to keep existing)</span>}
        </p>
        <div className="grid grid-cols-2 gap-4">
          <Input label="Username / Email" {...register("username")} />
          <Input label="Password" type="password" {...register("password")} />
        </div>
      </div>
      <Input label="Additional Auth Notes (optional)" {...register("additional_notes")} />
      <div className="flex justify-end pt-2">
        <Button type="submit" loading={loading}>Save Provider</Button>
      </div>
    </form>
  );
}

export default function ProvidersPage() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<{ open: boolean; provider: Provider | null }>({ open: false, provider: null });
  const [deleteConfirm, setDeleteConfirm] = useState<Provider | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["providers"],
    queryFn: () => providersApi.list(),
  });

  const providers: Provider[] = data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (d: ProviderFormData) =>
      providersApi.create({
        provider_name: d.provider_name,
        portal_url: d.portal_url,
        login_credentials: { username: d.username, password: d.password },
        additional_auth_details: d.additional_notes ? { notes: d.additional_notes } : undefined,
      }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["providers"] }); setModal({ open: false, provider: null }); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProviderFormData }) => {
      const payload: Record<string, unknown> = {
        provider_name: data.provider_name,
        portal_url: data.portal_url,
      };
      if (data.username || data.password) {
        payload.login_credentials = { username: data.username, password: data.password };
      }
      if (data.additional_notes) {
        payload.additional_auth_details = { notes: data.additional_notes };
      }
      return providersApi.update(id, payload);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["providers"] }); setModal({ open: false, provider: null }); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => providersApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["providers"] }); setDeleteConfirm(null); },
  });

  return (
    <div>
      <PageHeader
        title="Insurance Providers"
        description="Manage insurer portal credentials and metadata"
        action={
          <Button onClick={() => setModal({ open: true, provider: null })}>
            <Plus size={16} /> Add Provider
          </Button>
        }
      />

      <Table>
        <Thead>
          <tr>
            <Th>Provider Name</Th>
            <Th>Portal URL</Th>
            <Th>Credentials</Th>
            <Th>Actions</Th>
          </tr>
        </Thead>
        <Tbody>
          {isLoading ? (
            <tr><Td className="text-center text-gray-400 py-8" colSpan={4}>Loading…</Td></tr>
          ) : providers.length === 0 ? (
            <tr><Td className="text-center text-gray-400 py-8" colSpan={4}>No providers configured</Td></tr>
          ) : (
            providers.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <Td className="font-medium">{p.provider_name}</Td>
                <Td>
                  <a
                    href={p.portal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-600 hover:underline flex items-center gap-1 text-xs"
                  >
                    {p.portal_url.replace(/^https?:\/\//, "").slice(0, 40)}
                    <ExternalLink size={12} />
                  </a>
                </Td>
                <Td>
                  <span className="text-xs text-gray-400 font-mono">••••••••</span>
                </Td>
                <Td>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setModal({ open: true, provider: p })}>
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

      <Modal
        open={modal.open}
        onClose={() => setModal({ open: false, provider: null })}
        title={modal.provider ? "Edit Provider" : "Add Provider"}
        className="max-w-lg"
      >
        <ProviderForm
          isEdit={!!modal.provider}
          defaultValues={modal.provider ? { provider_name: modal.provider.provider_name, portal_url: modal.provider.portal_url } : undefined}
          loading={createMutation.isPending || updateMutation.isPending}
          onSubmit={(formData) => {
            if (modal.provider) {
              updateMutation.mutate({ id: modal.provider.id, data: formData });
            } else {
              createMutation.mutate(formData);
            }
          }}
        />
      </Modal>

      <Modal open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)} title="Delete Provider">
        <p className="text-sm text-gray-600 mb-6">
          Delete <strong>{deleteConfirm?.provider_name}</strong>? All associated policies will lose their provider reference.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="danger" loading={deleteMutation.isPending} onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm.id)}>
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
