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

interface PrintableEquipmentPageProps {
  c: Char;
  choicesMade?: Record<string, unknown>;
}

const KNOWN_WEIGHTS: Record<string, number> = {
  "explorer's pack": 59,
  "dungeoneer's pack": 61.5,
  "burglar's pack": 47.5,
  "priest's pack": 25,
  "scholar's pack": 10,
  "diplomat's pack": 36,
  "entertainer's pack": 38,
  "padded armor": 8,
  "leather armor": 10,
  "studded leather": 13,
  "studded leather armor": 13,
  "hide armor": 12,
  "chain shirt": 20,
  "scale mail": 45,
  "breastplate": 20,
  "half plate": 40,
  "half plate armor": 40,
  "ring mail": 40,
  "chain mail": 55,
  "splint armor": 60,
  "plate armor": 65,
  "plate": 65,
  "shield": 6,
  "greataxe": 7,
  "greatsword": 6,
  "handaxe": 2,
  "javelin": 2,
  "longsword": 3,
  "shortsword": 2,
  "scimitar": 3,
  "dagger": 1,
  "spear": 3,
  "mace": 4,
  "warhammer": 2,
  "flail": 2,
  "glaive": 6,
  "halberd": 6,
  "pike": 18,
  "rapier": 2,
  "shortbow": 2,
  "longbow": 2,
  "light crossbow": 5,
  "heavy crossbow": 18,
  "quarterstaff": 4,
};

function getEstimatedWeight(itemName: string, explicitWeight?: number): number {
  if (typeof explicitWeight === "number" && explicitWeight > 0) return explicitWeight;
  const clean = itemName.toLowerCase().replace(/\s*\(\d+\)$/, "").trim();
  return KNOWN_WEIGHTS[clean] ?? 0;
}

interface ParsedInventoryItem {
  name: string;
  quantity: number;
  weight: number;
  notes: string;
}

