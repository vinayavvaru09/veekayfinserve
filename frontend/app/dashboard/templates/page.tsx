"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { templatesApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import type { MessageTemplate } from "@/types";
import { Pencil, Eye } from "lucide-react";
import { useForm } from "react-hook-form";

const CHANNEL_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  email: "Email",
};

const LANG_LABELS: Record<string, string> = {
  en: "English",
  te: "Telugu",
};

type TemplateFormData = { subject: string; body: string };

export default function TemplatesPage() {
  const qc = useQueryClient();
  const [editModal, setEditModal] = useState<{ open: boolean; template: MessageTemplate | null }>({ open: false, template: null });
  const [previewModal, setPreviewModal] = useState<{ open: boolean; result: { subject?: string; body: string } | null }>({ open: false, result: null });

  const { data: templates = [], isLoading } = useQuery<MessageTemplate[]>({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TemplateFormData }) =>
      templatesApi.update(id, { subject: data.subject || null, body: data.body }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["templates"] }); setEditModal({ open: false, template: null }); },
  });

  const previewMutation = useMutation({
    mutationFn: (template_key: string) =>
      templatesApi.preview({ template_key }),
    onSuccess: (result) => setPreviewModal({ open: true, result }),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<TemplateFormData>();

  function openEdit(t: MessageTemplate) {
    reset({ subject: t.subject ?? "", body: t.body });
    setEditModal({ open: true, template: t });
  }

  return (
    <div>
      <PageHeader
        title="Message Templates"
        description="Configure WhatsApp and email notification content. Use {{customer_name}}, {{policy_number}}, {{policy_expiry_date}} as placeholders."
      />

      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="space-y-4">
          {templates.map((t) => (
            <div key={t.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <Badge className={t.channel === "whatsapp" ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"}>
                    {CHANNEL_LABELS[t.channel]}
                  </Badge>
                  {t.language && (
                    <Badge className="bg-gray-100 text-gray-600">{LANG_LABELS[t.language]}</Badge>
                  )}
                  <span className="text-xs font-mono text-gray-400">{t.template_key}</span>
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={() => previewMutation.mutate(t.template_key)} loading={previewMutation.isPending}>
                    <Eye size={14} /> Preview
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => openEdit(t)}>
                    <Pencil size={14} /> Edit
                  </Button>
                </div>
              </div>

              {t.subject && (
                <div className="mt-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Subject</p>
                  <p className="text-sm text-gray-700">{t.subject}</p>
                </div>
              )}
              <div className="mt-3">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Body</p>
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans bg-gray-50 rounded-lg p-3 border border-gray-100">
                  {t.body}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit modal */}
      <Modal
        open={editModal.open}
        onClose={() => setEditModal({ open: false, template: null })}
        title="Edit Template"
        className="max-w-2xl"
      >
        <form
          onSubmit={handleSubmit((data) => {
            if (editModal.template) updateMutation.mutate({ id: editModal.template.id, data });
          })}
          className="space-y-4"
        >
          {editModal.template?.channel === "email" && (
            <Input label="Subject" error={errors.subject?.message} {...register("subject")} />
          )}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700">Body</label>
            <textarea
              className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 min-h-[160px] font-mono"
              {...register("body", { required: "Required" })}
            />
            {errors.body && <p className="text-xs text-red-600">{errors.body.message}</p>}
          </div>
          <p className="text-xs text-gray-400">
            Available placeholders: <code>{"{{customer_name}}"}</code>, <code>{"{{policy_number}}"}</code>, <code>{"{{policy_expiry_date}}"}</code>
          </p>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setEditModal({ open: false, template: null })}>Cancel</Button>
            <Button type="submit" loading={updateMutation.isPending}>Save</Button>
          </div>
        </form>
      </Modal>

      {/* Preview modal */}
      <Modal
        open={previewModal.open}
        onClose={() => setPreviewModal({ open: false, result: null })}
        title="Template Preview"
        className="max-w-lg"
      >
        {previewModal.result && (
          <div className="space-y-3">
            {previewModal.result.subject && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Subject</p>
                <p className="text-sm text-gray-800">{previewModal.result.subject}</p>
              </div>
            )}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Body</p>
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans bg-gray-50 rounded-lg p-3 border border-gray-100">
                {previewModal.result.body}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
