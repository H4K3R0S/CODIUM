import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import type { ChatPos } from "../chat/chatPrefs";


// ==========          PAMETAN RASPORED OKO CHATA          ==========
/*
 * Isto ponašanje na svakom ekranu koji ima chat: čim razgovor krene, okviri se
 * sklapaju i odlaze uz levu ivicu radne površine (naslov/ikona umesto punog
 * sadržaja), klik na skupljen okvir ga otvara kao preview uz chat, a kada se
 * chat premesti u panel desno raspored mu se skloni s puta.
 *
 * Svaka promena rasporeda ide kroz FLIP (izmeri pre, izmeri posle, odigraj
 * razliku) — sam CSS ne ume da tvin-uje promenu mreže ili prelazak iz toka
 * stranice u fiksiran položaj.
 */

/** Trajanja (ms) — skupljanje je najduže jer je i put najduži. */
const TUCK_MS = 620;
const POS_MS = 520;
const PREVIEW_MS = 420;

const FLIP_EASING = "cubic-bezier(0.22, 0.61, 0.36, 1)";

export type SmartLayout = {
  /** Okvir ekrana; u njemu se traže okviri koji se premeštaju. */
  rootRef: React.RefObject<HTMLDivElement | null>;
  /** Skupljeno stanje (razgovor u toku). */
  tucked: boolean;
  /** Id okvira otvorenog kao preview uz chat, ili null. */
  preview: string | null;
  /** Gde stoji chat okvir. */
  chatPosition: ChatPos;
  /** Klase stanja za koren ekrana. */
  className: string;
  /** Skuplja ili vraća raspored (vezuje se na `onEngaged` chata). */
  changeTuck: (next: boolean) => void;
  /** Otvara/zatvara preview datog okvira. */
  togglePreview: (id: string) => void;
  /** Prima novi položaj chata (vezuje se na `onPosChange`). */
  handlePosChange: (next: ChatPos) => void;
};

/**
 * @param selector CSS selektor okvira koji se premeštaju (FLIP).
 */
export function useSmartLayout(selector: string): SmartLayout {
  const rootRef = useRef<HTMLDivElement | null>(null);

  const [tucked, setTucked] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [chatPosition, setChatPosition] = useState<ChatPos>("bottom");

  const tuckedRef = useRef(false);
  const chatPositionRef = useRef<ChatPos>("bottom");
  const flipRects = useRef<Map<HTMLElement, DOMRect>>(new Map());
  const flipDuration = useRef(TUCK_MS);

  /** FLIP „First": položaji pre nego što se raspored promeni. */
  const captureFlip = useCallback(
    (duration: number) => {
      const root = rootRef.current;
      if (root === null) {
        return;
      }
      flipDuration.current = duration;
      flipRects.current = new Map(
        Array.from(root.querySelectorAll<HTMLElement>(selector)).map((node) => [
          node,
          node.getBoundingClientRect(),
        ]),
      );
    },
    [selector],
  );

  const changeTuck = useCallback(
    (next: boolean) => {
      if (tuckedRef.current === next) {
        return;
      }
      tuckedRef.current = next;
      captureFlip(TUCK_MS);
      setTucked(next);
      if (!next) {
        // Pun raspored ne trpi preview — okviri su ponovo otvoreni.
        setPreview(null);
      }
    },
    [captureFlip],
  );

  const togglePreview = useCallback(
    (id: string) => {
      // Otvoren preview skraćuje chat (a uz panel desno i sam raspored), pa se
      // i taj pomak igra kroz istu animaciju.
      captureFlip(PREVIEW_MS);
      setPreview((current) => (current === id ? null : id));
    },
    [captureFlip],
  );

  const handlePosChange = useCallback(
    (next: ChatPos) => {
      if (chatPositionRef.current === next) {
        return;
      }
      chatPositionRef.current = next;
      // Poziv stiže pre nego što se raspored ekrana promeni — pravi trenutak
      // za snimak starih položaja.
      captureFlip(POS_MS);
      setChatPosition(next);
    },
    [captureFlip],
  );

  /*
   * Sistemski widget (CPU/GPU/RAM) stoji u gornjoj traci ljuske, van ekrana sa
   * chatom, pa do njega ne dopire klasa korena. Zato polozaj chata stoji i na
   * `body` — svako ko je van ekrana sme da mu se skloni s puta.
   */
  useEffect(() => {
    const desno = chatPosition === "right";
    document.body.classList.toggle("core-chat-right", desno);
    return () => document.body.classList.remove("core-chat-right");
  }, [chatPosition]);

  // FLIP „Last / Invert / Play".
  useLayoutEffect(() => {
    const before = flipRects.current;
    flipRects.current = new Map();
    if (before.size === 0) {
      return;
    }
    // Poštuje sistemsko „manje animacija".
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    for (const [node, from] of before) {
      if (typeof node.animate !== "function") {
        continue;
      }
      const to = node.getBoundingClientRect();
      if (
        to.width === 0 ||
        to.height === 0 ||
        from.width === 0 ||
        from.height === 0
      ) {
        continue;
      }
      const dx = from.left - to.left;
      const dy = from.top - to.top;
      const sx = from.width / to.width;
      const sy = from.height / to.height;
      if (
        Math.abs(dx) < 1 &&
        Math.abs(dy) < 1 &&
        Math.abs(sx - 1) < 0.01 &&
        Math.abs(sy - 1) < 0.01
      ) {
        continue;
      }
      node.animate(
        [
          {
            transformOrigin: "top left",
            transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`,
            opacity: 0.7,
          },
          { transformOrigin: "top left", transform: "none", opacity: 1 },
        ],
        { duration: flipDuration.current, easing: FLIP_EASING },
      );
    }
  }, [tucked, chatPosition, preview]);

  const className = [
    tucked ? "is-tucked" : "",
    `chat-${chatPosition}`,
    preview === null ? "" : "has-preview",
  ]
    .filter((deo) => deo !== "")
    .join(" ");

  return {
    rootRef,
    tucked,
    preview,
    chatPosition,
    className,
    changeTuck,
    togglePreview,
    handlePosChange,
  };
}
