import { Fragment, useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";

import ErrorState from "../components/ErrorState";
import LearnPanel from "../components/LearnPanel";
import { usePrismMutation } from "../hooks/usePrismQuery";
import type { IngestResult, PrismResponse } from "../lib/types";

const severityOptions = ["routine", "warning", "critical"];
const findingSeverityOptions = ["low", "medium", "high", "critical"];

type MaintenanceFormValues = {
  asset_id: number;
  severity: string;
  narrative: string;
};

type FindingFormValues = {
  category: string;
  severity: string;
  description: string;
  recommendation: string;
};

type InspectionFormValues = {
  asset_id: number;
  inspector: string;
  overall_grade: string;
  summary: string;
  findings: FindingFormValues[];
};

type IngestResponse = PrismResponse<IngestResult>;

function DataEntrySection() {
  return (
    <div className="space-y-12">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold text-slate-100">Data entry</h2>
        <p className="text-sm text-slate-400">
          Submit new maintenance logs and inspection reports. The backend handles chunking, embedding, and storage in one transaction.
        </p>
      </header>
      <MaintenanceForm />
      <InspectionForm />
    </div>
  );
}

function MaintenanceForm() {
  const { register, handleSubmit, reset } = useForm<MaintenanceFormValues>({
    defaultValues: { severity: "warning" },
  });

  const mutation = usePrismMutation<MaintenanceFormValues, IngestResult>({
    path: "/api/v1/ingest/maintenance-logs",
  });

  const [response, setResponse] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (values: MaintenanceFormValues) => {
    setError(null);
    try {
      const result = await mutation.mutateAsync(values);
      setResponse(result);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit maintenance log.");
    }
  };

  return (
    <section className="space-y-6 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
      <div>
        <h3 className="text-xl font-semibold text-slate-100">New maintenance log</h3>
        <p className="text-sm text-slate-400">Simulates operational data entry feeding the vector pipeline.</p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="maintenance-asset">
            Asset ID
          </label>
          <input
            id="maintenance-asset"
            type="number"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
            {...register("asset_id", { valueAsNumber: true, required: true })}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="maintenance-severity">
            Severity
          </label>
          <select
            id="maintenance-severity"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
            {...register("severity", { required: true })}
          >
            {severityOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="maintenance-narrative">
            Narrative
          </label>
          <textarea
            id="maintenance-narrative"
            rows={4}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
            {...register("narrative", { required: true, minLength: 10 })}
          />
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            className="rounded-lg bg-prism-teal px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-400 disabled:bg-teal-700/60"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Submitting…" : "Submit log"}
          </button>
        </div>
      </form>
      {error ? <ErrorState message={error} /> : null}
      {response ? <IngestSummary response={response} /> : null}
    </section>
  );
}

function InspectionForm() {
  const { register, control, handleSubmit, reset } = useForm<InspectionFormValues>({
    defaultValues: {
      findings: [
        { category: "structure", severity: "high", description: "", recommendation: "" },
      ],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "findings" });

  const mutation = usePrismMutation<InspectionFormValues, IngestResult>({
    path: "/api/v1/ingest/inspection-reports",
  });

  const [response, setResponse] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (values: InspectionFormValues) => {
    setError(null);
    try {
      const result = await mutation.mutateAsync(values);
      setResponse(result);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit inspection report.");
    }
  };

  return (
    <section className="space-y-6 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
      <div>
        <h3 className="text-xl font-semibold text-slate-100">New inspection report</h3>
        <p className="text-sm text-slate-400">Demonstrates multi-entity ingest through Duality Views and vectorization.</p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="inspection-asset">
              Asset ID
            </label>
            <input
              id="inspection-asset"
              type="number"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
              {...register("asset_id", { valueAsNumber: true, required: true })}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="inspection-inspector">
              Inspector
            </label>
            <input
              id="inspection-inspector"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
              {...register("inspector", { required: true })}
            />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="inspection-grade">
              Overall grade (A-F)
            </label>
            <input
              id="inspection-grade"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
              {...register("overall_grade", { required: true, pattern: /^[A-F]$/ })}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="inspection-summary">
              Summary
            </label>
            <textarea
              id="inspection-summary"
              rows={3}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
              {...register("summary", { required: true, minLength: 10 })}
            />
          </div>
        </div>

        <div className="space-y-4">
          <header className="flex items-center justify-between">
            <h4 className="text-lg font-semibold text-slate-100">Findings</h4>
            <button
              type="button"
              className="rounded-lg border border-prism-teal/40 px-3 py-1.5 text-xs font-semibold text-prism-teal hover:bg-prism-teal/10"
              onClick={() => append({ category: "structure", severity: "medium", description: "", recommendation: "" })}
            >
              Add finding
            </button>
          </header>
          <div className="space-y-4">
            {fields.map((field, index) => (
              <Fragment key={field.id}>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor={`findings.${index}.category`}>
                      Category
                    </label>
                    <input
                      id={`findings.${index}.category`}
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
                      {...register(`findings.${index}.category` as const, { required: true })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor={`findings.${index}.severity`}>
                      Severity
                    </label>
                    <select
                      id={`findings.${index}.severity`}
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
                      {...register(`findings.${index}.severity` as const, { required: true })}
                    >
                      {findingSeverityOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor={`findings.${index}.description`}>
                      Description
                    </label>
                    <textarea
                      id={`findings.${index}.description`}
                      rows={3}
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
                      {...register(`findings.${index}.description` as const, { required: true, minLength: 10 })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor={`findings.${index}.recommendation`}>
                      Recommendation
                    </label>
                    <textarea
                      id={`findings.${index}.recommendation`}
                      rows={3}
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
                      {...register(`findings.${index}.recommendation` as const, { required: true, minLength: 10 })}
                    />
                  </div>
                </div>
                {fields.length > 1 ? (
                  <div className="flex justify-end">
                    <button
                      type="button"
                      className="rounded-lg border border-red-500/40 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/10"
                      onClick={() => remove(index)}
                    >
                      Remove finding
                    </button>
                  </div>
                ) : null}
                <div className="border-t border-slate-800" />
              </Fragment>
            ))}
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="rounded-lg bg-prism-teal px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-400 disabled:bg-teal-700/60"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Submitting…" : "Submit report"}
          </button>
        </div>
      </form>
      {error ? <ErrorState message={error} /> : null}
      {response ? <IngestSummary response={response} /> : null}
    </section>
  );
}

type IngestSummaryProps = {
  response: IngestResponse;
};

function IngestSummary({ response }: IngestSummaryProps) {
  const { data, meta } = response;

  return (
    <div className="space-y-3 rounded-xl border border-prism-teal/40 bg-prism-teal/5 p-4">
      <div className="text-sm font-semibold text-prism-teal">
        Success! Source ID {data.source_id} created with {data.chunks_created} chunks and {data.vectors_stored} vectors.
      </div>
      <div className="space-y-2 text-xs text-slate-300">
        {data.pipeline_steps.map((step) => (
          <div key={step.step}>
            <p className="font-semibold uppercase tracking-[0.2em] text-prism-teal/70">{step.step}</p>
            <pre className="mt-1 overflow-x-auto rounded-lg bg-slate-950/80 p-3 text-xs text-slate-200">
              <code>{step.sql}</code>
            </pre>
          </div>
        ))}
      </div>
      <LearnPanel meta={meta} title="Ingest pipeline" />
    </div>
  );
}

export default DataEntrySection;
