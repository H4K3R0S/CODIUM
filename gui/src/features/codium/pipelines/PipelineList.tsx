import type { Pipeline } from "../../../types/codium";

type Props = {
  pipelines: Pipeline[];
  selectedId: number | null;
  onSelect: (pipelineId: number) => void;
  onRemove: (pipelineId: number) => void;
};

export default function PipelineList({
  pipelines,
  selectedId,
  onSelect,
  onRemove,
}: Props) {
  if (pipelines.length === 0) {
    return (
      <p className="cpipe-prazno">
        Nijedan pipeline nije definisan. Napravi ga u uređivaču ispod.
      </p>
    );
  }

  return (
    <ul className="cpipe-lista">
      {pipelines.map((pipeline) => (
        <li
          key={pipeline.id}
          className={`cpipe-stavka ${pipeline.id === selectedId ? "izabrana" : ""}`}
        >
          <button type="button" onClick={() => onSelect(pipeline.id)}>
            {pipeline.name}
          </button>
          <button type="button" onClick={() => onRemove(pipeline.id)}>
            Obriši
          </button>
        </li>
      ))}
    </ul>
  );
}