export function PrintableEquipmentPage({ c, choicesMade }: PrintableEquipmentPageProps) {
  const abilities = rec(c.abilities);
  const strScore = num(rec(abilities.strength).score) ?? 10;
  const carryCapacity = strScore * 15;
  const pushDragLift = strScore * 30;

  // 1. Currency Extraction (from choicesMade.inventory.coins, c.wealth, or c.equipment.gold)
  const savedInv = rec(choicesMade?.inventory);
  const savedCoins = rec(savedInv.coins);
  const wealth = rec(c.wealth);
  const equipDict = rec(c.equipment);

  const cp =
    num(savedCoins.cp) ??
    num(wealth.cp) ??
    0;
  const sp =
    num(savedCoins.sp) ??
    num(wealth.sp) ??
    0;
  const ep =
    num(savedCoins.ep) ??
    num(wealth.ep) ??
    0;
  const gp =
    num(savedCoins.gp) ??
    num(wealth.gp) ??
    num(equipDict.gold) ??
    num(c.gold) ??
    0;
  const pp =
    num(savedCoins.pp) ??
    num(wealth.pp) ??
    0;

  // 2. Inventory Items Extraction
  const itemsList: ParsedInventoryItem[] = [];

  const savedItems = arr<Record<string, unknown>>(savedInv.items);
  if (savedItems.length > 0) {
    savedItems.forEach((it) => {
      const name = str(it.name) ?? "Item";
      const qty = num(it.quantity) ?? 1;
      const explicitWeight = num(it.weight);
      const weight = getEstimatedWeight(name, explicitWeight);
      const notes = str(it.notes) ?? (it.equipped ? "Equipped" : "");
      itemsList.push({ name, quantity: qty, weight, notes });
    });
  } else if (c.equipment && typeof c.equipment === "object" && !Array.isArray(c.equipment)) {
    // Standard backend format: { weapons: [...], armor: [...], items: [...], gold: number }
    const weapons = arr<Record<string, unknown>>(equipDict.weapons);
    weapons.forEach((w) => {
      const props = rec(w.properties);
      const name = str(w.display_name) ?? str(w.name) ?? "Weapon";
      const qty = num(w.quantity) ?? 1;
      const explicitWeight = num(props.weight) ?? num(w.weight);
      const weight = getEstimatedWeight(name, explicitWeight);
      const category = str(props.category);
      const mastery = str(props.mastery);
      const weaponProps = arr<string>(props.properties).join(", ");
      const notes = [category, mastery ? `Mastery: ${mastery}` : "", weaponProps]
        .filter(Boolean)
        .join(" • ");

      itemsList.push({ name, quantity: qty, weight, notes });
    });

    const armor = arr<Record<string, unknown>>(equipDict.armor);
    armor.forEach((a) => {
      const name = str(a.display_name) ?? str(a.name) ?? "Armor";
      const qty = num(a.quantity) ?? 1;
      const weight = getEstimatedWeight(name, num(a.weight));
      const source = str(a.source) ? `Source: ${a.source}` : "Armor";
      itemsList.push({ name, quantity: qty, weight, notes: source });
    });

    const items = arr<Record<string, unknown>>(equipDict.items);
    items.forEach((it) => {
      const name = typeof it === "string" ? it : str(it.name) ?? "Gear";
      const qty = typeof it === "object" && typeof it.quantity === "number" ? it.quantity : 1;
      const weight = getEstimatedWeight(name, typeof it === "object" ? num(it.weight) : undefined);
      const source = typeof it === "object" && it.source ? `Source: ${it.source}` : "";
      itemsList.push({ name, quantity: qty, weight, notes: source });
    });
  } else if (Array.isArray(c.equipment)) {
    (c.equipment as Array<Record<string, unknown>>).forEach((it) => {
      const name = str(it.name) ?? "Item";
      const qty = num(it.quantity) ?? 1;
      const weight = getEstimatedWeight(name, num(it.weight));
      const notes = str(it.notes) ?? str(it.description) ?? "";
      itemsList.push({ name, quantity: qty, weight, notes });
    });
  } else if (Array.isArray(c.inventory)) {
    (c.inventory as Array<Record<string, unknown>>).forEach((it) => {
      const name = str(it.name) ?? "Item";
      const qty = num(it.quantity) ?? 1;
      const weight = getEstimatedWeight(name, num(it.weight));
      const notes = str(it.notes) ?? str(it.description) ?? "";
      itemsList.push({ name, quantity: qty, weight, notes });
    });
  }

  // 3. Equipped Armor detection
  const acOptions = arr<Record<string, unknown>>(c.ac_options);
  const combatAc = num(rec(c.combat).armor_class);
  const equippedArmorOpt =
    acOptions.find((o) => (o.equipped_armor || o.armor) && num(o.ac) === combatAc) ??
    acOptions.find((o) => o.equipped_armor || o.armor);

  const equippedArmorName = equippedArmorOpt
    ? (str(equippedArmorOpt.equipped_armor) ?? str(equippedArmorOpt.armor))
    : null;

  // 4. Total weight calculation
  let totalWeight = 0;
  itemsList.forEach((item) => {
    totalWeight += item.weight * item.quantity;
  });

  return (
    <div className="flex flex-col gap-3.5 text-slate-900 leading-tight">
      <div className="border-b-2 border-slate-900 pb-1 mb-1">
        <h2 className="font-display text-lg font-bold text-slate-950 uppercase tracking-wide">
          Equipment, Inventory & Roleplay Details
        </h2>
        <p className="text-[11px] text-slate-600">
          Carried items, wealth pouch, carrying capacity, and character background notes.
        </p>
      </div>

      {/* ── 1. Top Row: Currency & Carrying Capacity ── */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
        {/* Currency Pouch (7 cols) */}
        <div className="sm:col-span-7 border-2 border-slate-900 rounded-lg p-2.5 bg-white">
          <span className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 block mb-1.5">
            Coinage & Wealth Pouch
          </span>
          <div className="grid grid-cols-5 gap-1.5 text-center">
            <div className="border border-amber-900/30 bg-amber-50/50 rounded p-1">
              <span className="text-[9px] uppercase font-bold text-amber-900 block">CP</span>
              <span className="font-mono font-bold text-sm text-slate-900">{cp}</span>
            </div>
            <div className="border border-slate-300 bg-slate-100/50 rounded p-1">
              <span className="text-[9px] uppercase font-bold text-slate-600 block">SP</span>
              <span className="font-mono font-bold text-sm text-slate-900">{sp}</span>
            </div>
            <div className="border border-indigo-900/30 bg-indigo-50/50 rounded p-1">
              <span className="text-[9px] uppercase font-bold text-indigo-900 block">EP</span>
              <span className="font-mono font-bold text-sm text-slate-900">{ep}</span>
            </div>
            <div className="border border-yellow-700/50 bg-yellow-50 rounded p-1">
              <span className="text-[9px] uppercase font-bold text-yellow-800 block">GP</span>
              <span className="font-mono font-bold text-sm text-yellow-950">{gp}</span>
            </div>
            <div className="border border-cyan-900/30 bg-cyan-50/50 rounded p-1">
              <span className="text-[9px] uppercase font-bold text-cyan-900 block">PP</span>
              <span className="font-mono font-bold text-sm text-slate-900">{pp}</span>
            </div>
          </div>
        </div>

        {/* Carrying Capacity (5 cols) */}
        <div className="sm:col-span-5 border-2 border-slate-900 rounded-lg p-2.5 bg-slate-50/70 flex flex-col justify-between">
          <span className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 block mb-1">
            Encumbrance & Capacity
          </span>
          <div className="grid grid-cols-3 gap-1 text-center text-xs">
            <div>
              <span className="text-[9px] text-slate-500 uppercase font-bold block">Current</span>
              <span className="font-mono font-bold text-slate-900 text-sm">{totalWeight.toFixed(1)} <span className="text-[10px] font-normal">lbs</span></span>
            </div>
            <div>
              <span className="text-[9px] text-slate-500 uppercase font-bold block">Capacity</span>
              <span className="font-mono font-bold text-slate-900 text-sm">{carryCapacity} <span className="text-[10px] font-normal">lbs</span></span>
            </div>
            <div>
              <span className="text-[9px] text-slate-500 uppercase font-bold block">Push/Drag</span>
              <span className="font-mono font-bold text-slate-900 text-sm">{pushDragLift} <span className="text-[10px] font-normal">lbs</span></span>
            </div>
          </div>
          <div className="mt-1 text-[9px] text-slate-500 text-center">
            {totalWeight <= carryCapacity ? "● Normal Encumbrance" : "⚠️ Encumbered"}
          </div>
        </div>
      </div>

      {/* ── 2. Equipped Gear Summary ── */}
      <div className="border border-slate-800 rounded-lg p-2 bg-white text-xs">
        <span className="font-display font-bold text-[11px] uppercase tracking-wide text-slate-900 block mb-1">
          Equipped Armor & Attunement Items
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10.5px]">
          <div>
            <span className="text-slate-500 font-medium">Equipped Armor: </span>
            <span className="font-semibold text-slate-900">
              {equippedArmorName || "None (Unarmored)"}
            </span>
          </div>
          <div>
            <span className="text-slate-500 font-medium">Attuned Magic Items: </span>
            <span className="font-semibold text-slate-900">
              [ ] __________________ [ ] __________________ [ ] __________________
            </span>
          </div>
        </div>
      </div>

      {/* ── 3. Full Inventory List Table ── */}
      <div className="border-2 border-slate-900 rounded-lg bg-white">
        <div className="bg-slate-800 text-white px-3 py-1 flex items-center justify-between font-display font-bold text-xs uppercase tracking-wider">
          <span>Inventory & Backpack Items</span>
          <span className="text-[10px] font-normal text-slate-300">
            {itemsList.length} {itemsList.length === 1 ? "item" : "items"}
          </span>
        </div>

        <div>
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-[9px] uppercase text-slate-500 bg-slate-50">
                <th className="py-1 pl-3 pr-2 w-12 text-center">Qty</th>
                <th className="py-1 pr-3">Item Name</th>
                <th className="py-1 px-2 text-center w-20">Weight (lbs)</th>
                <th className="py-1 pr-3">Notes & Properties</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-[10.5px]">
              {itemsList.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-3 text-center text-slate-400 italic">
                    No items in inventory.
                  </td>
                </tr>
              ) : (
                itemsList.map((item, idx) => {
                  const iName = item.name;
                  const qty = item.quantity;
                  const weight = item.weight;
                  const notes = item.notes;

                  return (
                    <tr key={idx} className="hover:bg-slate-50/70">
                      <td className="py-1 pl-3 pr-2 text-center font-mono font-bold text-slate-800">
                        {qty}×
                      </td>
                      <td className="py-1 pr-3 font-semibold text-slate-900">
                        {iName}
                      </td>
                      <td className="py-1 px-2 text-center font-mono text-slate-600 text-[10px]">
                        {weight > 0 ? `${(weight * qty).toFixed(1)}` : "—"}
                      </td>
                      <td className="py-1 pr-3 text-slate-600 text-[10px] truncate max-w-[280px]">
                        {notes || "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── 4. Character Backstory, Appearance & Roleplay Notes ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Appearance & Physical Description */}
        <div className="border border-slate-800 rounded-lg p-2.5 bg-white text-xs space-y-1.5">
          <span className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 block border-b border-slate-200 pb-0.5">
            Physical Characteristics & Details
          </span>
          <div className="grid grid-cols-3 gap-1 text-[10px]">
            <div><span className="text-slate-500 font-medium">Age:</span> _______</div>
            <div><span className="text-slate-500 font-medium">Height:</span> _______</div>
            <div><span className="text-slate-500 font-medium">Weight:</span> _______</div>
            <div><span className="text-slate-500 font-medium">Eyes:</span> _______</div>
            <div><span className="text-slate-500 font-medium">Skin:</span> _______</div>
            <div><span className="text-slate-500 font-medium">Hair:</span> _______</div>
          </div>
          <div className="pt-1 border-t border-slate-100">
            <span className="text-[10px] text-slate-500 block font-medium">Distinctive Features:</span>
            <div className="h-12 border border-dashed border-slate-200 rounded p-1 text-[10px] text-slate-400">
              Scars, tattoos, holy symbols, spellcasting foci, clothing style...
            </div>
          </div>
        </div>

        {/* Backstory & Campaign Notes */}
        <div className="border border-slate-800 rounded-lg p-2.5 bg-white text-xs space-y-1">
          <span className="font-display font-bold text-xs uppercase tracking-wide text-slate-900 block border-b border-slate-200 pb-0.5">
            Campaign Notes, Allies & Quest Log
          </span>
          <div className="h-24 border border-dashed border-slate-200 rounded p-1 text-[10px] text-slate-400">
            Allies, factions, lingering quest hooks, treasure, safehouses...
          </div>
        </div>
      </div>
    </div>
  );
}
