import { cn } from "@/lib/utils";

type Char = Record<string, unknown>;

function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}
function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
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

interface PrintableCombatPageProps {
  c: Char;
}

export function PrintableCombatPage({ c }: PrintableCombatPageProps) {
  const name =
    str(c.name) ??
    str(c.character_name) ??
    "Unnamed Hero";
  const cls = str(c.class) ?? "Adventurer";
  const lvl = num(c.level) ?? 1;
  const subclass = str(c.subclass);
  const species = str(c.species) ?? "Unknown";
  const lineage = str(c.lineage);
  const background = str(c.background) ?? "None";
  const alignment = str(c.alignment) ?? "Unaligned";
  const size = str(c.size) ?? "Medium";
  const pb = num(c.proficiency_bonus) ?? 2;

  const combat = rec(c.combat);
  const hpMax = num(combat.hit_point_maximum) ?? 10;
  const ac = num(combat.armor_class) ?? 10;
  const initiative = num(combat.initiative) ?? 0;
  const speed = num(combat.speed) ?? 30;
  const hitDice = rec(combat.hit_dice);
  const hitDiceTotal = str(hitDice.total) ?? `${lvl}d8`;

  const abilities = rec(c.abilities);
  const abilityKeys = [
    { key: "strength", label: "STR", full: "Strength" },
    { key: "dexterity", label: "DEX", full: "Dexterity" },
    { key: "constitution", label: "CON", full: "Constitution" },
    { key: "intelligence", label: "INT", full: "Intelligence" },
    { key: "wisdom", label: "WIS", full: "Wisdom" },
    { key: "charisma", label: "CHA", full: "Charisma" },
  ];

  const savingThrows = rec(c.saving_throws);
  const skills = rec(c.skills);
  const attacks = arr<Record<string, unknown>>(c.attacks);
  const acOptions = arr<Record<string, unknown>>(c.ac_options);
  const equippedArmor = acOptions.find((opt) => opt.equipped === true) ?? acOptions[0];

  const proficiencies = rec(c.proficiencies);
  const armorProf = arr<string>(proficiencies.armor);
  const weaponProf = arr<string>(proficiencies.weapons);
  const toolProf = arr<string>(proficiencies.tools);
  const langProf = arr<string>(proficiencies.languages);

  const passPerception = num(combat.passive_perception) ?? 10;

  // Key combat features
  const classFeatures = arr<Record<string, unknown>>(rec(c.features).class);
  const subclassFeatures = arr<Record<string, unknown>>(rec(c.features).subclass);
  const allFeatures = [...classFeatures, ...subclassFeatures];

  return (
    <div className="flex flex-col gap-2.5 text-slate-900 leading-tight">
      {/* ── 1. Top Character Identity Banner ── */}
      <div className="border-2 border-slate-900 rounded-md p-2 bg-slate-50/70">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-300 pb-1.5 mb-1.5">
          <div>
            <span className="text-[9px] uppercase tracking-wider font-bold text-slate-500 block">
              Character Name
            </span>
            <h1 className="font-display text-xl font-black text-slate-950 uppercase tracking-wide">
              {name}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-[9px] uppercase tracking-wider font-bold text-slate-500 block">
                Class & Level
              </span>
              <span className="font-display font-bold text-sm text-slate-900">
                {cls} {lvl} {subclass ? `(${subclass})` : ""}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-xs">
          <div>
            <span className="text-[8.5px] uppercase font-bold text-slate-500 block">
              Species / Lineage
            </span>
            <span className="font-medium text-slate-800 text-[11px]">
              {species} {lineage ? `(${lineage})` : ""}
            </span>
          </div>
          <div>
            <span className="text-[8.5px] uppercase font-bold text-slate-500 block">
              Background
            </span>
            <span className="font-medium text-slate-800 text-[11px]">{background}</span>
          </div>
          <div>
            <span className="text-[8.5px] uppercase font-bold text-slate-500 block">
              Alignment & Size
            </span>
            <span className="font-medium text-slate-800 text-[11px]">
              {alignment} • {size}
            </span>
          </div>
          <div>
            <span className="text-[8.5px] uppercase font-bold text-slate-500 block">
              Proficiency Bonus
            </span>
            <span className="font-bold text-slate-900 text-xs font-mono">
              +{pb}
            </span>
          </div>
        </div>
      </div>

      {/* ── 2. Top Combat Vitals Bar ── */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
        {/* Armor Class */}
        <div className="border-2 border-slate-900 rounded-md p-1.5 text-center bg-white flex flex-col justify-between">
          <span className="text-[9px] uppercase font-bold text-slate-600">
            Armor Class
          </span>
          <div className="font-display font-black text-xl text-slate-950 my-0.5">
            {ac}
          </div>
          <span className="text-[8.5px] text-slate-500 truncate">
            {equippedArmor ? str(equippedArmor.name) : "Unarmored"}
          </span>
        </div>

        {/* Initiative */}
        <div className="border-2 border-slate-900 rounded-md p-1.5 text-center bg-white flex flex-col justify-between">
          <span className="text-[9px] uppercase font-bold text-slate-600">
            Initiative
          </span>
          <div className="font-display font-black text-xl text-slate-950 my-0.5">
            {signed(initiative)}
          </div>
          <span className="text-[8.5px] text-slate-500">Dexterity</span>
        </div>

        {/* Speed */}
        <div className="border-2 border-slate-900 rounded-md p-1.5 text-center bg-white flex flex-col justify-between">
          <span className="text-[9px] uppercase font-bold text-slate-600">
            Speed
          </span>
          <div className="font-display font-black text-xl text-slate-950 my-0.5">
            {speed}
            <span className="text-xs font-normal ml-0.5">ft</span>
          </div>
          <span className="text-[8.5px] text-slate-500">Walking</span>
        </div>

        {/* Hit Points Box */}
        <div className="border-2 border-slate-900 rounded-md p-1.5 text-center bg-white flex flex-col justify-between">
          <div className="flex items-center justify-between text-[9px] font-bold text-slate-600">
            <span>Hit Points</span>
            <span className="text-slate-500 font-mono">Max: {hpMax}</span>
          </div>
          <div className="h-5 border-b border-dashed border-slate-400 my-0.5 flex items-end justify-center">
            <span className="text-[9px] text-slate-400">Current</span>
          </div>
          <span className="text-[8.5px] text-slate-500">Temp HP: ______</span>
        </div>

        {/* Hit Dice */}
        <div className="border-2 border-slate-900 rounded-md p-1.5 text-center bg-white flex flex-col justify-between">
          <span className="text-[9px] uppercase font-bold text-slate-600">
            Hit Dice
          </span>
          <div className="font-display font-black text-base text-slate-950 my-0.5">
            {hitDiceTotal}
          </div>
          <span className="text-[8.5px] text-slate-500">Spent: [ ] [ ] [ ]</span>
        </div>

        {/* Death Saves & Inspiration */}
        <div className="border-2 border-slate-900 rounded-md p-1 bg-white flex flex-col justify-between text-[8.5px]">
          <div>
            <span className="font-bold text-slate-700 block">
              Death Saves
            </span>
            <div className="flex items-center justify-between text-[8.5px] text-slate-600">
              <span>Succ</span>
              <span className="font-mono tracking-tighter">O O O</span>
            </div>
            <div className="flex items-center justify-between text-[8.5px] text-slate-600">
              <span>Fail</span>
              <span className="font-mono tracking-tighter">O O O</span>
            </div>
          </div>
          <div className="border-t border-slate-200 pt-0.5 flex items-center justify-between">
            <span className="font-bold text-slate-700">Inspiration</span>
            <span className="font-mono font-bold">[ ]</span>
          </div>
        </div>
      </div>

      {/* ── 3. Main 2-Column Split: Stats on Left, Attacks & Actions on Right ── */}
      <div className="grid grid-cols-12 gap-2.5">
        {/* ── LEFT COLUMN (4 of 12 = ~33%): Abilities, Saves, Skills, Senses & Defenses ── */}
        <div className="col-span-12 sm:col-span-4 flex flex-col gap-2">
          {/* Ability Scores Mini Cards */}
          <div className="grid grid-cols-3 sm:grid-cols-2 gap-1">
            {abilityKeys.map((ab) => {
              const data = rec(abilities[ab.key]);
              const score = num(data.score) ?? 10;
              const mod = num(data.modifier) ?? 0;
              const save = rec(savingThrows[ab.key]);
              const isProf = save.proficient === true;
              const saveMod = num(save.modifier) ?? mod;

              return (
                <div
                  key={ab.key}
                  className="border border-slate-800 rounded p-1 bg-white text-center flex flex-col justify-between"
                >
                  <span className="text-[8.5px] uppercase font-bold text-slate-500 tracking-wider">
                    {ab.label}
                  </span>
                  <div className="font-display font-black text-base text-slate-950 my-0.5 leading-none">
                    {signed(mod)}
                  </div>
                  <div className="flex items-center justify-between text-[8.5px] px-0.5 border-t border-slate-200 pt-0.5">
                    <span className="text-slate-400 font-mono">{score}</span>
                    <span
                      className={cn(
                        "font-semibold",
                        isProf ? "text-slate-900 font-bold" : "text-slate-500",
                      )}
                      title="Saving Throw"
                    >
                      {isProf && "● "}
                      Save {signed(saveMod)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Skills List Table (Compact) */}
          <div className="border border-slate-800 rounded p-1.5 bg-white">
            <div className="font-display font-bold text-[11px] uppercase tracking-wide text-slate-900 border-b border-slate-200 pb-0.5 mb-1 flex items-center justify-between">
              <span>Skills</span>
              <span className="text-[8.5px] text-slate-400 font-normal">
                ● Prof ★ Exp
              </span>
            </div>
            <div className="grid grid-cols-1 text-[9px] leading-tight">
              {Object.entries(skills)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([skillName, rawSkill]) => {
                  const s = rec(rawSkill);
                  const isProf = s.proficient === true;
                  const isExp = s.expertise === true;
                  const mod = num(s.modifier) ?? 0;
                  const ab = str(s.ability) ?? "";

                  return (
                    <div
                      key={skillName}
                      className={cn(
                        "flex items-center justify-between py-[1px] px-1 rounded-2xs",
                        isExp
                          ? "bg-amber-50/70 font-semibold"
                          : isProf
                            ? "bg-slate-100/70 font-medium"
                            : "text-slate-600",
                      )}
                    >
                      <div className="flex items-center gap-1 min-w-0">
                        <span className="w-2.5 text-center text-slate-900 font-bold text-[8.5px]">
                          {isExp ? "★" : isProf ? "●" : "○"}
                        </span>
                        <span className="truncate capitalize text-slate-900">
                          {skillName.replace(/_/g, " ")}
                        </span>
                        <span className="text-[8px] text-slate-400 uppercase">
                          ({ab})
                        </span>
                      </div>
                      <span className="font-mono font-bold text-slate-900">
                        {signed(mod)}
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Senses, Passives & Defenses (Consolidated) */}
          <div className="border border-slate-800 rounded p-1.5 bg-white text-xs">
            <div className="font-display font-bold text-[10.5px] uppercase tracking-wide text-slate-900 border-b border-slate-200 pb-0.5 mb-1">
              Senses & Defenses
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[9px] text-slate-700">
              <div className="flex justify-between">
                <span>Perception:</span>
                <span className="font-bold font-mono">{passPerception}</span>
              </div>
              <div className="flex justify-between">
                <span>Darkvision:</span>
                <span className="font-bold">{c.darkvision ? `${c.darkvision} ft` : "None"}</span>
              </div>
              <div className="flex justify-between">
                <span>Insight:</span>
                <span className="font-bold font-mono">
                  {10 + (num(rec(skills.insight).modifier) ?? 0)}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Investigation:</span>
                <span className="font-bold font-mono">
                  {10 + (num(rec(skills.investigation).modifier) ?? 0)}
                </span>
              </div>
              {arr<string>(c.resistances).length > 0 && (
                <div className="col-span-2 pt-0.5 border-t border-slate-100 flex justify-between">
                  <span className="text-slate-500">Resistances:</span>
                  <span className="font-semibold text-slate-800 truncate max-w-[160px]">
                    {arr<string>(c.resistances).join(", ")}
                  </span>
                </div>
              )}
              {arr<string>(c.immunities).length > 0 && (
                <div className="col-span-2 flex justify-between">
                  <span className="text-slate-500">Immunities:</span>
                  <span className="font-semibold text-slate-800 truncate max-w-[160px]">
                    {arr<string>(c.immunities).join(", ")}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Proficiencies & Languages Box */}
          <div className="border border-slate-800 rounded p-1.5 bg-white text-xs">
            <div className="font-display font-bold text-[10.5px] uppercase tracking-wide text-slate-900 border-b border-slate-200 pb-0.5 mb-1">
              Proficiencies & Languages
            </div>
            <div className="space-y-1 text-[9.5px] text-slate-800">
              <div>
                <span className="font-bold text-slate-600 block text-[8.5px] uppercase">
                  Armor
                </span>
                <span>{armorProf.join(", ") || "None"}</span>
              </div>
              <div>
                <span className="font-bold text-slate-600 block text-[8.5px] uppercase">
                  Weapons
                </span>
                <span>{weaponProf.join(", ") || "None"}</span>
              </div>
              <div>
                <span className="font-bold text-slate-600 block text-[8.5px] uppercase">
                  Tools & Languages
                </span>
                <span>
                  {[...toolProf, ...langProf].join(", ") || "Common"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── RIGHT COLUMN (8 of 12 = ~67%): Attacks, Cantrips, Actions, Combat Features ── */}
        <div className="col-span-12 sm:col-span-8 flex flex-col gap-2">
          {/* Weapons & Attacks Table */}
          <div className="border-2 border-slate-900 rounded-md p-2 bg-white">
            <div className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 border-b border-slate-300 pb-1 mb-1 flex items-center justify-between">
              <span>Weapon Attacks & Offensive Cantrips</span>
              <span className="text-[9px] font-normal text-slate-500">
                Action to attack
              </span>
            </div>

            {attacks.length === 0 ? (
              <p className="text-xs text-slate-500 italic p-1.5">
                No equipped weapons or attacks recorded.
              </p>
            ) : (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-300 text-[8.5px] uppercase text-slate-500">
                    <th className="py-0.5 pr-2">Weapon / Attack</th>
                    <th className="py-0.5 px-1 text-center w-12">Bonus</th>
                    <th className="py-0.5 px-1.5">Damage & Type</th>
                    <th className="py-0.5 px-1">Range</th>
                    <th className="py-0.5 pl-1.5">Properties / Mastery</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-[10.5px]">
                  {attacks.map((atk, idx) => {
                    const atkName = str(atk.name) ?? "Attack";
                    const bonus =
                      str(atk.attack_bonus_display) ??
                      signed(num(atk.attack_bonus));
                    const dmg = `${str(atk.damage) ?? ""} ${str(atk.damage_type) ?? ""}`.trim();
                    const range = str(atk.range) ?? "Melee";
                    const props = arr<string>(atk.properties).join(", ");
                    const mastery = str(atk.mastery);

                    return (
                      <tr key={idx}>
                        <td className="py-1 pr-2 font-bold text-slate-900">
                          {atkName}
                        </td>
                        <td className="py-1 px-1 text-center font-mono font-bold text-slate-900">
                          {bonus}
                        </td>
                        <td className="py-1 px-1.5 font-medium text-slate-800 whitespace-nowrap">
                          {dmg}
                        </td>
                        <td className="py-1 px-1 text-[9.5px] text-slate-600 whitespace-nowrap">
                          {range}
                        </td>
                        <td className="py-1 pl-1.5 text-[9.5px] text-slate-700">
                          <span>{props}</span>
                          {mastery && (
                            <span className="ml-1 font-semibold text-amber-800 bg-amber-100 px-1 py-0.2 rounded text-[8.5px]">
                              {mastery}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Key Tactical Actions & Combat Features */}
          <div className="border border-slate-800 rounded-md p-2 bg-white flex-1">
            <div className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 border-b border-slate-300 pb-1 mb-1.5 flex items-center justify-between">
              <span>Tactical Actions & Combat Traits</span>
              <span className="text-[9px] font-normal text-slate-500">
                Core abilities
              </span>
            </div>

            <div className="space-y-1.5">
              {allFeatures.slice(0, 5).map((feat, idx) => {
                const fName = str(feat.name) ?? "Feature";
                const fDesc = str(feat.description) ?? "";
                const fLevel = num(feat.level);

                return (
                  <div
                    key={idx}
                    className="border-b border-slate-100 pb-1 last:border-none last:pb-0"
                  >
                    <div className="flex items-center justify-between text-[11px] font-bold text-slate-900">
                      <span>{fName}</span>
                      {fLevel && (
                        <span className="text-[8.5px] font-normal text-slate-500">
                          Lvl {fLevel}
                        </span>
                      )}
                    </div>
                    <p className="text-[9.5px] text-slate-700 line-clamp-2 leading-relaxed mt-0.5">
                      {fDesc}
                    </p>
                  </div>
                );
              })}
              {allFeatures.length > 5 && (
                <p className="text-[9.5px] text-slate-500 italic pt-1 border-t border-slate-200">
                  + {allFeatures.length - 5} more class/subclass traits and full rule descriptions on Page 2 (Features & Traits).
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
