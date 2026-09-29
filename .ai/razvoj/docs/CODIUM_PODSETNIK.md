---
id: codium-a6bee7b8-codium-podsetnik-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: Podsetnik — CODIUM (lokalni AI za programiranje)
summary: 'Materijal za budući domen **CODIUM**: lokalni code-modeli optimizovani za
  ~8 GB'
keywords:
- podsetnik
- codium
- lokalni
- programiranje
- docs
tags: []
source_path: docs/CODIUM_PODSETNIK.md
edges:
- type: references
  target: core-ccda48ce-dependencies-md
  weight: 0.3
- type: references
  target: core-78e9412c-ai-modeli-podsetnik-md
  weight: 0.3
---

# Podsetnik — CODIUM (lokalni AI za programiranje)

Materijal za budući domen **CODIUM**: lokalni code-modeli optimizovani za ~8 GB
VRAM, „Claude Artifacts / Bolt" tipovi alata sa live preview-om, i agentski
okviri koji se ponašaju kao pravi programer. Vrednosti su okvirne (zavise od
kvantizacije). Ovaj fajl je podsetnik — ne instalira ništa sam.

> Napomena o nazivima: **OpenDevin** se sada zove **OpenHands** (All-Hands AI).
> **OpenArtifacts** postoji u više varijanti (vidi linkove). „**Pagecraft AI**"
> nije potvrđen kao poseban projekat u pretrazi — najbliži sličan alat je
> `Fantalic/AI_HTML_Generator` (Ollama + Tailwind, prompt → HTML). Proveriti pre
> oslanjanja.

---

## 1. Lokalni „mozgovi" — code-reasoning modeli (za ~8 GB VRAM)

Za kodiranje trebaju code-reasoning modeli (ugrađena logika za sintaksu i
bagove), ne opšti modeli.

| Model | Veličina | VRAM (kvantizovano) | Najbolji za |
|-------|----------|---------------------|-------------|
| **DeepSeek-R1-Distill-Qwen-7B** (ili Llama 8B) | 7B / 8B | ~4.8 GB (`Q4_K_M`) | Chain-of-Thought — „razmišlja" pre koda. Kompleksna logika: Rust (memorija), Python, async u TypeScriptu. |
| **Qwen-2.5-Coder-7B-Instruct** | 7B | ~5 GB | Najbrži open-source za JS/TS i frontend: HTML, Tailwind CSS, React/Vue komponente. Kad je R1 prespor (ispisuje misli). |

Instalacija (Ollama): `ollama pull deepseek-r1:7b`,
`ollama pull qwen2.5-coder:7b`.

---

## 2. Lokalni „Claude Artifacts" / frontend alati (live preview)

Rešavaju najveći problem lokalnih modela — da vidiš šta kodiraš u realnom
vremenu (sandbox u pretraživaču).

| Alat | Šta radi | Izvor |
|------|----------|-------|
| **Bolt.diy** (community fork Bolt.new / zamena za Lovable) | Pokreneš lokalno (Node.js: `pnpm install` → `pnpm run dev`), povežeš na lokalnu Ollama-u i biraš Qwen-2.5-Coder ili DeepSeek-R1. Na prompt otvara terminal u browseru, instalira `npm` pakete, piše kod i prikazuje živi sajt u Preview prozoru. | https://github.com/stackblitz-labs/bolt.diy |
| **OpenArtifacts** | Kopija Claude „Artifacts" prozora: desna polovina ekrana je živi sandbox gde odmah klikćeš na generisane React/TS elemente. Varijante se razlikuju po tome koji model koriste (vidi ispod). | vidi ispod |
| **AI HTML Generator** (~„Pagecraft" tip) | Lokalna Ollama generiše čist HTML/Tailwind iz prompta; edit kroz follow-up prompt; snima `.html`. Za sliku→kod treba vizuelni model (npr. **LLaVA**). | https://github.com/Fantalic/AI_HTML_Generator |

### OpenArtifacts varijante (bitna razlika u modelu)

- **`mayfer/open-artifacts`** — jedan statični HTML, radi sa **bilo kojim**
  modelom po izboru (bundluje JSX u browseru preko esbuild-wasm, render u
  iframe). Najbliže „lokalnom" scenariju. https://github.com/mayfer/open-artifacts
- **`13point5/open-artifacts`** — Claude.ai clone; koristi **Anthropic/OpenAI
  API ključeve** (NE Ollama/lokalno). Stack: Next.js, Supabase, shadcn/ui,
  Vercel AI SDK. ⚠️ Repo **arhiviran 6.10.2024** (read-only).
  https://github.com/13point5/open-artifacts
- **`IntranetFactory/claude-artifacts-runner`** — boilerplate koji Claude-ov
  artifact (React/TS) pretvara u pokretljivu web aplikaciju lokalno.
  https://github.com/IntranetFactory/claude-artifacts-runner

Vizuelni model za skicu/sliku → frontend: **LLaVA** (https://github.com/haotian-liu/LLaVA), `ollama pull llava`.

---

## 3. Agentski okviri (ponašaju se kao pravi programer)

| Okvir | Kako radi | Izvor |
|-------|-----------|-------|
| **Aider** | Najbolji CLI AI programer koji radi direktno sa Git repozitorijumom. Npr. „dodaj dark mode u Tailwind config i napravi commit" — prepravi fajlove, proveri sintaksu, sam odradi `git commit`. Odlično sa lokalnim DeepSeek-R1. | https://github.com/Aider-AI/aider |
| **OpenHands** (bivši OpenDevin, All-Hands AI) | Podigne izolovan Docker kontejner sa sopstvenim VS Code-om, terminalom i pretraživačem. Daš zadatak (npr. ceo FastAPI ili Rust backend) — sam instalira biblioteke, pokrene server i testira dok ne proradi. | https://github.com/All-Hands-AI/OpenHands |

---

## Kako ovo koristiti u CODIUM-u

Kada CODIUM krene i budemo integrisali neki od ovih modela/alata, prati pravilo
iz [`docs/DEPENDENCIES.md`](DEPENDENCIES.md): unos u registar zavisnosti +
`scripts/install/<tool>.ps1` + uputstvo. Povezano: [`docs/AI_MODELI_PODSETNIK.md`](AI_MODELI_PODSETNIK.md).
