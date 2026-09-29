import { useEffect, useRef, useState } from "react";


// ==========          IZBORNIK UZ POLJE ZA UNOS          ==========
/*
 * Zamena za `<select>` u chat traci.
 *
 * Spisak koji otvara `<select>` crta operativni sistem: uvek je neprozirno beo
 * i ne prima stil stranice. Uz providan chat okvir to je iskakalo kao tuđ
 * prozor, pa se spisak ovde crta u samoj stranici — providan, sa istim blur-om
 * kao okvir.
 *
 * Zauzvrat se tastatura i pristupačnost moraju napisati ručno; zato su ovde
 * strelice, Enter i Escape, `role="listbox"` i `aria-selected`.
 */

export type ChatSelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
  /** Stavka koja ne kosta nista — dobija zelenu traku uz levu ivicu. */
  free?: boolean;
};

export type ChatSelectGroup = {
  /** Naslov grupe („Lokalno", „Online"); prazan za spisak bez grupa. */
  title?: string;
  options: ChatSelectOption[];
};

type ChatSelectProps = {
  ariaLabel: string;
  value: string;
  groups: ChatSelectGroup[];
  onChange: (next: string) => void;
  /** Tekst kad ništa nije izabrano (npr. „Model"). */
  placeholder: string;
  className?: string;
  title?: string;
};

function ChatSelect({
  ariaLabel,
  value,
  groups,
  onChange,
  placeholder,
  className = "",
  title,
}: ChatSelectProps) {
  const [otvoren, setOtvoren] = useState(false);
  const koren = useRef<HTMLDivElement | null>(null);

  const sve = groups.flatMap((g) => g.options);
  const izabrana = sve.find((o) => o.value === value);

  useEffect(() => {
    if (!otvoren) {
      return;
    }
    // Klik van izbornika zatvara spisak — isto što `<select>` radi sam.
    function vanKlika(event: MouseEvent): void {
      if (!koren.current?.contains(event.target as Node)) {
        setOtvoren(false);
      }
    }
    document.addEventListener("mousedown", vanKlika);
    return () => document.removeEventListener("mousedown", vanKlika);
  }, [otvoren]);

  function pomeri(korak: number): void {
    const dostupne = sve.filter((o) => o.disabled !== true);
    if (dostupne.length === 0) {
      return;
    }
    const trenutna = dostupne.findIndex((o) => o.value === value);
    const sledeca = Math.min(
      Math.max(trenutna + korak, 0),
      dostupne.length - 1,
    );
    onChange(dostupne[trenutna === -1 ? 0 : sledeca].value);
  }

  function naTaster(event: React.KeyboardEvent): void {
    if (event.key === "Escape") {
      setOtvoren(false);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      pomeri(event.key === "ArrowDown" ? 1 : -1);
    }
  }

  return (
    <div className={`chat-select ${className}`} ref={koren} onKeyDown={naTaster}>
      <button
        type="button"
        className="chat-select-trigger"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={otvoren}
        title={title}
        onClick={() => setOtvoren((v) => !v)}
      >
        {izabrana?.label ?? placeholder}
      </button>

      {otvoren && (
        // Natpis spiska nije isti kao natpis dugmeta: dva ista bi bila dva
        // elementa sa istim imenom, sto zbunjuje i citac ekrana.
        <ul
          className="chat-select-menu"
          role="listbox"
          aria-label={`${ariaLabel}: spisak`}
        >
          {groups.map((grupa, gi) => (
            <li key={grupa.title ?? gi} className="chat-select-group">
              {grupa.title !== undefined && (
                <span className="chat-select-group-title">{grupa.title}</span>
              )}

              <ul className="chat-select-options">
                {grupa.options.map((opcija) => (
                  <li key={opcija.value}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={opcija.value === value}
                      className={`chat-select-option ${
                        opcija.value === value ? "is-selected" : ""
                      } ${opcija.free === true ? "is-free" : ""}`}
                      disabled={opcija.disabled}
                      onClick={() => {
                        onChange(opcija.value);
                        setOtvoren(false);
                      }}
                    >
                      {opcija.label}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default ChatSelect;
