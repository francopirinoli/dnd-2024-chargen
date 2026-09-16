type Char = Record<string, unknown>;

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}
function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}
function arr<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}
function rec(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
function signed(v: number | undefined): string {
  if (v === undefined) return "—";
  return v >= 0 ? `+${v}` : String(v);
}

const SLOT_LEVEL_ORDINALS = [
  "Cantrip",
  "1st",
  "2nd",
  "3rd",
  "4th",
  "5th",
  "6th",
  "7th",
  "8th",
  "9th",
];

function slotLevelOrdinal(level: string): string {
  const numeric = Number(level.match(/\d+/)?.[0]);
  if (!Number.isFinite(numeric)) return level;
  return SLOT_LEVEL_ORDINALS[numeric] ?? `${numeric}th`;
}

function formatCastingTime(time: string): string {
  if (!time) return "1 Action";
  if (/bonus\s*action/i.test(time)) return "1 Bonus Act.";
  if (/reaction/i.test(time)) return "1 Reaction";
  if (/ritual/i.test(time)) return "Act./Ritual";
  if (/^1\s*action/i.test(time)) return "1 Action";
  if (time.length > 16) return time.slice(0, 14) + "…";
  return time;
}

interface PrintableSpellsPageProps {
  c: Char;
}

export function PrintableSpellsPage({ c }: PrintableSpellsPageProps) {
  const byLevel = rec(c.spells_by_level);
  const slots = rec(c.spell_slots);
  const stats = rec(c.spellcasting_stats);

  const ability = str(stats.spellcasting_ability) ?? "—";
  const saveDC = num(stats.spell_save_dc);
  const attackBonus = num(stats.spell_attack_bonus);
  const castingMod = num(stats.spellcasting_modifier);
  const ritual = stats.ritual_casting === true;

  const pactMagicSlots = arr<Record<string, unknown>>(stats.pact_magic_slots);

  // Invocations
  const eldritchStats = rec(c.eldritch_invocation_stats);
  const invocations = arr<Record<string, unknown>>(eldritchStats.invocations ?? []);

  // Wizard spellbook check
  const spellsData = rec(c.spells);
  const spellbook = arr<string>(spellsData.spellbook);
  const isWizard = (str(c.class) ?? "").toLowerCase().includes("wizard");

  const levels = Object.keys(byLevel).sort((a, b) => Number(a) - Number(b));

  return (
    <div className="flex flex-col gap-3.5 text-slate-900 leading-tight">
      {/* ── 1. Top Spellcasting Dashboard ── */}
      <div className="border-2 border-slate-900 rounded-lg p-2.5 bg-slate-50/70">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-300 pb-2 mb-2">
          <div>
            <h2 className="font-display text-lg font-black text-slate-950 uppercase tracking-wide">
              Spellcasting & Magic
            </h2>
            <span className="text-[10px] text-slate-600">
              {str(c.class)} Spellcasting • Regain expended slots on Long Rest
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-center px-2 py-1 bg-white border border-slate-300 rounded">
              <span className="text-[9px] uppercase font-bold text-slate-500 block">
                Ability
              </span>
              <span className="font-display font-bold text-xs text-slate-900">
                {ability}
              </span>
            </div>
            <div className="text-center px-2 py-1 bg-white border border-slate-300 rounded">
              <span className="text-[9px] uppercase font-bold text-slate-500 block">
                Save DC
              </span>
              <span className="font-display font-bold text-xs text-slate-900 font-mono">
                {saveDC ?? "—"}
              </span>
            </div>
            <div className="text-center px-2 py-1 bg-white border border-slate-300 rounded">
              <span className="text-[9px] uppercase font-bold text-slate-500 block">
                Attack Bonus
              </span>
              <span className="font-display font-bold text-xs text-slate-900 font-mono">
                {signed(attackBonus)}
              </span>
            </div>
            <div className="text-center px-2 py-1 bg-white border border-slate-300 rounded">
              <span className="text-[9px] uppercase font-bold text-slate-500 block">
                Modifier
              </span>
              <span className="font-display font-bold text-xs text-slate-900 font-mono">
                {signed(castingMod)}
              </span>
            </div>
            <div className="text-center px-2 py-1 bg-white border border-slate-300 rounded">
              <span className="text-[9px] uppercase font-bold text-slate-500 block">
                Ritual
              </span>
              <span className="font-display font-bold text-xs text-slate-900">
                {ritual ? "Yes" : "No"}
              </span>
            </div>
          </div>
        </div>

        {/* Spell Slots Tracker Grid */}
        {Object.keys(slots).length > 0 && (
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-500 block mb-1">
              Spell Slots Tracker
            </span>
            <div className="grid grid-cols-4 sm:grid-cols-9 gap-1.5 text-center">
              {Object.entries(slots).map(([lvl, n]) => {
                const totalSlots = num(n) ?? 0;
                return (
                  <div
                    key={lvl}
                    className="border border-slate-400 bg-white rounded p-1 flex flex-col items-center justify-between"
                  >
                    <span className="text-[9px] uppercase font-bold text-slate-600">
                      {slotLevelOrdinal(lvl)}
                    </span>
                    <span className="font-bold text-xs text-slate-900 my-0.5">
                      {totalSlots}
                    </span>
                    <div className="flex gap-0.5 justify-center font-mono text-[9px] text-slate-400 tracking-tighter">
                      {Array.from({ length: totalSlots }).map((_, i) => (
                        <span key={i}>[ ]</span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Pact Magic Slots (if Warlock) */}
        {pactMagicSlots.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-200">
            <span className="text-[9px] uppercase font-bold text-slate-500 block mb-1">
              Pact Magic Slots (Regain on Short Rest)
            </span>
            <div className="flex gap-2">
              {pactMagicSlots.map((entry, idx) => (
                <div
                  key={idx}
                  className="border border-amber-800/40 bg-amber-50 rounded px-2 py-1 text-center"
                >
                  <span className="text-[9px] uppercase font-bold text-amber-900 block">
                    {slotLevelOrdinal(String(num(entry.slot_level) ?? 1))}
                  </span>
                  <span className="font-bold text-xs text-amber-950">
                    {num(entry.slots)} Slots
                  </span>
                  <div className="font-mono text-[9px] text-amber-700">
                    {Array.from({ length: num(entry.slots) ?? 1 }).map((_, i) => (
                      <span key={i}>[ ] </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── 2. Spells by Level Table / Cards ── */}
      <div className="space-y-3">
        {levels.map((lvl) => {
          const list = arr<Record<string, unknown>>(byLevel[lvl]);
          if (list.length === 0) return null;

          return (
            <div
              key={lvl}
              className="avoid-break break-inside-avoid border border-slate-800 rounded-md overflow-hidden bg-white shadow-2xs"
              style={{ breakInside: "avoid", pageBreakInside: "avoid" }}
            >
              {/* Level Header Banner */}
              <div className="bg-slate-800 text-white px-3 py-1 flex items-center justify-between font-display font-bold text-xs uppercase tracking-wider">
                <span>{lvl === "0" ? "Cantrips (At Will)" : `Level ${lvl} Spells`}</span>
                <span className="text-[10px] font-normal text-slate-300">
                  {list.length} {list.length === 1 ? "spell" : "spells"}
                </span>
              </div>

              {/* Table of spells */}
              <div>
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 text-[8.5px] uppercase text-slate-500 bg-slate-50">
                      <th className="py-1 pl-2 w-6 text-center">Prep</th>
                      <th className="py-1 pr-2 w-40">Spell Name</th>
                      <th className="py-1 px-1.5 w-20">School</th>
                      <th className="py-1 px-1.5 w-22">Time</th>
                      <th className="py-1 px-1.5 w-16">Range</th>
                      <th className="py-1 px-1.5 w-12">Comp</th>
                      <th className="py-1 px-1.5 w-20">Duration</th>
                      <th className="py-1 pr-2">Summary</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-[10px]">
                    {list.map((sp, idx) => {
                      const name = str(sp.name) ?? "Spell";
                      const school = str(sp.school) ?? "";
                      const rawTime = str(sp.casting_time) ?? "Action";
                      const castingTime = formatCastingTime(rawTime);
                      const range = str(sp.range) ?? "Self";
                      const comps = arr<string>(sp.components).join(", ");
                      const duration = str(sp.duration) ?? "Instant.";
                      const desc = str(sp.description) ?? "";
                      const isConc = sp.concentration === true;
                      const isRitual = sp.ritual === true;
                      const isPrepared = sp.is_always_prepared === true || sp.counts_against_limit === true || lvl === "0";

                      return (
                        <tr key={idx} className="hover:bg-slate-50/80">
                          <td className="py-1 pl-2 text-center font-bold text-slate-800">
                            {isPrepared ? "●" : "○"}
                          </td>
                          <td className="py-1 pr-2 font-bold text-slate-900">
                            <div className="flex items-center gap-1">
                              <span className="truncate">{name}</span>
                              {isConc && (
                                <span className="font-bold text-[8px] bg-amber-100 text-amber-900 px-1 rounded shrink-0" title="Concentration">
                                  C
                                </span>
                              )}
                              {isRitual && (
                                <span className="font-bold text-[8px] bg-blue-100 text-blue-900 px-1 rounded shrink-0" title="Ritual">
                                  R
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-1 px-1.5 text-slate-600 text-[9.5px]">
                            {school}
                          </td>
                          <td className="py-1 px-1.5 text-slate-700 text-[9.5px] whitespace-nowrap">
                            {castingTime}
                          </td>
                          <td className="py-1 px-1.5 text-slate-700 text-[9.5px] whitespace-nowrap">
                            {range}
                          </td>
                          <td className="py-1 px-1.5 text-slate-500 text-[8.5px]">
                            {comps || "—"}
                          </td>
                          <td className="py-1 px-1.5 text-slate-700 text-[9.5px] whitespace-nowrap">
                            {duration}
                          </td>
                          <td className="py-1 pr-2 text-slate-600 text-[9px] leading-tight line-clamp-1" title={desc}>
                            {desc}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}

        {/* Wizard Spellbook Section (if applicable) */}
        {isWizard && spellbook.length > 0 && (
          <div className="avoid-break break-inside-avoid border border-slate-800 rounded-md p-2.5 bg-slate-50/70" style={{ breakInside: "avoid", pageBreakInside: "avoid" }}>
            <span className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 block mb-1">
              Wizard Spellbook (Known Scribed Spells)
            </span>
            <p className="text-[10px] text-slate-600 mb-1.5">
              Spells copied into your grimoire. You can cast ritual spells directly from this book without preparing them.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {spellbook.map((sName) => (
                <span key={sName} className="bg-white border border-slate-300 text-slate-800 text-[10px] px-2 py-0.5 rounded font-medium">
                  {sName}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Eldritch Invocations Section (if applicable) */}
        {invocations.length > 0 && (
          <div className="avoid-break break-inside-avoid border border-slate-800 rounded-md p-2.5 bg-slate-50/70" style={{ breakInside: "avoid", pageBreakInside: "avoid" }}>
            <span className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 block mb-1">
              Eldritch Invocations
            </span>
            <div className="space-y-1.5 text-[10.5px]">
              {invocations.map((inv, i) => (
                <div key={i} className="border-b border-slate-200 pb-1 last:border-none">
                  <span className="font-bold text-slate-900">{str(inv.name)}: </span>
                  <span className="text-slate-700">{str(inv.description)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
