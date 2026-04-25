import type { ModelInfo, ModelsResponse } from "../api/types";

interface Props {
  provider: string;
  model: string;
  onProviderChange: (p: string) => void;
  onModelChange: (m: string) => void;
  models?: ModelsResponse;
  loading?: boolean;
}

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google (Gemma)",
  minimax: "MiniMax",
  bedrock: "Bedrock",
};

export function ModelSelector({
  provider,
  model,
  onProviderChange,
  onModelChange,
  models,
  loading,
}: Props) {
  const providers = Object.keys(models ?? {}).filter(
    (p) => (models?.[p as keyof ModelsResponse] ?? []).length > 0,
  );

  const currentList: ModelInfo[] =
    models?.[provider as keyof ModelsResponse] ?? [];

  return (
    <div className="row">
      <div className="col">
        <label className="label" htmlFor="provider-select">
          Provider
        </label>
        <select
          id="provider-select"
          className="select"
          disabled={loading || providers.length === 0}
          value={provider}
          onChange={(e) => {
            const next = e.target.value;
            onProviderChange(next);
            const list = models?.[next as keyof ModelsResponse] ?? [];
            if (list.length > 0) onModelChange(list[0].id);
          }}
        >
          {providers.length === 0 && <option value="">No providers configured</option>}
          {providers.map((p) => (
            <option key={p} value={p}>
              {PROVIDER_LABELS[p] ?? p}
            </option>
          ))}
        </select>
      </div>
      <div className="col">
        <label className="label" htmlFor="model-select">
          Model
        </label>
        <select
          id="model-select"
          className="select"
          disabled={loading || currentList.length === 0}
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
        >
          {currentList.length === 0 && <option value="">—</option>}
          {currentList.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
