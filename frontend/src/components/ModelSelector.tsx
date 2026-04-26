import { useModels } from "../api/chat";

interface Props {
  provider: string;
  model: string;
  onProviderChange: (p: string) => void;
  onModelChange: (m: string) => void;
}

export function ModelSelector({ provider, model, onProviderChange, onModelChange }: Props) {
  const { data, isLoading } = useModels();
  if (isLoading) return <div>Loading models…</div>;
  const models = data?.models ?? [];
  const providers = Array.from(new Set(models.map((m) => m.provider)));
  const filtered = models.filter((m) => m.provider === provider);
  return (
    <div style={{ display: "flex", gap: "0.5rem" }}>
      <select value={provider} onChange={(e) => onProviderChange(e.target.value)}>
        {providers.map((p) => (
          <option key={p}>{p}</option>
        ))}
      </select>
      <select value={model} onChange={(e) => onModelChange(e.target.value)}>
        {filtered.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name}
          </option>
        ))}
      </select>
    </div>
  );
}
